"""Non-régression de la phonétique (siddour/phonetique.py).

Depuis la racine du dépôt : python3 -m unittest discover -s tests

Chaque lecture est donnée dans les deux prononciations : « sefarade », celle des
siddourim Pata'h Eliyahou et Beit Hassofer, et « israelienne », celle de l'édition
ashkénaze. Une lecture qui change ici doit être un choix, pas un effet de bord.
"""
import collections
import contextlib
import io
import unittest

from siddour import cli
from siddour.phonetique import (INCONNUS, NOM_DEBUT, NOM_FIN, PRONONCIATIONS, noms_html, non_vocalise,
                                translit, translit_word)
from siddour.rites import RITES

# (hébreu, sefarade, israelienne)
CAS = [
    # Textes de référence.
    ("שְׁמַע יִשְׂרָאֵל יְהֹוָה אֱלֹהֵינוּ יְהֹוָה אֶחָד",
     "Chema‘ Yissraèl Adonaïe Éloheinou Adonaïe éḥad",
     "Chema Yisraél Adonaï Èlohénou Adonaï è’had"),
    ("בָּרוּךְ אַתָּה יְהֹוָה אֱלֹהֵינוּ מֶלֶךְ הָעוֹלָם אֲשֶׁר קִדְּשָׁנוּ בְּמִצְוֹתָיו וְצִוָּנוּ עַל נְטִילַת יָדָיִם",
     "Baroukh atta Adonaïe Éloheinou mélékh ha‘olam achére qiddechanou bemitswotaw wetsiwwanou ‘al netilate yadaïm",
     "Baroukh ata Adonaï Èlohénou mèlèkh ha’olam achèr kidechanou bemitsvotav vetsivanou al netilat yadaïm"),
    ("יִתְגַּדַּל וְיִתְקַדַּשׁ שְׁמֵהּ רַבָּא (אָמֵן)",
     "Yitgaddal weïtqaddache chemèh rabba (amène)",
     "Yitgadal veïtkadach cheméh raba (amén)"),
    ("בָּרוּךְ שֵׁם כְּבוֹד מַלְכוּתוֹ לְעוֹלָם וָעֶד",
     "Baroukh chèm kevod malkhouto le‘olam wa‘éde",
     "Baroukh chém kevod malkhouto le’olam va’èd"),
    ("יְבָרֶכְךָ יְהֹוָה וְיִשְׁמְרֶךָ. יָאֵר יְהֹוָה פָּנָיו אֵלֶיךָ וִיחֻנֶּךָּ. "
     "יִשָּׂא יְהֹוָה פָּנָיו אֵלֶיךָ וְיָשֵׂם לְךָ שָׁלוֹם.",
     "Yevarékhekha Adonaïe weïchmerékha. Yaère Adonaïe panaw èlékha wiḥounnékka. "
     "Yissa Adonaïe panaw èlékha weïassèm lekha chalom.",
     "Yevarèkhekha Adonaï veïchmerèkha. Yaér Adonaï panav élèkha vi’hounèka. "
     "Yissa Adonaï panav élèkha veïassém lekha chalom."),
    # Gutturales : aleph prononcé après une consonne (’), patah furtif, ע au bord du mot.
    ("קִנְאָה וּגְאֻלָּה לִרְאוֹת מַלְאָךְ", "Qin’a oug’oulla lir’ote mal’akh", "Kin’a oug’oula lir’ot mal’akh"),
    ("יִפָּתֵחַ לִשְׁלֹחַ שָׁלִיחַ שׁוֹמֵעַ", "Yippatèaḥ lichloaḥ chaliaḥ chomèa‘", "Yipatéa’h lichloa’h chalia’h choméa"),
    ("מְעוֹנָה", "Me‘ona", "Me’ona"),
    ("עֲשֶׂרֶת", "‘Asséréte", "Assèrèt"),
    # Daguech fort et chva : gémination, chva prononcé après une voyelle longue.
    ("טוּבְךָ", "Touvekha", "Touvkha"),
    ("יְצַפְצְפוּ", "Yetsaftsefou", "Yetsaftsefou"),
    ("פְּדָהצוּר", "Pedahtsour", "Pedahtsour"),
    ("כֹּהֲנִים", "Kohanim", "Kohanim"),
    ("וְ", "We", "Ve"),  # lettre seule au chva
    ("חַיֵּי", "Ḥayyei", "’Hayé"),
    ("חַי", "Ḥaïe", "’Haï"),
    # Qamats qatan, et chva muet de l'araméen.
    ("קָרְבַּן", "Qorbane", "Korban"),
    ("קָדְשְׁךָ", "Qodchekha", "Kodchekha"),
    ("חָכְמָה", "Ḥokhma", "’Hokhma"),
    ("עָלְמָא", "‘Alma", "Alma"),
    # Maqaf : qamats lu « o », mots séparés (sefarade) ou liés par un trait d'union.
    ("נוֹרָא הוּא עַל־כָּל־אֱלֹהִים", "Nora hou ‘al kol élohim", "Nora hou al-kol-èlohim"),
    ("חַנּוּן וְרַחוּם יְהֹוָה אֶרֶךְ אַפַּיִם וּגְדָל־חָסֶד",
     "Ḥannoun weraḥoum Adonaïe érékh appaïm ougdol ḥasséde",
     "’Hanoun vera’houm Adonaï èrèkh apaïm ougdol-’hassèd"),
    ("הַשָּׂם־גְּבוּלֵךְ שָׁלוֹם", "Hassom guevoulèkh chalom", "Hassom-guevoulékh chalom"),
    ("שָׁם־רֶמֶשׂ", "Cham réméss", "Cham-rèmès"),
    ("כָּל־הָעָם", "Kol ha‘am", "Kol-ha’am"),
    ("עִם־רוּחִי", "‘Im rouḥi", "Im-rou’hi"),
    # Finales du Pata'h Eliyahou.
    ("הָאָרֶץ", "Haarétss", "Haarèts"),
    ("זְמַן", "Zemane", "Zeman"),
    ("אֶתְכֶם", "Éte-khém", "Ètkhèm"),
    ("וּבְכֵן לָקָחוּ", "Ouvkhène laqaḥou", "Ouvkhén laka’hou"),
    ("בְּרֵאשִׁית", "Berèchite", "Beréchit"),
    ("צְבָאוֹת", "Tsevaote", "Tsevaot"),
    # Lectures retenues.
    ("הַבְּרִיּוֹת", "Habberiyote", "Haberiyot"),
    ("שֶׁהֶחֱזַרְתָּ", "Chéhéḥézarta", "Chèhè’hèzarta"),
    ("אִי", "I", "I"),
    ("אֲפִלּוּ", "Afillou", "Afilou"),
    ("וְחֶמְלָה", "Weḥémla", "Ve’hèmla"),
    ("וְלָו", "Welaw", "Velav"),
    ("(וְ)רָאשֵׁי חֳדָשִׁים", "(We)rachei ḥodachim", "(Ve)raché ’hodachim"),
    # Vocalisation fautive de la source (CORRECTIONS).
    ("וְיַת כּל דִּי לִי", "Weïate kol di li", "Veïat kol di li"),
    ("וְעֹלַת ראשׁ חֹדֶשׁ", "We‘olate roche ḥodéche", "Ve’olat roch ’hodèch"),
    ("עׂז רַחֲמֶיךָ", "‘Oz raḥamékha", "Oz ra’hamèkha"),
    ("יְראוּ", "Yir’ou", "Yir’ou"),
    ("עמָּהֶם", "‘Immahém", "Imahèm"),
    ("חַטֹּאות", "Ḥattote", "’Hatot"),
    # Mots sans points et sigles (LECTURES, PH_WORDS).
    ("יום", "Yom", "Yom"),
    ('לְר"ח', "Leroche ḥodéche", "Leroch ’hodèch"),
    ('לְיַחֲדָא שֵׁם י"ה בו"ה בְּיִחוּדָא שְׁלִים',
     "Leïaḥada chèm yod qè bewaw qè beïḥouda chelim",
     "Leïa’hada chém yod ké bevav ké beï’houda chelim"),
    ('שֶׁל (פב"פ) רוּחַ', "Chél (untel fils d’untel) rouaḥ", "Chèl (untel fils d’untel) roua’h"),
    # Ketiv et qeré : seul le qeré se lit.
    ("קוּמִי (לכי) לָךְ רַעְיָתִי", "Qoumi lakh ra‘yati", "Koumi lakh ra’yati"),
    ("הביט [הַבִּיטָה] וּרְאֵה", "Habbita our’è", "Habita our’é"),
    # Énumération, ponctuation.
    ("(א) הֲרֵינִי זוֹכֵר יְצִיאַת מִצְרַיִם", "(1) hareini zokhère yetsiate Mitsraïm", "(1) haréni zokhér yetsiat Mitsraïm"),
    ("וְשָׁם נֶאֱמַר:", "Wecham néémar.", "Vecham nèèmar."),
    ("בְּיִרְאָתֶךָ. וְאַתָּה", "Beïr’atékha. Weatta", "Beïr’atèkha. Veata"),
    ("וְשָׂבָֽעְתָּ׃", "Wessava‘ta.", "Vessava’ta."),  # silouq, et non méteg
    # Noms divins.
    ("(יְהֹוָה)", "(Adonaïe)", "(Adonaï)"),
    ("יְיָ", "Adonaïe", "Adonaï"),
    ("בָּרוּךְ ה'", "Baroukh Adonaïe", "Baroukh Adonaï"),
    ("לַיהוָה", "LaAdonaïe", "LaAdonaï"),
    ("מֵיְהוָה", "MèAdonaïe", "MéAdonaï"),
    ("אֲדֹנָי", "Adonaïe", "Adonaï"),
    ("שַׁדַּי", "Chaddaïe", "Chadaï"),
    ("כִּי אֵל שׁוֹמֵעַ תְּפִלָּה", "Ki Èl chomèa‘ tefilla", "Ki Él choméa tefila"),
    ("וּמִתְפַּלְלִים אֶל אֵל לֹא יוֹשִׁיעַ", "Oumitpalelim él èl lo yochia‘", "Oumitpalelim èl él lo yochia"),
    # Noms propres : une seule capitale, sur le nom et non sur le préfixe.
    ("בִּירוּשָׁלַ‍ִם", "Birouchalaïm", "Birouchalaïm"),  # ZWJ de la source entre patah et hiriq
    ("וּבִירוּשָׁלַ‍ִם", "OuvIrouchalaïm", "OuvIrouchalaïm"),
    ("אָמַר בִּירוּשָׁלַ‍ִם", "Amar bIrouchalaïm", "Amar bIrouchalaïm"),
    ("לֵאלֹהִים", "Lèlohim", "Lélohim"),
    ("אָמַר לֵאלֹהִים", "Amar lÈlohim", "Amar lÉlohim"),
    ("אָמַר לְדָוִד", "Amar leDawid", "Amar leDavid"),
    ("וּמָרְדְּכַי", "OuMordekhaïe", "OuMordekhaï"),
]


