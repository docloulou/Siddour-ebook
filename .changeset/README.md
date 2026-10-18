# Changesets

Un fichier par modification du **contenu des livres**, en attente de la prochaine publication.
L’action « Publier les EPUB » les reporte dans `data/changelog.json` et `CHANGELOG.md`, sous le
numéro de la nouvelle édition, puis les efface. Les règles sont dans `AGENTS.md`.

Modèle (`.changeset/<nom-court>.md`) :

```markdown
---
niveau: revision
rites: sefarade
editions: phonetique, bilingue
chapitres: priere-du-matin, priere-du-soir
---
Corrige la phonétique du Tétragramme après le préfixe ché.

Détails facultatifs : un ou plusieurs paragraphes, repris dans le CHANGELOG, sur la page
« Modifications » du site et dans les notes de release.
```

- `niveau` : `revision` (correction) ou `edition` (changement important) ; `revision` par défaut.
- `rites` : `sefarade`, `ashkenaze` ou `tous` (défaut).
- `editions` : `hebreu`, `phonetique`, `bilingue` ou `toutes` (défaut).
- `chapitres` : identifiants du plan (`python3 siddour_ebook_liseuse.py --liste`) ou `tous` (défaut).
- Première ligne après l’en-tête : le résumé, une phrase de 160 caractères au plus, reprise
  telle quelle à la fin des EPUB et des PDF.

Vérifier : `python3 -m siddour.changements verifier`.
