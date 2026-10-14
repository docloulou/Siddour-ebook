"""Page d'accueil « Aujourd'hui » : dates grégorienne et hébraïque, prières du jour, horaires.

Tout est calculé dans le navigateur du lecteur :
- la date hébraïque par le calendrier hébraïque du navigateur (Intl), même hors connexion ;
- les horaires (zmanim), le Chabbat, les fêtes et les jeûnes par l'API de Hebcal.com
  (https://www.hebcal.com/home/developer-apis, données sous licence CC BY 4.0) ;
- la recherche de ville par l'API de géocodage d'Open-Meteo (noms en français, fuseau horaire) ;
- le nom de la ville trouvée par « Utiliser ma position » par l'API de BigDataCloud.
L'édition du siddour (hébreu, phonétique, bilingue), et son rite quand le site en a plusieurs,
est demandée une seule fois, à la première visite.
Les réglages (ville, allumage, sortie de Chabbat, rite, édition) restent dans le localStorage ;
la dernière réponse de Hebcal y est gardée pour un affichage hors connexion.
"""
from __future__ import annotations

import html
import json

# Pages du siddour proposées selon le jour : (chapitre du plan, titre de section ou None = début du chapitre).
CIBLES = {
    'matin': ('benedictions-du-matin', None),
    'talith': ('talith-et-tefilines', None),
    'chaharit': ('priere-du-matin', None),
    'torah': ('priere-du-matin', 'Lecture de la Torah (lundi et jeudi)'),
    'minha': ('priere-de-l-apres-midi', None),
    'arvit': ('priere-du-soir', None),
    'coucher': ('priere-du-coucher', None),
    'omer': ('omer', None),
    'havdala': ('havdala', 'Havdala'),
    'roch-hodech': ('roch-hodech', None),
    'hallel': ('roch-hodech', 'Hallel'),
    'moussaf': ('roch-hodech', 'Moussaf'),
    'hanouka': ('hanouka', 'Allumage'),
    'hanouka-matin': ('hanouka', 'Cha’harit de ’Hanouka'),
    'meguila': ('pourim', 'Lecture de la Méguila'),
    'pourim': ('pourim', 'Le jour de Pourim'),
    'Tzom Gedaliah': ('jeunes', 'Tsom Guédalia'),
    "Asara B'Tevet": ('jeunes', '10 Tévèt'),
    "Ta'anit Esther": ('jeunes', 'Jeûne d’Esther'),
    'Tzom Tammuz': ('jeunes', '17 Tamouz'),
    'jeune-torah': ('jeunes', 'Lecture de la Torah des jours de jeûne'),
    'hamazone': ('apres-le-repas', None),
    'me-ene-chaloch': ('me-ene-chaloch', None),
    'brakhot': ('avant-le-repas', None),
    'voyageur': ('priere-du-voyageur', None),
    'chir-hachirim': ('chir-hachirim', None),
    'hatsot': ('tikoun-hatsot', None),
}

AUJOURDHUI_CSS = '''
/* Page « Aujourd'hui » */
.jour { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; line-height: 1.4; }
.jour h1 { margin: .2em 0 .1em; font: bold 1.35em/1.25 system-ui, -apple-system, "Segoe UI", sans-serif; }
.jour .date-heb { margin: .1em 0; text-align: center; color: #5a4a1d; }
.jour .date-heb .he-date { font-family: "SiddurHebrew", "Noto Serif Hebrew", serif; font-size: 1.15em; margin-left: .4em; }
.jour .ce-soir { display: block; font-size: .85em; color: #6b6b6b; }
.jour .lieu { text-align: center; margin: .5em 0 .2em; font-size: .9em; color: #555; }
.jour .lien { font: inherit; color: #1f3a68; background: none; border: 0; padding: 0; text-decoration: underline;
              cursor: pointer; }
.puces { display: flex; flex-wrap: wrap; justify-content: center; gap: .35em; margin: .5em 0 0; padding: 0;
         list-style: none; }
.puces li { background: #f3ecd9; color: #5a4a1d; border-radius: 1em; padding: .15em .7em; font-size: .85em; }
.carte { border: 1px solid #e6dfcc; border-radius: 8px; padding: .7em 1em .8em; margin: 1em 0; background: #fff; }
.carte h2 { border: 0; margin: 0 0 .4em; padding: 0; font-size: 1.05em; color: #15284a; display: flex;
            justify-content: space-between; align-items: baseline; gap: .5em; }
.carte h2 small { font-weight: normal; font-size: .78em; color: #777; }
.carte ul, .carte ol { list-style: none; margin: 0; padding: 0; }
.prieres > li { display: grid; grid-template-columns: 1fr auto; gap: 0 .6em; padding: .45em .5em;
                border-radius: 6px; align-items: baseline; }
.prieres > li + li { border-top: 1px solid #f0ebdd; }
.prieres > li.maintenant { background: #eef1f7; border-top-color: transparent; }
.prieres > li.maintenant + li { border-top-color: transparent; }
.prieres .nom { font-weight: bold; font-size: 1.02em; }
.prieres a.nom { text-decoration: none; }
.prieres a.nom::after { content: " ›"; }
.prieres .quand { color: #555; font-size: .88em; white-space: nowrap; text-align: right; }
.prieres .maintenant .quand::before { content: "● "; color: #2e7d32; }
.prieres .notes { grid-column: 1 / -1; margin: .15em 0 0; font-size: .86em; color: #555; }
.prieres .notes a { white-space: nowrap; }
.raccourcis { display: flex; flex-wrap: wrap; gap: .4em; margin: .7em 0 0; }
.raccourcis a { font-size: .85em; text-decoration: none; border: 1px solid #d8cfb8; border-radius: 1em;
                padding: .2em .7em; color: #15284a; }
.zmanim li { display: grid; grid-template-columns: 3.4em 1fr; gap: 0 .6em; padding: .35em 0; }
.zmanim li + li { border-top: 1px solid #f0ebdd; }
.zmanim time { font-weight: bold; font-variant-numeric: tabular-nums; }
.zmanim .titre { font-weight: 600; }
.zmanim .com { display: block; font-size: .84em; color: #666; }
.zmanim .passe { color: #999; }
.zmanim .passe .com { color: #aaa; }
.zmanim .prochain { background: #fbf4dd; border-radius: 6px; margin: 0 -.4em; padding: .35em .4em; }
.zmanim .prochain + li { border-top-color: transparent; }
.lignes li { display: flex; justify-content: space-between; gap: .8em; padding: .3em 0; }
.lignes li + li { border-top: 1px solid #f0ebdd; }
.lignes b { font-variant-numeric: tabular-nums; white-space: nowrap; }
.chabbat-titre { font-weight: bold; margin: 0 0 .3em; }
.chabbat-titre .he-nom { font-family: "SiddurHebrew", "Noto Serif Hebrew", serif; font-weight: normal;
                         color: #5a4a1d; margin-left: .4em; }
.fetes > li { padding: .45em 0; }
.fetes > li + li { border-top: 1px solid #f0ebdd; }
.fetes .quand { color: #555; font-size: .88em; }
.fetes .heures { display: block; font-size: .85em; color: #555; }
.fetes .en-cours { color: #2e7d32; font-size: .8em; margin-left: .3em; }
.discret { font-size: .78em; color: #777; margin: .5em 0 0; }
.vers-livres { display: flex; align-items: center; gap: .8em; margin: 1.2em 0; padding: .8em 1em; border-radius: 8px;
               background: #15284a; color: #f1e4bf; text-decoration: none; }
.vers-livres img { width: 2.6em; height: auto; border-radius: 2px; box-shadow: 0 1px 4px rgba(0,0,0,.4); }
.vers-livres span { flex: 1; }
.vers-livres small { display: block; opacity: .85; }
.vers-livres::after { content: "›"; font-size: 1.6em; line-height: 1; }
/* Choix de l'édition : pastilles du panneau « Prières du jour » et de la première visite. */
.segments { display: flex; flex-wrap: wrap; gap: .35em; margin: .4em 0; }
.segments button { font: inherit; font-size: .88em; cursor: pointer; border: 1px solid #c9bfa6; border-radius: 1em;
                   background: #fff; color: #15284a; padding: .25em .75em; }
.segments button[aria-pressed="true"] { border-color: #15284a; background: #eef1f7; box-shadow: inset 0 0 0 1px #15284a; }
.choix-edition { margin: -.1em 0 .5em; padding: .5em .6em; background: #faf6ea; border-radius: 6px; font-size: .9em; }
.choix-edition[hidden] { display: none; }
.choix-edition p { margin: 0; color: #555; }
.choix-edition .segments { margin: .35em 0 0; }
.choix-edition .segments + p { margin-top: .6em; }
.premier-choix .choix-rite { justify-content: center; margin: 0 0 .4em; }
.premier-choix { box-sizing: border-box; width: calc(100% - 2em); max-width: 23em; border: 0; border-radius: 12px;
                 padding: 1.2em 1.1em 1em; background: #fff; color: #1d1d1d; box-shadow: 0 10px 40px rgba(0,0,0,.35);
                 font-family: system-ui, -apple-system, "Segoe UI", sans-serif; line-height: 1.4; }
.premier-choix[open] { position: fixed; inset: 0; margin: auto; height: fit-content; z-index: 100; }
.premier-choix::backdrop { background: rgba(21, 40, 74, .55); }
.premier-choix h2 { border: 0; margin: 0 0 .2em; padding: 0; font-size: 1.15em; color: #15284a; text-align: center; }
.premier-choix p { margin: .3em 0 .8em; text-align: center; color: #555; }
.premier-choix .options { display: grid; gap: .5em; }
.premier-choix .options button { display: flex; justify-content: space-between; align-items: baseline; gap: .8em;
                 font: inherit; text-align: left; cursor: pointer; padding: .7em .9em; border: 1px solid #c9bfa6;
                 border-radius: 8px; background: #fff; color: #15284a; }
.premier-choix .options button:hover, .premier-choix .options button:focus-visible { border-color: #15284a;
                 background: #eef1f7; }
.premier-choix .ex { color: #666; font-size: .88em; }
.premier-choix .ex[lang=he] { font-family: "SiddurHebrew", "Noto Serif Hebrew", serif; font-size: 1.2em; color: #5a4a1d; }
.premier-choix .discret { margin: .9em 0 0; }
/* Réglages de la page : ville et horaires de Chabbat. */
.reglages-jour { scroll-margin-top: 6em; }
.reglages-jour[hidden] { display: none; }
.reglages-jour label, .reglages-jour .etiquette { display: block; font-weight: 600; font-size: .9em; margin: .7em 0 .25em; }
.reglages-jour input[type=search], .reglages-jour select { box-sizing: border-box; width: 100%; font: inherit;
              padding: .45em .6em; border: 1px solid #c9bfa6; border-radius: 6px; background: #fff; color: #1d1d1d; }
.reglages-jour .resultats li button, .reglages-jour .villes button, .reglages-jour .actions button { font: inherit; font-size: .88em; cursor: pointer; border: 1px solid #c9bfa6;
              border-radius: 1em; background: #fff; color: #15284a; padding: .25em .75em; }
.reglages-jour .resultats { margin: .3em 0; }
.reglages-jour .resultats li button { display: block; width: 100%; text-align: left; border-radius: 6px; margin: .2em 0; }
.reglages-jour .villes { display: flex; flex-wrap: wrap; gap: .35em; margin: .4em 0; }
.reglages-jour .villes button[aria-pressed="true"] { border-color: #15284a; background: #eef1f7; box-shadow: inset 0 0 0 1px #15284a; }
.reglages-jour .actions { display: flex; justify-content: space-between; gap: .5em; margin-top: 1em; }
.reglages-jour .actions .ok { background: #15284a; color: #f1e4bf; border-color: #15284a; }
.reglages-jour .etat { font-size: .82em; color: #666; min-height: 1.2em; margin: .2em 0; }
'''

