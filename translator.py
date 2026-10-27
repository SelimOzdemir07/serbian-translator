"""Asks Claude for a translation and checks the answer. Knows nothing about the window."""
from dataclasses import dataclass

import anthropic

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
    grammar = to_latin((grammar or "").strip()) or None

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


TOOL_NAME = "give_translation"

TOOL = {
    "name": TOOL_NAME,
    "description": "Return the translation, grammar hint, alternatives and example sentences.",
    "input_schema": {
        "type": "object",
        "properties": {
            "translation": {"type": "string"},
            "grammar": {"type": "string"},
            "alternatives": {"type": "array", "items": {"type": "string"}, "maxItems": 2},
            "examples": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {"serbian": {"type": "string"}, "other": {"type": "string"}},
                    "required": ["serbian", "other"],
                },
            },
        },
        "required": ["translation", "grammar", "alternatives", "examples"],
    },
}

SYSTEM_PROMPT = """You are a concise {src}→{tgt} dictionary for a learner.
Translate the user's word or short phrase from {src} to {tgt} and answer only by calling the give_translation tool.
Always write Serbian in Latin script, never Cyrillic. Serbian input may be written in Latin or Cyrillic.
translation: the most common translation.
grammar: for a single word, a short hint like "noun, f." or "verb, imperfective"; empty string for phrases.
alternatives: up to 2 other common translations, or an empty list.
examples: exactly 3 short, natural Serbian sentences using the translation, with the Serbian word wrapped in **double asterisks**; "other" is each sentence translated into {other}."""


class TranslateError(Exception):
    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


def translate(client, direction: str, text: str) -> Result:
    if direction not in DIRECTIONS:
        raise ValueError(f"unknown direction: {direction}")
    text = text.strip()
    if not text:
        raise ValueError("text is empty")
    src, tgt = DIRECTIONS[direction]
    other = tgt if src == "Serbian" else src
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=600,
            timeout=15,
            system=SYSTEM_PROMPT.format(src=src, tgt=tgt, other=other),
            tools=[TOOL],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[{"role": "user", "content": text}],
        )
    except anthropic.AuthenticationError as e:
        raise TranslateError("auth") from e
    except anthropic.APITimeoutError as e:
        raise TranslateError("timeout") from e
    except anthropic.APIConnectionError as e:
        raise TranslateError("network") from e
    except anthropic.APIError as e:
        raise TranslateError("other") from e

    block = next((b for b in response.content if getattr(b, "type", None) == "tool_use"), None)
    if block is None:
        raise TranslateError("bad_answer")
    try:
        return parse_result(block.input, direction)
    except BadAnswer as e:
        raise TranslateError("bad_answer") from e
