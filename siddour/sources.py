"""Récupération des textes Sefaria, avec cache local pour travailler hors ligne."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .hebreu import HE_RE
from .plan import BOOK

API = "https://www.sefaria.org/api/v3/texts/{ref}"


def fetch_section(ref: str, cache_dir: Path, offline: bool) -> dict:
    version = "hebrew"
    if ref.startswith("@"):
        ref, _, v = ref[1:].partition("|")
        full_ref = ref
        version = v or version
    else:
        full_ref = f"{BOOK}, {ref}"
    key = full_ref + ("" if version == "hebrew" else f"__{version}")
    cache_file = cache_dir / (re.sub(r"[^\w]+", "_", key).strip("_") + ".json")
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    if offline:
        raise FileNotFoundError(f"Pas en cache : {full_ref}")
    import requests

    url = API.format(ref=full_ref.replace(" ", "_"))
    r = requests.get(url, params={"version": version}, timeout=30,
                     headers={"User-Agent": "siddour-ebook (usage personnel)"})
    r.raise_for_status()
    data = r.json()
    if not (data.get("versions") or [{}])[0].get("text"):
        raise ValueError(f"texte vide pour {full_ref} ({version})")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    time.sleep(0.5)  # rester poli avec l'API
    return data


def flatten(text) -> list[str]:
    if isinstance(text, str):
        return [text]
    out: list[str] = []
    for t in text or []:
        out.extend(flatten(t))
    return out


def validate_source(data: dict, ref: str) -> tuple[dict, list[str]]:
    versions = data.get("versions") or []
    if not versions:
        raise ValueError("Aucune version : " + ref)
    v = versions[0]
    if v.get("language") not in {"he", "hebrew"}:
        raise ValueError("Version non hébraïque : " + ref)
    texts = flatten(v.get("text"))
    if not any(HE_RE.search(t) for t in texts):
        raise ValueError("Texte hébreu vide : " + ref)
    return v, texts
