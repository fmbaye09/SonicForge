"""
Onglet Convertisseur Vidéo vers Audio pour Media Arsenal.
"""

import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from ..config import AUDIO_OUTPUT_FORMATS, DEFAULT_CONVERT_DIR
from ..converter import convert_video_to_audio, get_media_info
from .theme import COLORS


class ConverterTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(DEFAULT_CONVERT_DIR))
        self.selected_format = tk.StringVar(value="mp3")
        self.selected_bitrate = tk.StringVar(value="320k")
        self.selected_channels = tk.StringVar(value="Original")
        self.selected_sample_rate = tk.StringVar(value="Original")
        self.normalize_audio = tk.BooleanVar(value=False)
        self.volume_boost = tk.StringVar(value="100%")
        
        self.progress_val = tk.DoubleVar(value=0)
        self.status_msg = tk.StringVar(value="Prêt")
        self.is_converting = False
        
        self.build_ui()

    def build_ui(self):
        # En-tête
        header = ttk.Frame(self)
        header.pack(fill="x", padx=16, pady=(12, 8))
        ttk.Label(header, text="🎬 Convertisseur Vidéo ➔ Audio", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header, 
            text="Extrayez et convertissez l'audio de n'importe quelle vidéo (MP4, MKV, AVI, MOV, WEBM) en MP3, WAV, FLAC, AAC ou OGG.",
            style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(2, 0))

        # Conteneur principal avec 2 colonnes ou sections
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=16, pady=4)

        # 1. Section Fichier Source
        source_frame = ttk.LabelFrame(body, text=" 1. Fichier Source ", padding=10)
        source_frame.pack(fill="x", pady=5)
        source_frame.columnconfigure(1, weight=1)

        ttk.Label(source_frame, text="Vidéo / Média :", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(source_frame, textvariable=self.input_file).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(source_frame, text="📁 Parcourir...", command=self.browse_input).grid(row=0, column=2)

        self.info_label = ttk.Label(source_frame, text="Aucun fichier sélectionné", style="Card.TLabel", foreground=COLORS["text_muted"])
        self.info_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

        # 2. Section Options de Conversion
        opt_frame = ttk.LabelFrame(body, text=" 2. Paramètres Audio ", padding=10)
        opt_frame.pack(fill="x", pady=5)
        opt_frame.columnconfigure(1, weight=1)
        opt_frame.columnconfigure(3, weight=1)

        # Format de sortie
        ttk.Label(opt_frame, text="Format cible :", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        format_names = [f"{k.upper()} - {v['name']}" for k, v in AUDIO_OUTPUT_FORMATS.items()]
        self.format_combo = ttk.Combobox(opt_frame, state="readonly", values=format_names)
        self.format_combo.current(0)
        self.format_combo.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=4)
        self.format_combo.bind("<<ComboboxSelected>>", self.on_format_changed)

        # Débit binaire (Bitrate)
        ttk.Label(opt_frame, text="Qualité / Débit :", style="Card.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 8), pady=4)
        self.bitrate_combo = ttk.Combobox(opt_frame, textvariable=self.selected_bitrate, state="readonly", values=["320k", "256k", "192k", "128k"])
        self.bitrate_combo.grid(row=0, column=3, sticky="ew", pady=4)

        # Canaux & Fréquence
        ttk.Label(opt_frame, text="Canaux :", style="Card.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.channels_combo = ttk.Combobox(opt_frame, textvariable=self.selected_channels, state="readonly", values=["Original", "Stéréo (2.0)", "Mono (1.0)"])
        self.channels_combo.grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=4)

        ttk.Label(opt_frame, text="Échantillonnage :", style="Card.TLabel").grid(row=1, column=2, sticky="w", padx=(0, 8), pady=4)
        self.samplerate_combo = ttk.Combobox(opt_frame, textvariable=self.selected_sample_rate, state="readonly", values=["Original", "44100 Hz (CD)", "48000 Hz (Studio)", "96000 Hz (Hi-Res)"])
        self.samplerate_combo.grid(row=1, column=3, sticky="ew", pady=4)

        # Normalisation et Volume
        row2 = ttk.Frame(opt_frame, style="Card.TFrame")
        row2.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        ttk.Checkbutton(row2, text="✨ Normaliser le volume (EBU R128 Loudnorm)", variable=self.normalize_audio).pack(side="left", padx=(0, 20))
        ttk.Label(row2, text="Volume :", style="Card.TLabel").pack(side="left", padx=(0, 6))
        vol_combo = ttk.Combobox(row2, textvariable=self.volume_boost, width=8, state="readonly", values=["80%", "100%", "120%", "150%", "200%"])
        vol_combo.pack(side="left")

        # 3. Section Destination
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
        self.convert_btn = ttk.Button(
            btn_row, 
            text="⚡ Convertir en Audio", 
            style="Primary.TButton", 
            command=self.start_conversion
        )
        self.convert_btn.pack(side="left", padx=(0, 10))

        # 5. Console de logs
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

    def on_format_changed(self, event=None):
        selected_text = self.format_combo.get()
        fmt_key = selected_text.split(" - ")[0].lower()
        self.selected_format.set(fmt_key)
        
        info = AUDIO_OUTPUT_FORMATS.get(fmt_key, {})
        if info.get("bitrates"):
            self.bitrate_combo.config(values=info["bitrates"], state="readonly")
            if self.selected_bitrate.get() not in info["bitrates"]:
                self.selected_bitrate.set(info.get("default_bitrate", "320k"))
        else:
            self.bitrate_combo.config(values=["Non applicable"], state="disabled")
            self.selected_bitrate.set("Non applicable")

    def browse_input(self):
        filetypes = [
            ("Fichiers vidéo et audio", "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.ts *.m4a *.wav *.mp3"),
            ("Vidéos MP4", "*.mp4"),
            ("Vidéos MKV", "*.mkv"),
            ("Tous les fichiers", "*.*")
        ]
        chosen = filedialog.askopenfilename(title="Sélectionnez une vidéo ou un fichier média", filetypes=filetypes)
        if chosen:
            self.input_file.set(chosen)
            p = Path(chosen)
            self.log(f"📁 Fichier sélectionné : {p.name}")
            
            # Auto-analyse du fichier
            info = get_media_info(p)
            self.info_label.config(
                text=f"Taille : {info['file_size_mb']} Mo | Durée : {info['duration_formatted']} | Audio : {info['audio_codec']} ({info['audio_sample_rate']} Hz, {info['audio_channels']} ch)",
                foreground=COLORS["success"] if info["has_audio"] else COLORS["warning"]
            )
            # Dossier de sortie par défaut à côté du fichier ou dans le dossier dédié
            default_out = DEFAULT_CONVERT_DIR
            self.output_dir.set(str(default_out))

    def browse_output(self):
        chosen = filedialog.askdirectory(title="Choisir le dossier de sortie")
        if chosen:
            self.output_dir.set(chosen)
            self.log(f"📂 Dossier de destination : {chosen}")

    def open_output_folder(self):
        out_path = self.output_dir.get()
        if os.path.exists(out_path):
            if sys.platform == "win32":
                os.startfile(out_path)
            else:
                os.system(f'xdg-open "{out_path}"')
        else:
            messagebox.showinfo("Information", "Le dossier n'existe pas encore. Il sera créé lors de la conversion.")

    def start_conversion(self):
        if self.is_converting:
            return

        input_str = self.input_file.get().strip()
        if not input_str or not os.path.exists(input_str):
            messagebox.showerror("Erreur", "Veuillez choisir un fichier vidéo source existant.")
            return

        fmt = self.selected_format.get().lower()
        bitrate = self.selected_bitrate.get() if fmt in ["mp3", "aac", "ogg"] else None
        
        # Canaux
        ch_str = self.selected_channels.get()
        channels = 1 if "Mono" in ch_str else (2 if "Stéréo" in ch_str else None)

        # Échantillonnage
        sr_str = self.selected_sample_rate.get()
        sample_rate = 44100 if "44100" in sr_str else (48000 if "48000" in sr_str else (96000 if "96000" in sr_str else None))

        # Volume
        vol_str = self.volume_boost.get().replace("%", "")
        volume = float(vol_str) / 100.0 if vol_str.isdigit() else 1.0

        normalize = self.normalize_audio.get()
        out_dir = Path(self.output_dir.get())

        self.is_converting = True
        self.convert_btn.config(state="disabled")
        self.progress_val.set(0)
        self.status_msg.set("Conversion en cours...")

        def _worker():
            try:
                target_ext = AUDIO_OUTPUT_FORMATS.get(fmt, {}).get("ext", ".mp3")
                out_file = out_dir / f"{Path(input_str).stem}{target_ext}"

                def _progress_cb(pct):
                    self.progress_val.set(pct)
                    self.status_msg.set(f"{pct:.0f}%")

                res = convert_video_to_audio(
                    input_file=Path(input_str),
                    output_file=out_file,
                    output_format=fmt,
                    bitrate=bitrate,
                    channels=channels,
                    sample_rate=sample_rate,
                    normalize=normalize,
                    volume=volume,
                    on_progress=_progress_cb,
                    on_log=self.log
                )
                self.progress_val.set(100)
                self.status_msg.set("Terminé ✓")
                self.after(0, lambda: messagebox.showinfo(
                    "Succès", 
                    f"Conversion réussie !\n\nFichier généré :\n{res.name}\n\nDans :\n{res.parent}"
                ))
            except Exception as e:
                self.status_msg.set("Erreur ❌")
                self.log(f"❌ ERREUR : {e}")
                self.after(0, lambda: messagebox.showerror("Erreur de conversion", str(e)))
            finally:
                self.is_converting = False
                self.after(0, lambda: self.convert_btn.config(state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

