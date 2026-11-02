"""
Onglet Correcteur de Paroles & Synchronisation SRT pour Media Arsenal.
"""

import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from ..config import DEFAULT_SUBTITLES_DIR
from ..lyrics_corrector import correct_srt_file
from ..system import check_sentence_transformers
from .theme import COLORS


class CorrectorTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.srt_file = tk.StringVar()
        self.lyrics_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.use_embeddings = tk.BooleanVar(value=False)
        self.gap_penalty = tk.DoubleVar(value=0.35)

        self.status_msg = tk.StringVar(value="Prêt")
        self.is_running = False

        self.build_ui()
        self.check_env()

    def build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=16, pady=(12, 8))
        ttk.Label(header, text="✍️ Correcteur de Paroles & Alignement SRT", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Corrige le texte d'un .srt déjà généré en lui appliquant les vraies paroles, sans altérer les timestamps existants et en insérant les refrains sautés.",
            style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=16, pady=4)

        # 1. Fichiers
        files_frame = ttk.LabelFrame(body, text=" 1. Fichiers sources ", padding=10)
        files_frame.pack(fill="x", pady=5)
        files_frame.columnconfigure(1, weight=1)

        # SRT
        ttk.Label(files_frame, text="SRT généré :", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(files_frame, textvariable=self.srt_file).grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=4)
        ttk.Button(files_frame, text="📁 Choisir SRT...", command=self.browse_srt).grid(row=0, column=2, pady=4)

        # Paroles
        ttk.Label(files_frame, text="Paroles exactes (.txt) :", style="Card.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(files_frame, textvariable=self.lyrics_file).grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=4)
        ttk.Button(files_frame, text="📄 Choisir TXT...", command=self.browse_lyrics).grid(row=1, column=2, pady=4)

        # Sortie
        ttk.Label(files_frame, text="SRT corrigé :", style="Card.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(files_frame, textvariable=self.output_file).grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=4)
        ttk.Button(files_frame, text="💾 Enregistrer sous...", command=self.browse_output).grid(row=2, column=2, pady=4)

        # 2. Options d'alignement
        opt_frame = ttk.LabelFrame(body, text=" 2. Paramètres d'alignement ", padding=10)
        opt_frame.pack(fill="x", pady=5)
        opt_frame.columnconfigure(1, weight=1)

        row1 = ttk.Frame(opt_frame, style="Card.TFrame")
        row1.pack(fill="x", pady=2)
        ttk.Checkbutton(
            row1,
            text="🧠 Modèle d'embeddings multilingue (plus résistant si la transcription Whisper est très déformée)",
            variable=self.use_embeddings
        ).pack(side="left")

        row2 = ttk.Frame(opt_frame, style="Card.TFrame")
        row2.pack(fill="x", pady=(8, 2))
        ttk.Label(row2, text="Pénalité de saut (Gap Penalty) :", style="Card.TLabel").pack(side="left", padx=(0, 8))
        gap_spin = ttk.Spinbox(row2, from_=0.1, to=1.0, increment=0.05, textvariable=self.gap_penalty, width=6)
        gap_spin.pack(side="left")
        ttk.Label(
            row2,
            text="(0.35 recommandé - augmentez si trop de répétitions fictives sont ajoutées)",
            style="Subtitle.TLabel"
        ).pack(side="left", padx=(10, 0))

        # 3. Actions
        btn_row = ttk.Frame(body)
        btn_row.pack(fill="x", pady=8)

        self.run_btn = ttk.Button(
            btn_row,
            text="✨ Corriger et Réaligner le SRT",
            style="Primary.TButton",
            command=self.start_correction
        )
        self.run_btn.pack(side="left", padx=(0, 10))

        ttk.Button(btn_row, text="📂 Ouvrir Dossier SRT", command=self.open_output_folder).pack(side="left")

        self.status_label = ttk.Label(btn_row, textvariable=self.status_msg, style="Status.TLabel")
        self.status_label.pack(side="right")

        # 4. Logs
        log_frame = ttk.LabelFrame(body, text=" Rapport d'alignement ", padding=6)
        log_frame.pack(fill="both", expand=True, pady=(5, 0))

        self.log_widget = scrolledtext.ScrolledText(
            log_frame,
            height=6,
            bg=COLORS["terminal_bg"],
            fg=COLORS["terminal_fg"],
            insertbackground="#FFFFFF",
            font=("Consolas", 9)
        )
        self.log_widget.pack(fill="both", expand=True)
        self.log_widget.config(state="disabled")

    def log(self, text: str):
        def _append():
            self.log_widget.config(state="normal")
            self.log_widget.insert(tk.END, text + "\n")
            self.log_widget.see(tk.END)
            self.log_widget.config(state="disabled")
        self.after(0, _append)

    def check_env(self):
        emb_ok, _ = check_sentence_transformers()
        if emb_ok:
            self.log("✅ sentence-transformers détecté pour les embeddings.")
        else:
            self.log("ℹ️ Algorithme difflib rapide actif (sentence-transformers optionnel).")

    def browse_srt(self):
        chosen = filedialog.askopenfilename(title="Sélectionner le SRT", filetypes=[("Fichiers SRT", "*.srt"), ("Tous les fichiers", "*.*")])
        if chosen:
            self.srt_file.set(chosen)
            p = Path(chosen)
            self.log(f"📁 SRT sélectionné : {p.name}")
            
            # Essayer de deviner le fichier lyrics .txt
            txt_match = p.with_suffix(".txt")
            if txt_match.exists() and not self.lyrics_file.get():
                self.lyrics_file.set(str(txt_match))
                self.log(f"💡 Fichier de paroles associé trouvé : {txt_match.name}")

            out_match = p.parent / f"{p.stem}_corrigé.srt"
            self.output_file.set(str(out_match))

    def browse_lyrics(self):
        chosen = filedialog.askopenfilename(title="Sélectionner les paroles", filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")])
        if chosen:
            self.lyrics_file.set(chosen)
            self.log(f"📄 Paroles sélectionnées : {Path(chosen).name}")

    def browse_output(self):
        chosen = filedialog.asksaveasfilename(
            title="Enregistrer le SRT corrigé",
            defaultextension=".srt",
            filetypes=[("Fichiers SRT", "*.srt"), ("Tous les fichiers", "*.*")]
        )
        if chosen:
            self.output_file.set(chosen)

    def open_output_folder(self):
        out_str = self.output_file.get()
        folder = Path(out_str).parent if out_str else DEFAULT_SUBTITLES_DIR
        if folder.exists():
            if sys.platform == "win32":
                os.startfile(folder)
            else:
                os.system(f'xdg-open "{folder}"')
        else:
            messagebox.showinfo("Information", "Le dossier n'existe pas encore.")

    def start_correction(self):
        if self.is_running:
            return

        srt_str = self.srt_file.get().strip()
        lyrics_str = self.lyrics_file.get().strip()
        out_str = self.output_file.get().strip()

        if not srt_str or not os.path.exists(srt_str):
            messagebox.showerror("Erreur", "Veuillez choisir un fichier .srt existant.")
            return

        if not lyrics_str or not os.path.exists(lyrics_str):
            messagebox.showerror("Erreur", "Veuillez choisir un fichier .txt de paroles existant.")
            return

        if not out_str:
            out_str = str(Path(srt_str).parent / f"{Path(srt_str).stem}_corrigé.srt")
            self.output_file.set(out_str)

        self.is_running = True
        self.run_btn.config(state="disabled")
        self.status_msg.set("Correction...")

        def _worker():
            try:
                res = correct_srt_file(
                    srt_path=Path(srt_str),
                    lyrics_path=Path(lyrics_str),
                    output_path=Path(out_str),
                    use_embeddings=self.use_embeddings.get(),
                    gap_penalty=float(self.gap_penalty.get()),
                    on_log=self.log
                )
                self.status_msg.set("Terminé ✓")
                self.after(0, lambda: messagebox.showinfo(
                    "Correction réussie",
                    f"Fichier SRT corrigé avec succès !\n\n"
                    f"Correspondances : {res['matches']}\n"
                    f"Répétitions interpolées : {res['inserted_repeats']}\n"
                    f"Total sous-titres : {res['total_cues']}\n\n"
                    f"Enregistré dans :\n{res['output_path']}"
                ))
            except Exception as e:
                self.status_msg.set("Erreur ❌")
                self.log(f"❌ ERREUR : {e}")
                self.after(0, lambda: messagebox.showerror("Erreur", str(e)))
            finally:
                self.is_running = False
                self.after(0, lambda: self.run_btn.config(state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

