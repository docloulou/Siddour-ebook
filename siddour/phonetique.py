"""Translittération de l'hébreu en lettres latines, selon des conventions françaises.

Deux prononciations, choisies par rite (Rite.prononciation) :

* « sefarade » suit les siddourim Pata'h Eliyahou et Beit Hassofer : ḥ pour ח,
  ‘ pour ע, w pour ו, q pour ק, è pour le tséré et é pour le ségol, consonne
  doublée au daguech fort, chva prononcé après une voyelle longue, Adonaïe,
  finales du Pata'h Eliyahou (netilate, zemane, haarétss) ;
* « israelienne » suit la prononciation israélienne courante : ’h, ’, v, k,
  é pour le tséré et è pour le ségol, sans gémination, mots liés par un trait
  d'union au maqaf.

Dans les deux, l'aleph prononcé après une consonne s'écrit ’ (mal’akh) et le
qamats d'un mot lié par un maqaf se lit « o » (וּגְדָל־חָסֶד ougdol). Le méteg de la
source marque surtout l'accent : il ne rend pas un chva sonore, et le dernier
d'un verset cantillé est le silouq.

Chaque mot est d'abord analysé en sons (consonnes et voyelles), puis écrit selon
la prononciation. Le résultat reste une aide de lecture : un mot que les règles
rendent mal se corrige dans PH_WORDS ou LECTURES (mot non vocalisé) ou dans
CORRECTIONS (vocalisation fautive de la source). INCONNUS compte les mots restés
sans lecture ; tests/test_phonetique.py fixe les lectures attendues.
"""
from __future__ import annotations

import collections
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

from .hebreu import plain_hebrew

SHEVA, HATAF_SEGOL, HATAF_PATAH, HATAF_QAMATS = "ְ", "ֱ", "ֲ", "ֳ"
HIRIQ, TSERE, SEGOL, PATAH, QAMATS = "ִ", "ֵ", "ֶ", "ַ", "ָ"
HOLAM, HOLAM_HASER, QUBUTS, DAGESH, METEG = "ֹ", "ֺ", "ֻ", "ּ", "ֽ"
MAQAF, SHIN_DOT, SIN_DOT, QAMATS_QATAN = "־", "ׁ", "ׂ", "ׇ"

COURTES = (PATAH, SEGOL, HIRIQ, QUBUTS, QAMATS_QATAN)
LONGUES = (QAMATS, TSERE, HOLAM, HOLAM_HASER)
FINALES = str.maketrans("ךםןףץ", "כמנפצ")

# Clé de son des voyelles : e = tséré, E = ségol, ei = tséré suivi d'un yod, @ = chva prononcé.
VOYELLES = {
    PATAH: "a", QAMATS: "a", HATAF_PATAH: "a",
    HOLAM: "o", HOLAM_HASER: "o", QAMATS_QATAN: "o", HATAF_QAMATS: "o",
    TSERE: "e", SEGOL: "E", HATAF_SEGOL: "E", HIRIQ: "i", QUBUTS: "u",
}
CONSONNES = {
    "א": None, "ב": "v", "ג": "g", "ד": "d", "ה": "h", "ו": "w", "ז": "z", "ח": "ḥ", "ט": "t",
    "י": "y", "כ": "kh", "ך": "kh", "ל": "l", "מ": "m", "ם": "m", "נ": "n", "ן": "n", "ס": "s",
    "ע": "ʿ", "פ": "f", "ף": "f", "צ": "ts", "ץ": "ts", "ק": "q", "ר": "r", "ת": "t",
}
DURES = {"ב": "b", "כ": "k", "ך": "k", "פ": "p", "ף": "p"}  # avec daguech

CANTILLATION = re.compile(r"[֑-ֿׅ֯ׄ]")  # le méteg (ֽ) sert à l'analyse
ACCENTS = re.compile(r"[֑-֯]")
# Dans un texte cantillé, le dernier « méteg » du mot qui clôt le verset est le silouq,
# accent tonique et non méteg : וְשָׂבָֽעְתָּ׃ se lit wessava‘ta.
SILOUQ = re.compile(r"([^\s׃:]*)ֽ([^\sֽ׃:]*\s*[׃:])")
HEB_LETTER = re.compile(r"[א-ת]")
# Caractères invisibles de la source (ZWJ, marques de direction) : ils couperaient les mots.
INVISIBLES = re.compile("[\u00ad\u034f\u200b-\u200f\u2060\ufeff]")
GUILLEMETS = re.compile("(?<=[א-תְ-ׇ])[”“](?=[א-ת])")  # יוֹ”ד : guerchayim typographiques
MOTS = re.compile(r"([א-תְ-ׇ']+(?:[\"״][א-תְ-ׇ']+)*)")
# Ketiv non vocalisé à côté du qeré vocalisé entre crochets (הביט [הַבִּיטָה]) :
# on ne lit que le qeré.
KETIV_QERE = re.compile(r"(?<![א-תְ-ׇ'\"״׳])[א-ת]+\s*\[([^\]]*[ְ-ׇ][^\]]*)\]"
                        r"|\[([^\]]*[ְ-ׇ][^\]]*)\]\s*[א-ת]+(?![א-תְ-ׇ'\"״׳])")
# Ketiv entre parenthèses devant le qeré, de même initiale : קוּמִי (לכי) לָךְ.
KETIV_PARENTHESES = re.compile(r"\(([א-ת]+)\)\s*(?=([א-ת])[ְ-ׇ])")
NUMERO = re.compile(r"^(\s*)\(([א-צ]{1,2})\)")  # (א) … (י) en tête : énumération, lue (1) … (10)
UNITES, DIZAINES = "אבגדהוזחט", "יכלמנסעפצ"

