"""Mise en page de lecture : relie chaque consigne au passage qu'elle concerne.

Principes, inspirés des siddourim imprimés (Pata'h Eliyahou, Beit Hassofer) :

* une consigne courte est une rubrique en italique, collée au passage qui suit ;
* une variante brève (formule des dix jours de pénitence, forme féminine,
  ajout du Chabbat…) s'insère dans la phrase, entre crochets, au lieu de la couper ;
* « deux fois », « trois fois »… se placent à la fin du passage concerné ;
* les sources (Ben Ich 'Haï, Zohar…) et les explications techniques deviennent
  des notes numérotées, regroupées en fin de section (notes EPUB 3).
"""
from __future__ import annotations

import html
import re

from .consignes import REFERENCE_RE
from .hebreu import HE_RE, clean_markup, find_hebrew, is_vocalized, loose, outer_units, parse_paragraph, plain_hebrew
from .phonetique import translit
from .sources import AMIDA_RE

# Variante insérée dans le texte d'une prière : début, séparateur, fin.
VAR_OPEN, VAR_SEP, VAR_CLOSE = '', '', ''
VAR_RE = re.compile(VAR_OPEN + '(.*?)' + VAR_SEP + '(.*?)' + VAR_CLOSE, re.S)
# Au-delà, une variante est présentée dans un encadré plutôt que dans la phrase.
INLINE_WORDS = 12
INLINE_LABEL = 70

REPETITION_RE = re.compile(r'^\(?(?:Deux fois|Trois fois|Sept fois|Répéter)\.?\)?$')
AFTER_RE = re.compile(r'^(?:Deux fois|Trois fois|Sept fois|Répéter|Fin du|Jusqu’ici|Les auditeurs répondent)')
CITATION_RE = re.compile(r'\s*\(((?:[^()]*§[^()]*)|(?:Zohar|Ibid)[^()]*)\)')
TECHNICAL_RE = re.compile(r'initiales|valeur numérique|acrostiche|permutation|combinaison des Noms|Méditer le Nom', re.I)
CONDITION_RE = re.compile(r'^(?:À |En été|En hiver|Le Chabbat|Un jour|Les jours|Lors |Pendant |S’il |Si |Pour '
                          r'|Certains |Une femme|L’invité|Au repas|Avec |Produit |Le père )')

BRIEF = {
    'Pendant les dix jours de pénitence, dire :': 'Dix jours de pénitence',
    'Le Chabbat, dire :': 'Chabbat', 'Le Chabbat :': 'Chabbat',
    'À ’Hanouka, dire :': '’Hanouka', 'À Pourim, dire :': 'Pourim',
    'À ’Hanouka et Pourim, dire :': '’Hanouka et Pourim',
    'Un jour de fête.': 'Yom tov', 'Dans la soucca.': 'Dans la soucca',
    'À Roch ’Hodech :': 'Roch ’Hodech', 'À Pessa’h :': 'Pessa’h',
    'À Chavouot :': 'Chavouot', 'À Souccot :': 'Souccot',
    'À Roch ’Hodech, les jours de fête et à ’Hol hamoèd, dire :': 'Roch ’Hodech, Yom tov et ’Hol hamoèd',
    'Pendant la répétition de l’Amida, dire :': 'Répétition de l’Amida',
}

VIHI_NOAM_RE = re.compile('ו[֑-ׇ]*י[֑-ׇ]*ה[֑-ׇ]*י[֑-ׇ]*[\\s|׀]+נ[֑-ׇ]*ע[֑-ׇ]*ם')

# Formules remplacées pendant les dix jours de pénitence (ou par une femme).
# « Ken yehi ratson » répondu par l'assemblée, suivi de la suite de l'officiant.
KEN_YEHI_RE = re.compile('(' + loose('כן') + ' ' + loose('יהי') + ' ' + loose('רצון') + r':?)\s+(\S.*)', re.S)
# Ligne de méditation du compte de l'Omer : mot d'Ana bekoa'h, sefira, mot du
# psaume 67 et lettre. Elle ne se dit pas.
SEFIROT = {'חסד': '’Héssed', 'גבורה': 'Guevoura', 'תפארת': 'Tiféret', 'נצח': 'Nétsa’h',
           'הוד': 'Hod', 'יסוד': 'Yessod', 'מלכות': 'Malkhout'}