LIVRES_CSS = '''
/* Page des livres : 2 × 2 sur téléphone (3 éditions et l'aide), 4 colonnes sur grand écran. */
.editions { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1em; }
.edition-carte { display: flex; flex-direction: column; }
.edition-carte h2 { font-size: .98em; margin: .5em 0 .1em; }
.edition-carte .actions { display: flex; flex-wrap: wrap; justify-content: center; gap: .3em; margin-top: auto;
                          padding-top: .4em; }
.edition-carte .actions a { font-size: .85em; padding: .3em .7em; }
.carte-aide { border: 1px solid #e6dfcc; border-radius: 6px; padding: .7em; font-size: .85em; line-height: 1.4;
              text-align: left; background: #faf6ea; }
.carte-aide h2 { text-align: center; }
.carte-aide p { margin: .4em 0; }
.rite-titre { text-align: center; margin: 1.6em 0 0; }
.rite + .rite { margin-top: 2em; padding-top: .4em; border-top: 1px solid #e6dfcc; }
@media (max-width: 40em) { .editions { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .8em; margin: 1em 0; }
                           .edition-carte p.texte { display: none; } }
'''

AUJOURDHUI_JS = r'''"use strict";
// Page « Aujourd'hui » : voir siddour/aujourdhui.py.
(() => {
  const page = document.querySelector("[data-aujourdhui]");
  if (!page) return;
  const $ = (s) => page.querySelector(s);
  // Par rite : nom, préfixe des pages, éditions publiées et pages du jour (voir corps()).
  const RITES = JSON.parse(document.getElementById("cibles").textContent);
  const HEBCAL = "https://www.hebcal.com/";
  const GEO = "https://geocoding-api.open-meteo.com/v1/search";
  const GEO_INVERSE = "https://api.bigdatacloud.net/data/reverse-geocode-client";
  const CLE = "siddour-jour", CLE_CACHE = "siddour-jour-cache";
  const PARIS = { nom: "Paris", pays: "France", cc: "FR", lat: 48.85341, lon: 2.3488, tz: "Europe/Paris" };
  const VILLES = [PARIS,
    { nom: "Marseille", pays: "France", cc: "FR", lat: 43.29695, lon: 5.38107, tz: "Europe/Paris" },
    { nom: "Lyon", pays: "France", cc: "FR", lat: 45.74846, lon: 4.84671, tz: "Europe/Paris" },
    { nom: "Nice", pays: "France", cc: "FR", lat: 43.70313, lon: 7.26608, tz: "Europe/Paris" },
    { nom: "Strasbourg", pays: "France", cc: "FR", lat: 48.58392, lon: 7.74553, tz: "Europe/Paris" },
    { nom: "Toulouse", pays: "France", cc: "FR", lat: 43.60426, lon: 1.44367, tz: "Europe/Paris" },
    { nom: "Jérusalem", pays: "Israël", cc: "IL", lat: 31.76904, lon: 35.21633, tz: "Asia/Jerusalem" },
    { nom: "Tel-Aviv", pays: "Israël", cc: "IL", lat: 32.08088, lon: 34.78057, tz: "Asia/Jerusalem" },
    { nom: "Netanya", pays: "Israël", cc: "IL", lat: 32.33291, lon: 34.85992, tz: "Asia/Jerusalem" },
    { nom: "Bruxelles", pays: "Belgique", cc: "BE", lat: 50.85045, lon: 4.34878, tz: "Europe/Brussels" },
    { nom: "Genève", pays: "Suisse", cc: "CH", lat: 46.20222, lon: 6.14569, tz: "Europe/Zurich" },
    { nom: "Montréal", pays: "Canada", cc: "CA", lat: 45.50884, lon: -73.58781, tz: "America/Toronto" }];
  const EDITIONS = { hebreu: "Hébreu", phonetique: "Phonétique", bilingue: "Bilingue" };

  // -- Réglages, gardés sur l'appareil ------------------------------------------------------
  let reglages = {};
  try { reglages = JSON.parse(localStorage.getItem(CLE)) || {}; } catch (e) {}
  const lieu = () => reglages.lieu || PARIS;
  const rite = () => RITES[reglages.rite] ? reglages.rite : Object.keys(RITES)[0];
  const edition = () => {
    const modes = RITES[rite()].modes;
    return modes.includes(reglages.edition) ? reglages.edition : modes.includes("bilingue") ? "bilingue" : modes[0];
  };
  const dossier = () => RITES[rite()].prefixe + edition() + "/";
  const enregistrer = () => { try { localStorage.setItem(CLE, JSON.stringify(reglages)); } catch (e) {} };
  const jerusalem = (l) => Math.abs(l.lat - 31.77) < .12 && Math.abs(l.lon - 35.22) < .12;
  const minutesBougies = () => reglages.bougies ? Number(reglages.bougies) : (jerusalem(lieu()) ? 40 : 18);
  const israel = (l) => l.cc === "IL" || l.tz === "Asia/Jerusalem";

  // -- Dates -----------------------------------------------------------------------------------
  const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const tz = () => lieu().tz;
  const jourIso = (d) => new Intl.DateTimeFormat("en-CA", { timeZone: tz(), year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
  const midi = (iso) => new Date(iso + "T12:00:00Z");  // un jour civil, sans souci de fuseau
  const ajouter = (iso, n) => { const d = midi(iso); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
  const semaine = (iso) => midi(iso).getUTCDay();  // 0 dimanche … 6 samedi
  const fmtJour = (iso, opts) => new Intl.DateTimeFormat("fr-FR", Object.assign({ timeZone: "UTC" }, opts)).format(midi(iso));
  const jourCourt = (iso) => fmtJour(iso, { weekday: "short", day: "numeric", month: "short" });
  const heure = (t) => t ? new Intl.DateTimeFormat("fr-FR", { timeZone: tz(), hour: "2-digit", minute: "2-digit" }).format(new Date(t)) : "";
  const majuscule = (t) => t.charAt(0).toUpperCase() + t.slice(1);

  // Mois hébreux : noms du calendrier du navigateur (ICU) et de Hebcal → français et hébreu.
  const MOIS = {
    Tishri: ["Tichri", "תשרי"], Tishrei: ["Tichri", "תשרי"], Heshvan: ["’Hechvan", "חשון"], Cheshvan: ["’Hechvan", "חשון"],
    Kislev: ["Kislev", "כסלו"], Tevet: ["Tévet", "טבת"], Shevat: ["Chevat", "שבט"], "Sh'vat": ["Chevat", "שבט"],
    "Adar I": ["Adar I", "אדר א׳"], Adar: ["Adar", "אדר"], "Adar II": ["Adar II", "אדר ב׳"], Nisan: ["Nissan", "ניסן"],
    Iyar: ["Iyar", "אייר"], Iyyar: ["Iyar", "אייר"], Sivan: ["Sivan", "סיון"], Tamuz: ["Tamouz", "תמוז"],
    Tammuz: ["Tamouz", "תמוז"], Av: ["Av", "אב"], Elul: ["Eloul", "אלול"],
  };
  const gematria = (n) => {
    const U = ["", "א", "ב", "ג", "ד", "ה", "ו", "ז", "ח", "ט"], D = ["", "י", "כ", "ל", "מ", "נ", "ס", "ע", "פ", "צ"];
    const C = ["", "ק", "ר", "ש", "ת", "תק", "תר", "תש", "תת", "תתק"];
    let s = C[Math.floor(n / 100) % 10] + D[Math.floor(n / 10) % 10] + U[n % 10];
    s = s.replace("יה", "טו").replace("יו", "טז");
    return s.length > 1 ? s.slice(0, -1) + "״" + s.slice(-1) : s + "׳";
  };
  const dateHebraique = (iso) => {
    try {
      const p = {};
      for (const x of new Intl.DateTimeFormat("en-u-ca-hebrew", { timeZone: "UTC", day: "numeric", month: "long", year: "numeric" })
        .formatToParts(midi(iso))) p[x.type] = x.value;
      const jour = parseInt(p.day, 10), an = parseInt(p.year || p.relatedYear, 10), mois = MOIS[p.month] || [p.month, ""];
      return { jour, an, mois: p.month, fr: jour + (jour === 1 ? "ᵉʳ" : "") + " " + mois[0] + " " + an,
               he: gematria(jour) + " " + mois[1] + " " + gematria(an % 1000) };
    } catch (e) { return null; }
  };

  // -- Noms français des fêtes, jeûnes, parachiot ------------------------------------------
  const FETES = {
    "Rosh Hashana": "Roch Hachana", "Yom Kippur": "Yom Kippour", Sukkot: "Souccot", "Shmini Atzeret": "Chemini ’Atsérèt",
    "Simchat Torah": "Sim’hat Torah", Chanukah: "’Hanouka", "Tu BiShvat": "Tou bichvat", Purim: "Pourim",
    "Shushan Purim": "Chouchane Pourim", Pesach: "Pessa’h", "Pesach Sheni": "Pessa’h chéni", "Lag BaOmer": "Lag ba’omer",
    Shavuot: "Chavou’ot", "Tish'a B'Av": "Tich’a béav", "Tu B'Av": "Tou béav", "Tzom Gedaliah": "Jeûne de Guédalia",
    "Asara B'Tevet": "Jeûne du 10 Tévet", "Ta'anit Esther": "Jeûne d’Esther", "Ta'anit Bechorot": "Jeûne des premiers-nés",
    "Tzom Tammuz": "Jeûne du 17 Tamouz",
  };
  const PARACHIOT = {
    Bereshit: "Béréchit", Noach: "Noa’h", "Lech-Lecha": "Lekh Lekha", Vayera: "Vayéra", "Chayei Sara": "’Hayé Sarah",
    Toldot: "Toledot", Vayetzei: "Vayétsé", Vayishlach: "Vayichla’h", Vayeshev: "Vayéchev", Miketz: "Mikets",
    Vayigash: "Vayigach", Vayechi: "Vay’hi", Shemot: "Chemot", Vaera: "Vaéra", Bo: "Bo", Beshalach: "Béchala’h",
    Yitro: "Yitro", Mishpatim: "Michpatim", Terumah: "Terouma", Tetzaveh: "Tetsavé", "Ki Tisa": "Ki Tissa",
    Vayakhel: "Vayakhel", Pekudei: "Pekoudé", Vayikra: "Vayikra", Tzav: "Tsav", Shmini: "Chemini", Tazria: "Tazria",
    Metzora: "Metsora", "Achrei Mot": "A’haré Mot", Kedoshim: "Kedochim", Emor: "Emor", Behar: "Behar",
    Bechukotai: "Be’houkotaï", Bamidbar: "Bamidbar", Nasso: "Nasso", "Beha'alotcha": "Beha’alotekha",
    "Sh'lach": "Chela’h Lekha", Korach: "Kora’h", Chukat: "’Houkat", Balak: "Balak", Pinchas: "Pin’has", Matot: "Matot",
    Masei: "Massé", Devarim: "Devarim", Vaetchanan: "Vaét’hanan", Eikev: "’Ekev", "Re'eh": "Reéh", Shoftim: "Choftim",
    "Ki Teitzei": "Ki Tétsé", "Ki Tavo": "Ki Tavo", Nitzavim: "Nitsavim", Vayeilech: "Vayélekh", "Ha'azinu": "Haazinou",
  };
  const CHABBATOT = {
    "Shabbat Shuva": "Chabbat Chouva", "Shabbat Shekalim": "Chabbat Chekalim", "Shabbat Zachor": "Chabbat Zakhor",
    "Shabbat Parah": "Chabbat Para", "Shabbat HaChodesh": "Chabbat Ha’hodech", "Shabbat HaGadol": "Chabbat Hagadol",
    "Shabbat Chazon": "Chabbat ’Hazon", "Shabbat Nachamu": "Chabbat Na’hamou", "Shabbat Shirah": "Chabbat Chira",
  };
  const norm = (t) => (t || "").replace(/[’‘]/g, "'");
  const base = (t) => norm(t).replace(/^Erev /, "").replace(/:.*$/, "").replace(/ \d{4}$/, "")
    .replace(/ \(.*\)$/, "").replace(/ [IVX]+$/, "").replace(/ \(.*\)$/, "");
  const parachaFr = (titre) => {
    const nom = norm(titre).replace(/^Parashat /, "");
    return "Parachat " + (PARACHIOT[nom] || nom.split("-").map((p) => PARACHIOT[p] || p).join("-"));
  };

  // -- Hebcal : horaires de la semaine et calendrier sur six mois, gardés pour le hors-connexion --
  const parametres = (l) => "latitude=" + l.lat + "&longitude=" + l.lon + "&tzid=" + encodeURIComponent(l.tz);
  const signature = () => {
    const l = lieu();
    return [l.lat, l.lon, l.tz, minutesBougies(), reglages.sortie || "tset", israel(l) ? "il" : ""].join("|");
  };
  const lireCache = () => { try { return JSON.parse(localStorage.getItem(CLE_CACHE)) || null; } catch (e) { return null; } };
  const reduire = (it) => {
    const r = { t: norm(it.title), c: it.category, d: it.date };
    for (const [k, v] of [["s", it.subcat], ["h", it.hebrew], ["m", it.memo && it.category !== "holiday" ? norm(it.memo) : ""],
      ["y", it.yomtov]]) if (v) r[k] = v;
    return r;
  };
  async function charger(aujourdhui) {
    const cache = lireCache();
    const sig = signature();
    if (cache && cache.sig === sig && cache.debut <= aujourdhui && cache.fin >= ajouter(aujourdhui, 2)
        && cache.recu === aujourdhui) return cache;
    const l = lieu();
    const debut = ajouter(aujourdhui, -1), fin = ajouter(aujourdhui, 7);
    const sortie = reglages.sortie === "72" ? "&m=72" : "&M=on";
    try {
      const [z, c] = await Promise.all([
        fetch(HEBCAL + "zmanim?cfg=json&" + parametres(l) + "&start=" + debut + "&end=" + fin).then((r) => r.ok ? r.json() : Promise.reject(r)),
        // Calendrier pris dix jours en arrière : une fête en cours garde sa vraie date de début.
        fetch(HEBCAL + "hebcal?v=1&cfg=json&" + parametres(l) + "&start=" + ajouter(aujourdhui, -10) + "&end=" + ajouter(aujourdhui, 200)
          + "&maj=on&min=on&mod=off&nx=on&mf=on&ss=on&s=on&o=on&c=on&leyning=off&b=" + minutesBougies() + sortie
          + (israel(l) ? "&i=on" : "&i=off")).then((r) => r.ok ? r.json() : Promise.reject(r)),
      ]);
      const donnees = { sig, recu: aujourdhui, debut, fin, zmanim: z.times, items: c.items.map(reduire) };
      try { localStorage.setItem(CLE_CACHE, JSON.stringify(donnees)); } catch (e) {}
      return donnees;
    } catch (e) {
      // Hors connexion : les données gardées servent tant qu'elles couvrent la date du jour.
      if (cache && cache.sig === sig && cache.debut <= aujourdhui && cache.fin >= aujourdhui) return cache;
      return null;
    }
  }

  // -- Ce que l'on sait d'un jour ------------------------------------------------------------
  const infos = (donnees, iso) => {
    const items = donnees ? donnees.items.filter((i) => i.d.slice(0, 10) === iso) : [];
    const fetes = items.filter((i) => i.c === "holiday");
    const titre = (re) => fetes.find((i) => re.test(i.t));
    const he = dateHebraique(iso);
    const chabbat = semaine(iso) === 6;
    const yomtov = fetes.some((i) => i.y);
    return {
      iso, items, he, chabbat, yomtov, saint: chabbat || yomtov, yomtovNom: (fetes.find((i) => i.y) || {}).t,
      rochHodech: items.some((i) => i.c === "roshchodesh") || (!!he && !donnees && (he.jour === 30 || (he.jour === 1 && he.mois !== "Tishri"))),
      cholHamoed: !!titre(/CH''M|Hoshana Raba/),
      hanouka: !!titre(/^Chanukah: ([2-8] Candles|8th Day)/),
      bougiesHanouka: (titre(/^Chanukah: \d Candle/) || { t: "" }).t.replace(/^Chanukah: (\d).*$/, "$1"),
      jeune: fetes.find((i) => i.s === "fast" || /^Tish'a B'Av/.test(i.t)),
      veilleTichaBeav: !!titre(/^Erev Tish'a B'Av/),
      pourim: !!titre(/^Purim$/), veillePourim: !!titre(/^Erev Purim/),
      omer: (items.find((i) => i.c === "omer") || { t: "" }).t.replace(/^(\d+).*$/, "$1"),
      bougies: items.find((i) => i.c === "candles"),
      havdala: items.find((i) => i.c === "havdalah"),
      debutJeune: items.find((i) => i.c === "zmanim" && i.s === "fast" && /begins/.test(i.t)),
      finJeune: items.find((i) => i.c === "zmanim" && i.s === "fast" && /ends/.test(i.t)),
    };
  };
  const zman = (donnees, cle, iso) => donnees && donnees.zmanim[cle] ? donnees.zmanim[cle][iso] : null;

  // -- Affichage ---------------------------------------------------------------------------
  const lien = (cle, texte, classe) => RITES[rite()].pages[cle]
    ? '<a' + (classe ? ' class="' + classe + '"' : "") + ' href="' + dossier() + RITES[rite()].pages[cle] + '">' + texte + "</a>"
    : (classe ? '<span class="' + classe + '">' + texte + "</span>" : texte);

  function afficherDate(aujourdhui, donnees, maintenant) {
    $(".date-greg").textContent = majuscule(fmtJour(aujourdhui, { weekday: "long", day: "numeric", month: "long", year: "numeric" }));
    const he = dateHebraique(aujourdhui);
    const coucher = zman(donnees, "sunset", aujourdhui);
    let texte = "";
    if (he) {
      texte = esc(he.fr).replace("ᵉʳ", "<sup>er</sup>") + '<span class="he-date" lang="he" dir="rtl">' + he.he + "</span>";
      const demain = dateHebraique(ajouter(aujourdhui, 1));
      if (coucher && demain) texte += '<span class="ce-soir">' + (maintenant >= new Date(coucher) ? "Depuis" : "Dès")
        + " le coucher du soleil (" + heure(coucher) + ") : " + esc(demain.fr).replace("ᵉʳ", "<sup>er</sup>") + "</span>";
    }
    $(".date-heb").innerHTML = texte;
    const l = lieu();
    $(".lieu .ville").textContent = l.nom + (l.pays ? ", " + l.pays : "") + (reglages.lieu ? "" : " (par défaut)");
  }

  function prieres(donnees, aujourdhui, maintenant) {
    const t = infos(donnees, aujourdhui), d = infos(donnees, ajouter(aujourdhui, 1));
    const z = (cle, iso) => zman(donnees, cle, iso || aujourdhui);
    const lignes = [];
    const nomSaint = (j) => j.yomtov ? "de " + (FETES[base(j.yomtovNom)] || "fête") : "de Chabbat";

    // Matin
    if (t.saint) {
      lignes.push({ cle: "matin", nom: "Cha’harit et Moussaf " + nomSaint(t), quand: "", notes: ["Office propre à ce jour, pas encore dans ce siddour."] });
    } else {
      const notes = [lien("matin", "Bénédictions du matin") + " · " + lien("talith", "Talith et téfilines")];
      if (t.rochHodech) notes.push("Roch ’Hodech : Yaalé véyavo, " + lien("hallel", "Hallel") + " et " + lien("moussaf", "Moussaf"));
      if (t.cholHamoed) notes.push("’Hol hamoèd : Yaalé véyavo, Hallel et Moussaf de la fête");
      if (t.hanouka) notes.push("’Hanouka : Al hanissim et " + lien("hanouka-matin", "Hallel complet"));
      if (t.pourim) notes.push("Pourim : Al hanissim, " + lien("pourim", "lecture de la Méguila"));
      if (t.jeune) notes.push("Jeûne : " + lien(base(t.jeune.t), "Seli’hot") + ", " + lien("jeune-torah", "lecture de la Torah"));
      else if ((semaine(aujourdhui) === 1 || semaine(aujourdhui) === 4) && !t.rochHodech && !t.cholHamoed && !t.hanouka)
        notes.push(lien("torah", "Lecture de la Torah") + " (lundi et jeudi)");
      lignes.push({ cle: "chaharit", nom: "Cha’harit", quand: z("sofZmanTfilla") ? "avant " + heure(z("sofZmanTfilla")) : "", notes });
    }
    // Après-midi
    if (t.saint) lignes.push({ cle: "minha", nom: "Min’ha " + nomSaint(t), quand: z("sunset") ? "avant " + heure(z("sunset")) : "", notes: [] });
    else {
      const notes = [];
      if (t.jeune) notes.push("Jeûne : ’Anénou et lecture de la Torah" + (t.finJeune ? " · fin du jeûne à " + heure(t.finJeune.d) : ""));
      if (semaine(aujourdhui) === 5 && d.bougies) notes.push("La dire avant l’allumage des bougies");
      lignes.push({ cle: "minha", nom: "Min’ha", quand: z("minchaGedola") && z("sunset") ? heure(z("minchaGedola")) + " – " + heure(z("sunset")) : "", notes });
    }
    // Soir
    if (d.saint && !t.saint) {
      const notes = [];
      if (t.bougiesHanouka) notes.push("’Hanouka : " + lien("hanouka", "allumer " + t.bougiesHanouka + (t.bougiesHanouka === "1" ? " lumière" : " lumières")) + ", avant les bougies de Chabbat");
      if (t.bougies) notes.push("Allumage des bougies à <b>" + heure(t.bougies.d) + "</b>");
      if (semaine(aujourdhui) === 5) notes.push(lien("chir-hachirim", "Chir hachirim") + ", lu avant l’entrée de Chabbat");
      notes.push("Office propre à ce soir, pas encore dans ce siddour.");
      lignes.push({ cle: "arvit", nom: "Arvit " + nomSaint(d), quand: t.bougies ? "allumage " + heure(t.bougies.d) : "", notes });
    } else {
      const notes = [];
      if (t.saint && t.havdala && !d.saint) notes.push(lien("havdala", "Havdala") + " à la sortie, dès " + heure(t.havdala.d));
      if (t.bougiesHanouka) notes.push("’Hanouka : " + lien("hanouka", "allumer " + t.bougiesHanouka + (t.bougiesHanouka === "1" ? " lumière" : " lumières")));
      if (d.omer) notes.push(lien("omer", "Compter l’omer") + " : " + d.omer + (d.omer === "1" ? " jour" : " jours"));
      if (t.veillePourim) notes.push("Pourim : Al hanissim et " + lien("meguila", "lecture de la Méguila"));
      if (t.veilleTichaBeav && t.debutJeune) notes.push("Début du jeûne de Tich’a béav à " + heure(t.debutJeune.d));
      if (d.debutJeune && !d.veilleTichaBeav) notes.push("Jeûne demain, dès " + heure(d.debutJeune.d));
      if (t.saint && !d.saint) lignes.push({ cle: "arvit", nom: "Arvit de sortie", quand: t.havdala ? "dès " + heure(t.havdala.d) : "", notes: ["Ajouter Ata ’honantanou dans la Amida."].concat(notes) });
      else if (!(t.saint && d.saint)) lignes.push({ cle: "arvit", nom: "Arvit", quand: z("tzeit85deg") ? "dès " + heure(z("tzeit85deg")) : "", notes });
      else lignes.push({ cle: "arvit", nom: "Arvit " + nomSaint(d), quand: "", notes: notes.concat(["Office propre à ce soir, pas encore dans ce siddour."]) });
    }
    lignes.push({ cle: "coucher", nom: "Chéma du coucher", quand: "", notes: [] });

    // Moment présent : Cha'harit jusqu'à midi, Min'ha jusqu'au coucher du soleil, puis Arvit.
    const avant = (cle) => z(cle) && maintenant < new Date(z(cle));
    const actuel = !z("chatzot") ? "" : avant("chatzot") ? "chaharit" : avant("sunset") ? "minha" : "arvit";
    const ouvert = (l) => !/Office propre/.test(l.notes.join(" "));
    $(".prieres").innerHTML = lignes.map((l) => '<li class="' + (l.cle === actuel || (actuel === "chaharit" && l.cle === "matin") ? "maintenant" : "") + '">'
      + (ouvert(l) ? lien(l.cle, l.nom, "nom") : '<span class="nom">' + l.nom + "</span>")
      + '<span class="quand">' + l.quand + "</span>"
      + (l.notes.length ? '<p class="notes">' + l.notes.join("<br>") + "</p>" : "") + "</li>").join("");
    $(".raccourcis").innerHTML = [lien("hamazone", "Birkat hamazone"), lien("me-ene-chaloch", "Mé’ène chaloch"),
      lien("brakhot", "Bénédictions"), lien("voyageur", "Téfilat haderekh"),
      '<a href="' + dossier() + 'index.html">Tout le siddour</a>'].filter((x) => x.startsWith("<a")).join("");
  }

  const ZMANIM = [
    ["alotHaShachar", "Aube (Alot hacha’har)", "Le jour commence : Cha’harit est possible en cas de besoin."],
    ["misheyakir", "Talith et téfilines (Michéyakir)", "On peut les mettre avec leur bénédiction."],
    ["sunrise", "Lever du soleil (Nets)", "Moment idéal pour la Amida de Cha’harit (vatikin)."],
    ["sofZmanShmaMGA16Point1", "Fin du Chéma (Maguen Avraham)", "Lire le Chéma du matin avant cette heure, de préférence."],
    ["sofZmanShma", "Fin du Chéma (Gaon de Vilna)", "Dernière limite pour le Chéma du matin."],
    ["sofZmanTfilla", "Fin de la Amida du matin", "Dire la Amida de Cha’harit avant cette heure."],
    ["chatzot", "Milieu du jour (’Hatsot)", "Après cette heure, on ne dit plus Cha’harit."],
    ["minchaGedola", "Min’ha guedola", "Heure la plus tôt pour Min’ha."],
    ["minchaKetana", "Min’ha ketana", "Heure à privilégier pour Min’ha."],
    ["plagHaMincha", "Plag hamin’ha", "Dès cette heure, on peut avancer l’entrée de Chabbat."],
    ["sunset", "Coucher du soleil (Chkia)", "Terminer Min’ha avant le coucher du soleil."],
    ["tzeit85deg", "Tombée de la nuit (Tsét hakokhavim)", "Le jour hébraïque suivant commence : Chéma du soir et Arvit."],
    ["chatzotNight", "Milieu de la nuit", "Heure du Tikoun ’Hatsot.", 1],
  ];
  function horaires(donnees, aujourdhui, maintenant) {
    const liste = $(".zmanim");
    if (!donnees) {
      liste.innerHTML = '<li><span></span><span class="com">Horaires indisponibles : vérifier la connexion, puis recharger la page.</span></li>';
      return;
    }
    let prochain = false;
    liste.innerHTML = ZMANIM.map(([cle, titre, com, decalage]) => {
      const t = zman(donnees, cle, ajouter(aujourdhui, decalage || 0));
      if (!t) return "";
      let classe = new Date(t) <= maintenant ? "passe" : "";
      if (!classe && !prochain) { classe = "prochain"; prochain = true; }
      const titreLien = cle === "chatzotNight" ? lien("hatsot", titre) : titre;
      return '<li class="' + classe + '"><time datetime="' + t + '">' + heure(t) + '</time><span><span class="titre">'
        + titreLien + '</span><span class="com">' + com + "</span></span></li>";
    }).join("");
  }

  function chabbat(donnees, maintenant) {
    const bloc = $(".chabbat");
    if (!donnees) { bloc.innerHTML = '<p class="discret">Horaires indisponibles hors connexion.</p>'; return; }
    const items = donnees.items;
    const sortie = items.find((i) => i.c === "havdalah" && semaine(i.d.slice(0, 10)) === 6 && new Date(i.d) > maintenant);
    if (!sortie) { bloc.innerHTML = ""; return; }
    const samedi = sortie.d.slice(0, 10), vendredi = ajouter(samedi, -1);
    const entree = items.find((i) => i.c === "candles" && i.d.slice(0, 10) === vendredi);
    const paracha = items.find((i) => i.c === "parashat" && i.d === samedi);
    const special = items.find((i) => i.c === "holiday" && i.s === "shabbat" && i.d === samedi);
    const fete = items.find((i) => i.c === "holiday" && i.y && i.d === samedi);
    const titre = paracha ? parachaFr(paracha.t) : fete ? (FETES[base(fete.t)] || fete.t) : "Chabbat";
    const enCours = entree && new Date(entree.d) <= maintenant;
    $("#chabbat h2 small").textContent = enCours ? "Chabbat chalom !" : fmtJour(samedi, { day: "numeric", month: "long" });
    bloc.innerHTML = '<p class="chabbat-titre">' + esc(titre)
      + (paracha && paracha.h ? '<span class="he-nom" lang="he" dir="rtl">' + esc(paracha.h) + "</span>" : "")
      + (special ? " · " + esc(CHABBATOT[special.t] || special.t) : "") + "</p>"
      + '<ul class="lignes">'
      + (entree ? "<li><span>Allumage des bougies · " + jourCourt(vendredi) + "</span><b>" + heure(entree.d) + "</b></li>" : "")
      + "<li><span>Sortie de Chabbat · " + jourCourt(samedi) + "</span><b>" + heure(sortie.d) + "</b></li></ul>"
      + '<p class="discret">Allumage ' + minutesBougies() + " min avant le coucher du soleil ; sortie "
      + (reglages.sortie === "72" ? "72 min après le coucher du soleil (Rabbénou Tam)." : "à la tombée de la nuit.") + "</p>";
  }

  function fetes(donnees, aujourdhui) {
    const liste = $(".fetes");
    if (!donnees) { liste.innerHTML = '<li class="discret">Calendrier indisponible hors connexion.</li>'; return; }
    const groupes = [];
    const jours = (a, b) => Math.round((midi(b) - midi(a)) / 864e5);
    for (const i of donnees.items) {
      const jour = i.d.slice(0, 10);
      let cle, nom;
      if (i.c === "roshchodesh") { cle = i.t; nom = "Roch ’Hodech " + (MOIS[i.t.replace("Rosh Chodesh ", "")] || [i.t])[0]; }
      else if (i.c === "holiday" && ["major", "minor", "fast"].includes(i.s)) {
        cle = base(i.t);
        if (cle === "Simchat Torah") cle = "Shmini Atzeret";
        nom = cle === "Shmini Atzeret" && !israel(lieu()) ? "Chemini ’Atsérèt et Sim’hat Torah" : FETES[cle];
        if (!nom) continue;
      } else continue;
      // La 1re bougie de 'Hanouka s'allume la veille au soir, comme une entrée de fête.
      const veille = /^Erev |^Chanukah: 1 Candle/.test(i.t);
      let g = groupes.find((x) => x.cle === cle && jours(x.fin, jour) <= 2);
      if (!g) { g = { cle, nom, debut: jour, fin: jour, veille: veille ? jour : "", yomtov: [], jeune: i.s === "fast" || cle === "Tish'a B'Av" }; groupes.push(g); }
      if (veille) { g.veille = jour; if (g.debut === jour) g.debut = ajouter(jour, 1); }
      else { if (jour < g.debut) g.debut = jour; if (jour > g.fin) g.fin = jour; }
      if (i.y) g.yomtov.push(jour);
    }
    const proches = groupes.filter((g) => g.fin >= aujourdhui).slice(0, 5);
    liste.innerHTML = proches.map((g) => {
      const heures = [];
      if (g.yomtov.length) {
        // Seulement les heures à venir : pendant la fête, les allumages passés n'aident plus.
        const allumages = donnees.items.filter((i) => i.c === "candles" && i.d.slice(0, 10) >= aujourdhui && g.yomtov.includes(ajouter(i.d.slice(0, 10), 1)));
        const fins = donnees.items.filter((i) => i.c === "havdalah" && g.yomtov.includes(i.d.slice(0, 10)) && !g.yomtov.includes(ajouter(i.d.slice(0, 10), 1)));
        if (allumages.length) heures.push("Allumage " + allumages.map((i) => jourCourt(i.d.slice(0, 10)) + " " + heure(i.d)).join(", "));
        if (fins.length) heures.push("fin " + fins.map((i) => jourCourt(i.d.slice(0, 10)) + " " + heure(i.d)).join(", "));
      }
      if (g.cle === "Chanukah" && g.veille >= aujourdhui) heures.push("1<sup>re</sup> bougie " + jourCourt(g.veille) + " au soir");
      if (g.jeune) {
        const z = donnees.items.filter((i) => i.c === "zmanim" && i.s === "fast" && base(i.m) === g.cle);
        const debut = z.find((i) => /begins/.test(i.t)), fin = z.find((i) => /ends/.test(i.t));
        if (debut) heures.push("Début " + (debut.d.slice(0, 10) !== g.debut ? jourCourt(debut.d.slice(0, 10)) + " " : "") + heure(debut.d));
        if (fin) heures.push("fin " + heure(fin.d));
      }
      const quand = g.debut === g.fin ? jourCourt(g.debut) : jourCourt(g.debut) + " – " + jourCourt(g.fin);
      return "<li><b>" + esc(g.nom) + "</b>" + (g.debut <= aujourdhui ? '<span class="en-cours">● aujourd’hui</span>' : "")
        + ' <span class="quand">· ' + quand + "</span>"
        + (heures.length ? '<span class="heures">' + heures.join(" · ") + "</span>" : "") + "</li>";
    }).join("") || '<li class="discret">Aucune date dans les prochains mois.</li>';
  }

  function puces(donnees, aujourdhui) {
    const t = infos(donnees, aujourdhui);
    const noms = [];
    for (const i of t.items) {
      if (i.c === "roshchodesh") noms.push("Roch ’Hodech " + (MOIS[i.t.replace("Rosh Chodesh ", "")] || [""])[0]);
      else if (i.c === "holiday" && i.s === "shabbat") noms.push(CHABBATOT[i.t] || i.t);
      else if (/^Chanukah: 1 Candle/.test(i.t)) noms.push("’Hanouka : 1re bougie ce soir");
      else if (i.c === "holiday" && !/^Erev /.test(i.t)) {
        const nom = FETES[base(i.t)];
        if (nom) noms.push(nom + (/CH''M/.test(i.t) ? " (’Hol hamoèd)" : /Hoshana Raba/.test(i.t) ? " (Hochaana Rabba)" : ""));
      } else if (i.c === "holiday" && /^Erev /.test(i.t) && FETES[base(i.t)]) noms.push("Veille de " + FETES[base(i.t)]);
    }
    if (t.omer) noms.push(t.omer + (t.omer === "1" ? "ᵉʳ" : "ᵉ") + " jour de l’omer");
    const ul = $(".puces");
    ul.innerHTML = [...new Set(noms)].map((n) => "<li>" + esc(n).replace(/ᵉʳ/, "<sup>er</sup>").replace(/ᵉ/, "<sup>e</sup>") + "</li>").join("");
    ul.hidden = !noms.length;
  }

  // -- Cycle de la page ------------------------------------------------------------------------
  let donnees = null, jourAffiche = "";
  async function actualiser(forcer) {
    const maintenant = new Date();
    const aujourdhui = jourIso(maintenant);
    if (forcer || aujourdhui !== jourAffiche || !donnees) {
      jourAffiche = aujourdhui;
      afficherDate(aujourdhui, donnees && donnees.sig === signature() ? donnees : null, maintenant);
      donnees = await charger(aujourdhui);
      $(".etat-donnees").hidden = !!donnees;
    }
    afficherDate(aujourdhui, donnees, maintenant);
    puces(donnees, aujourdhui);
    prieres(donnees, aujourdhui, maintenant);
    horaires(donnees, aujourdhui, maintenant);
    chabbat(donnees, maintenant);
    fetes(donnees, aujourdhui);
  }
  actualiser(true);

  // -- Rite et édition du siddour : demandés à la première visite, modifiables dans « Prières du jour » --
  const choix = $(".choix-edition");
  const majEdition = () => {
    const r = rite(), m = edition();
    const nom = (Object.keys(RITES).length > 1 ? RITES[r].nom + " · " : "") + EDITIONS[m];
    $(".bouton-edition").textContent = nom + " ▾";
    $(".bouton-edition").setAttribute("aria-label", "Siddour : " + nom + ". Changer");
    page.querySelectorAll("[data-rite]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.rite === r)));
    choix.querySelectorAll("[data-edition]").forEach((b) => {
      b.hidden = !RITES[r].modes.includes(b.dataset.edition);
      b.setAttribute("aria-pressed", String(b.dataset.edition === m));
    });
  };
  const afficherPrieres = () => {
    majEdition();
    const maintenant = new Date();
    prieres(donnees, jourIso(maintenant), maintenant);
  };
  const choisirEdition = (m) => {
    reglages.edition = EDITIONS[m] ? m : "bilingue";
    enregistrer(); afficherPrieres();
  };
  // Les onglets du menu suivent le rite choisi (voir app.js).
  const choisirRite = (r) => {
    if (!RITES[r]) return;
    reglages.rite = r;
    enregistrer(); afficherPrieres();
    document.dispatchEvent(new Event("siddour-rite"));
  };
  page.querySelectorAll(".choix-rite").forEach((el) => el.addEventListener("click", (e) => {
    const b = e.target.closest("[data-rite]");
    if (b) choisirRite(b.dataset.rite);
  }));
  majEdition();
  $(".bouton-edition").addEventListener("click", (e) => {
    choix.hidden = !choix.hidden;
    e.currentTarget.setAttribute("aria-expanded", String(!choix.hidden));
  });
  choix.addEventListener("click", (e) => {
    const b = e.target.closest("[data-edition]");
    if (!b) return;
    choisirEdition(b.dataset.edition);
    choix.hidden = true; $(".bouton-edition").setAttribute("aria-expanded", "false");
  });
  const accueil = $(".premier-choix");
  if (!reglages.edition) {
    // Une seule fois : le choix (ou « Bilingue » si la fenêtre est fermée) est enregistré.
    const fermer = () => { if (accueil.open && accueil.close) accueil.close(); accueil.removeAttribute("open"); accueil.hidden = true; };
    accueil.addEventListener("click", (e) => {
      const b = e.target.closest("[data-edition]");
      if (b) { choisirEdition(b.dataset.edition); fermer(); }
    });
    accueil.addEventListener("cancel", () => { choisirEdition("bilingue"); });
    accueil.hidden = false;
    if (accueil.showModal) accueil.showModal(); else accueil.setAttribute("open", "");
  }

  setInterval(() => actualiser(false), 60 * 1000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) actualiser(false); });
  addEventListener("online", () => { if (!donnees) actualiser(true); });

  // -- Panneau des réglages ----------------------------------------------------------------------
  const panneau = $(".reglages-jour");
  const boutons = page.querySelectorAll("[data-ouvrir-reglages]");
  let brouillon = null;
  const remplir = () => {
    const l = brouillon.lieu || PARIS;
    $(".lieu-choisi").textContent = l.nom + (l.pays ? ", " + l.pays : "");
    panneau.querySelectorAll(".villes button").forEach((b, i) =>
      b.setAttribute("aria-pressed", String(VILLES[i].lat === l.lat && VILLES[i].lon === l.lon)));
    $("#reglage-bougies").value = brouillon.bougies || "";
    $("#reglage-sortie").value = brouillon.sortie || "";
  };
  const ouvrir = (oui) => {
    panneau.hidden = !oui;
    boutons.forEach((b) => b.setAttribute("aria-expanded", String(oui)));
    if (oui) { brouillon = JSON.parse(JSON.stringify(reglages)); remplir(); panneau.scrollIntoView({ block: "nearest" }); }
  };
  boutons.forEach((b) => b.addEventListener("click", () => ouvrir(panneau.hidden)));
  $(".villes").innerHTML = VILLES.map((v) => '<button type="button">' + esc(v.nom) + "</button>").join("");
  $(".villes").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    brouillon.lieu = VILLES[[...b.parentNode.children].indexOf(b)];
    remplir();
  });
  const etat = $(".reglages-jour .etat");
  let resultats = [], minuteur = 0;
  $("#reglage-ville").addEventListener("input", (e) => {
    clearTimeout(minuteur);
    const q = e.target.value.trim();
    if (q.length < 2) { $(".resultats").innerHTML = ""; etat.textContent = ""; return; }
    minuteur = setTimeout(async () => {
      etat.textContent = "Recherche…";
      try {
        const r = await fetch(GEO + "?count=8&language=fr&format=json&name=" + encodeURIComponent(q)).then((x) => x.json());
        resultats = (r.results || []).filter((v) => v.timezone);
        etat.textContent = resultats.length ? "" : "Aucune ville trouvée.";
        $(".resultats").innerHTML = resultats.map((v) => '<li><button type="button">' + esc(v.name)
          + '<small> — ' + esc([v.admin1, v.country].filter(Boolean).join(", ")) + "</small></button></li>").join("");
      } catch (err) { etat.textContent = "Recherche impossible sans connexion."; }
    }, 350);
  });
  $(".resultats").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const v = resultats[[...$(".resultats").children].indexOf(b.parentNode)];
    brouillon.lieu = { nom: v.name, pays: v.country || "", cc: v.country_code || "", lat: v.latitude, lon: v.longitude, tz: v.timezone };
    $(".resultats").innerHTML = ""; $("#reglage-ville").value = ""; remplir();
  });
  // Position de l'appareil. Sur iPhone, l'autorisation du site ne suffit pas : le Service de
  // localisation doit aussi être permis à Safari (sinon refus immédiat, code 1).
  const iOS = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const localiser = (precis) => new Promise((ok, ko) => navigator.geolocation.getCurrentPosition(ok, ko,
    { enableHighAccuracy: precis, timeout: precis ? 30000 : 15000, maximumAge: precis ? 0 : 600e3 }));
  async function nommer(lat, lon) {
    try {
      const arret = new AbortController(); setTimeout(() => arret.abort(), 8000);
      const r = await fetch(GEO_INVERSE + "?localityLanguage=fr&latitude=" + lat + "&longitude=" + lon,
        { signal: arret.signal }).then((x) => x.json());
      let pays = r.countryName || "";
      try { pays = new Intl.DisplayNames(["fr"], { type: "region" }).of(r.countryCode) || pays; } catch (e) {}
      return { nom: r.city || r.locality || "", pays, cc: r.countryCode || "" };
    } catch (e) { return { nom: "", pays: "", cc: "" }; }
  }
  $(".position").addEventListener("click", async () => {
    if (!navigator.geolocation) { etat.textContent = "Position indisponible sur cet appareil."; return; }
    if (!window.isSecureContext) { etat.textContent = "La position demande une adresse sécurisée (https)."; return; }
    etat.textContent = "Localisation…";
    let p = null;
    try { p = await localiser(false); } catch (e) {
      // Code 1 : refus. Codes 2 et 3 (introuvable, délai dépassé) : nouvel essai avec le GPS.
      if (e.code !== 1) { etat.textContent = "Localisation… (précise)"; try { p = await localiser(true); } catch (e2) { e = e2; } }
      if (!p) {
        etat.textContent = e.code === 1
          ? "Position refusée. " + (iOS ? "Sur iPhone : Réglages › Confidentialité et sécurité › Service de localisation"
            + " › Sites Safari (ou Safari) › « Lorsque l’app est active ». Sinon, choisir la ville ci-dessus."
            : "Autoriser la position pour ce site dans le navigateur, ou choisir la ville ci-dessus.")
          : e.code === 3 ? "La position met trop de temps à venir. Réessayer, ou choisir la ville ci-dessus."
          : "Position introuvable pour le moment. Réessayer, ou choisir la ville ci-dessus.";
        return;
      }
    }
    const lat = Math.round(p.coords.latitude * 1e4) / 1e4, lon = Math.round(p.coords.longitude * 1e4) / 1e4;
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    etat.textContent = "Position trouvée, recherche du nom de la ville…";
    const n = await nommer(lat, lon);
    brouillon.lieu = { nom: n.nom || "Ma position", pays: n.pays, cc: n.cc || (tz === "Asia/Jerusalem" ? "IL" : ""), lat, lon, tz };
    remplir();
    etat.textContent = "📍 " + brouillon.lieu.nom + (n.pays ? ", " + n.pays : "") + " : appuyer sur Enregistrer.";
  });
  $("#reglage-bougies").addEventListener("change", (e) => { brouillon.bougies = e.target.value; });
  $("#reglage-sortie").addEventListener("change", (e) => { brouillon.sortie = e.target.value; });
  $(".reglages-jour .ok").addEventListener("click", () => {
    for (const k of ["bougies", "sortie"]) if (!brouillon[k]) delete brouillon[k];
    reglages = brouillon; enregistrer(); ouvrir(false); actualiser(true);
  });
  $(".reglages-jour .annuler").addEventListener("click", () => ouvrir(false));
})();
'''


