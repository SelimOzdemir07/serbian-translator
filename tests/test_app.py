from app import Api
from settings import load
from translator import Result, Example, TranslateError

R = Result("knjiga", None, [], [Example("**knjiga**", "kitap")] * 3)


def make(tmp_path, fn=lambda c, d, t: R):
    made = []
    api = Api(tmp_path / "s.json",
              client_factory=lambda api_key: made.append(api_key) or object(),
              translate_fn=fn)
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
    def boom(c, d, t):
        raise TranslateError("network")
    api, _ = make(tmp_path, boom)
    api.save_key("k")
    assert api.translate("tr-sr", "x") == {"ok": False, "error": "network"}


def test_unexpected_exception_is_other(tmp_path):
    def boom(c, d, t):
        raise ValueError("blank")
    api, _ = make(tmp_path, boom)
    api.save_key("k")
    assert api.translate("tr-sr", " ") == {"ok": False, "error": "other"}
