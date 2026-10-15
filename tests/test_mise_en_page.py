"""Phonétique dans la mise en page : textes à réciter des consignes, passages non
vocalisés, et toutes les sections des deux rites, depuis le cache de sources du dépôt.

Depuis la racine du dépôt : python3 -m unittest discover -s tests
"""
import re
import unittest
from pathlib import Path

from siddour.consignes import Consignes
from siddour.mise_en_page import UNREAD, render_section
from siddour.phonetique import INCONNUS
from siddour.rites import RITES
from siddour.sources import fetch_section, validate_source

CACHE = Path(__file__).resolve().parent.parent / "cache"
LIGNE_PH = re.compile(r'<p class="ph"[^>]*>(.*?)</p>', re.S)


class RecitationTest(unittest.TestCase):
    def test_reference(self):
        consignes = Consignes()
        # Capitale après la référence d'un verset achevé…
        self.assertEqual(
            consignes.recitation_html("בָּרוּךְ יְהֹוָה לְעוֹלָם אָמֵן וְאָמֵן׃ (תהלים פט, נג) מָלַךְ יְהֹוָה׃", phonetic=True),
            'Baroukh <span class="nom">Adonaïe</span> le‘olam amène weamène. '
            '<span class="reference" lang="fr" dir="ltr">(Psaumes 89, 53.)</span> '
            'Malakh <span class="nom">Adonaïe</span>.')
        # … et pas au milieu d'une phrase.
        self.assertEqual(
            consignes.recitation_html("בָּרוּךְ יְהֹוָה לְעוֹלָם (תהלים פט, נג) מָלַךְ יְהֹוָה", phonetic=True,
                                      prononciation="israelienne"),
            'Baroukh <span class="nom">Adonaï</span> le’olam '
            '<span class="reference" lang="fr" dir="ltr">(Psaumes 89, 53.)</span> '
            'malakh <span class="nom">Adonaï</span>')


class NonVocaliseTest(unittest.TestCase):
    PARAGRAPHES = ["אָשַׁמְנוּ בָּגַדְנוּ גָּזַלְנוּ",
                   "אל מלך יושב על כסא רחמים מתנהג בחסידות",  # seli'ha que la source donne sans points
                   "מוחל עונות עמו מעביר ראשון ראשון",
                   "וַיֹּאמֶר יְהֹוָה סָלַחְתִּי כִּדְבָרֶךָ"]

    def rendre(self, mode: str) -> str:
        return render_section("Essai", self.PARAGRAPHES, mode, "Festivals, Selichot, Fast of Gedalia",
                              Consignes(), None, "israelienne")

    def test_bilingue(self):
        page = self.rendre("bilingue")
        self.assertEqual(page.count(UNREAD), 1)  # une fois pour toute la série
        self.assertEqual(page.count('class="ph"'), 2)
        self.assertEqual(page.count('class="he"'), 4)
        for i in range(4):
            self.assertIn(f'id="p-{i}"', page)  # ancres inchangées
        self.assertIn('<strong>Vayomèr</strong> <span class="nom">Adonaï</span> sala’hti kidvarèkha', page)

    def test_phonetique(self):
        page = self.rendre("phonetique")
        self.assertEqual(page.count(UNREAD), 1)
        self.assertEqual(page.count('class="ph"'), 2)
        self.assertNotIn('class="he"', page)

    def test_hebreu(self):
        self.assertNotIn(UNREAD, self.rendre("hebreu"))


class CorpusTest(unittest.TestCase):
    def test_sections(self):
        """Chaque section, en phonétique : aucun mot sans lecture (à ajouter à PH_WORDS ou
        LECTURES), ni hébreu ni marqueur interne dans le texte produit."""
        consignes = Consignes()
        for rite in RITES.values():
            for chap in rite.plan:
                for titre, ref in chap["sections"]:
                    with self.subTest(rite=rite.code, ref=ref):
                        INCONNUS.clear()
                        bornes, textes = validate_source(fetch_section(ref, CACHE, True, rite.livre), ref)
                        page = render_section(titre, textes, "phonetique", ref, consignes,
                                              bornes.get("bornes"), rite.prononciation)
                        self.assertFalse(INCONNUS, "mots sans lecture")
                        self.assertIsNone(re.search("[\x00-\x08\x0e-\x1f]", page))
                        for ligne in LIGNE_PH.findall(page):
                            self.assertIsNone(re.search("[֐-׿]", ligne), ligne)
        INCONNUS.clear()


if __name__ == "__main__":
    unittest.main()
