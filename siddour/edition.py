"""Assemblage des trois éditions EPUB (et des aperçus HTML facultatifs)."""
from __future__ import annotations

import html
import zipfile
from pathlib import Path

from .consignes import Consignes
from .mise_en_page import render_section
from .plan import BOOK
from .sources import validate_source

ROOT = Path(__file__).resolve().parent.parent
CSS = (Path(__file__).resolve().parent / 'style.css').read_text(encoding='utf-8')
FONT_PATH = ROOT / 'assets' / 'fonts' / 'NotoSerifHebrew-Regular.ttf'
FONT_LICENSE = ROOT / 'OFL-NotoSerifHebrew.txt'

TITLES = {'hebreu': 'hébreu', 'phonetique': 'phonétique', 'bilingue': 'hébreu et phonétique'}
EDITION_NOTES = {
    'hebreu': 'Textes à réciter en hébreu ; consignes en français.',
    'phonetique': 'Textes à réciter en phonétique ; consignes en français.',
    'bilingue': 'Chaque passage en hébreu, suivi de sa phonétique ; consignes en français.',
}


def make_credits(title: str, licences: set[str], mode: str) -> str:
    items = ''.join('<li>' + html.escape(x) + '</li>' for x in sorted(licences))
    note = ('La phonétique est générée automatiquement selon des conventions françaises '
            'et peut comporter des approximations. ') if mode != 'hebreu' else ''
    return ('<h1>' + html.escape(title) + '</h1>'
            '<p class="credits">' + EDITION_NOTES[mode] + '</p>'
            '<p class="credits">Rite séfarade (Edot HaMizrah). Textes issus de Sefaria.</p>'
            '<ul class="credits">' + items + '</ul>'
            '<p class="credits">' + note
            + 'Les consignes figurent en italique juste avant le passage qu’elles concernent. '
              'Une variante brève est donnée entre crochets, dans la phrase, avec sa condition. '
              'Les ajouts plus longs sont encadrés et proposent un lien vers la suite de la prière. '
              'Les sources et les précisions techniques sont en notes numérotées, en fin de section. '
              'Les consignes françaises traduisent cette source et ses usages, notamment ceux du Ben Ich ’Haï. '
              'Le classement reprend le plan fourni, inspiré de l’index du Sidour Torah-Box ; '
              'il ne constitue pas une reproduction de cette édition.</p>')


def build_edition(plan: list[dict], sources: dict, mode: str, consignes: Consignes,
                  sortie: Path, font: Path | None, with_html: bool = False) -> Path:
    consignes.missing.clear()
    chapters = []
    licences: set[str] = set()
    for chap in plan:
        sections = []
        for title, ref in chap['sections']:
            data = sources[ref]
            v, texts = validate_source(data, ref)
            licences.add((data.get('indexTitle') or data.get('book') or BOOK) + ', '
                         + v.get('versionTitle', '').strip() + ' : ' + v.get('license', 'licence non précisée'))
            sections.append((title, render_section(title, texts, mode, ref, consignes)))
        chapters.append((chap['fr'], sections))
    if consignes.missing:
        raise ValueError('Traductions manquantes :\n' + '\n'.join(sorted(consignes.missing)))

    from ebooklib import epub
    title = 'Siddour séfarade : ' + TITLES[mode]
    book = epub.EpubBook()
    book.set_identifier('siddour-edot-hamizrah-liseuse-' + mode)
    book.set_title(title)
    book.set_language('he' if mode == 'hebreu' else 'fr')
    book.add_metadata('DC', 'rights', 'Textes : Sefaria. ' + ' ; '.join(sorted(licences)))
    css = CSS
    if font and mode != 'phonetique':
        media = 'font/ttf' if font.suffix.lower() == '.ttf' else 'font/otf'
        book.add_item(epub.EpubItem(uid='hebrew-font', file_name='fonts/' + font.name,
                                    media_type=media, content=font.read_bytes()))
        if font.resolve() == FONT_PATH.resolve():
            book.add_item(epub.EpubItem(uid='font-license', file_name='fonts/OFL.txt',
                                        media_type='text/plain', content=FONT_LICENSE.read_bytes()))
        css = '@font-face { font-family: "SiddurHebrew"; src: url("../fonts/' + font.name + '"); }\n' + css
    book.add_item(epub.EpubItem(uid='style', file_name='style/main.css', media_type='text/css', content=css.encode()))

    def page(name: str, page_title: str, content: str):
        p = epub.EpubHtml(title=page_title, file_name='text/' + name + '.xhtml', lang='fr')
        p.content = content
        # Chemin relatif à text/, et non à la racine du livre.
        p.add_link(href='../style/main.css', rel='stylesheet', type='text/css')
        book.add_item(p)
        return p

    credits = make_credits(title, licences, mode)
    intro = page('presentation', 'Présentation', credits)
    spine = ['nav', intro]
    toc = [intro]
    htmlparts = [credits]
    for ci, (chap_title, sections) in enumerate(chapters, 1):
        pages = []
        htmlparts.append('<h1>' + html.escape(chap_title) + '</h1>')
        for si, (section_title, content) in enumerate(sections, 1):
            heading = '<h1>' + html.escape(chap_title) + '</h1>' if si == 1 else ''
            pages.append(page(f'c{ci:02d}_{si:02d}', section_title, heading + content))
            htmlparts.append(content)
        spine.extend(pages)
        toc.append((epub.Section(chap_title, href=pages[0].file_name), pages))
    book.spine = spine
    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    path = Path(sortie) / ('siddour_liseuse_' + mode + '.epub')
    temp = path.with_suffix('.epub.tmp')
    epub.write_epub(str(temp), book, options={'raise_exceptions': True})
    with zipfile.ZipFile(temp) as archive:
        if archive.testzip() is not None:
            raise ValueError('Archive EPUB endommagée : ' + str(temp))
    temp.replace(path)
    if with_html:
        path.with_suffix('.html').write_text(
            '<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>' + html.escape(title)
            + '</title><style>' + CSS + '</style></head><body>' + ''.join(htmlparts) + '</body></html>',
            encoding='utf-8')
    print('EPUB :', path, '|', len(chapters), 'chapitres,', sum(len(s) for _, s in chapters), 'sections')
    return path
