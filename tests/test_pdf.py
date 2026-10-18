"""Édition PDF : le livre en une seule page HTML, dont chaque lien interne trouve sa cible.

Ne demande pas WeasyPrint : seul le document qui lui est confié est vérifié.
Depuis la racine du dépôt : python3 -m unittest discover -s tests
"""
import re
import unittest
from collections import Counter
from pathlib import Path

from siddour.consignes import Consignes
from siddour.edition import FONT_PATH, render_book
from siddour.pdf import LATIN, document
from siddour.rites import RITES
from siddour.sources import fetch_section

CACHE = Path(__file__).resolve().parent.parent / "cache"


class DocumentTest(unittest.TestCase):
    def test_ancres(self):
        for rite in RITES.values():
            plan = rite.plan[:4]
            sources = {ref: fetch_section(ref, CACHE, True, rite.livre) for c in plan for _, ref in c["sections"]}
            for mode in ("hebreu", "bilingue"):
                with self.subTest(rite=rite.code, mode=mode):
                    page = document(render_book(plan, sources, mode, Consignes(), rite=rite), FONT_PATH)
                    ids = Counter(re.findall(r'\sid="([^"]+)"', page))
                    self.assertEqual([i for i, n in ids.items() if n > 1], [], "identifiants en double")
                    cibles = set(re.findall(r'\shref="#([^"]+)"', page))
                    self.assertTrue(cibles)
                    self.assertEqual(sorted(cibles - set(ids)), [], "liens internes sans cible")
                    # Une section par entrée du sommaire, chaque chapitre sur une nouvelle page.
                    self.assertEqual(page.count('<div class="chapitre">'), len(plan))
                    self.assertNotIn("epub:type", page)
                    # Le livre se termine par ses dernières modifications.
                    self.assertIn("<h1>Dernières modifications</h1>", page.rsplit('<div class="chapitre">', 1)[1])

    def test_polices(self):
        for name in LATIN.values():
            self.assertTrue((FONT_PATH.parent / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
