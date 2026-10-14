"""Site web de lecture (GitHub Pages) : les trois éditions consultables dans un navigateur.

Arborescence produite :
    index.html                         accueil « Aujourd'hui » : date hébraïque, prières et horaires du jour
    livres.html                        les éditions : lecture en ligne, téléchargements EPUB
    <mode>/index.html                  sommaire de l'édition
    <mode>/<chapitre>/<section>.html   une page par section, comme dans l'EPUB
    telecharger/*.epub, assets/, sitemap.xml, robots.txt, 404.html
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
from pathlib import Path

from .edition import (CSS, DESCRIPTION, FONT_PATH, INTRODUCTION, SUBJECTS, TITLES, Livre, cover_image,
                      exposants, make_contents, make_credits)
from .aujourdhui import AUJOURDHUI_CSS, AUJOURDHUI_JS, CIBLES, LIVRES_CSS, corps
from .icones import DOSSIER as ICONES, generer as generer_icones, liens_demarrage
from .version import date_fr

SITE_NAME = 'Siddour séfarade'
TAGLINE = 'Le livre de prière du rite séfarade (Edot HaMizrah), à lire en ligne ou sur liseuse'
SITE_DESCRIPTION = ('Siddour séfarade complet (Edot HaMizrah) à lire en ligne ou à télécharger en EPUB : '
                    'hébreu vocalisé, phonétique ou les deux, avec les consignes en français. '
                    'Prières de la semaine, Chabbat, fêtes, jeûnes, bénédictions et cycle de la vie.')
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
EPUB_NAME = 'siddour_liseuse_{}.epub'
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
      a.href = "mailto:" + adresse + "?subject=" + encodeURIComponent("Siddour séfarade");
      a.textContent = adresse;
      location.href = a.href;
    });
  }

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
  // Les EPUB se téléchargent toujours depuis le réseau.
  if (r.method !== "GET" || !r.url.startsWith(base) || new URL(r.url).pathname.endsWith(".epub")) return;
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
        self.pages: list[str] = []  # chemins pour le sitemap
        self.par_edition: dict[str, list[str]] = {}  # pages à garder hors ligne
        # Chemin de chaque section dans une édition : (chapitre, titre) ; (chapitre, None) = début du chapitre.
        self.chemins: dict[tuple[str, str | None], str] = {}

    def abs(self, path: str) -> str:
        return self.url + path if self.url else ''

    def write(self, path: str, title: str, description: str, body: str, *, mode: str = '',
              image: str = '', jsonld: list[dict] | None = None, index: bool = True, barre: str = '') -> None:
        # La page 404 est servie à n'importe quelle profondeur : liens depuis la racine du site.
        root = '../' * path.count('/') if index or not self.url else self.url
        canonical = self.abs(path.removesuffix('index.html'))
        image = self.abs(image or 'assets/covers/' + (mode or 'bilingue') + '.jpg')
        # Onglets des éditions : depuis une page d'une édition, la même page dans l'autre édition
        # (les éditions ont les mêmes chemins de sections) ; sinon, son sommaire.
        suite = path.removeprefix(mode + '/') if mode and path.startswith(mode + '/') else 'index.html'
        nav = ('<a class="jour' + (' actif' if path == 'index.html' else '') + '" href="' + root + 'index.html"'
               ' title="Aujourd’hui" aria-label="Aujourd’hui">' + CALENDRIER + '</a>'
               '<a href="' + root + 'livres.html"' + (' class="actif"' if path == 'livres.html' else '') + '>Livres</a>'
               + ''.join('<a href="' + root + m + '/' + suite + '"' + (' class="actif"' if m == mode else '') + '>'
                         + MENU[m] + '</a>' for m in (lv.mode for lv in self.livres)))
        head = [
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
            '<title>' + html.escape(title) + '</title>',
            '<meta name="description" content="' + html.escape(description, quote=True) + '">',
            '<meta name="robots" content="' + ('index, follow' if index else 'noindex') + '">',
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
            '<script src="' + root + 'assets/app.js" defer></script>',
            AFFICHAGE_JS,
            '<meta property="og:site_name" content="' + SITE_NAME + '">',
            '<meta property="og:locale" content="fr_FR">',
            '<meta property="og:type" content="' + ('book' if mode else 'website') + '">',
            '<meta property="og:title" content="' + html.escape(title, quote=True) + '">',
            '<meta property="og:description" content="' + html.escape(description, quote=True) + '">',
            '<meta name="twitter:card" content="summary">',
            '<meta name="twitter:title" content="' + html.escape(title, quote=True) + '">',
            '<meta name="twitter:description" content="' + html.escape(description, quote=True) + '">',
        ]
        if canonical:
            head += ['<link rel="canonical" href="' + canonical + '">',
                     '<meta property="og:url" content="' + canonical + '">']
        if image:
            head += ['<meta property="og:image" content="' + image + '">',
                     '<meta property="og:image:alt" content="Couverture du siddour">',
                     '<meta name="twitter:image" content="' + image + '">']
        if mode:
            head += ['<meta property="book:tag" content="' + html.escape(t, quote=True) + '">' for t in SUBJECTS]
        for data in jsonld or []:
            head.append('<script type="application/ld+json">'
                        + json.dumps(data, ensure_ascii=False).replace('</', '<\\/') + '</script>')
        # Le bandeau suit le défilement : la barre des sections quand la page en a une, sinon le bandeau du site.
        haut = ('<header class="site-head' + ('' if barre else ' colle') + '"><div class="inner"><a class="marque" href="'
                + root + 'index.html"><img src="' + root + 'assets/logo.png" alt="" width="107" height="36">'
                '<span class="nom">' + SITE_NAME + '<small>Rite Edot HaMizrah</small></span></a>'
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
        if mode:
            self.par_edition.setdefault(mode, []).append(path)

    # -- Données structurées (schema.org) -------------------------------------------------
    def book_jsonld(self, livre: Livre) -> dict:
        data = {
            '@type': 'Book', 'name': livre.title, 'bookFormat': 'https://schema.org/EBook',
            'inLanguage': ['he', 'fr'] if livre.mode != 'phonetique' else ['fr', 'he'],
            'genre': 'Liturgie juive', 'keywords': ', '.join(SUBJECTS),
            'description': DESCRIPTION[livre.mode], 'version': livre.version.libelle,
            'datePublished': livre.version.jour.isoformat(), 'isAccessibleForFree': True,
            'publisher': {'@type': 'Organization', 'name': 'Siddour-ebook'},
            'isBasedOn': {'@type': 'Book', 'name': 'Siddur Edot HaMizrach', 'url': 'https://www.sefaria.org'},
        }
        if self.url:
            data['url'] = self.abs(livre.mode + '/')
            data['image'] = self.abs('assets/covers/' + livre.mode + '.jpg')
            data['encoding'] = {'@type': 'MediaObject', 'encodingFormat': 'application/epub+zip',
                                'contentUrl': self.abs('telecharger/' + EPUB_NAME.format(livre.mode))}
        return data

    def breadcrumb(self, items: list[tuple[str, str]]) -> dict:
        return {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            dict({'@type': 'ListItem', 'position': i, 'name': name},
                 **({'item': self.abs(path)} if self.url else {}))
            for i, (name, path) in enumerate(items, 1)]}

    # -- Pages -----------------------------------------------------------------------------
    def edition(self, livre: Livre) -> None:
        mode = livre.mode
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
                self.chemins.setdefault((chap['id'], title), liens[-1][0])
            self.chemins.setdefault((chap['id'], None), liens[0][0])
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

        book = dict(self.book_jsonld(livre), **{'@context': 'https://schema.org'})
        sommaire = make_contents([(chap['fr'], chap.get('he', ''), [(h, t) for h, t, _ in liens])
                                  for chap, liens in chapitres])
        intro = ('<p class="accroche">' + exposants(livre.version.complet) + '</p>'
                 '<p style="text-align:center"><a class="bouton" href="' + sequence[0][1] + '">Commencer la lecture</a> '
                 '<a class="bouton second" href="../telecharger/' + EPUB_NAME.format(mode) + '" download>'
                 'Télécharger l’EPUB</a></p>')
        self.write(mode + '/index.html', livre.title + ' — lire en ligne',
                   'Sommaire du siddour séfarade ' + TEXTE[mode] + ', avec consignes en français : '
                   + ', '.join(chap['fr'] for chap, _ in chapitres[:8]) + '…',
                   intro + '<p class="hors-ligne"><button class="bouton second" data-hors-ligne="' + mode
                   + '" hidden>Garder hors ligne</button> <span></span></p>'
                   + sommaire + '<p style="text-align:center"><a href="a-propos.html">'
                   'À propos de cette édition</a></p>',
                   mode=mode, barre=aller(''), jsonld=[book, self.breadcrumb([(SITE_NAME, ''), (EDITIONS[mode], mode + '/')])])
        self.write(mode + '/a-propos.html', 'À propos — ' + livre.title,
                   'Sources, licences et conventions de mise en page de l’édition ' + TITLES[mode] + ' du siddour.',
                   web_html(make_credits(livre.title, livre.licences, mode, livre.version)), mode=mode, barre=aller(''))

        for k, (chap, href, title, content) in enumerate(sequence):
            prev = sequence[k - 1] if k else None
            nxt = sequence[k + 1] if k + 1 < len(sequence) else None
            up = '../' * href.count('/')
            # Le chapitre en titre de chaque page : repère pour le lecteur comme pour les moteurs.
            heading = ('<h1>' + html.escape(chap['fr'])
                       + ('<br><small lang="he" dir="rtl">' + html.escape(chap['he']) + '</small>' if chap.get('he') else '')
                       + '</h1>')
            autres = ' · '.join('<a href="' + up + '../' + m + '/' + href + '">' + html.escape(TITLES[m]) + '</a>'
                                for m in (lv.mode for lv in self.livres) if m != mode)
            fil = ('<p class="fil"><a href="' + up + 'index.html">' + EDITIONS[mode] + '</a> › '
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
            page_title = title + (' — ' + chap['fr'] if title != chap['fr'] else '') + ' | ' + livre.title
            description = ('« ' + title + ' » (' + chap['fr'] + ') : texte du siddour séfarade Edot HaMizrah '
                           + TEXTE[mode] + ', avec les consignes en français. Lecture en ligne ou EPUB.')
            jsonld = [self.breadcrumb([(SITE_NAME, ''), (EDITIONS[mode], mode + '/'),
                                       (chap['fr'], mode + '/' + premiere[chap['id']]), (title, mode + '/' + href)]),
                      {'@context': 'https://schema.org', '@type': 'WebPage', 'name': title,
                       'inLanguage': 'fr', 'isPartOf': self.book_jsonld(livre)}]
            self.write(mode + '/' + href, page_title, description, fil + heading + web_html(content) + pager,
                       mode=mode, jsonld=jsonld, barre=barre)

    def accueil(self) -> None:
        # Accueil : la journée (date hébraïque, prières, horaires), puis un lien vers les livres.
        cibles = {cle: self.chemins[cible] for cle, cible in CIBLES.items() if cible in self.chemins}
        couverture = next((p for p in ('assets/covers/' + m + '.jpg' for m in ('bilingue', *(lv.mode for lv in self.livres)))
                           if (self.dossier / p).exists()), 'assets/icone-192.png')
        sous_titre = ' · '.join(MENU[lv.mode] for lv in self.livres) + ' — en ligne ou en EPUB pour liseuse'
        site = {'@context': 'https://schema.org', '@type': 'WebSite', 'name': SITE_NAME,
                'description': SITE_DESCRIPTION, 'inLanguage': 'fr'}
        if self.url:
            site['url'] = self.url
        self.write('index.html', SITE_NAME + ' — prières et horaires du jour, siddour en ligne',
                   'Date hébraïque, prières du jour et horaires (zmanim) pour sa ville, Chabbat, fêtes et jeûnes à venir. '
                   'Puis le siddour séfarade complet à lire en ligne ou en EPUB.',
                   corps(cibles, couverture, sous_titre) + '<script src="assets/aujourdhui.js" defer></script>',
                   jsonld=[site])

        # Livres : les éditions en 2 × 2 sur téléphone, avec une case d'aide à la lecture sur liseuse.
        cartes = ''.join(
            '<div class="edition-carte"><a href="' + lv.mode + '/index.html"><img src="assets/covers/' + lv.mode
            + '.jpg" alt="Couverture : ' + html.escape(lv.title, quote=True) + '" width="400" height="600"'
            + (' loading="lazy"' if i > 1 else '') + '></a><h2>' + MENU[lv.mode] + '</h2>'
            '<p class="texte">Textes ' + TEXTE[lv.mode] + '</p>'
            '<p class="actions"><a class="bouton" href="' + lv.mode + '/index.html">Lire</a>'
            '<a class="bouton second" href="telecharger/' + EPUB_NAME.format(lv.mode) + '" download>EPUB</a></p></div>'
            for i, lv in enumerate(self.livres))
        aide = ('<div class="edition-carte carte-aide"><h2>Sur liseuse</h2>'
                '<p>Télécharger l’EPUB, puis l’ouvrir sur sa liseuse (Kobo, PocketBook, Apple Livres…) '
                'ou l’envoyer sur Kindle avec « Send to Kindle ».</p>'
                '<p>Les éditions se lisent aussi en ligne, même sans connexion une fois gardées.</p>'
                '<p><a href="' + self.github + '/releases">Toutes les versions</a></p></div>')
        body = ('<h1>' + SITE_NAME + '</h1><p class="accroche">' + TAGLINE + '</p>'
                '<section id="telecharger"><div class="editions">' + cartes + aide + '</div>'
                '<p class="accroche">' + exposants(self.version.complet) + '</p></section>'
                + web_html(INTRODUCTION).replace('<h1>', '<h2>').replace('</h1>', '</h2>'))
        work = {'@context': 'https://schema.org', '@type': 'Book', 'name': 'Siddour séfarade (Edot HaMizrah)',
                'description': SITE_DESCRIPTION, 'genre': 'Liturgie juive', 'keywords': ', '.join(SUBJECTS),
                'workExample': [self.book_jsonld(lv) for lv in self.livres]}
        self.write('livres.html', 'Le siddour en ligne et en EPUB — ' + SITE_NAME,
                   SITE_DESCRIPTION, body, jsonld=[work, self.breadcrumb([(SITE_NAME, ''), ('Livres', 'livres.html')])])
        self.write('404.html', 'Page introuvable — ' + SITE_NAME, SITE_DESCRIPTION,
                   '<h1>Page introuvable</h1><p style="text-align:center">'
                   '<a class="bouton" href="' + (self.url or 'index.html') + '">Retour à l’accueil</a></p>', index=False)
        self.write('hors-ligne.html', 'Hors connexion — ' + SITE_NAME, SITE_DESCRIPTION,
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
            cover = cover_image(lv.mode)
            if not cover:
                continue
            with Image.open(io.BytesIO(cover[1])) as im:
                im = im.convert('RGB')
                im.thumbnail((800, 1200))
                im.save(dossier / 'covers' / (lv.mode + '.jpg'), 'JPEG', quality=85, optimize=True, progressive=True)
        if not (ICONES / 'logo.png').exists():
            generer_icones()
        shutil.copytree(ICONES, dossier, dirs_exist_ok=True)
        telecharger = self.dossier / 'telecharger'
        telecharger.mkdir(exist_ok=True)
        for lv in self.livres:
            shutil.copyfile(sortie / EPUB_NAME.format(lv.mode), telecharger / EPUB_NAME.format(lv.mode))
        (self.dossier / '.nojekyll').write_text('', encoding='utf-8')
        if RACINE.is_dir():
            shutil.copytree(RACINE, self.dossier, dirs_exist_ok=True)

    def index_moteurs(self) -> None:
        # Tout est permis, aux moteurs de recherche comme aux robots des IA (entraînement, recherche,
        # réponses) : les textes sont libres et le siddour gagne à être trouvé. Les robots d'IA sont
        # nommés pour que l'autorisation reste explicite, même pour ceux qui ne lisent que leur nom.
        lignes = ['# Siddour séfarade : exploration et réutilisation permises à tous, IA comprises.',
                  '# Textes : Sefaria (licences indiquées sur chaque édition).', '',
                  'User-agent: *', 'Allow: /', '']
        lignes += ['User-agent: ' + robot for robot in ROBOTS_IA] + ['Allow: /', '']
        if self.url:
            jour = self.version.jour.isoformat()
            urls = ''.join('<url><loc>' + html.escape(self.abs(p.removesuffix('index.html'))) + '</loc><lastmod>'
                           + jour + '</lastmod></url>\n' for p in self.pages)
            (self.dossier / 'sitemap.xml').write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '</urlset>\n',
                encoding='utf-8')
            lignes.append('Sitemap: ' + self.abs('sitemap.xml'))
        (self.dossier / 'robots.txt').write_text('\n'.join(lignes) + '\n', encoding='utf-8')

    # -- Application installable (PWA) -----------------------------------------------------
    def pwa(self) -> None:
        liste = [{'src': 'assets/icone-' + n + '.png', 'sizes': s + 'x' + s, 'type': 'image/png', 'purpose': p}
                  for n, s, p in (('192', '192', 'any'), ('512', '512', 'any'), ('maskable', '512', 'maskable'))]
        manifest = {
            'id': './', 'name': SITE_NAME, 'short_name': 'Siddour', 'description': SITE_DESCRIPTION,
            'lang': 'fr', 'dir': 'ltr', 'start_url': './', 'scope': './', 'display': 'standalone',
            'background_color': '#fbf9f4', 'theme_color': '#15284a', 'categories': ['books', 'education'],
            'icons': liste,
            'shortcuts': [{'name': EDITIONS[lv.mode], 'short_name': MENU[lv.mode], 'url': lv.mode + '/index.html',
                           'icons': liste[:1]} for lv in self.livres]
                         + [{'name': 'Les livres', 'short_name': 'Livres', 'url': 'livres.html', 'icons': liste[:1]}],
        }
        (self.dossier / 'manifest.webmanifest').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
        (self.dossier / 'assets' / 'app.js').write_text(
            APP_JS.replace('__VERSION__', json.dumps(self.version.complet, ensure_ascii=False)), encoding='utf-8')

        # Le nom du cache combine l'édition et une empreinte de tout le site :
        # une nouvelle révision, comme une simple correction, déclenche la mise à jour.
        empreinte = hashlib.sha256()
        for f in sorted(p for p in self.dossier.rglob('*') if p.is_file()):
            empreinte.update(f.relative_to(self.dossier).as_posix().encode() + b'\0' + f.read_bytes())
        nom = (self.version.tag if self.version.edition else 'travail') + '-' + empreinte.hexdigest()[:12]
        coquille = (['index.html', 'livres.html', 'hors-ligne.html', 'manifest.webmanifest', 'assets/style.css',
                     'assets/app.js', 'assets/aujourdhui.js', 'assets/' + FONT_PATH.name]
                    + [i['src'] for i in liste] + ['assets/icone-32.png', 'assets/icone-180.png', 'assets/papier.jpg', 'assets/logo.png']
                    + [p.relative_to(self.dossier).as_posix() for p in sorted((self.dossier / 'assets' / 'covers').glob('*.jpg'))]
                    + [lv.mode + '/index.html' for lv in self.livres])
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
