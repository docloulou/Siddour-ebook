"""Icônes et écrans de démarrage du site installable (PWA), tirés de la couverture.

    python3 -m siddour.icones          # régénère assets/pwa/ après un changement de couverture

Les fichiers produits sont versionnés dans assets/pwa/ ; le site les recopie tels quels.
L'application est commune aux deux rites : seuls le mot סידור, la ligne « Sidour » et le filet
doré, identiques sur toutes les couvertures, en sont tirés, sans le rite ni l'édition.
- icone-32.png, icone-180.png (iPhone, iPad), icone-192.png, icone-512.png ;
- icone-maskable.png : variante qu'Android peut rogner en cercle ;
- ios/demarrage-<largeur>x<hauteur>.jpg : écrans affichés par iOS à l'ouverture de l'application
  (en portrait pour l'iPhone, dans les deux sens pour l'iPad) ;
- papier.jpg : texture raccordable du fond « Papier ancien » proposé au lecteur ;
- logo.png : le mot סידור doré de la couverture, en haut de chaque page.
"""
from __future__ import annotations

import random
import shutil
from pathlib import Path

from .rites import COVERS

ROOT = Path(__file__).resolve().parent.parent
COUVERTURE = COVERS / 'siddour_bilingue.png'
DOSSIER = ROOT / 'assets' / 'pwa'
FOND = '#0c2644'  # bleu de la couverture, fond des écrans de démarrage

# Lignes du titre communes à toutes les couvertures (en points d'une couverture large de 400) ;
# en dessous viennent le rite puis l'édition, propres à chaque livre.
HEBREU = (70, 82, 340, 180)   # le mot סידור
SIDOUR = (50, 180, 350, 208)  # « Sidour », en petites capitales
FILET = (50, 250, 350, 274)   # filet orné qui sépare le titre de l'édition

# Écrans iOS (points CSS en portrait, densité) : iOS n'affiche l'écran de démarrage
# que si une image correspond exactement à l'appareil.
ECRANS = [
    (440, 956, 3),   # iPhone 16 Pro Max
    (402, 874, 3),   # iPhone 16 Pro
    (430, 932, 3),   # iPhone 14 Pro Max, 15 Plus, 15 Pro Max, 16 Plus
    (393, 852, 3),   # iPhone 14 Pro, 15, 15 Pro, 16
    (428, 926, 3),   # iPhone 12 et 13 Pro Max, 14 Plus
    (390, 844, 3),   # iPhone 12, 13, 14, 12 et 13 Pro
    (375, 812, 3),   # iPhone X, XS, 11 Pro, 12 et 13 mini
    (414, 896, 3),   # iPhone XS Max, 11 Pro Max
    (414, 896, 2),   # iPhone XR, 11
    (414, 736, 3),   # iPhone 6 à 8 Plus
    (375, 667, 2),   # iPhone 6 à 8, SE (2ᵉ et 3ᵉ génération)
    (320, 568, 2),   # iPhone SE (1ʳᵉ génération)
    (744, 1133, 2),  # iPad mini (6ᵉ génération)
    (768, 1024, 2),  # iPad, iPad mini
    (810, 1080, 2),  # iPad (7ᵉ à 9ᵉ génération)
    (820, 1180, 2),  # iPad Air, iPad (10ᵉ génération)
    (834, 1112, 2),  # iPad Air (3ᵉ génération)
    (834, 1194, 2),  # iPad Pro 11 pouces
    (1024, 1366, 2), # iPad Pro 12,9 pouces
]


def demarrage(w: int, h: int, r: int) -> str:
    return 'ios/demarrage-' + str(w * r) + 'x' + str(h * r) + '.jpg'


def orientations(w: int, h: int) -> list[tuple[str, int, int]]:
    """L'application s'ouvre en portrait sur iPhone, dans les deux sens sur iPad."""
    sens = [('portrait', w, h)]
    return sens + [('landscape', h, w)] if w >= 744 else sens


def liens_demarrage(racine: str) -> list[str]:
    """Balises <link> des écrans de démarrage."""
    liens = []
    for w, h, r in ECRANS:
        for orientation, lw, lh in orientations(w, h):
            media = ('(device-width: ' + str(w) + 'px) and (device-height: ' + str(h) + 'px) and '
                     '(-webkit-device-pixel-ratio: ' + str(r) + ') and (orientation: ' + orientation + ')')
            liens.append('<link rel="apple-touch-startup-image" media="' + media + '" href="' + racine
                         + 'assets/' + demarrage(lw, lh, r) + '">')
    return liens


