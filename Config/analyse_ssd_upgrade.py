"""
=============================================================================
  ANALYSEUR DE CONFIGURATION MATÉRIELLE - AJOUT SSD
  Compatible Windows 11
  Nécessite : pip install wmi pywin32 colorama tabulate
=============================================================================
"""

import subprocess
import json
import sys
import os
import platform
from dataclasses import dataclass, field
from typing import Optional
import textwrap

# ── Vérification des dépendances ──────────────────────────────────────────────
def check_and_install(package: str, import_name: str = None):
    import_name = import_name or package
    try:
        __import__(import_name)
    except ImportError:
        print(f"  → Installation de '{package}'...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])

print("Vérification des dépendances...")
check_and_install("wmi")
check_and_install("pywin32", "win32api")
check_and_install("colorama")
check_and_install("tabulate")
check_and_install("reportlab")

import wmi
from colorama import init, Fore, Style, Back
from tabulate import tabulate

init(autoreset=True)

# ── Palette couleurs ──────────────────────────────────────────────────────────
OK    = Fore.GREEN  + Style.BRIGHT
WARN  = Fore.YELLOW + Style.BRIGHT
ERR   = Fore.RED    + Style.BRIGHT
INFO  = Fore.CYAN   + Style.BRIGHT
TITLE = Fore.WHITE  + Back.BLUE + Style.BRIGHT
DIM   = Style.DIM
RST   = Style.RESET_ALL

# ── Catalogue SSD (prix indicatifs 2025, marché européen) ────────────────────
SSD_CATALOG = {
    "M.2 NVMe PCIe 4.0": {
        "1To": [
            {"nom": "Samsung 980 Pro 1 To",          "prix": "85 €",  "lect": "7 000 MB/s", "ecrit": "5 000 MB/s"},
            {"nom": "WD Black SN850X 1 To",           "prix": "90 €",  "lect": "7 300 MB/s", "ecrit": "6 300 MB/s"},
            {"nom": "Seagate FireCuda 530 1 To",      "prix": "88 €",  "lect": "7 300 MB/s", "ecrit": "6 900 MB/s"},
            {"nom": "Kingston Fury Renegade 1 To",    "prix": "82 €",  "lect": "7 300 MB/s", "ecrit": "6 000 MB/s"},
        ],
        "2To": [
            {"nom": "Samsung 980 Pro 2 To",           "prix": "145 €", "lect": "7 000 MB/s", "ecrit": "5 100 MB/s"},
            {"nom": "WD Black SN850X 2 To",           "prix": "150 €", "lect": "7 300 MB/s", "ecrit": "6 600 MB/s"},
            {"nom": "Seagate FireCuda 530 2 To",      "prix": "155 €", "lect": "7 300 MB/s", "ecrit": "6 900 MB/s"},
            {"nom": "Kingston Fury Renegade 2 To",    "prix": "140 €", "lect": "7 300 MB/s", "ecrit": "7 000 MB/s"},
        ],
    },
    "M.2 NVMe PCIe 3.0": {
        "1To": [
            {"nom": "Samsung 970 EVO Plus 1 To",      "prix": "65 €",  "lect": "3 500 MB/s", "ecrit": "3 300 MB/s"},
            {"nom": "WD Blue SN570 1 To",             "prix": "55 €",  "lect": "3 500 MB/s", "ecrit": "3 000 MB/s"},
            {"nom": "Crucial P3 Plus 1 To",           "prix": "50 €",  "lect": "5 000 MB/s", "ecrit": "3 600 MB/s"},
            {"nom": "Kingston NV2 1 To",              "prix": "48 €",  "lect": "3 500 MB/s", "ecrit": "2 100 MB/s"},
        ],
        "2To": [
            {"nom": "Samsung 970 EVO Plus 2 To",      "prix": "115 €", "lect": "3 500 MB/s", "ecrit": "3 300 MB/s"},
            {"nom": "WD Blue SN570 2 To",             "prix": "100 €", "lect": "3 500 MB/s", "ecrit": "3 000 MB/s"},
            {"nom": "Crucial P3 Plus 2 To",           "prix": "90 €",  "lect": "5 000 MB/s", "ecrit": "3 600 MB/s"},
            {"nom": "Kingston NV2 2 To",              "prix": "85 €",  "lect": "3 500 MB/s", "ecrit": "2 800 MB/s"},
        ],
    },
    "M.2 SATA": {
        "1To": [
            {"nom": "Samsung 870 EVO M.2 1 To",       "prix": "75 €",  "lect": "560 MB/s",   "ecrit": "530 MB/s"},
            {"nom": "Crucial MX500 M.2 1 To",         "prix": "65 €",  "lect": "560 MB/s",   "ecrit": "510 MB/s"},
            {"nom": "WD Blue SA510 M.2 1 To",         "prix": "60 €",  "lect": "560 MB/s",   "ecrit": "510 MB/s"},
        ],
        "2To": [
            {"nom": "Samsung 870 EVO M.2 2 To",       "prix": "130 €", "lect": "560 MB/s",   "ecrit": "530 MB/s"},
            {"nom": "Crucial MX500 M.2 2 To",         "prix": "115 €", "lect": "560 MB/s",   "ecrit": "510 MB/s"},
            {"nom": "WD Blue SA510 M.2 2 To",         "prix": "110 €", "lect": "560 MB/s",   "ecrit": "510 MB/s"},
        ],
    },
    "SATA 2.5\"": {
        "1To": [
            {"nom": "Samsung 870 EVO 1 To",           "prix": "70 €",  "lect": "560 MB/s",   "ecrit": "530 MB/s"},
            {"nom": "Crucial MX500 1 To",             "prix": "60 €",  "lect": "560 MB/s",   "ecrit": "510 MB/s"},
            {"nom": "WD Blue SA510 1 To",             "prix": "58 €",  "lect": "560 MB/s",   "ecrit": "510 MB/s"},
            {"nom": "Seagate Barracuda 510 1 To",     "prix": "55 €",  "lect": "560 MB/s",   "ecrit": "540 MB/s"},
        ],
        "2To": [
            {"nom": "Samsung 870 EVO 2 To",           "prix": "120 €", "lect": "560 MB/s",   "ecrit": "530 MB/s"},
            {"nom": "Crucial MX500 2 To",             "prix": "105 €", "lect": "560 MB/s",   "ecrit": "510 MB/s"},
            {"nom": "WD Blue SA510 2 To",             "prix": "100 €", "lect": "560 MB/s",   "ecrit": "510 MB/s"},
            {"nom": "Seagate Barracuda 510 2 To",     "prix": "98 €",  "lect": "560 MB/s",   "ecrit": "540 MB/s"},
        ],
    },
}

# ── Structures de données ─────────────────────────────────────────────────────
@dataclass
class DisqueInfo:
    index: int
    modele: str
    taille_go: float
    interface: str
    type_media: str
    bus_type: str
    sante: str = "Inconnue"

@dataclass
class AnalyseResult:
    disques: list = field(default_factory=list)
    carte_mere: dict = field(default_factory=dict)
    processeur: dict = field(default_factory=dict)
    slots_m2_total: int = 0
    slots_sata_total: int = 0
    slots_m2_libres: int = 0
    slots_sata_libres: int = 0
    interfaces_detectees: list = field(default_factory=list)
    recommandations: list = field(default_factory=list)

# ── Fonctions PowerShell ──────────────────────────────────────────────────────
def run_ps(cmd: str) -> str:
    """Exécute une commande PowerShell et retourne la sortie."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip()
    except Exception:
        return ""

def get_physical_disks() -> list[dict]:
    """Récupère les disques physiques via PowerShell."""
    ps_cmd = """
    Get-PhysicalDisk | Select-Object -Property DeviceId, FriendlyName, MediaType, BusType,
        @{N='SizeGB';E={[math]::Round($_.Size/1GB,1)}}, HealthStatus |
    ConvertTo-Json -Depth 3
    """
    raw = run_ps(ps_cmd)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return []

def get_storage_controllers() -> list[dict]:
    """Récupère les contrôleurs de stockage."""
    ps_cmd = """
    Get-WmiObject Win32_SCSIController |
    Select-Object Name, DeviceID |
    ConvertTo-Json -Depth 2
    """
    raw = run_ps(ps_cmd)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else [data]
    except Exception:
        return []

def get_disk_partitions_info() -> list[dict]:
    """Récupère les infos sur les partitions."""
    ps_cmd = """
    Get-Partition | Select-Object DiskNumber, PartitionNumber, Size, DriveLetter |
    ConvertTo-Json -Depth 2
    """
    raw = run_ps(ps_cmd)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else [data]
    except Exception:
        return []

def detect_m2_slots_from_board(board_name: str, board_manufacturer: str) -> dict:
    """
    Estime le nombre de slots M.2 selon la gamme de la carte mère.
    Heuristique basée sur le nom du modèle.
    """
    name = (board_name + " " + board_manufacturer).upper()

    # Cartes haut de gamme (Z790, X670, B760, etc.)
    high_end = any(x in name for x in ["Z790", "Z690", "X670", "X570", "X470", "B760", "B660", "ROG", "STRIX", "AORUS", "MEG", "ACE", "APEX"])
    mid_range = any(x in name for x in ["B550", "B450", "B660", "B760", "PRIME", "TUF", "PRO", "PLUS"])

    if high_end:
        return {"m2_total": 4, "sata_total": 6, "note": "Carte haut de gamme (estimé)"}
    elif mid_range:
        return {"m2_total": 2, "sata_total": 4, "note": "Carte milieu de gamme (estimé)"}
    else:
        return {"m2_total": 1, "sata_total": 4, "note": "Estimation par défaut"}

def detect_pcie_generation(cpu_name: str) -> str:
    """Détecte la génération PCIe supportée selon le processeur."""
    cpu = cpu_name.upper()
    # Intel 12e/13e/14e gen → PCIe 5.0 / 4.0
    if any(x in cpu for x in ["I9-1", "I7-1", "I5-1", "I3-1"]):
        gen = cpu[cpu.find("I")+3:cpu.find("I")+6] if "I" in cpu else ""
        try:
            num = int(gen[:2])
            if num >= 12:
                return "PCIe 5.0 / 4.0"
            elif num >= 10:
                return "PCIe 4.0 / 3.0"
            else:
                return "PCIe 3.0"
        except Exception:
            pass
    # AMD Ryzen 7000 → PCIe 5.0 / 4.0
    if "RYZEN" in cpu:
        if "7" in cpu and any(x in cpu for x in ["7600","7700","7800","7900","7950"]):
            return "PCIe 5.0 / 4.0"
        elif any(x in cpu for x in ["5600","5700","5800","5900","5950","3600","3700","3800","3900"]):
            return "PCIe 4.0 / 3.0"
    return "PCIe 3.0 (estimé)"

# ── Analyse principale ────────────────────────────────────────────────────────
def analyser_configuration() -> AnalyseResult:
    result = AnalyseResult()
    c = wmi.WMI()

    # ── 1. Carte mère ─────────────────────────────────────────────────────────
    print(f"  {DIM}Lecture de la carte mère...{RST}")
    try:
        boards = c.Win32_BaseBoard()
        if boards:
            b = boards[0]
            result.carte_mere = {
                "fabricant": b.Manufacturer or "Inconnu",
                "modele":    b.Product or "Inconnu",
                "version":   b.Version or "",
            }
    except Exception as e:
        result.carte_mere = {"fabricant": "Erreur", "modele": str(e), "version": ""}

    # ── 2. Processeur ─────────────────────────────────────────────────────────
    print(f"  {DIM}Lecture du processeur...{RST}")
    try:
        cpus = c.Win32_Processor()
        if cpus:
            p = cpus[0]
            result.processeur = {
                "nom":    p.Name.strip() if p.Name else "Inconnu",
                "coeurs": p.NumberOfCores or 0,
                "pcie":   detect_pcie_generation(p.Name or ""),
            }
    except Exception:
        result.processeur = {"nom": "Inconnu", "coeurs": 0, "pcie": "Inconnu"}

    # ── 3. Disques physiques ──────────────────────────────────────────────────
    print(f"  {DIM}Analyse des disques...{RST}")
    raw_disks = get_physical_disks()

    if not raw_disks:
        # Fallback WMI
        try:
            for disk in c.Win32_DiskDrive():
                raw_disks.append({
                    "DeviceId":     disk.Index,
                    "FriendlyName": disk.Caption,
                    "MediaType":    "Unspecified",
                    "BusType":      "Unknown",
                    "SizeGB":       round(int(disk.Size or 0) / 1e9, 1),
                    "HealthStatus": "Unknown",
                })
        except Exception:
            pass

    bus_detectes = set()
    for d in raw_disks:
        bus  = str(d.get("BusType", "Unknown"))
        media = str(d.get("MediaType", "Unspecified"))
        taille = float(d.get("SizeGB", 0))
        nom    = str(d.get("FriendlyName", "Inconnu"))
        sante  = str(d.get("HealthStatus", "Unknown"))

        # Normalisation BusType numérique (PowerShell retourne parfois un int)
        BUS_MAP = {
            "0": "Unknown", "1": "SCSI", "2": "ATAPI", "3": "ATA",
            "4": "IEEE 1394", "5": "SSA", "6": "Fibre Channel",
            "7": "USB", "8": "RAID", "9": "iSCSI", "10": "SAS",
            "11": "SATA", "12": "SD", "13": "MMC", "14": "Virtual",
            "15": "FileBackedVirtual", "16": "Spaces", "17": "NVMe",
            "18": "SCM", "19": "UFS",
        }
        if bus.isdigit():
            bus = BUS_MAP.get(bus, bus)

        MEDIA_MAP = {
            "0": "Unspecified", "1": "HDD", "2": "SSD", "3": "SCM",
            "3": "Optane",
        }
        if media.isdigit():
            media = MEDIA_MAP.get(media, media)

        bus_detectes.add(bus)
        di = DisqueInfo(
            index=len(result.disques),
            modele=nom,
            taille_go=taille,
            interface=bus,
            type_media=media,
            bus_type=bus,
            sante=sante,
        )
        result.disques.append(di)

    result.interfaces_detectees = list(bus_detectes)

    # ── 4. Estimation des slots disponibles ───────────────────────────────────
    slots = detect_m2_slots_from_board(
        result.carte_mere.get("modele", ""),
        result.carte_mere.get("fabricant", "")
    )
    result.slots_m2_total   = slots["m2_total"]
    result.slots_sata_total  = slots["sata_total"]

    # Compter les disques NVMe et SATA actuels
    nvme_count = sum(1 for d in result.disques if "NVMe" in d.bus_type or d.bus_type == "17")
    sata_count = sum(1 for d in result.disques if "SATA" in d.bus_type or d.bus_type == "11")

    result.slots_m2_libres  = max(0, result.slots_m2_total - nvme_count)
    result.slots_sata_libres = max(0, result.slots_sata_total - sata_count)

    return result

# ── Génération des recommandations ───────────────────────────────────────────
def generer_recommandations(result: AnalyseResult) -> list[dict]:
    recs = []
    pcie = result.processeur.get("pcie", "PCIe 3.0")

    if result.slots_m2_libres > 0:
        if "5.0" in pcie or "4.0" in pcie:
            recs.append({"type": "M.2 NVMe PCIe 4.0", "raison": f"Slot M.2 libre + CPU {pcie}"})
        else:
            recs.append({"type": "M.2 NVMe PCIe 3.0", "raison": "Slot M.2 libre (PCIe 3.0)"})
        recs.append({"type": "M.2 SATA", "raison": "Alternative économique sur slot M.2"})

    if result.slots_sata_libres > 0:
        recs.append({"type": 'SATA 2.5"', "raison": "Port SATA disponible"})

    return recs

# ── Affichage ─────────────────────────────────────────────────────────────────
def sep(char="─", width=72):
    print(Fore.BLUE + char * width + RST)

def titre(texte):
    pad = (72 - len(texte) - 4) // 2
    print()
    print(TITLE + " " * pad + "  " + texte + "  " + " " * pad + RST)
    print()

def afficher_resultats(result: AnalyseResult):
    os.system("cls")

    print()
    print(TITLE + "  💿  ANALYSEUR DE CONFIGURATION - AJOUT SSD  💿  " + RST)
    print()

    # ── Section 1 : Matériel détecté ─────────────────────────────────────────
    titre("1 · MATÉRIEL DÉTECTÉ")

    board = result.carte_mere
    cpu   = result.processeur
    board_rows = [
        ["Carte mère",   f"{board.get('fabricant','')} {board.get('modele','')} {board.get('version','')}".strip()],
        ["Processeur",   cpu.get('nom', 'Inconnu')],
        ["Cœurs CPU",    str(cpu.get('coeurs', '?'))],
        ["PCIe supporté",cpu.get('pcie', '?')],
    ]
    print(tabulate(board_rows, tablefmt="rounded_outline",
                   headers=["Composant", "Détail"], colalign=("right", "left")))

    # ── Section 2 : Disques actuels ───────────────────────────────────────────
    titre("2 · DISQUES ACTUELLEMENT INSTALLÉS")
    if result.disques:
        disk_rows = []
        for d in result.disques:
            sante_c = (OK if "Healthy" in d.sante else WARN if d.sante == "Unknown" else ERR)
            disk_rows.append([
                f"#{d.index}",
                d.modele,
                f"{d.taille_go} Go",
                d.interface,
                d.type_media,
                sante_c + d.sante + RST,
            ])
        print(tabulate(disk_rows, tablefmt="rounded_outline",
                       headers=["#", "Modèle", "Taille", "Interface", "Média", "Santé"]))
    else:
        print(WARN + "  Aucun disque détecté (droits administrateur requis)" + RST)

    # ── Section 3 : Disponibilité des emplacements ───────────────────────────
    titre("3 · DISPONIBILITÉ DES EMPLACEMENTS")

    def slot_icon(n): return (OK + "✔ OUI" if n > 0 else ERR + "✘ NON") + RST

    slot_rows = [
        ["Slots M.2 (NVMe/SATA)",
         str(result.slots_m2_total),
         str(result.slots_m2_libres),
         slot_icon(result.slots_m2_libres)],
        ["Ports SATA (2.5\")",
         str(result.slots_sata_total),
         str(result.slots_sata_libres),
         slot_icon(result.slots_sata_libres)],
    ]
    print(tabulate(slot_rows, tablefmt="rounded_outline",
                   headers=["Type d'emplacement", "Total estimé", "Disponibles", "Ajout possible?"]))

    print()
    print(WARN + "  ⚠  Les slots sont estimés d'après le modèle de carte mère.")
    print("     Vérifiez le manuel de votre carte mère pour confirmer." + RST)

    # ── Section 4 : Recommandations ───────────────────────────────────────────
    titre("4 · TYPE D'INTERFACE RECOMMANDÉ")
    recs = generer_recommandations(result)

    # Critères de classement par type d'interface
    INTERFACE_DETAILS = {
        "M.2 NVMe PCIe 4.0": {
            "stars":      "★★★",
            "vitesse":    "3 500 – 7 300 MB/s",
            "format":     "M.2 2280 (carte)",
            "prix":       "€€€",
            "ideal_pour": "OS, jeux, montage vidéo",
            "limite":     "Requiert slot M.2 + CPU PCIe 4.0",
        },
        "M.2 NVMe PCIe 3.0": {
            "stars":      "★★☆",
            "vitesse":    "1 700 – 3 500 MB/s",
            "format":     "M.2 2280 (carte)",
            "prix":       "€€",
            "ideal_pour": "OS, jeux, usage général",
            "limite":     "Requiert slot M.2 NVMe",
        },
        "M.2 SATA": {
            "stars":      "★★☆",
            "vitesse":    "500 – 560 MB/s",
            "format":     "M.2 2280 (carte)",
            "prix":       "€€",
            "ideal_pour": "Stockage secondaire, budget",
            "limite":     "Slot M.2 doit supporter SATA (vérifier manuel)",
        },
        'SATA 2.5"': {
            "stars":      "★☆☆",
            "vitesse":    "500 – 560 MB/s",
            "format":     "2.5\" (boîtier classique)",
            "prix":       "€",
            "ideal_pour": "Upgrade depuis un HDD, stockage",
            "limite":     "Besoin d'une baie 2.5\" et d'un câble SATA libre",
        },
    }

    if not recs:
        print(ERR + "  ✘ Aucun emplacement disponible détecté." + RST)
        print(DIM + "    → Envisagez un SSD externe USB-C / Thunderbolt." + RST)
    else:
        rec_rows = []
        for i, r in enumerate(recs, 1):
            d = INTERFACE_DETAILS.get(r["type"], {})
            rec_rows.append([
                f"{INFO}{i}{RST}",
                f"{OK}{r['type']}{RST}",
                d.get("stars", "?"),
                d.get("vitesse", "?"),
                d.get("format", "?"),
                d.get("prix", "?"),
                d.get("ideal_pour", "?"),
                f"{WARN}{d.get('limite', '')}{RST}",
            ])
        print(tabulate(
            rec_rows,
            tablefmt="rounded_outline",
            headers=["#", "Interface", "Perf.", "Vitesse max", "Format", "Coût", "Idéal pour", "Contrainte"],
        ))
        print()
        print(f"  {DIM}Perf. : ★★★ = très rapide  ★★☆ = rapide  ★☆☆ = standard{RST}")
        print(f"  {DIM}Coût  : €€€ = premium       €€  = milieu   €   = économique{RST}")

    # ── Section 5 : Exemples de SSD ───────────────────────────────────────────
    titre("5 · EXEMPLES DE SSD 1 To ET 2 To")

    types_a_afficher = [r["type"] for r in recs] if recs else list(SSD_CATALOG.keys())

    for itype in types_a_afficher[:3]:    # On limite à 3 types pour lisibilité
        if itype not in SSD_CATALOG:
            continue
        sep("·")
        print(f"  {INFO}▸ {itype}{RST}")
        sep("·")

        for capacite in ["1To", "2To"]:
            print(f"\n  {WARN}{capacite.replace('To',' To')}{RST}")
            ssd_rows = []
            for ssd in SSD_CATALOG[itype][capacite]:
                ssd_rows.append([
                    ssd["nom"],
                    ssd["lect"],
                    ssd["ecrit"],
                    OK + ssd["prix"] + RST,
                ])
            print(tabulate(ssd_rows, tablefmt="simple",
                           headers=["Modèle", "Lecture", "Écriture", "Prix indicatif"],
                           colalign=("left","right","right","right")))
        print()

    # ── Footer ────────────────────────────────────────────────────────────────
    sep("═")
    print(f"  {DIM}Prix indicatifs constatés sur le marché européen (2025).")
    print(f"  Vérifiez les disponibilités et prix actuels chez votre revendeur.")
    print(f"  Script exécuté sur : {platform.node()} — {platform.version()}{RST}")
    sep("═")
    print()

# ── Génération du rapport PDF ─────────────────────────────────────────────────
def generer_pdf(result: AnalyseResult, recs: list, chemin: str = None) -> str:
    """Génère un rapport PDF complet de l'analyse."""
    import datetime
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable, PageBreak)

    if chemin is None:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              f"analyse_ssd_{ts}.pdf")

    # ── Couleurs ──────────────────────────────────────────────────────────────
    BLEU      = colors.HexColor("#1A3A5C")
    BLEU_CIEL = colors.HexColor("#2E86C1")
    VERT      = colors.HexColor("#1E8449")
    ORANGE    = colors.HexColor("#D35400")
    GRIS_F    = colors.HexColor("#F2F3F4")
    GRIS_M    = colors.HexColor("#D5D8DC")
    BLANC     = colors.white
    NOIR      = colors.HexColor("#1C1C1C")

    # ── Styles ────────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def style(name, **kw):
        return ParagraphStyle(name, **kw)

    s_titre = style("Titre",       fontSize=22, textColor=BLANC,     alignment=TA_CENTER,
                    fontName="Helvetica-Bold", spaceAfter=2)
    s_sous  = style("SousTitre",   fontSize=11, textColor=GRIS_M,    alignment=TA_CENTER,
                    fontName="Helvetica", spaceAfter=4)
    s_h1    = style("H1",          fontSize=13, textColor=BLEU,      fontName="Helvetica-Bold",
                    spaceBefore=12, spaceAfter=4, borderPad=2)
    s_body  = style("Body",        fontSize=9,  textColor=NOIR,      fontName="Helvetica",
                    spaceAfter=3, leading=13)
    s_note  = style("Note",        fontSize=8,  textColor=colors.HexColor("#7F8C8D"),
                    fontName="Helvetica-Oblique", spaceAfter=6)
    s_ok    = style("OK",          fontSize=9,  textColor=VERT,      fontName="Helvetica-Bold")
    s_warn  = style("Warn",        fontSize=9,  textColor=ORANGE,    fontName="Helvetica-Bold")

    W = A4[0] - 30*mm   # largeur utile

    def entete_section(texte):
        """Barre de titre de section."""
        t = Table([[Paragraph(texte, style("Hx", fontSize=11, textColor=BLANC,
                    fontName="Helvetica-Bold", spaceAfter=0))]], colWidths=[W])
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,-1), BLEU),
            ("TOPPADDING",  (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
        ]))
        return t

    def tableau(headers, rows, col_widths=None, zebra=True):
        """Tableau générique avec style cohérent."""
        data = [[Paragraph(f"<b>{h}</b>", style("TH", fontSize=8, textColor=BLANC,
                 fontName="Helvetica-Bold", spaceAfter=0)) for h in headers]]
        for row in rows:
            data.append([Paragraph(str(c), s_body) if not isinstance(c, Paragraph) else c
                         for c in row])
        t = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
        ts_cmds = [
            ("BACKGROUND",    (0,0), (-1,0),  BLEU_CIEL),
            ("TEXTCOLOR",     (0,0), (-1,0),  BLANC),
            ("GRID",          (0,0), (-1,-1), 0.4, GRIS_M),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [BLANC, GRIS_F] if zebra else [BLANC]),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
            ("FONTSIZE",      (0,0), (-1,-1), 8),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]
        t.setStyle(TableStyle(ts_cmds))
        return t

    # ── Construction du document ──────────────────────────────────────────────
    story = []

    # ▸ Bandeau titre
    now = datetime.datetime.now().strftime("%d/%m/%Y à %H:%M")
    header_data = [[
        Paragraph("ANALYSE DE CONFIGURATION", s_titre),
        Paragraph("Rapport d'ajout SSD", s_sous),
        Paragraph(f"Généré le {now}", s_note),
    ]]
    header_tbl = Table(header_data, colWidths=[W])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), BLEU),
        ("TOPPADDING",    (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 6*mm))

    # ── 1. Matériel détecté ───────────────────────────────────────────────────
    story.append(entete_section("1 · Matériel détecté"))
    story.append(Spacer(1, 2*mm))
    board = result.carte_mere
    cpu   = result.processeur
    hw_rows = [
        ["Carte mère",    f"{board.get('fabricant','')} {board.get('modele','')} {board.get('version','')}".strip()],
        ["Processeur",    cpu.get("nom", "Inconnu")],
        ["Coeurs CPU",    str(cpu.get("coeurs", "?"))],
        ["PCIe supporté", cpu.get("pcie", "?")],
        ["Hostname",      platform.node()],
    ]
    story.append(tableau(["Composant", "Détail"], hw_rows, col_widths=[50*mm, W-50*mm]))
    story.append(Spacer(1, 4*mm))

    # ── 2. Disques installés ──────────────────────────────────────────────────
    story.append(entete_section("2 · Disques actuellement installés"))
    story.append(Spacer(1, 2*mm))
    if result.disques:
        disk_rows = []
        for d in result.disques:
            sante_style = s_ok if "Healthy" in d.sante else s_warn
            disk_rows.append([
                f"#{d.index}", d.modele, f"{d.taille_go} Go",
                d.interface, d.type_media,
                Paragraph(d.sante, sante_style),
            ])
        story.append(tableau(
            ["#", "Modèle", "Taille", "Interface", "Média", "Santé"],
            disk_rows,
            col_widths=[8*mm, 62*mm, 18*mm, 22*mm, 18*mm, 22*mm],
        ))
    else:
        story.append(Paragraph("Aucun disque détecté (droits administrateur requis).", s_warn))
    story.append(Spacer(1, 4*mm))

    # ── 3. Emplacements disponibles ───────────────────────────────────────────
    story.append(entete_section("3 · Disponibilité des emplacements"))
    story.append(Spacer(1, 2*mm))

    def dispo(n):
        return Paragraph("✔ OUI" if n > 0 else "✘ NON",
                         s_ok if n > 0 else s_warn)

    slot_rows = [
        ["Slots M.2 (NVMe/SATA)",
         str(result.slots_m2_total), str(result.slots_m2_libres), dispo(result.slots_m2_libres)],
        ["Ports SATA (2.5\")",
         str(result.slots_sata_total), str(result.slots_sata_libres), dispo(result.slots_sata_libres)],
    ]
    story.append(tableau(
        ["Type d'emplacement", "Total estimé", "Disponibles", "Ajout possible ?"],
        slot_rows,
        col_widths=[70*mm, 30*mm, 30*mm, 30*mm],
    ))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "⚠ Les slots sont estimés d'après le modèle de carte mère. "
        "Vérifiez le manuel de votre carte mère pour confirmer.", s_note))
    story.append(Spacer(1, 4*mm))

    # ── 4. Recommandations d'interface ───────────────────────────────────────
    story.append(entete_section("4 · Type d'interface recommandé"))
    story.append(Spacer(1, 2*mm))

    INTERFACE_DETAILS = {
        "M.2 NVMe PCIe 4.0": {"stars": "★★★", "vitesse": "3 500 – 7 300 MB/s",
                               "format": "M.2 2280", "prix": "€€€",
                               "ideal": "OS, jeux, montage vidéo",
                               "limite": "Requiert slot M.2 + CPU PCIe 4.0"},
        "M.2 NVMe PCIe 3.0": {"stars": "★★☆", "vitesse": "1 700 – 3 500 MB/s",
                               "format": "M.2 2280", "prix": "€€",
                               "ideal": "OS, jeux, usage général",
                               "limite": "Requiert slot M.2 NVMe"},
        "M.2 SATA":           {"stars": "★★☆", "vitesse": "500 – 560 MB/s",
                               "format": "M.2 2280", "prix": "€€",
                               "ideal": "Stockage secondaire, budget",
                               "limite": "Vérifier compatibilité SATA du slot"},
        'SATA 2.5"':          {"stars": "★☆☆", "vitesse": "500 – 560 MB/s",
                               "format": '2.5"', "prix": "€",
                               "ideal": "Upgrade HDD, stockage",
                               "limite": 'Baie 2.5" + câble SATA libre requis'},
    }

    if recs:
        rec_rows = []
        for i, r in enumerate(recs, 1):
            d = INTERFACE_DETAILS.get(r["type"], {})
            rec_rows.append([
                str(i), r["type"], d.get("stars","?"),
                d.get("vitesse","?"), d.get("format","?"), d.get("prix","?"),
                d.get("ideal","?"),
                Paragraph(d.get("limite",""), s_note),
            ])
        story.append(tableau(
            ["#", "Interface", "Perf.", "Vitesse max", "Format", "Coût", "Idéal pour", "Contrainte"],
            rec_rows,
            col_widths=[6*mm, 32*mm, 14*mm, 30*mm, 16*mm, 12*mm, 32*mm, 28*mm],
        ))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(
            "Perf. : ★★★ = très rapide  |  ★★☆ = rapide  |  ★☆☆ = standard  —  "
            "Coût : €€€ = premium  |  €€ = milieu  |  € = économique", s_note))
    else:
        story.append(Paragraph("Aucun emplacement disponible détecté. "
                                "Envisagez un SSD externe USB-C / Thunderbolt.", s_warn))
    story.append(Spacer(1, 4*mm))

    # ── 5. Catalogue SSD ──────────────────────────────────────────────────────
    story.append(entete_section("5 · Exemples de SSD 1 To et 2 To"))

    types_pdf = [r["type"] for r in recs] if recs else list(SSD_CATALOG.keys())
    for itype in types_pdf[:3]:
        if itype not in SSD_CATALOG:
            continue
        story.append(Spacer(1, 3*mm))
        # Sous-titre interface
        st = Table([[Paragraph(f"  {itype}", style("SI", fontSize=10, textColor=BLEU,
                     fontName="Helvetica-Bold", spaceAfter=0))]],
                   colWidths=[W])
        st.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), GRIS_F),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("BOX",           (0,0),(-1,-1), 0.8, BLEU_CIEL),
        ]))
        story.append(st)
        story.append(Spacer(1, 1*mm))

        for capacite in ["1To", "2To"]:
            story.append(Paragraph(f"<b>{capacite.replace('To',' To')}</b>", s_body))
            ssd_rows = [
                [s["nom"], s["lect"], s["ecrit"],
                 Paragraph(f"<b>{s['prix']}</b>",
                           style("P", fontSize=9, textColor=VERT, fontName="Helvetica-Bold"))]
                for s in SSD_CATALOG[itype][capacite]
            ]
            story.append(tableau(
                ["Modèle", "Lecture", "Écriture", "Prix indicatif"],
                ssd_rows,
                col_widths=[80*mm, 28*mm, 28*mm, 28*mm],
            ))
            story.append(Spacer(1, 2*mm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width=W, color=GRIS_M))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "Prix indicatifs constatés sur le marché européen (2025). "
        "Vérifiez les disponibilités et prix actuels chez votre revendeur. "
        f"Rapport généré sur : {platform.node()} — {platform.version()}", s_note))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        chemin, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
        title="Analyse SSD Upgrade",
        author="analyse_ssd_upgrade.py",
    )
    doc.build(story)
    return chemin


