"""Asks Claude for a translation and checks the answer. Knows nothing about the window."""
from dataclasses import dataclass

MODEL = "claude-haiku-5-5"

DIRECTIONS = {
    "tr-sr": ("Turkish", "Serbian"),
    "en-sr": ("English", "Serbian"),
    "sr-en": ("Serbian", "English"),
    "sr-tr": ("Serbian", "Turkish"),
}

_CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ђ": "đ", "е": "e", "ж": "ž",
    "з": "z", "и": "i", "ј": "j", "к": "k", "л": "l", "љ": "lj", "м": "m", "н": "n",
    "њ": "nj", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "ћ": "ć", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "č", "џ": "dž", "ш": "š",
}
_CYR_TO_LAT.update({c.upper(): l.capitalize() for c, l in list(_CYR_TO_LAT.items())})


@dataclass
class Example:
    serbian: str
    other: str


@dataclass
class Result:
    translation: str
    grammar: str | None
    alternatives: list[str]
    examples: list[Example]


class BadAnswer(Exception):
    pass


def to_latin(text: str) -> str:
    return "".join(_CYR_TO_LAT.get(ch, ch) for ch in text)


def _text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BadAnswer(f"{field} must be a non-empty string")
    return value.strip()


def parse_result(tool_input: dict, direction: str) -> Result:
    if direction not in DIRECTIONS:
        raise ValueError(f"unknown direction: {direction}")
    if not isinstance(tool_input, dict):
        raise BadAnswer("answer is not an object")
    to_serbian = DIRECTIONS[direction][1] == "Serbian"

    translation = _text(tool_input.get("translation"), "translation")

    grammar = tool_input.get("grammar")
    if grammar is not None and not isinstance(grammar, str):
        raise BadAnswer("grammar must be a string")
    grammar = (grammar or "").strip() or None

    alternatives = tool_input.get("alternatives")
    if not isinstance(alternatives, list) or not all(isinstance(a, str) for a in alternatives):
        raise BadAnswer("alternatives must be a list of strings")
    alternatives = [a.strip() for a in alternatives if a.strip()][:2]

    raw_examples = tool_input.get("examples")
    if not isinstance(raw_examples, list) or len(raw_examples) != 3:
        raise BadAnswer("examples must be a list of exactly 3")
    examples = []
    for ex in raw_examples:
        if not isinstance(ex, dict):
            raise BadAnswer("each example must be an object")
        examples.append(Example(to_latin(_text(ex.get("serbian"), "serbian")),
                                _text(ex.get("other"), "other")))

    if to_serbian:
        translation = to_latin(translation)
        alternatives = [to_latin(a) for a in alternatives]
    return Result(translation, grammar, alternatives, examples)
