"""
csv_editor.py
-------------
Petit éditeur graphique (Tkinter) pour remplir/modifier confortablement
les fichiers CSV de lieux utilisés par geocode.py / csv_to_html.py.

Évite l'édition manuelle du CSV (champs longs, accents, séparateur ";",
guillemets) en proposant un formulaire avec liste à gauche et détail
à droite.

Usage :
    python csv_editor.py [chemin/vers/fichier.csv]

Si aucun fichier n'est passé en argument, l'éditeur s'ouvre vide et
propose "Ouvrir..." / "Nouveau fichier...".
"""

import os
import sys
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import utils  # SEPARATEUR, charger_categories, detecter_encodage

# ─────────────────────────────────────────────────────────────
# Thème sombre / violet
# ─────────────────────────────────────────────────────────────
BG          = "#1a1625"
PANEL       = "#221b33"
PANEL_2     = "#2a2140"
ENTRY_BG    = "#2d2440"
BORDER      = "#3d3258"
ACCENT      = "#9b59b6"
ACCENT_HOVR = "#b06fd1"
ACCENT_DARK = "#6c3483"
TEXT        = "#e8e0f5"
SUBTEXT     = "#a89cc8"
SUCCESS     = "#27ae60"
ERROR       = "#e74c3c"
WARN        = "#f39c12"

FONT_BASE   = ("Segoe UI", 10)
FONT_BOLD   = ("Segoe UI", 10, "bold")
FONT_TITLE  = ("Segoe UI", 13, "bold")
FONT_MONO   = ("Consolas", 9)

# Colonnes du CSV, dans l'ordre exact attendu par utils.lire_csv
COLONNES = ["categorie", "nom", "adresse", "note", "description",
            "transport", "url", "lon", "lat", "photo"]


# ─────────────────────────────────────────────────────────────
# Modèle de données (lecture / écriture du CSV)
# ─────────────────────────────────────────────────────────────
class Document:
    """Représente le fichier CSV en cours d'édition (pays/région + lieux)."""

    def __init__(self):
        self.chemin = None
        self.pays = ""
        self.region = ""
        self.lieux = []  # liste de dicts (mêmes clés que COLONNES)

    def nouveau(self):
        self.chemin = None
        self.pays = ""
        self.region = ""
        self.lieux = []

    def charger(self, chemin):
        enc = utils.detecter_encodage(chemin)
        with open(chemin, newline="", encoding=enc) as f:
            lignes = list(csv.reader(f, delimiter=utils.SEPARATEUR))

        pays, region = "", ""
        debut = 0
        if lignes and lignes[0] and lignes[0][0].strip().lower() in ("pays", "country"):
            if len(lignes) > 1:
                vals = lignes[1]
                pays   = vals[0].strip() if len(vals) > 0 else ""
                region = vals[1].strip() if len(vals) > 1 else ""
            debut = 2
            while debut < len(lignes) and not any(c.strip() for c in lignes[debut]):
                debut += 1

        lieux = []
        if debut < len(lignes):
            entete = [c.strip().lower() for c in lignes[debut]]
            debut += 1
            for row in lignes[debut:]:
                if not any(c.strip() for c in row):
                    continue
                d = {col: (row[i].strip() if i < len(row) else "")
                     for i, col in enumerate(entete)}
                lieux.append({col: d.get(col, "") for col in COLONNES})

        self.chemin = chemin
        self.pays = pays
        self.region = region
        self.lieux = lieux

    def sauvegarder(self, chemin=None):
        chemin = chemin or self.chemin
        if not chemin:
            raise ValueError("Aucun chemin de fichier")

        with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=utils.SEPARATEUR)
            w.writerow(["pays", "région"] + [""] * 8)
            w.writerow([self.pays, self.region] + [""] * 8)
            w.writerow([""] * 10)
            w.writerow(COLONNES)
            for lieu in self.lieux:
                w.writerow([lieu.get(col, "") for col in COLONNES])

        self.chemin = chemin


