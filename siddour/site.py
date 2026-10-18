"""Site web de lecture (GitHub Pages) : les éditions de chaque rite consultables dans un navigateur.

Arborescence produite :
    index.html                         accueil « Aujourd'hui » : date hébraïque, prières et horaires du jour
    livres.html                        les éditions : lecture en ligne, téléchargements EPUB et PDF
    <mode>/index.html                  sommaire d'une édition séfarade
    <mode>/<chapitre>/<section>.html   une page par section, comme dans l'EPUB
    ashkenaze/<mode>/...               les éditions ashkénazes, rangées de la même façon
    telecharger/*.epub, *.pdf, assets/, sitemap.xml, robots.txt, 404.html, <clé IndexNow>.txt, CNAME
    manifest.webmanifest, sw.js, hors-ligne.html   application installable (PWA)
Les ancres internes (notes, « Suite de la prière ») restent propres à chaque page.

Le service worker porte le numéro de l'édition et une empreinte du contenu : toute
nouvelle publication le modifie, le navigateur l'installe et la page se recharge.
"""
from __future__ import annotations

import hashlib
import html
import io
import json
import re
import shutil
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin

from .edition import (CSS, FONT_PATH, SITE_URL, TITLES, Livre, cover_image, description, exposants, introduction,
                      make_contents, make_credits)
from .hebreu import NIKUD_RE
from .publication import INDEXNOW
from .rites import Rite
from .aujourdhui import AUJOURDHUI_CSS, AUJOURDHUI_JS, CIBLES, LIVRES_CSS, corps
from .icones import DOSSIER as ICONES, generer as generer_icones, liens_demarrage
from .version import date_fr

SITE_NAME = 'Siddour séfarade et ashkénaze'
TAGLINE = 'Le livre de prière des rites séfarade (Edot HaMizrah) et ashkénaze, à lire en ligne ou sur liseuse'
# Descriptions : 160 caractères au plus, ce que les moteurs affichent sous le titre.
SITE_DESCRIPTION = ('Siddour séfarade (Edot HaMizrah) et ashkénaze gratuit, à lire en ligne ou en EPUB pour liseuse : '
                    'hébreu vocalisé, phonétique ou les deux, consignes en français.')
LIMITE_TITRE, LIMITE_DESCRIPTION = 70, 160
EDITIONS = {'hebreu': 'Édition hébraïque', 'phonetique': 'Édition phonétique',
            'bilingue': 'Édition hébreu et phonétique'}
TEXTE = {'hebreu': 'en hébreu vocalisé', 'phonetique': 'en phonétique',
         'bilingue': 'en hébreu vocalisé et en phonétique'}
# Robots des IA, autorisés explicitement dans robots.txt (en plus de « User-agent: * »).
ROBOTS_IA = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-SearchBot', 'Claude-User',
             'anthropic-ai', 'Google-Extended', 'GoogleOther', 'Applebot-Extended', 'PerplexityBot',
             'Perplexity-User', 'Meta-ExternalAgent', 'Meta-ExternalFetcher', 'CCBot', 'Amazonbot',
             'Bytespider', 'cohere-ai', 'MistralAI-User', 'DuckAssistBot', 'YouBot', 'Diffbot']
MENU = {'hebreu': 'Hébreu', 'phonetique': 'Phonétique', 'bilingue': 'Bilingue'}
# Le texte de l'édition en peu de mots, pour les titres des pages.
EN = {'hebreu': 'en hébreu', 'phonetique': 'en phonétique', 'bilingue': 'en hébreu et phonétique'}
# Mots-clés (balise keywords) : Google les ignore, Bing, Yandex ou Qwant s'en servent encore un peu.
# Les mots communs à toutes les pages, puis ceux de chaque édition ; chaque page y ajoute les siens.
MOTS_CLES = ('siddour', 'sidour', 'siddur', 'livre de prière juif', 'prière juive')
MOTS_EDITION = {'hebreu': ('siddour hébreu', 'hébreu vocalisé', 'tefila'),
                'phonetique': ('siddour phonétique', 'prière en phonétique', 'translittération'),
                'bilingue': ('siddour bilingue', 'hébreu et phonétique', 'translittération')}
DEPOT = 'docloulou/Siddour-ebook'  # dépôt GitHub, lien « Contribuer » du pied de page
# Adresse de contact, à l'envers et en base64 : absente en clair du dépôt comme des pages.
# Le script de la page la reconstitue seulement quand le lecteur clique.
# Fichiers copiés tels quels à la racine du site : validation Google Search Console, Bing…
RACINE = Path(__file__).resolve().parent.parent / 'assets' / 'racine'
CONTACT = 'aHZvLmJyekBrb29iZS1ydW9kZGlz'