def corps(cibles: dict[str, dict], couverture: str, sous_titre: str) -> str:
    """Contenu de la page d'accueil ; le script remplit les cartes au chargement.

    cibles : pour chaque rite, {"nom", "prefixe", "modes", "pages"}, où pages associe
    une clé de CIBLES au chemin de la page dans l'édition. Le premier rite est celui par défaut.
    """
    editions = ''.join('<button type="button" data-edition="' + m + '">' + nom + '</button>'
                       for m, nom in (('hebreu', 'Hébreu'), ('phonetique', 'Phonétique'), ('bilingue', 'Bilingue')))
    # Le choix du rite n'apparaît que si le site en a plusieurs.
    rites = ('<div class="segments choix-rite">' + ''.join(
        '<button type="button" data-rite="' + html.escape(code, quote=True) + '">' + html.escape(r['nom']) + '</button>'
        for code, r in cibles.items()) + '</div>') if len(cibles) > 1 else ''
    bougies = ''.join('<option value="' + v + '">' + t + '</option>' for v, t in (
        ('', 'Auto : 18 min (40 à Jérusalem)'), ('15', '15 min'), ('18', '18 min'), ('20', '20 min'),
        ('22', '22 min'), ('30', '30 min'), ('40', '40 min')))
    return (
        '<div class="jour" data-aujourdhui>'
        '<h1 class="date-greg">Aujourd’hui</h1>'
        '<p class="date-heb"></p>'
        '<p class="lieu">📍 <span class="ville">Paris, France</span> · '
        '<button type="button" class="lien" data-ouvrir-reglages aria-expanded="false" aria-controls="reglages-jour">'
        'Changer de ville</button></p>'
        '<ul class="puces" hidden></ul>'
        '<p class="installer-ios" hidden>Sur iPhone ou iPad, pour installer le siddour comme une application : '
        'bouton <b>Partager</b>, puis <b>Sur l’écran d’accueil</b>.</p>'
        '<section class="carte reglages-jour" id="reglages-jour" hidden aria-label="Ville et horaires">'
        '<h2>Ville et horaires</h2>'
        '<span class="etiquette">Ville : <span class="lieu-choisi"></span></span>'
        '<div class="villes"></div>'
        '<label for="reglage-ville">Autre ville</label>'
        '<input type="search" id="reglage-ville" placeholder="Nom de la ville…" autocomplete="off">'
        '<ul class="resultats"></ul>'
        '<p class="etat" role="status"></p>'
        '<div class="actions" style="justify-content:flex-start;margin-top:0">'
        '<button type="button" class="position">📍 Utiliser ma position</button></div>'
        '<label for="reglage-bougies">Allumage des bougies avant le coucher du soleil</label>'
        '<select id="reglage-bougies">' + bougies + '</select>'
        '<label for="reglage-sortie">Sortie de Chabbat et des fêtes</label>'
        '<select id="reglage-sortie"><option value="">Tombée de la nuit (3 étoiles)</option>'
        '<option value="72">Rabbénou Tam (72 min après le coucher du soleil)</option></select>'
        '<div class="actions"><button type="button" class="annuler">Annuler</button>'
        '<button type="button" class="ok">Enregistrer</button></div>'
        '<p class="discret">Les réglages restent sur cet appareil.</p>'
        '</section>'
        '<section class="carte" id="prieres"><h2>Prières du jour <small>'
        '<button type="button" class="lien bouton-edition" aria-expanded="false" aria-controls="choix-edition">'
        'Bilingue ▾</button></small></h2>'
        '<div class="choix-edition" id="choix-edition" hidden>'
        + ('<p>Rite :</p>' + rites if rites else '')
        + '<p>Ouvrir les prières dans l’édition :</p><div class="segments">' + editions + '</div></div>'
        '<ul class="prieres"></ul>'
        '<div class="raccourcis"></div></section>'
        '<p class="etat-donnees discret" hidden>Horaires indisponibles : vérifier la connexion.</p>'
        '<section class="carte" id="horaires"><h2>Horaires du jour</h2><ol class="zmanim"></ol>'
        '<p class="discret">Horaires calculés par <a href="https://www.hebcal.com">Hebcal.com</a>. '
        'Vérifier auprès de sa communauté.</p></section>'
        '<section class="carte" id="chabbat"><h2>Chabbat <small></small></h2><div class="chabbat"></div></section>'
        '<section class="carte" id="fetes"><h2>Prochaines fêtes et jeûnes</h2><ul class="fetes"></ul></section>'
        '<a class="vers-livres" href="livres.html"><img src="' + couverture + '" alt="" width="52" height="78">'
        '<span><b>Le siddour : lire en ligne ou télécharger</b><small>' + html.escape(sous_titre) + '</small></span></a>'
        '<dialog class="premier-choix" aria-labelledby="premier-choix-titre" hidden>'
        '<h2 id="premier-choix-titre">Bienvenue</h2>'
        + ('<p>Quel rite suivez-vous ?</p>' + rites if rites else '')
        + '<p>Comment lire les prières ?</p><div class="options">'
        '<button type="button" data-edition="hebreu"><b>Hébreu</b><span class="ex" lang="he" dir="rtl">בָּרוּךְ אַתָּה</span></button>'
        '<button type="button" data-edition="phonetique"><b>Phonétique</b><span class="ex">Baroukh ata</span></button>'
        '<button type="button" data-edition="bilingue"><b>Bilingue</b><span class="ex">hébreu puis phonétique</span></button>'
        '</div><p class="discret">Modifiable ensuite à côté de « Prières du jour ».</p></dialog>'
        '<noscript><p>Activer JavaScript pour afficher la date hébraïque et les horaires du jour.</p></noscript>'
        '</div>'
        '<script type="application/json" id="cibles">' + json.dumps(cibles, ensure_ascii=False) + '</script>'
    )
