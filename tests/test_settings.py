import json
from settings import load, save, DEFAULTS


def test_missing_file_gives_defaults(tmp_path):
    assert load(tmp_path / "s.json") == DEFAULTS


def test_corrupt_file_gives_defaults(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{not json", encoding="utf-8")
    assert load(p) == DEFAULTS


def test_non_dict_json_gives_defaults(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("[1, 2]", encoding="utf-8")
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