def dore(zone: tuple[int, int, int, int]):
    """Une ligne dorée de la couverture, détourée par sa luminosité, rognée au plus juste."""
    from PIL import Image
    with Image.open(COUVERTURE) as im:
        im = im.convert('RGB')
        k = im.width / 400
        ligne = im.crop(tuple(int(v * k) for v in zone))
    ligne.putalpha(ligne.convert('L').point(lambda v: max(0, min(255, (v - 70) * 3))))
    return ligne.crop(ligne.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox())


def empiler(*lignes, ecart: float = .12):
    """Lignes centrées l'une sous l'autre ; l'écart est une fraction de la hauteur de la première."""
    from PIL import Image
    pas = int(lignes[0].height * ecart)
    largeur = max(l.width for l in lignes)
    bloc = Image.new('RGBA', (largeur, sum(l.height for l in lignes) + pas * (len(lignes) - 1)), (0, 0, 0, 0))
    y = 0
    for l in lignes:
        bloc.paste(l, ((largeur - l.width) // 2, y))
        y += l.height + pas
    return bloc


def titre():
    """סידור et « Sidour » : le titre commun aux deux rites, sur fond transparent."""
    return empiler(dore(HEBREU), dore(SIDOUR))


def texte_dore():
    """Le titre commun et le filet orné de la couverture, pour les écrans de démarrage."""
    return empiler(dore(HEBREU), dore(SIDOUR), dore(FILET), ecart=.16)


def logo(hauteur: int = 120):
    """Le mot סידור doré de la couverture, détouré, pour le bandeau du site (affiché à 1/3 de sa taille)."""
    from PIL import Image
    zone = dore(HEBREU)
    zone = zone.resize((zone.width * hauteur // zone.height, hauteur), Image.LANCZOS)
    return zone.quantize(64, method=Image.Quantize.FASTOCTREE)  # 64 couleurs : 8 Ko au lieu de 45


def bleu(cote: int):
    """Le fond de la couverture : bleu nuit éclairé au centre, grain à peine visible."""
    from PIL import Image, ImageChops, ImageFilter
    alea = random.Random(613)  # graine fixe : même fichier à chaque génération
    grain = Image.frombytes('L', (48, 48), bytes(alea.randrange(256) for _ in range(48 * 48)))
    grain = grain.resize((cote, cote), Image.BICUBIC).filter(ImageFilter.GaussianBlur(cote / 256))
    halo = Image.radial_gradient('L').resize((cote, cote), Image.BICUBIC)  # 0 au centre, 255 aux bords
    centre, bord, relief = (9, 37, 68), (3, 21, 43), (.04, .06, .07)  # relevés sur la couverture
    return Image.merge('RGB', [
        ImageChops.add(halo.point(lambda v, c=c, b=b: round(c + (b - c) * min(1, v / 200))),
                       grain.point(lambda v, r=r: 64 + round((v - 128) * r)), offset=-64)
        for c, b, r in zip(centre, bord, relief)])


def icone(cote: int, part: float, sous_titre: bool = True):
    """Le titre doré centré sur le bleu ; part : largeur du titre rapportée au côté de l'icône."""
    from PIL import Image
    fond = bleu(cote)
    lettres = titre() if sous_titre else dore(HEBREU)
    w = int(cote * part)
    h = w * lettres.height // lettres.width
    lettres = lettres.resize((w, h), Image.LANCZOS)
    fond.paste(lettres, ((cote - w) // 2, (cote - h) // 2), lettres)
    return fond


def generer(dossier: Path = DOSSIER) -> list[Path]:
    from PIL import Image
    if dossier.exists():
        shutil.rmtree(dossier)
    (dossier / 'ios').mkdir(parents=True)
    faits = []

    def enregistrer(image, nom: str) -> None:
        if nom.endswith('.jpg'):  # écrans de démarrage : JPEG, dix fois plus léger que PNG
            image.save(dossier / nom, 'JPEG', quality=82, optimize=True, progressive=True)
        else:
            image.save(dossier / nom, optimize=True)
        faits.append(dossier / nom)

    carre = icone(512, .72)
    for taille in (180, 192, 512):
        enregistrer(carre.resize((taille, taille), Image.LANCZOS), 'icone-' + str(taille) + '.png')
    # Onglet du navigateur : « Sidour » serait illisible, seul le mot hébreu reste.
    enregistrer(icone(512, .86, sous_titre=False).resize((32, 32), Image.LANCZOS), 'icone-32.png')
    # Android peut rogner l'icône en cercle : le titre tient dans la zone sûre (cercle de 80 %).
    enregistrer(icone(512, .58), 'icone-maskable.png')

    # Écrans de démarrage iOS : seules les lettres dorées du titre, détourées par leur
    # luminosité, sont posées sur un bleu uni ; aucun cadre ne se voit sur l'écran.
    lettres = texte_dore()
    for w, h, r in ECRANS:
        for _, lw, lh in orientations(w, h):
            W, H = lw * r, lh * r
            ecran = Image.new('RGB', (W, H), FOND)
            lw2 = int(min(W, H) * 0.55)
            lh2 = lw2 * lettres.height // lettres.width
            image = lettres.resize((lw2, lh2), Image.LANCZOS)
            ecran.paste(image, ((W - lw2) // 2, (H - lh2) // 2), image)
            enregistrer(ecran, demarrage(lw, lh, r))
    enregistrer(papier(), 'papier.jpg')
    enregistrer(logo(), 'logo.png')
    return faits


def papier(cote: int = 512):
    """Papier vergé ancien : grain marbré, fibres, vergeures et pontuseaux, à peine visibles.

    L'image se raccorde sur ses quatre bords (répétée en fond de page sans couture) :
    tout est dessiné sur une mosaïque 3 × 3 dont on garde la case centrale."""
    import random
    from PIL import Image, ImageDraw, ImageFilter
    alea = random.Random(1492)  # graine fixe : même fichier à chaque génération
    grand = cote * 3

    def raccord(case):
        mosaique = Image.new(case.mode, (grand, grand))
        for i in range(3):
            for j in range(3):
                mosaique.paste(case, (i * cote, j * cote))
        return mosaique

    def bruit(taille: int, flou: float):
        case = Image.effect_noise((taille, taille), 64).resize((cote, cote), Image.BICUBIC)
        return raccord(case).filter(ImageFilter.GaussianBlur(flou)).crop((cote, cote, 2 * cote, 2 * cote))

    # Grain : taches larges et douces, puis grain fin.
    taches = Image.blend(bruit(6, cote / 12), bruit(16, cote / 40), .5).point(lambda v: 128 + (v - 128) * 2)
    grain = bruit(cote // 2, .6)
    relief = Image.blend(taches, grain, .4)

    # Fibres et vergeures sur la case centrale de la mosaïque, recopiées sur les bords.
    traits = Image.new('L', (cote, cote), 128)
    d = ImageDraw.Draw(traits)
    for y in range(0, cote, 6):  # vergeures : lignes serrées horizontales
        d.line((0, y, cote, y), fill=112)
    for x in range(cote // 8, cote, cote // 2):  # pontuseaux : deux lignes verticales espacées
        d.line((x, 0, x, cote), fill=100, width=2)
    traits = raccord(traits)
    d = ImageDraw.Draw(traits)
    for _ in range(220):  # fibres : courts traits courbes, clairs ou sombres
        x, y = alea.uniform(cote, 2 * cote), alea.uniform(cote, 2 * cote)
        points = [(x, y)]
        for _ in range(4):
            x += alea.uniform(-9, 9); y += alea.uniform(-9, 9)
            points.append((x, y))
        teinte = alea.choice((90, 100, 165))
        for dx in (-cote, 0, cote):
            for dy in (-cote, 0, cote):
                d.line([(px + dx, py + dy) for px, py in points], fill=teinte, width=1)
    traits = traits.filter(ImageFilter.GaussianBlur(.7)).crop((cote, cote, 2 * cote, 2 * cote))

    relief = Image.blend(relief, traits, .45)
    # Teinte parchemin : le relief module légèrement une couleur ivoire chaude.
    clair, sombre = (247, 238, 214), (226, 208, 166)
    return Image.merge('RGB', [relief.point(lambda v, a=a, b=b: round(b + (a - b) * min(1, max(0, (v - 50) / 156))))
                               for a, b in zip(clair, sombre)])


if __name__ == '__main__':
    fichiers = generer()
    taille = sum(f.stat().st_size for f in fichiers)
    print(len(fichiers), 'fichiers dans', DOSSIER.relative_to(ROOT), '|', round(taille / 1e6, 1), 'Mo')