OMER_KAVANA_RE = re.compile(r'^.+? ({0}) שב({0}) \S+ \S$'.format('|'.join(SEFIROT)))
# Nom de la personne, à insérer dans la prière.
PLACEHOLDER_RE = re.compile(r'^\((?:Untel|Unetelle)\b')
REPLACEMENTS = {'המלך הקדוש': 'האל הקדוש', 'המלך המשפט': 'מלך אוהב צדקה ומשפט', 'השלום': 'שלום'}


def brief(text: str) -> str:
    """Raccourcit uniquement les consignes simples, sans changer leurs conditions."""
    return BRIEF.get(text.strip(), text.strip())


def variant(label: str, text: str) -> str:
    return VAR_OPEN + label.strip().rstrip(' :.') + VAR_SEP + text.strip() + VAR_CLOSE


def is_condition(text: str) -> bool:
    return bool(CONDITION_RE.match(text))


def is_technical(text: str) -> bool:
    return bool(TECHNICAL_RE.search(text))


def merge_prayers(items):
    result = []
    for kind, text in items:
        text = text.strip()
        if not text:
            continue
        if kind == 'prayer' and result and result[-1][0] == 'prayer':
            result[-1] = ('prayer', result[-1][1] + ' ' + text)
        else:
            result.append((kind, text))
    return result


def excerpt(text: str, tail: bool = False) -> str:
    words = VAR_RE.sub(' ', text).strip(' ()').split()
    return translit(' '.join(words[-6:] if tail else words[:6])).strip(' ()')[:100]


def repetition_span(text: str) -> str:
    label = text.strip('().').lower()
    label = 'à répéter' if label == 'répéter' else label
    return ' <span class="repetition" lang="fr" dir="ltr">(' + html.escape(label) + ')</span>'


def split_vihi_noam(text: str) -> list[str]:
    """Vihi noam, à la fin d'un « Lechem yi'houd », est seul répété : on l'isole."""
    found = VIHI_NOAM_RE.search(text)
    if not found or not HE_RE.search(text[:found.start()]):
        return [text]
    return [text[:found.start()], text[found.start():]]


def append_to_last_prayer(parts: list[str], span: str) -> bool:
    """Ajoute « (trois fois) »… à la fin du dernier passage récité déjà mis en page."""
    for k in range(len(parts) - 1, -1, -1):
        s = parts[k]
        done = False
        for cls in ('ph', 'he'):
            start = s.rfind('<p class="' + cls + '"')
            if start >= 0:
                end = s.find('</p>', start)
                s = s[:end] + span + s[end:]
                done = True
        if done:
            parts[k] = s
            return True
    return False