# Noms divins entourés de ces marqueurs quand translit(noms=True) : voir noms_html.
NOM_DEBUT, NOM_FIN = "\x0e", "\x0f"
LIEN = "\x1f"  # maqaf, jusqu'à l'écriture du texte
POINTS = re.compile(r"[\u05b0-\u05bc\u05c1\u05c2\u05c7]")
INCONNUS: collections.Counter = collections.Counter()  # mots sans lecture fiable -> occurrences


@dataclass(frozen=True)
class Prononciation:
    nom: str
    graphies: dict = field(compare=False)  # clé de son -> graphie, quand elles diffèrent
    nom_divin: str          # lecture du Tétragramme
    yod_final: str          # yod consonne en fin de mot (ḥaïe)
    ayin_aux_bords: bool    # ע écrit en début et en fin de mot
    gemination: bool        # consonne doublée au daguech fort
    chva_long: bool         # chva prononcé après une voyelle longue
    usages_pe: bool         # graphies du Pata'h Eliyahou : Yissraèl, éte-khém, -te, -ne, -che…


_GRAPHIES = {"u": "ou", "@": "e"}
PRONONCIATIONS = {p.nom: p for p in (
    Prononciation("sefarade", {**_GRAPHIES, "e": "è", "E": "é", "ei": "ei", "ʿ": "‘"},
                  nom_divin="Adonaïe", yod_final="ïe", ayin_aux_bords=True,
                  gemination=True, chva_long=True, usages_pe=True),
    Prononciation("israelienne", {**_GRAPHIES, "e": "é", "E": "è", "ei": "é", "ʿ": "’",
                                  "ḥ": "’h", "w": "v", "q": "k"},
                  nom_divin="Adonaï", yod_final="ï", ayin_aux_bords=False,
                  gemination=False, chva_long=False, usages_pe=False),
)}


@dataclass
class Son:
    voyelle: bool
    cle: str
    i: int                  # indice de la lettre d'origine
    double: bool = False    # daguech fort : consonne doublée
    y_simple: bool = False  # yod au daguech, même omis (וַיְהִי) : toujours « y »
    coupure: bool = False   # suivie de « e- » (éte-khém)


# Qamats qatan que la source ne distingue pas du qamats : racines (lettre au
# qamats, lettre au chva, lettre suivante) et formes relevées dans le corpus.
QATAN_RACINES = ("קדש", "חכמ", "אזנ", "שרש", "חפנ", "ערפ", "צרכ", "קרט", "חלי", "עני", "רהב", "מתנ", "גבה", "כתל")
QATAN_MOTS = frozenset(unicodedata.normalize("NFC", w) for w in (
    "זָכְרֵנוּ", "וְזָכְרֵנוּ", "בְּזָכְרֵנוּ", "כָּתְבֵנוּ", "וְכָתְבֵנוּ", "פָּקְדֵנוּ", "פָקְדֵנוּ", "וּפָקְדֵנוּ",
    "שָׁמְרֵנִי", "שָׁמְרָה", "שָׁמְרֵם", "חָנֵּנִי", "וְחָנֵּנִי", "חָנֵּנוּ", "וְחָנֵּנוּ", "קָרְאֵנוּ", "בְּקָרְאֵנוּ",
    "וּלְעָבְדוֹ", "וּלְעָבְדָךְ", "וּלְעָבְדְךָ", "וּלְעָבְדְּךָ", "לְעָבְדוֹ", "לְעָבְדְךָ",
    "וּבְשָׁכְבְּךָ", "בְּשָׁכְבֵנוּ", "בְּשָׁכְבְּךָ", "מָרְדְּכַי", "לְמָרְדְּכַי", "וּמָרְדְּכַי", "בְּמָרְדְּכַי",
    "קָרְבַּן", "קָרְבְּנוֹת", "הַקָּרְבָּנוֹת", "חָרְבַּן", "חָרְבָּן", "אָכְלָם", "בְּאָכְלָם", "יִשְׁמָרְךָ", "לִשְׁמָרְךָ",
    "גָּדְלְךָ", "גָּדְלֶךָ", "רָגְזֶךָ", "יָשְׁרֵנוּ", "נַעֲבָדְךָ", "לְנָכְרִים", "נָכְרִים", "לְעָשְׁקָם",
    "בְּאָמְרָם", "כְּשָׁמְעוֹ", "חָדְשֵׁיכֶם", "בְּחָדְשׁוֹ", "לְחָדְשֵׁי", "הָבְקְעָה", "וְהָבְקְעָה", "בְעָזְּךָ",
    "אֶזְכָּרְךָ", "יִגְמָלְךָ", "עָרְבֵנִי",
))
ARAMEEN_NAH = ("עלמ", "עסק", "פסק")  # עָלְמָא, דְּעָסְקִין : chva muet malgré le qamats

