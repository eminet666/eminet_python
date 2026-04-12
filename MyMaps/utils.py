"""
utils.py
--------
Utilitaires partagés entre geocode.py et csv_to_html.py.

  SEPARATEUR      — séparateur de colonnes du CSV (";")
  DEFAUT          — style par défaut pour les catégories inconnues
  FICHIER_CONFIG  — nom du fichier de configuration des catégories
  detecter_encodage(chemin) → str
  charger_categories()      → dict
"""

import os
import json

# ─────────────────────────────────────────────────────────────
# Constantes communes
# ─────────────────────────────────────────────────────────────
SEPARATEUR     = ";"
DEFAUT         = {"couleur": "#95A5A6", "icone": "📍"}
FICHIER_CONFIG = "categories.json"

# ─────────────────────────────────────────────────────────────
# Catégories intégrées (utilisées si categories.json est absent)
# Pour ajouter une catégorie : édite categories.json directement.
# ─────────────────────────────────────────────────────────────
CATEGORIES_DEFAUT = {
    "Musée":         {"couleur": "#E8462A", "icone": "🏛"},
    "Musées":        {"couleur": "#E8462A", "icone": "🏛"},
    "Monument":      {"couleur": "#C0392B", "icone": "🗿"},
    "Monuments":     {"couleur": "#C0392B", "icone": "🗿"},
    "Eglise":        {"couleur": "#8E44AD", "icone": "⛪"},
    "Eglises":       {"couleur": "#8E44AD", "icone": "⛪"},
    "Restaurants":   {"couleur": "#E67E22", "icone": "🍽"},
    "Restaurant":    {"couleur": "#E67E22", "icone": "🍽"},
    "Hôtels":        {"couleur": "#2980B9", "icone": "🏨"},
    "Hôtel":         {"couleur": "#2980B9", "icone": "🏨"},
    "Hotel":         {"couleur": "#2980B9", "icone": "🏨"},
    "Points de vue": {"couleur": "#27AE60", "icone": "👁"},
    "A faire":       {"couleur": "#F39C12", "icone": "📌"},
    "Adresse":       {"couleur": "#7F8C8D", "icone": "📍"},
    "Plages":        {"couleur": "#1ABC9C", "icone": "🏖"},
    "Randonnées":    {"couleur": "#16A085", "icone": "🥾"},
    "Shopping":      {"couleur": "#D35400", "icone": "🛍"},
    "Antique":       {"couleur": "#A0522D", "icone": "🏺"},
    "Renaissance":   {"couleur": "#8B6914", "icone": "🎨"},
    "Moyen-Age":     {"couleur": "#148B69", "icone": "⚔️"},
    "Contemporain":  {"couleur": "#2C3E50", "icone": "🏙"},
    "Village":       {"couleur": "#502C3E", "icone": "🏘"},
    "Quartier":      {"couleur": "#16A085", "icone": "🚶"},
    "Train":         {"couleur": "#7D3C98", "icone": "🚂"},
    "Jardin":        {"couleur": "#52A835", "icone": "🌿"},
    "Place":         {"couleur": "#E0A020", "icone": "🏟"},
    "Néoclassique":  {"couleur": "#5B8DB8", "icone": "🏛"},
    "Cinéma":        {"couleur": "#E91E8C", "icone": "🎬"},
    "Byzantin":      {"couleur": "#8B1A8B", "icone": "✝️"},
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
