#!/usr/bin/env python3
"""
Siddour séfarade (Edot HaMizrah) pour liseuse : trois éditions EPUB
(hébreu, phonétique, hébreu suivi de phonétique), consignes en français.

    python3 siddour_ebook_liseuse.py --offline --cache ./cache --sortie ./dist
    python3 siddour_ebook_liseuse.py --help

Le code est dans le paquet siddour/ :
    plan.py         chapitres et sections
    sources.py      textes Sefaria (cache hors ligne)
    hebreu.py       nikoud, balises de la source
    phonetique.py   phonétique, dans la prononciation du rite (rites.py)
    consignes.py    traductions françaises (data/consignes.csv, data/intertitres.csv)
    mise_en_page.py rattachement des consignes aux passages
    edition.py      assemblage EPUB ; style.css pour l'apparence

Tests de non-régression : python3 -m unittest discover -s tests
"""
from siddour.cli import main

if __name__ == '__main__':
    main()