# Vocalisation fautive de la source (forme sans méteg) -> forme lue.
CORRECTIONS = {unicodedata.normalize("NFC", k): v for k, v in {
    "וְיָשם": "וְיָשֵׂם",              # bénédiction des Cohanim
    "וְיִתְנַשּא": "וְיִתְנַשֵּׂא",    # Kaddich
    "לְששון": "לְשָׂשׂוֹן",
    "וְלַעֲשות": "וְלַעֲשׂוֹת",
    "שונֵא": "שׂוֹנֵא",
    "שֶׁעָשֹה": "שֶׁעָשָׂה",
    "עֲשה": "עֲשֵׂה",                  # עֲשֵׂה לְמַעַן שְׁמֶךָ
    # Lettre sans voyelle ou point déplacé (relevés dans les deux éditions).
    "צוָחָה": "צְוָחָה", "רוָחָה": "רְוָחָה", "דבָרוֹ": "דְּבָרוֹ", "נדָבָה": "נְדָבָה",
    "ימֵי": "יְמֵי", "ימַלֵּא": "יְמַלֵּא", "יקַדְּמוּ": "יְקַדְּמוּ", "לכָל": "לְכָל",
    "הַמּלָכִים": "הַמְּלָכִים", "בְּצּד": "בְּצַד",
    "שׁכֹּחוֹ": "שֶׁכֹּחוֹ", "הַחדֶשׁ": "הַחֹדֶשׁ", "קרבֵנו": "קׇרְבֵנוּ",
    "וְעִשרון": "וְעִשָּׂרוֹן", "לַכֶּבֶש": "לַכֶּבֶשׂ", "יְראוּ": "יִרְאוּ", "עמָּהֶם": "עִמָּהֶם",
    "כּל": "כֹּל", "ראשׁ": "רֹאשׁ", "עׂז": "עֹז",
}.items()}

# Mots non vocalisés et sigles de la prière : forme vocalisée (analysée comme le reste
# du texte) ou phonétique. Un sigle s'y lit même partiellement vocalisé (בְּו"ה).
PH_WORDS = {k: unicodedata.normalize("NFC", v) for k, v in {
    "ה'": "יְהוָה", "יהוה": "יְהוָה", "יי": "יְיָ",
    'יו"ד': "יוֹד", 'י"ה': "יוֹד קֵא", 'בו"ה': "בְּוָו קֵא",  # לְיַחֵד שֵׁם י"ה בו"ה
    'לר"ח': "לְרֹאשׁ חֹדֶשׁ",
    'פב"פ': "untel fils d’untel", "פלוני": "untel",  # nom à dire
    "הוא": "הוּא", "כחו": "כֹּחוֹ", "ששי": "שִׁשִּׁי", "אכלתי": "אָכַלְתִּי",
    "חוס": "חוּס", "שום": "שׁוּם", "ונשוב": "וְנָשׁוּב", "שבות": "שְׁבוּת",
    "מיורדי": "מִיּוֹרְדֵי", "וצירם": "וְצִירָם", "קום": "קוּם", "הושר": "הוּשַׁר",
}.items()}
# Mots courants que la source laisse sans points au milieu d'une prière (le siddour
# ashkénaze perd le holam : יום, לא). À la différence de PH_WORDS, ils ne font pas
# d'une consigne en petits caractères (« ואומר: ») un texte à réciter.
LECTURES = {k: unicodedata.normalize("NFC", v) for k, v in {
    "יום": "יוֹם", "לא": "לֹא", "ראש": "רֹאשׁ", "אותו": "אוֹתוֹ", "אמן": "אָמֵן", "ואומר": "וְאוֹמֵר",
    "אתה": "אַתָּה", "בריך": "בְּרִיךְ", "שים": "שִׂים", "עשה": "עֹשֶׂה", "כל": "כָּל", "דכל": "דְּכָל",
}.items()}

# Tétragramme, précédé au plus de trois préfixes : il se lit Adonaï (Elohim s'il est
# vocalisé יֱהֹוִה) et le préfixe prend la voyelle de cette lecture (לַיהוָה laAdonaïe).
TETRAGRAMME = re.compile(r"([ובכלמשד]{0,3})(יהוה|יי|ה')")
NOMS_DIVINS = re.compile(r"אלוה|אלהא|אל(?:ו)?הי(?:ם|נו|ך|כם|כן|הם|ו|ה)?")
PREFIXES_DIVINS = "ובכלמשדה"
# « Dieux » des autres peuples : pas de capitale (אֱלֹהִים אֲחֵרִים).
PROFANES = frozenset("אחרים נכר הנכר העמים מסכה כסף זהב הגוים".split())
PROFANES_EL = frozenset(("לא", "זר", "אחר"))  # אֵל לֹא יוֹשִׁיעַ, אֵל זָר
TOUS = re.compile("[ובלמ]{0,2}כל")  # עַל־כׇּל־אֱלֹהִים : les dieux des nations
NOMS_PROPRES = frozenset(
    "ישראל אברהם יצחק יעקב משה אהרן אהרון ירושלים ירושלם ציון יהודה יוסף אליהו מרדכי אסתר "
    "מצרים סיני פרעה בנימין אפרים מנשה שרה רבקה רחל לאה יהושע שמואל ירמיהו ישעיהו יחזקאל "
    "דניאל נחמיה פנחס פינחס אחשורוש שושן כנען לבנון עמלק שלמה יששכר דוד דויד".split())
PREFIXES_NOMS = "ובכלמש"
# Point exigé (indice dans le nom) pour écarter un homographe : דּוֹד, שְׁלֵמָה, יוֹסִף…
CONTRAINTES = {"דוד": (1, HIRIQ), "שלמה": (1, HOLAM), "יוסף": (2, TSERE), "אסתר": (0, SEGOL),
               "שושן": (1, DAGESH), "מצרים": (0, HIRIQ), "לאה": (0, TSERE), "שרה": (0, QAMATS)}


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


def _squelette(lettres) -> str:
    return "".join(c for c, _ in lettres)


def _porte_vav(lettres, j: int) -> bool:
    """La lettre j est un vav nu, un holam malé ou un chourouk."""
    return j < len(lettres) and lettres[j][0] == "ו" and _vowel_of(lettres[j][1]) in (None, HOLAM, HOLAM_HASER)


def _he_nu(lettre) -> bool:
    return lettre[0] == "ה" and not lettre[1]


