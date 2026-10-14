"""Plan de l'ebook : chapitres et sections, reliés aux textes de Sefaria.

Index des prières du rite séfarade (Edot HaMizrah).

- "quotidien": True  -> inclus avec --quotidien (prières de la journée)
- ref : chemin dans le Siddur Edot HaMizrach ; une ref qui commence par "@"
  désigne un autre livre de Sefaria, avec éventuellement "|version" en suffixe.
"""
from __future__ import annotations

import sys

BOOK = "Siddur Edot HaMizrach"
TANAKH_PD = "hebrew|Tanach with Nikkud"  # version vocalisée du domaine public

PLAN = [
    # ----- Rite séfarade -------------------------------------------------------
    {"id": "tikoun-hatsot", "fr": "Tikoun ’Hatsot", "he": "תיקון חצות", "quotidien": False,
     "sections": [("Léchem yi’houd", "The Midnight Rite, LeShem Yichud"),
                  ("Tikoun Ra’hel", "The Midnight Rite, Tikkun Rachel"),
                  ("Tikoun Léa", "The Midnight Rite, Tikkun Leah")]},
    {"id": "benedictions-du-matin", "fr": "Bénédictions du matin", "he": "ברכות השחר", "quotidien": True,
     "sections": [("Modé ani", "Preparatory Prayers, Modeh Ani"),
                  ("Birkot hacha’har", "Preparatory Prayers, Morning Blessings"),
                  ("Birkot haTorah", "Preparatory Prayers, Torah Blessings")]},
    {"id": "talith-et-tefilines", "fr": "Talith et téfilines", "he": "ציצית ותפילין", "quotidien": True,
     "sections": [("Talith", "Weekday Shacharit, Order of Talit"),
                  ("Téfilines", "Weekday Shacharit, Order of Tefillin")]},
    {"id": "priere-du-matin", "fr": "Prière du matin", "he": "שחרית של חול", "quotidien": True,
     "sections": [("Peti’hat Éliahou", "Weekday Shacharit, Petichat Eliyahu"),
                  ("Vatitpalel ’Hana", "Weekday Shacharit, Hanna's Prayer"),
                  ("Ouverture de la prière", "Weekday Shacharit, Morning Prayer"),
                  ("Pitoum haKétoret", "Weekday Shacharit, Incense Offering"),
                  ("Hodou", "Weekday Shacharit, Hodu"),
                  ("Péssouké dezimra", "Weekday Shacharit, Pesukei D'Zimra"),
                  ("Chéma et ses bénédictions", "Weekday Shacharit, The Shema"),
                  ("Amida", "Weekday Shacharit, Amida"),
                  ("Vidouï", "Weekday Shacharit, Vidui"),
                  ("Lecture de la Torah (lundi et jeudi)", "Weekday Shacharit, Torah Reading"),
                  ("Achré", "Weekday Shacharit, Ashrei"),
                  ("Ouva leTsion", "Weekday Shacharit, Uva LeSion"),
                  ("Beit Yaakov", "Weekday Shacharit, Beit Yaakov"),
                  ("Psaume du jour", "Weekday Shacharit, Song of the Day"),
                  ("Kavé", "Weekday Shacharit, Kaveh"),
                  ("Alénou", "Weekday Shacharit, Alenu"),
                  ("Les 13 principes de foi", "Additions for Shacharit, Thirteen Principles of Faith"),
                  ("Les 10 souvenirs", "Additions for Shacharit, Ten Remembrances")]},
    {"id": "priere-de-l-apres-midi", "fr": "Prière de l’après-midi", "he": "מנחה של חול", "quotidien": True,
     "sections": [("Korbanot", "Weekday Mincha, Offerings"),
                  ("Amida", "Weekday Mincha, Amida"),
                  ("Vidouï", "Weekday Mincha, Vidui"),
                  ("Alénou", "Weekday Mincha, Alenu")]},
    {"id": "priere-du-soir", "fr": "Prière du soir", "he": "ערבית של חול", "quotidien": True,
     "sections": [("Barkhou", "Weekday Arvit, Barchu"),
                  ("Chéma et ses bénédictions", "Weekday Arvit, The Shema"),
                  ("Amida", "Weekday Arvit, Amidah"),
                  ("Alénou", "Weekday Arvit, Alenu")]},
    {"id": "omer", "fr": "Omer", "he": "ספירת העומר", "quotidien": False,
     "sections": [("Séfirat ha’omer", "Counting of the Omer")]},
    {"id": "priere-du-coucher", "fr": "Prière du coucher", "he": "קריאת שמע על המיטה", "quotidien": True,
     "sections": [("Kriat Chéma al hamita", "Bedtime Shema")]},
    {"id": "havdala", "fr": "Havdala", "he": "הבדלה", "quotidien": False,
     "sections": [("Avant la havdala", "Havdalah, Before Havdalah"),
                  ("Havdala", "Havdalah, Havdala"),
                  ("Chants de motsaé Chabbat", "Havdalah, Motzei Shabbat Songs"),
                  ("Véyitèn lekha", "Havdalah, Veyiten Lecha")]},
    {"id": "benediction-de-la-lune", "fr": "Bénédiction de la lune", "he": "ברכת הלבנה", "quotidien": False,
     "sections": [("Birkat halévana", "Blessing of the Moon")]},
    {"id": "avant-le-repas", "fr": "Avant le repas", "he": "ברכות לפני האוכל", "quotidien": True,
     "sections": [("Birkot hanéhénine", "Blessings on Enjoyments")]},
    {"id": "apres-le-repas", "fr": "Après le repas", "he": "ברכות אחרי האוכל", "quotidien": True,
     "sections": [("Birkat hamazone", "Post Meal Blessing")]},
    {"id": "me-ene-chaloch", "fr": "Mé’ène chaloch", "he": "מעין שלש", "quotidien": True,
     "sections": [("Al hami’hya", "Al Hamihya")]},
    {"id": "roch-hodech", "fr": "Roch ’Hodech", "he": "ראש חודש", "quotidien": False,
     "sections": [("Ordre de Roch ’Hodech", "Rosh Hodesh, Rosh Hodesh"),
                  ("Hallel", "Rosh Hodesh, Hallel"),
                  ("Ouva leTsion", "Rosh Hodesh, Uva LeSion"),
                  ("Psaume du jour", "Rosh Hodesh, Song of the Day"),
                  ("Moussaf", "Rosh Hodesh, Mussaf"),
                  ("Barkhi nafchi", "Rosh Hodesh, Barchi Nafshi"),
                  ("Kavé", "Rosh Hodesh, Kaveh"),
                  ("Pitoum haKétoret", "Rosh Hodesh, Incense Offering"),
                  ("Alénou", "Rosh Hodesh, Alenu")]},
    {"id": "hanouka", "fr": "’Hanouka (allumage & Séfer Torah)", "he": "חנוכה", "quotidien": False,
     "sections": [("Allumage", "Hanukkah, Menorah Lighting"),
                  ("Cha’harit de ’Hanouka", "Hanukkah, Shacharit")]},
    {"id": "pourim", "fr": "Pourim", "he": "פורים", "quotidien": False,
     "sections": [("Chabbat Zakhor", "Purim, Shabbat Zachor"),
                  ("Lecture de la Méguila", "Purim, Megillah Reading"),
                  ("Le jour de Pourim", "Purim, Purim Day")]},
    {"id": "jeunes", "fr": "Jeûnes publics (seli’hot)", "he": "תעניות ציבור", "quotidien": False,
     "sections": [("Tsom Guédalia", "Fast Days and Mourning, Fast of Gedalya"),
                  ("10 Tévèt", "Fast Days and Mourning, Tenth of Tevet"),
                  ("Jeûne d’Esther", "Fast Days and Mourning, Fast of Esther"),
                  ("17 Tamouz", "Fast Days and Mourning, Seventeenth of Tammuz"),
                  ("Lecture de la Torah des jours de jeûne", "Fast Days and Mourning, Torah Reading for Fast Days")]},
    {"id": "benedictions-diverses", "fr": "Bénédictions diverses", "he": "ברכות שונות", "quotidien": False,
     "sections": [("Mézouza", "Assorted Blessings and Prayers, Mezuza"),
                  ("Ma’aké (parapet)", "Assorted Blessings and Prayers, Building a Fence"),
                  ("Prélèvement de la ’hala", "Assorted Blessings and Prayers, Separating Hallah"),
                  ("Tévilat kélim", "Assorted Blessings and Prayers, Tevillat Kelim"),
                  ("Térouma et ma’asser", "Assorted Blessings and Prayers, Separating Tithes"),
                  ("Arc-en-ciel", "Assorted Blessings and Prayers, Rainbow"),
                  ("Éclairs et tonnerre", "Assorted Blessings and Prayers, Blessings on Lighting and Thunder"),
                  ("Avant de prendre un médicament", "Assorted Blessings and Prayers, Prayer for Taking Medicine")]},
    {"id": "hachkava", "fr": "Hachkava & deuil", "he": "השכבה ואבלות", "quotidien": False,
     "sections": [("Deuil", "Fast Days and Mourning, Mourning")]},
    # ----- Commun --------------------------------------------------------------
    {"id": "priere-du-voyageur", "fr": "Prière du voyageur", "he": "תפילת הדרך", "quotidien": True,
     "sections": [("Téfilat haderekh", "Assorted Blessings and Prayers, Traveler's Prayer")]},
    {"id": "tikoun-haklali", "fr": "Tikoun haklali", "he": "תיקון הכללי", "quotidien": False,
     "sections": [(f"Psaume {n}", f"@Psalms {n}|{TANAKH_PD}")
                  for n in (16, 32, 41, 42, 59, 77, 90, 105, 137, 150)]},
    {"id": "perek-chira", "fr": "Perek chira", "he": "פרק שירה", "quotidien": False,
     "sections": [(f"Chapitre {n}", f"@Perek Shirah {n}") for n in range(1, 7)]},
    {"id": "chir-hachirim", "fr": "Chir hachirim", "he": "שיר השירים", "quotidien": False,
     "sections": [("Chir hachirim", "Song of Songs")]},
    {"id": "ceremonie-du-mariage", "fr": "Cérémonie du mariage", "he": "סדר אירוסין ונישואין", "quotidien": False,
     "sections": [("Kidouchine et nissouine", "Assorted Blessings and Prayers, Marriage"),
                  ("Chéva brakhot", "Assorted Blessings and Prayers, Sheva Berachot")]},
    {"id": "brit-mila-pidyon-haben", "fr": "Brit mila & pidyon habèn", "he": "ברית מילה ופדיון הבן", "quotidien": False,
     "sections": [("Brit mila", "Assorted Blessings and Prayers, Brit Mila"),
                  ("Pidyon habèn", "Assorted Blessings and Prayers, Redeeming the First Born")]},
    {"id": "nomination-d-une-fille", "fr": "Nomination d’une fille", "he": "זבד הבת", "quotidien": False,
     "sections": [("Zéved habat", "Shabbat Shacharit, Zeved HaBat")]},
]

# Entrées souhaitables sans équivalent dans le Siddur Edot HaMizrach de Sefaria
# (à compléter par d'autres sources libres si besoin) :
#   Seli'hot (Eloul), Téhilim (livre entier : "@Psalms N|..." si besoin), Téfilot diverses,
#   Iguérèt haRamban, Kivré tsadikim, Tikoun Hocha'ana Rabba, Hatarat nédarim,
#   'Hanoukat habayit, Rituel décès & azkara, Brit Its'hak (Zohar),
#   offices complets de Tich'a béav, 'Hol hamoèd, Pourim et des jeûnes.
#   Kétoret : déjà inclus dans la prière du matin.


def select_plan(chapitres: str | None, complet: bool) -> list[dict]:
    if chapitres:
        wanted = [c.strip() for c in chapitres.split(",") if c.strip()]
        known = {c["id"] for c in PLAN}
        unknown = [w for w in wanted if w not in known]
        if unknown:
            sys.exit(f"Chapitres inconnus : {', '.join(unknown)}  (voir --liste)")
        return [c for c in PLAN if c["id"] in wanted]
    return [c for c in PLAN if complet or c["quotidien"]]
