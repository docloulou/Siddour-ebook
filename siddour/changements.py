"""Suivi des modifications du contenu des livres : changesets, journal et CHANGELOG.

Chaque modification du contenu (texte récité, consignes, phonétique, plan, présentation des
pages du livre) s'accompagne d'un changeset : un petit fichier .changeset/<nom>.md qui dit
ce qui change et où (rites, éditions, chapitres). Les changements d'architecture (site,
action de publication, outils) n'en demandent pas.

À la publication, l'action « Publier les EPUB » reporte les changesets en attente dans
data/changelog.json sous le numéro de la nouvelle édition, régénère CHANGELOG.md et efface
les fichiers reportés. Le journal alimente ensuite la page « Modifications » du site et le
récapitulatif placé à la fin de chaque EPUB et PDF.

    python3 -m siddour.changements verifier [--base origin/main]
    python3 -m siddour.changements publier --tag edition-1-revision-5 --date 2026-10-20
    python3 -m siddour.changements notes --tag edition-1-revision-5
    python3 -m siddour.changements changelog
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from .rites import RITES, Rite
from .version import TAG_RE, Version, date_fr

ROOT = Path(__file__).resolve().parent.parent
DOSSIER = ROOT / '.changeset'
JOURNAL = ROOT / 'data' / 'changelog.json'
CHANGELOG = ROOT / 'CHANGELOG.md'
MODES = {'hebreu': 'hébreu', 'phonetique': 'phonétique', 'bilingue': 'bilingue'}
NIVEAUX = ('revision', 'edition')
LIMITE_RESUME = 160
# Fichiers dont une modification change le contenu des livres : une pull request qui en touche
# un doit ajouter un changeset (étiquette « sans-changeset » pour un simple remaniement du code).
CONTENU = ('cache/', 'data/consignes.csv', 'data/consignes_locales.csv', 'data/intertitres.csv',
           'assets/covers/', 'assets/fonts/', 'siddour/plan.py', 'siddour/plan_ashkenaze.py',
           'siddour/sources.py', 'siddour/consignes.py', 'siddour/mise_en_page.py', 'siddour/phonetique.py',
           'siddour/hebreu.py', 'siddour/rites.py', 'siddour/edition.py', 'siddour/pdf.py', 'siddour/style.css')


@dataclass(frozen=True)
class Changement:
    resume: str                 # une phrase, reprise telle quelle à la fin des livres
    details: str = ''           # paragraphes facultatifs : CHANGELOG, site et notes de release
    niveau: str = 'revision'    # revision : correction ; edition : changement important
    rites: tuple = ()           # vide : les deux rites
    editions: tuple = ()        # vide : les trois éditions
    chapitres: tuple = ()       # identifiants du plan ; vide : tout le livre

    def concerne(self, rite: Rite, mode: str) -> bool:
        if self.rites and rite.code not in self.rites:
            return False
        if self.editions and mode not in self.editions:
            return False
        return not self.chapitres or any(c['id'] in self.chapitres for c in rite.plan)

    def noms_chapitres(self, rite: Rite | None = None) -> list[str]:
        """Noms des chapitres touchés, dans l'ordre du plan ; ceux d'un rite seulement si demandé."""
        rites = [rite] if rite else [r for r in RITES.values() if not self.rites or r.code in self.rites]
        noms: dict[str, str] = {}
        for r in rites:
            for c in r.plan:
                if c['id'] in self.chapitres:
                    noms.setdefault(c['id'], c['fr'])
        return list(noms.values())

    def perimetre(self) -> str:
        """« Rite séfarade · éditions phonétique et bilingue · Prière du matin, Prière du soir »."""
        rites = ('rite ' + RITES[self.rites[0]].adjectif if len(self.rites) == 1
                 else 'les deux rites')
        if not self.editions or len(self.editions) == len(MODES):
            editions = 'toutes les éditions'
        else:
            noms = [MODES[m] for m in MODES if m in self.editions]
            editions = 'édition ' + noms[0] if len(noms) == 1 else 'éditions ' + ' et '.join(noms)
        chapitres = ', '.join(self.noms_chapitres()) if self.chapitres else 'tout le livre'
        return ' · '.join((rites, editions, chapitres))

    def json(self) -> dict:
        d = asdict(self)
        return {k: list(v) if isinstance(v, tuple) else v for k, v in d.items() if v or k == 'resume'}


@dataclass(frozen=True)
class Publication:
    tag: str
    jour: date
    changements: list

    @property
    def version(self) -> Version:
        m = TAG_RE.match(self.tag)
        return Version(int(m[1]), int(m[2]), self.jour)


def _liste(valeur: str) -> tuple:
    valeur = valeur.strip()
    if valeur.lower() in ('', 'tous', 'toutes', 'tout'):
        return ()
    return tuple(dict.fromkeys(v.strip() for v in valeur.split(',') if v.strip()))


def valider(ch: Changement, origine: str) -> Changement:
    erreurs = []
    if not ch.resume:
        erreurs.append('résumé manquant (première ligne après l’en-tête)')
    elif len(ch.resume) > LIMITE_RESUME:
        erreurs.append(f'résumé trop long ({len(ch.resume)} caractères, {LIMITE_RESUME} au plus)')
    if ch.niveau not in NIVEAUX:
        erreurs.append('niveau inconnu : ' + ch.niveau + ' (revision ou edition)')
    erreurs += ['rite inconnu : ' + r for r in ch.rites if r not in RITES]
    erreurs += ['édition inconnue : ' + m for m in ch.editions if m not in MODES]
    rites = [r for r in RITES.values() if not ch.rites or r.code in ch.rites]
    connus = {c['id'] for r in rites for c in r.plan}
    erreurs += ['chapitre inconnu de ce périmètre : ' + c for c in ch.chapitres if c not in connus]
    if erreurs:
        raise ValueError(origine + ' : ' + ' ; '.join(erreurs))
    return ch


def lire(path: Path) -> Changement:
    """Lit un changeset : en-tête « clé: valeur » entre deux lignes ---, puis résumé et détails."""
    texte = path.read_text(encoding='utf-8').replace('\r\n', '\n')
    m = re.match(r'---\n(.*?)^---[ \t]*(?:\n|$)(.*)', texte, re.S | re.M)
    if not m:
        raise ValueError(str(path) + ' : en-tête --- … --- attendu en tête du fichier')
    champs = {}
    for ligne in m[1].splitlines():
        if not ligne.strip() or ligne.lstrip().startswith('#'):
            continue
        cle, sep, valeur = ligne.partition(':')
        cle = cle.strip().lower()
        if not sep or cle not in ('niveau', 'rites', 'editions', 'chapitres'):
            raise ValueError(str(path) + ' : ligne d’en-tête inconnue : ' + ligne)
        champs[cle] = valeur.strip()
    paragraphes = [p.strip() for p in re.split(r'\n\s*\n', m[2].strip()) if p.strip()]
    resume = ' '.join(paragraphes[0].split()) if paragraphes else ''
    ch = Changement(resume, '\n\n'.join(paragraphes[1:]), champs.get('niveau', 'revision').lower(),
                    _liste(champs.get('rites', '')), _liste(champs.get('editions', '')),
                    _liste(champs.get('chapitres', '')))
    return valider(ch, str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path))


def fichiers_en_attente(dossier: Path = DOSSIER) -> list[Path]:
    return sorted(p for p in dossier.glob('*.md') if p.name.lower() != 'readme.md') if dossier.is_dir() else []


def en_attente(dossier: Path = DOSSIER) -> list[Changement]:
    return [lire(p) for p in fichiers_en_attente(dossier)]


def journal(chemin: Path = JOURNAL) -> list[Publication]:
    """Publications, la plus récente d'abord."""
    if not chemin.exists():
        return []
    pubs = []
    for p in json.loads(chemin.read_text(encoding='utf-8')):
        if not TAG_RE.match(p['tag']):
            raise ValueError(str(chemin) + ' : étiquette invalide ' + p['tag'])
        chs = [valider(Changement(c['resume'], c.get('details', ''), c.get('niveau', 'revision'),
                                  tuple(c.get('rites', ())), tuple(c.get('editions', ())),
                                  tuple(c.get('chapitres', ()))), p['tag']) for c in p['changements']]
        pubs.append(Publication(p['tag'], date.fromisoformat(p['date']), chs))
    return sorted(pubs, key=lambda p: (p.version.edition, p.version.revision), reverse=True)


