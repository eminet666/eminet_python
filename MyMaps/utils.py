"""
utils.py
--------
Utilitaires partagés entre geocode.py, csv_to_html.py et export_gpx.py.

  SEPARATEUR      — séparateur de colonnes du CSV (";")
  DEFAUT          — style par défaut pour les catégories inconnues
  FICHIER_CONFIG  — nom du fichier de configuration des catégories
  detecter_encodage(chemin) → str
  charger_categories()      → dict
  lire_csv(chemin)          → (lieux, titre)
"""

import os
import csv
import json

# ─────────────────────────────────────────────────────────────
# Constantes communes
# ─────────────────────────────────────────────────────────────
SEPARATEUR     = ";"
DEFAUT         = {"couleur": "#95A5A6"}
FICHIER_CONFIG = "categories.json"

# ─────────────────────────────────────────────────────────────
# Catégories intégrées (utilisées si categories.json est absent)
# Pour ajouter une catégorie : édite categories.json directement.
# ─────────────────────────────────────────────────────────────
CATEGORIES_DEFAUT = {
    "Musée":         {"couleur": "#E84545"},
    "Monument":      {"couleur": "#FF6B35"},
    "Eglise":        {"couleur": "#A855F7"},
    "Resto":         {"couleur": "#F59E0B"},
    "Bar":           {"couleur": "#EF4444"},
    "Hôtel":         {"couleur": "#3B82F6"},
    "Points de vue": {"couleur": "#10B981"},
    "A faire":       {"couleur": "#F97316"},
    "Adresse":       {"couleur": "#6B7280"},
    "Plage":         {"couleur": "#06B6D4"},
    "Randonnées":    {"couleur": "#16A34A"},
    "Shopping":      {"couleur": "#DB2777"},
    "Antique":       {"couleur": "#92400E"},
    "Renaissance":   {"couleur": "#B45309"},
    "Moyen-Age":     {"couleur": "#065F46"},
    "Contemporain":  {"couleur": "#1E3A5F"},
    "Village":       {"couleur": "#7C3AED"},
    "Quartier":      {"couleur": "#0E7490"},
    "Train":         {"couleur": "#6D28D9"},
    "Jardin":        {"couleur": "#4ADE80"},
    "Place":         {"couleur": "#D97706"},
    "Néoclassique":  {"couleur": "#60A5FA"},
    "Cinéma":        {"couleur": "#EC4899"},
    "Byzantin":      {"couleur": "#9333EA"},
    "Visite":        {"couleur": "#14B8A6"},
}


# ─────────────────────────────────────────────────────────────
# Détection d'encodage
# ─────────────────────────────────────────────────────────────
def detecter_encodage(chemin):
    """Retourne l'encodage du fichier parmi utf-8-sig, utf-8, latin-1, cp1252."""
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            with open(chemin, encoding=enc) as f:
                f.read()
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


# ─────────────────────────────────────────────────────────────
# Chargement des catégories
# ─────────────────────────────────────────────────────────────
def charger_categories():
    """Charge categories.json si présent, sinon retourne les valeurs intégrées."""
    if os.path.exists(FICHIER_CONFIG):
        try:
            with open(FICHIER_CONFIG, encoding="utf-8") as f:
                cats = json.load(f)
            print(f"📋 Catégories chargées depuis {FICHIER_CONFIG} ({len(cats)} entrées)")
            return cats
        except Exception as e:
            print(f"⚠️  Erreur lecture {FICHIER_CONFIG} : {e} — utilisation des valeurs par défaut")
    return CATEGORIES_DEFAUT


# ─────────────────────────────────────────────────────────────
# Lecture CSV
# ─────────────────────────────────────────────────────────────
def lire_csv(chemin):
    """
    Lit un fichier CSV au format du projet et retourne (lieux, titre).

    lieux  — liste de dicts avec les clés :
              index, categorie, nom, adresse, note, description,
              transport, url, photo, lon (float), lat (float)
    titre  — chaîne "Région, Pays" issue de l'en-tête, ou "" si absente
    """
    enc = detecter_encodage(chemin)
    lieux = []
    titre = ""

    with open(chemin, newline="", encoding=enc) as f:
        lignes = list(csv.reader(f, delimiter=SEPARATEUR))

    debut = 0
    if lignes and lignes[0] and lignes[0][0].strip().lower() in ("pays", "country"):
        if len(lignes) > 1:
            vals  = lignes[1]
            pays   = vals[0].strip() if len(vals) > 0 else ""
            region = vals[1].strip() if len(vals) > 1 else ""
            titre  = f"{region}{', ' if region and pays else ''}{pays}"
        debut = 2
        while debut < len(lignes) and not any(c.strip() for c in lignes[debut]):
            debut += 1

    if debut >= len(lignes):
        return lieux, titre

    entete = [c.strip().lower() for c in lignes[debut]]
    debut += 1

    index_csv = 0
    for row in lignes[debut:]:
        if not any(c.strip() for c in row):
            continue
        index_csv += 1
        d = {col: (row[i].strip() if i < len(row) else "") for i, col in enumerate(entete)}
        try:
            lon = float(d.get("lon", ""))
            lat = float(d.get("lat", ""))
        except ValueError:
            nom = d.get("nom", "?")
            print(f"  ⚠️  Ignoré (pas de coordonnées) : {nom} — lance d'abord geocode.py")
            continue
        lieux.append({
            "index":       index_csv,
            "categorie":   d.get("categorie", "Autre"),
            "nom":         d.get("nom", "Sans nom"),
            "adresse":     d.get("adresse", ""),
            "note":        d.get("note", ""),
            "description": d.get("description", ""),
            "transport":   d.get("transport", ""),
            "url":         d.get("url", ""),
            "photo":       d.get("photo", ""),
            "lon":         lon,
            "lat":         lat,
        })

    return lieux, titre
