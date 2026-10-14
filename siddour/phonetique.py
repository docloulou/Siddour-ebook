"""Translittération séfarade selon des conventions françaises.

Heuristique : elle reste une aide de lecture, pas une édition savante.
Les cas particuliers se corrigent dans PH_WORDS.
"""
from __future__ import annotations

import re
import unicodedata

from .hebreu import is_vocalized, plain_hebrew

SHEVA, HATAF_SEGOL, HATAF_PATAH, HATAF_QAMATS = "ְ", "ֱ", "ֲ", "ֳ"
HIRIQ, TSERE, SEGOL, PATAH, QAMATS = "ִ", "ֵ", "ֶ", "ַ", "ָ"
HOLAM, HOLAM_HASER, QUBUTS, DAGESH = "ֹ", "ֺ", "ֻ", "ּ"
SHIN_DOT, SIN_DOT, QAMATS_QATAN, MAQAF = "ׁ", "ׂ", "ׇ", "־"

VOWELS = {
    PATAH: "a", QAMATS: "a", HATAF_PATAH: "a", HATAF_QAMATS: "o",
    TSERE: "é", SEGOL: "è", HATAF_SEGOL: "è",
    HIRIQ: "i", HOLAM: "o", HOLAM_HASER: "o", QUBUTS: "ou", QAMATS_QATAN: "o",
}
SHEVA_NA = "e"

CONSONANTS = {
    "א": "", "ג": "g", "ד": "d", "ה": "h", "ז": "z", "ח": "'h", "ט": "t",
    "י": "y", "ל": "l", "מ": "m", "ם": "m", "נ": "n", "ן": "n", "ס": "s",
    "ע": "'", "צ": "ts", "ץ": "ts", "ק": "k", "ר": "r", "ת": "t", "ו": "v",
}
SOFT_HARD = {"ב": ("v", "b"), "כ": ("kh", "k"), "ך": ("kh", "k"),
             "פ": ("f", "p"), "ף": ("f", "p")}

# Mots au cas particulier (forme consonantique -> phonétique)
EXCEPTIONS = {
    "יהוה": "Adonaï", "יי": "Adonaï", "ה'": "Hachem",
    "כל": None,  # traité plus bas (kol / kal)
}
CANTILLATION = re.compile(r"[֑-ֽֿׅ֯ׄ]")
HEB_LETTER = re.compile(r"[א-ת]")


def _split_letters(word: str) -> list[tuple[str, set[str]]]:
    letters: list[tuple[str, set[str]]] = []
    for ch in word:
        if HEB_LETTER.match(ch):
            letters.append((ch, set()))
        elif letters and "ְ" <= ch <= "ׇ":
            letters[-1][1].add(ch)
    return letters


def _vowel_of(marks: set[str]) -> str | None:
    for m in (PATAH, QAMATS, HATAF_PATAH, HATAF_QAMATS, TSERE, SEGOL, HATAF_SEGOL,
              HIRIQ, HOLAM, HOLAM_HASER, QUBUTS, QAMATS_QATAN, SHEVA):
        if m in marks:
            return m
    return None


