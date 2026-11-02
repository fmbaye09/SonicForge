"""
Application principale SonicForge - Interface graphique unifiée.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk

from .theme import apply_theme, COLORS
from .tab_converter import ConverterTab
from .tab_separator import SeparatorTab
from .tab_subtitles import SubtitlesTab
from .tab_corrector import CorrectorTab
from .tab_doctor import DoctorTab
from ..system import check_ffmpeg, check_cuda
from ..config import APP_NAME, APP_VERSION


class MediaArsenalApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION} - Suite Média & IA")
        self.root.geometry("860x720")
        self.root.minsize(780, 620)

        apply_theme(self.root)
        self.build_ui()

    def build_ui(self):
        # Barre supérieure (Top Bar Brand)
        top_bar = ttk.Frame(self.root)
        top_bar.pack(fill="x", padx=16, pady=(12, 6))

        title_box = ttk.Frame(top_bar)
        title_box.pack(side="left")

        brand_lbl = ttk.Label(
            title_box, 
            text="⚡ SONICFORGE", 
            font=("Segoe UI", 16, "bold"), 
            foreground=COLORS["accent"]
        )
        brand_lbl.pack(anchor="w")

        sub_lbl = ttk.Label(
            title_box, 
            text="Arsenal Média IA : Conversion, Séparation Vocale & Sous-Titrage", 
            style="Subtitle.TLabel"
        )
        sub_lbl.pack(anchor="w")

        # Indicateurs rapides à droite
        badges_box = ttk.Frame(top_bar)
        badges_box.pack(side="right", pady=4)

        ffmpeg_ok, _ = check_ffmpeg()
        cuda_ok, _ = check_cuda()

        badge_ffmpeg = ttk.Label(
            badges_box,
            text=" FFmpeg: OK " if ffmpeg_ok else " FFmpeg: Manquant ",
            foreground="#FFFFFF",
            background=COLORS["success"] if ffmpeg_ok else COLORS["danger"],
            font=("Segoe UI", 9, "bold"),
            padding=(6, 2)
        )
        badge_ffmpeg.pack(side="left", padx=4)

        badge_gpu = ttk.Label(
            badges_box,
            text=" GPU CUDA " if cuda_ok else " Mode CPU ",
            foreground="#FFFFFF",
            background=COLORS["accent"] if cuda_ok else COLORS["card_border"],
            font=("Segoe UI", 9, "bold"),
            padding=(6, 2)
        )
        badge_gpu.pack(side="left", padx=4)

        # Séparateur subtil
        sep = ttk.Separator(self.root, orient="horizontal")
        sep.pack(fill="x", padx=16, pady=(4, 8))

        # Onglets principaux (Notebook)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        # Création des onglets
        self.tab_converter = ConverterTab(self.notebook)
        self.tab_separator = SeparatorTab(self.notebook)
        self.tab_subtitles = SubtitlesTab(self.notebook)
        self.tab_corrector = CorrectorTab(self.notebook)
        self.tab_doctor = DoctorTab(self.notebook)

        self.notebook.add(self.tab_converter, text=" 🎬 Convertisseur Vidéo/Audio ")
        self.notebook.add(self.tab_separator, text=" 🎵 Séparateur Demucs ")
        self.notebook.add(self.tab_subtitles, text=" 📝 Sous-titres Whisper ")
        self.notebook.add(self.tab_corrector, text=" ✍️ Correcteur Paroles ")
        self.notebook.add(self.tab_doctor, text=" 🩺 Diagnostic ")

        # Barre d'état en bas
        bottom_bar = ttk.Frame(self.root)
        bottom_bar.pack(fill="x", padx=16, pady=(0, 8))

        ttk.Label(
            bottom_bar,
            text=f"{APP_NAME} v{APP_VERSION} • Prêt pour le traitement audio/vidéo",
            style="Status.TLabel"
        ).pack(side="left")


def run_gui():
    """Point d'entrée pour lancer l'application graphique."""
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    root = tk.Tk()
    
    # Centre la fenêtre sur l'écran
    root.update_idletasks()
    width = 860
    height = 720
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    app = MediaArsenalApp(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()

