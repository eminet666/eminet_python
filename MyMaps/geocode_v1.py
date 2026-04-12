"""
geocode.py
----------
Complète automatiquement les coordonnées GPS et les URLs Wikipedia
d'un fichier CSV via Nominatim et l'API Wikipedia — 100% gratuit, sans clé API.

Priorité de géocodage pour chaque ligne :
  1. lon + lat déjà remplis        → ignoré (coordonnées conservées)
  2. url Wikipedia déjà renseignée → extraction des coords depuis Wikipedia
  3. recherche Wikipedia           → si page trouvée, extraction des coords
  4. sinon                         → géocodage Nominatim (par adresse ou par nom)

Recherche Wikipedia (optionnelle) :
  - Si la colonne "url" est vide, cherche une page Wikipedia (FR puis EN)
  - Si une URL est déjà présente, elle est conservée et utilisée pour les coords
  - Désactivable avec --no-wiki (repasse en Nominatim pur)

Format CSV (séparateur ";") :
    Ligne 1 : pays;région
    Ligne 2 : France;Ile de France
    Ligne 3 : (vide)
    Ligne 4 : categorie;nom;adresse;note;description;transport;url;lon;lat

Usage :
    python geocode.py                         → traite lieux.csv
    python geocode.py paris.csv               → traite le fichier indiqué
    python geocode.py a.csv b.csv             → traite plusieurs fichiers
    python geocode.py paris.csv --force       → re-géocode même les lieux déjà remplis
    python geocode.py paris.csv --no-wiki     → Nominatim uniquement, sans Wikipedia
    python geocode.py paris.csv --wiki-en     → cherche Wikipedia en anglais en priorité
"""

import csv
import sys
import time
import os
import re
import urllib.request
import urllib.parse
import json

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
NOMINATIM_URL  = "https://nominatim.openstreetmap.org/search"
WIKIPEDIA_API  = "https://{lang}.wikipedia.org/w/api.php"
USER_AGENT     = "VoyageKML/1.0 (usage personnel)"
DELAI_SECONDES = 1.1
SEPARATEUR     = ";"

# Catégories pour lesquelles on ne cherche pas Wikipedia
CATEGORIES_SANS_WIKI = {"adresse"}


# ─────────────────────────────────────────────────────────────
# Conversion DMS → décimal
# ─────────────────────────────────────────────────────────────

def dms_en_decimal(valeur):
    """
    Convertit une coordonnée GPS en degrés-minutes-secondes (DMS) en décimal.
    Accepte les formats :
      40°16'06.6"N    →  40.268500
      23°26'50.3"E    →  23.447306
      40°16'06.6"S    → -40.268500
      40 16 06.6 N    (variante avec espaces)
      40:16:06.6N     (variante avec deux-points)
    Retourne le float décimal, ou None si non reconnu.
    """
    if not valeur:
        return None

    # Déjà un décimal ?
    try:
        return float(valeur.replace(",", "."))
    except ValueError:
        pass

    # Décimal avec ° et/ou lettre cardinale : "22.9475° E", "40.6361°N", "22,9475 E"
    m0 = re.match(r"^\s*(\d+(?:[.,]\d+)?)\s*°?\s*([NSEWnsew])\s*$", valeur.strip())
    if m0:
        d, hemi = m0.groups()
        decimal = float(d.replace(",", "."))
        if hemi.upper() in ("S", "W"):
            decimal = -decimal
        return round(decimal, 6)

    # Regex DMS souple : degrés, minutes, secondes, hémisphère
    pattern = r"""
        ^\s*
        (\d+(?:[.,]\d+)?)           # degrés (entier ou décimal)
        [°:\s]+                      # séparateur
        (\d+(?:[.,]\d+)?)           # minutes
        [':\s]+                      # séparateur (apostrophe, deux-points ou espace)
        (\d+(?:[.,]\d+)?)           # secondes
        [":\s]*                      # séparateur optionnel
        ([NSEWnsew])                 # hémisphère
        \s*$
    """
    m = re.match(pattern, valeur.strip(), re.VERBOSE)
    if not m:
        # Essai sans secondes : 40°16'N
        pattern2 = r"^\s*(\d+(?:[.,]\d+)?)[°:\s]+(\d+(?:[.,]\d+)?)['\s]*([NSEWnsew])\s*$"
        m2 = re.match(pattern2, valeur.strip())
        if m2:
            d, mn, hemi = m2.groups()
            decimal = float(d.replace(",", ".")) + float(mn.replace(",", ".")) / 60
            if hemi.upper() in ("S", "W"):
                decimal = -decimal
            return round(decimal, 6)
        return None

    d, mn, sec, hemi = m.groups()
    decimal = (
        float(d.replace(",", "."))
        + float(mn.replace(",", ".")) / 60
        + float(sec.replace(",", ".")) / 3600
    )
    if hemi.upper() in ("S", "W"):
        decimal = -decimal
    return round(decimal, 6)


