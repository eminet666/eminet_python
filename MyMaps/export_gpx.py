"""
export_gpx.py
-------------
Exporte un (ou plusieurs) fichiers CSV du projet en fichier GPX standard.

Le GPX généré est compatible avec :
  OsmAnd, Organic Maps, Maps.me, Google Maps (import),
  Garmin BaseCamp, QGIS, uMap, GPX Viewer…

Chaque lieu devient un waypoint (<wpt>) avec :
  <name>        — nom du lieu
  <desc>        — bloc complet : catégorie, adresse, note, description, transport
  <cmt>         — commentaire court (catégorie + note étoiles)
  <type>        — catégorie (utilisée par OsmAnd pour le groupe)
  <link>        — URL Wikipedia ou site officiel
  <sym>         — symbole Garmin approximatif selon la catégorie

Usage :
    python export_gpx.py                          → traite lieux.csv, génère lieux.gpx
    python export_gpx.py athenes.csv              → génère athenes.gpx
    python export_gpx.py a.csv b.csv              → fusionne et génère voyage.gpx
    python export_gpx.py athenes.csv -o mon.gpx   → nom de fichier personnalisé
    python export_gpx.py athenes.csv --cat Musée,Restaurant
    python export_gpx.py athenes.csv --sans Adresse,Amis
"""

import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape   # échappe & < > dans les textes

from utils import lire_csv

# ─────────────────────────────────────────────────────────────
# Correspondances catégorie → symbole Garmin
# (ignoré par la plupart des apps, utile pour BaseCamp / Oregon)
# ─────────────────────────────────────────────────────────────
SYMBOLES_GARMIN = {
    "Musée":         "Museum",
    "Musées":        "Museum",
    "Monument":      "Historic Site",
    "Monuments":     "Historic Site",
    "Eglise":        "Church",
    "Eglises":       "Church",
    "Restaurant":    "Restaurant",
    "Restaurants":   "Restaurant",
    "Hôtel":         "Hotel",
    "Hôtels":        "Hotel",
    "Hotel":         "Hotel",
    "Points de vue": "Scenic Area",
    "A faire":       "Flag, Blue",
    "Adresse":       "Pin, Blue",
    "Plages":        "Swimming Area",
    "Randonnées":    "Trail Head",
    "Shopping":      "Shopping Center",
    "Jardin":        "Park",
    "Place":         "City (Large)",
    "Quartier":      "City (Medium)",
    "Village":       "City (Small)",
    "Train":         "Train Station",
    "Antique":       "Historic Site",
    "Renaissance":   "Historic Site",
    "Moyen-Age":     "Historic Site",
    "Byzantin":      "Historic Site",
    "Néoclassique":  "Historic Site",
    "Contemporain":  "Building",
    "Cinéma":        "Theater",
}
SYMBOLE_DEFAUT = "Waypoint"


# ─────────────────────────────────────────────────────────────
# Construction du <desc> enrichi
# ─────────────────────────────────────────────────────────────
def _etoiles(note_str):
    """Convertit une note "3" en "★★★☆☆"."""
    try:
        n = min(5, max(1, int(note_str)))
        return "★" * n + "☆" * (5 - n)
    except (ValueError, TypeError):
        return ""


def _construire_desc(lieu):
    """Construit le texte complet du champ <desc>."""
    parties = [lieu["categorie"]]
    if lieu["note"]:
        etoiles = _etoiles(lieu["note"])
        if etoiles:
            parties[0] += f"  {etoiles}"
    if lieu["adresse"]:
        parties.append(lieu["adresse"])
    if lieu["description"]:
        parties.append(lieu["description"])
    if lieu["transport"]:
        parties.append(f"🚇 {lieu['transport']}")
    return "\n".join(parties)


def _construire_cmt(lieu):
    """Commentaire court : catégorie + note."""
    cmt = lieu["categorie"]
    etoiles = _etoiles(lieu["note"])
    if etoiles:
        cmt += f" {etoiles}"
    return cmt


# ─────────────────────────────────────────────────────────────
# Génération GPX (écriture directe en chaîne)
# Note : on n'utilise pas xml.etree.ElementTree car Python 3.12
# tronque le tag <name> en <n> avec un namespace par défaut.
# L'approche string + escape() est plus sûre et lisible ici.
# ─────────────────────────────────────────────────────────────
GPX_HEADER = """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="export_gpx.py"
     xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://www.topografix.com/GPX/1/1
       http://www.topografix.com/GPX/1/1/gpx.xsd">"""

def _t(texte):
    """Échappe les caractères XML spéciaux (&, <, >)."""
    return escape(str(texte)) if texte else ""


def _wpt_xml(lieu):
    """Retourne le bloc <wpt>…</wpt> pour un lieu."""
    nom   = _t(lieu["nom"])
    cmt   = _t(_construire_cmt(lieu))
    desc  = _t(_construire_desc(lieu))
    cat   = _t(lieu["categorie"])
    sym   = _t(SYMBOLES_GARMIN.get(lieu["categorie"], SYMBOLE_DEFAUT))
    lat   = f"{lieu['lat']:.6f}"
    lon   = f"{lieu['lon']:.6f}"

    lines = [
        f'  <wpt lat="{lat}" lon="{lon}">',
        f'    <name>{nom}</name>',
        f'    <cmt>{cmt}</cmt>',
        f'    <desc>{desc}</desc>',
        f'    <type>{cat}</type>',
        f'    <sym>{sym}</sym>',
    ]
    if lieu["url"]:
        lines += [
            f'    <link href="{_t(lieu["url"])}">',
            f'      <text>Lien</text>',
            f'    </link>',
        ]
    lines.append('  </wpt>')
    return "\n".join(lines)


