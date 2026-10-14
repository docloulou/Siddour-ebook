"""Site web de lecture (GitHub Pages) : les trois éditions consultables dans un navigateur.

Arborescence produite :
    index.html                         accueil : couvertures, lecture en ligne, téléchargements
    <mode>/index.html                  sommaire de l'édition
    <mode>/<chapitre>/<section>.html   une page par section, comme dans l'EPUB
    telecharger/*.epub, assets/, sitemap.xml, robots.txt, 404.html
Les ancres internes (notes, « Suite de la prière ») restent propres à chaque page.
"""
from __future__ import annotations

import html
import io
import json
import re
import shutil
import unicodedata
from pathlib import Path

from .edition import (CSS, DESCRIPTION, FONT_PATH, INTRODUCTION, SUBJECTS, TITLES, Livre, cover_image,
                      exposants, make_contents, make_credits)
from .version import date_fr

SITE_NAME = 'Siddour séfarade'
TAGLINE = 'Le livre de prière du rite séfarade (Edot HaMizrah), à lire en ligne ou sur liseuse'
SITE_DESCRIPTION = ('Siddour séfarade complet (Edot HaMizrah) à lire en ligne ou à télécharger en EPUB : '
                    'hébreu vocalisé, phonétique ou les deux, avec les consignes en français. '
                    'Prières de la semaine, Chabbat, fêtes, jeûnes, bénédictions et cycle de la vie.')
EDITIONS = {'hebreu': 'Édition hébraïque', 'phonetique': 'Édition phonétique',
            'bilingue': 'Édition hébreu et phonétique'}
TEXTE = {'hebreu': 'en hébreu vocalisé', 'phonetique': 'en phonétique',
         'bilingue': 'en hébreu vocalisé et en phonétique'}
MENU = {'hebreu': 'Hébreu', 'phonetique': 'Phonétique', 'bilingue': 'Bilingue'}
EPUB_NAME = 'siddour_liseuse_{}.epub'

WEB_CSS = '''
@font-face { font-family: "SiddurHebrew"; src: url("FONT_URL") format("truetype"); font-display: swap; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: #fbf9f4; color: #1d1d1d; font-size: 1.12em; }
main { max-width: 40em; margin: 0 auto; padding: 1em 1.2em 3em; background: #fff; }
a { color: #1f3a68; }
.site-head { background: #15284a; color: #f1e4bf; font: .95em/1.4 sans-serif; }
.site-head .inner { max-width: 44em; margin: 0 auto; padding: .6em 1.2em; display: flex; flex-wrap: wrap;
                    gap: .4em 1.2em; align-items: baseline; }
.site-head a { color: #f1e4bf; text-decoration: none; }
.site-head .marque { font-weight: bold; margin-right: auto; }
.site-head .actif { text-decoration: underline; }
.fil { font: .85em sans-serif; color: #666; margin: .6em 0 0; }
.fil a { color: #666; }
.pager { display: flex; justify-content: space-between; gap: 1em; margin: 2.5em 0 0; padding-top: 1em;
         border-top: 1px solid #ddd; font: .92em/1.4 sans-serif; }
.pager a { text-decoration: none; max-width: 48%; }
.pager .suiv { margin-left: auto; text-align: right; }
.site-foot { max-width: 40em; margin: 0 auto; padding: 1.2em; font: .8em/1.5 sans-serif; color: #666;
             text-align: center; }
.editions { display: grid; grid-template-columns: repeat(auto-fit, minmax(11em, 1fr)); gap: 1.4em; margin: 1.5em 0; }
.edition-carte { text-align: center; font-family: sans-serif; }
.edition-carte img { width: 100%; height: auto; border-radius: 4px; box-shadow: 0 2px 10px rgba(0,0,0,.25); }
.edition-carte h2 { border: 0; font-size: 1.02em; margin: .6em 0 .2em; }
.edition-carte p { margin: .25em 0; font-size: .9em; }
.bouton { display: inline-block; padding: .35em .9em; border-radius: 3px; background: #15284a; color: #f1e4bf;
          text-decoration: none; }
.bouton.second { background: none; color: #15284a; border: 1px solid #15284a; }
.accroche { text-align: center; font-style: italic; color: #444; }
@media (max-width: 34em) { .sommaire { column-count: 1; -webkit-column-count: 1; } body { font-size: 1.05em; }
                           .site-head .marque { flex-basis: 100%; } }
'''


def slug(text: str) -> str:
    text = unicodedata.normalize('NFKD', text.replace('’', '').replace("'", ''))
    text = ''.join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-') or 'section'


def web_html(content: str) -> str:
    """Le XHTML des sections, avec les rôles ARIA du web à la place des attributs EPUB."""
    content = content.replace('epub:type="noteref"', 'role="doc-noteref"')
    content = content.replace('epub:type="footnote"', 'role="doc-footnote"')
    return re.sub(r'\sepub:type="[^"]*"', '', content)