def normaliser_coords(lon_brut, lat_brut):
    """
    Normalise lon et lat depuis n'importe quel format.

    Cas gérés :
      - Décimal standard          : "2.2945"  / "48.8584"
      - Décimal virgule           : "2,2945"  / "48,8584"
      - DMS dans les deux champs  : "48°51'N" / "2°17'E"
      - DMS lat dans lon, lon dans lat (ordre Google Maps) :
          lon="40°16'06.6\"N"  lat="23°26'50.3\"E"
          → on détecte N/S vs E/W pour réaffecter correctement
      - Un seul champ DMS rempli  : ignoré (retourne "", "")

    Retourne (lon_str, lat_str) normalisés ou ("", "") si échec.
    """
    def contient_ns(s): return bool(re.search(r'[NSns]', s))
    def contient_ew(s): return bool(re.search(r'[EWew]', s))

    lon_a_ns = contient_ns(lon_brut)
    lon_a_ew = contient_ew(lon_brut)
    lat_a_ns = contient_ns(lat_brut)
    lat_a_ew = contient_ew(lat_brut)

    # Les deux champs sont en DMS avec hémisphère explicite
    if (lon_a_ns or lon_a_ew) and (lat_a_ns or lat_a_ew):
        # Identifier lequel est lat (N/S) et lequel est lon (E/W)
        if lon_a_ns and lat_a_ew:
            # Ordre inversé : lon contient la lat, lat contient la lon
            lat_val = dms_en_decimal(lon_brut)
            lon_val = dms_en_decimal(lat_brut)
        elif lon_a_ew and lat_a_ns:
            # Ordre correct
            lon_val = dms_en_decimal(lon_brut)
            lat_val = dms_en_decimal(lat_brut)
        else:
            return "", ""

    # Un seul champ est en DMS, l'autre est décimal ou vide
    elif lon_a_ns or lon_a_ew:
        val = dms_en_decimal(lon_brut)
        if val is None:
            return "", ""
        lat_try = dms_en_decimal(lat_brut)
        if lon_a_ns:
            lat_val, lon_val = val, lat_try
        else:
            lon_val, lat_val = val, lat_try

    elif lat_a_ns or lat_a_ew:
        val = dms_en_decimal(lat_brut)
        if val is None:
            return "", ""
        lon_try = dms_en_decimal(lon_brut)
        if lat_a_ns:
            lat_val, lon_val = val, lon_try
        else:
            lon_val, lat_val = val, lon_try

    # Aucun hémisphère : conversion décimale simple
    else:
        lon_val = dms_en_decimal(lon_brut)
        lat_val = dms_en_decimal(lat_brut)

    if lon_val is not None and lat_val is not None:
        return f"{lon_val:.6f}", f"{lat_val:.6f}"
    return "", ""