def marques(texte: str) -> str:
    """[Nom] -> nom divin entre ses marqueurs."""
    return texte.replace("[", NOM_DEBUT).replace("]", NOM_FIN)


class TranslitTest(unittest.TestCase):
    def setUp(self):
        INCONNUS.clear()
        self.addCleanup(INCONNUS.clear)

    def test_deux_prononciations(self):
        for hebreu, sefarade, israelienne in CAS:
            with self.subTest(hebreu=hebreu):
                self.assertEqual(translit(hebreu), sefarade)
                self.assertEqual(translit(hebreu, prononciation="israelienne"), israelienne)
        self.assertFalse(INCONNUS, "mots sans lecture")

    def test_sans_capitale(self):
        self.assertEqual(translit("בָּרוּךְ אַתָּה", capitalize=False), "baroukh atta")
        self.assertEqual(translit("לֵאלֹהִים", capitalize=False), "lÈlohim")

    def test_mot_isole(self):
        self.assertEqual(translit_word("בָּרוּךְ"), "baroukh")
        self.assertEqual(translit_word("יְהֹוָה", "israelienne"), "Adonaï")

    def test_mots_sans_lecture(self):
        translit("בָּרוּךְ ברך")
        self.assertEqual(INCONNUS, collections.Counter({"ברך": 1}))
        INCONNUS.clear()
        translit("יום יהוה לא")  # lus d'après LECTURES et PH_WORDS
        self.assertFalse(INCONNUS)


