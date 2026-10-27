"""Opens the window and connects the page (ui/app.js) to Python."""
import sys
from dataclasses import asdict
from pathlib import Path

import anthropic

import settings
import translator


class Api:
    """Methods called from JavaScript as window.pywebview.api.<name>(...)."""

    def __init__(self, settings_path: Path, client_factory=anthropic.Anthropic,
                 translate_fn=translator.translate):
        self._path = Path(settings_path)
        self._client_factory = client_factory
        self._translate_fn = translate_fn
        self._settings = settings.load(self._path)
        self._client = None
        if self._settings["api_key"]:
            self._client = client_factory(api_key=self._settings["api_key"])

    def get_state(self) -> dict:
        return {"has_key": self._client is not None, "direction": self._settings["direction"]}

    def save_key(self, key: str) -> dict:
        key = (key or "").strip()
        if not key:
            return {"ok": False}
        self._settings["api_key"] = key
        settings.save(self._path, self._settings)
        self._client = self._client_factory(api_key=key)
        return {"ok": True}

    def set_direction(self, direction: str) -> None:
        if direction in settings.VALID_DIRECTIONS:
            self._settings["direction"] = direction
            settings.save(self._path, self._settings)

    def translate(self, direction: str, text: str) -> dict:
        if self._client is None:
            return {"ok": False, "error": "no_key"}
        try:
            result = self._translate_fn(self._client, direction, text)
        except translator.TranslateError as e:
            return {"ok": False, "error": e.kind}
        except Exception:
            return {"ok": False, "error": "other"}
        return {"ok": True, "result": asdict(result)}


def main() -> None:
    import webview

    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    webview.create_window("Serbian Translator", url=str(base / "ui" / "index.html"),
                          js_api=Api(settings.default_path()),
                          width=500, height=600, resizable=True)
    webview.start()


if __name__ == "__main__":
    main()
