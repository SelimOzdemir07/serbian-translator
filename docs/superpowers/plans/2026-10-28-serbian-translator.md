# Serbian Quick Translator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small Windows desktop app that translates words and short
phrases between Turkish/English and Serbian, and shows 3 example sentences
for each lookup.

**Architecture:** `translator.py` (Claude request and answer validation) and
`settings.py` (JSON file in AppData) are plain Python modules with no UI.
`app.py` exposes an `Api` class to a pywebview window whose UI is static
HTML/CSS/JS in `ui/`. Everything except the window is unit-tested offline
with fakes.

**Tech Stack:** Python 3.12, pywebview, anthropic SDK, pytest, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-10-28-serbian-translator-design.md`

## Global Constraints

- Windows desktop only; Python 3.12 (already installed). No Node, no frontend framework.
- Model: `claude-haiku-5-5`, in one constant `MODEL` in `translator.py`.
- Directions: exactly `tr-sr`, `en-sr`, `sr-en`, `sr-tr`. Default `tr-sr`.
- Serbian output is always Latin script; Serbian input may be Latin or Cyrillic.
- Request timeout 15 seconds; `max_tokens` 600.
- Exactly 3 examples; at most 2 alternatives.
- Settings file: `%APPDATA%\SerbianTranslator\settings.json`, keys `api_key` and `direction`.
- Window title "Serbian Translator", about 500×600, resizable.
- Error copy (verbatim):
  - `auth` → "API key was rejected — check it in ⚙"
  - `network` → "No connection — check your internet"
  - `timeout` → "Took too long — try again"
  - `bad_answer` → "Couldn't read the answer — try again"
  - `other` → "Something went wrong — try again"
- The UI never inserts raw HTML from the model. It escapes all text, then turns `**…**` into `<strong>`.
- Tests never make real API calls.

## Review Focus

1. **The model answers in Cyrillic despite the instruction.** The user should still see Latin. `parse_result` transliterates Serbian fields (Task 2, `test_cyrillic_serbian_is_transliterated`).
2. **Cyrillic input for `sr-en` / `sr-tr`.** It should be understood. The system prompt states that Serbian input may be in Cyrillic (Task 3, `test_request_mentions_cyrillic_input`).
3. **A blank or whitespace-only API key is saved.** It must be refused, not stored (Task 4, `test_save_key_rejects_blank`).
4. **The settings file holds an unknown direction or a non-dict JSON.** Fall back to defaults instead of crashing (Task 1, `test_invalid_direction_falls_back`, `test_non_dict_json_gives_defaults`).
5. **A phrase or sentence is entered instead of one word.** `grammar` comes back empty and must render as nothing, not as "None" (Task 2, `test_empty_grammar_becomes_none`).

---

## File Structure

```
app.py               # pywebview window + Api class bridging JS ↔ Python
translator.py        # MODEL, DIRECTIONS, Result/Example, to_latin, parse_result, translate, errors
settings.py          # load/save/default_path for settings.json
ui/index.html        # markup
ui/style.css         # minimal styling, light/dark via prefers-color-scheme
ui/app.js            # UI behaviour, keyboard shortcuts, rendering, error copy
tests/test_settings.py
tests/test_translator.py
tests/test_app.py
requirements.txt     # pywebview, anthropic
requirements-dev.txt # -r requirements.txt, pytest, pyinstaller
.gitignore           # .venv/, __pycache__/, build/, dist/, *.spec
```

Run every command from the repo root using the virtualenv's Python:
`.venv\Scripts\python`.

---

### Task 1: Project setup and settings

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `settings.py`, `tests/test_settings.py`

**Interfaces:**
- Produces:
  - `settings.DEFAULTS: dict = {"api_key": None, "direction": "tr-sr"}`
  - `settings.VALID_DIRECTIONS = ("tr-sr", "en-sr", "sr-en", "sr-tr")`
  - `settings.load(path: pathlib.Path) -> dict`
  - `settings.save(path: pathlib.Path, data: dict) -> None`
  - `settings.default_path() -> pathlib.Path`

- [ ] **Step 1: Create the virtualenv and install dependencies**

Write `requirements.txt` (`pywebview`, `anthropic`) and `requirements-dev.txt`
(`-r requirements.txt`, `pytest`, `pyinstaller`), plus `.gitignore` as listed
above.

Run: `python -m venv .venv` then `.venv\Scripts\python -m pip install -r requirements-dev.txt`
Expected: ends with "Successfully installed …", including pywebview, anthropic and pytest.

- [ ] **Step 2: Write the failing tests** in `tests/test_settings.py`

```python
import json
from settings import load, save, DEFAULTS