# --- Restitution des points perdus par la source ------------------------------
def _voyelle_sin(lettres, i: int) -> str:
    """Voyelle d'un sin dont le point a pris la place (יִשרָאֵל, עָשיתָ)."""
    n = len(lettres)
    suivante = lettres[i + 1]
    pv = _vowel_of(lettres[i - 1][1])
    if suivante[0] == "י" and not suivante[1] and i + 1 < n - 1:
        return HIRIQ
    if i + 1 == n - 1:
        return (QAMATS if pv == QAMATS else SEGOL) if _he_nu(suivante) else QAMATS
    if _vowel_of(suivante[1]) == SHEVA:
        return HIRIQ
    if pv in COURTES:
        return SHEVA
    return QAMATS if pv == SHEVA else SHEVA


def _vav_voyelle(lettres, j: int) -> bool:
    """La lettre j est un holam malé ou un chourouk explicites."""
    if j >= len(lettres) or lettres[j][0] != "ו":
        return False
    m = lettres[j][1]
    return _vowel_of(m) in (HOLAM, HOLAM_HASER) or (DAGESH in m and _vowel_of(m) is None)


def _patah_furtif(lettres) -> None:
    """Pata'h furtif perdu sous le ח ou le ע final, après une voyelle autre que « a »
    (יִפָּתֵחַ, שָׁלִיחַ, לִשְׁלוֹחַ)."""
    n = len(lettres)
    if n < 2 or lettres[-1][0] not in "חע" or _vowel_of(lettres[-1][1]) is not None:
        return
    pch, pm = lettres[-2]
    if pch == "י" and _vowel_of(pm) is None and DAGESH not in pm:
        longue = n > 2 and _vowel_of(lettres[-3][1]) in (HIRIQ, TSERE)
    else:
        longue = _vav_voyelle(lettres, n - 2) or _vowel_of(pm) in (TSERE, HIRIQ, HOLAM, HOLAM_HASER, QUBUTS)
    if longue:
        lettres[-1][1].add(PATAH)


def _restituer(lettres) -> None:
    """Rétablit le point du shin ou du sin, les voyelles perdues et le holam du vav."""
    n = len(lettres)
    if not any(_vowel_of(m) for _, m in lettres):
        return
    _patah_furtif(lettres)
    for i, (ch, m) in enumerate(lettres):
        if ch != "ש" or SHIN_DOT in m or SIN_DOT in m:
            continue
        if HOLAM in m:  # point du sin noté comme un holam
            m.add(SIN_DOT)
            if _vowel_of(m - {HOLAM}) is not None or _porte_vav(lettres, i + 1):
                m.discard(HOLAM)
            elif i + 1 == n - 1 and _he_nu(lettres[i + 1]):
                m.discard(HOLAM)
                m.add(QAMATS if i and QAMATS in lettres[i - 1][1] else SEGOL)
        elif _vowel_of(m) is None and 0 < i < n - 1 and not _porte_vav(lettres, i + 1):
            m.update((SIN_DOT, _voyelle_sin(lettres, i)))
        else:
            m.add(SHIN_DOT)
    for i in range(n - 1):
        ch, m = lettres[i]
        if _vowel_of(m) is not None or ch in "או" or (ch == "י" and i) or _porte_vav(lettres, i + 1):
            continue
        pm = lettres[i - 1][1] if i else set()
        pv = _vowel_of(pm)
        suivante = lettres[i + 1]
        sv = _vowel_of(suivante[1])
        if ch == "ה" and pv == QAMATS:
            continue  # hé muet au milieu d'un nom composé : פְּדָהצוּר
        if METEG in m:
            m.add(HOLAM)
        elif (sv in (HOLAM, HOLAM_HASER) or (sv is None and _vav_voyelle(lettres, i + 2))
              or (i == n - 2 and suivante[0] == "ך" and sv == QAMATS)):
            m.add(SHEVA)  # devant la syllabe du holam ou du chourouk (מְעוֹנָה, יְצַפְצְפוּ) ; טוּבְךָ
        elif i == 0 and ch in "בכל" and n >= 4 and sv not in (HATAF_PATAH, HATAF_SEGOL, HATAF_QAMATS):
            m.add(SHEVA)
        elif pv in COURTES and DAGESH not in m:
            m.add(SHEVA)
        elif METEG in pm and pv not in (None, SHEVA):
            m.add(SHEVA)
        elif suivante[0] == "י" and not suivante[1] and i + 1 < n - 1:
            m.add(HIRIQ)
        elif i + 1 == n - 1 and _he_nu(suivante):
            m.add(SEGOL)
        else:
            m.add(HOLAM)
    for i in range(1, n):  # vav nu après une lettre sans voyelle : holam malé (הָעולָם)
        ch, m = lettres[i]
        if (ch == "ו" and _vowel_of(m) is None and DAGESH not in m and _vowel_of(lettres[i - 1][1]) is None
                and not (i == n - 1 and lettres[i - 1][0] in "יא")  # ָיו, לָאו : « aw »
                and _voyelle_precedente(lettres, i) not in (HOLAM, HOLAM_HASER)):  # חַטֹּאות : holam déjà là
            m.add(HOLAM)