def _requete_nominatim(query):
    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": 1, "addressdetails": 0})
    req = urllib.request.Request(f"{NOMINATIM_URL}?{params}", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data:
                return float(data[0]["lon"]), float(data[0]["lat"])
    except Exception as e:
        print(f"\n    ⚠️  Erreur Nominatim : {e}", end="")
    return None


def geocoder_par_nom(nom, pays="", region=""):
    parties = [p for p in [nom, region, pays] if p]
    return _requete_nominatim(", ".join(parties))


def geocoder_par_adresse(adresse, pays="", region=""):
    resultat = _requete_nominatim(adresse)
    if resultat:
        return resultat
    if pays and pays.lower() not in adresse.lower():
        time.sleep(DELAI_SECONDES)
        resultat = _requete_nominatim(f"{adresse}, {pays}")
    return resultat


# ─────────────────────────────────────────────────────────────
# Wikipedia — recherche + extraction de coordonnées
# ─────────────────────────────────────────────────────────────

def _extraire_pageid_depuis_url(url):
    """
    Extrait le pageid ou le titre depuis une URL Wikipedia.
    Supporte :
      https://fr.wikipedia.org/?curid=12345
      https://fr.wikipedia.org/wiki/Tour_Eiffel
      https://en.wikipedia.org/wiki/Colosseum
    """
    # Format curid
    m = re.search(r'curid=(\d+)', url)
    if m:
        return ("id", m.group(1), _extraire_lang_depuis_url(url))

    # Format /wiki/Titre
    m = re.search(r'wikipedia\.org/wiki/(.+)', url)
    if m:
        titre = urllib.parse.unquote(m.group(1))
        return ("titre", titre, _extraire_lang_depuis_url(url))

    return None


def _extraire_lang_depuis_url(url):
    """Extrait le code langue depuis une URL Wikipedia (fr, en, it...)"""
    m = re.match(r'https?://([a-z]{2})\.wikipedia\.org', url)
    return m.group(1) if m else "fr"


def coords_depuis_wikipedia_url(url):
    """
    Extrait les coordonnées GPS depuis une URL Wikipedia existante.
    Utilise l'API prop=coordinates de MediaWiki.
    Retourne (lon, lat) ou None.
    """
    info = _extraire_pageid_depuis_url(url)
    if not info:
        return None

    mode, valeur, lang = info
    api_url = WIKIPEDIA_API.format(lang=lang)

    if mode == "id":
        params = urllib.parse.urlencode({
            "action":    "query",
            "prop":      "coordinates",
            "pageids":   valeur,
            "format":    "json",
        })
    else:
        params = urllib.parse.urlencode({
            "action":    "query",
            "prop":      "coordinates",
            "titles":    valeur,
            "format":    "json",
        })

    req = urllib.request.Request(f"{api_url}?{params}", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                coords = page.get("coordinates", [])
                if coords:
                    return float(coords[0]["lon"]), float(coords[0]["lat"])
    except Exception as e:
        print(f"\n    ⚠️  Erreur Wikipedia coords : {e}", end="")
    return None


def _requete_wikipedia_recherche(nom, pays, lang):
    """Cherche une page Wikipedia et retourne son URL ou None."""
    query = f"{nom} {pays}".strip()
    params = urllib.parse.urlencode({
        "action":   "query",
        "list":     "search",
        "srsearch": query,
        "format":   "json",
        "srlimit":  1,
        "srinfo":   "",
        "srprop":   "size",
    })
    url = WIKIPEDIA_API.format(lang=lang) + "?" + params
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("query", {}).get("search", [])
            if results:
                pageid = results[0]["pageid"]
                return f"https://{lang}.wikipedia.org/?curid={pageid}"
    except Exception as e:
        print(f"\n    ⚠️  Erreur Wikipedia recherche : {e}", end="")
    return None


def chercher_wikipedia(nom, pays="", lang_prioritaire="fr"):
    """
    Cherche une page Wikipedia (FR puis EN en fallback).
    Retourne (url, lang) ou (None, None).
    """
    lang_secondaire = "en" if lang_prioritaire == "fr" else "fr"

    url = _requete_wikipedia_recherche(nom, pays, lang_prioritaire)
    time.sleep(DELAI_SECONDES)
    if url:
        return url, lang_prioritaire

    url = _requete_wikipedia_recherche(nom, pays, lang_secondaire)
    time.sleep(DELAI_SECONDES)
    if url:
        return url, lang_secondaire

    return None, None


# ─────────────────────────────────────────────────────────────
# Lecture / écriture CSV
# ─────────────────────────────────────────────────────────────

def _detecter_encodage(chemin):
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            with open(chemin, encoding=enc) as f:
                f.read()
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def lire_fichier(chemin):
    contexte = {"pays": "", "region": ""}
    enc = _detecter_encodage(chemin)

    # Lecture brute ligne par ligne — on split sur ; sans interpréter les guillemets
    # car les coordonnées DMS contiennent des " (secondes d'arc)
    with open(chemin, encoding=enc) as f:
        lignes_brutes = f.read().splitlines()

    def split_ligne(ligne):
        return [c.strip() for c in ligne.split(SEPARATEUR)]

    lignes = [split_ligne(l) for l in lignes_brutes]

    debut = 0
    if lignes and lignes[0] and lignes[0][0].strip().lower() in ("pays", "country"):
        if len(lignes) > 1:
            vals = lignes[1]
            contexte["pays"]   = vals[0].strip() if len(vals) > 0 else ""
            contexte["region"] = vals[1].strip() if len(vals) > 1 else ""
        debut = 2
        while debut < len(lignes) and not any(c.strip() for c in lignes[debut]):
            debut += 1

    if debut >= len(lignes):
        return contexte, []

    entete = [c.strip().lower() for c in lignes[debut]]
    debut += 1

    lieux = []
    for row in lignes[debut:]:
        if not any(c.strip() for c in row):
            continue
        d = {col: (row[i].strip() if i < len(row) else "") for i, col in enumerate(entete)}
        lieux.append(d)

    return contexte, lieux


def ecrire_fichier(chemin, contexte, lieux):
    # Écriture brute sans module csv pour éviter l'échappement des guillemets DMS
    def join_ligne(valeurs):
        return SEPARATEUR.join(str(v) for v in valeurs)

    lignes = []
    if contexte["pays"] or contexte["region"]:
        lignes.append(join_ligne(["pays", "région", "", "", "", "", "", "", ""]))
        lignes.append(join_ligne([contexte["pays"], contexte["region"], "", "", "", "", "", "", ""]))
        lignes.append(join_ligne(["", "", "", "", "", "", "", "", ""]))

    lignes.append(join_ligne(["categorie", "nom", "adresse", "note", "description", "transport", "url", "lon", "lat"]))

    for lieu in lieux:
        lignes.append(join_ligne([
            lieu.get("categorie", ""),
            lieu.get("nom", ""),
            lieu.get("adresse", ""),
            lieu.get("note", ""),
            lieu.get("description", ""),
            lieu.get("transport", ""),
            lieu.get("url", ""),
            lieu.get("lon", ""),
            lieu.get("lat", ""),
        ]))

    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lignes) + "\n")