WEB_CSS = '''
@font-face { font-family: "SiddurHebrew"; src: url("FONT_URL") format("truetype"); font-display: swap; }
/* Fond bleu sous la page : en application sur iPhone, la barre d'état transparente prend la couleur
   du fond du document ; crème, elle voilait le haut du bandeau. La page garde son fond crème. */
html { -webkit-text-size-adjust: 100%; scroll-padding-top: 3.5em; background: #15284a; }
html:has(.site-head.colle) { scroll-padding-top: 6em; }
body { margin: 0; background: #fbf9f4; color: #1d1d1d; font-size: 1.12em; min-height: 100vh; min-height: 100dvh; }
/* Bande bleue fixe sous la barre d'état (heure, batterie) : le texte défile dessous sans s'y mêler. */
body::before { content: ""; position: fixed; top: 0; left: 0; right: 0; z-index: 9; height: env(safe-area-inset-top);
               background: #0c2644; pointer-events: none; }
/* --taille : réglage « Affichage » du lecteur (1 = taille normale). */
main { max-width: 40em; margin: 0 auto; padding: 1rem 1.2rem 3rem; background: #fff;
       font-size: calc(var(--taille, 1) * 1em); }
a { color: #1f3a68; }
/* Bandeau du site : logo doré de la couverture et nom, bouton « Affichage », puis les onglets. */
.site-head { background: #15284a linear-gradient(180deg, #0c2644, #15284a) no-repeat 0 env(safe-area-inset-top); color: #f1e4bf;
             font: .95em/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; border-bottom: 1px solid #a8873a;
             padding: env(safe-area-inset-top) env(safe-area-inset-right) 0 env(safe-area-inset-left); }
.site-head .inner { max-width: 44em; margin: 0 auto; padding: .6em 1.2em 0; display: grid;
                    grid-template-columns: minmax(0, 1fr) auto; gap: 0 1em; align-items: center; }
.site-head a { color: #f1e4bf; text-decoration: none; }
.site-head .marque { display: flex; align-items: center; gap: .75em; justify-self: start; min-width: 0; max-width: 100%; }
.site-head .marque img { display: block; height: 2.2em; width: auto; filter: drop-shadow(0 1px 1px rgba(0,0,0,.45)); }
.site-head .nom { font: 600 1.08em/1.15 Georgia, "Times New Roman", serif; letter-spacing: .02em; min-width: 0;
                  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.site-head .nom small { display: block; margin-top: .15em; font: .66em/1.2 system-ui, -apple-system, "Segoe UI", sans-serif;
                        letter-spacing: .12em; text-transform: uppercase; color: #d9b45a; }
.site-head .menu { grid-column: 1 / -1; display: flex; gap: .3em; margin: .5em 0 0; }
.site-head .menu a { padding: .4em .75em .45em; border-bottom: 3px solid transparent; color: rgba(241,228,191,.8); }
.site-head .menu a:hover { color: #fff; }
.site-head .menu a.actif { color: #fff; font-weight: 600; border-bottom-color: #d9b45a; }
/* Onglet « Aujourd'hui » : un petit calendrier, avant les livres. */
.site-head .menu .jour { flex: 0 0 auto; display: flex; align-items: center; }
.site-head .menu .jour svg { display: block; width: 1.25em; height: 1.25em; }
/* Bandeau qui reste en haut de l'écran : sur les pages de lecture, la barre des sections
   (précédente, aller à…, suivante) ; ailleurs, le bandeau du site lui-même.
   La barre se colle juste sous la barre d'état de l'iPhone : pas de bande vide sous le bandeau du site. */
.site-head.colle, .barre { position: -webkit-sticky; position: sticky; top: 0; z-index: 5; }
.barre { top: env(safe-area-inset-top); background: #15284a; color: #f1e4bf; font: .95em/1.4 sans-serif;
         border-top: 1px solid #2c4470; box-shadow: 0 1px 6px rgba(0,0,0,.25);
         padding: 0 env(safe-area-inset-right) 0 env(safe-area-inset-left); }
.barre .inner { max-width: 44em; margin: 0 auto; padding: .35em 1.2em; display: flex; gap: .5em;
                align-items: center; position: relative; }
.barre a, .barre .vide { color: #f1e4bf; text-decoration: none; font-size: 1.5em; line-height: 1; padding: 0 .25em; }
.barre .vide { opacity: .3; }
.barre select { flex: 1; min-width: 0; font: inherit; font-size: .9em; color: #15284a; background: #f1e4bf;
                border: 0; border-radius: 3px; padding: .3em .4em; text-overflow: ellipsis; }
.site-head .inner { position: relative; }
/* Bouton « Affichage » : discret mais lisible, et son panneau de réglages. */
.aa { font: bold .95em/1.2 sans-serif; color: #f1e4bf; background: none; border: 1px solid rgba(241,228,191,.55);
      border-radius: 1em; padding: .2em .75em; cursor: pointer; white-space: nowrap; }
.aa span { font-weight: normal; }
.aa[aria-expanded="true"] { background: #f1e4bf; color: #15284a; }
.reglages { position: absolute; right: .6em; top: calc(100% + .3em); z-index: 6; width: 19em;
            max-width: calc(100vw - 1.2em); box-sizing: border-box; padding: .8em 1em; border-radius: 6px;
            background: #fffdf7; color: #222; border: 1px solid #d8cfb8; box-shadow: 0 4px 18px rgba(0,0,0,.25);
            font: .9em/1.3 sans-serif; text-align: left; }
.reglages[hidden] { display: none; }
.reglages .ligne { display: flex; align-items: center; justify-content: space-between; gap: .6em; margin: .55em 0; }
.reglages .ligne > span { color: #555; }
.reglages .choix { display: flex; gap: .3em; align-items: center; }
.reglages button { font: inherit; color: #15284a; background: #fff; border: 1px solid #c9bfa6; border-radius: 4px;
                   min-width: 2.3em; height: 2.1em; padding: 0 .45em; cursor: pointer; }
.reglages button[aria-pressed="true"] { border-color: #15284a; box-shadow: inset 0 0 0 1px #15284a; background: #eef1f7; }
.reglages button svg { width: 1.15em; height: 1.15em; vertical-align: middle; }
.reglages output { min-width: 3.2em; text-align: center; }
.reglages .fond { width: 2.1em; padding: 0; }
.reglages .fond[data-v="blanc"] { background: #fff; }
.reglages .fond[data-v="ivoire"] { background: #fcf5df; }
.reglages .fond[data-v="papier"] { background: #ecdcb4 url("papier.jpg"); }
.reglages .remise { display: block; margin: .8em 0 0 auto; height: auto; padding: .25em .6em; font-size: .9em; color: #555; }
/* Alignements choisis par le lecteur (par défaut : hébreu à droite, phonétique justifiée). */
html[data-he="justify"] main .he { text-align: justify; text-align-last: auto; }
html[data-he="center"] main .he { text-align: center; text-align-last: center; }
html[data-he="left"] main .he { text-align: left; text-align-last: left; }
html[data-ph="left"] main .ph { text-align: left; text-align-last: left; }
html[data-ph="center"] main .ph { text-align: center; text-align-last: center; }
html[data-ph="right"] main .ph { text-align: right; text-align-last: right; }
/* Fonds : ivoire (jaune pâle) et papier ancien vergé ; blanc par défaut. */
html[data-fond="ivoire"] body { background: #efe6cb; }
html[data-fond="ivoire"] main { background: #fcf5df; }
html[data-fond="papier"] body { background: #d8c79f; }
html[data-fond="papier"] main { background: #f1e5c6 url("papier.jpg"); color: #2a2116;
                                 box-shadow: inset 0 0 4em rgba(110,75,25,.2); }
html[data-fond="ivoire"] .site-foot, html[data-fond="papier"] .site-foot { color: #5a5040; }
html[data-fond="ivoire"] main .addition, html[data-fond="ivoire"] main .choice, html[data-fond="ivoire"] main .role,
html[data-fond="papier"] main .addition, html[data-fond="papier"] main .choice, html[data-fond="papier"] main .role {
  background: rgba(120,90,30,.07); border-color: rgba(120,90,30,.4); }
.fil { font: .85em sans-serif; color: #666; margin: .6em 0 0; }
/* Pages de section : le chapitre garde l'aspect d'un grand titre, la section (titre de niveau 1 de la page)
   celui d'un titre de niveau 2 du livre. Sommaire : « Sommaire » garde l'aspect d'un grand titre. */
main .titre-chapitre, main h2.sommaire-titre { font-size: 1.4em; font-weight: bold; text-align: center; margin: 1em 0;
                                              border: 0; padding: 0; }
main h1.titre-section { font-size: 1.2em; text-align: inherit; margin: .83em 0; border-bottom: 1px solid #000;
                        padding-bottom: .3em; }
.fil a { color: #666; }
.pager { display: flex; justify-content: space-between; gap: 1em; margin: 2.5em 0 0; padding-top: 1em;
         border-top: 1px solid #ddd; font: .92em/1.4 sans-serif; }
.pager a { text-decoration: none; max-width: 48%; }
.pager .suiv { margin-left: auto; text-align: right; }
.site-foot { max-width: 40em; margin: 0 auto; padding: 1.2em 1.2em calc(1.2em + env(safe-area-inset-bottom)); font: .8em/1.5 sans-serif; color: #666;
             text-align: center; }
.editions { display: grid; grid-template-columns: repeat(auto-fit, minmax(11em, 1fr)); gap: 1.4em; margin: 1.5em 0; }
.edition-carte { text-align: center; font-family: sans-serif; }
.edition-carte img { width: 100%; height: auto; border-radius: 4px; box-shadow: 0 2px 10px rgba(0,0,0,.25); }
.edition-carte h2 { border: 0; font-size: 1.02em; margin: .6em 0 .2em; }
.edition-carte p { margin: .25em 0; font-size: .9em; }
.bouton { display: inline-block; padding: .35em .9em; border-radius: 3px; background: #15284a; color: #f1e4bf;
          text-decoration: none; }
.bouton.second { background: none; color: #15284a; border: 1px solid #15284a; }
.accroche { text-align: center; font-style: italic; color: #444; }
.autre-rite { text-align: center; font: .9em/1.5 sans-serif; color: #555; margin: .5em 0; }
button.bouton { font: inherit; cursor: pointer; }
.hors-ligne { text-align: center; font-size: .95em; color: #555; }
.installer-ios { margin: 1em 0; padding: .7em 1em; border: 1px solid #d8cfb8; border-radius: 4px; background: #f6f0e1;
                 font: .9em/1.5 sans-serif; text-align: center; }
.hors-ligne span { display: block; margin-top: .3em; font: .85em/1.4 sans-serif; }
.annonce { position: fixed; left: 50%; bottom: calc(1.2em + env(safe-area-inset-bottom)); transform: translateX(-50%); z-index: 10;
           max-width: calc(100% - 2.4em); padding: .7em 1.1em; border-radius: 4px; background: #15284a;
           color: #f1e4bf; font: .9em/1.4 sans-serif; box-shadow: 0 2px 12px rgba(0,0,0,.3); }
/* Lecture à l'écran : phonétique justifiée comme dans un livre, dernière ligne à gauche. */
.ph { text-align: justify; text-align-last: left; -webkit-hyphens: auto; hyphens: auto; }
@media (max-width: 34em) { .sommaire { column-count: 1; -webkit-column-count: 1; } body { font-size: 1.05em; }
                           .aa span { display: none; } .site-head .inner { padding: .55em .9em 0; }
                           .site-head .menu { gap: 0; margin-top: .35em; }
                           .site-head .menu a { flex: 1 1 auto; text-align: center; padding: .4em .1em .45em; }
                           .site-head .marque { gap: .55em; } .site-head .marque img { height: 1.9em; }
                           .barre .inner { padding: .35em .8em; } }
@media (max-width: 22em) { .site-head .nom small { letter-spacing: .06em; } }
'''

