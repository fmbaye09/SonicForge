"""
Onglet Diagnostic Système & Dépendances pour Media Arsenal.
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from ..system import get_full_diagnostics, format_diagnostic_report
from .theme import COLORS


class DoctorTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.build_ui()
        self.run_diag()

    def build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=16, pady=(12, 8))
        ttk.Label(header, text="🩺 Diagnostic Système & Outils Média", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="État des dépendances matérielles (GPU/CUDA, FFmpeg) et des bibliothèques d'intelligence artificielle.",
            style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=16, pady=4)

        # Cartes d'état
        self.status_frame = ttk.LabelFrame(body, text=" État des Composants ", padding=12)
        self.status_frame.pack(fill="x", pady=5)
        self.status_frame.columnconfigure(1, weight=1)

        # Rapport textuel
        report_frame = ttk.LabelFrame(body, text=" Rapport Détaillé & Recommandations ", padding=10)
        report_frame.pack(fill="both", expand=True, pady=5)

        self.report_text = scrolledtext.ScrolledText(
            report_frame,
            bg=COLORS["terminal_bg"],
            fg=COLORS["terminal_fg"],
            insertbackground="#FFFFFF",
            font=("Consolas", 10)
        )
        self.report_text.pack(fill="both", expand=True)

        # Barre d'actions
        btn_row = ttk.Frame(body)
        btn_row.pack(fill="x", pady=8)

        ttk.Button(
            btn_row,
            text="🔄 Réactualiser le Diagnostic",
            style="Primary.TButton",
            command=self.run_diag
        ).pack(side="left", padx=(0, 10))

    def run_diag(self):
        # Nettoyage des widgets précédents
        for widget in self.status_frame.winfo_children():
            widget.destroy()

        diag = get_full_diagnostics()

        row = 0
        labels_map = {
            "ffmpeg": "FFmpeg (Moteur Vidéo/Audio)",
            "ffprobe": "FFprobe (Inspecteur Métadonnées)",
            "pytorch": "PyTorch (Moteur Deep Learning)",
            "cuda": "CUDA / GPU NVIDIA (Accélération)",
            "demucs": "Demucs (Séparateur Vocal/Instrument)",
            "whisper": "Whisper (Sous-titres & Transcription)",
            "soundfile": "SoundFile (Backend audio)",
            "sentence_transformers": "Sentence-Transformers (Embeddings IA)"
        }

        for key, (ok, desc) in diag.items():
            name = labels_map.get(key, key)
            icon = "✅" if ok else "⚠️"
            color = COLORS["success"] if ok else COLORS["warning"]

            lbl_name = ttk.Label(self.status_frame, text=f"{icon} {name} :", font=("Segoe UI", 10, "bold"), style="Card.TLabel")
            lbl_name.grid(row=row, column=0, sticky="w", padx=(0, 15), pady=3)

            lbl_desc = ttk.Label(self.status_frame, text=desc, foreground=color, style="Card.TLabel")
            lbl_desc.grid(row=row, column=1, sticky="w", pady=3)
            row += 1

        # Affichage du rapport
        self.report_text.config(state="normal")
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert(tk.END, format_diagnostic_report() + "\n\n")

        # Conseils d'installation pour les manquants
        missing = [k for k, (ok, _) in diag.items() if not ok]
        if missing:
            self.report_text.insert(tk.END, "💡 GUIDE D'INSTALLATION DES COMPOSANTS MANQUANTS :\n")
            self.report_text.insert(tk.END, "-----------------------------------------------------------\n")
            if "whisper" in missing:
                self.report_text.insert(tk.END, "• Pour activer la génération de sous-titres Whisper :\n")
                self.report_text.insert(tk.END, "   pip install stable-ts\n\n")
            if "soundfile" in missing:
                self.report_text.insert(tk.END, "• Pour améliorer la compatibilité audio Windows de Demucs :\n")
                self.report_text.insert(tk.END, "   pip install soundfile\n\n")
            if "sentence_transformers" in missing:
                self.report_text.insert(tk.END, "• Pour activer les embeddings multilingues dans le correcteur :\n")
                self.report_text.insert(tk.END, "   pip install sentence-transformers\n\n")
            if "cuda" in missing:
                self.report_text.insert(tk.END, "• Pour activer l'accélération carte graphique NVIDIA (GPU) :\n")
                self.report_text.insert(tk.END, "   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118\n\n")
        else:
            self.report_text.insert(tk.END, "🎉 Félicitations : tous les outils et dépendances sont 100% installés et opérationnels !\n")

        self.report_text.config(state="disabled")