def _qamats_qatan(lettres, forme: str, lie: bool = False) -> None:
    """Change en qamats qatan (« o ») le qamats d'une syllabe fermée non accentuée ;
    lie : mot suivi d'un maqaf, qui perd son accent (וּגְדָל־חָסֶד ougdol)."""
    n = len(lettres)
    premier = forme in QATAN_MOTS  # seul le premier qamats de ces formes est qatan
    for i in range(n - 1):
        ch, m = lettres[i]
        if _vowel_of(m) != QAMATS:
            continue
        suivante = lettres[i + 1]
        if HATAF_QAMATS in suivante[1] and not (i == 0 and ch in "וכ"):
            qatan = True  # צָהֳרַיִם
        elif METEG in m:
            qatan = False
        elif premier:
            qatan = True
        elif _vowel_of(suivante[1]) == SHEVA and i + 2 < n:
            apres = lettres[i + 2]
            qatan = ((ch + suivante[0] + apres[0]).translate(FINALES) in QATAN_RACINES
                     or (apres[0] in "בגדכפ" and DAGESH in apres[1]))  # מָרְדְּכַי, קָרְבַּן
        else:
            qatan = False
        premier = False
        if qatan:
            m.discard(QAMATS)
            m.add(QAMATS_QATAN)
    if n < 2 or _vowel_of(lettres[-1][1]) is not None or _vowel_of(lettres[-2][1]) != QAMATS:
        return
    (avant, m), fin = lettres[-2], lettres[-1][0]
    if (avant, fin) == ("כ", "ל") or (  # כָּל, בְּכָל, וּבְכָל : kol
            lie and fin not in "אהוי" and METEG not in m
            and not (avant == "ש" and SHIN_DOT in m and fin == "ם") and (avant, fin) != ("א", "ז")):
        m.discard(QAMATS)  # שָׁם־ et אָז־ gardent leur qamats
        m.add(QAMATS_QATAN)


def _corriger_noms(lettres) -> int | None:
    """יִשָּׂשכָר (second sin muet), יְרוּשָׁלִַם (yod sous-entendu) : indice du nom, ou None."""
    sq = _squelette(lettres)
    for p in range(min(4, len(sq))):
        if p and sq[p - 1] not in PREFIXES_NOMS:
            return None
        reste = sq[p:]
        if reste == "יששכר":
            del lettres[p + 2]
            return p
        if reste == "ירושלם":
            lamed, mem = lettres[p + 4][1], lettres[p + 5][1]
            if HIRIQ in mem or (HIRIQ in lamed and (PATAH in lamed or QAMATS in lamed)):
                lamed.discard(HIRIQ)
                mem.discard(HIRIQ)
                if _vowel_of(lamed) is None:
                    lamed.add(PATAH)
                lettres.insert(p + 5, ("י", {HIRIQ}))
                return p
    return None


# --- Analyse en sons ----------------------------------------------------------
def _voyelle_precedente(lettres, i: int) -> str | None:
    """Voyelle de la lettre précédente, par-dessus un aleph muet (תִּמָּצֶאינָה)."""
    if i == 0:
        return None
    j = i - 1
    if j > 0 and lettres[j][0] == "א" and _vowel_of(lettres[j][1]) is None:
        j -= 1
    return _vowel_of(lettres[j][1])


def _consonne(ch: str, marks: set[str]) -> str | None:
    if ch == "ש":
        return "s" if SIN_DOT in marks else "ch"
    if DAGESH in marks and ch in DURES:
        return DURES[ch]
    return CONSONNES.get(ch)


def _daguech_omis(lettres, i: int) -> bool:
    """Daguech fort omis sous le chva : וַיְהִי, הַמְבָרֵךְ, הַיְשׁוּעָה."""
    if i == 0 or _vowel_of(lettres[i - 1][1]) != PATAH:
        return False
    ch, avant = lettres[i][0], lettres[i - 1][0]
    if avant == "ו":
        return i == 1 and ch == "י"
    return avant == "ה" and ch in "מי" and all(c in "ושמ" for c, _ in lettres[:i - 1])


def _chva_na(lettres, i: int, profil: Prononciation) -> bool:
    """Le chva de la lettre i (qui n'est pas la dernière) se prononce-t-il ?"""
    if i == 0:
        return True
    ch, m = lettres[i]
    pch, pm = lettres[i - 1]
    suivante = lettres[i + 1]
    # Le méteg de la source marque surtout l'accent (בָּגַֽדְנוּ) : il ne rend pas le chva sonore.
    if (SHEVA in pm or DAGESH in m or suivante[0].translate(FINALES) == ch.translate(FINALES)
            or _daguech_omis(lettres, i)):
        return True
    if not profil.chva_long or ch == "י":
        return False
    # Après une voyelle longue, le chva se prononce (lecture séfarade), sauf en fin de
    # mot, devant un daguech doux, une désinence verbale ou dans עָלְמָא.
    pv = _vowel_of(pm)
    longue = (_voyelle_precedente(lettres, i) in LONGUES
              or (pch == "ו" and i > 1 and (DAGESH in pm or pv in (HOLAM, HOLAM_HASER))
                  and pv in (None, HOLAM, HOLAM_HASER))
              or (pch == "י" and pv is None and DAGESH not in pm and i > 1
                  and _vowel_of(lettres[i - 2][1]) in (HIRIQ, TSERE)))
    if not longue:
        return False
    n = len(lettres)
    if i + 1 == n - 1 and (_vowel_of(suivante[1]) == SHEVA or suivante[0] in "אה"):
        return False
    if suivante[0].translate(FINALES) in "בגדכפת" and DAGESH in suivante[1]:
        return False
    if (_squelette(lettres[i + 1:]) in ("נו", "תי", "ת", "תם", "תן")
            and _vowel_of(suivante[1]) in (None, SHEVA, QAMATS, HIRIQ, SEGOL)):
        return False
    return (pch + ch + suivante[0]).translate(FINALES) not in ARAMEEN_NAH


