# Serbian Quick Translator — Design

Date: 2026-10-28
Status: Approved in conversation, awaiting spec review

## Purpose

A tiny personal desktop app for looking up Serbian words and short phrases
quickly while learning/using Serbian. The user already knows Turkish and
English. Each lookup shows the translation plus example sentences so the
user understands how the word is actually used.

**Success:** open the app, type a word, press Enter, and within ~1–2 seconds
see the translation and 3 example sentences — no mouse needed.

**Non-goals (deliberately excluded):** history, favorites, flashcards,
text-to-speech, accounts, sharing, document translation, theme toggle,
mobile support.

## Decisions

| Topic | Decision |
|---|---|
| Platform | Windows desktop only |
| Technology | Python 3.12 + pywebview (native window using Edge WebView2, UI in HTML/CSS/JS) |
| Translation engine | Claude API via the `anthropic` Python SDK |
| Model | `claude-haiku-5-5`, defined in one constant `MODEL` in `translator.py` |
| Serbian script | Output always Latin. Input accepted in Latin or Cyrillic |
| Directions | TR→SR, EN→SR, SR→EN, SR→TR (exactly these four) |
| API key storage | Plain text in `%APPDATA%\SerbianTranslator\settings.json` |

## User interface

A single window, about 500×600 px.

- **Top row:** four direction buttons `TR→SR`, `EN→SR`, `SR→EN`, `SR→TR`,
  with a ⚙ settings button on the right. The active direction is
  highlighted. Ctrl+1 … Ctrl+4 select the directions in that order. The
  last used direction is remembered across launches (default: `TR→SR`).
- **Input:** one single-line text box, focused on launch and after each
  direction change. Enter submits. Empty or whitespace-only input does
  nothing.
- **While waiting:** the result area shows a subtle "Translating…" line;
  the input stays editable.
- **Result area:**
  - Main translation in large text.
  - Grammar hint in small text when the input is a single word (for
    example `noun, f.` or `verb, imperfective`). It is omitted for phrases.
  - Alternatives: if the word has other common meanings, show up to 2
    extra translations on one small line ("also: …"). Omitted if none.
  - **Examples:** exactly 3. Each example is a Serbian sentence with the
    translated word in bold, followed on the next line by its translation
    into the non-Serbian language of the current direction (Turkish for
    TR↔SR, English for EN↔SR).
- **Settings (⚙):** a small inline panel with one password-type field for
  the API key, plus Save. On first launch (no key saved), this panel is
  shown automatically instead of the input.
- **Errors:** shown as one short line in place of the result, never as a
  popup:
  - no key → the settings panel opens
  - invalid key (401) → "API key was rejected — check it in ⚙"
  - network failure → "No connection — check your internet"
  - timeout (15 s) → "Took too long — try again"
  - malformed model answer → "Couldn't read the answer — try again"
  - any other API error → "Something went wrong — try again"
- **Theme:** follows the Windows light/dark setting through
  `prefers-color-scheme`.

## Architecture

```
ui/app.js ──(pywebview js_api)──► app.py: Api
                                   ├─► translator.py ──► Claude API
                                   └─► settings.py   ──► settings.json
```

### `translator.py`

The translation logic, independent of the UI.

- `MODEL = "claude-haiku-5-5"`
- `DIRECTIONS`: a mapping of `"tr-sr" | "en-sr" | "sr-en" | "sr-tr"` to
  (source language name, target language name).
- `translate(client, direction, text) -> Result`
  - Validates `direction` (unknown → `ValueError`) and strips `text`.
  - Sends one Messages API request. The system prompt says: translate
    from source to target; write all Serbian in Latin script; return the
    structured result. The response is forced into a fixed JSON shape by
    tool use with `tool_choice` set to one tool named `give_translation`.
  - Timeout: 15 seconds. `max_tokens`: 600.
- `Result` (dataclass): `translation: str`, `grammar: str | None`,
  `alternatives: list[str]` (max 2), `examples: list[Example]`
  (exactly 3), where `Example` is `serbian: str`, `other: str`. In
  `Example.serbian`, the word in focus is wrapped in `**…**`.
- `parse_result(tool_input: dict) -> Result` validates the shape. It
  raises `BadAnswer` for missing or empty fields, wrong types, or a
  number of examples other than 3. Extra alternatives are cut to 2.
- API errors are mapped to one exception type,
  `TranslateError(kind)`, where `kind` is one of `auth`, `network`,
  `timeout`, `bad_answer`, `other`.
- `client` is passed in, so tests can supply a fake.

### `settings.py`

- `load(path) -> dict` returns `{"api_key": str | None, "direction": str}`.
  A missing or corrupt file gives the defaults
  `{"api_key": None, "direction": "tr-sr"}`.
- `save(path, data)` writes JSON and creates the folder if needed.
- `default_path()` returns `%APPDATA%\SerbianTranslator\settings.json`.

### `app.py`

- `Api` class exposed to JavaScript:
  - `get_state() -> {"has_key": bool, "direction": str}`
  - `save_key(key) -> {"ok": bool}`: saves the key and rebuilds the
    Anthropic client.
  - `set_direction(direction) -> None`: saves it.
  - `translate(direction, text) -> {"ok": true, "result": {...}}` or
    `{"ok": false, "error": kind}`.
- Creates the pywebview window titled "Serbian Translator" from
  `ui/index.html`, about 500×600, resizable.

### `ui/`

- `index.html`, `style.css`, `app.js`. Plain HTML/CSS/JS, no framework
  and no external network resources.
- `app.js` turns the `**…**` markers into `<strong>` after escaping all
  text (no raw HTML from the model is inserted).
- `app.js` maps error kinds to the messages listed above.

## Testing

- **pytest, offline, no real API calls:**
  - `translator.py`, using a fake client:
    - the request contains the right language pair and the Latin-script
      instruction
    - `parse_result` accepts a valid answer
    - `parse_result` rejects missing fields, wrong types and the wrong
      number of examples
    - alternatives are trimmed to 2
    - API exceptions map to the right `TranslateError.kind`
    - an unknown direction raises `ValueError`
  - `settings.py`, using a temporary folder: defaults when the file is
    missing or corrupt, save/load round trip, the folder is created.
- **Manual check:**
  - first launch shows the key panel
  - each of the 4 directions gives a correct translation
  - Cyrillic input works for SR→EN and SR→TR
  - Ctrl+1–4 switch directions
  - the error line appears with a wrong key and with no network
  - the remembered direction survives a restart

## Packaging

- `requirements.txt`: `pywebview`, `anthropic`. Dev dependencies: `pytest`.
- Run during development with `python app.py`.
- Final step: build a single windowed `.exe` with PyInstaller (bundling
  `ui/`) and create a desktop shortcut to it.
