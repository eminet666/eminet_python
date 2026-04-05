"""
csv_to_kml.py
-------------
Convertit un fichier CSV de lieux en fichier KML avec marqueurs colorés par catégorie.
Compatible avec : OsmAnd, Google My Maps, Apple Plans, QGIS

Format CSV (séparateur ";") :
    categorie;nom;adresse;description;lon;lat

Usage :
    python csv_to_kml.py                        → utilise lieux.csv, génère lieux.kml
    python csv_to_kml.py paris.csv              → génère paris.kml
    python csv_to_kml.py paris.csv rome.csv     → fusionne et génère voyage.kml
"""

import csv
import sys
import os
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom

# ─────────────────────────────────────────────────────────────
# Couleurs par catégorie (format KML : aabbggrr)
# ─────────────────────────────────────────────────────────────
COULEURS = {
    "Musée":          "ff1400FF",
    "Musées":         "ff1400FF",
    "Monument":       "ff0050FF",
    "Monuments":      "ff0050FF",
    "Eglise":         "ff5000FF",
    "Eglises":        "ff500096",
    "Restaurants":    "ff14F0FF",
    "Restaurant":     "ff14F0FF",
    "Hôtels":         "ffF07814",
    "Hôtel":          "ffF07814",
    "Points de vue":  "ff14B400",
    "A faire":        "ffF014DC",
    "Adresse":        "ffFFFFFF",
    "Plages":         "ff78F0FF",
    "Randonnées":     "ff0A7828",
    "Shopping":       "ff1478FF",
}
COULEUR_DEFAUT = "ffA0A0A0"

ICONES = {
    "Musée":          "http://maps.google.com/mapfiles/kml/pal3/icon21.png",
    "Musées":         "http://maps.google.com/mapfiles/kml/pal3/icon21.png",
    "Restaurants":    "http://maps.google.com/mapfiles/kml/pal2/icon57.png",
    "Restaurant":     "http://maps.google.com/mapfiles/kml/pal2/icon57.png",
    "Hôtels":         "http://maps.google.com/mapfiles/kml/pal2/icon17.png",
    "Hôtel":          "http://maps.google.com/mapfiles/kml/pal2/icon17.png",
    "Points de vue":  "http://maps.google.com/mapfiles/kml/pal4/icon49.png",
    "A faire":        "http://maps.google.com/mapfiles/kml/pal3/icon35.png",
    "Adresse":        "http://maps.google.com/mapfiles/kml/pal4/icon57.png",
}
ICONE_DEFAUT = "http://maps.google.com/mapfiles/kml/paddle/wht-circle.png"


def _detecter_encodage(chemin):
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            with open(chemin, encoding=enc) as f:
                f.read()
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def lire_csv(chemin):
    """Lit un CSV (avec ou sans en-tête contexte pays/région) et retourne une liste de dicts."""
    enc = _detecter_encodage(chemin)
    lieux = []

    with open(chemin, newline="", encoding=enc) as f:
        lignes = list(csv.reader(f, delimiter=";"))

    debut = 0
    # Sauter l'en-tête pays/région si présent
    if lignes and lignes[0] and lignes[0][0].strip().lower() in ("pays", "country"):
        debut = 2
        while debut < len(lignes) and not any(c.strip() for c in lignes[debut]):
            debut += 1

    if debut >= len(lignes):
        return lieux

    entete = [c.strip().lower() for c in lignes[debut]]
    debut += 1

    for i, row in enumerate(lignes[debut:], start=debut + 1):
        if not any(c.strip() for c in row):
            continue
        d = {col: (row[j].strip() if j < len(row) else "") for j, col in enumerate(entete)}

        # Validation coordonnées
        try:
            lon = float(d.get("lon", ""))
            lat = float(d.get("lat", ""))
        except ValueError:
            nom = d.get("nom", "?")
            if d.get("lon") or d.get("lat"):
                print(f"  ⚠️  Ligne {i} ignorée (coordonnées invalides) : {nom}")
            else:
                print(f"  ⚠️  Ligne {i} ignorée (pas de coordonnées) : {nom} — lance d'abord geocode.py")
            continue

        lieux.append({
            "categorie":   d.get("categorie", "Autre"),
            "nom":         d.get("nom", "Sans nom"),
            "adresse":     d.get("adresse", ""),
            "note":        d.get("note", ""),
            "description": d.get("description", ""),
            "transport":   d.get("transport", ""),
            "url":         d.get("url", ""),
            "lon":         lon,
            "lat":         lat,
        })

    return lieux


