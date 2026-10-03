"""Prompt files with front matter and versions, and the style guards on
what the model writes back: the scrub that keeps quotes and dashes out
of every summary, and the script check that catches a model slipping
into another writing system mid-word."""

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"
# The model's refusal sentinel: the fetched page was not the article.
NO_ARTICLE = "NO_ARTICLE"

_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True)
class Prompt:
    id: str
    version: int
    text: str


@cache
def load_prompt(name: str, directory: Path = PROMPTS_DIR) -> Prompt:
    raw = (directory / f"{name}.md").read_text()
    match = _FRONT_MATTER.match(raw)
    if match is None:
        raise ValueError(f"prompt {name} has no front matter")
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return Prompt(
        id=meta.get("id", name),
        version=int(meta.get("version", "1")),
        text=" ".join(raw[match.end() :].split()),
    )


def system_prompt() -> str:
    return load_prompt("summary").text


def prompt_version() -> int:
    return load_prompt("summary").version


# The model is told to avoid these, but style rules leak: scrub so no
# summary ever ships with quotes or dashes.
_SCRUB = {"—": ",", "–": ",", "--": ",", "“": "", "”": "", '"': ""}


def scrub_piece(text: str) -> str:
    """`scrub_style` for one streamed piece: the same character swaps, but
    no trimming, as the whitespace at a chunk boundary is part of the
    prose."""
    for old, new in _SCRUB.items():
        text = text.replace(old, new)
    return text


def scrub_style(text: str) -> str:
    for bad, good in _SCRUB.items():
        text = text.replace(bad, good)
    return " ".join(text.split())


# Scripts a summary must never slip into. English output is Latin, so
# anything from these blocks is the model leaving the language
# mid-sentence, except where the scraped page carried the same characters
# (a name in its own script), which is excused token by token below.
_FOREIGN_SCRIPT_RE = re.compile("[Ѐ-ӿͰ-Ͽ؀-ۿݐ-ݿ֐-׿ऀ-ॿঀ-৿฀-๿぀-ヿ㐀-䶿一-鿿가-힯]")
_FUSED_SCRIPT_RE = re.compile(
    "[A-Za-zÀ-ɏ][Ѐ-ӿͰ-Ͽ؀-ۿ"
    "ݐ-ݿ֐-׿ऀ-ॿঀ-৿"
    "฀-๿぀-ヿ㐀-䶿一-鿿"
    "가-힯]"
    "|[Ѐ-ӿͰ-Ͽ؀-ۿݐ-ݿ"
    "֐-׿ऀ-ॿঀ-৿฀-๿"
    "぀-ヿ㐀-䶿一-鿿가-힯]"
    "[A-Za-zÀ-ɏ]"
)


def script_mismatch(text: str, source: str = "") -> bool:
    """True when *text* carries non-Latin characters the scraped page did
    not. A foreign character fused straight into a Latin word is the model
    slipping mid-word, but brand names genuinely fuse scripts, so a fused
    token copied verbatim out of the source is left alone. The source is a
    scraped page whose nav and footer junk carries stray foreign
    characters, so a bare presence match is not enough on its own: only the
    fused check is decisive."""
    foreign = set(_FOREIGN_SCRIPT_RE.findall(text))
    if not foreign:
        return False
    for match in _FUSED_SCRIPT_RE.finditer(text):
        start, end = match.start(), match.end()
        while start > 0 and not text[start - 1].isspace():
            start -= 1
        while end < len(text) and not text[end].isspace():
            end += 1
        token = text[start:end].strip(".,;:!?()[]«»\"'。、，；：？！《》「」")
        if token and token in source:
            continue
        return True
    return not foreign <= set(_FOREIGN_SCRIPT_RE.findall(source))
