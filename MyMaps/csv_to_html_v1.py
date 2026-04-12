"""
csv_to_html.py
--------------
Génère une carte interactive HTML (Leaflet.js) à partir d'un fichier CSV.

- Marqueurs colorés et icônes par catégorie
- Légende interactive (clic pour afficher/masquer une catégorie)
- Popup avec nom, adresse, description au clic sur un marqueur
- Fond de carte OpenStreetMap (sans POI parasites possibles)
- Fonctionne dans tout navigateur, partageable, offline si carte en cache

Usage :
    python csv_to_html.py                    → utilise lieux.csv, génère lieux.html
    python csv_to_html.py paris.csv          → génère paris.html
    python csv_to_html.py a.csv b.csv        → fusionne et génère voyage.html
"""

import csv
import sys
import os
import json
from pathlib import Path

SEPARATEUR     = ";"
DEFAUT         = {"couleur": "#95A5A6", "icone": "📍"}
FICHIER_CONFIG = "categories.json"

# ─────────────────────────────────────────────────────────────
# Chargement des couleurs/icônes depuis categories.json
# Si le fichier n'existe pas, utilise les valeurs intégrées.
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
    "Contemporain":  {"couleur": "#2C3E50", "icone": "🏙"},
    "Quartier":      {"couleur": "#16A085", "icone": "🚶"},
    "Train":         {"couleur": "#7D3C98", "icone": "🚂"},
}

def _charger_categories():
    """Charge categories.json si présent, sinon utilise les valeurs intégrées."""
    if os.path.exists(FICHIER_CONFIG):
        try:
            with open(FICHIER_CONFIG, encoding="utf-8") as f:
                cats = json.load(f)
            print(f"📋 Catégories chargées depuis {FICHIER_CONFIG} ({len(cats)} entrées)")
            return cats
        except Exception as e:
            print(f"⚠️  Erreur lecture {FICHIER_CONFIG} : {e} — utilisation des valeurs par défaut")
    return CATEGORIES_DEFAUT


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
    enc = _detecter_encodage(chemin)
    lieux = []
    titre_carte = ""

    with open(chemin, newline="", encoding=enc) as f:
        lignes = list(csv.reader(f, delimiter=SEPARATEUR))

    debut = 0
    if lignes and lignes[0] and lignes[0][0].strip().lower() in ("pays", "country"):
        if len(lignes) > 1:
            vals = lignes[1]
            pays   = vals[0].strip() if len(vals) > 0 else ""
            region = vals[1].strip() if len(vals) > 1 else ""
            titre_carte = f"{region}{', ' if region and pays else ''}{pays}"
        debut = 2
        while debut < len(lignes) and not any(c.strip() for c in lignes[debut]):
            debut += 1

    if debut >= len(lignes):
        return lieux, titre_carte

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
            "lon":         lon,
            "lat":         lat,
        })

    return lieux, titre_carte


