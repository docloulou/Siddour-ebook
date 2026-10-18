"""Édition PDF, au format A5, à imprimer ou à lire sur tablette : même contenu que l'EPUB.

Le livre est mis en page par WeasyPrint à partir des pages de l'EPUB : couverture, sommaire avec
numéros de page, introduction, « À propos », puis les chapitres, chacun sur une nouvelle page.
Le PDF porte des signets (chapitres et sections), le titre du chapitre en haut de page et les
liens internes du sommaire, des notes et des ajouts encadrés.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from .edition import (CSS, FONT_PATH, Livre, colophon, cover_image, description,
                      introduction, make_contents, make_credits, make_modifications)

FONTS = FONT_PATH.parent
# Noto Serif (latin), réduite aux alphabets latins : le texte français et la phonétique (ḥ, ‘…)
# s'affichent pareil sur toutes les machines, quelles que soient les polices installées.
LATIN = {('normal', 'normal'): 'NotoSerif-Regular.ttf', ('italic', 'normal'): 'NotoSerif-Italic.ttf',
         ('normal', 'bold'): 'NotoSerif-Bold.ttf'}
FONT_NOTICE = 'Les polices Noto Serif et Noto Serif Hebrew sont distribuées sous SIL Open Font License 1.1.'

PDF_CSS = '''
@page {
  size: A5; margin: 17mm 15mm 18mm;
  @top-center { content: string(chapitre); font: italic 8pt "Livre", serif; color: #666; }
  @bottom-center { content: counter(page); font: 8.5pt "Livre", serif; color: #444; }
}
@page couverture { margin: 0; background: #0a1f3c; @top-center { content: none; } @bottom-center { content: none; } }
@page liminaire { @top-center { content: none; } }
html { font-size: 10.5pt; }
body { font-family: "Livre", "SiddurHebrew", serif; margin: 0; hyphens: auto; orphans: 2; widows: 2; }
/* Les petits titres sans empattement de l'EPUB restent dans les polices du livre. */
h4, .role-label, .join-label, .card-head, .card-rule, .resume, .alternative-label, .reference, .note-ref,
.colophon { font-family: "Livre", "SiddurHebrew", serif; }
h1 { bookmark-level: 1; margin: 0 0 1.2em; }
h2 { bookmark-level: 2; break-before: auto; margin-top: 1.6em; }
h3, h4 { bookmark-level: none; }
.he, .sommaire-he, .chapitre-he { font-family: "SiddurHebrew", "Livre", serif; }
.he { hyphens: manual; }
.ph { text-align: justify; }
.rubrique, .credits, .sommaire { text-align: left; }
.he + .ph { break-before: avoid; }
.colophon { break-inside: avoid; }
.liminaire .intro { font-size: .95em; }
a { text-decoration: none; }
.couverture { page: couverture; height: 210mm; }
.couverture img { width: 148mm; height: 210mm; max-height: none; object-fit: contain; display: block; }
.liminaire { page: liminaire; break-before: page; }
.chapitre { break-before: page; }
.chapitre > h1 { string-set: chapitre content(); }
.chapitre-he { text-align: center; font-size: 1.15em; color: #555;
               margin: -.7em 0 1.4em; }
/* Le sommaire renvoie aux pages du livre. */
.sommaire { font-size: .86em; }
.sommaire-chap a::after, .sommaire-sections a::after { content: " " target-counter(attr(href), page); color: #8a6d1f; }
.sommaire-sections a::after { font-size: .92em; }
'''


def font_faces(font: Path | None) -> str:
    faces = ''.join('@font-face { font-family: "Livre"; font-style: ' + style + '; font-weight: ' + weight
                    + '; src: url("' + (FONTS / name).as_uri() + '"); }\n'
                    for (style, weight), name in LATIN.items() if (FONTS / name).exists())
    if font:
        faces += '@font-face { font-family: "SiddurHebrew"; src: url("' + font.resolve().as_uri() + '"); }\n'
    return faces


def ancres(content: str, prefixe: str) -> str:
    """Préfixe les identifiants d'une section : chaque section de l'EPUB a ses propres p-15, note-1…"""
    content = re.sub(r'(\sid=")([^"]+)"', lambda m: m[1] + prefixe + m[2] + '"', content)
    return re.sub(r'(\shref="#)([^"]+)"', lambda m: m[1] + prefixe + m[2] + '"', content)


def document(livre: Livre, font: Path | None) -> str:
    """Le livre en une seule page HTML, prête pour WeasyPrint."""
    mode, version, rite = livre.mode, livre.version, livre.rite
    cover = cover_image(mode, rite)
    parts = []
    if cover:
        import base64
        mime = 'image/jpeg' if cover[0].endswith('.jpg') else 'image/png'
        parts.append('<div class="couverture"><img src="data:' + mime + ';base64,'
                     + base64.b64encode(cover[1]).decode() + '" alt="' + html.escape(livre.title, quote=True) + '"/></div>')
    contents = make_contents([
        (chap['fr'], chap.get('he', ''), [('#c%02d_%02d' % (ci, si), title) for si, (title, _) in enumerate(sections, 1)])
        for ci, (chap, sections) in enumerate(livre.chapters, 1)])
    credits = make_credits(livre.title, livre.licences, mode, version, rite)
    # Le PDF embarque toujours les deux polices, phonétique comprise (titres hébreux du sommaire).
    credits = re.sub(r'<p class="credits">[^<]*Open Font License[^<]*</p>', '', credits)
    credits += '<p class="credits">' + FONT_NOTICE + '</p>'
    for page in (contents, introduction(rite) + colophon(version), credits):
        parts.append('<div class="liminaire">' + page + '</div>')
    for ci, (chap, sections) in enumerate(livre.chapters, 1):
        he = ('<p class="chapitre-he" lang="he" dir="rtl">' + html.escape(chap['he']) + '</p>') if chap.get('he') else ''
        body = ''.join('<section id="c%02d_%02d">' % (ci, si) + ancres(content, 's%02d%02d-' % (ci, si)) + '</section>'
                       for si, (_, content) in enumerate(sections, 1))
        parts.append('<div class="chapitre"><h1>' + html.escape(chap['fr']) + '</h1>' + he + body + '</div>')
    modifications = make_modifications(livre)
    if modifications:
        parts.append('<div class="liminaire">' + modifications + '</div>')
    body = ''.join(parts).replace('epub:type="noteref"', 'role="doc-noteref"').replace('epub:type="footnote"', 'role="doc-footnote"')
    lang = 'he' if mode == 'hebreu' else 'fr'
    return ('<!doctype html><html lang="' + lang + '"><head><meta charset="utf-8"><title>' + html.escape(livre.title)
            + '</title><meta name="author" content="Siddour-ebook">'
            + '<meta name="description" content="' + html.escape(description(mode, rite) + ' ' + version.complet + '.', quote=True) + '">'
            + '<meta name="keywords" content="' + html.escape(', '.join(rite.sujets), quote=True) + '">'
            + '<meta name="generator" content="Siddour-ebook">'
            + '<meta name="dcterms.created" content="' + version.jour.isoformat() + '">'
            + '<style>' + font_faces(font) + CSS + PDF_CSS + '</style></head><body>' + body + '</body></html>')


def build_pdf(livre: Livre, sortie: Path, font: Path | None = FONT_PATH) -> Path:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise SystemExit('Le PDF demande WeasyPrint : python3 -m pip install weasyprint') from exc
    path = Path(sortie) / livre.pdf
    temp = path.with_suffix('.pdf.tmp')
    HTML(string=document(livre, font), base_url=str(FONTS)).write_pdf(temp)
    temp.replace(path)
    print('PDF :', path, '|', livre.version.libelle, '|', len(livre.chapters), 'chapitres')
    return path
