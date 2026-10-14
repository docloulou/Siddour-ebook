"""Numérotation des éditions, à la manière d'un livre imprimé.

- Une nouvelle **édition** (1ʳᵉ, 2ᵉ…) marque un changement important : contenu
  ajouté, plan revu, nouvelle présentation.
- Une **révision** de la même édition corrige sans changer le livre : coquilles,
  traductions de consignes, phonétique.

La 1ʳᵉ édition commence sans révision ; une nouvelle édition remet le compteur
de révisions à zéro. Dans Git, chaque publication porte l'étiquette
« edition-<N>-revision-<M> ».
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
        'août', 'septembre', 'octobre', 'novembre', 'décembre']
TAG_RE = re.compile(r'^edition-(\d+)-revision-(\d+)$')


def date_fr(d: date) -> str:
    return ('1ᵉʳ' if d.day == 1 else str(d.day)) + ' ' + MOIS[d.month - 1] + ' ' + str(d.year)


@dataclass(frozen=True)
class Version:
    edition: int | None = None  # None : version de travail, générée hors publication
    revision: int = 0
    jour: date = field(default_factory=date.today)

    @property
    def libelle(self) -> str:
        """« 2ᵉ édition, révision 3 », « 1ʳᵉ édition » ou « Version de travail »."""
        if self.edition is None:
            return 'Version de travail'
        nom = ('1ʳᵉ' if self.edition == 1 else str(self.edition) + 'ᵉ') + ' édition'
        return nom + (', révision ' + str(self.revision) if self.revision else '')

    @property
    def complet(self) -> str:
        """Libellé suivi de la date de fabrication."""
        return self.libelle + ' — ' + date_fr(self.jour)

    @property
    def tag(self) -> str:
        return f'edition-{self.edition}-revision-{self.revision}'


def suivante(tags: list[str], increment: str) -> Version:
    """Version qui suit la plus récente des étiquettes ; « edition » ou « revision »."""
    connues = sorted((int(m[1]), int(m[2])) for m in map(TAG_RE.match, tags) if m)
    if not connues:
        return Version(1, 0)
    edition, revision = connues[-1]
    if increment == 'edition':
        return Version(edition + 1, 0)
    if increment == 'revision':
        return Version(edition, revision + 1)
    raise ValueError('incrément inconnu : ' + increment)
