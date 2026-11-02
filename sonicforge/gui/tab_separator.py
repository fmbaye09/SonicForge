"""
Onglet Séparateur Audio (Voix / Instrumental) pour Media Arsenal.
"""

import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from ..config import DEMUCS_MODELS, DEFAULT_SEPARATE_DIR
from ..separator import separate_audio
from ..system import check_cuda, check_demucs
from .theme import COLORS


class SeparatorTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(DEFAULT_SEPARATE_DIR))
        self.model = tk.StringVar(value="htdemucs")
        
        cuda_ok, _ = check_cuda()
        self.device = tk.StringVar(value="cuda" if cuda_ok else "cpu")
        self.two_stems = tk.BooleanVar(value=True)
        self.mp3_output = tk.BooleanVar(value=True)
        
        self.progress_val = tk.DoubleVar(value=0)
        self.status_msg = tk.StringVar(value="Prêt")
        self.is_separating = False
        
        self.build_ui()
        self.check_env()

    def build_ui(self):
        # En-tête
        header = ttk.Frame(self)
        header.pack(fill="x", padx=16, pady=(12, 8))
        ttk.Label(header, text="🎵 Séparateur Audio Demucs", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Isole la parole / le chant et l'accompagnement instrumental à l'aide de l'IA Demucs (Meta AI).",
            style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=16, pady=4)

        # 1. Source
        source_frame = ttk.LabelFrame(body, text=" 1. Fichier Audio Source ", padding=10)
        source_frame.pack(fill="x", pady=5)
        source_frame.columnconfigure(1, weight=1)

        ttk.Label(source_frame, text="Audio :", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(source_frame, textvariable=self.input_file).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(source_frame, text="📁 Parcourir...", command=self.browse_input).grid(row=0, column=2)

        # 2. Options Demucs
        opt_frame = ttk.LabelFrame(body, text=" 2. Paramètres IA & Modèle ", padding=10)
        opt_frame.pack(fill="x", pady=5)
        opt_frame.columnconfigure(1, weight=1)
        opt_frame.columnconfigure(3, weight=1)

        ttk.Label(opt_frame, text="Modèle IA :", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        model_combo = ttk.Combobox(opt_frame, textvariable=self.model, state="readonly", values=DEMUCS_MODELS)
        model_combo.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=4)

        ttk.Label(opt_frame, text="Processeur :", style="Card.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 8), pady=4)
        dev_frame = ttk.Frame(opt_frame, style="Card.TFrame")
        dev_frame.grid(row=0, column=3, sticky="w", pady=4)
        ttk.Radiobutton(dev_frame, text="CPU", variable=self.device, value="cpu").pack(side="left", padx=(0, 12))
        self.gpu_radio = ttk.Radiobutton(dev_frame, text="GPU (CUDA)", variable=self.device, value="cuda")
        self.gpu_radio.pack(side="left")

        row2 = ttk.Frame(opt_frame, style="Card.TFrame")
        row2.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        ttk.Checkbutton(row2, text="2 Pistes : Parole vs Instrumental (recommandé)", variable=self.two_stems).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(row2, text="Format MP3 320 kbps (plus léger)", variable=self.mp3_output).pack(side="left")

        # 3. Destination
        dest_frame = ttk.LabelFrame(body, text=" 3. Dossier de Destination ", padding=10)
        dest_frame.pack(fill="x", pady=5)
        dest_frame.columnconfigure(1, weight=1)

        ttk.Label(dest_frame, text="Sortie :", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(dest_frame, textvariable=self.output_dir).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(dest_frame, text="📁 Choisir...", command=self.browse_output).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(dest_frame, text="📂 Ouvrir", command=self.open_output_folder).grid(row=0, column=3)

        # 4. Barre de progression & Action
        action_frame = ttk.Frame(body)
        action_frame.pack(fill="x", pady=(10, 4))
        action_frame.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(action_frame, variable=self.progress_val, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 12))

        self.status_label = ttk.Label(action_frame, textvariable=self.status_msg, style="Status.TLabel", width=15)
        self.status_label.grid(row=0, column=1, sticky="e")

        btn_row = ttk.Frame(body)
        btn_row.pack(fill="x", pady=6)
        self.separate_btn = ttk.Button(
            btn_row,
            text="🚀 Lancer la Séparation",
            style="Primary.TButton",
            command=self.start_separation
        )
        self.separate_btn.pack(side="left", padx=(0, 10))

        # 5. Logs
        log_frame = ttk.LabelFrame(body, text=" Journal des Opérations ", padding=6)
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
        cuda_ok, cuda_msg = check_cuda()
        demucs_ok, demucs_msg = check_demucs()
        if not demucs_ok:
            self.log("⚠️ Demucs n'est pas installé. (pip install demucs)")
        else:
            self.log(f"✅ {demucs_msg}")

        if not cuda_ok:
            self.gpu_radio.config(state="disabled")
            self.log("ℹ️ Mode CPU activé (GPU non disponible).")
        else:
            self.log(f"✅ Accélération GPU prête : {cuda_msg}")

    def browse_input(self):
        filetypes = [
            ("Fichiers audio", "*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma"),
            ("Tous les fichiers", "*.*")
        ]
        chosen = filedialog.askopenfilename(title="Sélectionner un fichier audio", filetypes=filetypes)
        if chosen:
            self.input_file.set(chosen)
            p = Path(chosen)
            self.log(f"📁 Fichier audio sélectionné : {p.name}")
            target = DEFAULT_SEPARATE_DIR / p.stem
            self.output_dir.set(str(target))

    def browse_output(self):
        chosen = filedialog.askdirectory(title="Choisir le dossier de sortie")
        if chosen:
            self.output_dir.set(chosen)
            self.log(f"📂 Dossier de sortie : {chosen}")

    def open_output_folder(self):
        out_path = self.output_dir.get()
        if os.path.exists(out_path):
            if sys.platform == "win32":
                os.startfile(out_path)
            else:
                os.system(f'xdg-open "{out_path}"')
        else:
            messagebox.showinfo("Information", "Le dossier n'existe pas encore.")

    def start_separation(self):
        if self.is_separating:
            return

        input_str = self.input_file.get().strip()
        if not input_str or not os.path.exists(input_str):
            messagebox.showerror("Erreur", "Veuillez choisir un fichier audio valide.")
            return

        self.is_separating = True
        self.separate_btn.config(state="disabled")
        self.progress_val.set(0)
        self.status_msg.set("Séparation...")

        def _worker():
            try:
                def _progress_cb(pct):
                    self.progress_val.set(pct)
                    self.status_msg.set(f"{pct:.0f}%")

                results = separate_audio(
                    input_file=Path(input_str),
                    output_dir=Path(self.output_dir.get()),
                    model=self.model.get(),
                    device=self.device.get(),
                    two_stems=self.two_stems.get(),
                    mp3_output=self.mp3_output.get(),
                    on_progress=_progress_cb,
                    on_log=self.log
                )
                self.progress_val.set(100)
                self.status_msg.set("Terminé ✓")
                self.after(0, lambda: messagebox.showinfo(
                    "Succès",
                    f"Séparation terminée avec succès !\n\nPistes séparées :\n" +
                    "\n".join(f"- {name} : {path.name}" for name, path in results.items())
                ))
            except Exception as e:
                self.status_msg.set("Erreur ❌")
                self.log(f"❌ ERREUR : {e}")
                self.after(0, lambda: messagebox.showerror("Erreur Demucs", str(e)))
            finally:
                self.is_separating = False
                self.after(0, lambda: self.separate_btn.config(state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

