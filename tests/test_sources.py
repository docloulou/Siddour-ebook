"""Lecture des sources : balises des paragraphes, indications du siddour ashkénaze et
correctifs ponctuels (SOURCE_FIXES), vérifiés sur le cache de sources du dépôt.

Depuis la racine du dépôt : python3 -m unittest discover -s tests
"""
import re
import unittest
from pathlib import Path
from unittest import mock

from siddour import plan, plan_ashkenaze
from siddour.hebreu import parse_paragraph
from siddour.sources import SOURCE_FIXES, apply_fixes, fetch_section, normalize_ashkenaze, validate_source

CACHE = Path(__file__).resolve().parent.parent / "cache"


def sections(plan_) -> set[str]:
    return {ref for chap in plan_ for _, ref in chap["sections"]}


LIVRES = [(plan.BOOK, sections(plan.PLAN)), (plan_ashkenaze.BOOK, sections(plan_ashkenaze.PLAN))]


class ParagrapheTest(unittest.TestCase):
    def test_balises(self):
        for brut, attendu in [
            # <b> et <big> peuvent couper un mot : ils ne séparent pas le texte.
            ("<b>אָ</b>שַׁמְנוּ. <b>בָּ</b>גַדְנוּ.", ("text", [("אָשַׁמְנוּ. בָּגַדְנוּ.", False)])),
            ("שְׁמַ<big>ע</big> יִשְׂרָאֵל", ("text", [("שְׁמַע יִשְׂרָאֵל", False)])),
            # <small> sépare la consigne du texte à dire.
            ("<small>ואומר:</small> שְׁמַע יִשְׂרָאֵל", ("text", [("ואומר:", True), (" שְׁמַע יִשְׂרָאֵל", False)])),
            ("<small>הקהל עונה</small>", ("note", [("הקהל עונה", True)])),
            ("<big>סליחה ב</big>", ("heading", [("סליחה ב", False)])),
        ]:
            with self.subTest(brut=brut):
                self.assertEqual(parse_paragraph(brut), attendu)


class AshkenazeTest(unittest.TestCase):
    def test_indications(self):
        for brut, attendu in [
            ("בקיץ - מוֹרִיד הַטָּל", "<small>בקיץ</small> מוֹרִיד הַטָּל"),
            ("בחורף - מַשִּׁיב הָרוּחַ", "<small>בחורף</small> מַשִּׁיב הָרוּחַ"),
            ("שְׁמֵהּ רַבָּא. ועונים: אמן", "שְׁמֵהּ רַבָּא. <small>ועונים</small> אמן"),
            ("בְּרִיךְ הוּא. הקהל: אָמֵן", "בְּרִיךְ הוּא. <small>הקהל</small> אָמֵן"),
            ('לש"ץ - לְדוֹר וָדוֹר', '<small>לש"ץ</small> לְדוֹר וָדוֹר'),
            ("<small>הקהל: עונה</small>", "<small>הקהל: עונה</small>"),  # déjà en petits caractères
        ]:
            with self.subTest(brut=brut):
                self.assertEqual(normalize_ashkenaze([brut]), [attendu])


class CorrectifsTest(unittest.TestCase):
    def test_exemples(self):
        for ref, brut, attendu in [
            ("Berachot, Tefillat HaDerech", "כִּי אל שׁוֹמֵעַ תְּפִלָּה", "כִּי אֵל שׁוֹמֵעַ תְּפִלָּה"),
            ("Festivals, Selichot, Fast of Gedalia", "וְכֵן כָּתוּב ושם נאמר: וַיַּעֲבֹר",
             "וְכֵן כָּתוּב וְשָׁם נֶאֱמַר: וַיַּעֲבֹר"),
            ("The Midnight Rite, Tikkun Rachel", "<b>זְכֹ֤ר</b>יְהֹוָה֙ מֶה־הָ֣יָה לָ֔נוּ",
             "<b>זְכֹ֤ר</b> יְהֹוָה֙ מֶה־הָ֣יָה לָ֔נוּ"),
            ("Fast Days and Mourning, Mourning", "לֹא לָקָחעֹשֵׂה אֵלֶּה", "לֹא לָקָח עֹשֵׂה אֵלֶּה"),
            ("Havdalah, Motzei Shabbat Songs", 'וַתָּרֹנָּה [נ"א: וַתִּבְכֶּינָה]',
             'וַתָּרֹנָּה (<small>נ"א</small> וַתִּבְכֶּינָה)'),
            ("Festivals, Selichot, Ten of Tevet", "אבותי: כִּי בָטְחוּ", "<small>(אבותי)</small> כִּי בָטְחוּ"),
        ]:
            with self.subTest(ref=ref):
                self.assertEqual(apply_fixes(ref, [brut]), [attendu])

    def test_sections_du_plan(self):
        connues = set().union(*(refs for _, refs in LIVRES))
        for ref in SOURCE_FIXES:
            with self.subTest(ref=ref):
                self.assertIn(ref, connues)

    def test_motifs(self):
        for ref, correctifs in SOURCE_FIXES.items():
            for motif, _ in correctifs:
                with self.subTest(ref=ref, motif=motif):
                    re.compile(motif)

    def test_toujours_utiles(self):
        """Chaque correctif trouve encore son passage dans la source en cache : celui qu'une
        mise à jour de Sefaria rend sans objet, ou qui ne s'applique plus, se signale ici."""
        for livre, refs in LIVRES:
            for ref, correctifs in list(SOURCE_FIXES.items()):
                if ref not in refs:
                    continue
                with mock.patch.dict(SOURCE_FIXES, {ref: []}):
                    _, textes = validate_source(fetch_section(ref, CACHE, True, livre), ref)
                for motif, remplacement in correctifs:
                    with self.subTest(ref=ref, motif=motif):
                        self.assertTrue(any(re.search(motif, t) for t in textes))
                    textes = [re.sub(motif, remplacement, t) for t in textes]


if __name__ == "__main__":
    unittest.main()
