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