# Script commun aux pages : inscription du service worker, annonce de mise à jour,
# bouton « Garder hors ligne » sur le sommaire de chaque édition.
APP_JS = r'''"use strict";
(() => {
  const VERSION = __VERSION__;
  const script = document.currentScript;

  // Contact : l'adresse n'est reconstituée qu'au clic, hors de portée des robots qui lisent les pages.
  const contact = document.querySelector(".contact");
  if (contact) {
    contact.hidden = false;
    contact.querySelector("a").addEventListener("click", (e) => {
      const a = e.currentTarget;
      if (a.href.startsWith("mailto:")) return;
      e.preventDefault();
      const adresse = atob(contact.dataset.c).split("").reverse().join("");
      a.href = "mailto:" + adresse + "?subject=" + encodeURIComponent("Siddour");
      a.textContent = adresse;
      location.href = a.href;
    });
  }

  // Pages communes (accueil, livres) : les onglets des éditions mènent au rite choisi dans « Aujourd'hui ».
  const PREFIXES = __PREFIXES__;
  const onglets = () => {
    let rite;
    try { rite = (JSON.parse(localStorage.getItem("siddour-jour")) || {}).rite; } catch (e) {}
    if (!script || !(rite in PREFIXES)) return;
    document.querySelectorAll(".menu a[data-mode]").forEach((a) => {
      a.href = new URL("../" + PREFIXES[rite] + a.dataset.mode + "/index.html", script.src).href;
    });
  };
  onglets();
  document.addEventListener("siddour-rite", onglets);

  // Barre des sections : aller directement à une section choisie dans la liste.
  const aller = document.querySelector(".barre select");
  if (aller) aller.addEventListener("change", () => { if (aller.value) location.href = aller.value; });

  // Affichage : taille du texte, alignement de l'hébreu et de la phonétique, fond de page.
  // Le choix est gardé sur l'appareil ; le script en tête de page l'applique avant l'affichage.
  const aa = document.querySelector(".aa");
  if (aa) {
    const racine = document.documentElement;
    const TAILLES = [0.8, 0.9, 1, 1.1, 1.25, 1.4, 1.6, 1.8, 2.1];
    const DEFAUT = { taille: 1, he: "right", ph: "justify", fond: "blanc" };
    let reglages = {};
    try { reglages = JSON.parse(localStorage.getItem("siddour-affichage")) || {}; } catch (e) {}
    const valeur = (cle) => reglages[cle] === undefined ? DEFAUT[cle] : reglages[cle];
    const icone = (lignes) => '<svg viewBox="0 0 16 16" aria-hidden="true">' + lignes.map(([x, l], i) =>
      '<rect x="' + x + '" y="' + (2 + i * 3.5) + '" width="' + l + '" height="1.6" rx=".8" fill="currentColor"/>').join("") + "</svg>";
    const ALIGNEMENTS = [
      ["right", "Aligné à droite", icone([[1, 14], [5, 10], [3, 12], [7, 8]])],
      ["justify", "Justifié", icone([[1, 14], [1, 14], [1, 14], [1, 9]])],
      ["center", "Centré", icone([[1, 14], [4, 8], [2, 12], [5, 6]])],
      ["left", "Aligné à gauche", icone([[1, 14], [1, 10], [1, 12], [1, 8]])],
    ];
    const choix = (cle, options) => '<div class="choix" role="group">' + options.map(([v, nom, contenu, classe]) =>
      '<button type="button" data-cle="' + cle + '" data-v="' + v + '" title="' + nom + '" aria-label="' + nom + '"'
      + (classe ? ' class="' + classe + '"' : "") + ">" + contenu + "</button>").join("") + "</div>";
    const panneau = document.createElement("div");
    panneau.className = "reglages"; panneau.id = "reglages"; panneau.hidden = true;
    panneau.setAttribute("role", "dialog"); panneau.setAttribute("aria-label", "Affichage");
    panneau.innerHTML =
      '<div class="ligne"><span>Taille du texte</span><div class="choix">'
      + '<button type="button" data-pas="-1" title="Réduire" aria-label="Réduire le texte">A−</button><output></output>'
      + '<button type="button" data-pas="1" title="Agrandir" aria-label="Agrandir le texte">A+</button></div></div>'
      + '<div class="ligne"><span>Hébreu</span>' + choix("he", ALIGNEMENTS) + "</div>"
      + '<div class="ligne"><span>Phonétique</span>' + choix("ph", ALIGNEMENTS) + "</div>"
      + '<div class="ligne"><span>Fond de page</span>' + choix("fond", [["blanc", "Blanc", "", "fond"],
        ["ivoire", "Ivoire", "", "fond"], ["papier", "Papier ancien", "", "fond"]]) + "</div>"
      + '<button type="button" class="remise">Réglages par défaut</button>';
    aa.parentNode.appendChild(panneau);
    const appliquer = () => {
      for (const cle of ["he", "ph", "fond"]) {
        if (reglages[cle] && reglages[cle] !== DEFAUT[cle]) racine.dataset[cle] = reglages[cle];
        else delete racine.dataset[cle];
      }
      if (valeur("taille") !== 1) racine.style.setProperty("--taille", valeur("taille"));
      else racine.style.removeProperty("--taille");
      panneau.querySelector("output").textContent = Math.round(valeur("taille") * 100) + " %";
      panneau.querySelectorAll("[data-cle]").forEach((b) =>
        b.setAttribute("aria-pressed", String(valeur(b.dataset.cle) === b.dataset.v)));
      try { localStorage.setItem("siddour-affichage", JSON.stringify(reglages)); } catch (e) {}
    };
    panneau.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      if (b.dataset.cle) reglages[b.dataset.cle] = b.dataset.v;
      else if (b.dataset.pas) {
        const i = TAILLES.indexOf(valeur("taille"));
        reglages.taille = TAILLES[Math.max(0, Math.min(TAILLES.length - 1, (i < 0 ? 2 : i) + Number(b.dataset.pas)))];
      } else reglages = {};
      appliquer();
    });
    const ouvrir = (oui) => { panneau.hidden = !oui; aa.setAttribute("aria-expanded", String(oui)); };
    aa.addEventListener("click", () => ouvrir(panneau.hidden));
    document.addEventListener("click", (e) => { if (!panneau.hidden && !panneau.contains(e.target) && !aa.contains(e.target)) ouvrir(false); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !panneau.hidden) { ouvrir(false); aa.focus(); } });
    appliquer();
    aa.hidden = false;
  }

  if (!("serviceWorker" in navigator) || !script) return;
  const annonce = (texte) => {
    const div = document.createElement("div");
    div.className = "annonce"; div.setAttribute("role", "status"); div.textContent = texte;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 6000);
  };
  try {
    if (sessionStorage.getItem("siddour-maj")) {
      sessionStorage.removeItem("siddour-maj");
      annonce("Siddour mis à jour : " + VERSION);
    }
  } catch (e) {}

  // Nouvelle édition ou révision : le nouveau service worker prend la main, on recharge.
  const avait = !!navigator.serviceWorker.controller;
  let recharge = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!avait || recharge) return;
    recharge = true;
    try { sessionStorage.setItem("siddour-maj", "1"); } catch (e) {}
    location.reload();
  });
  navigator.serviceWorker.register(new URL("../sw.js", script.src), { updateViaCache: "none" }).then((reg) => {
    const verifier = () => reg.update().catch(() => {});
    setInterval(verifier, 3600 * 1000);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) verifier(); });
  }).catch(() => {});

  // Safari sur iPhone et iPad n'a pas de bouton d'installation : on explique la marche à suivre.
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const aide = document.querySelector(".installer-ios");
  if (aide && ios && !navigator.standalone) aide.hidden = false;

  const bouton = document.querySelector("[data-hors-ligne]");
  if (!bouton || !("caches" in window)) return;
  const mode = bouton.dataset.horsLigne;
  const etat = document.querySelector(".hors-ligne span");
  const marque = new URL("../hors-ligne/" + mode, script.src).href;
  let garde = false;
  const afficher = (oui) => {
    garde = oui;
    bouton.textContent = oui ? "Ne plus garder hors ligne" : "Garder hors ligne";
    etat.textContent = oui ? "✓ Cette édition se lit sans connexion." : "";
  };
  caches.open("siddour-reglages").then((c) => c.match(marque)).then((r) => afficher(!!r));
  bouton.hidden = false;
  navigator.serviceWorker.addEventListener("message", (e) => {
    const m = e.data || {};
    if (m.mode !== mode) return;
    if (m.type === "progression") etat.textContent = "Téléchargement : " + m.n + " / " + m.total + " pages…";
    if (m.type === "fini") {
      bouton.disabled = false;
      if (m.ok) afficher(m.garde);
      else etat.textContent = "Téléchargement interrompu ; réessayer avec une connexion.";
    }
  });
  bouton.addEventListener("click", () => {
    bouton.disabled = true;
    navigator.serviceWorker.ready.then((reg) => reg.active.postMessage({ type: garde ? "retirer" : "garder", mode }));
  });
})();
'''

# Applique les réglages d'affichage du lecteur dès la tête de page, avant le premier rendu.
AFFICHAGE_JS = ('<script>try{var a=JSON.parse(localStorage.getItem("siddour-affichage"))||{},d=document.documentElement;'
                '["he","ph","fond"].forEach(function(k){if(a[k])d.dataset[k]=a[k]});'
                'if(a.taille)d.style.setProperty("--taille",a.taille)}catch(e){}</script>')
# Petit calendrier (onglet « Aujourd'hui » du bandeau), dessiné au trait dans la couleur du texte.
CALENDRIER = ('<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" '
              'stroke-linecap="round"><rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>'
              '<path d="M7.5 14h2M11 14h2M14.5 14h2M7.5 17h2M11 17h2" stroke-width="2"/></svg>')

BOUTON_AA = ('<button class="aa" type="button" aria-expanded="false" aria-controls="reglages" hidden '
             'title="Affichage : taille du texte, alignement, fond de page">Aa<span> Affichage</span></button>')

SW_JS = r'''"use strict";
// Service worker du siddour. CACHE change à chaque publication : le navigateur
// détecte la nouvelle version, l'installe et remplace l'ancienne.
const CACHE = "siddour-" + __CACHE__;
const REGLAGES = "siddour-reglages";
const COQUILLE = __COQUILLE__;
const EDITIONS = __EDITIONS__;
const base = self.registration.scope;
const url = (p) => new URL(p, base).href;
const marque = (mode) => url("hors-ligne/" + mode);

async function garder(cache, mode, client) {
  const pages = EDITIONS[mode];
  let erreurs = 0;
  for (let i = 0; i < pages.length; i += 8) {
    await Promise.all(pages.slice(i, i + 8).map((p) =>
      cache.add(new Request(url(p), { cache: "reload" })).catch(() => { erreurs += 1; })));
    if (client) client.postMessage({ type: "progression", mode, n: Math.min(i + 8, pages.length), total: pages.length });
  }
  return erreurs === 0;
}

self.addEventListener("install", (e) => e.waitUntil((async () => {
  const cache = await caches.open(CACHE);
  await cache.addAll(COQUILLE.map((p) => new Request(url(p), { cache: "reload" })));
  // Les éditions gardées hors ligne sont rechargées dans leur nouvelle version.
  const reglages = await caches.open(REGLAGES);
  for (const mode of Object.keys(EDITIONS)) {
    if (await reglages.match(marque(mode))) await garder(cache, mode);
  }
  await self.skipWaiting();
})()));

self.addEventListener("activate", (e) => e.waitUntil((async () => {
  for (const nom of await caches.keys()) {
    if (nom.startsWith("siddour-") && nom !== CACHE && nom !== REGLAGES) await caches.delete(nom);
  }
  await self.clients.claim();
})()));

async function page(e) {
  try {
    const reponse = await fetch(e.request);
    if (reponse.ok && !reponse.redirected) {
      const copie = reponse.clone();
      e.waitUntil(caches.open(CACHE).then((c) => c.put(e.request, copie)));
    }
    return reponse;
  } catch (err) {
    const u = new URL(e.request.url);
    u.search = ""; u.hash = "";
    return (await caches.match(u.href, { cacheName: CACHE }))
      || (u.pathname.endsWith("/") && await caches.match(u.href + "index.html", { cacheName: CACHE }))
      || caches.match(url("hors-ligne.html"), { cacheName: CACHE });
  }
}

async function fichier(e) {
  const trouve = await caches.match(e.request, { cacheName: CACHE });
  if (trouve) return trouve;
  const reponse = await fetch(e.request);
  if (reponse.ok) {
    const copie = reponse.clone();
    e.waitUntil(caches.open(CACHE).then((c) => c.put(e.request, copie)));
  }
  return reponse;
}

self.addEventListener("fetch", (e) => {
  const r = e.request;
  // Les EPUB et les PDF se téléchargent toujours depuis le réseau.
  if (r.method !== "GET" || !r.url.startsWith(base) || /\.(epub|pdf)$/.test(new URL(r.url).pathname)) return;
  e.respondWith(r.mode === "navigate" ? page(e) : fichier(e));
});

self.addEventListener("message", (e) => {
  const { type, mode } = e.data || {};
  if (!EDITIONS[mode] || !e.source) return;
  e.waitUntil((async () => {
    const reglages = await caches.open(REGLAGES);
    const cache = await caches.open(CACHE);
    if (type === "garder") {
      const ok = await garder(cache, mode, e.source);
      if (ok) await reglages.put(marque(mode), new Response("1"));
      e.source.postMessage({ type: "fini", mode, ok, garde: ok });
    } else if (type === "retirer") {
      await reglages.delete(marque(mode));
      const coquille = new Set(COQUILLE);
      await Promise.all(EDITIONS[mode].filter((p) => !coquille.has(p)).map((p) => cache.delete(url(p))));
      e.source.postMessage({ type: "fini", mode, ok: true, garde: false });
    }
  })());
});
'''


