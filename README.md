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

Pillow sert à recompresser les couvertures en JPEG ; sans lui, le PNG d’origine est intégré tel quel.

Sous Windows, activer l’environnement avec `.venv\Scripts\Activate.ps1` dans PowerShell, puis utiliser `python` si `python3` n’est pas disponible.

## Régénérer les livres

Les textes sources sont inclus dans `cache/`, ce qui permet de générer les livres **hors ligne**. La police hébraïque est intégrée au script et extraite automatiquement.

```bash
python3 siddour_ebook_liseuse.py --offline --cache ./cache --sortie ./dist
```

Cette commande produit les trois EPUB et exporte `rubriques_traduites.csv`, la liste des consignes avec leur nombre d’utilisations. Autres exemples :

```bash
# Une édition seulement
python3 siddour_ebook_liseuse.py --offline --mode phonetique --sortie ./dist

# Aperçus HTML pour relire la mise en page
python3 siddour_ebook_liseuse.py --offline --html --sortie ./build

# Essayer des traductions sans toucher aux données (colonnes hebreu;francais)
python3 siddour_ebook_liseuse.py --offline --rubriques ./mes_corrections.csv --sortie ./build

# Sous-ensemble du plan
python3 siddour_ebook_liseuse.py --offline --chapitres apres-le-repas,priere-du-matin --sortie ./build

# Afficher les identifiants disponibles
python3 siddour_ebook_liseuse.py --liste
```

Sans `--offline`, le script télécharge auprès de Sefaria les sections absentes du cache. Il réutilise les fichiers déjà présents.

## Continuer le travail

Le script `siddour_ebook_liseuse.py` ne fait qu’appeler le paquet `siddour/` :

| Fichier | Rôle |
| --- | --- |
| `siddour/plan.py` | Plan du livre : chapitres, sections et références Sefaria. |
| `siddour/sources.py` | Téléchargement, cache et corrections ponctuelles de la source (`SOURCE_FIXES`). |
| `siddour/hebreu.py` | Nikoud, balises `<small>`/`<big>`, recherche dans le texte hébreu. |
| `siddour/consignes.py` | Traduction des consignes et découpage consigne / texte à réciter. |
| `siddour/mise_en_page.py` | Placement des consignes, variantes, encadrés et notes (`ReadingLayout`). |
| `siddour/phonetique.py` | Translittération ; cas particuliers dans `PH_WORDS`. |
| `siddour/edition.py`, `siddour/style.css` | Assemblage des EPUB et feuille de style. |

Les traductions sont des données, séparées du code (UTF-8, séparateur `;`) :

- `data/consignes.csv` : consignes, repères et références, indexés par l’hébreu sans nikoud.
- `data/intertitres.csv` : titres internes.
- `data/consignes_locales.csv` : consigne dont le sens dépend du passage (section Sefaria et numéro de paragraphe), par exemple un « אומרים » qui désigne l’officiant.

Une consigne absente de ces tables bloque la génération et est listée, pour qu’aucun hébreu non traduit n’apparaisse dans les livres.

### Contenu de chaque EPUB

Couverture (`assets/covers/siddour_<mode>.png`), sommaire sur deux colonnes, introduction, page « À propos de cette édition » (sources, licences, conventions), puis les 26 chapitres. Le texte de l’introduction et les métadonnées sont dans `siddour/edition.py`.

Métadonnées : titre, identifiant, langues (hébreu et français), auteur et éditeur, date, description, sujets, source Sefaria, droits et licences, série « Siddour séfarade pour liseuse » avec le numéro de l’édition (EPUB 3 et Calibre), couverture, date de modification et informations d’accessibilité. Les trois livres passent EPUBCheck 5.1 sans erreur.

### Conventions de mise en page

Inspirées du Pata’h Eliyahou et de l’édition Beit Hassofer :

- La consigne figure en italique, en petit, juste avant le passage qu’elle concerne. Une consigne qui suit le passage (« deux fois », « jusqu’ici ») est collée à ce passage.
- Une répétition courte s’écrit dans la ligne : *(trois fois)*.
- Une variante brève reste dans la phrase, entre crochets, avec sa condition : *[Dix jours de pénitence : …]*. Les noms à insérer s’écrivent de la même façon : *[Untel, fils d’Untel]*.
- Un ajout long est encadré, avec la condition en en-tête et un lien « Suite de la prière ». Les rôles (zimoun, Kedoucha, bénédiction des Cohanim) sont aussi encadrés.
- Les sources (Ben Ich ’Haï, Kaf ha’Haïm…) et les précisions techniques (initiales, acrostiches) passent en notes numérotées, en fin de section, avec liens aller et retour.

## Sources et limites

Les JSON du cache conservent les références et les métadonnées des versions Sefaria : *Siddur Edot HaMizrach*, édition Shaliehsaboo (CC0), *Tanach with Nikkud* et *Torat Emet 357* (domaine public, selon les métadonnées sources). Les usages traduits suivent cette source, notamment ceux du Ben Ich ’Haï.

La police **Noto Serif Hebrew** est distribuée sous SIL Open Font License 1.1, reproduite dans [OFL-NotoSerifHebrew.txt](OFL-NotoSerifHebrew.txt).

La phonétique est générée automatiquement et reste approximative. Le contenu couvre le plan inclus, pas tous les offices possibles. La conservation des textes, la structure XML et les liens des trois EPUB ont été vérifiés ; leur affichage exact dépend de la liseuse. Les références Pata’h Eliyahou et Beit Hassofer ont servi à guider la présentation, sans reproduire leurs textes.
