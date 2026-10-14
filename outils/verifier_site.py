"""Vérifie le site de lecture et l'application installable (PWA).

    python3 outils/verifier_site.py

Fabrique le site dans un dossier temporaire, servi sous /Siddour-ebook/ comme sur
GitHub Pages, puis contrôle :
1. les liens internes et les fichiers listés dans le service worker ;
2. avec Playwright (facultatif : pip install playwright) :
   - les critères d'installation de Chrome ;
   - la mise en cache « Garder hors ligne » et la lecture serveur arrêté ;
   - la mise à jour automatique après une nouvelle révision ;
   - l'aide à l'installation affichée sur iPhone ;
   - la barre des sections qui suit le défilement et les réglages d'affichage.
Le script s'arrête à la première erreur.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
PORT = 8765
BASE = f'http://localhost:{PORT}/Siddour-ebook/'
CHROMIUM = '/opt/pw-browsers/chromium'  # navigateur préinstallé dans certains environnements


def fabriquer(dossier: Path, revision: int, jour: str) -> None:
    subprocess.run([sys.executable, 'siddour_ebook_liseuse.py', '--offline', '--sortie', str(dossier / 'epub'),
                    '--site', str(dossier / 'www' / 'Siddour-ebook'), '--site-url', BASE,
                    '--edition', '1', '--revision', str(revision), '--date', jour],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)


def verifier_liens(site: Path) -> None:
    liens = 0
    for page in site.rglob('*.html'):
        for lien in re.findall(r'(?:href|src)="([^"#]+)', page.read_text(encoding='utf-8')):
            adresse = urljoin(BASE + page.relative_to(site).as_posix(), lien)
            if not adresse.startswith(BASE):
                continue
            cible = site / urlparse(adresse).path[len(urlparse(BASE).path):]
            if cible.is_dir():
                cible /= 'index.html'
            assert cible.exists(), f'lien cassé dans {page.relative_to(site)} : {lien}'
            liens += 1
    sw = (site / 'sw.js').read_text(encoding='utf-8')
    for nom in ('COQUILLE', 'EDITIONS'):
        valeur = json.loads(re.search(nom + r' = (.*);', sw).group(1))
        for chemin in valeur if isinstance(valeur, list) else sum(valeur.values(), []):
            assert (site / chemin).exists(), f'{nom} : fichier absent {chemin}'
    print(f'✓ {liens} liens internes, fichiers du service worker présents')


def serveur(dossier: Path) -> subprocess.Popen:
    p = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT)], cwd=dossier / 'www',
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    return p


def arreter(p: subprocess.Popen) -> None:
    p.kill()
    p.wait()
    time.sleep(.5)


def verifier_pwa(dossier: Path) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('· Playwright absent : vérifications de la PWA ignorées')
        return
    options = {'executable_path': CHROMIUM} if os.path.exists(CHROMIUM) else {}
    srv = serveur(dossier)
    try:
        with sync_playwright() as p:
            # Profil persistant : Chrome refuse l'installation en navigation privée.
            ctx = p.chromium.launch_persistent_context(str(dossier / 'profil'), viewport={'width': 420, 'height': 800},
                                                       **options)
            pg = ctx.new_page()
            pg.goto(BASE + 'bilingue/index.html')
            pg.wait_for_function('navigator.serviceWorker.controller !== null', timeout=20000)
            cdp = ctx.new_cdp_session(pg)
            erreurs = cdp.send('Page.getInstallabilityErrors')['installabilityErrors']
            assert not erreurs, erreurs
            assert not cdp.send('Page.getAppManifest').get('errors'), 'manifeste invalide'
            print('✓ installable (manifeste, icônes, service worker)')

            pg.wait_for_selector('[data-hors-ligne]:not([hidden])')
            pg.click('[data-hors-ligne]')
            pg.wait_for_function('document.querySelector(".hors-ligne span").textContent.startsWith("✓")',
                                 timeout=60000)
            sections = pg.eval_on_selector_all('.sommaire a', 'a => a.map(x => x.getAttribute("href"))')
            arreter(srv)
            for adresse in (BASE, BASE + 'bilingue/' + sections[len(sections) // 2], BASE + 'hebreu/index.html'):
                pg.goto(adresse)
                assert 'Hors connexion' not in pg.title(), adresse
            pg.goto(BASE + 'hebreu/' + sections[10])
            assert pg.title().startswith('Hors connexion'), 'page de secours attendue'
            print('✓ lecture hors connexion (édition gardée, page de secours)')

            srv = serveur(dossier)
            fabriquer(dossier, 1, '2026-01-02')
            pg.goto(BASE + 'bilingue/index.html')
            pg.wait_for_selector('.annonce', timeout=30000)
            assert 'révision 1' in pg.text_content('.annonce')
            assert len([c for c in pg.evaluate('caches.keys()') if c != 'siddour-reglages']) == 1, 'ancien cache'
            arreter(srv)
            pg.goto(BASE + 'bilingue/' + sections[-1])
            assert 'révision 1' in pg.text_content('.site-foot'), 'édition gardée non mise à jour'
            print('✓ mise à jour automatique :', pg.evaluate('caches.keys()'))
            ctx.close()

            srv = serveur(dossier)
            iphone = p.chromium.launch(**options).new_context(**p.devices['iPhone 13'])
            pg = iphone.new_page()
            pg.goto(BASE)
            assert pg.is_visible('.installer-ios'), 'aide à l’installation iOS absente'
            assert pg.locator('link[rel=apple-touch-startup-image]').count() > 0
            print('✓ iPhone : aide à l’installation, écrans de démarrage déclarés')

            pg.goto(BASE + 'bilingue/' + sections[3])  # section longue : la page défile
            pg.evaluate('scrollTo(0, document.body.scrollHeight)')
            assert pg.evaluate('scrollY > 300 && document.querySelector(".barre").getBoundingClientRect().top === 0'), \
                'barre non collée'
            pg.click('.barre .aa')
            pg.click('[data-cle=fond][data-v=papier]')
            pg.click('[data-cle=ph][data-v=center]')
            pg.click('[data-pas="1"]')
            pg.reload()  # réglages gardés et appliqués dès le chargement
            assert pg.eval_on_selector('main .ph', 'p => getComputedStyle(p).textAlign') == 'center'
            assert pg.evaluate('document.documentElement.dataset.fond') == 'papier'
            pg.select_option('.barre select', index=0)
            pg.wait_for_url('**/' + sections[0].split('#')[0])
            print('✓ barre des sections collée, réglages d’affichage gardés')
    finally:
        arreter(srv)


def main() -> None:
    with socket.socket() as s:
        # Un autre serveur sur ce port fausserait les essais hors connexion.
        if s.connect_ex(('localhost', PORT)) == 0:
            raise SystemExit(f'Le port {PORT} est déjà utilisé : arrêter le serveur qui l’occupe.')
    with tempfile.TemporaryDirectory() as tmp:
        dossier = Path(tmp)
        fabriquer(dossier, 0, '2026-01-01')
        verifier_liens(dossier / 'www' / 'Siddour-ebook')
        verifier_pwa(dossier)


if __name__ == '__main__':
    main()