def slug(text: str) -> str:
    text = unicodedata.normalize('NFKD', text.replace('’', '').replace("'", ''))
    text = ''.join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-') or 'section'


def couper(texte: str, n: int) -> str:
    """Le texte en n caractères au plus, coupé après un mot et terminé par « … » s'il est coupé."""
    if len(texte) <= n:
        return texte
    return texte[:n].rsplit(' ', 1)[0][:n - 1].rstrip(',;:.־ ') + '…'


def incipit(content: str, classe: str) -> str:
    """Début du premier paragraphe récité (classe he ou ph), en texte brut, pour les descriptions.
    L'hébreu y est sans voyelles, comme on le cherche, et le Tétragramme s'écrit ה'."""
    morceaux = []
    # Un premier paragraphe court (un verset, un titre de psaume) est complété par les suivants.
    for m in re.finditer(r'<p class="' + classe + r'"[^>]*>(.*?)</p>', content, re.S):
        # Sans les renvois de notes ni les variantes ([Une femme : מוֹדָה]).
        texte = re.sub(r'<a class="note-ref".*?</a>|<span class="variante">.*?\]</span>', '', m.group(1), flags=re.S)
        texte = html.unescape(re.sub(r'<[^>]+>', '', texte))
        if classe == 'he':
            texte = NIKUD_RE.sub('', unicodedata.normalize('NFC', texte.replace('־', ' '))).replace('יהוה', "ה'")
        morceaux.append(' '.join(texte.split()))
        if sum(map(len, morceaux)) >= LIMITE_DESCRIPTION:
            break
    return ' '.join(morceaux).rstrip(':.,; ')


def mots_cles(*groupes) -> str:
    """Mots-clés d'une page : les siens d'abord, puis les communs ; sans doublon, douze au plus."""
    vus = {}
    for mot in (m for g in (*groupes, MOTS_CLES) for m in g if m):
        vus.setdefault(mot.lower(), mot)
    return ', '.join(list(vus.values())[:12])


def web_html(content: str) -> str:
    """Le XHTML des sections, avec les rôles ARIA du web à la place des attributs EPUB."""
    content = content.replace('epub:type="noteref"', 'role="doc-noteref"')
    content = content.replace('epub:type="footnote"', 'role="doc-footnote"')
    return re.sub(r'\sepub:type="[^"]*"', '', content)