class Site:
    def __init__(self, livres: list[Livre], dossier: Path, url: str):
        self.livres, self.dossier, self.url = livres, dossier, url.rstrip('/') + '/' if url else ''
        self.version = livres[0].version
        self.pages: list[str] = []  # chemins pour le sitemap

    def abs(self, path: str) -> str:
        return self.url + path if self.url else ''

    def write(self, path: str, title: str, description: str, body: str, *, mode: str = '',
              image: str = '', jsonld: list[dict] | None = None, index: bool = True) -> None:
        # La page 404 est servie à n'importe quelle profondeur : liens depuis la racine du site.
        root = '../' * path.count('/') if index or not self.url else self.url
        canonical = self.abs(path.removesuffix('index.html'))
        image = self.abs(image or 'assets/covers/' + (mode or 'bilingue') + '.jpg')
        nav = ''.join(
            '<a href="' + root + m + '/index.html"' + (' class="actif"' if m == mode else '') + '>'
            + MENU[m] + '</a>' for m in (lv.mode for lv in self.livres))
        head = [
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<title>' + html.escape(title) + '</title>',
            '<meta name="description" content="' + html.escape(description, quote=True) + '">',
            '<meta name="robots" content="' + ('index, follow' if index else 'noindex') + '">',
            '<meta name="theme-color" content="#15284a">',
            '<link rel="icon" type="image/png" href="' + root + 'assets/icone.png">',
            '<link rel="apple-touch-icon" href="' + root + 'assets/icone.png">',
            '<link rel="stylesheet" href="' + root + 'assets/style.css">',
            '<meta property="og:site_name" content="' + SITE_NAME + '">',
            '<meta property="og:locale" content="fr_FR">',
            '<meta property="og:type" content="' + ('book' if mode else 'website') + '">',
            '<meta property="og:title" content="' + html.escape(title, quote=True) + '">',
            '<meta property="og:description" content="' + html.escape(description, quote=True) + '">',
            '<meta name="twitter:card" content="summary">',
            '<meta name="twitter:title" content="' + html.escape(title, quote=True) + '">',
            '<meta name="twitter:description" content="' + html.escape(description, quote=True) + '">',
        ]
        if canonical:
            head += ['<link rel="canonical" href="' + canonical + '">',
                     '<meta property="og:url" content="' + canonical + '">']
        if image:
            head += ['<meta property="og:image" content="' + image + '">',
                     '<meta property="og:image:alt" content="Couverture du siddour">',
                     '<meta name="twitter:image" content="' + image + '">']
        if mode:
            head += ['<meta property="book:tag" content="' + html.escape(t, quote=True) + '">' for t in SUBJECTS]
        for data in jsonld or []:
            head.append('<script type="application/ld+json">'
                        + json.dumps(data, ensure_ascii=False).replace('</', '<\\/') + '</script>')
        page = ('<!doctype html>\n<html lang="fr">\n<head>\n' + '\n'.join(head) + '\n</head>\n<body>\n'
                '<header class="site-head"><div class="inner"><a class="marque" href="' + root + 'index.html">'
                + SITE_NAME + '</a>' + nav + '</div></header>\n<main>\n' + body + '\n</main>\n'
                '<footer class="site-foot"><p>' + exposants(self.version.complet) + ' · Textes issus de '
                '<a href="https://www.sefaria.org">Sefaria</a> · '
                '<a href="' + root + 'index.html#telecharger">Télécharger les EPUB</a></p></footer>\n'
                '</body>\n</html>\n')
        target = self.dossier / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding='utf-8')
        if index:
            self.pages.append(path)

    # -- Données structurées (schema.org) -------------------------------------------------
    def book_jsonld(self, livre: Livre) -> dict:
        data = {
            '@type': 'Book', 'name': livre.title, 'bookFormat': 'https://schema.org/EBook',
            'inLanguage': ['he', 'fr'] if livre.mode != 'phonetique' else ['fr', 'he'],
            'genre': 'Liturgie juive', 'keywords': ', '.join(SUBJECTS),
            'description': DESCRIPTION[livre.mode], 'version': livre.version.libelle,
            'datePublished': livre.version.jour.isoformat(), 'isAccessibleForFree': True,
            'publisher': {'@type': 'Organization', 'name': 'Siddour-ebook'},
            'isBasedOn': {'@type': 'Book', 'name': 'Siddur Edot HaMizrach', 'url': 'https://www.sefaria.org'},
        }
        if self.url:
            data['url'] = self.abs(livre.mode + '/')
            data['image'] = self.abs('assets/covers/' + livre.mode + '.jpg')
            data['encoding'] = {'@type': 'MediaObject', 'encodingFormat': 'application/epub+zip',
                                'contentUrl': self.abs('telecharger/' + EPUB_NAME.format(livre.mode))}
        return data

    def breadcrumb(self, items: list[tuple[str, str]]) -> dict:
        return {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            dict({'@type': 'ListItem', 'position': i, 'name': name},
                 **({'item': self.abs(path)} if self.url else {}))
            for i, (name, path) in enumerate(items, 1)]}

    # -- Pages -----------------------------------------------------------------------------
    def edition(self, livre: Livre) -> None:
        mode = livre.mode
        # Chemins des sections : <chapitre>/<titre>.html, uniques dans le chapitre.
        chapitres = []
        for chap, sections in livre.chapters:
            vus: set[str] = set()
            liens = []
            for title, content in sections:
                nom = slug(title)
                while nom in vus:
                    nom += '-2'
                vus.add(nom)
                liens.append((chap['id'] + '/' + nom + '.html', title, content))
            chapitres.append((chap, liens))
        sequence = [(chap, href, title, content) for chap, liens in chapitres for href, title, content in liens]
        premiere = {chap['id']: liens[0][0] for chap, liens in chapitres}

        book = dict(self.book_jsonld(livre), **{'@context': 'https://schema.org'})
        sommaire = make_contents([(chap['fr'], chap.get('he', ''), [(h, t) for h, t, _ in liens])
                                  for chap, liens in chapitres])
        intro = ('<p class="accroche">' + exposants(livre.version.complet) + '</p>'
                 '<p style="text-align:center"><a class="bouton" href="' + sequence[0][1] + '">Commencer la lecture</a> '
                 '<a class="bouton second" href="../telecharger/' + EPUB_NAME.format(mode) + '" download>'
                 'Télécharger l’EPUB</a></p>')
        self.write(mode + '/index.html', livre.title + ' — lire en ligne',
                   'Sommaire du siddour séfarade ' + TEXTE[mode] + ', avec consignes en français : '
                   + ', '.join(chap['fr'] for chap, _ in chapitres[:8]) + '…',
                   intro + sommaire + '<p style="text-align:center"><a href="a-propos.html">'
                   'À propos de cette édition</a></p>',
                   mode=mode, jsonld=[book, self.breadcrumb([(SITE_NAME, ''), (EDITIONS[mode], mode + '/')])])
        self.write(mode + '/a-propos.html', 'À propos — ' + livre.title,
                   'Sources, licences et conventions de mise en page de l’édition ' + TITLES[mode] + ' du siddour.',
                   web_html(make_credits(livre.title, livre.licences, mode, livre.version)), mode=mode)

        for k, (chap, href, title, content) in enumerate(sequence):
            prev = sequence[k - 1] if k else None
            nxt = sequence[k + 1] if k + 1 < len(sequence) else None
            up = '../' * href.count('/')
            # Le chapitre en titre de chaque page : repère pour le lecteur comme pour les moteurs.
            heading = ('<h1>' + html.escape(chap['fr'])
                       + ('<br><small lang="he" dir="rtl">' + html.escape(chap['he']) + '</small>' if chap.get('he') else '')
                       + '</h1>')
            autres = ' · '.join('<a href="' + up + '../' + m + '/' + href + '">' + html.escape(TITLES[m]) + '</a>'
                                for m in (lv.mode for lv in self.livres) if m != mode)
            fil = ('<p class="fil"><a href="' + up + 'index.html">' + EDITIONS[mode] + '</a> › '
                   + html.escape(chap['fr']) + (' · Aussi en ' + autres if autres else '') + '</p>')
            pager = '<nav class="pager">' + (
                '<a class="prec" rel="prev" href="' + up + prev[1] + '">← ' + html.escape(prev[2]) + '</a>' if prev else '') + (
                '<a class="suiv" rel="next" href="' + up + nxt[1] + '">' + html.escape(nxt[2]) + ' →</a>' if nxt else '') + '</nav>'
            page_title = title + (' — ' + chap['fr'] if title != chap['fr'] else '') + ' | ' + livre.title
            description = ('« ' + title + ' » (' + chap['fr'] + ') : texte du siddour séfarade Edot HaMizrah '
                           + TEXTE[mode] + ', avec les consignes en français. Lecture en ligne ou EPUB.')
            jsonld = [self.breadcrumb([(SITE_NAME, ''), (EDITIONS[mode], mode + '/'),
                                       (chap['fr'], mode + '/' + premiere[chap['id']]), (title, mode + '/' + href)]),
                      {'@context': 'https://schema.org', '@type': 'WebPage', 'name': title,
                       'inLanguage': 'fr', 'isPartOf': self.book_jsonld(livre)}]
            self.write(mode + '/' + href, page_title, description, fil + heading + web_html(content) + pager,
                       mode=mode, jsonld=jsonld)

    def accueil(self) -> None:
        cartes = ''.join(
            '<div class="edition-carte"><a href="' + lv.mode + '/index.html"><img src="assets/covers/' + lv.mode
            + '.jpg" alt="Couverture : ' + html.escape(lv.title, quote=True) + '" width="400" height="600"'
            + (' loading="lazy"' if i else '') + '></a><h2>' + EDITIONS[lv.mode] + '</h2>'
            '<p>Textes ' + TEXTE[lv.mode] + '</p>'
            '<p><a class="bouton" href="' + lv.mode + '/index.html">Lire en ligne</a></p>'
            '<p><a href="telecharger/' + EPUB_NAME.format(lv.mode) + '" download>Télécharger l’EPUB</a></p></div>'
            for i, lv in enumerate(self.livres))
        body = ('<h1>' + SITE_NAME + '</h1><p class="accroche">' + TAGLINE + '</p>'
                '<section id="telecharger"><div class="editions">' + cartes + '</div>'
                '<p class="accroche">' + exposants(self.version.complet) + '</p></section>'
                + web_html(INTRODUCTION).replace('<h1>', '<h2>').replace('</h1>', '</h2>'))
        site = {'@context': 'https://schema.org', '@type': 'WebSite', 'name': SITE_NAME,
                'description': SITE_DESCRIPTION, 'inLanguage': 'fr'}
        if self.url:
            site['url'] = self.url
        work = {'@context': 'https://schema.org', '@type': 'Book', 'name': 'Siddour séfarade (Edot HaMizrah)',
                'description': SITE_DESCRIPTION, 'genre': 'Liturgie juive', 'keywords': ', '.join(SUBJECTS),
                'workExample': [self.book_jsonld(lv) for lv in self.livres]}
        self.write('index.html', SITE_NAME + ' — siddour Edot HaMizrah en ligne et en EPUB',
                   SITE_DESCRIPTION, body, jsonld=[site, work])
        self.write('404.html', 'Page introuvable — ' + SITE_NAME, SITE_DESCRIPTION,
                   '<h1>Page introuvable</h1><p style="text-align:center">'
                   '<a class="bouton" href="' + (self.url or 'index.html') + '">Retour à l’accueil</a></p>', index=False)

    def assets(self, sortie: Path) -> None:
        from PIL import Image
        dossier = self.dossier / 'assets'
        (dossier / 'covers').mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FONT_PATH, dossier / FONT_PATH.name)
        # Feuille du livre d'abord, puis les règles propres au web qui la complètent.
        font_face, web = WEB_CSS.replace('FONT_URL', FONT_PATH.name).split('\n', 2)[1:]
        (dossier / 'style.css').write_text(font_face + '\n' + CSS + web, encoding='utf-8')
        for lv in self.livres:
            cover = cover_image(lv.mode)
            if not cover:
                continue
            with Image.open(io.BytesIO(cover[1])) as im:
                im = im.convert('RGB')
                im.thumbnail((800, 1200))
                im.save(dossier / 'covers' / (lv.mode + '.jpg'), 'JPEG', quality=85, optimize=True, progressive=True)
                if not (dossier / 'icone.png').exists():
                    # Icône : le haut de la couverture (le titre), en carré.
                    w = im.width
                    im.crop((0, 0, w, w)).resize((192, 192), Image.LANCZOS).save(dossier / 'icone.png', optimize=True)
        telecharger = self.dossier / 'telecharger'
        telecharger.mkdir(exist_ok=True)
        for lv in self.livres:
            shutil.copyfile(sortie / EPUB_NAME.format(lv.mode), telecharger / EPUB_NAME.format(lv.mode))
        (self.dossier / '.nojekyll').write_text('', encoding='utf-8')

    def index_moteurs(self) -> None:
        lignes = ['User-agent: *', 'Allow: /']
        if self.url:
            jour = self.version.jour.isoformat()
            urls = ''.join('<url><loc>' + html.escape(self.abs(p.removesuffix('index.html'))) + '</loc><lastmod>'
                           + jour + '</lastmod></url>\n' for p in self.pages)
            (self.dossier / 'sitemap.xml').write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '</urlset>\n',
                encoding='utf-8')
            lignes.append('Sitemap: ' + self.abs('sitemap.xml'))
        (self.dossier / 'robots.txt').write_text('\n'.join(lignes) + '\n', encoding='utf-8')


def build_site(livres: list[Livre], dossier: Path, sortie: Path, url: str = '') -> Path:
    if dossier.exists():
        shutil.rmtree(dossier)
    dossier.mkdir(parents=True)
    site = Site(livres, dossier, url)
    site.assets(sortie)
    for livre in livres:
        site.edition(livre)
    site.accueil()
    site.index_moteurs()
    print('Site :', dossier, '|', len(site.pages), 'pages', '|', date_fr(site.version.jour))
    return dossier