def generer_html(lieux, titre="Mon Voyage", categories=None):
    # Centre de la carte = moyenne des coordonnées
    lat_moy = sum(l["lat"] for l in lieux) / len(lieux)
    lon_moy = sum(l["lon"] for l in lieux) / len(lieux)

    # Construire les données JS par catégorie
    cats_data = {}
    for lieu in lieux:
        cat = lieu["categorie"]
        cats_data.setdefault(cat, []).append(lieu)

    if categories is None:
        categories = CATEGORIES_DEFAUT

    # Sérialiser en JSON pour injection dans le HTML
    data_js = json.dumps(cats_data, ensure_ascii=False, indent=2)
    styles_js = json.dumps(
        {cat: categories.get(cat, DEFAUT) for cat in cats_data},
        ensure_ascii=False
    )

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{titre}</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
  <style>
    /* ── Reset ─────────────────────────────────────────────── */
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
      font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
      background: #f5f5f5;
      color: #222;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}

    /* ── Header ─────────────────────────────────────────────── */
    header {{
      background: #ffffff;
      padding: 10px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid #e0e0e0;
      z-index: 1000;
      flex-shrink: 0;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }}

    header h1 {{
      font-size: 1rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #333;
    }}

    header .count {{
      font-size: 0.75rem;
      color: #999;
      letter-spacing: 0.05em;
    }}

    /* ── Carte ──────────────────────────────────────────────── */
    #map {{ flex: 1; z-index: 1; }}

    /* ── Bouton GPS ─────────────────────────────────────────── */
    #gps-toggle {{
      position: absolute;
      bottom: 30px;
      left: 10px;
      z-index: 1000;
      width: 40px;
      height: 40px;
      border-radius: 6px;
      background: #ffffff;
      border: 1px solid #ddd;
      box-shadow: 0 2px 8px rgba(0,0,0,0.12);
      font-size: 1.1rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s, box-shadow 0.2s;
    }}
    #gps-toggle:hover  {{ box-shadow: 0 3px 12px rgba(0,0,0,0.2); }}
    #gps-toggle.active {{ background: #e8f5e9; border-color: #27AE60; }}
    #gps-toggle.error  {{ background: #fdecea; border-color: #e74c3c; }}

    /* ── Marqueurs ──────────────────────────────────────────── */
    .marker-pin {{
      width: 32px;
      height: 32px;
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25);
      border: 2px solid rgba(255,255,255,0.7);
    }}
    .marker-pin .marker-icon {{
      transform: rotate(45deg);
      font-size: 14px;
      line-height: 1;
    }}

    /* ── Légende DESKTOP ────────────────────────────────────── */
    #legend {{
      position: absolute;
      bottom: 30px;
      right: 10px;
      z-index: 1000;
      background: rgba(255,255,255,0.97);
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 12px 16px;
      min-width: 165px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.12);
    }}

    #legend h3 {{
      font-size: 0.65rem;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: #999;
      margin-bottom: 10px;
    }}

    .legend-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 6px;
      border-radius: 4px;
      cursor: pointer;
      transition: background 0.15s;
      user-select: none;
    }}
    .legend-item:hover {{ background: #f5f5f5; }}
    .legend-item.hidden {{ opacity: 0.3; }}

    .legend-dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex-shrink: 0;
    }}
    .legend-label {{ font-size: 0.8rem; color: #333; flex: 1; }}
    .legend-count  {{ font-size: 0.7rem; color: #bbb; }}

    /* Bouton légende mobile — caché sur desktop */
    #legend-toggle {{ display: none; }}

    /* ── Popup DESKTOP ──────────────────────────────────────── */
    .leaflet-popup-content-wrapper {{
      background: #ffffff;
      border: 1px solid #e8e8e8;
      border-radius: 8px;
      color: #222;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }}
    .leaflet-popup-tip       {{ background: #ffffff; }}
    .leaflet-popup-close-button {{ color: #aaa !important; }}

    /* ── Bottom sheet MOBILE (caché par défaut) ─────────────── */
    #bottom-sheet {{
      display: none; /* activé en JS sur mobile */
    }}

    /* ── Contenu popup / bottom-sheet (partagé) ─────────────── */
    .popup-content  {{ padding: 4px 2px; }}
    .popup-cat      {{ font-size: 0.65rem; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px; }}
    .popup-nom      {{ font-size: 1rem; font-weight: 600; color: #111; margin-bottom: 4px; }}
    .popup-note     {{ font-size: 0.85rem; color: #f0a500; letter-spacing: 0.05em; margin-bottom: 6px; }}
    .popup-adresse  {{ font-size: 0.75rem; color: #888; margin-bottom: 4px; }}
    .popup-transport{{ font-size: 0.75rem; color: #5d8aa8; margin-bottom: 4px; }}
    .popup-desc     {{ font-size: 0.8rem; color: #555; line-height: 1.4; }}
    .popup-url      {{ font-size: 0.75rem; margin-top: 6px; }}
    .popup-url a    {{ color: #2980B9; text-decoration: none; font-weight: 500; }}
    .popup-url a:hover {{ text-decoration: underline; }}

    /* ════════════════════════════════════════════════════════
       MOBILE  (écrans ≤ 768px)
       ════════════════════════════════════════════════════════ */
    @media (max-width: 768px) {{

      /* Header plus compact */
      header {{ padding: 8px 14px; }}
      header h1 {{ font-size: 0.85rem; }}

      /* Marqueurs plus grands pour le doigt */
      .marker-pin {{
        width: 42px;
        height: 42px;
        border-width: 3px;
      }}
      .marker-pin .marker-icon {{ font-size: 18px; }}

      /* Légende cachée par défaut, ouvrable */
      #legend {{
        bottom: 0;
        right: 0;
        left: 0;
        border-radius: 16px 16px 0 0;
        padding: 16px 20px 24px;
        min-width: unset;
        transform: translateY(100%);
        transition: transform 0.3s ease;
        max-height: 60vh;
        overflow-y: auto;
      }}
      #legend.open {{ transform: translateY(0); }}

      #legend h3 {{
        font-size: 0.7rem;
        text-align: center;
        margin-bottom: 14px;
      }}

      /* Drag handle au dessus de la légende */
      #legend::before {{
        content: '';
        display: block;
        width: 36px;
        height: 4px;
        background: #ddd;
        border-radius: 2px;
        margin: 0 auto 14px;
      }}

      .legend-item  {{ padding: 8px 6px; }}
      .legend-label {{ font-size: 0.9rem; }}
      .legend-count {{ font-size: 0.8rem; }}
      .legend-dot   {{ width: 12px; height: 12px; }}

      /* Bouton flottant pour ouvrir la légende */
      #legend-toggle {{
        display: flex;
        position: absolute;
        bottom: 24px;
        right: 16px;
        z-index: 1001;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: #ffffff;
        border: 1px solid #ddd;
        box-shadow: 0 2px 10px rgba(0,0,0,0.15);
        align-items: center;
        justify-content: center;
        font-size: 1.3rem;
        cursor: pointer;
        transition: box-shadow 0.15s;
      }}
      #legend-toggle:hover {{ box-shadow: 0 4px 16px rgba(0,0,0,0.2); }}

      /* Bouton GPS mobile — empilé au-dessus du bouton légende */
      #gps-toggle {{
        position: absolute;
        bottom: 84px;
        left: unset;
        right: 16px;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        box-shadow: 0 2px 10px rgba(0,0,0,0.15);
        font-size: 1.3rem;
        z-index: 1001;
      }}


      .leaflet-popup {{ display: none !important; }}

      /* Bottom sheet à la place */
      #bottom-sheet {{
        display: block;
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        z-index: 1002;
        background: #ffffff;
        border-radius: 16px 16px 0 0;
        padding: 20px 20px 32px;
        box-shadow: 0 -4px 24px rgba(0,0,0,0.15);
        transform: translateY(100%);
        transition: transform 0.3s ease;
        max-height: 55vh;
        overflow-y: auto;
      }}
      #bottom-sheet.open {{ transform: translateY(0); }}

      #bottom-sheet::before {{
        content: '';
        display: block;
        width: 36px;
        height: 4px;
        background: #ddd;
        border-radius: 2px;
        margin: 0 auto 16px;
      }}

      #bottom-sheet .popup-nom     {{ font-size: 1.15rem; margin-bottom: 6px; }}
      #bottom-sheet .popup-cat     {{ font-size: 0.7rem; margin-bottom: 6px; }}
      #bottom-sheet .popup-note    {{ font-size: 1rem; margin-bottom: 8px; }}
      #bottom-sheet .popup-adresse {{ font-size: 0.85rem; margin-bottom: 6px; }}
      #bottom-sheet .popup-transport {{ font-size: 0.85rem; margin-bottom: 6px; }}
      #bottom-sheet .popup-desc    {{ font-size: 0.9rem; line-height: 1.5; }}
      #bottom-sheet .popup-url     {{ font-size: 0.9rem; margin-top: 12px; }}
      #bottom-sheet .popup-url a   {{ font-size: 1rem; padding: 8px 0; display: inline-block; }}

      /* Bouton fermer le bottom sheet */
      #sheet-close {{
        position: absolute;
        top: 16px;
        right: 16px;
        background: #f5f5f5;
        border: none;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        font-size: 1rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #888;
      }}
    }}
  </style>
</head>
<body>

<header>
  <h1>🗺 {titre}</h1>
  <span class="count">{len(lieux)} lieux</span>
</header>

<div id="map"></div>

<!-- Bouton GPS -->
<button id="gps-toggle" title="Ma position">📍</button>

<!-- Légende (desktop : flottante / mobile : bottom sheet) -->
<div id="legend"><h3>Catégories</h3></div>

<!-- Bouton mobile pour ouvrir la légende -->
<button id="legend-toggle" title="Catégories">🗂</button>

<!-- Bottom sheet mobile -->
<div id="bottom-sheet">
  <button id="sheet-close">✕</button>
  <div id="sheet-content"></div>
</div>

<script>
const DATA    = {data_js};
const STYLES  = {styles_js};
const layers  = {{}};
const hidden  = new Set();
const isMobile = () => window.innerWidth <= 768;

// ── Carte ────────────────────────────────────────────────────
const map = L.map('map', {{
  center: [{lat_moy:.6f}, {lon_moy:.6f}],
  zoom: 13,
  zoomControl: true,
  tap: true,
}});

L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  attribution: '© OpenStreetMap',
  maxZoom: 19,
}}).addTo(map);

// ── Icônes ───────────────────────────────────────────────────
function creerIcone(style, icone) {{
  const sz = isMobile() ? 42 : 32;
  const label = (icone !== undefined) ? icone : style.icone;
  const isNum = (typeof label === 'number' || (typeof label === 'string' && /^[0-9]+$/.test(label)));
  const fs = isNum
    ? (isMobile() ? 13 : 11)
    : (isMobile() ? 18 : 14);
  const extraStyle = isNum
    ? 'font-weight:700;color:#fff;font-family:monospace;transform:rotate(45deg);'
    : 'transform:rotate(45deg);';
  return L.divIcon({{
    className: '',
    html: `<div class="marker-pin" style="background:${{style.couleur}};width:${{sz}}px;height:${{sz}}px">
             <span class="marker-icon" style="font-size:${{fs}}px;${{extraStyle}}">${{label}}</span>
           </div>`,
    iconSize:    [sz, sz],
    iconAnchor:  [sz/2, sz],
    popupAnchor: [0, -(sz+4)],
  }});
}}

// ── Contenu popup ─────────────────────────────────────────────
function buildPopupHtml(lieu, cat, style) {{
  let html = `<div class="popup-content">
    <div class="popup-cat" style="color:${{style.couleur}}">${{cat}}</div>
    <div class="popup-nom">${{lieu.nom}}</div>`;
  if (lieu.note) {{
    const n = Math.min(5, Math.max(1, parseInt(lieu.note) || 0));
    html += `<div class="popup-note">${{'★'.repeat(n) + '☆'.repeat(5-n)}}</div>`;
  }}
  if (lieu.adresse)     html += `<div class="popup-adresse">📮 ${{lieu.adresse}}</div>`;
  if (lieu.transport)   html += `<div class="popup-transport">🚇 ${{lieu.transport}}</div>`;
  if (lieu.description) html += `<div class="popup-desc">${{lieu.description}}</div>`;
  if (lieu.url)         html += `<div class="popup-url"><a href="${{lieu.url}}" target="_blank">🔗 Site</a></div>`;
  html += `</div>`;
  return html;
}}

// ── Bottom sheet mobile ───────────────────────────────────────
const sheet        = document.getElementById('bottom-sheet');
const sheetContent = document.getElementById('sheet-content');
const sheetClose   = document.getElementById('sheet-close');

function openSheet(html) {{
  sheetContent.innerHTML = html;
  sheet.classList.add('open');
  // Fermer la légende si ouverte
  document.getElementById('legend').classList.remove('open');
}}

sheetClose.addEventListener('click', () => sheet.classList.remove('open'));
map.on('click', () => sheet.classList.remove('open'));

// ── Marqueurs ────────────────────────────────────────────────
Object.entries(DATA).forEach(([cat, lieux]) => {{
  const style  = STYLES[cat] || {{couleur: '#95A5A6', icone: '📍'}};
  const groupe = L.layerGroup().addTo(map);
  layers[cat]  = groupe;

  lieux.forEach(lieu => {{
    const marker = L.marker([lieu.lat, lieu.lon], {{icon: creerIcone(style, lieu.index)}});

    marker.on('click', () => {{
      if (isMobile()) {{
        openSheet(buildPopupHtml(lieu, cat, style));
      }} else {{
        marker.bindPopup(buildPopupHtml(lieu, cat, style), {{maxWidth: 260}}).openPopup();
      }}
    }});

    groupe.addLayer(marker);
  }});
}});

// ── Légende interactive ───────────────────────────────────────
const legend = document.getElementById('legend');
Object.entries(DATA).forEach(([cat, lieux]) => {{
  const style = STYLES[cat] || {{couleur: '#95A5A6', icone: '📍'}};
  const item  = document.createElement('div');
  item.className   = 'legend-item';
  item.dataset.cat = cat;
  item.innerHTML   = `
    <div class="legend-dot" style="background:${{style.couleur}}"></div>
    <span class="legend-label">${{style.icone}} ${{cat}}</span>
    <span class="legend-count">${{lieux.length}}</span>`;

  item.addEventListener('click', () => {{
    if (hidden.has(cat)) {{
      map.addLayer(layers[cat]);
      hidden.delete(cat);
      item.classList.remove('hidden');
    }} else {{
      map.removeLayer(layers[cat]);
      hidden.add(cat);
      item.classList.add('hidden');
    }}
  }});
  legend.appendChild(item);
}});

// ── Géolocalisation ──────────────────────────────────────────
const gpsBtn      = document.getElementById('gps-toggle');
let   gpsActif    = false;
let   gpsWatchId  = null;
let   gpsMarker   = null;
let   gpsCercle   = null;

function stopperGPS() {{
  if (gpsWatchId !== null) {{
    navigator.geolocation.clearWatch(gpsWatchId);
    gpsWatchId = null;
  }}
  if (gpsMarker)  {{ map.removeLayer(gpsMarker);  gpsMarker  = null; }}
  if (gpsCercle)  {{ map.removeLayer(gpsCercle);  gpsCercle  = null; }}
  gpsActif = false;
  gpsBtn.classList.remove('active', 'error');
  gpsBtn.title = 'Ma position';
  gpsBtn.textContent = '📍';
}}

function mettreAJourPosition(pos) {{
  const lat = pos.coords.latitude;
  const lon = pos.coords.longitude;
  const acc = pos.coords.accuracy;

  // Icône position personnalisée
  const iconePos = L.divIcon({{
    className: '',
    html: `<div style="
      width:16px; height:16px; border-radius:50%;
      background:#2980B9; border:3px solid #fff;
      box-shadow:0 0 0 2px #2980B9;
    "></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  }});

  if (gpsMarker) {{
    gpsMarker.setLatLng([lat, lon]);
    gpsCercle.setLatLng([lat, lon]).setRadius(acc);
  }} else {{
    gpsMarker = L.marker([lat, lon], {{icon: iconePos, zIndexOffset: 9999}})
      .bindPopup(`📍 Vous êtes ici<br><small>Précision : ${{Math.round(acc)}} m</small>`)
      .addTo(map);
    gpsCercle = L.circle([lat, lon], {{
      radius: acc,
      color: '#2980B9',
      fillColor: '#2980B9',
      fillOpacity: 0.08,
      weight: 1,
    }}).addTo(map);
    map.setView([lat, lon], 15);
  }}
}}

function erreurGPS(err) {{
  gpsBtn.classList.remove('active');
  gpsBtn.classList.add('error');
  gpsBtn.title = err.code === 1 ? 'Accès refusé' : 'Position indisponible';
  gpsBtn.textContent = '⚠️';
  setTimeout(() => {{
    gpsBtn.classList.remove('error');
    gpsBtn.textContent = '📍';
  }}, 3000);
}}

gpsBtn.addEventListener('click', () => {{
  if (!navigator.geolocation) {{
    alert("La géolocalisation n'est pas supportée par ce navigateur.");
    return;
  }}
  if (gpsActif) {{
    stopperGPS();
  }} else {{
    gpsActif = true;
    gpsBtn.classList.add('active');
    gpsBtn.title = 'Désactiver GPS';
    gpsBtn.textContent = '🔵';
    gpsWatchId = navigator.geolocation.watchPosition(
      mettreAJourPosition,
      erreurGPS,
      {{ enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }}
    );
  }}
}});

// ── Bouton légende mobile ─────────────────────────────────────
document.getElementById('legend-toggle').addEventListener('click', () => {{
  sheet.classList.remove('open');
  legend.classList.toggle('open');
}});

// Fermer légende si clic sur la carte
map.on('click', () => legend.classList.remove('open'));
</script>
</body>
</html>
"""
    return html


def main():
    fichiers_csv = sys.argv[1:] if len(sys.argv) > 1 else ["lieux.csv"]

    tous_les_lieux = []
    titre_carte    = ""

    for fichier in fichiers_csv:
        if not os.path.exists(fichier):
            print(f"❌ Fichier introuvable : {fichier}")
            continue
        print(f"📂 Lecture de {fichier}...")
        lieux, titre = lire_csv(fichier)
        print(f"   → {len(lieux)} lieux chargés")
        tous_les_lieux.extend(lieux)
        if not titre_carte and titre:
            titre_carte = titre

    if not tous_les_lieux:
        print("❌ Aucun lieu valide. Vérifiez vos fichiers (coordonnées présentes ?).")
        sys.exit(1)

    if not titre_carte:
        titre_carte = Path(fichiers_csv[0]).stem.replace("_", " ").title()

    # Charger les catégories (depuis categories.json ou valeurs intégrées)
    cats = _charger_categories()

    # Avertir pour les catégories inconnues
    cats_inconnues = set(l["categorie"] for l in tous_les_lieux) - set(cats.keys())
    if cats_inconnues:
        print(f"\n⚠️  Catégories inconnues (marqueur gris par défaut) :")
        for c in sorted(cats_inconnues):
            print(f"   • {c}  ← ajoute-la dans {FICHIER_CONFIG}")

    sortie = (Path(fichiers_csv[0]).stem + ".html") if len(fichiers_csv) == 1 else "voyage.html"

    print(f"\n🗺️  Génération : {sortie}")
    with open(sortie, "w", encoding="utf-8") as f:
        f.write(generer_html(tous_les_lieux, titre=titre_carte, categories=cats))

    nb_cats = set(l["categorie"] for l in tous_les_lieux)
    print(f"✅ {len(tous_les_lieux)} marqueurs – {len(nb_cats)} catégories → {sortie}")
    print(f"\n👉 Ouvre {sortie} dans ton navigateur")


if __name__ == "__main__":
    main()