def test_missing_file_gives_defaults(tmp_path):
    assert load(tmp_path / "s.json") == DEFAULTS

def test_corrupt_file_gives_defaults(tmp_path):
    p = tmp_path / "s.json"; p.write_text("{not json", encoding="utf-8")
    assert load(p) == DEFAULTS

def test_non_dict_json_gives_defaults(tmp_path):
    p = tmp_path / "s.json"; p.write_text("[1, 2]", encoding="utf-8")
    assert load(p) == DEFAULTS

def test_invalid_direction_falls_back(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"api_key": "k", "direction": "xx-yy"}), encoding="utf-8")
    assert load(p) == {"api_key": "k", "direction": "tr-sr"}

def test_round_trip_creates_folder(tmp_path):
    p = tmp_path / "nested" / "dir" / "s.json"
    save(p, {"api_key": "sk-1", "direction": "sr-en"})
    assert load(p) == {"api_key": "sk-1", "direction": "sr-en"}

def test_default_path_is_in_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from settings import default_path
    assert default_path() == tmp_path / "SerbianTranslator" / "settings.json"
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv\Scripts\python -m pytest tests/test_settings.py -v`
Expected: errors with `ModuleNotFoundError: No module named 'settings'`.

- [ ] **Step 4: Implement `settings.py`**

`load` must never raise for a missing, unreadable or invalid file. It merges
the known keys over `DEFAULTS` and ignores unknown keys. An `api_key` that is
not a non-empty string becomes `None`. A `direction` not in
`VALID_DIRECTIONS` becomes `"tr-sr"`. `save` does `mkdir(parents=True,
exist_ok=True)` and writes UTF-8 JSON. Return a fresh dict each time; never
return `DEFAULTS` itself.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m pytest tests/test_settings.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt requirements-dev.txt .gitignore settings.py tests/test_settings.py
git commit -m "feat: add settings storage and project setup"
```

---

### Task 2: Result model, Cyrillic→Latin conversion, answer validation

**Files:**
- Create: `translator.py`, `tests/test_translator.py`

**Interfaces:**
- Produces:
  - `MODEL = "claude-haiku-5-5"`
  - `DIRECTIONS: dict[str, tuple[str, str]]` = `{"tr-sr": ("Turkish", "Serbian"), "en-sr": ("English", "Serbian"), "sr-en": ("Serbian", "English"), "sr-tr": ("Serbian", "Turkish")}`
  - `@dataclass Example(serbian: str, other: str)`
  - `@dataclass Result(translation: str, grammar: str | None, alternatives: list[str], examples: list[Example])`
  - `class BadAnswer(Exception)`
  - `to_latin(text: str) -> str`
  - `parse_result(tool_input: dict, direction: str) -> Result`. This adds a `direction` parameter to the spec's signature, so the function knows which fields are Serbian and need Cyrillic→Latin conversion.

- [ ] **Step 1: Write the failing tests** in `tests/test_translator.py`