def _sons(lettres, profil: Prononciation, debut: int = 0) -> list[Son]:
    """Sons du mot ; debut : première lettre d'un nom propre, jamais doublée (miMitsraïm)."""
    sons: list[Son] = []
    n = len(lettres)
    for i, (ch, m) in enumerate(lettres):
        v = _vowel_of(m)
        dernier = i == n - 1
        pv = _vowel_of(lettres[i - 1][1]) if i else None
        if ch == "ו":
            if v in (HOLAM, HOLAM_HASER) and i and pv is None:
                sons.append(Son(True, "o", i))
                continue
            if DAGESH in m and v is None and (i == 0 or pv is None):
                sons.append(Son(True, "u", i))
                continue
            if v is None and DAGESH not in m and i and _voyelle_precedente(lettres, i) in (HOLAM, HOLAM_HASER):
                continue  # holam posé sur la lettre précédente, au besoin par-dessus l'aleph (חַטֹּאות)
        if ch == "י" and v is None and DAGESH not in m and i:
            pv_imm = _voyelle_precedente(lettres, i)
            if pv_imm in (HIRIQ, SEGOL, HATAF_SEGOL):
                continue
            if pv_imm == TSERE:
                if sons and sons[-1].voyelle and sons[-1].cle == "e":
                    sons[-1].cle = "ei"
                continue
            if pv_imm in (PATAH, QAMATS) and i == n - 2 and lettres[i + 1][0] == "ו" \
                    and DAGESH not in lettres[i + 1][1] and _vowel_of(lettres[i + 1][1]) is None:
                continue  # ָיו : « aw »
        if ch == "א" and sons and not sons[-1].voyelle and (
                v not in (None, SHEVA) or (v is None and _porte_vav(lettres, i + 1))):
            sons.append(Son(False, "’", i))  # aleph après une consonne : lir’ote, mal’akh
        if v is None and (ch == "א" or (dernier and ch == "ה" and DAGESH not in m)):
            continue
        cons = _consonne(ch, m)
        if dernier and i and v == PATAH and (ch in "חע" or (ch == "ה" and DAGESH in m)):
            sons += [Son(True, "a", i), Son(False, cons, i)]  # pata'h furtif : rouaḥ
            continue
        if cons is not None:
            double = (profil.gemination and DAGESH in m and i not in (0, debut) and ch != "ה"
                      and not (dernier and v in (None, SHEVA)) and bool(sons) and sons[-1].voyelle)
            sons.append(Son(False, cons, i, double=double,
                            y_simple=ch == "י" and (DAGESH in m or _daguech_omis(lettres, i))))
        if v == SHEVA:
            if (n == 1 or not dernier) and _chva_na(lettres, i, profil):  # (וְ) isolé : we
                sons.append(Son(True, "@", i))
        elif v is not None:
            sons.append(Son(True, VOYELLES[v], i))
    return sons


# --- Écriture -----------------------------------------------------------------
def _ecrire(sons: list[Son], profil: Prononciation, nom_son: int | None = None) -> list[str]:
    """Graphie de chaque son ; nom_son : premier son d'un nom propre."""
    g = profil.graphies
    pieces: list[str] = []
    for k, s in enumerate(sons):
        prec = sons[k - 1] if k else None
        suiv = sons[k + 1] if k + 1 < len(sons) else None
        pv = prec.cle if prec is not None and prec.voyelle else None
        c = s.cle
        if s.voyelle:
            if c != "i":
                p = g.get(c, c)
            elif pv is not None:
                p = "-i" if pv in ("e", "E", "ei") else "ï"  # ché-im, raïti
            elif prec is not None and c == "i" and prec.cle == "y" and pieces[-1].endswith("ï"):
                p = ""  # maïm
            else:
                p = "i"
        elif c == "y":
            if s.double:
                p = "y" if pv == "i" else "yy"
            elif s.y_simple or pv is None or pv == "i" or k == nom_son:
                p = "y"
            else:
                p = profil.yod_final if suiv is None else "ï"  # wehaïou, ḥaïe
        elif c == "ʿ":
            if not profil.ayin_aux_bords and (prec is None or suiv is None):
                p = ""
            elif profil.usages_pe and prec is not None and prec.cle == "ch" and pv is None \
                    and not pieces[-1].endswith("-"):
                p = "e-" + g[c]  # ouviche-‘arékha
            else:
                p = g[c]
        elif c == "s":
            entre = pv is not None and suiv is not None and suiv.voyelle
            p = "ss" if s.double or entre or (profil.usages_pe and suiv is None) else "s"
        else:
            p = g.get(c, c)
            if s.double and len(p) == 1:
                p += p
            if c == "g" and suiv is not None and suiv.voyelle and suiv.cle in ("e", "E", "ei", "i", "@"):
                p += "u"
            elif c == "h" and prec is not None and pv is None and pieces[-1][-1:] in ("t", "k", "p", "s") \
                    and not pieces[-1].endswith("ts"):
                p = "-h"  # weït-haddar
        if not s.voyelle and profil.usages_pe:
            if suiv is None:
                if c in ("t", "ch") or (c == "n" and pv in ("a", "o", "i", "e", "E", "ei")) \
                        or (c in ("r", "d", "z") and pv in ("e", "E")):
                    p += "e"  # netilate, zemane, achére, wa‘éde
                elif c == "ts":
                    p += "s"  # haarétss
            elif c == "n" and not s.double and pv in ("a", "o", "i", "ei") and not suiv.voyelle \
                    and suiv.cle not in ("y", "’"):
                p += "e-"  # wechinnane-tam
        if s.coupure:
            p += "e-"
        pieces.append(p)
    return pieces


def _capitale(texte: str, debut: int) -> str:
    for k in range(debut, len(texte)):
        if texte[k].isalpha():
            return texte[:k] + texte[k].upper() + texte[k + 1:]
    return texte


