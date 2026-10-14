# Siddour-ebook

<!-- publication:debut -->
## Télécharger

**1ʳᵉ édition, révision 2 — 14 octobre 2026** · [notes de publication](https://github.com/docloulou/Siddour-ebook/releases/tag/edition-1-revision-2) · [toutes les éditions](https://github.com/docloulou/Siddour-ebook/releases)

### Rite séfarade (Edot HaMizrah)

- [Édition hébraïque](https://github.com/docloulou/Siddour-ebook/releases/download/edition-1-revision-2/siddour_liseuse_hebreu.epub)
- [Édition phonétique](https://github.com/docloulou/Siddour-ebook/releases/download/edition-1-revision-2/siddour_liseuse_phonetique.epub)
- [Édition hébreu puis phonétique](https://github.com/docloulou/Siddour-ebook/releases/download/edition-1-revision-2/siddour_liseuse_bilingue.epub)

### Rite ashkénaze

*Pourim, le Tikoun ’Hatsot et les prières du cycle de la vie (mariage, brit mila, deuil) ne sont pas encore inclus : la source Sefaria de ce rite ne les contient pas.*

- [Édition hébraïque](https://github.com/docloulou/Siddour-ebook/releases/download/edition-1-revision-2/siddour_liseuse_ashkenaze_hebreu.epub)
- [Édition phonétique](https://github.com/docloulou/Siddour-ebook/releases/download/edition-1-revision-2/siddour_liseuse_ashkenaze_phonetique.epub)
- [Édition hébreu puis phonétique](https://github.com/docloulou/Siddour-ebook/releases/download/edition-1-revision-2/siddour_liseuse_ashkenaze_bilingue.epub)

📖 [Lire en ligne dans le navigateur](https://docloulou.github.io/Siddour-ebook/)
<!-- publication:fin -->

Siddour pour liseuse, en deux rites, chacun en trois éditions (hébreu, phonétique, hébreu puis phonétique) :

- **rite séfarade (Edot HaMizrah)**, selon le plan fourni : **26 chapitres et 95 sections** ;
- **rite ashkénaze**, tiré du *Siddur Ashkenaz* de Sefaria et rangé sur le même modèle : **21 chapitres et 92 sections**. Pourim, le Tikoun ’Hatsot et les prières du cycle de la vie n’y sont pas encore : la source Sefaria de ce rite ne les contient pas.

Les consignes pratiques sont en français dans les six éditions.

Cette version reprend le travail de mise en page du 13 octobre 2026 : consignes raccourcies, suppression des citations répétitives, ajouts délimités et zimoun présenté comme un dialogue.

## Livres disponibles

Les liens de la dernière publication s’affichent en haut de cette page après chaque passage de l’action « Publier les EPUB ». Les fichiers de `dist/` sont ceux de la dernière fabrication :

- [Édition hébraïque](dist/siddour_liseuse_hebreu.epub)
- [Édition phonétique](dist/siddour_liseuse_phonetique.epub)
- [Édition hébreu puis phonétique pour chaque passage](dist/siddour_liseuse_bilingue.epub)

Les éditions ashkénazes (`siddour_liseuse_ashkenaze_<mode>.epub`) rejoindront `dist/` à leur première publication.

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

Cette commande produit les six EPUB (trois par rite) et exporte `rubriques_traduites.csv`, la liste des consignes avec leur nombre d’utilisations. Autres exemples :

```bash
# Un seul rite (sefarade ou ashkenaze)
python3 siddour_ebook_liseuse.py --offline --rite ashkenaze --sortie ./dist

# Une édition seulement, dans chaque rite
python3 siddour_ebook_liseuse.py --offline --mode phonetique --sortie ./dist

# Aperçus HTML pour relire la mise en page
python3 siddour_ebook_liseuse.py --offline --html --sortie ./build

# Site de lecture en ligne (ouvrir ./site/index.html dans le navigateur)
python3 siddour_ebook_liseuse.py --offline --sortie ./build --site ./site

# Essayer des traductions sans toucher aux données (colonnes hebreu;francais)
python3 siddour_ebook_liseuse.py --offline --rubriques ./mes_corrections.csv --sortie ./build

# Sous-ensemble du plan
python3 siddour_ebook_liseuse.py --offline --chapitres apres-le-repas,priere-du-matin --sortie ./build

# Afficher les identifiants disponibles, rite par rite
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
2. fabrique les six EPUB (trois par rite) ;
3. les vérifie avec EPUBCheck ;
4. met à jour `dist/` et les liens en haut de ce README ;
5. ajoute l’étiquette `edition-<N>-revision-<M>` ;
6. crée la release avec les six fichiers, rangés par rite dans les notes ;
7. publie le site de lecture en ligne sur GitHub Pages.

Avant le premier lancement, il faut activer GitHub Pages : **Settings › Pages › Build and deployment › Source : GitHub Actions**.

### Corriger le site sans nouvelle édition

Pour une correction qui ne touche que le site (mise en page, liens…), lancer l’action **Republier le site**. Elle ne crée ni étiquette ni release. Le site :

- garde le numéro et la date de la dernière publication ;
- propose les EPUB de cette publication (`dist/`) ;
- se met à jour dans l’application installée, comme après une révision.

Une correction du texte des livres demande en revanche une nouvelle révision, pour que les EPUB et le site restent identiques.

**Essayer une branche.** Dans **Republier le site**, le champ « Branche à publier » publie le site d’une autre branche, par exemple avant de fusionner une pull request. Garder `main` dans « Use workflow from ». Le site en ligne devient alors celui de la branche, application installée comprise. Pour revenir à `main`, relancer l’action avec le champ vide.

### Site de lecture en ligne

Les six éditions se lisent aussi dans un navigateur. Le rite séfarade est à la racine du site (`hebreu/`, `phonetique/`, `bilingue/`), le rite ashkénaze sous `ashkenaze/` (`ashkenaze/hebreu/`…). En haut de chaque page, le bandeau montre le logo (le mot סידור doré de la couverture, `assets/pwa/logo.png`), le nom du site et les onglets : un petit calendrier pour revenir à la page du jour, puis Livres, Hébreu, Phonétique, Bilingue. Depuis une page de prière, les onglets Hébreu, Phonétique et Bilingue ouvrent la même page dans l’autre édition du même rite. Sur l’accueil et la page des livres, ils mènent aux éditions du rite choisi dans « Aujourd’hui » (séfarade par défaut). Le site comprend :

- une page d’accueil **Aujourd’hui**, décrite plus bas : date du jour, prières et horaires ;
- une page **Livres** (`livres.html`) avec, pour chaque rite, les couvertures, la lecture en ligne et les EPUB à télécharger. Sur téléphone, les trois éditions d’un rite et une case (aide à la lecture sur liseuse pour le rite séfarade, contenu du livre pour le rite ashkénaze) tiennent en 2 × 2 ; sur grand écran, sur une seule ligne ;
- un sommaire par édition, avec un lien vers la même édition dans l’autre rite ;
- une page par section, comme dans l’EPUB, avec page précédente / suivante et un lien vers la même section dans les autres éditions.
- une barre qui reste en haut de l’écran pendant la lecture : section précédente ‹, liste de toutes les sections rangées par chapitre pour y aller directement, section suivante ›. Sur les pages sans sections (accueil…), c’est le bandeau du site qui reste en haut.
- un bouton **Aa Affichage** dans cette barre, qui ouvre les réglages de lecture :
  - taille du texte (A− / A+, de 80 % à 210 %) ;
  - alignement de l’hébreu et, séparément, de la phonétique : à droite, justifié, centré ou à gauche (par défaut, hébreu à droite, phonétique justifiée) ;
  - fond de page : blanc (par défaut), ivoire (jaune pâle) ou papier ancien vergé.

  Les réglages sont gardés sur l’appareil et appliqués dès l’ouverture de chaque page. La texture du papier ancien (`assets/pwa/papier.jpg`, raccordable sur ses bords) est générée avec les icônes par `python3 -m siddour.icones`.
- une application installable qui se lit hors connexion et se met à jour à chaque publication (voir plus bas).
- en pied de page, un lien vers ce dépôt pour contribuer, un autre pour signaler une erreur, et un lien « nous écrire ». L’action donne le dépôt avec `--depot` ; par défaut, c’est `docloulou/Siddour-ebook`.
  L’adresse de contact n’apparaît en clair ni dans les pages ni dans le dépôt : elle est stockée à l’envers et encodée (`CONTACT` dans `siddour/site.py`), puis reconstituée par le script de la page au moment du clic.

Pour le référencement, chaque page porte :

- **un titre propre**, le sujet en tête, puis le chapitre et le rite : « Modé ani en hébreu — Bénédictions du matin | Siddour séfarade ». Au-delà de 70 caractères, le chapitre est omis, sauf si le nom de la section revient dans plusieurs chapitres (« Amida en phonétique — Prière du soir | Siddour séfarade ») ;
- **une description propre**, 160 caractères au plus : la section, son chapitre, l’édition, puis le début du texte de la prière (« Modé ani (Bénédictions du matin) en hébreu, siddour séfarade : « מודה אני לפניך מלך חי וקים… » Consignes en français. »). L’hébreu y est sans voyelles ni cantillation, comme le tape un internaute ;
- **des mots-clés** (`<meta name="keywords">`) : la section, son chapitre en français et en hébreu, le rite, l’édition, puis siddour, sidour, siddur, livre de prière juif. Google les ignore ; Bing, Yandex et Qwant s’en servent encore un peu ;
- **un seul titre `h1`** : le nom de l’édition sur le sommaire, celui de la section sur ses pages (le chapitre passe au-dessus, sans changer l’affichage) ;
- **une adresse canonique**, les liens `prev` / `next` vers les sections voisines et la consigne `robots` qui autorise les grands aperçus. La page 404 et la page hors connexion sont exclues (`noindex`), sans canonique ;
- **les balises Open Graph et Twitter** : type `book` pour les sommaires, `article` pour les sections, avec l’image, ses dimensions et son texte alternatif. Les éditions montrent leur couverture ; l’accueil et la page des livres, une image de partage au format paysage (`assets/partage.jpg`, 1200 × 630), fabriquée avec le site à partir du logo et de trois couvertures ;
- **des données structurées schema.org**, en un seul graphe relié par identifiants : `WebSite` et l’éditeur (`Organization`) sur toutes les pages, `CollectionPage` et `Book` avec ses six éditions sur la page des livres, `Book` sur chaque sommaire, `Chapter` rattaché à son `Book` sur chaque section, `AboutPage` pour « À propos », `BreadcrumbList` partout sauf l’accueil.

La police hébraïque est préchargée sur les éditions qui contiennent de l’hébreu. Sur l’accueil, sous le lien vers les livres, un court texte présente le siddour en ligne et mène aux six sommaires.

Le site fournit aussi `sitemap.xml` (avec les images des pages) et `robots.txt`. Le `robots.txt` autorise tout, à tous les robots, y compris ceux des IA (GPTBot, ClaudeBot, Google-Extended, PerplexityBot, CCBot…), nommés un par un dans `ROBOTS_IA` (`siddour/site.py`). Sur une page de projet GitHub (`owner.github.io/depot/`), les robots ne lisent que le `robots.txt` du domaine, pas celui du site : il faut donc déclarer le sitemap soi-même.

Pour un meilleur référencement, déclarer le site et son sitemap dans Google Search Console et Bing Webmaster Tools :

- **Google Search Console** : propriété de type « Préfixe de l’URL », avec l’adresse du site. Le fichier de validation HTML est dans `assets/racine/`. Soumettre ensuite `sitemap.xml` (Sitemaps > Ajouter).
- **Bing Webmaster Tools** : importer le site depuis Google Search Console. Bing reprend alors la validation et le sitemap.

**IndexNow.** Après chaque déploiement, les actions signalent toutes les pages du sitemap à IndexNow : Bing, Yandex, Seznam ou Naver les réexplorent sans attendre leur prochain passage. La clé (`INDEXNOW`, `siddour/publication.py`) est publiée dans `<clé>.txt` à la racine du site. Un refus n’arrête pas la publication. Pour le faire à la main :

```bash
python3 -m siddour.publication indexnow --site https://docloulou.github.io/Siddour-ebook/
```

Tout fichier placé dans `assets/racine/` est copié tel quel à la racine du site (fichiers de validation, etc.).

#### Page d’accueil « Aujourd’hui »

L’accueil montre la journée du lecteur, comme un calendrier de synagogue :

- la date grégorienne et la date hébraïque, en français et en hébreu, avec la date hébraïque qui commence au coucher du soleil ;
- les **prières du jour** :
  - Cha’harit, Min’ha et Arvit, avec un lien vers la page du siddour, dans le rite choisi. La prière du moment est mise en évidence.
  - Les ajouts du jour : lundi et jeudi, Roch ’Hodech, ’Hol hamoèd, ’Hanouka, Pourim, jeûnes, compte de l’omer, Havdala.
  - Le Chabbat et les jours de fête, dont les offices ne sont pas encore dans ce siddour, sont signalés sans lien, comme les prières absentes du rite choisi (la Méguila de Pourim dans le rite ashkénaze, par exemple).
- les **horaires du jour** (zmanim), chacun avec une ligne d’explication : aube, téfilines, Chéma, Amida, ’hatsot, Min’ha, coucher du soleil, tombée de la nuit, milieu de la nuit ;
- les horaires du prochain **Chabbat** (allumage, sortie, paracha) ;
- les **prochaines fêtes et jeûnes**, avec leurs heures d’allumage, de début et de fin ;
- un lien bien visible vers la page des livres.

Les horaires et le calendrier viennent de l’[API de Hebcal.com](https://www.hebcal.com/home/developer-apis) (licence CC BY 4.0). La date hébraïque est calculée par le navigateur, même sans connexion.

À la première visite, une fenêtre demande une seule fois le rite (séfarade ou ashkénaze) et l’édition à ouvrir par les liens : hébreu, phonétique ou bilingue. Si on la ferme sans choisir, le rite séfarade et l’édition bilingue sont retenus. On change ensuite de rite ou d’édition par le petit bouton à droite du titre **Prières du jour**.

Le lien **Changer de ville** ouvre les réglages :

- la ville, choisie parmi une liste, cherchée par son nom (géocodage d’[Open-Meteo](https://open-meteo.com)) ou trouvée par la position de l’appareil (nom de la ville par [BigDataCloud](https://www.bigdatacloud.com)) ;
- l’allumage des bougies : 18 minutes avant le coucher du soleil par défaut, 40 à Jérusalem ;
- la sortie de Chabbat : tombée de la nuit ou Rabbénou Tam.

Sur iPhone, autoriser le site ne suffit pas toujours : le Service de localisation doit aussi être permis à Safari (Réglages › Confidentialité et sécurité › Service de localisation › Sites Safari). En cas de refus, la page l’indique.

Pour Israël, le calendrier suit l’usage israélien (un seul jour de fête). Les réglages et la dernière réponse de Hebcal sont gardés dans le stockage du navigateur (`localStorage`), ce qui permet un affichage hors connexion. La page et son script sont dans `siddour/aujourdhui.py`.

#### Application installable (PWA)

Le site s’installe comme une application, sur téléphone comme sur ordinateur : menu du navigateur, puis **Installer l’application** ou **Ajouter à l’écran d’accueil**. Il fournit pour cela :

- un manifeste (`manifest.webmanifest`) avec les icônes, dont une version adaptée aux icônes rondes d’Android, et un raccourci vers chaque édition des deux rites et vers la page des livres ;
- un service worker (`sw.js`).

**Lecture hors connexion.** Les pages déjà lues restent disponibles. Le bouton **Garder hors ligne**, sur le sommaire de chaque édition, enregistre toute l’édition sur l’appareil.

**Mise à jour automatique.** Le nom du cache du service worker combine l’étiquette de la publication (`edition-1-revision-2`) et une empreinte de tout le site. Chaque nouvelle édition ou révision modifie donc `sw.js`. Le navigateur détecte ce changement :

- à l’ouverture d’une page ;
- au retour sur l’application ;
- toutes les heures si elle reste ouverte.

Il télécharge alors la nouvelle version, éditions gardées hors ligne comprises, puis recharge la page. Un message indique le nouveau numéro, par exemple « Siddour mis à jour : 1ʳᵉ édition, révision 1 ».

**iPhone et iPad.** Safari n’a pas de bouton d’installation. Sur iPhone et iPad, la page d’accueil explique donc la marche à suivre : **Partager › Sur l’écran d’accueil**. Une fois installée, l’application :

- s’ouvre en plein écran, avec son icône et son nom court « Siddour » ;
- place la barre d’état sur une bande bleue fixe, sans masquer le contenu sous l’encoche ; la barre des sections se colle juste dessous ;
- affiche un écran de démarrage (סידור et « Sidour » en lettres dorées sur fond bleu), adapté à chaque modèle d’iPhone et d’iPad.

**Icônes et écrans de démarrage.** Ils sont tirés de la couverture et rangés dans `assets/pwa/`. L’application sert les deux rites : on n’y garde que le titre commun à toutes les couvertures (le mot סידור, « Sidour » et le filet doré), sans le rite ni l’édition. Après un changement de couverture, les régénérer avec :

```bash
python3 -m siddour.icones
```

**Vérification.** La commande suivante fabrique le site dans un dossier temporaire et contrôle :

- les liens ;
- le référencement : titre et description propres à chaque page, un seul `h1`, canonique, image de partage et données structurées sur chaque page du sitemap ;
- l’installabilité selon Chrome ;
- la lecture hors connexion ;
- la mise à jour automatique après une nouvelle révision ;
- l’aide affichée sur iPhone ;
- la page « Aujourd’hui » (édition demandée une seule fois, liens vers le siddour, réglages gardés), le choix du rite (prières du jour et onglets du bandeau) et les livres de chaque rite en 2 × 2 sur iPhone ;
- la barre des sections qui suit le défilement et les réglages d’affichage gardés d’une page à l’autre.

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
| `siddour/rites.py` | Les deux rites : livre Sefaria, plan, couvertures, dossier du site, textes de présentation et métadonnées propres à chacun. |
| `siddour/plan.py` | Plan du rite séfarade : chapitres, sections et références Sefaria. |
| `siddour/plan_ashkenaze.py` | Plan du rite ashkénaze, d’après les parties du *Siddur Ashkenaz*. |
| `siddour/sources.py` | Téléchargement, cache, corrections ponctuelles de la source (`SOURCE_FIXES`) et mise au format séfarade du texte ashkénaze (`normalize_ashkenaze`). |
| `siddour/hebreu.py` | Nikoud, balises `<small>`/`<big>`, recherche dans le texte hébreu. |
| `siddour/consignes.py` | Traduction des consignes et découpage consigne / texte à réciter. |
| `siddour/mise_en_page.py` | Placement des consignes, variantes, encadrés et notes (`ReadingLayout`). |
| `siddour/phonetique.py` | Translittération ; cas particuliers dans `PH_WORDS`. |
| `siddour/edition.py`, `siddour/style.css` | Assemblage des EPUB et feuille de style. |
| `siddour/site.py` | Site web de lecture, métadonnées de référencement et application installable (PWA). |
| `siddour/aujourdhui.py` | Page d’accueil « Aujourd’hui » (date hébraïque, prières, horaires Hebcal, réglages) et grille des livres. |
| `siddour/icones.py`, `assets/pwa/` | Icônes, écrans de démarrage iOS et logo du bandeau, générés depuis le titre commun des couvertures ; texture du fond « papier ancien ». |
| `outils/verifier_site.py` | Vérification du site, de son référencement et de la PWA. |
| `siddour/version.py`, `siddour/publication.py` | Numéro d’édition ; outils des actions de publication (`.github/workflows/publier.yml`, `site.yml`), dont le signalement IndexNow. |

Les traductions sont des données, séparées du code (UTF-8, séparateur `;`) :

- `data/consignes.csv` : consignes, repères et références, indexés par l’hébreu sans nikoud.
- `data/intertitres.csv` : titres internes.
- `data/consignes_locales.csv` : consigne dont le sens dépend du passage (section Sefaria et numéro de paragraphe), par exemple un « אומרים » qui désigne l’officiant.

Les deux rites partagent ces tables : une consigne identique se traduit une seule fois. Une consigne absente de ces tables bloque la génération et est listée, pour qu’aucun hébreu non traduit n’apparaisse dans les livres.

### Contenu de chaque EPUB

Couverture (`assets/covers/siddour_<mode>.png`, ou `assets/covers/ashkenaze/siddour_<mode>.png`), sommaire sur deux colonnes, introduction, page « À propos de cette édition » (sources, licences, conventions), puis les 26 chapitres du rite séfarade ou les 21 du rite ashkénaze. Le texte de l’introduction et les métadonnées sont dans `siddour/edition.py` ; ce qui change d’un rite à l’autre est dans `siddour/rites.py`.

Métadonnées : titre, identifiant, langues (hébreu et français), auteur et éditeur, date, description, sujets, source Sefaria, droits et licences, série « Siddour séfarade pour liseuse » ou « Siddour ashkénaze pour liseuse » avec le numéro de l’édition (EPUB 3 et Calibre), couverture, date de modification et informations d’accessibilité. Les six livres passent EPUBCheck 5.1 sans erreur.

### Conventions de mise en page

Inspirées du Pata’h Eliyahou et de l’édition Beit Hassofer :

- La consigne figure en italique, en petit, juste avant le passage qu’elle concerne. Une consigne qui suit le passage (« deux fois », « jusqu’ici ») est collée à ce passage.
- Une répétition courte s’écrit dans la ligne : *(trois fois)*.
- Une variante brève reste dans la phrase, entre crochets, avec sa condition : *[Dix jours de pénitence : …]*. Les noms à insérer s’écrivent de la même façon : *[Untel, fils d’Untel]*.
- Un ajout long est encadré, avec la condition en en-tête et un lien « Suite de la prière ». Les rôles (zimoun, Kedoucha, bénédiction des Cohanim) sont aussi encadrés.
- Les sources (Ben Ich ’Haï, Kaf ha’Haïm…) et les précisions techniques (initiales, acrostiches) passent en notes numérotées, en fin de section, avec liens aller et retour.

## Sources et limites

Les JSON du cache conservent les références et les métadonnées des versions Sefaria : *Siddur Edot HaMizrach*, édition Shaliehsaboo (CC0), *Tanach with Nikkud* et *Torat Emet 357* (domaine public, selon les métadonnées sources). Les usages traduits suivent cette source, notamment ceux du Ben Ich ’Haï.

Le rite ashkénaze vient du *Siddur Ashkenaz* de Sefaria, qui réunit deux versions : *The Metsudah siddur, 1981* (CC-BY) et *Daat Siddur Ashkenaz* (domaine public). Chaque EPUB cite, page « À propos », les versions qu’il utilise. Les consignes traduites suivent surtout la Michna beroura. La phonétique de ce rite suit la prononciation israélienne, et non la prononciation ashkénaze traditionnelle. Les prières pour l’État et pour la communauté, vides dans la source, n’y figurent pas, ni Véyitèn lekha, faute de texte sous licence connue.

La police **Noto Serif Hebrew** est distribuée sous SIL Open Font License 1.1, reproduite dans [OFL-NotoSerifHebrew.txt](OFL-NotoSerifHebrew.txt).

La phonétique est générée automatiquement et reste approximative. Le Tétragramme y est toujours lu Adonaï, préfixe compris (laAdonaï, kaAdonaï, chèAdonaï) ; quand la source donne le ketiv suivi du qeré entre crochets, seul le qeré, la forme lue, est translittéré. Le contenu couvre le plan inclus, pas tous les offices possibles. La conservation des textes, la structure XML et les liens des six EPUB ont été vérifiés ; leur affichage exact dépend de la liseuse. Les références Pata’h Eliyahou et Beit Hassofer ont servi à guider la présentation, sans reproduire leurs textes.