def generer_gpx(lieux, titre="Mon Voyage", source_csv=""):
    """Retourne la chaîne XML GPX 1.1 complète."""
    maintenant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    blocs = [
        GPX_HEADER,
        "  <metadata>",
        f"    <name>{_t(titre)}</name>",
        f"    <desc>{_t(len(lieux))} lieux exportés depuis {_t(source_csv)}</desc>",
        f"    <time>{maintenant}</time>",
        "    <author><name>export_gpx.py</name></author>",
        "  </metadata>",
    ]
    for lieu in lieux:
        blocs.append(_wpt_xml(lieu))
    blocs.append("</gpx>")
    return "\n".join(blocs) + "\n"


def ecrire_gpx(contenu, chemin):
    """Écrit la chaîne GPX dans un fichier."""
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(contenu)


# ─────────────────────────────────────────────────────────────
# Filtrage
# ─────────────────────────────────────────────────────────────
def _filtrer(lieux, inclure=None, exclure=None):
    """
    Filtre la liste selon les catégories.
      inclure — set de catégories à garder (None = toutes)
      exclure — set de catégories à supprimer (None = aucune)
    """
    if inclure:
        lieux = [l for l in lieux if l["categorie"] in inclure]
    if exclure:
        lieux = [l for l in lieux if l["categorie"] not in exclure]
    return lieux


# ─────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]

    # ── Parsing des options ───────────────────────────────────
    inclure  = None
    exclure  = None
    sortie   = None
    fichiers = []

    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-o", "--sortir") and i + 1 < len(args):
            sortie = args[i + 1]
            i += 2
        elif a.startswith("--cat="):
            inclure = set(c.strip() for c in a[6:].split(",") if c.strip())
            i += 1
        elif a == "--cat" and i + 1 < len(args):
            inclure = set(c.strip() for c in args[i + 1].split(",") if c.strip())
            i += 2
        elif a.startswith("--sans="):
            exclure = set(c.strip() for c in a[7:].split(",") if c.strip())
            i += 1
        elif a == "--sans" and i + 1 < len(args):
            exclure = set(c.strip() for c in args[i + 1].split(",") if c.strip())
            i += 2
        elif not a.startswith("-"):
            fichiers.append(a)
            i += 1
        else:
            print(f"⚠️  Option inconnue ignorée : {a}")
            i += 1

    if not fichiers:
        fichiers = ["lieux.csv"]

    # ── Lecture et fusion des CSV ─────────────────────────────
    tous_les_lieux = []
    titre_carte    = ""
    sources        = []

    for chemin in fichiers:
        if not os.path.exists(chemin):
            print(f"❌ Fichier introuvable : {chemin}")
            continue
        print(f"📂 Lecture de {chemin}…")
        lieux, titre = lire_csv(chemin)
        print(f"   → {len(lieux)} lieux chargés")
        tous_les_lieux.extend(lieux)
        sources.append(Path(chemin).name)
        if not titre_carte and titre:
            titre_carte = titre

    if not tous_les_lieux:
        print("❌ Aucun lieu valide. Vérifiez vos fichiers.")
        sys.exit(1)

    if not titre_carte:
        titre_carte = Path(fichiers[0]).stem.replace("_", " ").title()

    # ── Filtrage ──────────────────────────────────────────────
    avant = len(tous_les_lieux)
    tous_les_lieux = _filtrer(tous_les_lieux, inclure=inclure, exclure=exclure)
    apres = len(tous_les_lieux)

    if inclure:
        print(f"🔍 Filtre --cat  : {', '.join(sorted(inclure))}")
    if exclure:
        print(f"🔍 Filtre --sans : {', '.join(sorted(exclure))}")
    if avant != apres:
        print(f"   → {avant - apres} lieux exclus, {apres} conservés")

    if not tous_les_lieux:
        print("❌ Aucun lieu après filtrage.")
        sys.exit(1)

    # ── Nom du fichier de sortie ──────────────────────────────
    if not sortie:
        if len(fichiers) == 1:
            sortie = Path(fichiers[0]).stem + ".gpx"
        else:
            sortie = "voyage.gpx"

    # ── Résumé par catégorie ──────────────────────────────────
    cats = {}
    for l in tous_les_lieux:
        cats[l["categorie"]] = cats.get(l["categorie"], 0) + 1

    print(f"\n📊 {apres} waypoints — {len(cats)} catégories :")
    for cat, nb in sorted(cats.items(), key=lambda x: -x[1]):
        sym = SYMBOLES_GARMIN.get(cat, SYMBOLE_DEFAUT)
        print(f"   {nb:>3}  {cat:<20} ({sym})")

    # ── Génération et écriture ────────────────────────────────
    source_label = " + ".join(sources)
    print(f"\n🗺️  Génération : {sortie}")
    contenu = generer_gpx(tous_les_lieux, titre=titre_carte, source_csv=source_label)
    ecrire_gpx(contenu, sortie)

    print(f"✅ {sortie} généré ({apres} waypoints)")
    print(f"\n👉 Importe {sortie} dans OsmAnd, Organic Maps, Google Maps ou BaseCamp")


if __name__ == "__main__":
    main()