# ─────────────────────────────────────────────────────────────
# Traitement principal
# ─────────────────────────────────────────────────────────────

def traiter_fichier(chemin, force=False, avec_wiki=True, lang_wiki="fr"):
    print(f"\n📂 Traitement de : {chemin}")
    contexte, lieux = lire_fichier(chemin)

    pays   = contexte["pays"]
    region = contexte["region"]
    if pays or region:
        ctx = f"{region}{', ' if region and pays else ''}{pays}"
        print(f"   📍 Contexte : {ctx}")
    if avec_wiki:
        print(f"   🌐 Wikipedia : activé (langue prioritaire : {lang_wiki})")
    print()

    geo_trouves   = 0
    geo_nominatim = 0
    geo_wiki      = 0
    geo_ignores   = 0
    geo_echecs    = []
    wiki_trouves  = 0
    wiki_ignores  = 0
    wiki_echecs   = []

    for lieu in lieux:
        nom       = lieu.get("nom", "").strip()
        adresse   = lieu.get("adresse", "").strip()
        categorie = lieu.get("categorie", "").strip()
        lon       = lieu.get("lon", "").strip()
        lat       = lieu.get("lat", "").strip()
        url       = lieu.get("url", "").strip()

        if not nom and not adresse:
            continue

        # ── Conversion DMS → décimal si nécessaire ───────────────
        if lon or lat:
            lon_conv, lat_conv = normaliser_coords(lon, lat)
            if lon_conv and lat_conv and (lon_conv != lon or lat_conv != lat):
                print(f"   🔄 {nom} — DMS converti : {lon} / {lat} → {lon_conv} / {lat_conv}")
                lieu["lon"] = lon_conv
                lieu["lat"] = lat_conv
                lon, lat = lon_conv, lat_conv

        # ── Cas 1 : coordonnées déjà présentes ───────────────────
        if lon and lat and not force:
            print(f"   ⏭️  {nom} — coords déjà remplis")
            geo_ignores += 1
            # Chercher Wikipedia quand même si url vide
            if avec_wiki and not url and categorie.lower() not in CATEGORIES_SANS_WIKI:
                print(f"   🌐 {nom}...", end=" ", flush=True)
                wiki_url, lang_trouve = chercher_wikipedia(nom, pays=pays, lang_prioritaire=lang_wiki)
                if wiki_url:
                    lieu["url"] = wiki_url
                    print(f"✅  Wikipedia {lang_trouve.upper()}")
                    wiki_trouves += 1
                else:
                    print("— pas de page Wikipedia")
                    wiki_echecs.append(nom)
            elif url:
                wiki_ignores += 1
            continue

        coordonnees = None
        source      = None

        # ── Cas 2 : URL Wikipedia déjà renseignée → coords si vides ─
        if url and "wikipedia.org" in url and avec_wiki and not lon and not lat:
            print(f"   📖 {nom} — coords depuis Wikipedia...", end=" ", flush=True)
            coordonnees = coords_depuis_wikipedia_url(url)
            time.sleep(DELAI_SECONDES)
            if coordonnees:
                source = "Wikipedia (URL existante)"
                wiki_ignores += 1  # URL déjà présente, pas de nouvelle recherche

        # ── Cas 3 : recherche Wikipedia → coords ─────────────────
        if coordonnees is None and avec_wiki and categorie.lower() not in CATEGORIES_SANS_WIKI:
            print(f"   🌐 {nom}...", end=" ", flush=True)
            wiki_url, lang_trouve = chercher_wikipedia(nom, pays=pays, lang_prioritaire=lang_wiki)

            if wiki_url:
                lieu["url"] = wiki_url
                wiki_trouves += 1
                print(f"✅  Wikipedia {lang_trouve.upper()} — extraction coords...", end=" ", flush=True)
                coordonnees = coords_depuis_wikipedia_url(wiki_url)
                time.sleep(DELAI_SECONDES)
                if coordonnees:
                    source = f"Wikipedia {lang_trouve.upper()}"
                else:
                    print(f"pas de coords Wiki...", end=" ", flush=True)
            else:
                print("— pas de page Wikipedia", end="")
                wiki_echecs.append(nom)
                print()

        # ── Cas 4 : fallback Nominatim ────────────────────────────
        if coordonnees is None:
            if source is None:  # Pas encore affiché de ligne
                if adresse:
                    print(f"   📮 {nom} ({adresse})...", end=" ", flush=True)
                else:
                    print(f"   🔍 {nom}...", end=" ", flush=True)

            if adresse:
                coordonnees = geocoder_par_adresse(adresse, pays=pays, region=region)
            else:
                coordonnees = geocoder_par_nom(nom, pays=pays, region=region)
            time.sleep(DELAI_SECONDES)

            if coordonnees:
                source = "Nominatim"
                geo_nominatim += 1

        # ── Enregistrement ────────────────────────────────────────
        if coordonnees:
            lieu["lon"] = f"{coordonnees[0]:.6f}"
            lieu["lat"] = f"{coordonnees[1]:.6f}"
            print(f"✅  ({lieu['lat']}, {lieu['lon']})  [{source}]")
            geo_trouves += 1
            if "Wikipedia" in source:
                geo_wiki += 1
        else:
            print("❌ Non trouvé")
            geo_echecs.append((categorie, nom, adresse))

    ecrire_fichier(chemin, contexte, lieux)

    # ── Résumé ───────────────────────────────────────────────────
    print(f"\n📊 Résumé :")
    print(f"   📍 Géocodés        : {geo_trouves}")
    if geo_wiki:
        print(f"      └ via Wikipedia : {geo_wiki}")
    if geo_nominatim:
        print(f"      └ via Nominatim : {geo_nominatim}")
    print(f"   ⏭️  Déjà remplis   : {geo_ignores}")
    if avec_wiki:
        print(f"   🌐 URLs Wikipedia  : {wiki_trouves} trouvées, {wiki_ignores} déjà présentes", end="")
        print(f", {len(wiki_echecs)} sans page" if wiki_echecs else "")
    if geo_echecs:
        print(f"\n   ❌ Lieux non géocodés :")
        for cat, n, adr in geo_echecs:
            print(f"      • [{cat}] {n}{' — ' + adr if adr else ''}")
        print(f"\n   💡 Conseils :")
        print(f"      - Vérifie l'orthographe")
        print(f"      - Renseigne l'adresse dans la colonne adresse")
        print(f"      - Saisis les coordonnées manuellement (clic droit Google Maps)")
    if wiki_echecs:
        print(f"\n   ℹ️  Sans page Wikipedia : {', '.join(wiki_echecs[:5])}", end="")
        print(f"... (+{len(wiki_echecs)-5})" if len(wiki_echecs) > 5 else "")
    print(f"\n   💾 Fichier mis à jour : {chemin}")


def main():
    args      = sys.argv[1:]
    force     = "--force"   in args
    sans_wiki = "--no-wiki" in args
    lang_en   = "--wiki-en" in args
    fichiers  = [a for a in args if not a.startswith("--")]
    lang_wiki = "en" if lang_en else "fr"

    if not fichiers:
        fichiers = ["lieux.csv"]

    for chemin in fichiers:
        if not os.path.exists(chemin):
            print(f"❌ Fichier introuvable : {chemin}")
            continue
        traiter_fichier(chemin, force=force, avec_wiki=not sans_wiki, lang_wiki=lang_wiki)

    print("\n✨ Terminé ! Lance maintenant : python csv_to_html.py")


if __name__ == "__main__":
    main()