```python
import pytest
from translator import parse_result, to_latin, BadAnswer, Result, Example

def valid(**over):
    d = {
        "translation": "knjiga",
        "grammar": "noun, f.",
        "alternatives": ["sveska"],
        "examples": [
            {"serbian": "Čitam **knjigu**.", "other": "Kitap okuyorum."},
            {"serbian": "Ova **knjiga** je moja.", "other": "Bu kitap benim."},
            {"serbian": "Kupio sam **knjigu**.", "other": "Bir kitap aldım."},
        ],
    }
    d.update(over); return d

def test_valid_answer_parses():
    r = parse_result(valid(), "tr-sr")
    assert r == Result("knjiga", "noun, f.", ["sveska"],
                       [Example("Čitam **knjigu**.", "Kitap okuyorum."),
                        Example("Ova **knjiga** je moja.", "Bu kitap benim."),
                        Example("Kupio sam **knjigu**.", "Bir kitap aldım.")])

@pytest.mark.parametrize("field", ["translation", "examples", "alternatives"])
def test_missing_field_rejected(field):
    d = valid(); del d[field]
    with pytest.raises(BadAnswer):
        parse_result(d, "tr-sr")

def test_empty_translation_rejected():
    with pytest.raises(BadAnswer):
        parse_result(valid(translation="  "), "tr-sr")

@pytest.mark.parametrize("n", [2, 4])
def test_wrong_example_count_rejected(n):
    ex = valid()["examples"]
    with pytest.raises(BadAnswer):
        parse_result(valid(examples=(ex * 2)[:n]), "tr-sr")

def test_wrong_types_rejected():
    with pytest.raises(BadAnswer):
        parse_result(valid(examples=[{"serbian": 1, "other": "x"}] * 3), "tr-sr")
    with pytest.raises(BadAnswer):
        parse_result(valid(alternatives="sveska"), "tr-sr")

def test_alternatives_trimmed_to_two():
    assert parse_result(valid(alternatives=["a", "b", "c"]), "tr-sr").alternatives == ["a", "b"]

@pytest.mark.parametrize("g", ["", "   ", None])
def test_empty_grammar_becomes_none(g):
    assert parse_result(valid(grammar=g), "tr-sr").grammar is None

def test_to_latin():
    assert to_latin("Добар дан, Љубљана и Џеј!") == "Dobar dan, Ljubljana i Džej!"
    assert to_latin("already latin") == "already latin"

def test_cyrillic_serbian_is_transliterated():
    d = valid(translation="књига", alternatives=["свеска"])
    d["examples"][0]["serbian"] = "Читам **књигу**."
    r = parse_result(d, "tr-sr")
    assert r.translation == "knjiga"
    assert r.alternatives == ["sveska"]
    assert r.examples[0].serbian == "Čitam **knjigu**."

def test_non_serbian_target_not_transliterated():
    # sr-en: translation is English, so it is left untouched
    assert parse_result(valid(translation="book"), "sr-en").translation == "book"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python -m pytest tests/test_translator.py -v`
Expected: errors with `ModuleNotFoundError: No module named 'translator'`.

- [ ] **Step 3: Implement the Task 2 interfaces in `translator.py`**

`to_latin` is a character map applied character by character. It covers
uppercase and lowercase, and leaves unmapped characters unchanged. The
lowercase map is below; uppercase maps the same way, with the first letter
capitalized (`Љ→Lj`, `Њ→Nj`, `Џ→Dž`).

```
а a  б b  в v  г g  д d  ђ đ  е e  ж ž  з z  и i  ј j  к k  л l  љ lj
м m  н n  њ nj о o  п p  р r  с s  т t  ћ ć  у u  ф f  х h  ц c  ч č
џ dž ш š
```

`parse_result` validates types strictly and raises `BadAnswer` with a short
reason. It strips every string. `examples` must be a list of exactly 3
objects, each with non-empty string `serbian` and `other`. `alternatives`
must be a list of strings; drop empty ones, then keep the first 2. Apply
`to_latin` to `examples[*].serbian` always. When the direction's target is
Serbian (`tr-sr`, `en-sr`), also apply it to `translation` and
`alternatives`. An unknown direction raises `ValueError`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m pytest tests/test_translator.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add translator.py tests/test_translator.py
git commit -m "feat: add translation result parsing and Cyrillic-to-Latin conversion"
```

---

### Task 3: Calling Claude and mapping errors

**Files:**
- Modify: `translator.py`
- Modify: `tests/test_translator.py`

**Interfaces:**
- Consumes: `MODEL`, `DIRECTIONS`, `parse_result`, `BadAnswer` (Task 2)
- Produces:
  - `TOOL_NAME = "give_translation"`
  - `class TranslateError(Exception)` with attribute `kind: str`, one of `"auth" | "network" | "timeout" | "bad_answer" | "other"`
  - `translate(client, direction: str, text: str) -> Result`. `client` is anything with `client.messages.create(**kwargs)` (an `anthropic.Anthropic` in production).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_translator.py`)

