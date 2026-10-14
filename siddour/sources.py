"""Récupération des textes Sefaria, avec cache local pour travailler hors ligne.

L'API refuse une partie entière d'un livre « complexe » comme le Siddur Ashkenaz :
ses prières sont alors téléchargées une à une, d'après l'index du livre, et le
cache garde la section réunie sous la forme {"parties": [...]}.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from .hebreu import HE_RE, is_vocalized, loose
from .plan import BOOK
from .plan_ashkenaze import BOOK as BOOK_ASHKENAZE

API = "https://www.sefaria.org/api/v3/texts/{ref}"
INDEX_API = "https://www.sefaria.org/api/v2/raw/index/{book}"
HEADERS = {"User-Agent": "siddour-ebook (usage personnel)"}
_INDEX: dict[str, list[dict]] = {}


def cache_path(cache_dir: Path, key: str) -> Path:
    name = re.sub(r"[^\w]+", "_", key).strip("_")
    if len(name) > 150:  # sections réunies : nom trop long pour certains systèmes
        name = name[:120] + "_" + hashlib.sha1(name.encode()).hexdigest()[:10]
    return cache_dir / (name + ".json")


def _get(url: str, **params) -> dict:
    import requests

    r = requests.get(url, params=params, timeout=30, headers=HEADERS)
    r.raise_for_status()
    time.sleep(0.5)  # rester poli avec l'API
    return r.json()


def leaves(book: str) -> list[dict]:
    """Prières (feuilles) du livre, dans l'ordre : {"ref", "title", "heTitle"}."""
    if book not in _INDEX:
        schema = _get(INDEX_API.format(book=book.replace(" ", "_")))["schema"]

        def title(node, lang):
            return next((t["text"] for t in node.get("titles", []) if t.get("lang") == lang and t.get("primary")),
                        node.get("key", ""))

        found: list[dict] = []

        def walk(node, path):
            if node.get("nodes"):
                for child in node["nodes"]:
                    walk(child, path + [title(child, "en")])
            else:
                found.append({"ref": ", ".join(path), "title": title(node, "en"), "heTitle": title(node, "he")})

        walk(schema, [book])
        _INDEX[book] = found
    return _INDEX[book]


def fetch_leaves(full_refs: list[str], book: str) -> dict:
    """Réunit les prières d'une ou plusieurs parties du livre ; les prières vides sont omises."""
    import requests

    parties = []
    for full_ref in full_refs:
        selected = [leaf for leaf in leaves(book) if leaf["ref"] == full_ref or leaf["ref"].startswith(full_ref + ", ")]
        if not selected:
            raise ValueError(f"partie introuvable dans l'index : {full_ref}")
        for leaf in selected:
            try:
                data = _get(API.format(ref=leaf["ref"].replace(" ", "_")), version="hebrew")
            except requests.HTTPError as exc:  # prière sans aucun texte dans Sefaria
                if exc.response is not None and exc.response.status_code == 404:
                    continue
                raise
            v = (data.get("versions") or [{}])[0]
            if not v.get("text"):
                continue
            parties.append(dict(leaf, **{k: v.get(k, "") for k in ("versionTitle", "license", "versionSource",
                                                                     "language")}, text=v["text"]))
    return {"book": book, "indexTitle": book, "ref": " + ".join(full_refs), "parties": parties}


def fetch_section(ref: str, cache_dir: Path, offline: bool, book: str = BOOK) -> dict:
    version = "hebrew"
    other_book = ref.startswith("@")
    if other_book:
        ref, _, v = ref[1:].partition("|")
        full_ref = ref
        version = v or version
    else:
        full_ref = f"{book}, {ref}"
    key = full_ref + ("" if version == "hebrew" else f"__{version}")
    cache_file = cache_path(cache_dir, key)
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    if offline:
        raise FileNotFoundError(f"Pas en cache : {full_ref}")
    full_refs = [f"{book}, {part.strip()}" for part in ref.split(" + ")]
    if not other_book and book != BOOK and (
            len(full_refs) > 1 or not any(leaf["ref"] == full_ref for leaf in leaves(book))):
        data = fetch_leaves(full_refs, book)
        if not data["parties"]:
            raise ValueError(f"texte vide pour {full_ref}")
    else:
        data = _get(API.format(ref=full_ref.replace(" ", "_")), version=version)
        if not (data.get("versions") or [{}])[0].get("text"):
            raise ValueError(f"texte vide pour {full_ref} ({version})")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


