"""Assemblage des trois éditions EPUB (et des aperçus HTML facultatifs)."""
from __future__ import annotations

import html
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .consignes import Consignes
from .mise_en_page import render_section
from .rites import SEFARADE, Rite
from .sources import validate_source, versions_of
from .version import Version, date_fr

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

SERIES_POSITION = {'hebreu': '1', 'phonetique': '2', 'bilingue': '3'}
_DESCRIPTION = {
    'hebreu': '{}, textes en hébreu vocalisé, consignes en français : {}.',
    'phonetique': '{} en phonétique française, consignes en français : {}.',
    'bilingue': '{} : chaque passage en hébreu vocalisé suivi de sa phonétique, consignes en français : {}.',
}
FONT_NOTICE = 'La police Noto Serif Hebrew est distribuée sous SIL Open Font License 1.1.'


def description(mode: str, rite: Rite = SEFARADE) -> str:
    return _DESCRIPTION[mode].format(rite.titre_long, rite.description)


# Introduction de la page des livres, quand le site réunit les deux rites.
RITES_INTRODUCTION = 'Deux rites sont proposés : le rite séfarade (Edot HaMizrah) et le rite ashkénaze.'


def introduction(rite: Rite | None = SEFARADE) -> str:
    """Introduction d'une édition ; sans rite, celle du site qui réunit les deux."""
    contenu, phrase = (SEFARADE.contenu, RITES_INTRODUCTION) if rite is None else (rite.contenu, rite.introduction)
    return (
        '<h1>Introduction</h1>'
        '<p class="intro">Ce siddour est né d’un souhait simple : que chacun puisse avoir sur soi, '
        'où qu’il soit, un livre de prière aussi complet que possible. Le voyageur loin de sa '
        'synagogue, celui qui part pour quelques jours et ne peut emporter ses livres, celui qui '
        'veut retrouver la prière d’un moment ou d’une fête sans chercher dans plusieurs volumes : '
        'tous trouveront ici, dans une liseuse ou un téléphone, ' + contenu + '.</p>'
        '<p class="intro">' + phrase + ' Les consignes sont '
        'traduites en français et placées juste avant le passage qu’elles concernent, pour que '
        'l’on sache toujours quoi dire, quand et comment, même sans connaître l’hébreu des '
        'rubriques. Trois éditions sont proposées : en hébreu, en phonétique, ou chaque passage '
        'en hébreu suivi de sa phonétique.</p>'
        '<p class="intro">Il faut pourtant le dire avec humilité : un fichier n’est qu’un '
        'compagnon de route. Depuis des siècles, c’est le livre de papier, copié, imprimé, '
        'relié, usé par les mains des pères puis transmis aux enfants, qui a porté les paroles '
        'saintes à travers les âges et les générations. Aucun écran ne remplace ce siddour '
        'de famille dont les pages gardent la trace de ceux qui ont prié avant nous. Ce livre '
        'numérique ne prétend pas prendre sa place ; il voudrait seulement accompagner ceux qui '
        'sont loin de lui, jusqu’à ce qu’ils le retrouvent.</p>'
        '<p class="intro fin">Que nos prières soient agréées.</p>'
    )


def exposants(text: str) -> str:
    """Échappe le texte ; ʳᵉ, ᵉʳ et ᵉ deviennent des <sup>, absents de certaines polices de liseuse."""
    text = html.escape(text)
    for uni, sup in (('ʳᵉ', 're'), ('ᵉʳ', 'er'), ('ᵉ', 'e')):
        text = text.replace(uni, '<sup>' + sup + '</sup>')
    return text


def colophon(version: Version) -> str:
    """Repère d'édition en bas de l'introduction, visible dès l'ouverture du livre."""
    return ('<div class="colophon"><p>' + exposants(version.libelle) + '</p>'
            '<p>Fabriqué le ' + exposants(date_fr(version.jour)) + '</p></div>')


def make_credits(title: str, licences: set[str], mode: str, version: Version, rite: Rite = SEFARADE) -> str:
    items = ''.join('<li>' + html.escape(x) + '</li>' for x in sorted(licences))
    note = ('La phonétique est générée automatiquement selon des conventions françaises '
            'et peut comporter des approximations. ' + rite.phonetique) if mode != 'hebreu' else ''
    return ('<h1>À propos de cette édition</h1>'
            '<p class="credits"><b>' + html.escape(title) + '.</b> ' + EDITION_NOTES[mode] + '</p>'
            '<p class="credits">' + exposants(version.complet) + '.</p>'
            '<p class="credits">' + html.escape(rite.libelle) + '. Textes issus de Sefaria.</p>'
            '<ul class="credits">' + items + '</ul>'
            '<p class="credits">' + note
            + 'Les consignes figurent en italique juste avant le passage qu’elles concernent. '
              'Une variante brève est donnée entre crochets, dans la phrase, avec sa condition. '
              'Les ajouts plus longs sont encadrés et proposent un lien vers la suite de la prière. '
              'Les sources et les précisions techniques sont en notes numérotées, en fin de section. '
              'Les consignes françaises traduisent cette source et ses usages, ' + rite.usages + '.</p>'
            + ('<p class="credits">' + FONT_NOTICE + '</p>' if mode != 'phonetique' else ''))