```python
import anthropic, httpx
from types import SimpleNamespace
from translator import translate, TranslateError, MODEL, TOOL_NAME

class FakeClient:
    def __init__(self, tool_input=None, exc=None):
        self.calls, self._input, self._exc = [], tool_input, exc
        self.messages = self
    def create(self, **kw):
        self.calls.append(kw)
        if self._exc: raise self._exc
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", name=TOOL_NAME, input=self._input)])

REQ = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

def test_request_shape():
    c = FakeClient(valid())
    r = translate(c, "tr-sr", "  kitap  ")
    kw = c.calls[0]
    assert r.translation == "knjiga"
    assert kw["model"] == MODEL and kw["max_tokens"] == 600 and kw["timeout"] == 15
    assert kw["tool_choice"] == {"type": "tool", "name": TOOL_NAME}
    assert kw["tools"][0]["name"] == TOOL_NAME
    assert "Turkish" in kw["system"] and "Serbian" in kw["system"] and "Latin" in kw["system"]
    assert kw["messages"] == [{"role": "user", "content": "kitap"}]

def test_request_mentions_cyrillic_input():
    c = FakeClient(valid(translation="book"))
    translate(c, "sr-en", "књига")
    assert "Cyrillic" in c.calls[0]["system"]

def test_unknown_direction():
    with pytest.raises(ValueError):
        translate(FakeClient(valid()), "de-sr", "x")

def test_blank_text():
    with pytest.raises(ValueError):
        translate(FakeClient(valid()), "tr-sr", "   ")

@pytest.mark.parametrize("exc, kind", [
    (anthropic.AuthenticationError("bad", response=httpx.Response(401, request=REQ), body=None), "auth"),
    (anthropic.APITimeoutError(request=REQ), "timeout"),
    (anthropic.APIConnectionError(request=REQ), "network"),
    (anthropic.InternalServerError("boom", response=httpx.Response(500, request=REQ), body=None), "other"),
])
def test_api_errors_mapped(exc, kind):
    with pytest.raises(TranslateError) as e:
        translate(FakeClient(exc=exc), "tr-sr", "kitap")
    assert e.value.kind == kind

def test_malformed_answer_is_bad_answer():
    with pytest.raises(TranslateError) as e:
        translate(FakeClient({"translation": "x"}), "tr-sr", "kitap")
    assert e.value.kind == "bad_answer"

def test_no_tool_block_is_bad_answer():
    c = FakeClient(valid())
    c.create = lambda **kw: SimpleNamespace(content=[SimpleNamespace(type="text", text="hi")])
    with pytest.raises(TranslateError) as e:
        translate(c, "tr-sr", "kitap")
    assert e.value.kind == "bad_answer"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python -m pytest tests/test_translator.py -v`
Expected: the new tests fail with `ImportError: cannot import name 'translate'`.

- [ ] **Step 3: Implement `translate` in `translator.py`**

- Validate the direction (`ValueError`), then strip the text (`ValueError` if empty).
- Call `client.messages.create(model=MODEL, max_tokens=600, timeout=15, system=…, tools=[TOOL], tool_choice={"type": "tool", "name": TOOL_NAME}, messages=[{"role": "user", "content": text}])`.
- `TOOL.input_schema` is an object with required properties:
  - `translation` (string)
  - `grammar` (string; empty for phrases)
  - `alternatives` (array of string, `maxItems` 2)
  - `examples` (array, `minItems` and `maxItems` 3, of objects with required string `serbian` and `other`)
- System prompt text, with `{src}` and `{tgt}` taken from `DIRECTIONS`. `{other}` is the non-Serbian language of the pair:

```
You are a concise {src}→{tgt} dictionary for a learner.
Translate the user's word or short phrase from {src} to {tgt} and answer only by calling the give_translation tool.
Always write Serbian in Latin script, never Cyrillic. Serbian input may be written in Latin or Cyrillic.
translation: the most common translation.
grammar: for a single word, a short hint like "noun, f." or "verb, imperfective"; empty string for phrases.
alternatives: up to 2 other common translations, or an empty list.
examples: exactly 3 short, natural Serbian sentences using the translation, with the Serbian word wrapped in **double asterisks**; "other" is each sentence translated into {other}.
```