# Corrections ponctuelles du texte source, par section : (motif, remplacement).
_YOM_TOV = (loose('ביום') + r' <small><small>(ביום טוב[^<]*)</small> (' + loose('טוב') + r')</small> ('
            + loose('מקרא') + ' ' + loose('קדש') + ' ' + loose('הזה') + r'\.?)')
_YOM_TOV_FIX = r'<small><small>\1</small> בְּיוֹם \2 \3</small>'
# Oubli de « טל ומטר » : les incipits cités dans la consigne étaient vocalisés.
_TAL_OUMATAR = ('<small>אם שכח לומר ' + loose('טל') + ' ' + loose('ומטר') + ' [^<]*</small>',
                '<small>אם שכח לומר טל ומטר ונזכר קודם שהתחיל תקע אומרו במקום שנזכר. התחיל לומר תקע יאמרנה '
                'בשומע תפלה. ואם לא נזכר בש"ת יאמרנה בין ש"ת לרצה. שכח גם שם אם נזכר קודם שעקר רגליו חוזר '
                'לברכת השנים ויתחיל ברך עלינו ויתפלל כסדר. ואם עקר רגליו חוזר לראש התפלה.</small>')

SOURCE_FIXES = {
    # Lettre parasite à la fin de l'invitation au zimoun.
    'Fast Days and Mourning, Mourning': [('(' + loose('קדישא') + ':)צ', r'\1')],
    # « בְּיוֹם » appartient à l'ajout de Yom tov : à 'Hol hamoèd, on s'arrête avant.
    'Post Meal Blessing': [(_YOM_TOV, _YOM_TOV_FIX)],
    'Al Hamihya': [(_YOM_TOV, _YOM_TOV_FIX)],
    # Consigne de lecture : « אלהיכם » se lie à « אמת » ; les deux mots cités étaient vocalisés.
    'Weekday, Shacharit, Blessings of the Shema': [('<small>יש לצרף [^<]*</small>', '<small>יש לצרף אלהיכם לאמת</small>')],
    'Weekday, Maariv, Blessings of the Shema': [('<small>יש לצרף [^<]*</small>', '<small>יש לצרף אלהיכם לאמת</small>')],
    'Weekday, Shacharit, Amidah': [_TAL_OUMATAR],
    'Weekday, Minchah, Amida': [_TAL_OUMATAR],
    'Weekday, Maariv, Amidah': [_TAL_OUMATAR],
    # Titre de la seconde seli'ha, sur quatre lignes.
    'Festivals, Selichot, Fast of Gedalia': [('^סליחות לימי התשובה<br>.*<br>סליחה ב$', '<big>סליחה ב</big>')],
    # Textes à réciter que Daat donne sans voyelles.
    'Shabbat, Havdalah': [('^כן תהיה לנו:$', 'כֵּן תִּהְיֶה לָּנוּ:')],
    # Mesure de la 'halla : l'équivalent en grammes manque, il ne reste que l'unité.
    'Berachot, Birkhot Hamitzvot': [('<small> ?גרם</small> ?', '')],
    'Berachot, Asher Yatzar Etchem Badin': [(
        '^ברוך אתה יי .*מחיה המתים\\.$',
        'בָּרוּךְ אַתָּה יְיָ אֱלֹהֵינוּ מֶלֶךְ הָעוֹלָם, אֲשֶׁר יָצַר אֶתְכֶם בַּדִּין, וְזָן וְכִלְכֵּל אֶתְכֶם בַּדִּין, '
        'וְהֵמִית אֶתְכֶם בַּדִּין, וְיוֹדֵעַ מִסְפַּר כֻּלְּכֶם בַּדִּין, וְהוּא עָתִיד לְהַחֲיוֹתְכֶם וּלְקַיֵּם אֶתְכֶם '
        'בַּדִּין. בָּרוּךְ אַתָּה יְיָ, מְחַיֵּה הַמֵּתִים.')],
}


def apply_fixes(ref: str, texts: list[str]) -> list[str]:
    for pattern, repl in SOURCE_FIXES.get(ref, []):
        texts = [re.sub(pattern, repl, t) for t in texts]
    return texts


def flatten(text) -> list[str]:
    if isinstance(text, str):
        return [text]
    out: list[str] = []
    for t in text or []:
        out.extend(flatten(t))
    return out


# Siddur Ashkenaz : écritures propres à ses deux sources (Metsudah et Daat).
_REFERENCE_START = None


def _is_reference(text: str) -> bool:
    global _REFERENCE_START
    if _REFERENCE_START is None:
        from .consignes import REFERENCE_BOOKS
        _REFERENCE_START = re.compile(r"(?:" + "|".join(map(re.escape, [*REFERENCE_BOOKS, "שם"])) + r")\s")
    return bool(_REFERENCE_START.match(text.strip()))


