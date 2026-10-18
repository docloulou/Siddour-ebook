# Consignes pour les agents

Siddour séfarade et ashkénaze en EPUB, PDF et site web, généré par `siddour_ebook_liseuse.py`
(code dans `siddour/`, textes Sefaria dans `cache/`, traductions des consignes dans `data/`).
Le `README.md` décrit l’installation, la fabrication et la publication.

- Tests : `python3 -m unittest discover -s tests`
- Fabrication hors ligne : `python3 siddour_ebook_liseuse.py --offline --sortie ./build`

## Toute modification du contenu des livres s’accompagne d’un changeset

Le contenu des livres, c’est ce que le lecteur voit dans un EPUB, un PDF ou une page de prière :
texte récité, consignes et leur traduction, intertitres, notes, phonétique, plan (chapitres et
sections), encadrés et liens de reprise, pages liminaires (introduction, « À propos »),
couvertures. Une modification de l’un d’eux, même d’une seule consigne, **doit** être suivie
d’un changeset dans le même commit ou la même pull request.

Ne demandent pas de changeset les changements d’architecture qui laissent les livres identiques :
site (navigation, page Aujourd’hui, PWA, référencement), actions GitHub, outils, tests,
documentation, remaniement du code sans effet sur le texte produit. Une pull request qui touche
un fichier de contenu sans changer les livres prend l’étiquette `sans-changeset`.

### Écrire le changeset

Un fichier `.changeset/<nom-court>.md` par modification (modèle dans `.changeset/README.md`) :

```markdown
---
niveau: revision
rites: ashkenaze
editions: toutes
chapitres: priere-du-matin, priere-de-l-apres-midi
---
Corrige la traduction de la consigne d’oubli de « Tal oumatar ».

Détails facultatifs : ce qui était faux, la source qui fonde la correction.
```

- **Périmètre exact** : `rites` (`sefarade`, `ashkenaze`, `tous`), `editions` (`hebreu`,
  `phonetique`, `bilingue`, `toutes`), `chapitres` (identifiants de `--liste`, ou `tous`).
  Ne déclarer que ce qui change vraiment : une correction de phonétique ne touche pas l’édition
  hébraïque, une consigne séfarade ne touche pas le rite ashkénaze.
- **`niveau`** : `revision` pour une correction (coquille, traduction, phonétique), `edition`
  pour un changement important (contenu ajouté, plan revu, nouvelle présentation). Un changeset
  `edition` empêche de publier une simple révision.
- **Résumé** : la première ligne, une phrase de 160 caractères au plus, au présent (« Corrige… »,
  « Ajoute… »). Elle est reprise telle quelle à la fin des livres : rester très succinct.
- **Détails** : facultatifs, pour le CHANGELOG, le site et les notes de release.

Vérifier avec `python3 -m siddour.changements verifier` (format, rites, éditions et chapitres
connus) ; `--base origin/main` exige en plus un changeset si la branche touche au contenu, comme
le fait l’action « Changeset » sur chaque pull request.

### Ce que deviennent les changesets

À chaque publication, l’action « Publier les EPUB » reporte les changesets en attente sous le
numéro de la nouvelle édition (`python3 -m siddour.changements publier`) :

- `data/changelog.json` : le journal, source de vérité ; `CHANGELOG.md` en est généré ;
- la page **Modifications** du site (`modifications.html`), avec le périmètre de chaque changement ;
- la page **Dernières modifications** à la fin de chaque EPUB et PDF : les trois dernières
  publications qui touchent cette édition, en une ligne par changement ;
- les notes de la release GitHub.

Ne modifier à la main ni `CHANGELOG.md` ni les entrées publiées de `data/changelog.json` ; pour
rectifier une entrée publiée, corriger `data/changelog.json` puis lancer
`python3 -m siddour.changements changelog`. Sans changeset en attente, la publication échoue :
une correction du site seul passe par « Republier le site ».