- Exception mapping, in this order (`APITimeoutError` subclasses `APIConnectionError`):
  - `anthropic.AuthenticationError` → `auth`
  - `anthropic.APITimeoutError` → `timeout`
  - `anthropic.APIConnectionError` → `network`
  - any other `anthropic.APIError` → `other`
  - no `tool_use` block, or `BadAnswer` → `bad_answer`

  Re-raise as `TranslateError(kind)` with `from` the original.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m pytest -v`
Expected: all tests in both files pass.

- [ ] **Step 5: Commit**

```bash
git add translator.py tests/test_translator.py
git commit -m "feat: call Claude for translations and map API errors"
```

---

### Task 4: The `Api` bridge in `app.py`

**Files:**
- Create: `app.py`, `tests/test_app.py`

**Interfaces:**
- Consumes: `settings.load/save/default_path/VALID_DIRECTIONS` (Task 1); `translator.translate`, `TranslateError` (Task 3)
- Produces: `class Api` with:
  - `__init__(self, settings_path: Path, client_factory=anthropic.Anthropic, translate_fn=translator.translate)`. All internal attributes are prefixed `_`, so pywebview does not expose them to JS.
  - `get_state() -> {"has_key": bool, "direction": str}`
  - `save_key(key: str) -> {"ok": bool}`
  - `set_direction(direction: str) -> None`
  - `translate(direction: str, text: str) -> {"ok": True, "result": dict} | {"ok": False, "error": str}`. `error` is one of the five `TranslateError` kinds, or `"no_key"`.
  - `main() -> None`: opens the window.

- [ ] **Step 1: Write the failing tests** in `tests/test_app.py`

```python
from app import Api
from settings import load
from translator import Result, Example, TranslateError

R = Result("knjiga", None, [], [Example("**knjiga**", "kitap")] * 3)

def make(tmp_path, fn=lambda c, d, t: R):
    made = []
    api = Api(tmp_path / "s.json", client_factory=lambda api_key: made.append(api_key) or object(), translate_fn=fn)
    return api, made

def test_initial_state(tmp_path):
    api, _ = make(tmp_path)
    assert api.get_state() == {"has_key": False, "direction": "tr-sr"}

def test_translate_without_key(tmp_path):
    api, _ = make(tmp_path)
    assert api.translate("tr-sr", "kitap") == {"ok": False, "error": "no_key"}

def test_save_key_and_translate(tmp_path):
    api, made = make(tmp_path)
    assert api.save_key("  sk-123 ") == {"ok": True}
    assert made == ["sk-123"] and load(tmp_path / "s.json")["api_key"] == "sk-123"
    out = api.translate("tr-sr", "kitap")
    assert out["ok"] is True and out["result"]["translation"] == "knjiga"
    assert out["result"]["examples"][0] == {"serbian": "**knjiga**", "other": "kitap"}

def test_save_key_rejects_blank(tmp_path):
    api, _ = make(tmp_path)
    assert api.save_key("   ") == {"ok": False}
    assert api.get_state()["has_key"] is False

def test_existing_key_loaded_on_start(tmp_path):
    make(tmp_path)[0].save_key("sk-1")
    api, made = make(tmp_path)
    assert api.get_state()["has_key"] is True and made == ["sk-1"]

def test_direction_persisted_and_validated(tmp_path):
    api, _ = make(tmp_path)
    api.set_direction("sr-tr")
    api.set_direction("bogus")
    assert make(tmp_path)[0].get_state()["direction"] == "sr-tr"

def test_errors_become_kinds(tmp_path):
    def boom(c, d, t): raise TranslateError("network")
    api, _ = make(tmp_path, boom); api.save_key("k")
    assert api.translate("tr-sr", "x") == {"ok": False, "error": "network"}