def make_contents(chapters: list[tuple[str, str, list[str]]]) -> str:
    """Sommaire sur deux colonnes : chapitres numérotés et leurs sections (liens)."""
    blocks = []
    for ci, (fr, he, hrefs_titles) in enumerate(chapters, 1):
        first = hrefs_titles[0][0]
        head = ('<p class="sommaire-chap"><a href="' + first + '"><span class="sommaire-num">'
                + str(ci) + '</span> ' + html.escape(fr) + '</a>'
                + (' <span class="sommaire-he" lang="he" dir="rtl">' + html.escape(he) + '</span>' if he else '')
                + '</p>')
        subs = ''
        if len(hrefs_titles) > 1:
            subs = '<ul class="sommaire-sections">' + ''.join(
                '<li><a href="' + href + '">' + html.escape(t) + '</a></li>' for href, t in hrefs_titles) + '</ul>'
        blocks.append('<div class="sommaire-bloc">' + head + subs + '</div>')
    return '<h1>Sommaire</h1><div class="sommaire">' + ''.join(blocks) + '</div>'


def cover_image(mode: str, rite: Rite = SEFARADE) -> tuple[str, bytes] | None:
    """Couverture de l'édition, recompressée en JPEG si Pillow est disponible."""
    path = rite.couvertures / ('siddour_' + mode + '.png')
    if not path.exists():
        return None
    try:
        import io
        from PIL import Image
    except ImportError:
        return 'images/cover.png', path.read_bytes()
    with Image.open(path) as im:
        im = im.convert('RGB')
        if im.height > 1600:
            im = im.resize((round(im.width * 1600 / im.height), 1600), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, 'JPEG', quality=88, optimize=True, progressive=True)
    return 'images/cover.jpg', out.getvalue()


def cover_page(cover: tuple[str, bytes], title: str) -> str:
    """Image en pleine page, proportions conservées, quelle que soit la taille de l'écran."""
    return ('<div class="couverture"><img src="../' + cover[0] + '" alt="'
            + html.escape(title, quote=True) + '"/></div>')


def add_metadata(book, title: str, mode: str, licences: set[str], version: Version, rite: Rite = SEFARADE) -> None:
    book.set_identifier(rite.urn + mode)
    book.set_title(title)
    # Langue principale du texte récité, puis celle des consignes.
    main, other = ('he', 'fr') if mode == 'hebreu' else ('fr', 'he')
    book.set_language(main)
    book.add_metadata('DC', 'language', other)
    book.add_author('Siddour-ebook', uid='creator')
    book.add_metadata('DC', 'contributor', 'Sefaria (textes sources)')
    book.add_metadata('DC', 'publisher', 'Siddour-ebook')
    book.add_metadata('DC', 'date', version.jour.isoformat())
    book.add_metadata('DC', 'description', description(mode, rite) + ' ' + version.complet + '.')
    book.add_metadata(None, 'meta', version.libelle, {'property': 'schema:version'})
    for subject in rite.sujets:
        book.add_metadata('DC', 'subject', subject)
    book.add_metadata('DC', 'source', 'Sefaria, ' + rite.livre + ' (https://www.sefaria.org)')
    book.add_metadata('DC', 'rights', 'Textes : Sefaria. ' + ' ; '.join(sorted(licences))
                      + ('. ' + FONT_NOTICE if mode != 'phonetique' else '.'))
    book.add_metadata(None, 'meta', rite.serie, {'property': 'belongs-to-collection', 'id': 'collection'})
    book.add_metadata(None, 'meta', 'series', {'refines': '#collection', 'property': 'collection-type'})
    book.add_metadata(None, 'meta', SERIES_POSITION[mode], {'refines': '#collection', 'property': 'group-position'})
    # Calibre lit encore ces métadonnées EPUB 2 pour la série.
    book.add_prefix('schema', 'http://schema.org/')
    book.add_metadata(None, 'meta', '', {'name': 'calibre:series', 'content': rite.serie})
    book.add_metadata(None, 'meta', '', {'name': 'calibre:series_index', 'content': SERIES_POSITION[mode]})
    # Accessibilité (schema.org), lue par les catalogues et certaines liseuses.
    for prop, value in [('schema:accessMode', 'textual'), ('schema:accessModeSufficient', 'textual'),
                        ('schema:accessibilityFeature', 'structuralNavigation'),
                        ('schema:accessibilityFeature', 'tableOfContents'),
                        ('schema:accessibilityHazard', 'none'),
                        ('schema:accessibilitySummary',
                         'Texte structuré par chapitres et sections, avec sommaire, '
                         'notes liées et langue hébraïque balisée.')]:
        book.add_metadata(None, 'meta', value, {'property': prop})


