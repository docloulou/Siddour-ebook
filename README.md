# Siddour-ebook

<!-- publication:debut -->
## Télécharger

**1ʳᵉ édition — 14 octobre 2026** · [notes de publication](https://github.com/docloulou/Siddour-ebook/releases/tag/edition-1-revision-0) · [toutes les éditions](https://github.com/docloulou/Siddour-ebook/releases)

- [Édition hébraïque](https://github.com/docloulou/Siddour-ebook/releases/download/edition-1-revision-0/siddour_liseuse_hebreu.epub)
- [Édition phonétique](https://github.com/docloulou/Siddour-ebook/releases/download/edition-1-revision-0/siddour_liseuse_phonetique.epub)
- [Édition hébreu puis phonétique](https://github.com/docloulou/Siddour-ebook/releases/download/edition-1-revision-0/siddour_liseuse_bilingue.epub)

📖 [Lire en ligne dans le navigateur](https://docloulou.github.io/Siddour-ebook/)
<!-- publication:fin -->

Siddour séfarade pour liseuse, selon le plan fourni : **26 chapitres et 95 sections**. Les consignes pratiques sont en français dans les trois éditions.

Cette version reprend le travail de mise en page du 13 octobre 2026 : consignes raccourcies, suppression des citations répétitives, ajouts délimités et zimoun présenté comme un dialogue.

## Livres disponibles

Les liens de la dernière publication s’affichent en haut de cette page après chaque passage de l’action « Publier les EPUB ». Les fichiers de `dist/` sont ceux de la dernière fabrication :

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

# Site de lecture en ligne (ouvrir ./site/index.html dans le navigateur)
python3 siddour_ebook_liseuse.py --offline --sortie ./build --site ./site

# Essayer des traductions sans toucher aux données (colonnes hebreu;francais)
python3 siddour_ebook_liseuse.py --offline --rubriques ./mes_corrections.csv --sortie ./build

# Sous-ensemble du plan
python3 siddour_ebook_liseuse.py --offline --chapitres apres-le-repas,priere-du-matin --sortie ./build

# Afficher les identifiants disponibles
python3 siddour_ebook_liseuse.py --liste
```

Sans `--offline`, le script télécharge auprès de Sefaria les sections absentes du cache. Il réutilise les fichiers déjà présents.

## Publier une nouvelle édition

Dans l’onglet **Actions** de GitHub, choisir **Publier les EPUB**, puis **Run workflow**, et indiquer :

- **revision** pour des corrections : coquilles, traductions de consignes, phonétique ;
- **edition** pour un changement important : contenu ajouté, plan revu, nouvelle présentation ;
- éventuellement une phrase décrivant les changements, reprise dans la release.

L’action :

1. calcule le numéro suivant ;
2. fabrique les trois EPUB ;
3. les vérifie avec EPUBCheck ;
4. met à jour `dist/` et les liens en haut de ce README ;
5. ajoute l’étiquette `edition-<N>-revision-<M>` ;
6. crée la release avec les trois fichiers ;
7. publie le site de lecture en ligne sur GitHub Pages.

Avant le premier lancement, il faut activer GitHub Pages : **Settings › Pages › Build and deployment › Source : GitHub Actions**.

### Corriger le site sans nouvelle édition

Pour une correction qui ne touche que le site (mise en page, liens…), lancer l’action **Republier le site**. Elle ne crée ni étiquette ni release. Le site :

- garde le numéro et la date de la dernière publication ;
- propose les EPUB de cette publication (`dist/`) ;
- se met à jour dans l’application installée, comme après une révision.

Une correction du texte des livres demande en revanche une nouvelle révision, pour que les EPUB et le site restent identiques.

### Site de lecture en ligne

Les trois éditions se lisent aussi dans un navigateur. Le site comprend :

- une page d’accueil avec les couvertures, la lecture en ligne et les EPUB à télécharger ;
- un sommaire par édition ;
- une page par section, comme dans l’EPUB, avec page précédente / suivante et un lien vers la même section dans les autres éditions.
- une application installable qui se lit hors connexion et se met à jour à chaque publication (voir plus bas).
- en pied de page, un lien vers ce dépôt pour contribuer, un autre pour signaler une erreur, et un lien « nous écrire ». L’action donne le dépôt avec `--depot` ; par défaut, c’est `docloulou/Siddour-ebook`.
  L’adresse de contact n’apparaît en clair ni dans les pages ni dans le dépôt : elle est stockée à l’envers et encodée (`CONTACT` dans `siddour/site.py`), puis reconstituée par le script de la page au moment du clic.

Pour le référencement, chaque page porte :

- un titre et une description propres ;
- une adresse canonique ;
- les balises Open Graph et Twitter pour les aperçus de partage ;
- des données structurées schema.org : `Book` avec ses trois éditions, `BreadcrumbList` et `WebPage`.

Le site fournit aussi `sitemap.xml` et `robots.txt`.

Pour un meilleur référencement, déclarer le site et son sitemap dans Google Search Console et Bing Webmaster Tools :

- **Google Search Console** : propriété de type « Préfixe de l’URL », avec l’adresse du site. Le fichier de validation HTML est dans `assets/racine/`.
- **Bing Webmaster Tools** : importer le site depuis Google Search Console. Bing reprend alors la validation et le sitemap.

Tout fichier placé dans `assets/racine/` est copié tel quel à la racine du site (fichiers de validation, etc.).

#### Application installable (PWA)

Le site s’installe comme une application, sur téléphone comme sur ordinateur : menu du navigateur, puis **Installer l’application** ou **Ajouter à l’écran d’accueil**. Il fournit pour cela :

- un manifeste (`manifest.webmanifest`) avec les icônes, dont une version adaptée aux icônes rondes d’Android, et un raccourci vers chaque édition ;
- un service worker (`sw.js`).

**Lecture hors connexion.** Les pages déjà lues restent disponibles. Le bouton **Garder hors ligne**, sur le sommaire de chaque édition, enregistre toute l’édition sur l’appareil.

**Mise à jour automatique.** Le nom du cache du service worker combine l’étiquette de la publication (`edition-1-revision-2`) et une empreinte de tout le site. Chaque nouvelle édition ou révision modifie donc `sw.js`. Le navigateur détecte ce changement :

- à l’ouverture d’une page ;
- au retour sur l’application ;
- toutes les heures si elle reste ouverte.

Il télécharge alors la nouvelle version, éditions gardées hors ligne comprises, puis recharge la page. Un message indique le nouveau numéro, par exemple « Siddour mis à jour : 1ʳᵉ édition, révision 1 ».

**iPhone et iPad.** Safari n’a pas de bouton d’installation. Sur iPhone et iPad, la page d’accueil explique donc la marche à suivre : **Partager › Sur l’écran d’accueil**. Une fois installée, l’application :

- s’ouvre en plein écran, avec son icône et son nom court « Siddour » ;
- place la barre d’état sur le bandeau bleu, sans masquer le contenu sous l’encoche ;
- affiche un écran de démarrage (le titre doré sur fond bleu), adapté à chaque modèle d’iPhone et d’iPad.

**Icônes et écrans de démarrage.** Ils sont tirés de la couverture et rangés dans `assets/pwa/`. Après un changement de couverture, les régénérer avec :

```bash
python3 -m siddour.icones
```

**Vérification.** La commande suivante fabrique le site dans un dossier temporaire et contrôle :

- les liens ;
- l’installabilité selon Chrome ;
- la lecture hors connexion ;
- la mise à jour automatique après une nouvelle révision ;
- l’aide affichée sur iPhone.

Les contrôles dans le navigateur demandent Playwright (`pip install playwright`).

```bash
python3 outils/verifier_site.py
```

La numérotation suit celle d’un livre imprimé : *1ʳᵉ édition*, puis *1ʳᵉ édition, révision 1*, *révision 2*… Une nouvelle édition remet les révisions à zéro, par exemple *2ᵉ édition*.

Le numéro et la date de fabrication apparaissent à trois endroits :

- en bas de l’introduction ;
- sur la page « À propos de cette édition » ;
- dans la description du livre, que la plupart des liseuses affichent dans la fiche du livre.

Une génération locale sans `--edition` porte la mention « Version de travail ». Pour fabriquer localement un livre numéroté :

```bash
python3 siddour_ebook_liseuse.py --offline --sortie ./build --edition 1 --revision 2 --date 2026-10-14
```

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
| `siddour/site.py` | Site web de lecture, métadonnées de référencement et application installable (PWA). |
| `siddour/icones.py`, `assets/pwa/` | Icônes et écrans de démarrage iOS de l’application, générés depuis la couverture. |
| `outils/verifier_site.py` | Vérification du site et de la PWA. |
| `siddour/version.py`, `siddour/publication.py` | Numéro d’édition ; outils des actions de publication (`.github/workflows/publier.yml`, `site.yml`). |

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
