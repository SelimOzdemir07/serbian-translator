"""Reads and writes the app's small settings file (API key and last direction)."""
import json
import os
from pathlib import Path

VALID_DIRECTIONS = ("tr-sr", "en-sr", "sr-en", "sr-tr")
DEFAULTS = {"api_key": None, "direction": "tr-sr"}


def default_path() -> Path:
    return Path(os.environ["APPDATA"]) / "SerbianTranslator" / "settings.json"


def load(path: Path) -> dict:
    result = dict(DEFAULTS)
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return result
    if not isinstance(data, dict):
        return result
    key = data.get("api_key")
    if isinstance(key, str) and key.strip():
        result["api_key"] = key
    if data.get("direction") in VALID_DIRECTIONS:
        result["direction"] = data["direction"]
    return result


def save(path: Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