def test_unexpected_exception_is_other(tmp_path):
    def boom(c, d, t): raise ValueError("blank")
    api, _ = make(tmp_path, boom); api.save_key("k")
    assert api.translate("tr-sr", " ") == {"ok": False, "error": "other"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python -m pytest tests/test_app.py -v`
Expected: errors with `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 3: Implement `Api` and `main()` in `app.py`**

- Build the client with `client_factory(api_key=key)` at init when a key exists, and on every successful `save_key`.
- `set_direction` silently ignores invalid values.
- The result dict comes from `dataclasses.asdict`.
- `translate` catches `TranslateError` and returns its kind; any other `Exception` becomes `"other"`.
- `main()`:
  - Resolve the UI folder as `Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "ui" / "index.html"`.
  - `webview.create_window("Serbian Translator", url=str(that path), js_api=Api(settings.default_path()), width=500, height=600, resizable=True)`
  - `webview.start()`
  - Guard with `if __name__ == "__main__": main()`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m pytest -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: add Api bridge and window entry point"
```

---

### Task 5: The user interface

**Files:**
- Create: `ui/index.html`, `ui/style.css`, `ui/app.js`

**Interfaces:**
- Consumes: `window.pywebview.api.get_state()`, `.save_key(key)`, `.set_direction(dir)`, `.translate(dir, text)` (Task 4). All return Promises, and are available only after the `pywebviewready` event.

- [ ] **Step 1: Build the markup and styles**

- `index.html` has a top bar with four buttons, in this order: `TR→SR`, `EN→SR`, `SR→EN`, `SR→TR`, with `data-dir` set to `tr-sr`, `en-sr`, `sr-en`, `sr-tr`. A ⚙ button sits on the right.
- Below the bar: a settings panel (hidden by default), containing a `type="password"` input and a Save button.
- Then one text input, then a result area with these parts: the main translation, the grammar, the "also:" alternatives line, an "Examples" heading, and an examples list.
- No external resources.
- `style.css` uses the system font stack and generous spacing, with the translation at about 28px. Colors are CSS variables, swapped under `@media (prefers-color-scheme: dark)`. The active direction button is highlighted.

- [ ] **Step 2: Implement the behaviour in `app.js`**

- **Startup:** on `pywebviewready`, call `get_state()`, highlight the stored direction, and show the settings panel if `has_key` is false; otherwise focus the input.
- **Switching direction:** clicking a direction button, or Ctrl+1…4 (`keydown` with `ctrlKey` and keys `1`–`4`), sets the direction, calls `set_direction`, and refocuses the input.
- **Enter in the input:**
  - Ignore it if the input is blank after trimming.
  - Otherwise show "Translating…" and call `translate`.
  - Discard the response if a newer request was started meanwhile (use an incrementing request id).
  - On `ok`, render the result.
  - On the `no_key` error, open the settings panel.
  - On any other error, show the matching message from Global Constraints as a single line.
- **⚙ / Save:** ⚙ toggles the settings panel. Save calls `save_key`. On `ok`, it hides the panel and focuses the input. Otherwise it shows "Please paste a valid key" under the field.
- **Rendering:**
  - Build all text with an `escapeHtml` function first, then replace `/\*\*(.+?)\*\*/g` with `<strong>$1</strong>`.
  - Hide the grammar line when `grammar` is null, and the "also:" line when `alternatives` is empty.

- [ ] **Step 3: Manual check with your real key**

Run: `.venv\Scripts\python app.py`

Expected, every item ticked:

- [ ] First launch (no settings file) shows the key panel.
- [ ] After saving the key, the input is focused.
- [ ] `kitap` in TR→SR gives `knjiga`, a grammar hint, and 3 examples with the word in bold and Turkish lines underneath.
- [ ] `book` in EN→SR gives a Serbian result with English example lines.
- [ ] `knjiga` in SR→EN and `књига` in SR→TR both translate, and all Serbian is shown in Latin script.
- [ ] Ctrl+1…4 switch the highlighted direction.
- [ ] A phrase (`dobar dan`) shows no grammar line.
- [ ] Typing `<b>x</b>` and translating shows the tags as text, never as bold.
- [ ] A wrong key shows "API key was rejected — check it in ⚙".
- [ ] With Wi-Fi off, the app shows "No connection — check your internet".
- [ ] After closing and reopening, the last direction is still selected.
- [ ] With Windows in dark mode, the window is dark.

- [ ] **Step 4: Commit**

```bash
git add ui
git commit -m "feat: add minimal translator UI"
```

---

### Task 6: Package as an .exe with a desktop shortcut

**Files:**
- Create: `build.ps1`
- Modify: `.gitignore` (already ignores `build/`, `dist/`, `*.spec`)

- [ ] **Step 1: Write `build.ps1`**

The script does three things:

1. Runs the tests (`.venv\Scripts\python -m pytest -q`) and stops if they fail.
2. Builds the app:

   ```
   .venv\Scripts\pyinstaller --noconfirm --onefile --windowed --name SerbianTranslator --add-data "ui;ui" app.py
   ```

3. Creates `SerbianTranslator.lnk` on the user's Desktop. It points to `dist\SerbianTranslator.exe` (absolute path), using `WScript.Shell`'s `CreateShortcut`.

- [ ] **Step 2: Build**

Run: `powershell -ExecutionPolicy Bypass -File build.ps1`
Expected: tests pass, `dist\SerbianTranslator.exe` exists, and a "SerbianTranslator" shortcut appears on the Desktop.

- [ ] **Step 3: Launch from the shortcut**

Double-click the Desktop shortcut.
Expected: the window opens with no console window. The saved key and direction are still there, because settings live in AppData, not next to the exe. Translating `kitap` works.

- [ ] **Step 4: Commit and push**

```bash
git add build.ps1
git commit -m "build: package app as single exe with desktop shortcut"
git push
```