# ─────────────────────────────────────────────────────────────
# Widgets utilitaires (style sombre cohérent)
# ─────────────────────────────────────────────────────────────
def styliser_ttk(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure("TFrame", background=PANEL)
    style.configure("Main.TFrame", background=BG)

    style.configure("TLabel", background=PANEL, foreground=TEXT, font=FONT_BASE)
    style.configure("Sub.TLabel", background=PANEL, foreground=SUBTEXT, font=FONT_BASE)
    style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_TITLE)

    style.configure("TEntry", fieldbackground=ENTRY_BG, foreground=TEXT,
                     insertcolor=TEXT, bordercolor=BORDER, lightcolor=BORDER,
                     darkcolor=BORDER, padding=6)
    style.map("TEntry", fieldbackground=[("focus", ENTRY_BG)])

    style.configure("TCombobox", fieldbackground=ENTRY_BG, background=ENTRY_BG,
                     foreground=TEXT, arrowcolor=TEXT, bordercolor=BORDER,
                     padding=5)
    style.map("TCombobox",
              fieldbackground=[("readonly", ENTRY_BG)],
              foreground=[("readonly", TEXT)])

    style.configure("Accent.TButton", background=ACCENT, foreground="white",
                     font=FONT_BOLD, padding=(12, 8), borderwidth=0)
    style.map("Accent.TButton", background=[("active", ACCENT_HOVR)])

    style.configure("Flat.TButton", background=PANEL_2, foreground=TEXT,
                     font=FONT_BASE, padding=(10, 6), borderwidth=0)
    style.map("Flat.TButton", background=[("active", BORDER)])

    style.configure("Danger.TButton", background="#5a2438", foreground="#ffb3c6",
                     font=FONT_BASE, padding=(10, 6), borderwidth=0)
    style.map("Danger.TButton", background=[("active", ERROR)])

    style.configure("Treeview", background=PANEL_2, fieldbackground=PANEL_2,
                     foreground=TEXT, rowheight=26, font=FONT_BASE, borderwidth=0)
    style.configure("Treeview.Heading", background=PANEL, foreground=SUBTEXT,
                     font=FONT_BOLD, borderwidth=0)
    style.map("Treeview", background=[("selected", ACCENT_DARK)],
              foreground=[("selected", "white")])

    style.configure("Vertical.TScrollbar", background=PANEL_2, troughcolor=BG,
                     bordercolor=BG, arrowcolor=TEXT)


def champ_label(parent, texte):
    lbl = ttk.Label(parent, text=texte, style="Sub.TLabel")
    lbl.pack(anchor="w", pady=(10, 2))
    return lbl


