"""Consignes françaises : chargement des traductions et découpage des petits caractères.

Les traductions vivent dans data/consignes.csv (rubriques) et data/intertitres.csv
(titres internes). La clé est l'hébreu sans nikoud ; voir hebreu.plain_hebrew.
data/consignes_locales.csv précise une consigne dont le sens dépend du passage
(section Sefaria et numéro de paragraphe).
"""
from __future__ import annotations

import csv
import html
import re
import unicodedata
from pathlib import Path

from .hebreu import HE_RE, is_vocalized, plain_hebrew
from .phonetique import PH_WORDS, translit

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

MISSING_RUBRIC = "[Consigne à traduire]"
MISSING_REFERENCE = "[Référence à traduire]"

REFERENCE_BOOKS = {
    'דברי הימים': 'Chroniques', 'שיר השירים': 'Cantique des cantiques', 'תהילים': 'Psaumes',
    'תהלים': 'Psaumes', 'בראשית': 'Genèse', 'שמות': 'Exode', 'ויקרא': 'Lévitique',
    'במדבר': 'Nombres', 'דברים': 'Deutéronome', 'ישעיהו': 'Isaïe', 'ישעיה': 'Isaïe',
    'ירמיהו': 'Jérémie', 'ירמיה': 'Jérémie', 'משלי': 'Proverbes', 'חבקוק': 'Habacuc',
    'נחמיה': 'Néhémie', 'איוב': 'Job', 'הושע': 'Osée', 'זכריה': 'Zacharie',
    'עובדיה': 'Abdias', 'דניאל': 'Daniel', 'מיכה': 'Michée',
}
REFERENCE_RE = re.compile(r'\((?:' + '|'.join(re.escape(k) for k in sorted(REFERENCE_BOOKS, key=len, reverse=True))
                          + r')\s+[^)]*\)')
NUMBER_VALUES = dict(zip('אבגדהוזחטיכלמנסעפצקרשת',
                         [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400]))

# Cas particulier : la consigne de la bénédiction des Cohanim contient l'appel
# « Cohanim », vocalisé, que l'officiant prononce : il reste un texte à réciter.
_KOHANIM_CALL = 'קורא להם החזן'
_KOHANIM_KEY = 'בחזרת הש"ץ אומרים ברכת כהנים, אם יש יותר מכהן אחד קורא להם החזן: כהנים: הכהנים מברכים'


def rubric_key(text: str) -> str:
    return re.sub(r'\s+([),.;:])', r'\1', plain_hebrew(text))


def whole_psalm(key: str, french: str) -> str:
    """« (תהילים ק"ב:א'-ב') » : Sefaria cite les premiers versets d'un psaume
    récité en entier ; seul le numéro du psaume est utile au lecteur."""
    if re.fullmatch(r"\([^()]*:א'-[^()]*\)", key):
        return re.sub(r', 1–\d+\.\)$', '.)', french)
    return french


def read_table(path: Path) -> list[dict]:
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter=';'))


