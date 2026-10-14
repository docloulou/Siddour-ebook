"""Plan du rite ashkénaze, d'après le Siddur Ashkenaz de Sefaria.

Une ref désigne un nœud du livre : une prière (feuille) ou une partie entière,
dont les prières sont alors réunies dans l'ordre du livre. Plusieurs nœuds se
joignent par « + ». Une ref qui commence par "@" désigne un autre livre de
Sefaria, comme dans plan.py.

Comme l'édition séfarade, celle-ci laisse de côté les offices du Chabbat et des
fêtes, sauf la Havdala. Véyitèn lekha n'y figure pas : le seul texte de Sefaria
n'a pas de licence connue.
"""
from __future__ import annotations

from .plan import TANAKH_PD

BOOK = "Siddur Ashkenaz"

_PREP = "Weekday, Shacharit, Preparatory Prayers, "
_FIN = "Weekday, Shacharit, Concluding Prayers, "
_APRES = "Weekday, Shacharit, Post Service, "
_MANGER = "Berachot, Birkat Hanehenin, Eating, "

PLAN = [
    {"id": "benedictions-du-matin", "fr": "Bénédictions du matin", "he": "ברכות השחר", "quotidien": True,
     "sections": [("Modé ani", _PREP + "Modeh Ani"),
                  ("Nétilat yadayim", _PREP + "Netilat Yadayim"),
                  ("Acher yatsar", _PREP + "Asher Yatzar"),
                  ("Élohaï nechama", _PREP + "Elokai Neshama"),
                  ("Birkot haTorah", _PREP + "Torah Blessings + " + _PREP + "Torah Study"),
                  ("Birkot hacha’har", _PREP + "Morning Blessings")]},
    {"id": "talith-et-tefilines", "fr": "Talith et téfilines", "he": "ציצית ותפילין", "quotidien": True,
     "sections": [("Tsitsit", _PREP + "Tzitzit"),
                  ("Talith", _PREP + "Tallit"),
                  ("Téfilines", _PREP + "Tefillin")]},
    {"id": "priere-du-matin", "fr": "Prière du matin", "he": "שחרית של חול", "quotidien": True,
     "sections": [("Ma tovou", _PREP + "Ma Tovu"),
                  ("Adon olam et Yigdal", _PREP + "Adon Olam + " + _PREP + "Yigdal"),
                  ("Akédat Its’hak", _PREP + "Akedah"),
                  ("Léolam yehé adam", _PREP + "Sovereignty of Heaven"),
                  ("Korbanot", _PREP + "Korbanot"),
                  ("Péssouké dezimra", "Weekday, Shacharit, Pesukei Dezimra"),
                  ("Chéma et ses bénédictions", "Weekday, Shacharit, Blessings of the Shema"),
                  ("Amida", "Weekday, Shacharit, Amidah"),
                  ("Vidouï et treize attributs", "Weekday, Shacharit, Post Amidah, Vidui and 13 Middot"),
                  ("Avinou malkénou", "Weekday, Shacharit, Post Amidah, Avinu Malkenu"),
                  ("Ta’hanoun", "Weekday, Shacharit, Post Amidah, Tachanun"),
                  ("Lecture de la Torah (lundi et jeudi)", "Weekday, Shacharit, Torah Reading"),
                  ("Achré", _FIN + "Ashrei"),
                  ("Lamnatséa’h", _FIN + "Lamenatze'ach"),
                  ("Ouva leTsion", _FIN + "Uva Letzion"),
                  ("Kaddich chalem", _FIN + "Kaddish Shalem"),
                  ("Alénou", _FIN + "Alenu + " + _FIN + "Mourner's Kaddish"),
                  ("Psaume du jour", _FIN + "Song of the Day"),
                  ("Lédavid Hachem ori", _FIN + "LeDavid"),
                  ("Ein kélohénou (usage d’Israël)", _FIN + "Korbanot (Israel)"),
                  ("Les 6 souvenirs", _APRES + "Six Remembrances"),
                  ("Les 10 commandements", f"@Exodus 20:2-14|{TANAKH_PD}"),
                  ("Les 13 principes de foi", _APRES + "Thirteen Principles")]},
    {"id": "priere-de-l-apres-midi", "fr": "Prière de l’après-midi", "he": "מנחה של חול", "quotidien": True,
     "sections": [("Achré", "Weekday, Minchah, Ashrei"),
                  ("Amida", "Weekday, Minchah, Amida"),
                  ("Avinou malkénou", "Weekday, Minchah, Post Amidah, Avinu Malkenu"),
                  ("Ta’hanoun", "Weekday, Minchah, Post Amidah, Tachanun"),
                  ("Kaddich chalem", "Weekday, Minchah, Post Amidah, Kaddish Shalem"),
                  ("Alénou", "Weekday, Minchah, Concluding Prayers")]},
    {"id": "priere-du-soir", "fr": "Prière du soir", "he": "ערבית של חול", "quotidien": True,
     "sections": [("Véhou ra’houm", "Weekday, Maariv, Vehu Rachum"),
                  ("Barkhou", "Weekday, Maariv, Barchu"),
                  ("Chéma et ses bénédictions", "Weekday, Maariv, Blessings of the Shema"),
                  ("Amida", "Weekday, Maariv, Amidah"),
                  ("Kaddich chalem", "Weekday, Maariv, Kaddish Shalem"),
                  ("Alénou", "Weekday, Maariv, Alenu + Weekday, Maariv, Mourner's Kaddish"),
                  ("Lédavid Hachem ori", "Weekday, Maariv, LeDavid")]},
    {"id": "omer", "fr": "Omer", "he": "ספירת העומר", "quotidien": False,
     "sections": [("Séfirat ha’omer", "Weekday, Maariv, Sefirat HaOmer")]},
    {"id": "priere-du-coucher", "fr": "Prière du coucher", "he": "קריאת שמע על המיטה", "quotidien": True,
     "sections": [("Kriat Chéma al hamita", "Weekday, Maariv, Keri'at Shema al Hamita")]},
    {"id": "havdala", "fr": "Havdala", "he": "הבדלה", "quotidien": False,
     "sections": [("Vihi noam", "Weekday, Maariv, Additions for Motza'ei Shabbat, Viyehi Noam"),
                  ("Havdala", "Shabbat, Havdalah")]},
    {"id": "benediction-de-la-lune", "fr": "Bénédiction de la lune", "he": "ברכת הלבנה", "quotidien": False,
     "sections": [("Birkat halévana", "Weekday, Maariv, Birkat HaLevana")]},
    {"id": "avant-le-repas", "fr": "Avant le repas", "he": "ברכות לפני האוכל", "quotidien": True,
     "sections": [("Bénédictions avant de manger", _MANGER + "Barachot Rishonot")]},
    {"id": "apres-le-repas", "fr": "Après le repas", "he": "ברכות אחרי האוכל", "quotidien": True,
     "sections": [("Birkat hamazone", "Berachot, Birkat HaMazon")]},
    {"id": "me-ene-chaloch", "fr": "Mé’ène chaloch", "he": "מעין שלש", "quotidien": True,
     "sections": [("Al hami’hya", _MANGER + "Brachot Achronot, Al Hamichyah"),
                  ("Boré néfachot", _MANGER + "Brachot Achronot, Borei Nefashot")]},
    {"id": "roch-hodech", "fr": "Roch ’Hodech", "he": "ראש חודש", "quotidien": False,
     "sections": [("Hallel", "Festivals, Rosh Chodesh, Hallel"),
                  ("Moussaf", "Festivals, Rosh Chodesh, Musaf Amidah for Rosh Chodesh"),
                  ("Barkhi nafchi", _FIN + "Barchi Nafshi")]},
    {"id": "hanouka", "fr": "’Hanouka", "he": "חנוכה", "quotidien": False,
     "sections": [("Allumage", "Festivals, Chanukah, Service for Lighting Chanukah Candles")]},
    {"id": "jeunes", "fr": "Jeûnes publics (seli’hot)", "he": "תעניות ציבור", "quotidien": False,
     "sections": [("Tsom Guédalia", "Festivals, Selichot, Fast of Gedalia"),
                  ("10 Tévèt", "Festivals, Selichot, Ten of Tevet"),
                  ("Jeûne d’Esther", "Festivals, Selichot, Fast of Esther"),
                  ("17 Tamouz", "Festivals, Selichot, Seventeen of Tamuz"),
                  ("Yom Kippour katan", "Festivals, Selichot, Yom Kippur Katan"),
                  ("Béhab", "Festivals, Selichot, BaHaB")]},
    {"id": "benedictions-diverses", "fr": "Bénédictions diverses", "he": "ברכות שונות", "quotidien": False,
     "sections": [("Bénédictions des mitsvot", "Berachot, Birkhot Hamitzvot"),
                  ("Ce que l’on voit, entend ou sent", "Berachot, Birkat Hanehenin, Blessings on Sights Sounds and Smells"),
                  ("Au cimetière", "Berachot, Asher Yatzar Etchem Badin"),
                  ("Havinénou", "Berachot, Havinenu")]},
    {"id": "kaddich", "fr": "Kaddich", "he": "קדיש", "quotidien": False,
     "sections": [("Demi-Kaddich", "Kaddish, Half Kaddish"),
                  ("Kaddich des endeuillés", "Kaddish, Mourner's Kaddish"),
                  ("Kaddich chalem", "Kaddish, Kaddish Shalem"),
                  ("Kaddich derabbanan", "Kaddish, Kaddish d'Rabbanan"),
                  ("Kaddich après l’inhumation", "Kaddish, Kaddish achar HaKevura"),
                  ("Kaddich de fin de traité", "Kaddish, Kaddish achar Hashlamat Meschet")]},
    # ----- Commun --------------------------------------------------------------
    {"id": "priere-du-voyageur", "fr": "Prière du voyageur", "he": "תפילת הדרך", "quotidien": True,
     "sections": [("Téfilat haderekh", "Berachot, Tefillat HaDerech")]},
    {"id": "tikoun-haklali", "fr": "Tikoun haklali", "he": "תיקון הכללי", "quotidien": False,
     "sections": [(f"Psaume {n}", f"@Psalms {n}|{TANAKH_PD}")
                  for n in (16, 32, 41, 42, 59, 77, 90, 105, 137, 150)]},
    {"id": "perek-chira", "fr": "Perek chira", "he": "פרק שירה", "quotidien": False,
     "sections": [(f"Chapitre {n}", f"@Perek Shirah {n}") for n in range(1, 7)]},
    {"id": "chir-hachirim", "fr": "Chir hachirim", "he": "שיר השירים", "quotidien": False,
     "sections": [("Chir hachirim", f"@Song of Songs|{TANAKH_PD}")]},
]