# ─────────────────────────────────────────────────────────────
# Application principale
# ─────────────────────────────────────────────────────────────
class App:
    def __init__(self, root, chemin_initial=None):
        self.root = root
        self.doc = Document()
        self.lieu_courant = None       # index dans self.doc.lieux, ou None
        self.modifie = False
        self.categories = utils.charger_categories()

        root.title("Éditeur de lieux — CSV")
        root.geometry("1180x720")
        root.minsize(900, 560)
        root.configure(bg=BG)
        styliser_ttk(root)

        self._construire_ui()
        self._rafraichir_titre()

        if chemin_initial and os.path.exists(chemin_initial):
            self._charger_fichier(chemin_initial)

        root.protocol("WM_DELETE_WINDOW", self._quitter)

    # ── Construction de l'interface ────────────────────────────
    def _construire_ui(self):
        # Barre du haut
        barre = tk.Frame(self.root, bg=BG)
        barre.pack(fill="x", padx=16, pady=(14, 6))

        tk.Label(barre, text="🗺  Éditeur de lieux", bg=BG, fg=TEXT,
                 font=FONT_TITLE).pack(side="left")

        boutons = tk.Frame(barre, bg=BG)
        boutons.pack(side="right")
        ttk.Button(boutons, text="Nouveau", style="Flat.TButton",
                   command=self._nouveau_fichier).pack(side="left", padx=4)
        ttk.Button(boutons, text="Ouvrir…", style="Flat.TButton",
                   command=self._ouvrir_fichier).pack(side="left", padx=4)
        ttk.Button(boutons, text="💾 Enregistrer", style="Accent.TButton",
                   command=self._enregistrer).pack(side="left", padx=4)

        # Ligne pays / région
        ligne_titre = tk.Frame(self.root, bg=BG)
        ligne_titre.pack(fill="x", padx=16, pady=(0, 10))
        tk.Label(ligne_titre, text="Pays :", bg=BG, fg=SUBTEXT, font=FONT_BASE).pack(side="left")
        self.var_pays = tk.StringVar()
        e_pays = ttk.Entry(ligne_titre, textvariable=self.var_pays, width=18)
        e_pays.pack(side="left", padx=(6, 18))
        self.var_pays.trace_add("write", lambda *a: self._marquer_modifie())

        tk.Label(ligne_titre, text="Région :", bg=BG, fg=SUBTEXT, font=FONT_BASE).pack(side="left")
        self.var_region = tk.StringVar()
        e_region = ttk.Entry(ligne_titre, textvariable=self.var_region, width=18)
        e_region.pack(side="left", padx=(6, 0))
        self.var_region.trace_add("write", lambda *a: self._marquer_modifie())

        # Corps : liste à gauche / formulaire à droite
        corps = tk.Frame(self.root, bg=BG)
        corps.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        corps.columnconfigure(0, weight=0, minsize=320)
        corps.columnconfigure(1, weight=1)
        corps.rowconfigure(0, weight=1)

        self._construire_liste(corps)
        self._construire_formulaire(corps)

        # Barre de statut
        self.var_statut = tk.StringVar(value="Prêt.")
        statut = tk.Label(self.root, textvariable=self.var_statut, bg=PANEL,
                           fg=SUBTEXT, anchor="w", font=("Segoe UI", 9), padx=12, pady=5)
        statut.pack(fill="x", side="bottom")

    def _construire_liste(self, parent):
        cadre = tk.Frame(parent, bg=PANEL)
        cadre.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        entete = tk.Frame(cadre, bg=PANEL)
        entete.pack(fill="x", padx=12, pady=12)
        tk.Label(entete, text="Lieux", bg=PANEL, fg=TEXT, font=FONT_BOLD).pack(side="left")
        self.var_compte = tk.StringVar(value="0")
        tk.Label(entete, textvariable=self.var_compte, bg=PANEL, fg=SUBTEXT,
                 font=FONT_BASE).pack(side="right")

        recherche = tk.Frame(cadre, bg=PANEL)
        recherche.pack(fill="x", padx=12, pady=(0, 8))
        self.var_recherche = tk.StringVar()
        self.var_recherche.trace_add("write", lambda *a: self._filtrer_liste())
        e = ttk.Entry(recherche, textvariable=self.var_recherche)
        e.pack(fill="x")
        e.insert(0, "")
        self._placeholder(e, "🔍 Filtrer…")

        cols = ("nom", "cat")
        self.tree = ttk.Treeview(cadre, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("nom", text="Nom")
        self.tree.heading("cat", text="Catégorie")
        self.tree.column("nom", width=190)
        self.tree.column("cat", width=100)
        self.tree.pack(fill="both", expand=True, padx=12)
        self.tree.bind("<<TreeviewSelect>>", self._on_select_liste)

        actions = tk.Frame(cadre, bg=PANEL)
        actions.pack(fill="x", padx=12, pady=12)
        ttk.Button(actions, text="➕ Nouveau lieu", style="Accent.TButton",
                   command=self._nouveau_lieu).pack(fill="x", pady=(0, 6))
        ligne = tk.Frame(actions, bg=PANEL)
        ligne.pack(fill="x")
        ttk.Button(ligne, text="⧉ Dupliquer", style="Flat.TButton",
                   command=self._dupliquer_lieu).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(ligne, text="🗑 Supprimer", style="Danger.TButton",
                   command=self._supprimer_lieu).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _construire_formulaire(self, parent):
        cadre_ext = tk.Frame(parent, bg=PANEL)
        cadre_ext.grid(row=0, column=1, sticky="nsew")

        canvas = tk.Canvas(cadre_ext, bg=PANEL, highlightthickness=0)
        vbar = ttk.Scrollbar(cadre_ext, orient="vertical", command=canvas.yview)
        cadre = tk.Frame(canvas, bg=PANEL)
        cadre.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=cadre, anchor="nw")
        canvas.configure(yscrollcommand=vbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")

        def _molette(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _molette)

        inner = tk.Frame(cadre, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=24, pady=18)

        self.var_nom = tk.StringVar()
        self.var_categorie = tk.StringVar()
        self.var_adresse = tk.StringVar()
        self.var_note = tk.StringVar()
        self.var_transport = tk.StringVar()
        self.var_url = tk.StringVar()
        self.var_lon = tk.StringVar()
        self.var_lat = tk.StringVar()
        self.var_photo = tk.StringVar()

        # Nom + catégorie
        ligne1 = tk.Frame(inner, bg=PANEL)
        ligne1.pack(fill="x")
        gauche = tk.Frame(ligne1, bg=PANEL)
        gauche.pack(side="left", fill="x", expand=True, padx=(0, 12))
        champ_label(gauche, "Nom du lieu")
        e_nom = ttk.Entry(gauche, textvariable=self.var_nom, font=FONT_BASE)
        e_nom.pack(fill="x", ipady=3)

        droite = tk.Frame(ligne1, bg=PANEL)
        droite.pack(side="left", fill="x", expand=True)
        champ_label(droite, "Catégorie")
        noms_cat = sorted(self.categories.keys())
        self.cb_categorie = ttk.Combobox(droite, textvariable=self.var_categorie,
                                          values=noms_cat, font=FONT_BASE)
        self.cb_categorie.pack(fill="x", ipady=3)

        champ_label(inner, "Adresse")
        ttk.Entry(inner, textvariable=self.var_adresse, font=FONT_BASE).pack(fill="x", ipady=3)

        champ_label(inner, "Note (ex : ⭐⭐⭐⭐ ou un commentaire court)")
        ttk.Entry(inner, textvariable=self.var_note, font=FONT_BASE).pack(fill="x", ipady=3)

        champ_label(inner, "Description")
        cadre_desc = tk.Frame(inner, bg=BORDER)
        cadre_desc.pack(fill="x")
        self.txt_description = tk.Text(cadre_desc, height=6, bg=ENTRY_BG, fg=TEXT,
                                        insertbackground=TEXT, font=FONT_BASE,
                                        wrap="word", relief="flat", padx=8, pady=8,
                                        highlightthickness=0, bd=0)
        self.txt_description.pack(fill="x", padx=1, pady=1)
        self.txt_description.bind("<<Modified>>", self._on_desc_modifiee)

        champ_label(inner, "Transport")
        ttk.Entry(inner, textvariable=self.var_transport, font=FONT_BASE).pack(fill="x", ipady=3)

        champ_label(inner, "Site web / URL")
        ttk.Entry(inner, textvariable=self.var_url, font=FONT_BASE).pack(fill="x", ipady=3)

        champ_label(inner, "Photo (chemin relatif au CSV)")
        ligne_photo = tk.Frame(inner, bg=PANEL)
        ligne_photo.pack(fill="x")
        ttk.Entry(ligne_photo, textvariable=self.var_photo, font=FONT_BASE).pack(
            side="left", fill="x", expand=True, ipady=3)
        ttk.Button(ligne_photo, text="Parcourir…", style="Flat.TButton",
                   command=self._choisir_photo).pack(side="left", padx=(8, 0))

        # Coordonnées (lecture/édition facultative — normalement remplies par geocode.py)
        champ_label(inner, "Coordonnées (laisser vide si non géocodé)")
        ligne_coord = tk.Frame(inner, bg=PANEL)
        ligne_coord.pack(fill="x")
        tk.Label(ligne_coord, text="lon", bg=PANEL, fg=SUBTEXT, font=FONT_BASE).pack(side="left")
        ttk.Entry(ligne_coord, textvariable=self.var_lon, width=14, font=FONT_BASE).pack(
            side="left", padx=(4, 16), ipady=3)
        tk.Label(ligne_coord, text="lat", bg=PANEL, fg=SUBTEXT, font=FONT_BASE).pack(side="left")
        ttk.Entry(ligne_coord, textvariable=self.var_lat, width=14, font=FONT_BASE).pack(
            side="left", padx=(4, 0), ipady=3)

        for var in (self.var_nom, self.var_categorie, self.var_adresse, self.var_note,
                    self.var_transport, self.var_url, self.var_photo,
                    self.var_lon, self.var_lat):
            var.trace_add("write", lambda *a: self._on_champ_modifie())

        self.inner_form = inner
        self._activer_formulaire(False)

    # ── Placeholder simple pour la recherche ────────────────────
    def _placeholder(self, entry, texte):
        entry.insert(0, texte)
        entry.config(foreground=SUBTEXT)

        def on_focus_in(_e):
            if entry.get() == texte:
                entry.delete(0, "end")
                entry.config(foreground=TEXT)

        def on_focus_out(_e):
            if not entry.get():
                entry.insert(0, texte)
                entry.config(foreground=SUBTEXT)

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    # ── Gestion fichier ─────────────────────────────────────────
    def _nouveau_fichier(self):
        if not self._confirmer_perte_modifs():
            return
        self.doc.nouveau()
        self.var_pays.set("")
        self.var_region.set("")
        self.lieu_courant = None
        self._activer_formulaire(False)
        self._rafraichir_liste()
        self._rafraichir_titre()
        self._statut("Nouveau fichier. Choisissez « Enregistrer » pour définir son emplacement.")

    def _ouvrir_fichier(self):
        if not self._confirmer_perte_modifs():
            return
        chemin = filedialog.askopenfilename(
            title="Ouvrir un fichier de lieux",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")])
        if chemin:
            self._charger_fichier(chemin)

    def _charger_fichier(self, chemin):
        try:
            self.doc.charger(chemin)
        except Exception as e:
            messagebox.showerror("Erreur de lecture", f"Impossible de lire ce fichier :\n{e}")
            return
        self.var_pays.set(self.doc.pays)
        self.var_region.set(self.doc.region)
        self.lieu_courant = None
        self._activer_formulaire(False)
        self._rafraichir_liste()
        self.modifie = False
        self._rafraichir_titre()
        self._statut(f"{len(self.doc.lieux)} lieu(x) chargé(s) depuis {os.path.basename(chemin)}.")

    def _enregistrer(self):
        self._valider_vers_modele()  # pousse le formulaire courant dans self.doc avant sauvegarde
        chemin = self.doc.chemin
        if not chemin:
            chemin = filedialog.asksaveasfilename(
                title="Enregistrer le fichier de lieux",
                defaultextension=".csv",
                filetypes=[("Fichiers CSV", "*.csv")])
            if not chemin:
                return
        try:
            self.doc.sauvegarder(chemin)
        except Exception as e:
            messagebox.showerror("Erreur d'enregistrement", f"Impossible d'enregistrer :\n{e}")
            return
        self.modifie = False
        self._rafraichir_titre()
        self._statut(f"✅ Enregistré : {chemin}")

    def _confirmer_perte_modifs(self):
        if not self.modifie:
            return True
        rep = messagebox.askyesnocancel(
            "Modifications non enregistrées",
            "Le fichier en cours contient des modifications non enregistrées.\n"
            "Voulez-vous les enregistrer avant de continuer ?")
        if rep is None:
            return False
        if rep:
            self._enregistrer()
        return True

    def _quitter(self):
        if self._confirmer_perte_modifs():
            self.root.destroy()

    # ── Gestion de la liste des lieux ───────────────────────────
    def _rafraichir_liste(self, filtre=""):
        self.tree.delete(*self.tree.get_children())
        filtre = filtre.strip().lower()
        for i, lieu in enumerate(self.doc.lieux):
            texte = f"{lieu.get('nom', '')} {lieu.get('categorie', '')} {lieu.get('adresse', '')}".lower()
            if filtre and filtre not in texte:
                continue
            nom = lieu.get("nom") or "(sans nom)"
            self.tree.insert("", "end", iid=str(i), values=(nom, lieu.get("categorie", "")))
        self.var_compte.set(str(len(self.doc.lieux)))

    def _filtrer_liste(self):
        valeur = self.var_recherche.get()
        if valeur == "🔍 Filtrer…":
            valeur = ""
        self._rafraichir_liste(valeur)

    def _on_select_liste(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self._valider_vers_modele(idx_precedent=self.lieu_courant)
        idx = int(sel[0])
        self.lieu_courant = idx
        self._charger_dans_formulaire(self.doc.lieux[idx])
        self._activer_formulaire(True)

    # ── Actions sur les lieux ───────────────────────────────────
    def _nouveau_lieu(self):
        self._valider_vers_modele(idx_precedent=self.lieu_courant)
        nouveau = {col: "" for col in COLONNES}
        nouveau["nom"] = "Nouveau lieu"
        self.doc.lieux.append(nouveau)
        self._marquer_modifie()
        self._rafraichir_liste()
        idx = len(self.doc.lieux) - 1
        self.tree.selection_set(str(idx))
        self.tree.see(str(idx))
        self.lieu_courant = idx
        self._charger_dans_formulaire(nouveau)
        self._activer_formulaire(True)

    def _dupliquer_lieu(self):
        if self.lieu_courant is None:
            messagebox.showinfo("Dupliquer", "Sélectionnez d'abord un lieu dans la liste.")
            return
        self._valider_vers_modele(idx_precedent=self.lieu_courant)
        copie = dict(self.doc.lieux[self.lieu_courant])
        copie["nom"] = (copie.get("nom") or "") + " (copie)"
        self.doc.lieux.insert(self.lieu_courant + 1, copie)
        self._marquer_modifie()
        self._rafraichir_liste()
        idx = self.lieu_courant + 1
        self.tree.selection_set(str(idx))
        self.tree.see(str(idx))
        self.lieu_courant = idx
        self._charger_dans_formulaire(copie)

    def _supprimer_lieu(self):
        if self.lieu_courant is None:
            messagebox.showinfo("Supprimer", "Sélectionnez d'abord un lieu dans la liste.")
            return
        lieu = self.doc.lieux[self.lieu_courant]
        if not messagebox.askyesno("Supprimer", f"Supprimer « {lieu.get('nom') or 'ce lieu'} » ?"):
            return
        del self.doc.lieux[self.lieu_courant]
        self.lieu_courant = None
        self._marquer_modifie()
        self._rafraichir_liste()
        self._activer_formulaire(False)
        self._vider_formulaire()

    # ── Formulaire ⇄ modèle ─────────────────────────────────────
    def _charger_dans_formulaire(self, lieu):
        self.var_nom.set(lieu.get("nom", ""))
        self.var_categorie.set(lieu.get("categorie", ""))
        self.var_adresse.set(lieu.get("adresse", ""))
        self.var_note.set(lieu.get("note", ""))
        self.var_transport.set(lieu.get("transport", ""))
        self.var_url.set(lieu.get("url", ""))
        self.var_photo.set(lieu.get("photo", ""))
        self.var_lon.set(lieu.get("lon", ""))
        self.var_lat.set(lieu.get("lat", ""))
        self.txt_description.delete("1.0", "end")
        self.txt_description.insert("1.0", lieu.get("description", ""))
        self.txt_description.edit_modified(False)

    def _vider_formulaire(self):
        for var in (self.var_nom, self.var_categorie, self.var_adresse, self.var_note,
                    self.var_transport, self.var_url, self.var_photo,
                    self.var_lon, self.var_lat):
            var.set("")
        self.txt_description.delete("1.0", "end")

    def _valider_vers_modele(self, idx_precedent=None):
        """Recopie le contenu du formulaire dans self.doc.lieux[idx]."""
        idx = self.lieu_courant if idx_precedent is None else idx_precedent
        if idx is None or idx >= len(self.doc.lieux):
            return
        self.doc.lieux[idx] = {
            "categorie":   self.var_categorie.get().strip(),
            "nom":         self.var_nom.get().strip(),
            "adresse":     self.var_adresse.get().strip(),
            "note":        self.var_note.get().strip(),
            "description": self.txt_description.get("1.0", "end-1c").strip(),
            "transport":   self.var_transport.get().strip(),
            "url":         self.var_url.get().strip(),
            "lon":         self.var_lon.get().strip(),
            "lat":         self.var_lat.get().strip(),
            "photo":       self.var_photo.get().strip(),
        }
        # Reflète le nom/catégorie modifiés dans la liste
        item = str(idx)
        if self.tree.exists(item):
            self.tree.item(item, values=(self.doc.lieux[idx]["nom"] or "(sans nom)",
                                          self.doc.lieux[idx]["categorie"]))

    def _activer_formulaire(self, actif):
        etat = "normal" if actif else "disabled"
        for widget in (self.cb_categorie, self.txt_description):
            try:
                widget.configure(state=etat)
            except tk.TclError:
                pass
        # Désactive aussi tous les ttk.Entry du formulaire
        def _parcourir(w):
            for enfant in w.winfo_children():
                if isinstance(enfant, ttk.Entry):
                    enfant.configure(state=etat)
                _parcourir(enfant)
        _parcourir(self.inner_form)

    def _choisir_photo(self):
        chemin = filedialog.askopenfilename(
            title="Choisir une photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.gif"), ("Tous les fichiers", "*.*")])
        if not chemin:
            return
        if self.doc.chemin:
            base = os.path.dirname(os.path.abspath(self.doc.chemin))
            try:
                relatif = os.path.relpath(chemin, base).replace(os.sep, "/")
                if not relatif.startswith("."):
                    relatif = "./" + relatif
                self.var_photo.set(relatif)
                return
            except ValueError:
                pass  # ex : lecteur différent sous Windows -> chemin absolu en repli
        self.var_photo.set(chemin)

    def _on_champ_modifie(self):
        self._marquer_modifie()
        if self.lieu_courant is not None:
            self._valider_vers_modele()

    def _on_desc_modifiee(self, _event=None):
        if self.txt_description.edit_modified():
            self._on_champ_modifie()
            self.txt_description.edit_modified(False)

    # ── Divers ───────────────────────────────────────────────────
    def _marquer_modifie(self):
        if not self.modifie:
            self.modifie = True
            self._rafraichir_titre()

    def _rafraichir_titre(self):
        nom_fichier = os.path.basename(self.doc.chemin) if self.doc.chemin else "(non enregistré)"
        marque = " *" if self.modifie else ""
        self.root.title(f"Éditeur de lieux — {nom_fichier}{marque}")

    def _statut(self, texte):
        self.var_statut.set(texte)


def main():
    chemin_initial = sys.argv[1] if len(sys.argv) > 1 else None
    root = tk.Tk()
    App(root, chemin_initial)
    root.mainloop()


if __name__ == "__main__":
    main()
