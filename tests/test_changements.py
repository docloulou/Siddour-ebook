"""Changesets et journal des modifications : lecture, report à la publication, fin des livres.

Depuis la racine du dépôt : python3 -m unittest discover -s tests
"""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from siddour import changements
from siddour.changements import Changement, Publication, historique, journal, lire, publier
from siddour.rites import RITES
from siddour.version import Version

SEFARADE, ASHKENAZE = RITES['sefarade'], RITES['ashkenaze']
EXEMPLE = '''---
niveau: revision
rites: ashkenaze
editions: phonetique, bilingue
chapitres: priere-du-matin, priere-du-soir
---
Corrige la phonétique de Tal oumatar.

Premier paragraphe de détails.

Second paragraphe.
'''


class ChangesetTest(unittest.TestCase):
    def setUp(self):
        self.dossier = Path(tempfile.mkdtemp())

    def ecrire(self, nom: str, texte: str) -> Path:
        path = self.dossier / nom
        path.write_text(texte, encoding='utf-8')
        return path

    def test_lecture(self):
        ch = lire(self.ecrire('a.md', EXEMPLE))
        self.assertEqual(ch.resume, 'Corrige la phonétique de Tal oumatar.')
        self.assertEqual(ch.details, 'Premier paragraphe de détails.\n\nSecond paragraphe.')
        self.assertEqual(ch.rites, ('ashkenaze',))
        self.assertEqual(ch.editions, ('phonetique', 'bilingue'))
        self.assertEqual(ch.perimetre(), 'rite ashkénaze · éditions phonétique et bilingue · '
                                         'Prière du matin, Prière du soir')
        self.assertTrue(ch.concerne(ASHKENAZE, 'bilingue'))
        self.assertFalse(ch.concerne(ASHKENAZE, 'hebreu'))
        self.assertFalse(ch.concerne(SEFARADE, 'bilingue'))

    def test_defauts(self):
        ch = lire(self.ecrire('b.md', '---\n---\nAjoute une page.\n'))
        self.assertEqual((ch.niveau, ch.rites, ch.editions, ch.chapitres), ('revision', (), (), ()))
        self.assertEqual(ch.perimetre(), 'les deux rites · toutes les éditions · tout le livre')
        self.assertTrue(all(ch.concerne(r, m) for r in RITES.values() for m in changements.MODES))

    def test_chapitre_d_un_seul_rite(self):
        # Pourim n'existe que dans le plan séfarade : le changement ne touche pas les livres ashkénazes.
        ch = lire(self.ecrire('c.md', '---\nchapitres: pourim\n---\nCorrige Pourim.\n'))
        self.assertTrue(ch.concerne(SEFARADE, 'hebreu'))
        self.assertFalse(ch.concerne(ASHKENAZE, 'hebreu'))

    def test_erreurs(self):
        for entete, message in [('rites: yemenite', 'rite inconnu'), ('editions: audio', 'édition inconnue'),
                                ('chapitres: nulle-part', 'chapitre inconnu'), ('niveau: majeur', 'niveau inconnu'),
                                ('rites: ashkenaze\nchapitres: pourim', 'chapitre inconnu'), ('auteur: moi', 'inconnue')]:
            with self.subTest(entete=entete), self.assertRaisesRegex(ValueError, message):
                lire(self.ecrire('d.md', '---\n' + entete + '\n---\nRésumé.\n'))
        with self.assertRaisesRegex(ValueError, 'résumé manquant'):
            lire(self.ecrire('e.md', '---\n---\n'))
        with self.assertRaisesRegex(ValueError, 'trop long'):
            lire(self.ecrire('f.md', '---\n---\n' + 'x' * 200 + '\n'))
        with self.assertRaisesRegex(ValueError, 'en-tête'):
            lire(self.ecrire('g.md', 'Sans en-tête.\n'))

    def test_publier(self):
        attente = self.dossier / 'attente'
        attente.mkdir()
        (attente / 'README.md').write_text('mode d’emploi', encoding='utf-8')
        (attente / 'a.md').write_text(EXEMPLE, encoding='utf-8')
        chemin, changelog = self.dossier / 'changelog.json', self.dossier / 'CHANGELOG.md'
        chemin.write_text('[]', encoding='utf-8')
        pub = publier(Version(1, 5, date(2026, 10, 20)), attente, chemin, changelog)
        self.assertEqual(len(pub.changements), 1)
        self.assertEqual([p.name for p in attente.iterdir()], ['README.md'])
        donnees = json.loads(chemin.read_text(encoding='utf-8'))
        self.assertEqual(donnees[0]['tag'], 'edition-1-revision-5')
        self.assertEqual(donnees[0]['changements'][0]['rites'], ['ashkenaze'])
        self.assertIn('## 1ʳᵉ édition, révision 5 — 20 octobre 2026', changelog.read_text(encoding='utf-8'))
        # Rien en attente, ou une nouvelle édition annoncée dans une simple révision : refusé.
        with self.assertRaises(SystemExit):
            publier(Version(1, 6), attente, chemin, changelog)
        (attente / 'b.md').write_text('---\nniveau: edition\n---\nRevoit le plan.\n', encoding='utf-8')
        with self.assertRaisesRegex(SystemExit, 'nouvelle édition'):
            publier(Version(1, 6), attente, chemin, changelog)
        publier(Version(2, 0), attente, chemin, changelog)
        self.assertEqual([p.tag for p in journal(chemin)], ['edition-2-revision-0', 'edition-1-revision-5'])

    def test_historique(self):
        pubs = [Publication('edition-1-revision-2', date(2026, 10, 16), [Changement('Ashkénaze.', rites=('ashkenaze',))]),
                Publication('edition-1-revision-1', date(2026, 10, 15), [Changement('Phonétique.', editions=('phonetique',))]),
                Publication('edition-1-revision-0', date(2026, 10, 14), [Changement('Première édition.')])]
        titres = lambda rite, mode, v: [t for t, _ in historique(rite, mode, v, 3, pubs)]
        self.assertEqual(len(titres(SEFARADE, 'hebreu', Version(1, 2))), 1)
        self.assertEqual(len(titres(SEFARADE, 'phonetique', Version(1, 2))), 2)
        self.assertEqual(len(titres(ASHKENAZE, 'phonetique', Version(1, 2))), 3)
        # Un livre publié ne cite pas les publications qui le suivent.
        self.assertEqual(len(titres(ASHKENAZE, 'phonetique', Version(1, 1))), 2)


class DepotTest(unittest.TestCase):
    def test_journal_et_changesets_du_depot(self):
        pubs = journal()
        self.assertTrue(pubs)
        self.assertEqual(len({p.tag for p in pubs}), len(pubs))
        changements.en_attente()  # lève une erreur si un changeset est mal formé


if __name__ == '__main__':
    unittest.main()
