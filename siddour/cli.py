"""Ligne de commande : python3 siddour_ebook_liseuse.py --help"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .consignes import Consignes
from .edition import FONT_PATH, build_edition, render_book
from .phonetique import INCONNUS, PRONONCIATIONS, translit
from .plan import select_plan
from .rites import RITES
from .site import DEPOT
from .sources import fetch_section, validate_source
from .version import Version

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description='Siddour séfarade et ashkénaze : hébreu, phonétique et bilingue, '
                                             'avec consignes françaises intégrées.')
    ap.add_argument('--rite', choices=['tous', *RITES], default='tous',
                    help='tous génère les éditions des deux rites (défaut)')
    ap.add_argument('--mode', choices=['tous', 'hebreu', 'phonetique', 'bilingue'], default='tous',
                    help='tous génère les trois ePub de chaque rite (défaut)')
    ap.add_argument('--sortie', default='.', help='dossier de sortie')
    ap.add_argument('--cache', default=str(ROOT / 'cache'))
    ap.add_argument('--offline', action='store_true', help='utiliser uniquement les textes déjà mis en cache')
    ap.add_argument('--quotidien', action='store_true',
                    help='limiter aux chapitres quotidiens ; tout le plan est inclus par défaut')
    ap.add_argument('--complet', action='store_true', help='inclure tout le plan (déjà le comportement par défaut)')
    ap.add_argument('--chapitres', help='identifiants de chapitres séparés par des virgules')
    ap.add_argument('--liste', action='store_true')
    ap.add_argument('--rubriques', help='CSV facultatif de corrections : hebreu;francais')
    ap.add_argument('--font', help='police .ttf ou .otf à embarquer')
    ap.add_argument('--html', action='store_true', help='produire aussi les versions HTML pour relecture')
    ap.add_argument('--edition', type=int, help='numéro d’édition imprimé dans le livre (sinon « Version de travail »)')
    ap.add_argument('--revision', type=int, default=0, help='numéro de révision de cette édition (défaut : 0)')
    ap.add_argument('--date', type=date.fromisoformat, default=date.today(),
                    help='date de fabrication AAAA-MM-JJ (défaut : aujourd’hui)')
    ap.add_argument('--site', metavar='DOSSIER', help='produire aussi le site web de lecture (GitHub Pages)')
    ap.add_argument('--depot', default=DEPOT,
                    help='dépôt GitHub (propriétaire/dépôt) cité dans le pied de page du site')
    ap.add_argument('--site-url', default='', help='adresse publique du site, pour les liens canoniques et le sitemap (https://sidour.page/)')
    ap.add_argument('--translit', metavar='TEXTE', help='tester la phonétique et quitter')
    ap.add_argument('--prononciation', choices=list(PRONONCIATIONS),
                    help='prononciation de --translit (défaut : celle du rite choisi, sinon sefarade)')
    args = ap.parse_args(argv)

    rites = list(RITES.values()) if args.rite == 'tous' else [RITES[args.rite]]
    if args.liste:
        for rite in rites:
            print('#', rite.libelle)
            for c in rite.plan:
                print(c['id'], ':', c['fr'], '(' + str(len(c['sections'])) + ' sections)')
        return
    if args.translit:
        print(translit(args.translit, prononciation=args.prononciation or rites[0].prononciation))
        return

    consignes = Consignes()
    consignes.load_overrides(args.rubriques)
    plans = {}
    for rite in rites:
        plans[rite.code] = select_plan(args.chapitres, not args.quotidien, rite.plan, strict=len(rites) == 1)
    if args.chapitres and not any(plans.values()):
        select_plan(args.chapitres, not args.quotidien, rites[0].plan)  # message d'erreur habituel
    sources: dict[str, dict[str, dict]] = {}
    failures = []
    for rite in rites:
        sources[rite.code] = {}
        for chap in plans[rite.code]:
            for _, ref in chap['sections']:
                try:
                    data = fetch_section(ref, Path(args.cache), args.offline, rite.livre)
                    validate_source(data, ref)
                    sources[rite.code][ref] = data
                except Exception as exc:
                    failures.append(rite.adjectif + ', ' + ref + ' : ' + str(exc))
    if failures:
        raise SystemExit('Aucun ePub produit, pour éviter une édition incomplète :\n' + '\n'.join(failures))

    font = Path(args.font) if args.font else FONT_PATH
    sortie = Path(args.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    modes = ['hebreu', 'phonetique', 'bilingue'] if args.mode == 'tous' else [args.mode]
    version = Version(args.edition, args.revision, args.date)
    livres = []
    for rite in rites:
        if not plans[rite.code]:
            continue
        for mode in modes:
            livre = render_book(plans[rite.code], sources[rite.code], mode, consignes, version, rite)
            build_edition(livre, sortie, font, args.html)
            livres.append(livre)
    if args.site:
        from .site import build_site
        build_site(livres, Path(args.site), sortie, args.site_url, args.depot)
    cp = sortie / 'rubriques_traduites.csv'
    consignes.export(cp)
    print('CSV :', cp)
    if INCONNUS:
        # Mots que la phonétique n'a pu lire (non vocalisés, absents de ses tables) : à corriger
        # dans phonetique.PH_WORDS ou LECTURES.
        print('Phonétique : ' + str(len(INCONNUS)) + ' mots sans lecture fiable, dont '
              + ', '.join(mot + ' (' + str(n) + ')' for mot, n in INCONNUS.most_common(12)))
