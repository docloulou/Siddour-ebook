# Siddour-ebook

Siddour séfarade pour liseuse, selon le plan fourni : **26 chapitres et 95 sections**. Les consignes pratiques sont en français dans les trois éditions.

Cette version reprend le travail de mise en page du 13 octobre 2026 : consignes raccourcies, suppression des citations répétitives, ajouts délimités et zimoun présenté comme un dialogue.

## Livres disponibles

- [Édition hébraïque](dist/siddour_liseuse_hebreu.epub)
- [Édition phonétique](dist/siddour_liseuse_phonetique.epub)
- [Édition hébreu puis phonétique pour chaque passage](dist/siddour_liseuse_bilingue.epub)

## Installation

Python 3.10 ou supérieur.

```bash
git clone https://github.com/docloulou/Siddour-ebook.git
cd Siddour-ebook
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Sous Windows, activer l’environnement avec `.venv\Scripts\Activate.ps1` dans PowerShell, puis utiliser `python` si `python3` n’est pas disponible.

## Régénérer les livres

Les textes sources sont inclus dans `cache/`, ce qui permet de générer les livres **hors ligne**. La police hébraïque est intégrée au script et extraite automatiquement.

```bash
python3 siddour_ebook_liseuse.py --offline --cache ./cache --sortie ./dist
```

Cette commande produit les trois EPUB et exporte un CSV de toutes les rubriques. Autres exemples :

```bash
# Une édition seulement
python3 siddour_ebook_liseuse.py --offline --mode phonetique --sortie ./dist

# Aperçus HTML pour relire la mise en page
python3 siddour_ebook_liseuse.py --offline --html --sortie ./build

# Traductions corrigées dans le CSV éditable
python3 siddour_ebook_liseuse.py --offline --rubriques ./data/rubriques_traduites.csv --sortie ./dist

# Sous-ensemble du plan
python3 siddour_ebook_liseuse.py --offline --chapitres apres-le-repas,priere-du-matin --sortie ./build

# Afficher les identifiants disponibles
python3 siddour_ebook_liseuse.py --liste
```

Sans `--offline`, le script télécharge auprès de Sefaria les sections absentes du cache. Il réutilise les fichiers déjà présents.

## Continuer le travail

- **Plan et textes à inclure** : modifier `PLAN` dans `siddour_ebook_liseuse.py`.
- **Traductions des consignes** : modifier `data/rubriques_traduites.csv`, enregistré en UTF-8, séparateur `;`, puis générer avec `--rubriques`. Le script embarque déjà 680 traductions ; le CSV est facultatif.
- **Police, tailles, espacements et séparateurs** : modifier `CSS` dans le script.
- **Articulation des commentaires** : modifier `ReadingLayout`, notamment `note`, `paragraph`, `conditional_items` et `render`. `_brief_rubric` raccourcit certaines consignes à l’affichage.
- **Phonétique** : modifier `translit_word`, `translit` et les corrections de `PH_WORDS`.

Le zimoun regroupe les rôles et affiche les mots ajoutés à partir de dix convives entre crochets. Les variantes proposent de choisir une seule formule. Les notes techniques restent en fin de section, avec liens de retour.

## Sources et limites

Les JSON du cache conservent les références et les métadonnées des versions Sefaria : *Siddur Edot HaMizrach*, édition Shaliehsaboo (CC0), *Tanach with Nikkud* et *Torat Emet 357* (domaine public, selon les métadonnées sources). Les usages traduits suivent cette source, notamment ceux du Ben Ich ’Haï.

La police **Noto Serif Hebrew** est distribuée sous SIL Open Font License 1.1, reproduite dans [OFL-NotoSerifHebrew.txt](OFL-NotoSerifHebrew.txt).

La phonétique est générée automatiquement et reste approximative. Le contenu couvre le plan inclus, pas tous les offices possibles. La conservation des textes, la structure XML et les liens des trois EPUB ont été vérifiés ; leur affichage exact dépend de la liseuse. Les références Pata’h Eliyahou et Beit Hassofer ont servi à guider la présentation, sans reproduire leurs textes.