class NomsDivinsTest(unittest.TestCase):
    def test_marqueurs(self):
        for hebreu, sefarade, israelienne in [
            ("אֱלֹהִים", "[Élohim]", "[Èlohim]"),
            ("אֱלֹהֵי אַבְרָהָם", "[Élohei] Avraham", "[Èlohé] Avraham"),
            ("הָאֱלֹהִים", "Ha[Élohim]", "Ha[Èlohim]"),
            ("אָמַר לַיהוָה", "Amar la[Adonaïe]", "Amar la[Adonaï]"),
            ("כִּי אֵל שׁוֹמֵעַ", "Ki [Èl] chomèa‘", "Ki [Él] choméa"),
            ("שַׁדַּי", "[Chaddaïe]", "[Chadaï]"),
            # Texte cantillé, maqaf.
            ("וּבָרַכְתָּ֖ אֶת־יְהֹוָ֣ה אֱלֹהֶ֑יךָ",
             "Ouvarakhta éte [Adonaïe] [Élohékha]", "Ouvarakhta èt-[Adonaï] [Èlohèkha]"),
            # Dieux des nations, et mots qui ne sont pas des noms divins.
            ("וַעֲבַדְתֶּם אֱלֹהִים אֲחֵרִים", "Wa‘avadtém élohim aḥèrim", "Va’avadtèm èlohim a’hérim"),
            ("כִּי אֵל זָר", "Ki èl zar", "Ki él zar"),
            ("נוֹרָא הוּא עַל־כָּל־אֱלֹהִים", "Nora hou ‘al kol élohim", "Nora hou al-kol-èlohim"),
            ("אֵלַי", "Èlaïe", "Élaï"),
        ]:
            with self.subTest(hebreu=hebreu):
                self.assertEqual(translit(hebreu, noms=True), marques(sefarade))
                self.assertEqual(translit(hebreu, prononciation="israelienne", noms=True), marques(israelienne))

    def test_sans_marqueurs(self):
        self.assertEqual(translit("יְהֹוָה אֱלֹהִים"), "Adonaïe Élohim")

    def test_html(self):
        self.assertEqual(noms_html(translit("יְהֹוָה אֱלֹהִים", noms=True)),
                         '<span class="nom">Adonaïe</span> <span class="nom">Élohim</span>')


