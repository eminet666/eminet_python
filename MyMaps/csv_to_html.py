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

from utils import (
    SEPARATEUR, DEFAUT, FICHIER_CONFIG,
    CATEGORIES_DEFAUT,
    detecter_encodage, charger_categories, lire_csv,
)




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
      white-space: nowrap;
    }}

    /* ── Barre de recherche ─────────────────────────────────── */
    #search-box {{
      position: relative;
      display: flex;
      align-items: center;
      flex: 1;
      max-width: 300px;
      margin: 0 16px;
    }}

    .search-icon {{
      position: absolute;
      left: 10px;
      font-size: 0.8rem;
      pointer-events: none;
      color: #bbb;
      line-height: 1;
    }}

    #search-input {{
      width: 100%;
      padding: 6px 28px 6px 30px;
      border: 1px solid #e0e0e0;
      border-radius: 20px;
      font-size: 0.83rem;
      font-family: inherit;
      outline: none;
      background: #f5f5f5;
      color: #333;
      transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
      /* Masque le bouton natif "✕" des navigateurs sur type=search */
      -webkit-appearance: none;
    }}
    #search-input:focus {{
      border-color: #bbb;
      background: #fff;
      box-shadow: 0 1px 6px rgba(0,0,0,0.08);
    }}
    #search-input::placeholder {{ color: #ccc; }}
    #search-input::-webkit-search-cancel-button {{ display: none; }}

    #search-clear {{
      position: absolute;
      right: 9px;
      background: none;
      border: none;
      cursor: pointer;
      font-size: 0.7rem;
      color: #bbb;
      display: none;
      padding: 2px 4px;
      line-height: 1;
      border-radius: 50%;
    }}
    #search-clear:hover {{ color: #555; background: #eee; }}

    /* ── Dropdown résultats ─────────────────────────────────── */
    #search-results {{
      display: none;
      position: absolute;
      top: calc(100% + 6px);
      left: 0;
      right: 0;
      background: #fff;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.12);
      max-height: 300px;
      overflow-y: auto;
      z-index: 2000;
    }}
    #search-results.visible {{ display: block; }}

    .result-item {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      cursor: pointer;
      border-bottom: 1px solid #f2f2f2;
      transition: background 0.1s;
    }}
    .result-item:last-child {{ border-bottom: none; }}
    .result-item:hover {{ background: #f7f7f7; }}

    .result-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }}
    .result-text {{ flex: 1; min-width: 0; }}
    .result-nom {{
      font-size: 0.83rem;
      font-weight: 600;
      color: #222;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .result-meta {{ font-size: 0.7rem; color: #aaa; margin-top: 1px; }}

    .result-empty {{
      padding: 14px 12px;
      text-align: center;
      font-size: 0.8rem;
      color: #bbb;
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

      /* Barre de recherche pleine largeur sur mobile */
      #search-box {{
        max-width: unset;
        margin: 0 10px;
      }}
      header .count {{ display: none; }}

      /* Résultats — position fixe sous le header sur mobile */
      #search-results {{
        position: fixed;
        top: 51px;
        left: 8px;
        right: 8px;
        max-height: 50vh;
      }}

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
  <div id="search-box">
    <span class="search-icon">🔍</span>
    <input id="search-input" type="search" placeholder="Rechercher un lieu…" autocomplete="off" spellcheck="false">
    <button id="search-clear" title="Effacer">✕</button>
    <div id="search-results"></div>
  </div>
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
const allMarkers = [];   // {{ marker, lieu, cat, style }} — pour la recherche
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
    allMarkers.push({{marker, lieu, cat, style}});
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

// ── Barre de recherche ────────────────────────────────────────
const searchInput   = document.getElementById('search-input');
const searchClear   = document.getElementById('search-clear');
const searchResults = document.getElementById('search-results');
const searchLayer   = L.layerGroup().addTo(map);
let   enRecherche   = false;

function quitterRecherche() {{
  searchLayer.clearLayers();
  enRecherche = false;
  // Réinjecter chaque marqueur dans son groupe de catégorie
  allMarkers.forEach(({{marker, cat}}) => layers[cat].addLayer(marker));
  // Restaurer la visibilité selon l'état de la légende
  Object.entries(layers).forEach(([cat, groupe]) => {{
    if (!hidden.has(cat)) map.addLayer(groupe);
    else map.removeLayer(groupe);
  }});
  searchResults.classList.remove('visible');
  searchResults.innerHTML = '';
  searchClear.style.display = 'none';
}}

function filtrerMarqueurs(query) {{
  const q = query.trim().toLowerCase();
  if (!q) {{ quitterRecherche(); return; }}

  searchClear.style.display = 'block';

  // Première frappe : retirer tous les groupes de catégories de la carte
  if (!enRecherche) {{
    Object.values(layers).forEach(g => map.removeLayer(g));
    enRecherche = true;
  }}
  searchLayer.clearLayers();

  const resultats = [];
  allMarkers.forEach(entry => {{
    const {{lieu, cat}} = entry;
    const haystack = [lieu.nom, lieu.adresse, lieu.description, cat]
      .join(' ').toLowerCase();
    if (haystack.includes(q)) {{
      searchLayer.addLayer(entry.marker);
      resultats.push(entry);
    }}
  }});

  // Construire le dropdown
  searchResults.innerHTML = '';
  if (resultats.length === 0) {{
    searchResults.innerHTML = '<div class="result-empty">Aucun résultat</div>';
  }} else {{
    resultats.slice(0, 25).forEach(({{lieu, cat, style, marker}}) => {{
      const item = document.createElement('div');
      item.className = 'result-item';
      const meta = [cat, lieu.adresse].filter(Boolean).join(' · ');
      item.innerHTML = `
        <div class="result-dot" style="background:${{style.couleur}}"></div>
        <div class="result-text">
          <div class="result-nom">${{lieu.nom}}</div>
          <div class="result-meta">${{meta}}</div>
        </div>`;
      item.addEventListener('click', () => {{
        map.setView([lieu.lat, lieu.lon], 17);
        if (isMobile()) {{
          openSheet(buildPopupHtml(lieu, cat, style));
        }} else {{
          marker.bindPopup(buildPopupHtml(lieu, cat, style), {{maxWidth: 260}}).openPopup();
        }}
        searchResults.classList.remove('visible');
      }});
      searchResults.appendChild(item);
    }});
    if (resultats.length > 25) {{
      const more = document.createElement('div');
      more.className = 'result-empty';
      more.textContent = `… ${{resultats.length - 25}} résultats supplémentaires`;
      searchResults.appendChild(more);
    }}
  }}
  searchResults.classList.add('visible');
}}

searchInput.addEventListener('input', e => filtrerMarqueurs(e.target.value));

searchInput.addEventListener('focus', () => {{
  if (searchInput.value.trim()) searchResults.classList.add('visible');
}});

searchClear.addEventListener('click', () => {{
  searchInput.value = '';
  searchInput.focus();
  quitterRecherche();
}});

document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') {{
    searchInput.value = '';
    quitterRecherche();
    searchInput.blur();
  }}
}});

map.on('click', () => searchResults.classList.remove('visible'));

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
    cats = charger_categories()

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