def _translit_word_base(word: str) -> str:
    consonants_only = "".join(c for c in word if HEB_LETTER.match(c) or c == "'")
    if consonants_only in ("יהוה", "יי", "ה'"):
        return EXCEPTIONS[consonants_only]
    letters = _split_letters(word)
    if not letters:
        return word
    if consonants_only == "כל" and QAMATS in letters[0][1]:
        return "kol"

    out: list[str] = []
    n = len(letters)
    prev_vowel: str | None = None  # dernière voyelle prononcée
    for i, (ch, marks) in enumerate(letters):
        v = _vowel_of(marks)
        last = i == n - 1
        nxt = letters[i + 1] if i + 1 < n else None

        # --- vav : holam malé (וֹ) ou chourouk (וּ)
        if ch == "ו" and v in (HOLAM, HOLAM_HASER) and i > 0 and _vowel_of(letters[i - 1][1]) is None:
            out.append("o"); prev_vowel = HOLAM; continue
        if ch == "ו" and DAGESH in marks and v is None and (i == 0 or _vowel_of(letters[i - 1][1]) is None):
            out.append("ou"); prev_vowel = QUBUTS; continue

        # --- yod mater lectionis
        if ch == "י" and v is None and DAGESH not in marks and i > 0:
            if prev_vowel in (HIRIQ, TSERE, SEGOL):
                continue  # ִי / ֵי / ֶי : yod muet
            if prev_vowel in (PATAH, QAMATS):
                if nxt and nxt[0] == "ו" and i + 1 == n - 1:
                    continue  # ָיו -> "av"
                if last:
                    out.append("ï"); continue

        # --- lettres muettes en fin de mot
        if last and v is None and ch in "אה" and not (ch == "ה" and DAGESH in marks):
            continue
        if last and v is None and ch == "ע":
            continue

        # --- consonne
        if ch in SOFT_HARD:
            soft, hard = SOFT_HARD[ch]
            cons = hard if DAGESH in marks else soft
        elif ch == "ש":
            cons = "s" if SIN_DOT in marks else "ch"
        else:
            cons = CONSONANTS.get(ch, ch)
        if ch == "ע" and i == 0:
            cons = ""

        # --- patah furtif (רוּחַ -> roua'h)
        if last and v == PATAH and ch in "חע" or (last and v == PATAH and ch == "ה" and DAGESH in marks):
            out.append("a" + cons); prev_vowel = PATAH; continue

        # --- voyelle
        if v == SHEVA:
            prev_marks = letters[i - 1][1] if i > 0 else set()
            na = (i == 0
                  or (i == 1 and out and out[0] == "ou")
                  or (SHEVA in prev_marks and not last)
                  or (DAGESH in marks and i > 0 and not last)
                  or (nxt is not None and nxt[0] == ch))
            vow = SHEVA_NA if (na and not last) else ""
        elif v is not None:
            vow = VOWELS[v]
        else:
            vow = ""
        out.append(cons + vow)
        if v is not None and v != SHEVA:
            prev_vowel = v
        elif vow:
            prev_vowel = SHEVA

    word_out = "".join(out).replace("''", "'")
    # כָּל / בְּכָל / וּבְכָל : kamats katan -> "kol"
    if len(letters) >= 2 and letters[-1][0] == "ל" and _vowel_of(letters[-1][1]) is None \
            and letters[-2][0] == "כ" and QAMATS in letters[-2][1]:
        word_out = re.sub(r"(k|kh)al$", r"\1ol", word_out)
    return word_out


# Mots non vocalisés ou mal rendus par les règles générales.
PH_WORDS = {
    'הוא': 'hou', 'כחו': 'ko’ho', 'ששי': 'chichi', 'אכלתי': 'akhalti',
    'חוס': '’hous', 'שום': 'choum', 'ונשוב': 'venachouv', 'שבות': 'chevout',
    'מיורדי': 'miyoredé', 'וצירם': 'vetsiram', 'קום': 'koum', 'הושר': 'hochar',
    "ה'": 'Hachem', 'יו"ד': 'youd', 'יהוה': 'Adonaï', 'יי': 'Adonaï',
}
# Préfixes devant le Tétragramme (le, ve, mi, ka, ché, oumé…) : le Nom se lit
# toujours Adonaï, le préfixe gardant la voyelle de cette lecture (כַּיהוָה kaAdonaï).
_NAME_PREFIX = re.compile(r'[ובכלמשד]{1,3}')


def translit_word(word: str) -> str:
    key = plain_hebrew(word)
    if key in PH_WORDS and not is_vocalized(word):
        return PH_WORDS[key]
    letters = _split_letters(word)
    cons = ''.join(ch for ch, _ in letters)
    if cons.endswith('יהוה') and len(cons) > 4 and _NAME_PREFIX.fullmatch(cons[:-4]):
        positions = [i for i, ch in enumerate(word) if HEB_LETTER.match(ch)]
        return _translit_word_base(word[:positions[-4]]) + 'Adonaï'
    return _translit_word_base(word)


def translit(text: str, capitalize: bool = True) -> str:
    text = unicodedata.normalize("NFC", text)
    text = CANTILLATION.sub("", text)
    text = text.replace(MAQAF, "-").replace("׃", ".").replace("׀", "")
    parts = re.split(r"([א-תְ-ׇ']+)", text)
    res = []
    for p in parts:
        if p and HEB_LETTER.search(p):
            res.append(translit_word(p))
        else:
            res.append(p)
    s = "".join(res)
    s = re.sub(r"\s+([,.:;])", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    if capitalize and s:
        s = s[:1].upper() + s[1:]
    return s.replace('״', '"').replace('׳', "'").replace('‍', '')