# --- Noms -----------------------------------------------------------------------
def _nom_divin_court(lettres, p: int, reste: str) -> bool:
    m = [mk for _, mk in lettres[p:]]
    if reste == "אלה":
        return DAGESH in m[2]  # אֱלוֹהַּ, et non אֵלֶּה
    if reste in ("אל", "אלי"):  # אֵל, אֵלִי ; pas שְׁאֵל
        return (TSERE in m[0] and (reste == "אל" or HIRIQ in m[1])
                and all(c in "ובכלמה" for c, _ in lettres[:p]))
    if reste == "שדי":
        return PATAH in m[0] and DAGESH in m[1]
    if reste == "יה":
        return QAMATS in m[0] and DAGESH in m[1]
    if reste == "צבאות":
        return p == 0 and SHEVA in m[0]
    if reste == "אדני":
        return QAMATS in m[2]
    return False


def _nom(lettres, profane: bool) -> tuple[int, bool] | None:
    """(indice du nom après ses préfixes, nom divin ?) ou None."""
    sq = _squelette(lettres)
    if not profane:
        for p in range(min(4, len(sq))):
            if p and sq[p - 1] not in PREFIXES_DIVINS:
                break
            if NOMS_DIVINS.fullmatch(sq[p:]) or _nom_divin_court(lettres, p, sq[p:]):
                return p, True
    for p in range(min(4, len(sq))):
        if p and sq[p - 1] not in PREFIXES_NOMS:
            break
        if sq[p:] in NOMS_PROPRES:
            contrainte = CONTRAINTES.get(sq[p:])
            if contrainte is None or contrainte[1] in lettres[p + contrainte[0]][1]:
                return p, False
    return None


def _prefixe(lettres, profil: Prononciation) -> str:
    """Préfixe du Tétragramme, vocalisé pour la lecture Adonaï (laAdonaïe, mèAdonaïe)."""
    lettres = [(c, set(m)) for c, m in lettres]
    for k, (c, m) in enumerate(lettres):
        if _vowel_of(m) not in (None, SHEVA):
            continue
        if k == len(lettres) - 1:
            m.discard(SHEVA)
            m.add(TSERE if c == "מ" else SEGOL if c == "ש" else PATAH)
        elif c == "ו" and DAGESH not in m:
            m.add(DAGESH if lettres[k + 1][0] in "במפ" else SHEVA)
        elif c != "ו":
            m.add(SHEVA)
    return "".join(_ecrire(_sons(lettres, profil), profil))


def _tetragramme(mot: str, profil: Prononciation) -> str | None:
    found = TETRAGRAMME.fullmatch("".join(c for c in mot if HEB_LETTER.match(c) or c == "'"))
    if not found:
        return None
    lettres = _split_letters(mot)
    p = len(found[1])
    if found[2] == "יי" and (_vowel_of(lettres[p][1]) not in (None, SHEVA)
                             or _vowel_of(lettres[p + 1][1]) not in (None, QAMATS)):
        return None
    if found[2] == "יהוה" and HIRIQ in lettres[p + 2][1]:
        # יֱהֹוִה se lit Elohim : לֵיהֹוִה comme לֵאלֹהִים.
        prefixe = [(c, set(m)) for c, m in lettres[:p]]
        if prefixe and _vowel_of(prefixe[-1][1]) in (None, SHEVA):
            prefixe[-1][1].discard(SHEVA)
            prefixe[-1][1].add(TSERE)
        pre = "".join(c + "".join(sorted(m)) for c, m in prefixe)
        return _mot(unicodedata.normalize("NFC", pre + ("אלֹהִים" if p else "אֱלֹהִים")), profil.nom)[0]
    return _prefixe(lettres[:p], profil) + NOM_DEBUT + profil.nom_divin + NOM_FIN


# --- Mot et texte -----------------------------------------------------------------
@lru_cache(maxsize=None)
def _mot(mot: str, prononciation: str = "sefarade", profane: bool = False, lie: bool = False) -> tuple[str, bool]:
    """(phonétique du mot, sans lecture fiable ?) ; lie : mot suivi d'un maqaf."""
    profil = PRONONCIATIONS[prononciation]
    tetra = _tetragramme(mot, profil)
    if tetra is not None:
        return tetra, False
    cle = plain_hebrew(mot)
    if cle not in PH_WORDS and mot.strip("'") != mot and HEB_LETTER.search(mot):
        texte, inconnu = _mot(mot.strip("'"), prononciation, profane, lie)  # guillemets simples
        return "'" * (len(mot) - len(mot.lstrip("'"))) + texte + "'" * (len(mot) - len(mot.rstrip("'"))), inconnu
    if not POINTS.search(mot) or ('"' in cle and cle in PH_WORDS):
        valeur = PH_WORDS.get(cle, LECTURES.get(cle))
        if valeur is not None and not HEB_LETTER.search(valeur):
            return valeur, False
        if valeur is not None:  # יוּד קֵא : plusieurs mots
            parts = valeur.split()
            return " ".join(_mot(v, prononciation, profane, lie and k == len(parts) - 1)[0]
                            for k, v in enumerate(parts)), False
    forme = mot.replace(METEG, "")
    if forme in CORRECTIONS:
        mot = CORRECTIONS[forme]
        forme = mot.replace(METEG, "")
    lettres = _split_letters(mot)
    nom_corrige = _corriger_noms(lettres)
    _restituer(lettres)
    _qamats_qatan(lettres, forme, lie)
    sq = _squelette(lettres)
    if profil.usages_pe and sq in ("את", "ואת") and TSERE in lettres[-2][1]:
        lettres[-2][1].discard(TSERE)  # la particule אֵת se lit éte, comme אֶת
        lettres[-2][1].add(SEGOL)
    nom = (nom_corrige, False) if nom_corrige is not None else _nom(lettres, profane)
    p = nom[0] if nom else 0
    sons = _sons(lettres, profil, debut=p)
    if profil.usages_pe:
        for s in sons:
            if not s.voyelle and nom and sq[p:] == "ישראל" and s.i == p + 1:
                s.double = True  # Yissraèl
            if not s.voyelle and sq in ("אתכם", "ואתכם") and s.i == len(sq) - 3:
                s.coupure = True  # éte-khém
    nom_son = next((k for k, s in enumerate(sons) if s.i >= p), None) if nom else None
    pieces = _ecrire(sons, profil, nom_son)
    texte = "".join(pieces)
    if nom_son is not None:
        if sons[nom_son].i != p and nom_son and sons[nom_son - 1].voyelle:
            nom_son -= 1  # la voyelle du préfixe ouvre le nom : lÈlohim, bIrouchalaïm
        debut = sum(len(x) for x in pieces[:nom_son])
        texte = _capitale(texte, debut)
        if nom[1]:
            texte = texte[:debut] + NOM_DEBUT + texte[debut:] + NOM_FIN
    return texte, not re.search(r"[aeiouéèïAEIOUÉÈÏ]", texte)


