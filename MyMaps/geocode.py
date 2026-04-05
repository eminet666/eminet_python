"""
geocode.py
----------
Complète automatiquement les coordonnées GPS et les URLs Wikipedia
d'un fichier CSV via Nominatim et l'API Wikipedia — 100% gratuit, sans clé API.

Priorité de géocodage pour chaque ligne :
  1. lon + lat déjà remplis  →  ignoré (coordonnées conservées)
  2. colonne "adresse" remplie  →  géocodage par adresse
  3. sinon  →  géocodage par nom du lieu + contexte pays/région

Recherche Wikipedia (optionnelle) :
  - Si la colonne "url" est vide, cherche une page Wikipedia (FR puis EN)
  - Si une URL est déjà présente, elle est conservée
  - Désactivable avec --no-wiki

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
    python geocode.py paris.csv --no-wiki     → désactive la recherche Wikipedia
    python geocode.py paris.csv --wiki-en     → cherche en anglais en priorité
"""

import csv
import sys
import time
import os
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
# (adresses personnelles, restaurants peu connus...)
CATEGORIES_SANS_WIKI = {"adresse"}


# ─────────────────────────────────────────────────────────────
# Géocodage Nominatim
# ─────────────────────────────────────────────────────────────

def _requete_nominatim(query):
    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": 1, "addressdetails": 0})
    req = urllib.request.Request(f"{NOMINATIM_URL}?{params}", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data:
                return float(data[0]["lon"]), float(data[0]["lat"])
    except Exception as e:
        print(f"\n    ⚠️  Erreur réseau : {e}", end="")
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
# Recherche Wikipedia
# ─────────────────────────────────────────────────────────────

def _requete_wikipedia(nom, pays, lang):
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
        print(f"\n    ⚠️  Erreur Wikipedia : {e}", end="")
    return None


def chercher_wikipedia(nom, pays="", lang_prioritaire="fr"):
    """
    Cherche d'abord dans la langue prioritaire, puis dans l'autre.
    Retourne l'URL Wikipedia ou None.
    """
    lang_secondaire = "en" if lang_prioritaire == "fr" else "fr"

    url = _requete_wikipedia(nom, pays, lang_prioritaire)
    time.sleep(DELAI_SECONDES)
    if url:
        return url, lang_prioritaire

    url = _requete_wikipedia(nom, pays, lang_secondaire)
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

    with open(chemin, newline="", encoding=enc) as f:
        lignes = list(csv.reader(f, delimiter=SEPARATEUR))

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
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=SEPARATEUR)

        if contexte["pays"] or contexte["region"]:
            writer.writerow(["pays", "région", "", "", "", "", "", ""])
            writer.writerow([contexte["pays"], contexte["region"], "", "", "", "", "", ""])
            writer.writerow(["", "", "", "", "", "", "", ""])

        writer.writerow(["categorie", "nom", "adresse", "note", "description", "transport", "url", "lon", "lat"])

        for lieu in lieux:
            writer.writerow([
                lieu.get("categorie", ""),
                lieu.get("nom", ""),
                lieu.get("adresse", ""),
                lieu.get("note", ""),
                lieu.get("description", ""),
                lieu.get("transport", ""),
                lieu.get("url", ""),
                lieu.get("lon", ""),
                lieu.get("lat", ""),
            ])


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

    geo_trouves  = 0
    geo_ignores  = 0
    geo_echecs   = []
    wiki_trouves = 0
    wiki_ignores = 0
    wiki_echecs  = []

    for lieu in lieux:
        nom       = lieu.get("nom", "").strip()
        adresse   = lieu.get("adresse", "").strip()
        categorie = lieu.get("categorie", "").strip()
        lon       = lieu.get("lon", "").strip()
        lat       = lieu.get("lat", "").strip()
        url       = lieu.get("url", "").strip()

        if not nom and not adresse:
            continue

        # ── Géocodage ────────────────────────────────────────────
        if lon and lat and not force:
            print(f"   ⏭️  {nom} — coordonnées déjà présentes")
            geo_ignores += 1
        else:
            if adresse:
                print(f"   📮 {nom} ({adresse})...", end=" ", flush=True)
                resultat = geocoder_par_adresse(adresse, pays=pays, region=region)
            else:
                print(f"   🔍 {nom}...", end=" ", flush=True)
                resultat = geocoder_par_nom(nom, pays=pays, region=region)

            time.sleep(DELAI_SECONDES)

            if resultat:
                lieu["lon"] = f"{resultat[0]:.6f}"
                lieu["lat"] = f"{resultat[1]:.6f}"
                print(f"✅  ({lieu['lat']}, {lieu['lon']})")
                geo_trouves += 1
            else:
                print("❌ Non trouvé")
                geo_echecs.append((categorie, nom, adresse))

        # ── Recherche Wikipedia ───────────────────────────────────
        if not avec_wiki:
            continue
        if categorie.lower() in CATEGORIES_SANS_WIKI:
            continue
        if url and not force:
            print(f"   🌐 {nom} — URL déjà présente")
            wiki_ignores += 1
            continue

        print(f"   🌐 {nom}...", end=" ", flush=True)
        wiki_url, lang_trouve = chercher_wikipedia(nom, pays=pays, lang_prioritaire=lang_wiki)

        if wiki_url:
            lieu["url"] = wiki_url
            print(f"✅  Wikipedia {lang_trouve.upper()}")
            wiki_trouves += 1
        else:
            print("— pas de page Wikipedia")
            wiki_echecs.append(nom)

    ecrire_fichier(chemin, contexte, lieux)

    # ── Résumé ───────────────────────────────────────────────────
    print(f"\n📊 Résumé :")
    print(f"   📍 Géocodage   : {geo_trouves} trouvés, {geo_ignores} déjà remplis", end="")
    print(f", {len(geo_echecs)} échecs" if geo_echecs else "")
    if avec_wiki:
        print(f"   🌐 Wikipedia   : {wiki_trouves} trouvés, {wiki_ignores} déjà remplis", end="")
        print(f", {len(wiki_echecs)} sans page" if wiki_echecs else "")
    if geo_echecs:
        print(f"\n   ❌ Lieux non géocodés :")
        for cat, n, adr in geo_echecs:
            print(f"      • [{cat}] {n}{' — ' + adr if adr else ''}")
    if wiki_echecs:
        print(f"\n   ℹ️  Lieux sans page Wikipedia :")
        for n in wiki_echecs:
            print(f"      • {n}")
    print(f"\n   💾 Fichier mis à jour : {chemin}")


def main():
    args        = sys.argv[1:]
    force       = "--force"   in args
    sans_wiki   = "--no-wiki" in args
    lang_en     = "--wiki-en" in args
    fichiers    = [a for a in args if not a.startswith("--")]
    lang_wiki   = "en" if lang_en else "fr"

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
