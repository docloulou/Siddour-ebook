"""Les deux rites du projet : séfarade (Edot HaMizrah) et ashkénaze.

Chaque rite a son plan, son livre Sefaria, ses éditions EPUB et sa partie du site.
Le rite séfarade reste à la racine du site ; le rite ashkénaze vit sous ashkenaze/.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import plan as plan_sefarade
from . import plan_ashkenaze

COVERS = Path(__file__).resolve().parent.parent / 'assets' / 'covers'


@dataclass(frozen=True, eq=False)
class Rite:
    code: str            # identifiant : sefarade, ashkenaze
    adjectif: str        # « Siddour séfarade »
    livre: str           # livre de Sefaria
    plan: list = field(repr=False)
    libelle: str         # « Rite séfarade (Edot HaMizrah) »
    appellation: str     # dans les descriptions du site : « texte du siddour séfarade Edot HaMizrah »
    sous_titre: str      # en-tête du site
    prefixe: str         # dossier du rite dans le site
    couvertures: Path
    urn: str
    titre_long: str      # début de la description des éditions
    description: str     # contenu, repris dans les métadonnées des trois éditions
    sujets: tuple
    introduction: str    # phrase de l'introduction sur le rite suivi
    contenu: str         # ce que contient le livre, dans l'introduction
    usages: str          # sources des consignes, dans « À propos »
    phonetique: str = ''  # précision sur la phonétique
    limites: str = ''     # ce qui manque encore, annoncé sur la page des livres
    prononciation: str = 'sefarade'  # profil de la phonétique (phonetique.PRONONCIATIONS)

    @property
    def nom(self) -> str:
        return 'Siddour ' + self.adjectif

    @property
    def court(self) -> str:
        return self.adjectif.capitalize()

    @property
    def serie(self) -> str:
        return self.nom + ' pour liseuse'

    def epub(self, mode: str) -> str:
        return 'siddour_liseuse_' + ('' if self.code == 'sefarade' else self.code + '_') + mode + '.epub'


SEFARADE = Rite(
    code='sefarade', adjectif='séfarade', livre=plan_sefarade.BOOK, plan=plan_sefarade.PLAN,
    libelle='Rite séfarade (Edot HaMizrah)', appellation='siddour séfarade Edot HaMizrah',
    sous_titre='Rite Edot HaMizrah', prefixe='',
    couvertures=COVERS, urn='urn:siddour-ebook:edot-hamizrah:',
    titre_long='Siddour complet du rite séfarade (Edot HaMizrah)',
    description='prières de la semaine, Chabbat, fêtes, jeûnes, bénédictions et cycle de la vie',
    sujets=('Prière juive', 'Siddour', 'Rite séfarade', 'Edot HaMizrah', 'Liturgie', 'Judaïsme'),
    introduction='Le texte suit le rite séfarade (Edot HaMizrah).',
    contenu='les offices de la semaine, du Chabbat et des fêtes, les jeûnes, les bénédictions '
            'et les étapes de la vie',
    usages='notamment ceux du Ben Ich ’Haï',
    phonetique='Elle suit l’usage des siddourim Pata’h Eliyahou et Beit Hassofer : ḥ pour le ’het, '
               '‘ pour le ayin, w pour le vav, q pour le qof, consonne doublée au daguech fort. ',
)

ASHKENAZE = Rite(
    code='ashkenaze', adjectif='ashkénaze', livre=plan_ashkenaze.BOOK, plan=plan_ashkenaze.PLAN,
    libelle='Rite ashkénaze', appellation='siddour ashkénaze', sous_titre='Rite ashkénaze',
    prefixe='ashkenaze/',
    couvertures=COVERS / 'ashkenaze', urn='urn:siddour-ebook:ashkenaze:',
    titre_long='Siddour du rite ashkénaze',
    description='prières de la semaine, Havdala, Roch ’Hodech, ’Hanouka, jeûnes, bénédictions et Kaddich',
    sujets=('Prière juive', 'Siddour', 'Rite ashkénaze', 'Liturgie', 'Judaïsme'),
    introduction='Le texte suit le rite ashkénaze (Siddur Ashkenaz de Sefaria).',
    contenu='les offices de la semaine, la Havdala, Roch ’Hodech et ’Hanouka, les jeûnes, '
            'les bénédictions et le Kaddich',
    usages='notamment ceux de la Michna beroura',
    phonetique='Elle suit la prononciation israélienne, et non la prononciation ashkénaze traditionnelle : '
               '’h pour le ’het, v pour le vav, k pour le qof, sans consonne doublée. ',
    prononciation='israelienne',
    limites='Pourim, le Tikoun ’Hatsot et les prières du cycle de la vie (mariage, brit mila, deuil) '
            'ne sont pas encore inclus : la source Sefaria de ce rite ne les contient pas.',
)

RITES = {r.code: r for r in (SEFARADE, ASHKENAZE)}


def du_livre(book: str) -> Rite:
    """Rite dont le livre Sefaria est book (SEFARADE pour un autre livre, Tanakh compris)."""
    return next((r for r in RITES.values() if r.livre == book), SEFARADE)