class ReadingLayout:
    def __init__(self, title, paragraphs, mode, ref, consignes, bornes=None):
        self.title, self.mode, self.ref, self.c = title, mode, ref, consignes
        # Section réunie de plusieurs prières : début, fin et titre anglais de chacune.
        self.bornes = {start: end for start, end, _ in bornes or []}
        self.notes: list[list] = []      # [numéro, texte, passage concerné]
        self.pending: list[int] = []     # notes à rattacher au prochain passage récité
        self.carry: list[str] = []       # appels de note sans place propre, posés sur ce passage
        self.is_amida = bool(AMIDA_RE.search(ref))
        self.is_meal = ref == 'Post Meal Blessing'
        self.in_zimoun = False
        self.records = []
        for i, raw in enumerate(paragraphs):
            kind, segs = parse_paragraph(raw)
            text = ' '.join(t for t, _ in segs)
            if kind == 'text' and plain_hebrew(text) in consignes.headings and not is_vocalized(text):
                kind = 'heading'  # titre interne, non vocalisé, que la source n'a pas balisé
            elif kind == 'text' and consignes.is_instruction(text):
                kind, raw = 'note', '<small>' + raw + '</small>'
            self.records.append({'i': i, 'raw': raw, 'kind': kind, 'text': text, 'plain': plain_hebrew(text)})

    # --- Notes numérotées ----------------------------------------------------
    def footnote(self, text: str, target: str = '', anchored: bool = True) -> str:
        """Appel de note. Le passage concerné (target) est rappelé dans la note ;
        sans target, c'est le prochain passage récité, sauf pour une simple source."""
        n = len(self.notes) + 1
        self.notes.append([n, text, excerpt(target, tail=True) if target else ''])
        if not target and anchored:
            self.pending.append(n)
        return ('<a class="note-ref" epub:type="noteref" id="appel-' + str(n) + '" href="#note-' + str(n) + '">'
                + str(n) + '</a>')

    def with_citations(self, text: str) -> str:
        """Texte HTML de la consigne ; ses références de source passent en note."""
        out, pos = [], 0
        for m in CITATION_RE.finditer(text):
            out.append(html.escape(text[pos:m.start()]))
            out.append(self.footnote(m[1].strip().rstrip('.') + '.', anchored=False))
            pos = m.end()
        out.append(html.escape(text[pos:]))
        return ''.join(out).strip()

    # --- Éléments de base ----------------------------------------------------
    def recitation(self, text: str, phonetic: bool) -> str:
        chunks = VAR_RE.split(text)
        out = []
        for k in range(0, len(chunks), 3):
            plain = chunks[k].strip()
            if plain:
                body = self.c.recitation_html(plain, phonetic, capitalize=not out)
                if not out and not body.startswith('<'):
                    first, space, rest = body.partition(' ')
                    body = '<strong>' + first + '</strong>' + space + rest
                out.append(body)
            if k + 2 < len(chunks):
                label, alt = chunks[k + 1], chunks[k + 2]
                if not alt:
                    # Nom à insérer : simple indication entre crochets.
                    out.append('<span class="variante">[<span class="variante-label" lang="fr" dir="ltr">'
                               + html.escape(label) + '</span>]</span>')
                    continue
                value = translit(alt, capitalize=False) if phonetic else alt
                # En hébreu, le deux-points reste hors de l'étiquette française pour
                # se placer entre l'étiquette et le texte dans le sens de lecture.
                out.append('<span class="variante">[<span class="variante-label" lang="fr" dir="ltr">'
                           + html.escape(label) + (' :</span> ' if phonetic else '</span>: ')
                           + html.escape(value) + ']</span>')
        # Pas d'espace entre l'indication d'un nom et la ponctuation qui la suit.
        return re.sub(r'(\]</span>) ([,.:;])', r'\1\2', ' '.join(out))

    def prayer(self, text: str, marker: str = '', suffix: str = '') -> str:
        text = text.strip()
        if not text or not HE_RE.search(text):
            return ''
        for n in self.pending:
            self.notes[n - 1][2] = excerpt(text)
        self.pending = []
        marker = ''.join(self.carry) + marker
        self.carry = []
        marker = '<span class="note-markers" dir="ltr">' + marker + '</span>' if marker else ''
        he = '<p class="he" lang="he" dir="rtl">' + self.recitation(text, False) + marker + suffix + '</p>'
        ph = ('<p class="ph" lang="fr" dir="ltr">' + self.recitation(text, True)
              + (marker if self.mode != 'bilingue' else '') + suffix + '</p>')
        if self.mode == 'hebreu':
            return he
        if self.mode == 'phonetique':
            return ph
        return '<div class="pair">' + he + ph + '</div>'

    def note(self, text: str, after: bool = False) -> str:
        """Rubrique en italique, collée au passage suivant (ou précédent si after)."""
        if not re.search(r'\w', text):
            return ''
        body = self.with_citations(brief(text))
        if not re.search(r'\w', re.sub(r'<[^>]+>', '', body)):
            self.carry.append(body)  # simple référence : appel posé sur le prochain passage
            return ''
        return ('<p class="rubrique ' + ('after' if after else 'before') + '" lang="fr" dir="ltr">'
                + body + '</p>')

    def answer(self, text: str) -> str:
        """Réponse de l'assemblée ; la suite de l'officiant, collée dans la source, est séparée."""
        match = KEN_YEHI_RE.match(text)
        if not match:
            return self.prayer(text)
        return self.prayer(match[1]) + self.note('L’officiant poursuit :') + self.prayer(match[2])

    def kavana(self, text: str, match) -> str:
        label = ('Méditation (ne se dit pas) : ' + SEFIROT[match[1]] + ' de ' + SEFIROT[match[2]] + '.')
        line = ('<p class="he kavana" lang="he" dir="rtl">' + html.escape(text.strip()) + '</p>'
                if self.mode != 'phonetique' else '')
        return '<p class="rubrique after" lang="fr" dir="ltr">' + label + '</p>' + line

    def box(self, body: str, label: str = '', rule: str = '', resume: str = '', css: str = 'addition') -> str:
        head = '<p class="card-head">' + self.with_citations(label) + '</p>' if label else ''
        rule = '<p class="card-rule" lang="fr" dir="ltr">' + rule + '</p>' if rule else ''
        end = '<p class="resume" lang="fr" dir="ltr"><a href="' + html.escape(resume) + '">Suite de la prière</a></p>' if resume else ''
        return '<div class="' + css + '">' + head + rule + body + end + '</div>'

    def block(self, i: int, content: str) -> str:
        return '<div id="p-' + str(i) + '">' + content + '</div>'

    def resume_from(self, index: int) -> str:
        nxt = self.next_prayer(index)
        return '#p-' + str(nxt) if nxt is not None else ''

    # --- Découpage des paragraphes de la source --------------------------------
    def items(self, r):
        self.c.where = (self.ref, r['i'])
        kind, segs = parse_paragraph(r['raw'])
        if kind == 'note':
            return merge_prayers(self.c.split(' '.join(t for t, _ in segs)))
        result = []
        for text, small in segs:
            result.extend(self.c.split(text) if small else [('prayer', text)])
        return merge_prayers(result)

    def next_prayer(self, index: int):
        for r in self.records[index:]:
            if r['kind'] != 'heading' and any(k == 'prayer' and HE_RE.search(t) for k, t in self.items(r)):
                return r['i']
        return None

    def record_body(self, r) -> str:
        return self.block(r['i'], self.paragraph(r))

    def render_sequence(self, items) -> str:
        parts = []
        items = merge_prayers(items)
        for k, (kind, text) in enumerate(items):
            if kind == 'prayer' and k and items[k - 1][1].startswith('On répond'):
                parts.append(self.answer(text))
            elif kind == 'prayer':
                repeated = k + 1 < len(items) and REPETITION_RE.match(items[k + 1][1])
                for piece in (split_vihi_noam(text) if repeated else [text]):
                    parts.append(self.prayer(piece))
            elif REPETITION_RE.match(text) and append_to_last_prayer(parts, repetition_span(text)):
                pass
            else:
                parts.append(self.note(text, after=bool(AFTER_RE.match(text))))
        return ''.join(parts)

    def conditional_items(self, items) -> str:
        # La condition est le seul titre de l'encadré.
        items, condition = list(items), []
        while items and items[0][0] == 'instruction':
            condition.append(items.pop(0)[1])
        return self.box(self.render_sequence(items), brief(' '.join(condition)))

    def paragraph(self, r) -> str:
        self.c.where = (self.ref, r['i'])
        raw = r['raw']
        if self.in_zimoun:
            raw = re.sub(r'<small>\(בעשרה ויותר:\s*<b>(.*?)</b>\)\s*</small>', r'[\1]', raw)
        # « (<small>condition</small> texte) » : ajout ou remplacement conditionnel.
        paren = re.compile(r'\(<small>(.*?)</small>\s*([^()]*)\)', re.S)
        units, pos = [], 0
        for m in paren.finditer(raw):
            units.extend(outer_units(raw[pos:m.start()]))
            units.append(('parenthesis', (clean_markup(m[1]), clean_markup(m[2]))))
            pos = m.end()
        units.extend(outer_units(raw[pos:]))

        parts: list[str] = []
        state = {'buffer': '', 'before': [], 'markers': ''}

        def flush(suffix: str = '') -> None:
            for text in state['before']:
                parts.append(self.note(text))
            if HE_RE.search(state['buffer']):
                if self.in_zimoun:
                    rendered = self.prayer(state['buffer'], state['markers'], suffix)
                    parts.append(re.sub(r'\[([^\[\]<>]+)\]', r'<span class="optional-word">[\1]</span>', rendered))
                else:
                    parts.append(self.prayer(state['buffer'], state['markers'], suffix))
            elif suffix:
                append_to_last_prayer(parts, suffix)
            state.update(buffer='', before=[], markers='')

        def short(prayer: str, label: str) -> bool:
            return len(prayer.split()) <= INLINE_WORDS and len(label) <= INLINE_LABEL

        for k, (unit, value) in enumerate(units):
            if unit == 'main':
                state['buffer'] += ' ' + value
                continue
            if unit == 'parenthesis':
                cond, prayer = value
                label = brief(self.c.instruction(cond))
                if HE_RE.search(state['buffer']) and short(prayer, label) and not CITATION_RE.search(label):
                    state['buffer'] += ' ' + variant(label, prayer)
                else:
                    flush()
                    parts.append('<div class="insertion"><p class="card-head">' + self.with_citations(label)
                                 + '</p>' + self.prayer(prayer) + '</div>')
                    nxt = units[k + 1] if k + 1 < len(units) else None
                    if self.in_zimoun and nxt and nxt[0] == 'main' and HE_RE.search(nxt[1]):
                        parts.append('<p class="join-label">Suite pour tous</p>')
                continue

            if REFERENCE_RE.fullmatch(value.strip()) and HE_RE.search(state['buffer']):
                # Référence biblique au fil du texte : elle reste à sa place, en petit.
                state['buffer'] += ' ' + value.strip()
                continue
            items = merge_prayers(self.c.split(value))
            instructions = [t for kind, t in items if kind == 'instruction' and re.search(r'\w', t)]
            prayers = [t for kind, t in items if kind == 'prayer']
            if not instructions:
                state['buffer'] += ' ' + ' '.join(prayers)
                continue
            text = ' '.join(instructions)
            if not prayers:
                if PLACEHOLDER_RE.match(text) and HE_RE.search(state['buffer']):
                    state['buffer'] += ' ' + variant(text.strip('().'), '')
                elif is_technical(text):
                    state['markers'] += self.footnote(text, state['buffer'])
                elif REPETITION_RE.match(text):
                    *first, last = split_vihi_noam(state['buffer'])
                    if first:
                        state['buffer'] = first[0]
                        flush()
                        state['buffer'] = last
                    flush(repetition_span(text))
                elif AFTER_RE.match(text):
                    flush()
                    parts.append(self.note(text, after=True))
                else:
                    # Une consigne gestuelle reste à son emplacement exact.
                    flush()
                    parts.append(self.note(text))
                continue

            key = plain_hebrew(' '.join(prayers))
            woman = 'Une femme dit' in text
            target = 'מודה' if woman and key == 'מודה' else REPLACEMENTS.get(key)
            found = find_hebrew(state['buffer'], target) if target else None
            alt = ' '.join(prayers)
            if found:
                # Remplacement d'un mot ou d'une formule : la variante suit la formule habituelle.
                b = state['buffer']
                label = 'Une femme' if woman else brief(text)
                state['buffer'] = b[:found.end()] + ' ' + variant(label, alt) + b[found.end():]
                continue
            if plain_hebrew(state['buffer']).strip() == 'מגדיל' and key == 'מגדול':
                state['buffer'] += ' ' + variant(brief(text), alt)
                continue
            if len(items) == 2 and items[0][0] == 'instruction' and text.startswith('On répond'):
                # Réponse de l'assemblée : consigne en italique, puis la réponse, hors encadré.
                flush()
                parts.append(self.note(text) + self.answer(alt))
                continue
            if (len(items) == 2 and items[0][0] == 'instruction' and HE_RE.search(state['buffer'])
                    and is_condition(text) and short(alt, brief(text)) and not CITATION_RE.search(text)):
                state['buffer'] += ' ' + variant(brief(text), alt)
                continue
            flush()
            parts.append(self.conditional_items(items))
        flush()
        return ''.join(parts)

    # --- Section complète ------------------------------------------------------
    def span_until(self, start: int, stop=None) -> int:
        """Index du premier paragraphe qui n'est plus une note, à partir de start."""
        j = start
        while j < len(self.records) and self.records[j]['kind'] == 'note' and not (stop and stop(self.records[j])):
            j += 1
        return j

    def zimoun(self, i: int, out: list[str]) -> int:
        """Invitation au Birkat hamazone : un seul encadré pour tout le dialogue."""
        j = i + 1
        while j < len(self.records) and not self.records[j]['plain'].startswith('ברוך אתה'):
            j += 1
        roles = {'Celui qui conduit le zimoun dit :': 'Celui qui conduit',
                 'Celui qui conduit le zimoun répond :': 'Celui qui conduit',
                 'Les convives répondent :': 'Les convives'}
        body = []
        self.in_zimoun = True
        try:
            for part in self.records[i + 1:j]:
                sequence = self.items(part)
                if sequence and all(k == 'instruction' for k, _ in sequence):
                    fr = ' '.join(t for _, t in sequence)
                    body.append('<p class="role-label" id="p-' + str(part['i']) + '">'
                                + html.escape(roles.get(fr, fr)) + '</p>')
                else:
                    body.append(self.record_body(part))
        finally:
            self.in_zimoun = False
        skip = '<a href="#p-' + str(j) + '">Sans zimoun : passer à la première bénédiction</a>'
        out.append(self.block(i, self.box(''.join(body), 'Zimoun · à partir de trois convives',
                                          'À partir de dix convives, ajouter les mots entre crochets. ' + skip,
                                          css='role')))
        return j

    def special(self, i: int, r, out: list[str]) -> int | None:
        """Passages de l'Amida et du Birkat hamazone traités comme un tout. Renvoie l'index suivant."""
        p = r['plain']
        if self.is_meal and p == 'אם המסובים שלושה או יותר אומרים':
            return self.zimoun(i, out)
        if not self.is_amida:
            return None
        # Quelques intertitres de la source n'étaient pas balisés <big>.
        if p == 'ברכת כהנים' or (p.startswith('קדושה') and len(p) < 55):
            # Repère posé au début d'une prière réunie : l'encadré la couvre en entier.
            j = self.bornes.get(i, self.span_until(i + 1))
            label = ('Bénédiction des Cohanim · répétition de l’Amida' if p == 'ברכת כהנים'
                     else 'Kedoucha · répétition de l’Amida')
            body = ''.join(self.record_body(x) for x in self.records[i + 1:j])
            out.append(self.block(i, self.box(body, label, resume=self.resume_from(j), css='role')))
            return j
        if p.startswith('כתר יתנו'):
            out.append(self.block(i, self.box(self.paragraph(r), 'Kedoucha de Moussaf · répétition',
                                              resume=self.resume_from(i + 1), css='role')))
            return i + 1
        if p == 'מודים דרבנן' or p.startswith('מודים דרבנן בחזרת'):
            rule = 'Pendant la répétition, quand l’officiant dit Modim.'
            if p == 'מודים דרבנן':
                j = self.span_until(i + 1, lambda x: x['plain'].startswith('בחנוכה'))
                body = ''.join(self.record_body(x) for x in self.records[i + 1:j])
            else:
                # Le titre, non vocalisé, fait double emploi avec l'en-tête de l'encadré ;
                # la consigne qui suit remplace la règle de l'encadré.
                j, rule = i + 1, ''
                body = self.paragraph(dict(r, raw=re.sub(r'^\s*מודים דרבנן\s*(?:<br\s*/?>)?', '', r['raw'])))
            out.append(self.block(i, self.box(body, 'Modim derabbanan · réponse de l’assemblée', rule,
                                              resume=self.resume_from(j), css='role')))
            return j
        # Barékhénou / Barékh alénou : deux versions d'une même bénédiction.
        if p == 'בקיץ' and i + 3 < len(self.records) and self.records[i + 2]['plain'] == 'בחורף':
            body = ('<p class="alternative-label">En été</p>' + self.record_body(self.records[i + 1])
                    + '<p class="alternative-label">En hiver</p>' + self.record_body(self.records[i + 3]))
            out.append(self.block(i, self.box(body, 'Bénédiction de l’année · une seule version',
                                              resume=self.resume_from(i + 4), css='choice')))
            return i + 4
        if p.startswith('בקיץ') and 'בחורף' in p and 'מוריד הטל' in p:
            body = ''.join('<p class="alternative-label">' + html.escape(t) + '</p>' if k == 'instruction'
                           else self.prayer(t) for k, t in self.items(r))
            out.append(self.block(i, self.box(body, 'Une seule formule selon la saison', css='choice')))
            return i + 1
        return None

    def condition_block(self, i: int, r, fr: str, out: list[str]) -> int | None:
        """Consigne isolée suivie d'un ajout conditionnel : un encadré avec lien de reprise."""
        nxt = self.records[i + 1] if i + 1 < len(self.records) else None
        if not (nxt and nxt['kind'] == 'note' and any(k == 'prayer' for k, _ in self.items(nxt))):
            return None
        if not (is_condition(fr) or self.is_amida and ('répétition' in fr or 'officiant' in fr)):
            return None
        first, p = nxt['plain'], r['plain']
        yaale = re.match(r'אלהינו ואלהי אבותינו[, ]+יעלה', first)
        long_insert = (yaale or first.startswith('על הנסים') or first.startswith('אבינו מלכנו')
                       or p.startswith('אם שכח') or p.startswith('בתענית ציבור השליח'))
        j = self.span_until(i + 2) if long_insert else i + 2
        body = ''.join(self.record_body(x) for x in self.records[i + 1:j])
        if yaale:
            body = self.note('À « beyom », choisir la date, puis poursuivre à « Léra’hem bo… ».') + body
        out.append(self.block(i, self.box(body, brief(fr), resume=self.resume_from(j))))
        return j

    def render(self) -> str:
        out = ['<h2>' + html.escape(self.title) + '</h2>']
        i = 0
        while i < len(self.records):
            r = self.records[i]
            if r['kind'] == 'heading':
                heading = self.c.heading(r['plain'])
                if heading.casefold() != self.title.casefold():
                    out.append('<h3>' + html.escape(heading) + '</h3>')
                i += 1
                continue
            kavana = OMER_KAVANA_RE.match(r['plain'])
            if kavana:
                out.append(self.block(i, self.kavana(r['text'], kavana)))
                i += 1
                continue
            j = self.special(i, r, out)
            if j is not None:
                i = j
                continue
            items = self.items(r)
            standalone = r['kind'] == 'note' and items and all(k == 'instruction' for k, _ in items)
            if not standalone:
                out.append(self.block(i, self.paragraph(r)))
                i += 1
                continue
            fr = ' '.join(t for _, t in items)
            j = self.condition_block(i, r, fr, out)
            if j is not None:
                i = j
                continue
            if is_technical(fr):
                self.carry.append(self.footnote(fr))
                out.append(self.block(i, ''))
            elif REPETITION_RE.match(fr) and append_to_last_prayer(out, repetition_span(fr)):
                out.append(self.block(i, ''))
            else:
                out.append(self.block(i, self.note(fr, after=bool(AFTER_RE.match(fr)))))
            i += 1
        if self.notes:
            out.append('<section class="notes"><h3>Notes</h3>')
            for n, text, target in self.notes:
                where = '<em>« ' + html.escape(target) + ' »</em> : ' if target else ''
                out.append('<aside epub:type="footnote" id="note-' + str(n) + '"><p><a href="#appel-' + str(n)
                           + '">' + str(n) + '.</a> ' + where + html.escape(text) + '</p></aside>')
            out.append('</section>')
        return '\n'.join(out)


def render_section(title, paragraphs, mode, ref, consignes, bornes=None):
    return ReadingLayout(title, paragraphs, mode, ref, consignes, bornes).render()