@dataclass
class Livre:
    """Une édition mise en page, prête à être assemblée en EPUB ou en site web."""
    mode: str
    version: Version
    licences: set[str]
    chapters: list[tuple[dict, list[tuple[str, str]]]]  # (chapitre du plan, [(titre, html)])
    rite: Rite = SEFARADE

    @property
    def title(self) -> str:
        return self.rite.nom + ' : ' + TITLES[self.mode]

    @property
    def epub(self) -> str:
        return self.rite.epub(self.mode)


def render_book(plan: list[dict], sources: dict, mode: str, consignes: Consignes,
                version: Version | None = None, rite: Rite = SEFARADE, strict: bool = True) -> Livre:
    """Met en page une édition ; strict=False laisse les traductions manquantes en place, pour relecture."""
    consignes.missing.clear()
    chapters = []
    licences: set[str] = set()
    for chap in plan:
        sections = []
        for title, ref in chap['sections']:
            data = sources[ref]
            v, texts = validate_source(data, ref)
            for book, version_ in versions_of(data):
                licences.add(book + ', ' + version_.get('versionTitle', '').strip() + ' : '
                             + version_.get('license', 'licence non précisée'))
            sections.append((title, render_section(title, texts, mode, ref, consignes, v.get('bornes'),
                                                   rite.prononciation)))
        chapters.append((chap, sections))
    if consignes.missing and strict:
        raise ValueError('Traductions manquantes :\n' + '\n'.join(sorted(consignes.missing)))
    return Livre(mode, version or Version(), licences, chapters, rite)


def build_edition(livre: Livre, sortie: Path, font: Path | None, with_html: bool = False) -> Path:
    mode, version, licences, title, rite = livre.mode, livre.version, livre.licences, livre.title, livre.rite
    chapters = [(chap['fr'], sections) for chap, sections in livre.chapters]
    plan = [chap for chap, _ in livre.chapters]
    from ebooklib import epub
    book = epub.EpubBook()
    add_metadata(book, title, mode, licences, version, rite)
    cover = cover_image(mode, rite)
    if cover:
        book.set_cover(cover[0], cover[1], create_page=False)
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

    # Les pages de chapitre sont créées d'abord pour connaître leurs liens ;
    # l'ordre de lecture est fixé ensuite par la spine.
    chapter_pages = []
    for ci, (chap_title, sections) in enumerate(chapters, 1):
        pages = []
        for si, (section_title, content) in enumerate(sections, 1):
            heading = '<h1>' + html.escape(chap_title) + '</h1>' if si == 1 else ''
            pages.append(page(f'c{ci:02d}_{si:02d}', section_title, heading + content))
        chapter_pages.append(pages)
    contents = make_contents([
        (chap['fr'], chap.get('he', ''), [(p.file_name.removeprefix('text/'), p.title) for p in pages])
        for chap, pages in zip(plan, chapter_pages)])
    credits = make_credits(title, licences, mode, version, rite)
    intro_html = introduction(rite) + colophon(version)
    sommaire = page('sommaire', 'Sommaire', contents)
    intro = page('introduction', 'Introduction', intro_html)
    about = page('a-propos', 'À propos de cette édition', credits)
    spine = [sommaire, intro, about]
    guide = []
    if cover:
        couverture = page('couverture', 'Couverture', cover_page(cover, title))
        spine.insert(0, couverture)
        guide.append({'type': 'cover', 'title': 'Couverture', 'href': couverture.file_name})
    toc = [intro, about]
    htmlparts = [contents, intro_html, credits]
    for (chap_title, sections), pages in zip(chapters, chapter_pages):
        htmlparts.append('<h1>' + html.escape(chap_title) + '</h1>')
        htmlparts.extend(content for _, content in sections)
        spine.extend(pages)
        toc.append((epub.Section(chap_title, href=pages[0].file_name), pages))
    book.guide = guide + [{'type': 'toc', 'title': 'Sommaire', 'href': sommaire.file_name},
                  {'type': 'text', 'title': 'Introduction', 'href': intro.file_name}]
    book.spine = spine
    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())  # navigation de la liseuse (hors ordre de lecture)

    path = Path(sortie) / livre.epub
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
    print('EPUB :', path, '|', version.libelle, '|', len(chapters), 'chapitres,', sum(len(s) for _, s in chapters), 'sections')
    return path