class NonVocaliseTest(unittest.TestCase):
    def test_passages(self):
        for texte, attendu in [
            ("אל מלך יושב על כסא רחמים מתנהג בחסידות", True),  # seli'ha du siddour ashkénaze
            ("אָשַׁמְנוּ בָּגַדְנוּ גזלנו דברנו דפי", True),
            ("אָמֵן יְהֵא שְׁמֵהּ רַבָּא", False),
            ("ועונים אמן", False),  # trop court
            ("יהוה אמן יום לא", False),  # mots lus sans points
        ]:
            with self.subTest(texte=texte):
                self.assertIs(non_vocalise(texte), attendu)


class ProfilTest(unittest.TestCase):
    def test_profil_du_rite(self):
        self.assertEqual(RITES["sefarade"].prononciation, "sefarade")
        self.assertEqual(RITES["ashkenaze"].prononciation, "israelienne")
        for rite in RITES.values():
            self.assertIn(rite.prononciation, PRONONCIATIONS)

    def test_ligne_de_commande(self):
        def sortie(*options):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cli.main(["--translit", "חַנּוּן וְרַחוּם", *options])
            return out.getvalue().strip()

        self.assertEqual(sortie(), "Ḥannoun weraḥoum")
        self.assertEqual(sortie("--rite", "ashkenaze"), "’Hanoun vera’houm")
        self.assertEqual(sortie("--prononciation", "israelienne"), "’Hanoun vera’houm")
        self.assertEqual(sortie("--rite", "ashkenaze", "--prononciation", "sefarade"), "Ḥannoun weraḥoum")


if __name__ == "__main__":
    unittest.main()