def _variante(m: re.Match) -> str:
    """« <small>(בעשרת ימי תשובה: הַשָּׁלוֹם)</small> » : condition, puis texte vocalisé.
    La forme du livre séfarade, « (<small>condition</small> texte) », est reprise.
    Daat écrit aussi la variante en italique, sans parenthèses."""
    words = m[1].split()
    k = next((k for k, w in enumerate(words) if is_vocalized(w)), len(words))
    if 0 < k < len(words) and sum(map(is_vocalized, words[k:])) * 2 >= len(words) - k:
        return "(<small>" + " ".join(words[:k]).rstrip(":") + "</small> " + " ".join(words[k:]) + ")"
    return m[0]


def normalize_ashkenaze(texts: list[str]) -> list[str]:
    out = []
    for t in texts:
        t = re.sub(r"(?<=[\u05d0-\u05ea\u0591-\u05c7])\u2011(?=[\u05d0-\u05ea])", "", t)  # יְ‑יָ
        # Les <b> n'ont pas de sens ici ; chaque balise couperait le mot en deux.
        t = re.sub(r"</?b>", "", t)
        t = re.sub(r"<big>([\u05d0-\u05ea][\u0591-\u05c7]*)</big>", r"\1", t)  # lettre agrandie
        # Référence biblique de Daat : « <em><small>תהלים קמה</small></em> ».
        t = re.sub(r"<em><small>([^<>]*)</small></em>",
                   lambda m: "<small>(" + m[1].strip() + ")</small>" if _is_reference(m[1]) else _variante(m), t)
        t = re.sub(r"<small>\(([^()<>]+)\)</small>", _variante, t)
        # « ג"פ » précède ici le verset à répéter ; le livre séfarade le met après.
        t = re.sub(r'<small>ג"פ:?</small>\s*([^<]+?:)(?=\s|$)', r'\1 <small>ג"פ</small>', t)
        if t.strip():
            out.append(t)
    return out


# Dans l'Amida, les prières ne prennent pas d'intertitre : seules la Kedoucha et
# la bénédiction des Cohanim, propres à la répétition, sont repérées et encadrées.
AMIDA_MARKERS = {"Kedushah": "קדושה", "Keduasha": "קדושה", "Birkat Kohanim": "ברכת כהנים"}
AMIDA_RE = re.compile(r"(?<!Post )\bAmidah?\b|Mussaf|Musaf")


def versions_of(data: dict) -> list[tuple[str, dict]]:
    """(livre, version) de chaque texte d'une section, pour les crédits."""
    book = data.get("indexTitle") or data.get("book") or BOOK
    if "parties" in data:
        return [(book, p) for p in data["parties"]]
    return [(book, (data.get("versions") or [{}])[0])]


def assemble(data: dict, ref: str) -> tuple[dict, list[str]]:
    """Section réunie : un intertitre par prière et les bornes de chacune."""
    texts: list[str] = []
    bornes = []
    parties = data["parties"]
    amida = AMIDA_RE.search(ref)
    for p in parties:
        if p.get("language") not in {"he", "hebrew"}:
            raise ValueError("Version non hébraïque : " + p["ref"])
        body = normalize_ashkenaze(flatten(p["text"]))
        if not body:
            continue
        start = len(texts)
        if len(parties) > 1:
            if not amida:
                texts.append("<big>" + p["heTitle"] + "</big>")
            elif p["title"] in AMIDA_MARKERS:
                texts.append("<small>" + AMIDA_MARKERS[p["title"]] + "</small>")
        texts.extend(body)
        bornes.append((start, len(texts), p["title"]))
    return {"language": "he", "bornes": bornes}, texts


def validate_source(data: dict, ref: str) -> tuple[dict, list[str]]:
    if "parties" in data:
        v, texts = assemble(data, ref)
    else:
        versions = data.get("versions") or []
        if not versions:
            raise ValueError("Aucune version : " + ref)
        v = versions[0]
        if v.get("language") not in {"he", "hebrew"}:
            raise ValueError("Version non hébraïque : " + ref)
        texts = flatten(v.get("text"))
        if (data.get("indexTitle") or data.get("book")) == BOOK_ASHKENAZE:
            texts = normalize_ashkenaze(texts)
    texts = apply_fixes(ref, texts)
    if not any(HE_RE.search(t) for t in texts):
        raise ValueError("Texte hébreu vide : " + ref)
    return v, texts
