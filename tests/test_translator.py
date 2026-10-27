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
    d.update(over)
    return d


def test_valid_answer_parses():
    r = parse_result(valid(), "tr-sr")
    assert r == Result("knjiga", "noun, f.", ["sveska"],
                       [Example("Čitam **knjigu**.", "Kitap okuyorum."),
                        Example("Ova **knjiga** je moja.", "Bu kitap benim."),
                        Example("Kupio sam **knjigu**.", "Bir kitap aldım.")])


@pytest.mark.parametrize("field", ["translation", "examples", "alternatives"])
def test_missing_field_rejected(field):
    d = valid()
    del d[field]
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


import anthropic
import httpx2 as httpx  # anthropic 2.x ships its HTTP layer as httpx2
from types import SimpleNamespace
from translator import translate, TranslateError, MODEL, TOOL_NAME


class FakeClient:
    def __init__(self, tool_input=None, exc=None):
        self.calls, self._input, self._exc = [], tool_input, exc
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        if self._exc:
            raise self._exc
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