def _numero(m: re.Match) -> str:
    for n in range(1, 100):
        d, u = divmod(n, 10)
        forme = {15: "טו", 16: "טז"}.get(n, DIZAINES[d - 1:d] + UNITES[u - 1:u] if u else DIZAINES[d - 1])
        if forme == m[2]:
            return m[1] + "(%d)" % n
    return m[0]


def _ketiv(m: re.Match) -> str:
    garder = m[1][0] != m[2] or m[1] in PH_WORDS or TETRAGRAMME.fullmatch(m[1])
    return m[0] if garder else ""


_DEBUT = re.compile("^([(\"«“‘’'\x0e-]*)(\\w)")
_PHRASE = re.compile("([.!?]\\s+[(\"«“‘’'\x0e-]*)(\\w)")
# Capitale de phrase sur le préfixe d'un nom (BIrouchalaïm) : une seule capitale.
_DEUX_CAPITALES = re.compile("(?<!\\w)([^\\W\\d_])(\x0e?)([^\\W\\d_])(?=[^\\W\\d_])")


def _une_capitale(m: re.Match) -> str:
    return m[1] + m[2] + m[3].lower() if m[1].isupper() and m[3].isupper() else m[0]


def translit(text: str, capitalize: bool = True, prononciation: str = "sefarade", noms: bool = False) -> str:
    """Phonétique d'un texte hébreu ; noms : garder les marqueurs des noms divins."""
    profil = PRONONCIATIONS[prononciation]
    text = GUILLEMETS.sub("״", unicodedata.normalize("NFC", INVISIBLES.sub("", text)))
    if ACCENTS.search(text):
        text = SILOUQ.sub(r"\1\2", text)
    text = CANTILLATION.sub("", text)
    text = text.replace(MAQAF, LIEN).replace("׃", ".").replace("׀", "").replace("׳", "'")
    text = KETIV_QERE.sub(lambda m: m[1] or m[2], text)
    text = KETIV_PARENTHESES.sub(_ketiv, NUMERO.sub(_numero, text))
    parts = MOTS.split(text)
    hebreu = [k for k, part in enumerate(parts) if HEB_LETTER.search(part)]
    cles = [plain_hebrew(parts[k]) for k in hebreu]
    for n, k in enumerate(hebreu):
        suivant = cles[n + 1] if n + 1 < len(cles) else ""
        profane = (suivant in PROFANES or (suivant in PROFANES_EL and cles[n].endswith("אל"))
                   or (n > 0 and TOUS.fullmatch(cles[n - 1]) is not None))
        lie = k + 1 < len(parts) and parts[k + 1].startswith(LIEN)
        texte, inconnu = _mot(parts[k], prononciation, profane, lie)
        if inconnu:
            INCONNUS[cles[n]] += 1
        parts[k] = texte
    s = re.sub(r"[ְ-ׇ]", "", "".join(parts)).replace(LIEN, " " if profil.usages_pe else "-")
    s = re.sub(r"\s+([,.:;])", r"\1", s).replace(":", ".")
    s = re.sub(r"\s+", " ", s).strip()
    s = _PHRASE.sub(lambda m: m[1] + m[2].upper(), s)
    if capitalize:
        s = _DEBUT.sub(lambda m: m[1] + m[2].upper(), s)
    s = _DEUX_CAPITALES.sub(_une_capitale, s)
    if not noms:
        s = s.replace(NOM_DEBUT, "").replace(NOM_FIN, "")
    return s.replace("״", '"')


def non_vocalise(text: str) -> bool:
    """Passage que la source donne sans points (seli'ha du siddour ashkénaze) : la plupart
    de ses mots n'ont pas de lecture, sa phonétique ne serait qu'une suite de consonnes."""
    text = CANTILLATION.sub("", unicodedata.normalize("NFC", INVISIBLES.sub("", text))).replace(MAQAF, " ")
    mots = [m for m in MOTS.findall(text) if HEB_LETTER.search(m)]
    sans = [m for m in mots if not POINTS.search(m) and plain_hebrew(m) not in PH_WORDS
            and plain_hebrew(m) not in LECTURES and not TETRAGRAMME.fullmatch(plain_hebrew(m))]
    return len(sans) >= 3 and 2 * len(sans) >= len(mots)


def translit_word(word: str, prononciation: str = "sefarade") -> str:
    """Phonétique d'un mot isolé."""
    texte = _mot(unicodedata.normalize("NFC", INVISIBLES.sub("", word)), prononciation)[0]
    return texte.replace(NOM_DEBUT, "").replace(NOM_FIN, "")


def noms_html(texte: str) -> str:
    """Marqueurs des noms divins -> <span class="nom">, après l'échappement HTML."""
    return texte.replace(NOM_DEBUT, '<span class="nom">').replace(NOM_FIN, "</span>")