def ecrire_journal(pubs: list[Publication], chemin: Path = JOURNAL) -> None:
    donnees = [{'tag': p.tag, 'date': p.jour.isoformat(), 'changements': [c.json() for c in p.changements]}
               for p in pubs]
    chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def historique(rite: Rite, mode: str, version: Version, nombre: int = 3,
               pubs: list[Publication] | None = None) -> list[tuple[str, list[Changement]]]:
    """Dernières publications qui touchent une édition, avec leurs changements, pour la fin du livre.

    Une version de travail montre d'abord les changesets en attente, pour la relecture.
    Une version publiée ne montre que les publications jusqu'à la sienne."""
    pubs = journal() if pubs is None else pubs
    lignes = []
    if version.edition is None:
        attente = [c for c in en_attente() if c.concerne(rite, mode)]
        if attente:
            lignes.append(('Version de travail (non publiée)', attente))
    for p in pubs:
        v = p.version
        if version.edition is not None and (v.edition, v.revision) > (version.edition, version.revision):
            continue
        chs = [c for c in p.changements if c.concerne(rite, mode)]
        if chs:
            lignes.append((v.complet, chs))
    return lignes[:nombre]


def markdown(p: Publication, titre: str = '##') -> str:
    lignes = [titre + ' ' + p.version.complet, '']
    for c in p.changements:
        lignes.append('- **' + c.resume + '** — ' + c.perimetre()
                      + (' *(nouvelle édition)*' if c.niveau == 'edition' else ''))
        if c.details:
            lignes += [''] + ['  ' + ligne if ligne else '' for ligne in c.details.splitlines()] + ['']
    return '\n'.join(lignes).rstrip() + '\n'