class Site:
    def __init__(self, livres: list[Livre], dossier: Path, url: str, depot: str = DEPOT):
        self.github = 'https://github.com/' + depot
        self.livres, self.dossier, self.url = livres, dossier, url.rstrip('/') + '/' if url else ''
        self.version = livres[0].version
        self.rites: list[Rite] = list(dict.fromkeys(lv.rite for lv in livres))
        self.pages: list[str] = []  # chemins pour le sitemap
        self.images: dict[str, list[str]] = {}  # images de chaque page, pour le sitemap
        self.tailles: dict[str, tuple[int, int]] = {}  # dimensions des images de partage
        self.par_edition: dict[str, list[str]] = {}  # pages à garder hors ligne, par édition
        self.pdfs: set[str] = set()  # PDF proposés au téléchargement (fabriqués avec --pdf)
        # Chemin de chaque section dans les éditions d'un rite : (chapitre, titre) ; (chapitre, None) = début du chapitre.
        self.chemins: dict[str, dict[tuple[str, str | None], str]] = {r.code: {} for r in self.rites}

    def abs(self, path: str) -> str:
        return self.url + path if self.url else ''

    @staticmethod
    def cle(livre: Livre) -> str:
        """Dossier de l'édition dans le site : hebreu, ashkenaze/hebreu…"""
        return livre.rite.prefixe + livre.mode

    def modes(self, rite: Rite) -> list[str]:
        return [lv.mode for lv in self.livres if lv.rite is rite]

    def nom_edition(self, livre: Livre) -> str:
        """« Édition hébraïque », précisée du rite quand le site en réunit plusieurs."""
        return EDITIONS[livre.mode] + (' (' + livre.rite.adjectif + ')' if len(self.rites) > 1 else '')

    def write(self, path: str, title: str, description: str, body: str, *, livre: Livre | None = None,
              image: str = '', jsonld: list[dict] | None = None, index: bool = True, barre: str = '',
              mots: str = '', og_type: str = 'website', og: list[tuple[str, str]] | None = None,
              voisins: tuple[str | None, str | None] = (None, None)) -> None:
        # La page 404 est servie à n'importe quelle profondeur : liens depuis la racine du site.
        root = '../' * path.count('/') if index or not self.url else self.url
        # Pas d'adresse canonique pour les pages exclues de l'index (404, hors connexion).
        canonical = self.abs(path.removesuffix('index.html')) if index else ''
        cle = self.cle(livre) if livre else ''
        # Image de partage : la couverture de l'édition, sinon l'image du site (format paysage des réseaux).
        image = image or ('assets/covers/' + cle + '.jpg' if livre else 'assets/partage.jpg')
        if image not in self.tailles:
            image = 'assets/covers/' + (cle or 'bilingue') + '.jpg'
        largeur, hauteur = self.tailles.get(image, (0, 0))
        alt = ('Couverture du ' + livre.title if livre else 'Couvertures des éditions du ' + SITE_NAME.lower())
        image = self.abs(image)
        # Onglets des éditions : depuis une page d'une édition, la même page dans les autres éditions
        # du rite (elles ont les mêmes chemins de sections) ; ailleurs, leur sommaire, dans le rite choisi
        # par le lecteur (le script de la page récrit ces liens ; le premier rite par défaut).
        rite = livre.rite if livre else self.rites[0]
        suite = path.removeprefix(cle + '/') if livre and path.startswith(cle + '/') else 'index.html'
        nav = ('<a class="jour' + (' actif' if path == 'index.html' else '') + '" href="' + root + 'index.html"'
               ' title="Aujourd’hui" aria-label="Aujourd’hui">' + CALENDRIER + '</a>'
               '<a href="' + root + 'livres.html"' + (' class="actif"' if path == 'livres.html' else '') + '>Livres</a>'
               + ''.join('<a href="' + root + rite.prefixe + m + '/' + suite + '"'
                         + (' class="actif"' if livre and m == livre.mode else '' if livre else ' data-mode="' + m + '"')
                         + '>' + MENU[m] + '</a>' for m in self.modes(rite)))
        if livre or len(self.rites) == 1:
            nom = html.escape(rite.nom) + '<small>' + html.escape(rite.sous_titre) + '</small>'
        else:
            nom = 'Siddour<small>' + ' · '.join(r.court for r in self.rites) + '</small>'

        def meta(attribut: str, nom: str, valeur: str) -> str:
            return '<meta ' + attribut + '="' + nom + '" content="' + html.escape(valeur, quote=True) + '">'
        head = [
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
            '<title>' + html.escape(title) + '</title>',
            meta('name', 'description', description),
            # Grandes images et extraits sans limite dans les résultats ; les pages techniques restent hors index.
            meta('name', 'robots', 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'
                 if index else 'noindex, follow'),
        ]
        if mots:
            head.append(meta('name', 'keywords', mots))
        if canonical:
            head.append('<link rel="canonical" href="' + canonical + '">')
        # Sections voisines : ordre de lecture du livre, pour les moteurs qui s'en servent encore.
        head += ['<link rel="' + rel + '" href="' + href + '">' for rel, href in zip(('prev', 'next'), voisins) if href]
        head += [
            '<meta name="theme-color" content="#15284a">',
            '<link rel="icon" type="image/png" sizes="32x32" href="' + root + 'assets/icone-32.png">',
            '<link rel="icon" type="image/png" sizes="192x192" href="' + root + 'assets/icone-192.png">',
            '<link rel="manifest" href="' + root + 'manifest.webmanifest">',
            # iPhone et iPad : icône, plein écran, barre d'état sur le bandeau bleu, écrans de démarrage.
            '<link rel="apple-touch-icon" sizes="180x180" href="' + root + 'assets/icone-180.png">',
            '<meta name="apple-mobile-web-app-title" content="Siddour">',
            '<meta name="apple-mobile-web-app-capable" content="yes">',
            '<meta name="mobile-web-app-capable" content="yes">',
            '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">',
            *liens_demarrage(root),
            '<link rel="stylesheet" href="' + root + 'assets/style.css">',
        ]
        # Police hébraïque demandée dès la tête de page : le texte s'affiche sans changer de police en cours de route.
        if livre and livre.mode != 'phonetique':
            head.append('<link rel="preload" href="' + root + 'assets/' + FONT_PATH.name
                        + '" as="font" type="font/ttf" crossorigin>')
        head += [
            '<script src="' + root + 'assets/app.js" defer></script>',
            AFFICHAGE_JS,
            # Aperçus des réseaux sociaux et messageries (Open Graph, X/Twitter).
            meta('property', 'og:site_name', SITE_NAME),
            meta('property', 'og:locale', 'fr_FR'),
            meta('property', 'og:type', og_type),
            meta('property', 'og:title', title),
            meta('property', 'og:description', description),
        ]
        if canonical:
            head.append(meta('property', 'og:url', canonical))
        if image:
            head += [meta('property', 'og:image', image),
                     meta('property', 'og:image:type', 'image/jpeg')]
            if largeur:
                head += [meta('property', 'og:image:width', str(largeur)),
                         meta('property', 'og:image:height', str(hauteur))]
            head.append(meta('property', 'og:image:alt', alt))
        head += [meta('property', p, v) for p, v in og or []]
        # Grande image pour l'image paysage du site ; vignette pour une couverture (format portrait).
        head += [meta('name', 'twitter:card', 'summary_large_image' if largeur > hauteur else 'summary'),
                 meta('name', 'twitter:title', title),
                 meta('name', 'twitter:description', description)]
        if image:
            head += [meta('name', 'twitter:image', image), meta('name', 'twitter:image:alt', alt)]
        # Données structurées : un seul graphe par page, relié au site et à son éditeur par leurs @id.
        if jsonld is not None:
            graphe = {'@context': 'https://schema.org', '@graph': self.graphe_commun() + jsonld}
            head.append('<script type="application/ld+json">'
                        + json.dumps(graphe, ensure_ascii=False).replace('</', '<\\/') + '</script>')
        # Le bandeau suit le défilement : la barre des sections quand la page en a une, sinon le bandeau du site.
        haut = ('<header class="site-head' + ('' if barre else ' colle') + '"><div class="inner"><a class="marque" href="'
                + root + 'index.html"><img src="' + root + 'assets/logo.png" alt="" width="107" height="36">'
                '<span class="nom">' + nom + '</span></a>'
                + ('' if barre else BOUTON_AA) + '<nav class="menu" aria-label="Menu">' + nav + '</nav></div></header>\n')
        if barre:
            haut += '<nav class="barre" aria-label="Sections"><div class="inner">' + barre + BOUTON_AA + '</div></nav>\n'
        page = ('<!doctype html>\n<html lang="fr">\n<head>\n' + '\n'.join(head) + '\n</head>\n<body>\n'
                + haut + '<main>\n' + body + '\n</main>\n'
                '<footer class="site-foot"><p>' + exposants(self.version.complet) + ' · Textes issus de '
                '<a href="https://www.sefaria.org">Sefaria</a> · '
                '<a href="' + root + 'livres.html#telecharger">Télécharger les EPUB</a></p>'
                '<p>Projet libre et collaboratif : <a href="' + self.github + '">contribuer sur GitHub</a> · '
                '<a href="' + self.github + '/issues">signaler une erreur</a>'
                '<span class="contact" data-c="' + CONTACT + '" hidden> · <a href="#">nous écrire</a></span></p></footer>\n'
                '</body>\n</html>\n')
        target = self.dossier / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding='utf-8')
        if index:
            self.pages.append(path)
            # Images de la page (couvertures), pour le sitemap des images.
            self.images[path] = [urljoin(self.abs(path), src) for src in re.findall(r'<img src="([^"]+\.jpg)"', body)]
        if livre:
            self.par_edition.setdefault(cle, []).append(path)

    # -- Données structurées (schema.org) -------------------------------------------------
    def ident(self, path: str, nom: str) -> str:
        """@id d'un nœud du graphe : l'adresse de la page et un nom de fragment."""
        return self.url + path + '#' + nom

    def graphe_commun(self) -> list[dict]:
        """Le site et son éditeur, en tête du graphe de chaque page."""
        site = {'@type': 'WebSite', '@id': self.ident('', 'site'), 'name': SITE_NAME,
                'alternateName': ['sidour.page', 'Siddour en ligne', 'Sidour', 'Siddur'], 'description': SITE_DESCRIPTION,
                'inLanguage': 'fr', 'publisher': {'@id': self.ident('', 'editeur')}}
        editeur = {'@type': 'Organization', '@id': self.ident('', 'editeur'), 'name': 'Siddour-ebook',
                   'url': self.github, 'sameAs': [self.github]}
        if self.url:
            site['url'] = self.url
            editeur['logo'] = {'@type': 'ImageObject', 'url': self.abs('assets/icone-512.png'),
                               'width': 512, 'height': 512}
        return [site, editeur]

    def page_jsonld(self, path: str, type_: str, title: str, description: str, image: str = '', **autres) -> dict:
        """La page elle-même (WebPage, AboutPage…), rattachée au site."""
        adresse = self.abs(path.removesuffix('index.html'))
        data = {'@type': type_, '@id': self.ident(path.removesuffix('index.html'), 'page'), 'name': title,
                'description': description, 'inLanguage': 'fr', 'isPartOf': {'@id': self.ident('', 'site')},
                'dateModified': self.version.jour.isoformat()}
        if adresse:
            data['url'] = adresse
            if image:
                data['primaryImageOfPage'] = {'@type': 'ImageObject', 'url': self.abs(image)}
        return dict(data, **autres)

    # -- Titres, descriptions et mots-clés des pages d'une édition ---------------------------
    @staticmethod
    def titres_sections(livre: Livre, sequence: list) -> list[str]:
        """Titre de chaque section : la section et le texte de l'édition, puis le chapitre et le rite.
        Le chapitre tombe quand le titre dépasse LIMITE_TITRE et que la section se reconnaît sans lui."""
        nombre = Counter(title for _, _, title, _ in sequence)
        titres = []
        for chap, _, title, _ in sequence:
            court = title + ' ' + EN[livre.mode] + ' | ' + livre.rite.nom
            long = title + ' ' + EN[livre.mode] + ' — ' + chap['fr'] + ' | ' + livre.rite.nom
            titres.append(court if title == chap['fr'] or (len(long) > LIMITE_TITRE and nombre[title] == 1) else long)
        # Deux sections de même titre dans un chapitre : numérotées, pour que chaque page ait son titre.
        vus: Counter = Counter()
        for i, titre in enumerate(titres):
            vus[titre] += 1
            if vus[titre] > 1:
                titres[i] = titre.replace(' | ', ' (' + str(vus[titre]) + ') | ', 1)
        return titres

    @staticmethod
    def description_section(livre: Livre, chap: str, title: str, content: str) -> str:
        """La section, l'édition et le rite, puis le début du texte récité : ce qui distingue la page."""
        mode, rite = livre.mode, livre.rite
        tete = title + ('' if title == chap else ' — ' + chap if '(' in chap + title else ' (' + chap + ')')
        consignes = 'class="rubrique' in content
        debut = tete + ' ' + EN[mode] + ', ' + rite.nom[0].lower() + rite.nom[1:] + ' : '
        fin = ' Consignes en français.' if consignes else ''
        textes = [x for x in (incipit(content, c) for c in {'hebreu': ('he',), 'phonetique': ('ph',),
                                                              'bilingue': ('he', 'ph')}[mode]) if x]
        # Chaque citation prend « » (4 caractères), séparées par « – » (3).
        reste = LIMITE_DESCRIPTION - len(debut) - len(fin) - 4 * len(textes) - 3 * max(len(textes) - 1, 0)
        if len(textes) == 2 and reste < 2 * 30:
            textes, reste = textes[:1], reste + 7
        if textes and reste >= 25 * len(textes):
            citations = []
            for i, texte in enumerate(textes):
                citations.append(couper(texte, reste // (len(textes) - i)))
                reste -= len(citations[-1])
            return debut + ' – '.join('« ' + c + ' »' for c in citations) + fin
        # Pas de citation possible : le texte de l'édition, plus ou moins détaillé selon la place.
        variantes = [tete + ' : texte du ' + rite.appellation + ' ' + TEXTE[mode]
                     + (', avec les consignes en français' if consignes else '') + '.',
                     tete + ' : texte du ' + rite.nom.lower() + ' ' + TEXTE[mode] + '.',
                     tete + ' ' + EN[mode] + ', ' + rite.nom.lower() + '.']
        return next((v for v in variantes if len(v) <= LIMITE_DESCRIPTION), variantes[-1])

    @staticmethod
    def mots_rite(rite: Rite) -> tuple:
        """Mots-clés propres au rite : « siddour séfarade », « Rite séfarade », « Edot HaMizrah »…"""
        return (rite.nom.lower(), *(s for s in rite.sujets if s not in ('Siddour', 'Prière juive', 'Liturgie', 'Judaïsme')))

    def book_jsonld(self, livre: Livre) -> dict:
        cle = self.cle(livre)
        data = {
            '@type': 'Book', '@id': self.ident(cle + '/', 'livre'), 'name': livre.title,
            'bookFormat': 'https://schema.org/EBook', 'bookEdition': EDITIONS[livre.mode],
            'inLanguage': ['he', 'fr'] if livre.mode != 'phonetique' else ['fr', 'he'],
            'genre': 'Liturgie juive', 'keywords': ', '.join(livre.rite.sujets),
            'description': description(livre.mode, livre.rite), 'version': livre.version.libelle,
            'datePublished': livre.version.jour.isoformat(), 'dateModified': livre.version.jour.isoformat(),
            'isAccessibleForFree': True,
            'publisher': {'@id': self.ident('', 'editeur')},
            'isBasedOn': {'@type': 'Book', 'name': livre.rite.livre, 'url': 'https://www.sefaria.org'},
        }
        if self.url:
            data['url'] = self.abs(cle + '/')
            data['image'] = self.abs('assets/covers/' + cle + '.jpg')
            data['encoding'] = [{'@type': 'MediaObject', 'encodingFormat': 'application/epub+zip',
                                 'contentUrl': self.abs('telecharger/' + livre.epub)}]
            if livre.pdf in self.pdfs:
                data['encoding'].append({'@type': 'MediaObject', 'encodingFormat': 'application/pdf',
                                         'contentUrl': self.abs('telecharger/' + livre.pdf)})
        return data

    def breadcrumb(self, path: str, items: list[tuple[str, str]]) -> dict:
        return {'@type': 'BreadcrumbList', '@id': self.ident(path.removesuffix('index.html'), 'fil'),
                'itemListElement': [dict({'@type': 'ListItem', 'position': i, 'name': name},
                                         **({'item': self.abs(chemin)} if self.url else {}))
                                    for i, (name, chemin) in enumerate(items, 1)]}

    # -- Pages -----------------------------------------------------------------------------
    def edition(self, livre: Livre) -> None:
        mode, rite, cle = livre.mode, livre.rite, self.cle(livre)
        racine = '../' * (cle.count('/') + 1)  # depuis le sommaire de l'édition
        # Chemins des sections : <chapitre>/<titre>.html, uniques dans le chapitre.
        chapitres = []
        for chap, sections in livre.chapters:
            vus: set[str] = set()
            liens = []
            for title, content in sections:
                nom = slug(title)
                while nom in vus:
                    nom += '-2'
                vus.add(nom)
                liens.append((chap['id'] + '/' + nom + '.html', title, content))
                self.chemins[rite.code].setdefault((chap['id'], title), liens[-1][0])
            self.chemins[rite.code].setdefault((chap['id'], None), liens[0][0])
            chapitres.append((chap, liens))
        sequence = [(chap, href, title, content) for chap, liens in chapitres for href, title, content in liens]
        premiere = {chap['id']: liens[0][0] for chap, liens in chapitres}

        def aller(prefixe: str, actuel: str = '') -> str:
            """Liste de toutes les sections, rangées par chapitre, pour y aller directement."""
            return ('<select aria-label="Aller à une section">'
                    + ('' if actuel else '<option value="" selected>Aller à une section…</option>')
                    + ''.join('<optgroup label="' + html.escape(chap['fr'], quote=True) + '">' + ''.join(
                        '<option value="' + prefixe + h + '"' + (' selected' if h == actuel else '') + '>'
                        + html.escape(t) + '</option>' for h, t, _ in liens) + '</optgroup>'
                        for chap, liens in chapitres)
                    + '</select>')

        book = self.book_jsonld(livre)
        jour = livre.version.jour.isoformat()
        couverture = 'assets/covers/' + cle + '.jpg'
        # Le sommaire du livre (même rendu que l'EPUB), sous le titre de l'édition, seul titre de niveau 1.
        sommaire = make_contents([(chap['fr'], chap.get('he', ''), [(h, t) for h, t, _ in liens])
                                  for chap, liens in chapitres]).replace(
            '<h1>Sommaire</h1>', '<h2 class="sommaire-titre">Sommaire</h2>', 1)
        # Le même livre dans l'autre rite : son sommaire, dans la même édition.
        autres_rites = ' · '.join('<a href="' + racine + r.prefixe + mode + '/index.html">' + html.escape(r.nom) + '</a>'
                                  for r in self.rites if r is not rite and mode in self.modes(r))
        intro = ('<h1 class="titre-edition">' + html.escape(livre.title) + '</h1>'
                 '<p class="accroche">' + exposants(livre.version.complet) + '</p>'
                 '<p style="text-align:center"><a class="bouton" href="' + sequence[0][1] + '">Commencer la lecture</a> '
                 '<a class="bouton second" href="' + racine + 'telecharger/' + livre.epub + '" download>'
                 'Télécharger l’EPUB</a>'
                 + (' <a class="bouton second" href="' + racine + 'telecharger/' + livre.pdf + '" download>PDF</a>'
                    if livre.pdf in self.pdfs else '') + '</p>'
                 + ('<p class="autre-rite">' + html.escape(rite.limites) + '</p>' if rite.limites else '')
                 + ('<p class="autre-rite">Voir aussi : ' + autres_rites + '</p>' if autres_rites else ''))
        crumb = [(SITE_NAME, ''), (self.nom_edition(livre), cle + '/')]
        # Sommaire : l'édition, puis ses chapitres tant qu'ils tiennent dans la description.
        titre = rite.nom + ' ' + EN[mode] + ' — lire en ligne ou en EPUB'
        resume = rite.appellation[0].upper() + rite.appellation[1:] + ' ' + TEXTE[mode] + ', en ligne ou en EPUB gratuit : '
        for i, (chap, _) in enumerate(chapitres):
            ajout = (', ' if i else '') + chap['fr']
            if len(resume) + len(ajout) + 1 > LIMITE_DESCRIPTION:
                resume += '…'
                break
            resume += ajout
        else:
            resume += '.'
        path = cle + '/index.html'
        self.write(path, titre, resume,
                   intro + '<p class="hors-ligne"><button class="bouton second" data-hors-ligne="' + cle
                   + '" hidden>Garder hors ligne</button> <span></span></p>'
                   + sommaire + '<p style="text-align:center"><a href="a-propos.html">'
                   'À propos de cette édition</a></p>',
                   livre=livre, barre=aller(''), og_type='book',
                   og=[('book:release_date', jour)] + [('book:tag', s) for s in rite.sujets],
                   mots=mots_cles(self.mots_rite(rite), MOTS_EDITION[mode], ('siddour en ligne', 'siddour epub')),
                   jsonld=[self.page_jsonld(path, 'WebPage', titre, resume, couverture,
                                            breadcrumb={'@id': self.ident(cle + '/', 'fil')},
                                            mainEntity={'@id': book['@id']}),
                           book, self.breadcrumb(path, crumb)])
        path = cle + '/a-propos.html'
        titre = 'Sources et licences — ' + rite.nom + ' ' + EN[mode]
        resume = ('Sources (Sefaria), licences, conventions de mise en page et numéro d’édition du '
                  + rite.appellation + ' ' + TEXTE[mode] + '.')
        self.write(path, titre, resume,
                   web_html(make_credits(livre.title, livre.licences, mode, livre.version, rite)),
                   livre=livre, barre=aller(''),
                   mots=mots_cles(('sources', 'licences', 'Sefaria'), (rite.nom.lower(),), MOTS_EDITION[mode][:1]),
                   jsonld=[self.page_jsonld(path, 'AboutPage', titre, resume, about={'@id': book['@id']},
                                            breadcrumb={'@id': self.ident(path, 'fil')}),
                           self.breadcrumb(path, crumb + [('À propos', path)])])

        titres = self.titres_sections(livre, sequence)
        for k, (chap, href, title, content) in enumerate(sequence):
            prev = sequence[k - 1] if k else None
            nxt = sequence[k + 1] if k + 1 < len(sequence) else None
            up = '../' * href.count('/')
            path = cle + '/' + href
            # La section en titre de niveau 1 (le premier titre du texte), sous le nom du chapitre,
            # repère pour le lecteur : chaque page a ainsi son propre titre principal.
            texte = web_html(content)
            chapitre = (html.escape(chap['fr'])
                        + ('<br><small lang="he" dir="rtl">' + html.escape(chap['he']) + '</small>' if chap.get('he') else ''))
            if texte.startswith('<h2>'):
                heading = '<p class="titre-chapitre">' + chapitre + '</p>'
                texte = '<h1 class="titre-section">' + texte[4:].replace('</h2>', '</h1>', 1)
            else:
                heading = '<h1>' + chapitre + '</h1>'
            autres = ' · '.join('<a href="' + up + '../' + m + '/' + href + '">' + html.escape(TITLES[m]) + '</a>'
                                for m in self.modes(rite) if m != mode)
            fil = ('<p class="fil"><a href="' + up + 'index.html">' + self.nom_edition(livre) + '</a> › '
                   + html.escape(chap['fr']) + (' · Aussi en ' + autres if autres else '') + '</p>')
            pager = '<nav class="pager">' + (
                '<a class="prec" rel="prev" href="' + up + prev[1] + '">← ' + html.escape(prev[2]) + '</a>' if prev else '') + (
                '<a class="suiv" rel="next" href="' + up + nxt[1] + '">' + html.escape(nxt[2]) + ' →</a>' if nxt else '') + '</nav>'

            def fleche(voisin, classe: str, signe: str, nom: str) -> str:
                if not voisin:
                    return '<span class="vide" aria-hidden="true">' + signe + '</span>'
                return ('<a class="' + classe + '" href="' + up + voisin[1] + '" title="' + nom + ' : '
                        + html.escape(voisin[2], quote=True) + '" aria-label="' + nom + '">' + signe + '</a>')
            barre = (fleche(prev, 'prec', '‹', 'Section précédente') + aller(up, href)
                     + fleche(nxt, 'suiv', '›', 'Section suivante'))
            resume = self.description_section(livre, chap['fr'], title, content)
            jsonld = [self.page_jsonld(path, 'WebPage', titres[k], resume, couverture,
                                       breadcrumb={'@id': self.ident(path, 'fil')},
                                       mainEntity={'@id': self.ident(path, 'texte')}),
                      dict({'@type': 'Chapter', '@id': self.ident(path, 'texte'), 'name': title,
                            'position': k + 1, 'inLanguage': book['inLanguage'],
                            'isPartOf': {'@id': book['@id']}}, **({'url': self.abs(path)} if self.url else {})),
                      book,
                      self.breadcrumb(path, crumb + [(chap['fr'], cle + '/' + premiere[chap['id']]), (title, path)])]
            self.write(path, titres[k], resume, fil + heading + texte + pager,
                       livre=livre, jsonld=jsonld, barre=barre, og_type='article',
                       og=[('article:modified_time', jour), ('article:section', chap['fr']), ('article:tag', title)],
                       mots=mots_cles((title, chap['fr'], chap.get('he', '')), (rite.nom.lower(),), MOTS_EDITION[mode][:2]),
                       voisins=(up + prev[1] if prev else None, up + nxt[1] if nxt else None))

    def accueil(self) -> None:
        # Accueil : la journée (date hébraïque, prières, horaires), puis un lien vers les livres.
        # Pages du jour de chaque rite ; celles qu'un rite n'a pas restent sans lien.
        cibles = {r.code: {'nom': r.court, 'prefixe': r.prefixe, 'modes': self.modes(r),
                           'pages': {cle: self.chemins[r.code][cible] for cle, cible in CIBLES.items()
                                     if cible in self.chemins[r.code]}}
                  for r in self.rites}
        couverture = next((p for p in ('assets/covers/' + m + '.jpg' for m in ('bilingue', *(self.cle(lv) for lv in self.livres)))
                           if (self.dossier / p).exists()), 'assets/icone-192.png')
        sous_titre = ((' · '.join(r.court for r in self.rites) + ' — ' if len(self.rites) > 1 else '')
                      + ' · '.join(MENU[m] for m in dict.fromkeys(lv.mode for lv in self.livres))
                      + ' — en ligne ou en EPUB pour liseuse')
        # Texte fixe sous les cartes du jour : ce que propose le site, et un lien vers chaque édition.
        adjectifs = ' et '.join(r.adjectif for r in self.rites)
        presentation = (
            '<section class="carte presentation" aria-labelledby="presentation-titre">'
            '<h2 id="presentation-titre">Le siddour en ligne</h2>'
            '<p>Cette page donne la date hébraïque, les prières du jour et leurs horaires (zmanim) pour sa ville : '
            'lever du soleil, fin du Chéma, Min’ha, allumage des bougies et sortie de Chabbat, '
            'avec les prochaines fêtes et jeûnes.</p>'
            '<p>Le siddour, livre de prière juif, s’y lit en ligne, même sans connexion une fois gardé, '
            'ou se télécharge gratuitement en EPUB pour liseuse : hébreu vocalisé, phonétique ou les deux, '
            'avec les consignes en français.</p><ul>'
            + ''.join('<li><b>' + html.escape(r.libelle) + '</b> : ' + html.escape(r.contenu) + '. Lire le '
                      + html.escape(r.nom.lower()) + ' ' + ', '.join(
                          '<a href="' + r.prefixe + m + '/index.html">' + EN[m] + '</a>' for m in self.modes(r)) + '.</li>'
                      for r in self.rites)
            + '</ul></section>')
        titre = 'Siddour en ligne — prières et zmanim du jour, ' + ('rite ' if len(self.rites) == 1 else '') + adjectifs
        resume = ('Date hébraïque, prières et horaires du jour (zmanim) pour sa ville, Chabbat et fêtes ; siddour '
                  + adjectifs + ' en hébreu ou phonétique, en ligne ou EPUB.')
        self.write('index.html', titre, resume,
                   corps(cibles, couverture, sous_titre, presentation) + '<script src="assets/aujourdhui.js" defer></script>',
                   mots=mots_cles(('siddour en ligne', 'prière du jour', 'zmanim', 'horaires de prière', 'date hébraïque',
                                   'calendrier juif', 'horaires de Chabbat')),
                   jsonld=[self.page_jsonld('index.html', 'WebPage', titre, resume, 'assets/partage.jpg',
                                            about={'@id': self.ident('', 'livres')})])

        # Livres : pour chaque rite, les éditions en 2 × 2 sur téléphone, avec une case d'aide à la lecture
        # sur liseuse (premier rite) ou sur le contenu du livre (les suivants).
        aide = ('<div class="edition-carte carte-aide"><h2>Sur liseuse</h2>'
                '<p>Télécharger l’EPUB, puis l’ouvrir sur sa liseuse (Kobo, PocketBook, Apple Livres…) '
                'ou l’envoyer sur Kindle avec « Send to Kindle ».</p>'
                + ('<p>Le PDF, au format A5, s’imprime ou se lit sur tablette.</p>' if self.pdfs else '') +
                '<p>Les éditions se lisent aussi en ligne, même sans connexion une fois gardées.</p>'
                '<p><a href="' + self.github + '/releases">Toutes les versions</a></p></div>')
        sections = []
        for n, rite in enumerate(self.rites):
            livres = [lv for lv in self.livres if lv.rite is rite]
            cartes = ''.join(
                '<div class="edition-carte"><a href="' + self.cle(lv) + '/index.html"><img src="assets/covers/'
                + self.cle(lv) + '.jpg" alt="Couverture : ' + html.escape(lv.title, quote=True) + '" width="400" height="600"'
                + (' loading="lazy"' if n or i > 1 else '') + '></a><h2>' + MENU[lv.mode] + '</h2>'
                '<p class="texte">Textes ' + TEXTE[lv.mode] + '</p>'
                '<p class="actions"><a class="bouton" href="' + self.cle(lv) + '/index.html">Lire</a>'
                '<a class="bouton second" href="telecharger/' + lv.epub + '" download>EPUB</a>'
                + ('<a class="bouton second" href="telecharger/' + lv.pdf + '" download>PDF</a>' if lv.pdf in self.pdfs else '')
                + '</p></div>'
                for i, lv in enumerate(livres))
            contenu = ('<div class="edition-carte carte-aide"><h2>Contenu</h2><p>'
                       + html.escape(rite.contenu[0].upper() + rite.contenu[1:]) + '.</p>'
                       + ('<p>' + html.escape(rite.limites) + '</p>' if rite.limites else '') + '</div>')
            sections.append('<section class="rite" id="' + rite.code + '">'
                            + ('<h2 class="rite-titre">' + html.escape(rite.libelle) + '</h2>' if len(self.rites) > 1 else '')
                            + '<div class="editions">' + cartes + (contenu if n else aide) + '</div></section>')
        body = ('<h1>' + SITE_NAME + '</h1><p class="accroche">' + TAGLINE + '</p>'
                '<div id="telecharger">' + ''.join(sections)
                + '<p class="accroche">' + exposants(self.version.complet) + '</p></div>'
                + web_html(introduction(self.rites[0] if len(self.rites) == 1 else None))
                .replace('<h1>', '<h2>').replace('</h1>', '</h2>'))
        # L'œuvre (le siddour) et ses éditions, chacune avec son EPUB.
        work = {'@type': 'Book', '@id': self.ident('', 'livres'), 'name': SITE_NAME,
                'alternateName': ['Siddour', 'Sidour', 'Siddur'], 'description': SITE_DESCRIPTION,
                'genre': 'Liturgie juive', 'inLanguage': ['he', 'fr'], 'isAccessibleForFree': True,
                'keywords': ', '.join(dict.fromkeys(s for r in self.rites for s in r.sujets)),
                'publisher': {'@id': self.ident('', 'editeur')},
                'workExample': [self.book_jsonld(lv) for lv in self.livres]}
        titre = SITE_NAME + ' gratuit : lire en ligne ou en EPUB'
        self.write('livres.html', titre, SITE_DESCRIPTION, body,
                   mots=mots_cles(('siddour gratuit', 'siddour en ligne', 'siddour epub', 'siddour pour liseuse'),
                                  *(self.mots_rite(r)[:1] for r in self.rites), ('siddour phonétique',)),
                   jsonld=[self.page_jsonld('livres.html', 'CollectionPage', titre, SITE_DESCRIPTION,
                                            'assets/partage.jpg', mainEntity={'@id': work['@id']},
                                            breadcrumb={'@id': self.ident('livres.html', 'fil')}),
                           work, self.breadcrumb('livres.html', [(SITE_NAME, ''), ('Livres', 'livres.html')])])
        self.write('404.html', 'Page introuvable — ' + SITE_NAME,
                   'Cette page du siddour n’existe pas ou a changé d’adresse : retrouver les prières du jour '
                   'et les éditions depuis l’accueil.',
                   '<h1>Page introuvable</h1><p style="text-align:center">'
                   '<a class="bouton" href="' + (self.url or 'index.html') + '">Retour à l’accueil</a></p>', index=False)
        self.write('hors-ligne.html', 'Hors connexion — ' + SITE_NAME,
                   'Page affichée sans connexion : les pages déjà lues et les éditions gardées hors ligne '
                   'restent disponibles.',
                   '<h1>Hors connexion</h1><p>Cette page n’a pas encore été enregistrée sur cet appareil. '
                   'Les pages déjà lues restent disponibles ; pour lire une édition entière sans connexion, '
                   'ouvrir son sommaire et choisir « Garder hors ligne ».</p><p style="text-align:center">'
                   '<a class="bouton" href="' + (self.url or 'index.html') + '">Retour à l’accueil</a></p>', index=False)

    def assets(self, sortie: Path) -> None:
        from PIL import Image
        dossier = self.dossier / 'assets'
        (dossier / 'covers').mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FONT_PATH, dossier / FONT_PATH.name)
        # Feuille du livre d'abord, puis les règles propres au web qui la complètent.
        font_face, web = WEB_CSS.replace('FONT_URL', FONT_PATH.name).split('\n', 2)[1:]
        (dossier / 'style.css').write_text(font_face + '\n' + CSS + web + AUJOURDHUI_CSS + LIVRES_CSS, encoding='utf-8')
        (dossier / 'aujourdhui.js').write_text(AUJOURDHUI_JS, encoding='utf-8')
        for lv in self.livres:
            cover = cover_image(lv.mode, lv.rite)
            if not cover:
                continue
            fichier = dossier / 'covers' / (self.cle(lv) + '.jpg')
            fichier.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(io.BytesIO(cover[1])) as im:
                im = im.convert('RGB')
                im.thumbnail((800, 1200))
                im.save(fichier, 'JPEG', quality=85, optimize=True, progressive=True)
                self.tailles['assets/covers/' + self.cle(lv) + '.jpg'] = im.size
        if not (ICONES / 'logo.png').exists():
            generer_icones()
        shutil.copytree(ICONES, dossier, dirs_exist_ok=True)
        self.image_partage(dossier)
        telecharger = self.dossier / 'telecharger'
        telecharger.mkdir(exist_ok=True)
        for lv in self.livres:
            shutil.copyfile(sortie / lv.epub, telecharger / lv.epub)
            if (sortie / lv.pdf).exists():
                shutil.copyfile(sortie / lv.pdf, telecharger / lv.pdf)
                self.pdfs.add(lv.pdf)
        (self.dossier / '.nojekyll').write_text('', encoding='utf-8')
        (self.dossier / (INDEXNOW + '.txt')).write_text(INDEXNOW, encoding='utf-8')
        # Domaine personnalisé de GitHub Pages, quand le site est publié à son adresse.
        if self.url == SITE_URL:
            (self.dossier / 'CNAME').write_text(SITE_URL.removeprefix('https://').rstrip('/') + '\n', encoding='utf-8')
        if RACINE.is_dir():
            shutil.copytree(RACINE, self.dossier, dirs_exist_ok=True)

    def image_partage(self, dossier: Path) -> None:
        """Image des aperçus (réseaux sociaux, messageries) pour les pages communes : 1200 × 630,
        le logo doré sur le bleu des couvertures, puis jusqu'à trois couvertures côte à côte."""
        from PIL import Image, ImageDraw, ImageFilter
        from .icones import FOND
        largeur, hauteur = 1200, 630
        image = Image.new('RGB', (largeur, hauteur), FOND)
        # Léger dégradé vers le bleu du bandeau, vers le bas.
        degrade = Image.linear_gradient('L').resize((largeur, hauteur))
        image = Image.composite(Image.new('RGB', (largeur, hauteur), '#1d3966'), image, degrade.point(lambda v: v // 2))
        with Image.open(ICONES / 'logo.png') as logo:
            logo = logo.convert('RGBA')
            logo = logo.resize((logo.width * 110 // logo.height, 110), Image.LANCZOS)
            image.paste(logo, ((largeur - logo.width) // 2, 36), logo)
        # Trois couvertures : hébreu et phonétique du premier rite, bilingue du dernier.
        voulues = [(self.rites[0], 'hebreu'), (self.rites[0], 'phonetique'), (self.rites[-1], 'bilingue')]
        cles = dict.fromkeys(self.cle(lv) for r, m in voulues for lv in self.livres if lv.rite is r and lv.mode == m)
        couvertures = [dossier / 'covers' / (c + '.jpg') for c in cles or [self.cle(lv) for lv in self.livres[:3]]]
        couvertures = [c for c in couvertures if c.exists()]
        h = hauteur - 180 - 36
        w = h * 2 // 3
        ecart = 44
        x = (largeur - len(couvertures) * w - (len(couvertures) - 1) * ecart) // 2
        for c in couvertures:
            with Image.open(c) as couv:
                couv = couv.convert('RGB').resize((w, h), Image.LANCZOS)
            ombre = Image.new('L', (largeur, hauteur), 0)
            ImageDraw.Draw(ombre).rectangle((x + 4, 180 + 8, x + w + 4, 180 + h + 8), fill=150)
            image = Image.composite(Image.new('RGB', (largeur, hauteur), '#050d1a'), image,
                                    ombre.filter(ImageFilter.GaussianBlur(10)))
            image.paste(couv, (x, 180))
            x += w + ecart
        image.save(dossier / 'partage.jpg', 'JPEG', quality=85, optimize=True, progressive=True)
        self.tailles['assets/partage.jpg'] = (largeur, hauteur)

    def index_moteurs(self) -> None:
        # Tout est permis, aux moteurs de recherche comme aux robots des IA (entraînement, recherche,
        # réponses) : les textes sont libres et le siddour gagne à être trouvé. Les robots d'IA sont
        # nommés pour que l'autorisation reste explicite, même pour ceux qui ne lisent que leur nom.
        lignes = ['# ' + SITE_NAME + ' : exploration et réutilisation permises à tous, IA comprises.',
                  '# Textes : Sefaria (licences indiquées sur chaque édition).', '',
                  'User-agent: *', 'Allow: /', '']
        lignes += ['User-agent: ' + robot for robot in ROBOTS_IA] + ['Allow: /', '']
        if self.url:
            jour = self.version.jour.isoformat()
            urls = ''.join('<url><loc>' + html.escape(self.abs(p.removesuffix('index.html'))) + '</loc><lastmod>'
                           + jour + '</lastmod>' + ''.join('<image:image><image:loc>' + html.escape(i)
                                                            + '</image:loc></image:image>' for i in self.images.get(p, []))
                           + '</url>\n' for p in self.pages)
            (self.dossier / 'sitemap.xml').write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' + urls + '</urlset>\n',
                encoding='utf-8')
            lignes.append('Sitemap: ' + self.abs('sitemap.xml'))
        (self.dossier / 'robots.txt').write_text('\n'.join(lignes) + '\n', encoding='utf-8')

    # -- Application installable (PWA) -----------------------------------------------------
    def pwa(self) -> None:
        liste = [{'src': 'assets/icone-' + n + '.png', 'sizes': s + 'x' + s, 'type': 'image/png', 'purpose': p}
                  for n, s, p in (('192', '192', 'any'), ('512', '512', 'any'), ('maskable', '512', 'maskable'))]
        plusieurs = len(self.rites) > 1
        manifest = {
            'id': './', 'name': SITE_NAME, 'short_name': 'Siddour', 'description': SITE_DESCRIPTION,
            'lang': 'fr', 'dir': 'ltr', 'start_url': './', 'scope': './', 'display': 'standalone',
            'background_color': '#fbf9f4', 'theme_color': '#15284a', 'categories': ['books', 'education'],
            'icons': liste,
            'shortcuts': [{'name': self.nom_edition(lv),
                           'short_name': MENU[lv.mode] + (' ' + lv.rite.adjectif if plusieurs else ''),
                           'url': self.cle(lv) + '/index.html', 'icons': liste[:1]} for lv in self.livres]
                         + [{'name': 'Les livres', 'short_name': 'Livres', 'url': 'livres.html', 'icons': liste[:1]}],
        }
        (self.dossier / 'manifest.webmanifest').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
        (self.dossier / 'assets' / 'app.js').write_text(
            APP_JS.replace('__VERSION__', json.dumps(self.version.complet, ensure_ascii=False))
            .replace('__PREFIXES__', json.dumps({r.code: r.prefixe for r in self.rites})), encoding='utf-8')

        # Le nom du cache combine l'édition et une empreinte de tout le site :
        # une nouvelle révision, comme une simple correction, déclenche la mise à jour.
        empreinte = hashlib.sha256()
        for f in sorted(p for p in self.dossier.rglob('*') if p.is_file()):
            empreinte.update(f.relative_to(self.dossier).as_posix().encode() + b'\0' + f.read_bytes())
        nom = (self.version.tag if self.version.edition else 'travail') + '-' + empreinte.hexdigest()[:12]
        coquille = (['index.html', 'livres.html', 'hors-ligne.html', 'manifest.webmanifest', 'assets/style.css',
                     'assets/app.js', 'assets/aujourdhui.js', 'assets/' + FONT_PATH.name]
                    + [i['src'] for i in liste] + ['assets/icone-32.png', 'assets/icone-180.png', 'assets/papier.jpg', 'assets/logo.png']
                    + [p.relative_to(self.dossier).as_posix() for p in sorted((self.dossier / 'assets' / 'covers').rglob('*.jpg'))]
                    + [self.cle(lv) + '/index.html' for lv in self.livres])
        sw = (SW_JS.replace('__CACHE__', json.dumps(nom))
              .replace('__COQUILLE__', json.dumps(coquille))
              .replace('__EDITIONS__', json.dumps(self.par_edition, ensure_ascii=False)))
        (self.dossier / 'sw.js').write_text(sw, encoding='utf-8')
        self.cache = nom


def build_site(livres: list[Livre], dossier: Path, sortie: Path, url: str = '', depot: str = DEPOT) -> Path:
    if dossier.exists():
        shutil.rmtree(dossier)
    dossier.mkdir(parents=True)
    site = Site(livres, dossier, url, depot)
    site.assets(sortie)
    for livre in livres:
        site.edition(livre)
    site.accueil()
    site.index_moteurs()
    site.pwa()
    print('Site :', dossier, '|', len(site.pages), 'pages', '|', date_fr(site.version.jour), '| cache', site.cache)
    return dossier