# ── Point d'entrée ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyse la configuration matérielle pour l'ajout d'un SSD."
    )
    parser.add_argument(
        "--pdf",
        metavar="NOM_FICHIER",
        help="Nom du fichier PDF à générer (ex: rapport_pc_bureau). "
             "L'extension .pdf est ajoutée automatiquement si absente. "
             "Le fichier est créé dans le même dossier que le script.",
        default=None,
    )
    args = parser.parse_args()
    # Vérification OS
    if platform.system() != "Windows":
        print(ERR + "Ce script est conçu pour Windows uniquement." + RST)
        sys.exit(1)

    # Recommander les droits admin
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False

    if not is_admin:
        print(WARN + "\n⚠  Pour des résultats optimaux, exécutez ce script")
        print("   en tant qu'Administrateur (clic droit → Exécuter en tant qu'administrateur).\n" + RST)

    print()
    print(INFO + "Analyse de la configuration matérielle en cours..." + RST)

    try:
        result = analyser_configuration()
        afficher_resultats(result)

        # ── Génération du PDF ─────────────────────────────────────────────────
        recs = generer_recommandations(result)
        print(INFO + "\nGénération du rapport PDF en cours..." + RST)
        try:
            # Construire le chemin PDF depuis l'argument ou un nom horodaté
            if args.pdf:
                nom = args.pdf if args.pdf.lower().endswith(".pdf") else args.pdf + ".pdf"
                chemin_pdf = os.path.join(os.path.dirname(os.path.abspath(__file__)), nom)
            else:
                chemin_pdf = None   # generer_pdf() utilisera le nom horodaté par défaut

            chemin_pdf = generer_pdf(result, recs, chemin_pdf)
            print(OK + f"  ✔ Rapport PDF généré : {chemin_pdf}" + RST)
            # Ouverture automatique du PDF
            os.startfile(chemin_pdf)
        except Exception as pdf_err:
            print(WARN + f"  ⚠ Impossible de générer le PDF : {pdf_err}" + RST)

    except KeyboardInterrupt:
        print("\nInterrompu.")
    except Exception as e:
        print(ERR + f"\nErreur inattendue : {e}" + RST)
        import traceback
        traceback.print_exc()

    input(DIM + "\nAppuyez sur Entrée pour quitter..." + RST)
