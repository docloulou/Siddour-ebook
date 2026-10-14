"""Outils sur le texte hébreu de Sefaria : nikoud, balises <small>/<big>, recherche."""
from __future__ import annotations

import html
import re
import unicodedata

NIKUD_RE = re.compile(r"[֑-ׇ]")
HE_RE = re.compile(r"[א-ת]")
TAG_RE = re.compile(r"<(/?)(\w+)[^>]*>")


def plain_hebrew(text: str) -> str:
    """Forme sans nikoud ni ponctuation finale : sert de clé aux traductions."""
    t = NIKUD_RE.sub("", unicodedata.normalize("NFC", text)).replace("״", '"').replace("׳", "'")
    return re.sub(r"\s+", " ", t).strip(" :.,;")


def is_vocalized(word: str) -> bool:
    return bool(re.search(r"[ְ-ׇֻ]", word))


def parse_paragraph(raw: str) -> tuple[str, list[tuple[str, bool]]]:
    """Retourne (type, segments) ; type = 'heading' | 'note' | 'text'.

    Chaque segment est (texte, est_en_petits_caractères).
    """
    raw = re.sub(r"<br\s*/?>", " ", raw, flags=re.I)
    raw = re.sub(r"\{[פס]\}", "", raw)  # marqueurs de paracha du Tanakh
    segments: list[tuple[str, bool]] = []
    depth = 0
    pos = 0
    for match in TAG_RE.finditer(raw):
        chunk = raw[pos:match.start()]
        if chunk:
            segments.append((html.unescape(chunk), depth > 0))
        closing, tag = match.group(1), match.group(2).lower()
        if tag == "small":
            depth = max(0, depth + (-1 if closing else 1))
        pos = match.end()
    if raw[pos:]:
        segments.append((html.unescape(raw[pos:]), depth > 0))
    segments = [(re.sub(r"\s+", " ", s), n) for s, n in segments if s.strip()]
    if re.fullmatch(r"<big>.*</big>", raw.strip(), re.S) and "<small>" not in raw:
        return "heading", segments
    if segments and all(n for _, n in segments):
        return "note", segments
    return "text", segments


def clean_markup(raw: str) -> str:
    _, segs = parse_paragraph(raw)
    return " ".join(s.strip() for s, _ in segs)


def outer_units(raw: str) -> list[tuple[str, str]]:
    """Découpe en ('main', texte) / ('small', texte), y compris <small> imbriqués."""
    result = []
    depth = 0
    start = 0
    capture = None
    for match in TAG_RE.finditer(raw):
        closing, tag = match.group(1), match.group(2).lower()
        if tag != "small":
            continue
        if not closing:
            if depth == 0:
                if raw[start:match.start()].strip():
                    result.append(("main", clean_markup(raw[start:match.start()])))
                capture = match.start()
            depth += 1
        else:
            depth = max(0, depth - 1)
            if depth == 0 and capture is not None:
                result.append(("small", clean_markup(raw[capture:match.end()])))
                start = match.end()
                capture = None
    if capture is not None:
        result.append(("small", clean_markup(raw[capture:])))
    elif raw[start:].strip():
        result.append(("main", clean_markup(raw[start:])))
    return [(k, t) for k, t in result if t.strip()]


def find_hebrew(text: str, target: str):
    """Localise une formule dans le texte vocalisé sans retirer ses nikoud."""
    pattern = "".join(r"\s+" if c == " " else re.escape(c) + r"[֑-ׇ]*" for c in target)
    return re.search(pattern, text)