def ecrire_changelog(pubs: list[Publication], chemin: Path = CHANGELOG) -> None:
    entete = ('# Journal des modifications\n\n'
              'Les modifications du contenu des livres (textes, consignes, phonétique, plan, présentation), '
              'publication par publication. Les changements du site et des outils n’y figurent pas.\n\n'
              'Ce fichier est généré à partir de `data/changelog.json` à chaque publication : ne pas le modifier '
              'à la main. Les modifications pas encore publiées attendent dans `.changeset/` '
              '(voir `AGENTS.md`).\n')
    chemin.write_text(entete + ''.join('\n' + markdown(p) for p in pubs), encoding='utf-8')


def publier(version: Version, dossier: Path = DOSSIER, chemin: Path = JOURNAL, changelog: Path = CHANGELOG) -> Publication:
    """Reporte les changesets en attente sous le numéro de la publication et les efface."""
    fichiers = fichiers_en_attente(dossier)
    if not fichiers:
        raise SystemExit('Aucun changeset en attente dans .changeset/ : une nouvelle publication doit dire ce qui '
                         'change dans les livres (voir AGENTS.md). Pour corriger seulement le site, lancer '
                         '« Republier le site ».')
    chs = [lire(f) for f in fichiers]
    if version.revision and any(c.niveau == 'edition' for c in chs):
        raise SystemExit('Un changeset demande une nouvelle édition ; relancer la publication avec « edition ».')
    pubs = journal(chemin)
    if any(p.tag == version.tag for p in pubs):
        raise SystemExit('Le journal contient déjà ' + version.tag)
    pub = Publication(version.tag, version.jour, chs)
    pubs.insert(0, pub)
    ecrire_journal(pubs, chemin)
    ecrire_changelog(pubs, changelog)
    for f in fichiers:
        f.unlink()
    print('Journal :', version.libelle, '|', len(chs), 'modification' + ('s' if len(chs) > 1 else ''))
    return pub


def fichiers_modifies(base: str) -> list[tuple[str, str]]:
    sortie = subprocess.run(['git', 'diff', '--name-status', '--no-renames', base + '...HEAD'], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout
    return [tuple(ligne.split('\t', 1)) for ligne in sortie.splitlines() if '\t' in ligne]


def verifier(base: str | None = None) -> None:
    """Valide le journal et les changesets en attente ; avec une base Git, exige un changeset
    quand la branche touche au contenu des livres."""
    pubs = journal()
    chs = en_attente()
    print('Journal :', len(pubs), 'publications ;', len(chs), 'changeset' + ('s' if len(chs) > 1 else ''), 'en attente')
    if base is None:
        return
    modifies = fichiers_modifies(base)
    contenu = [f for _, f in modifies if f.startswith(CONTENU)]
    nouveaux = [f for statut, f in modifies if statut in ('A', 'M') and f.startswith('.changeset/')
                and f.endswith('.md') and Path(f).name.lower() != 'readme.md']
    if contenu and not nouveaux:
        raise SystemExit('Cette branche modifie le contenu des livres sans changeset :\n  '
                         + '\n  '.join(contenu[:15]) + ('\n  …' if len(contenu) > 15 else '')
                         + '\nAjouter un fichier .changeset/<nom>.md (voir AGENTS.md), ou poser l’étiquette '
                           '« sans-changeset » si le contenu des livres ne change pas.')
    print('Changesets de la branche :', ', '.join(nouveaux) if nouveaux else 'aucun (contenu inchangé)')


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description='Changesets et journal des modifications du contenu des livres.')
    sub = ap.add_subparsers(dest='commande', required=True)
    v = sub.add_parser('verifier', help='valide les changesets ; avec --base, exige un changeset si le contenu change')
    v.add_argument('--base', help='référence Git de comparaison, par exemple origin/main')
    p = sub.add_parser('publier', help='reporte les changesets en attente dans le journal, sous cette publication')
    p.add_argument('--tag', required=True)
    p.add_argument('--date', type=date.fromisoformat, default=date.today())
    n = sub.add_parser('notes', help='modifications d’une publication, en Markdown (notes de release)')
    n.add_argument('--tag', required=True)
    sub.add_parser('changelog', help='régénère CHANGELOG.md à partir du journal')
    args = ap.parse_args(argv)

    if args.commande == 'verifier':
        verifier(args.base)
    elif args.commande == 'changelog':
        ecrire_changelog(journal())
    else:
        m = TAG_RE.match(args.tag)
        if not m:
            raise SystemExit('Étiquette attendue : edition-<N>-revision-<M>')
        if args.commande == 'publier':
            publier(Version(int(m[1]), int(m[2]), args.date))
        else:
            pub = next((p for p in journal() if p.tag == args.tag), None)
            if pub is None:
                raise SystemExit('Publication absente du journal : ' + args.tag)
            print(markdown(pub, '###').split('\n', 2)[2].rstrip())


if __name__ == '__main__':
    main()
