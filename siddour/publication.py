"""Outils de publication utilisés par l'action GitHub « Publier les EPUB ».

    python3 -m siddour.publication suivante --increment revision
    python3 -m siddour.publication actuelle
    python3 -m siddour.publication readme --tag edition-1-revision-0 --depot owner/repo --date 2026-10-14
"""
from __future__ import annotations

import argparse
import re
import subprocess
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .version import TAG_RE, Version, suivante

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / 'README.md'
DEBUT, FIN = '<!-- publication:debut -->', '<!-- publication:fin -->'
LIVRES = [('Édition hébraïque', 'siddour_liseuse_hebreu.epub'),
          ('Édition phonétique', 'siddour_liseuse_phonetique.epub'),
          ('Édition hébreu puis phonétique', 'siddour_liseuse_bilingue.epub')]


def bloc_readme(version: Version, depot: str, site: str = '') -> str:
    base = 'https://github.com/' + depot + '/releases/download/' + version.tag + '/'
    liens = '\n'.join('- [' + nom + '](' + base + fichier + ')' for nom, fichier in LIVRES)
    return (DEBUT + '\n## Télécharger\n\n**' + version.complet + '** · '
            '[notes de publication](https://github.com/' + depot + '/releases/tag/' + version.tag + ')'
            ' · [toutes les éditions](https://github.com/' + depot + '/releases)\n\n'
            + liens + '\n'
            + ('\n📖 [Lire en ligne dans le navigateur](' + site.rstrip('/') + '/)\n' if site else '') + FIN)


def mettre_a_jour_readme(version: Version, depot: str, site: str = '') -> None:
    texte = README.read_text(encoding='utf-8')
    bloc = bloc_readme(version, depot, site)
    if DEBUT in texte:
        texte = re.sub(re.escape(DEBUT) + '.*?' + re.escape(FIN), lambda _: bloc, texte, flags=re.S)
    else:
        # Première publication : le bloc se place juste sous le titre.
        titre, _, reste = texte.partition('\n')
        texte = titre + '\n\n' + bloc + '\n' + reste
    README.write_text(texte, encoding='utf-8')


def git(*args: str) -> str:
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def actuelle(tags: list[str]) -> Version:
    """Dernière publication, datée du jour de son étiquette (heure de Paris)."""
    connues = sorted((int(m[1]), int(m[2]), m[0]) for m in map(TAG_RE.match, tags) if m)
    if not connues:
        raise SystemExit('Aucune édition publiée : lancer d’abord « Publier les EPUB ».')
    edition, revision, tag = connues[-1]
    quand = datetime.fromisoformat(git('log', '-1', '--format=%cI', tag).strip())
    return Version(edition, revision, quand.astimezone(ZoneInfo('Europe/Paris')).date())


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='commande', required=True)
    s = sub.add_parser('suivante', help='calcule le numéro de la prochaine publication')
    s.add_argument('--increment', choices=['revision', 'edition'], required=True)
    sub.add_parser('actuelle', help='numéro et date de la dernière publication, pour republier le site')
    r = sub.add_parser('readme', help='met à jour les liens de téléchargement du README')
    r.add_argument('--tag', required=True)
    r.add_argument('--depot', required=True, help='propriétaire/dépôt')
    r.add_argument('--date', type=date.fromisoformat, default=date.today())
    r.add_argument('--site', default='', help='adresse du site de lecture en ligne')
    args = ap.parse_args(argv)

    if args.commande in ('suivante', 'actuelle'):
        tags = git('tag', '--list', 'edition-*').split()
        v = suivante(tags, args.increment) if args.commande == 'suivante' else actuelle(tags)
        # Format clé=valeur, directement ajoutable à $GITHUB_OUTPUT.
        print(f'edition={v.edition}\nrevision={v.revision}\ntag={v.tag}\nlibelle={v.libelle}')
        if args.commande == 'actuelle':
            print('date=' + v.jour.isoformat())
    else:
        m = TAG_RE.match(args.tag)
        if not m:
            raise SystemExit('Étiquette attendue : edition-<N>-revision-<M>')
        mettre_a_jour_readme(Version(int(m[1]), int(m[2]), args.date), args.depot, args.site)


if __name__ == '__main__':
    main()
