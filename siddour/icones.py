"""Icônes et écrans de démarrage du site installable (PWA), tirés de la couverture.

    python3 -m siddour.icones          # régénère assets/pwa/ après un changement de couverture

Les fichiers produits sont versionnés dans assets/pwa/ ; le site les recopie tels quels.
- icone-32.png, icone-180.png (iPhone, iPad), icone-192.png, icone-512.png ;
- icone-maskable.png : variante qu'Android peut rogner en cercle ;
- ios/demarrage-<largeur>x<hauteur>.jpg : écrans affichés par iOS à l'ouverture de l'application
  (en portrait pour l'iPhone, dans les deux sens pour l'iPad) ;
- papier.jpg : texture raccordable du fond « Papier ancien » proposé au lecteur ;
- logo.png : le mot סידור doré de la couverture, en haut de chaque page.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COUVERTURE = ROOT / 'assets' / 'covers' / 'siddour_bilingue.png'
DOSSIER = ROOT / 'assets' / 'pwa'
FOND = '#0c2644'  # bleu de la couverture, aussi utilisé comme couleur de fond du manifeste

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


def titre():
    """Le haut de la couverture (le titre), en carré, sans le cadre doré."""
    from PIL import Image
    with Image.open(COUVERTURE) as im:
        im = im.convert('RGB')
        k = im.width / 400
        return im.crop(tuple(int(v * k) for v in (20, 20, 380, 380)))


def texte_dore():
    """Le titre de la couverture (hébreu, nom, mention de l'édition), sur fond transparent."""
    from PIL import Image
    with Image.open(COUVERTURE) as im:
        im = im.convert('RGB')
        k = im.width / 400
        zone = im.crop(tuple(int(v * k) for v in (50, 75, 350, 330)))
    alpha = zone.convert('L').point(lambda v: max(0, min(255, (v - 70) * 3)))
    zone.putalpha(alpha)
    return zone


def logo(hauteur: int = 120):
    """Le mot סידור doré de la couverture, détouré, pour le bandeau du site (affiché à 1/3 de sa taille)."""
    from PIL import Image
    with Image.open(COUVERTURE) as im:
        im = im.convert('RGB')
        k = im.width / 400
        zone = im.crop(tuple(int(v * k) for v in (70, 82, 340, 182)))
    zone.putalpha(zone.convert('L').point(lambda v: max(0, min(255, (v - 70) * 3))))
    zone = zone.crop(zone.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox())
    zone = zone.resize((zone.width * hauteur // zone.height, hauteur), Image.LANCZOS)
    return zone.quantize(64, method=Image.Quantize.FASTOCTREE)  # 64 couleurs : 8 Ko au lieu de 45


def adouci(image, marge: int, flou: int):
    """Masque qui fond les bords de l'image dans l'arrière-plan."""
    from PIL import Image, ImageDraw, ImageFilter
    masque = Image.new('L', image.size, 0)
    ImageDraw.Draw(masque).rectangle((marge, marge, image.width - marge, image.height - marge), fill=255)
    return masque.filter(ImageFilter.GaussianBlur(flou))


def generer(dossier: Path = DOSSIER) -> list[Path]:
    from PIL import Image, ImageFilter
    if dossier.exists():
        shutil.rmtree(dossier)
    (dossier / 'ios').mkdir(parents=True)
    carre = titre()
    faits = []

    def enregistrer(image, nom: str) -> None:
        if nom.endswith('.jpg'):  # écrans de démarrage : JPEG, dix fois plus léger que PNG
            image.save(dossier / nom, 'JPEG', quality=82, optimize=True, progressive=True)
        else:
            image.save(dossier / nom, optimize=True)
        faits.append(dossier / nom)

    for taille in (32, 180, 192, 512):
        enregistrer(carre.resize((taille, taille), Image.LANCZOS), 'icone-' + str(taille) + '.png')

    # Android peut rogner l'icône en cercle : le titre est réduit dans la zone sûre.
    fond = carre.resize((64, 64)).filter(ImageFilter.GaussianBlur(12)).resize((512, 512), Image.BICUBIC)
    s = 380
    fond.paste(carre.resize((s, s), Image.LANCZOS), ((512 - s) // 2,) * 2, adouci(Image.new('L', (s, s)), 14, 10))
    enregistrer(fond, 'icone-maskable.png')

    # Écrans de démarrage iOS : seules les lettres dorées du titre, détourées par leur
    # luminosité, sont posées sur un bleu uni ; aucun cadre ne se voit sur l'écran.
    lettres = texte_dore()
    for w, h, r in ECRANS:
        for _, lw, lh in orientations(w, h):
            W, H = lw * r, lh * r
            ecran = Image.new('RGB', (W, H), FOND)
            lw2 = int(min(W, H) * 0.6)
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
