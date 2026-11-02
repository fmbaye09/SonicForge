"""
Onglet Générateur de Sous-titres (Whisper / Alignement) pour Media Arsenal.
"""

import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from ..config import WHISPER_MODELS, SUBTITLE_LANGUAGES, DEFAULT_SUBTITLES_DIR
from ..subtitles import align_subtitles, transcribe_audio, is_whisper_available
from .theme import COLORS


class SubtitlesTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.mode = tk.StringVar(value="transcribe")  # 'transcribe' ou 'align'
        self.audio_file = tk.StringVar()
        self.text_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.model_size = tk.StringVar(value="medium")
        self.selected_lang = tk.StringVar(value="ar")
        
        self.status_msg = tk.StringVar(value="Prêt")
        self.is_running = False

        self.build_ui()
        self.check_env()

    def build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=16, pady=(12, 8))
        ttk.Label(header, text="📝 Générateur de Sous-titres SRT (Whisper)", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Générez des sous-titres précis synchronisés avec l'audio. Mode transcription libre ou alignement forcé avec paroles connues.",
            style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=16, pady=4)

        # 1. Mode de travail
        mode_frame = ttk.LabelFrame(body, text=" 1. Méthode de génération ", padding=10)
        mode_frame.pack(fill="x", pady=5)
        
        ttk.Radiobutton(
            mode_frame,
            text="🎙️ Transcription automatique (Whisper écoute l'audio et transcrit le texte)",
            variable=self.mode,
            value="transcribe",
            command=self.on_mode_change
        ).pack(anchor="w", pady=2)

        ttk.Radiobutton(
            mode_frame,
            text="🎯 Alignement forcé (Vous fournissez le texte exact .txt, Whisper cale précisément les timings)",
            variable=self.mode,
            value="align",
            command=self.on_mode_change
        ).pack(anchor="w", pady=2)

        # 2. Fichiers
        files_frame = ttk.LabelFrame(body, text=" 2. Fichiers ", padding=10)
        files_frame.pack(fill="x", pady=5)
        files_frame.columnconfigure(1, weight=1)

        # Audio
        ttk.Label(files_frame, text="Audio source :", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(files_frame, textvariable=self.audio_file).grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=4)
        ttk.Button(files_frame, text="📁 Parcourir...", command=self.browse_audio).grid(row=0, column=2, pady=4)

        # Texte (désactivé si transcribe)
        self.text_label = ttk.Label(files_frame, text="Paroles (.txt) :", style="Card.TLabel")
        self.text_label.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.text_entry = ttk.Entry(files_frame, textvariable=self.text_file)
        self.text_entry.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=4)
        self.text_btn = ttk.Button(files_frame, text="📄 Choisir...", command=self.browse_text)
        self.text_btn.grid(row=1, column=2, pady=4)

        # Sortie SRT
        ttk.Label(files_frame, text="Sortie (.srt) :", style="Card.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(files_frame, textvariable=self.output_file).grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=4)
        ttk.Button(files_frame, text="💾 Enregistrer sous...", command=self.browse_output).grid(row=2, column=2, pady=4)

        # 3. Paramètres
        param_frame = ttk.LabelFrame(body, text=" 3. Modèle & Langue ", padding=10)
        param_frame.pack(fill="x", pady=5)
        param_frame.columnconfigure(1, weight=1)
        param_frame.columnconfigure(3, weight=1)

        ttk.Label(param_frame, text="Taille Modèle :", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        model_combo = ttk.Combobox(param_frame, textvariable=self.model_size, state="readonly", values=WHISPER_MODELS)
        model_combo.grid(row=0, column=1, sticky="ew", padx=(0, 16))

        ttk.Label(param_frame, text="Langue :", style="Card.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 8))
        lang_names = [f"{label} ({code if code else 'auto'})" for label, code in SUBTITLE_LANGUAGES]
        self.lang_combo = ttk.Combobox(param_frame, state="readonly", values=lang_names)
        self.lang_combo.current(0)
        self.lang_combo.grid(row=0, column=3, sticky="ew")

        # 4. Actions
        btn_row = ttk.Frame(body)
        btn_row.pack(fill="x", pady=8)

        self.run_btn = ttk.Button(
            btn_row,
            text="⚡ Générer le SRT",
            style="Primary.TButton",
            command=self.start_generation
        )
        self.run_btn.pack(side="left", padx=(0, 10))

        ttk.Button(btn_row, text="📂 Ouvrir Dossier SRT", command=self.open_output_folder).pack(side="left")

        self.status_label = ttk.Label(btn_row, textvariable=self.status_msg, style="Status.TLabel")
        self.status_label.pack(side="right")

        # 5. Logs
        log_frame = ttk.LabelFrame(body, text=" Journal d'Exécution ", padding=6)
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

        self.on_mode_change()

    def log(self, text: str):
        def _append():
            self.log_widget.config(state="normal")
            self.log_widget.insert(tk.END, text + "\n")
            self.log_widget.see(tk.END)
            self.log_widget.config(state="disabled")
        self.after(0, _append)

    def check_env(self):
        if is_whisper_available():
            self.log("✅ Moteur Whisper disponible.")
        else:
            self.log("⚠️ Module 'stable-ts' non installé. Installez-le avec : pip install stable-ts")

    def on_mode_change(self):
        mode = self.mode.get()
        if mode == "align":
            self.text_entry.config(state="normal")
            self.text_btn.config(state="normal")
            self.text_label.config(foreground=COLORS["text"])
        else:
            self.text_entry.config(state="disabled")
            self.text_btn.config(state="disabled")
            self.text_label.config(foreground=COLORS["text_muted"])

    def browse_audio(self):
        filetypes = [
            ("Fichiers audio", "*.mp3 *.wav *.m4a *.flac *.ogg"),
            ("Tous les fichiers", "*.*")
        ]
        chosen = filedialog.askopenfilename(title="Sélectionner l'audio", filetypes=filetypes)
        if chosen:
            self.audio_file.set(chosen)
            p = Path(chosen)
            self.log(f"📁 Audio sélectionné : {p.name}")
            
            # Définir chemin de sortie par défaut
            default_out = DEFAULT_SUBTITLES_DIR / f"{p.stem}.srt"
            self.output_file.set(str(default_out))

            # Si un .txt existe à côté, auto-remplir
            text_match = p.with_suffix(".txt")
            if text_match.exists() and not self.text_file.get():
                self.text_file.set(str(text_match))
                self.mode.set("align")
                self.on_mode_change()
                self.log(f"💡 Fichier texte associé trouvé : {text_match.name} -> Basculement en mode alignement")

    def browse_text(self):
        chosen = filedialog.askopenfilename(title="Sélectionner le fichier des paroles", filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")])
        if chosen:
            self.text_file.set(chosen)
            self.log(f"📄 Paroles sélectionnées : {Path(chosen).name}")

    def browse_output(self):
        chosen = filedialog.asksaveasfilename(
            title="Enregistrer le fichier SRT",
            defaultextension=".srt",
            filetypes=[("Fichiers sous-titres SRT", "*.srt"), ("Tous les fichiers", "*.*")]
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

    def get_selected_language_code(self) -> str | None:
        idx = self.lang_combo.current()
        if 0 <= idx < len(SUBTITLE_LANGUAGES):
            return SUBTITLE_LANGUAGES[idx][1]
        return "ar"

    def start_generation(self):
        if self.is_running:
            return

        if not is_whisper_available():
            messagebox.showerror(
                "Dépendance manquante",
                "Le module 'stable-ts' n'est pas installé.\n\n"
                "Installez-le avec :\npip install stable-ts\n"
                "Puis réessayez."
            )
            return

        audio_str = self.audio_file.get().strip()
        if not audio_str or not os.path.exists(audio_str):
            messagebox.showerror("Erreur", "Veuillez sélectionner un fichier audio valide.")
            return

        mode = self.mode.get()
        if mode == "align":
            text_str = self.text_file.get().strip()
            if not text_str or not os.path.exists(text_str):
                messagebox.showerror("Erreur", "En mode alignement, un fichier texte (.txt) de paroles est obligatoire.")
                return

        out_str = self.output_file.get().strip()
        if not out_str:
            out_str = str(DEFAULT_SUBTITLES_DIR / f"{Path(audio_str).stem}.srt")
            self.output_file.set(out_str)

        self.is_running = True
        self.run_btn.config(state="disabled")
        self.status_msg.set("Traitement en cours...")

        def _worker():
            try:
                lang = self.get_selected_language_code()
                model_sz = self.model_size.get()

                if mode == "align":
                    out_path = align_subtitles(
                        audio_path=Path(audio_str),
                        text_path=Path(self.text_file.get()),
                        output_path=Path(out_str),
                        language=lang,
                        model_size=model_sz,
                        on_log=self.log
                    )
                else:
                    out_path = transcribe_audio(
                        audio_path=Path(audio_str),
                        output_path=Path(out_str),
                        language=lang,
                        model_size=model_sz,
                        on_log=self.log
                    )

                self.status_msg.set("Terminé ✓")
                self.after(0, lambda: messagebox.showinfo(
                    "Succès",
                    f"Fichier de sous-titres généré avec succès !\n\nSortie :\n{out_path}"
                ))
            except Exception as e:
                self.status_msg.set("Erreur ❌")
                self.log(f"❌ ERREUR : {e}")
                self.after(0, lambda: messagebox.showerror("Erreur Sous-titres", str(e)))
            finally:
                self.is_running = False
                self.after(0, lambda: self.run_btn.config(state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

