"""
run.py
------
Enchaîne automatiquement les trois scripts pour un fichier CSV donné.

Usage :
    python run.py                      → traite lieux.csv
    python run.py paris.csv            → traite paris.csv
    python run.py rome.csv --wiki-en   → Rome avec Wikipedia en anglais
    python run.py paris.csv --no-wiki  → sans recherche Wikipedia
    python run.py paris.csv --force    → tout re-traiter même si déjà rempli
"""

import subprocess
import sys

args     = sys.argv[1:]
fichier  = next((a for a in args if not a.startswith("--")), "lieux.csv")
options  = [a for a in args if a.startswith("--")]

print(f"🚀 Traitement de : {fichier}")
print("─" * 40)

# Étape 1 — Géocodage + Wikipedia
print("\n📍 Étape 1 : Géocodage + Wikipedia")
subprocess.run(["python", "geocode.py", fichier] + options, check=True)

# Étape 2 — Génération HTML
print("\n🗺️  Étape 2 : Carte HTML")
subprocess.run(["python", "csv_to_html.py", fichier], check=True)

# Étape 3 — Génération KML (pour OsmAnd)
print("\n📱 Étape 3 : Carte KML (OsmAnd)")
subprocess.run(["python", "csv_to_kml.py", fichier], check=True)

print("\n✅ Tout est prêt !")