class Consignes:
    """Table des traductions, avec relevé des consignes manquantes et utilisées."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.rows = read_table(data_dir / 'consignes.csv')
        self.translations = {r['hebreu']: r['francais'] for r in self.rows}
        self.headings = {r['hebreu']: r['francais'] for r in read_table(data_dir / 'intertitres.csv')}
        self.local = {(r['section'], int(r['paragraphe']), rubric_key(r['hebreu'])): r['francais']
                      for r in read_table(data_dir / 'consignes_locales.csv')}
        self.missing: set[str] = set()
        # (section, paragraphe, clé) : sert à compter les occurrences réelles.
        self.where: tuple = ()
        self.seen: set[tuple] = set()
        self._lookup: dict[str, tuple[str, str]] | None = None

    def load_overrides(self, path: str | None) -> None:
        """Applique un CSV de corrections (colonnes hebreu;francais)."""
        if not path:
            return
        for row in read_table(Path(path)):
            he, fr = (row.get('hebreu') or '').strip(), (row.get('francais') or '').strip()
            if he and fr:
                if HE_RE.search(fr):
                    raise ValueError('Une traduction française contient encore de l’hébreu : ' + he)
                self.translations[plain_hebrew(he)] = fr
        self._lookup = None

    def _table(self) -> dict[str, tuple[str, str]]:
        if self._lookup is None:
            self._lookup = {rubric_key(k): (k, v) for k, v in self.translations.items()}
        return self._lookup

    def _get(self, key: str) -> str | None:
        local = self.local.get(self.where[:2] + (key,))
        if local is not None:
            return local
        found = self._table().get(key)
        if found is None:
            return None
        self.seen.add(self.where + (found[0],))
        return found[1]

    def is_instruction(self, text: str) -> bool:
        """Consigne connue, non vocalisée, bien que la source ne l'ait pas mise en petits caractères."""
        words = text.split()
        return (bool(words) and sum(is_vocalized(w) for w in words) / len(words) < .15
                and rubric_key(text) in self._table())

    def heading(self, plain: str) -> str:
        if plain in self.headings:
            return self.headings[plain]
        return plain if not HE_RE.search(plain) else self.instruction(plain)

    def instruction(self, text: str) -> str:
        key = rubric_key(text)
        if not HE_RE.search(key):
            return text.strip()
        found = self._get(key)
        if found is not None:
            return whole_psalm(key, found)
        # Les balises <b> de la source séparent parfois une consigne de sa citation.
        citations = re.findall(r'\([^()]*\)', key)
        base = re.sub(r'\([^()]*\)', '', key).strip()
        table = self._table()
        if base in table and citations and all(c in table for c in citations):
            return self._get(base) + ' ' + ' '.join(self._get(c) for c in citations)
        self.missing.add(key)
        return MISSING_RUBRIC

    def split(self, text: str) -> list[tuple[str, str]]:
        """Sépare les consignes (à traduire) et les prières vocalisées d'un passage en petits caractères.

        Les indications non vocalisées sont traduites ; les textes liturgiques restent
        des prières, même s'ils étaient balisés <small> dans la source.
        """
        key = plain_hebrew(text)
        if _KOHANIM_CALL in key:
            word = next((w for w in text.split() if plain_hebrew(w).strip(':') == 'כהנים' and is_vocalized(w)), None)
            if word:
                head, tail = text.split(word, 1)
                if rubric_key(text) == _KOHANIM_KEY:
                    return [('instruction', 'Pendant la répétition de l’Amida, s’il y a plusieurs Cohanim, '
                                            'l’officiant les appelle :'),
                            ('prayer', word), ('instruction', 'Les Cohanim récitent la bénédiction :')]
                tail = tail.strip().lstrip(':').strip()
                return ([('instruction', self.instruction(head + ' כהנים')), ('prayer', word)]
                        + (self.split(tail) if HE_RE.search(tail) else []))
        # Le passage de Maïmonide est vocalisé dans la source et se lit avec la
        # prière qui suit : seule la mention de la source est une consigne.
        if key.startswith('פרוש (הרמב'):
            end = text.find(')')
            if end > 0:
                description = self.translations[key].split(') : ')[0] + ') :'
                self.seen.add(self.where + (key,))
                return [('instruction', description)] + self.split(text[end + 1:])
        # Référence biblique seule : elle accompagne le verset, comme au fil du texte.
        if REFERENCE_RE.fullmatch(text.strip()) and rubric_key(text) not in self._table():
            return [('prayer', text.strip())]
        words = re.findall(r'\S+', unicodedata.normalize('NFC', text))
        if not words:
            return []
        ratio = sum(is_vocalized(w) for w in words) / len(words)
        if ratio < .15:
            return [('instruction', self.instruction(text))]
        result: list[tuple[str, str]] = []
        i = 0
        while i < len(words):
            vocal = is_vocalized(words[i])
            j = i + 1
            while j < len(words) and is_vocalized(words[j]) == vocal:
                j += 1
            chunk = ' '.join(words[i:j])
            chunk_key = plain_hebrew(chunk)
            if vocal or not HE_RE.search(chunk_key) or chunk_key in PH_WORDS:
                kind, value = 'prayer', chunk
            else:
                kind, value = 'instruction', self.instruction(chunk)
            if result and kind == 'prayer' and result[-1][0] == 'prayer':
                result[-1] = ('prayer', result[-1][1] + ' ' + value)
            else:
                result.append((kind, value))
            i = j
        return result

    # --- Références bibliques entre parenthèses -------------------------------
    def reference(self, text: str) -> str:
        key = plain_hebrew(text)
        return whole_psalm(key, self._reference(key))

    def _reference(self, key: str) -> str:
        if key in self.translations:
            self.seen.add(self.where + (key,))
            return self.translations[key]
        body = re.sub(r'\s*-\s*', '-', key[1:-1].strip())
        # « בשינוי » : verset cité avec des changements ; « חצי ראשון » : sa première moitié.
        changed = re.search(r',?\s*(?:עם\s+|ב)שינוי$', body)
        body = body[:changed.start()] if changed else body
        half = re.search(r'\s+חצי ראשון,?$', body)
        body = body[:half.start()] if half else body
        for he, fr in sorted(REFERENCE_BOOKS.items(), key=lambda x: -len(x[0])):
            if body.startswith(he + ' '):
                values = re.split(r'[ :,]+', body[len(he):].strip())
                if fr == 'Chroniques':
                    fr = ('I' if values.pop(0).startswith('א') else 'II') + ' ' + fr
                converted = ['–'.join(str(sum(NUMBER_VALUES.get(c, 0) for c in part)) for part in value.split('-'))
                             for value in values]
                return ('(' + ('D’après ' if changed else '') + fr + ' ' + ', '.join(converted)
                        + (', première moitié' if half else '') + '.)')
        self.missing.add('Référence : ' + key)
        return MISSING_REFERENCE

    def recitation_html(self, value: str, phonetic: bool = False, capitalize: bool = True) -> str:
        """Texte à réciter (hébreu ou phonétique), références bibliques traduites."""
        parts = []
        pos = 0
        for match in REFERENCE_RE.finditer(value):
            text = value[pos:match.start()]
            parts.append(html.escape(translit(text, capitalize=capitalize and pos == 0) if phonetic else text))
            parts.append('<span class="reference" lang="fr" dir="ltr">' + html.escape(self.reference(match.group())) + '</span>')
            pos = match.end()
        text = value[pos:]
        parts.append(html.escape(translit(text, capitalize=capitalize and pos == 0) if phonetic else text))
        return ' '.join(p for p in parts if p)

    def export(self, path: Path) -> None:
        """Écrit le CSV éditable des consignes, avec le nombre d'utilisations."""
        with Path(path).open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['hebreu', 'francais', 'occurrences', 'type'])
            counts: dict[str, int] = {}
            for *_, key in self.seen:
                counts[key] = counts.get(key, 0) + 1
            for row in self.rows:
                he = row['hebreu']
                writer.writerow([he, self.translations.get(he, row['francais']), counts.get(he, 0), row['type']])
