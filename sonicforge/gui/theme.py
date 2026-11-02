"""
Thème visuel sombre et moderne pour l'interface SonicForge (Tkinter / TTK).
"""

import tkinter as tk
from tkinter import ttk

# Palette de couleurs "Cyber Slate / Midnight"
COLORS = {
    "bg": "#12131C",               # Fond principal très sombre
    "card_bg": "#1E202E",          # Fond des cartes / conteneurs
    "card_border": "#2E3247",      # Bordure subtile
    "input_bg": "#2A2D40",         # Fond des champs de saisie
    "text": "#F1F5F9",             # Texte principal (blanc cassé)
    "text_muted": "#94A3B8",       # Texte secondaire (gris doux)
    "accent": "#3B82F6",           # Bleu principal
    "accent_hover": "#2563EB",     # Bleu survol
    "success": "#10B981",          # Vert succès
    "warning": "#F59E0B",          # Jaune / orange avertissement
    "danger": "#EF4444",           # Rouge erreur
    "terminal_bg": "#0D0E15",      # Fond console de logs
    "terminal_fg": "#A7F3D0",      # Texte console vert pastel
}


def apply_theme(root: tk.Tk):
    """Applique le thème moderne sombre sur la racine Tk et les widgets TTK."""
    root.configure(bg=COLORS["bg"])

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Configuration générale
    style.configure(".", 
        background=COLORS["bg"], 
        foreground=COLORS["text"], 
        font=("Segoe UI", 10)
    )

    # Frames
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Card.TFrame", background=COLORS["card_bg"], relief="flat")
    
    # LabelFrames
    style.configure("TLabelframe", 
        background=COLORS["card_bg"], 
        foreground=COLORS["text"], 
        relief="solid", 
        borderwidth=1,
        bordercolor=COLORS["card_border"]
    )
    style.configure("TLabelframe.Label", 
        background=COLORS["card_bg"], 
        foreground=COLORS["accent"], 
        font=("Segoe UI", 10, "bold")
    )

    # Labels
    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("Card.TLabel", background=COLORS["card_bg"], foreground=COLORS["text"])
    style.configure("Title.TLabel", 
        background=COLORS["bg"], 
        foreground=COLORS["text"], 
        font=("Segoe UI", 16, "bold")
    )
    style.configure("Subtitle.TLabel", 
        background=COLORS["bg"], 
        foreground=COLORS["text_muted"], 
        font=("Segoe UI", 9)
    )
    style.configure("Section.TLabel", 
        background=COLORS["card_bg"], 
        foreground=COLORS["accent"], 
        font=("Segoe UI", 11, "bold")
    )
    style.configure("Status.TLabel", 
        background=COLORS["bg"], 
        foreground=COLORS["text_muted"], 
        font=("Segoe UI", 9, "italic")
    )

    # Boutons
    style.configure("TButton", 
        background=COLORS["card_bg"], 
        foreground=COLORS["text"], 
        borderwidth=1, 
        relief="flat",
        font=("Segoe UI", 10, "bold"),
        padding=(10, 6)
    )
    style.map("TButton", 
        background=[("active", COLORS["card_border"]), ("pressed", COLORS["accent"])],
        foreground=[("active", "#FFFFFF")]
    )

    style.configure("Primary.TButton", 
        background=COLORS["accent"], 
        foreground="#FFFFFF", 
        borderwidth=0, 
        font=("Segoe UI", 10, "bold"),
        padding=(14, 8)
    )
    style.map("Primary.TButton", 
        background=[("active", COLORS["accent_hover"]), ("disabled", "#334155")]
    )

    style.configure("Success.TButton", 
        background=COLORS["success"], 
        foreground="#FFFFFF", 
        borderwidth=0, 
        font=("Segoe UI", 10, "bold"),
        padding=(12, 7)
    )

    # Entrées texte et combobox
    style.configure("TEntry", 
        fieldbackground=COLORS["input_bg"], 
        foreground=COLORS["text"], 
        insertcolor=COLORS["text"],
        borderwidth=1,
        padding=5
    )
    style.configure("TCombobox", 
        fieldbackground=COLORS["input_bg"], 
        background=COLORS["card_bg"], 
        foreground=COLORS["text"], 
        arrowcolor=COLORS["text"],
        padding=4
    )
    style.map("TCombobox", 
        fieldbackground=[("readonly", COLORS["input_bg"])],
        foreground=[("readonly", COLORS["text"])]
    )

    # Checkbuttons & Radiobuttons
    style.configure("TCheckbutton", background=COLORS["card_bg"], foreground=COLORS["text"])
    style.configure("TRadiobutton", background=COLORS["card_bg"], foreground=COLORS["text"])

    # Barre de progression
    style.configure("Horizontal.TProgressbar", 
        troughcolor=COLORS["card_border"], 
        background=COLORS["accent"], 
        thickness=10, 
        relief="flat"
    )

    # Onglets (Notebook)
    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", 
        background=COLORS["card_bg"], 
        foreground=COLORS["text_muted"], 
        padding=(16, 8), 
        font=("Segoe UI", 10, "bold"),
        relief="flat"
    )
    style.map("TNotebook.Tab", 
        background=[("selected", COLORS["accent"]), ("active", COLORS["card_border"])],
        foreground=[("selected", "#FFFFFF"), ("active", COLORS["text"])]
    )