def construire_kml(lieux, titre="Mon Voyage"):
    # Regrouper par catégorie
    categories = {}
    for lieu in lieux:
        categories.setdefault(lieu["categorie"], []).append(lieu)

    kml = Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    doc = SubElement(kml, "Document")
    SubElement(doc, "name").text = titre
    SubElement(doc, "description").text = f"{len(lieux)} lieux – {len(categories)} catégories"

    # Styles par catégorie
    for cat in categories:
        style = SubElement(doc, "Style", id=cat.replace(" ", "_"))
        icon_style = SubElement(style, "IconStyle")
        SubElement(icon_style, "color").text = COULEURS.get(cat, COULEUR_DEFAUT)
        SubElement(icon_style, "scale").text = "1.2"
        icon = SubElement(icon_style, "Icon")
        SubElement(icon, "href").text = ICONES.get(cat, ICONE_DEFAUT)
        SubElement(SubElement(style, "LabelStyle"), "scale").text = "0.8"

    # Un Folder par catégorie
    for cat, lieux_cat in sorted(categories.items()):
        folder = SubElement(doc, "Folder")
        SubElement(folder, "name").text = f"{cat} ({len(lieux_cat)})"

        for lieu in lieux_cat:
            pm = SubElement(folder, "Placemark")
            SubElement(pm, "name").text = lieu["nom"]

            # Description enrichie : texte + adresse + transport si présents
            desc_parts = []
            if lieu["note"]:
                try:
                    n = min(5, max(1, int(lieu["note"])))
                    desc_parts.append("★" * n + "☆" * (5 - n))
                except ValueError:
                    pass
            if lieu["description"]:
                desc_parts.append(lieu["description"])
            if lieu["adresse"]:
                desc_parts.append(f"📮 {lieu['adresse']}")
            if lieu["transport"]:
                desc_parts.append(f"🚇 {lieu['transport']}")
            if lieu["url"]:
                desc_parts.append(f"🔗 {lieu['url']}")
            if desc_parts:
                SubElement(pm, "description").text = "\n".join(desc_parts)

            SubElement(pm, "styleUrl").text = f"#{cat.replace(' ', '_')}"
            point = SubElement(pm, "Point")
            SubElement(point, "coordinates").text = f"{lieu['lon']},{lieu['lat']},0"

    xml_brut = tostring(kml, encoding="unicode")
    return xml.dom.minidom.parseString(xml_brut).toprettyxml(indent="  ")


def main():
    fichiers_csv = sys.argv[1:] if len(sys.argv) > 1 else ["lieux.csv"]

    tous_les_lieux = []
    for fichier in fichiers_csv:
        if not os.path.exists(fichier):
            print(f"❌ Fichier introuvable : {fichier}")
            continue
        print(f"📂 Lecture de {fichier}...")
        lieux = lire_csv(fichier)
        print(f"   → {len(lieux)} lieux chargés")
        tous_les_lieux.extend(lieux)

    if not tous_les_lieux:
        print("❌ Aucun lieu valide. Vérifiez vos fichiers CSV (coordonnées présentes ?).")
        sys.exit(1)

    sortie = (Path(fichiers_csv[0]).stem + ".kml") if len(fichiers_csv) == 1 else "voyage.kml"
    titre  = Path(sortie).stem.replace("_", " ").title()

    print(f"\n🗺️  Génération : {sortie}")
    with open(sortie, "w", encoding="utf-8") as f:
        f.write(construire_kml(tous_les_lieux, titre=titre))

    cats = set(l["categorie"] for l in tous_les_lieux)
    print(f"✅ {len(tous_les_lieux)} marqueurs – {len(cats)} catégories → {sortie}")
    print()
    print("📱 Import OsmAnd        : Menu → Mes lieux → Favoris → Importer")
    print("🌍 Import Google My Maps : maps.google.com/maps/d → Importer")


if __name__ == "__main__":
    main()
