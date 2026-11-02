#!/usr/bin/env python3
"""
khassida_subtitles_gui.py
--------------------------
Interface graphique pour le pipeline complet de sous-titrage des khassidas.

Onglet 1 - Générer SRT : transcription Whisper (texte inconnu) ou alignement
forcé (texte connu) -> fichier .srt avec timing.

Onglet 2 - Corriger les paroles : prend un .srt déjà généré (bon timing,
texte approximatif) + le texte exact des paroles, et corrige le contenu
sans toucher au timing. Gère aussi l'insertion des répétitions manquées.

Lancer avec : python khassida_subtitles_gui.py
"""

import threading
import traceback
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

import stable_whisper
import lyrics_corrector as lc

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v3"]
LANGUAGES = [
    ("Arabe", "ar"),
    ("Français", "fr"),
    ("Anglais", "en"),
    ("Auto-détection", None),
]


def build_file_row(parent, label_text, command, return_frame=False):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=12, pady=4)
    ctk.CTkLabel(row, text=label_text, width=140, anchor="w").pack(side="left")
    value_label = ctk.CTkLabel(row, text="(aucun fichier)", anchor="w", text_color="gray60")
    value_label.pack(side="left", fill="x", expand=True)
    ctk.CTkButton(row, text="Choisir...", width=90, command=command).pack(side="right")
    if return_frame:
        return row, value_label
    return value_label


# ====================================================================== Onglet 1

class GenerateTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.model = None
        self.model_size_loaded = None
        self.audio_path: Path | None = None
        self.text_path: Path | None = None
        self.output_path: Path | None = None
        self.is_running = False

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 16, "pady": 8}

        mode_frame = ctk.CTkFrame(self)
        mode_frame.pack(fill="x", **pad)
        ctk.CTkLabel(mode_frame, text="Mode", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(10, 2))
        self.mode_var = ctk.StringVar(value="transcribe")
        mode_row = ctk.CTkFrame(mode_frame, fg_color="transparent")
        mode_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkRadioButton(
            mode_row, text="Texte inconnu (transcription Whisper — bon timing, à corriger ensuite)",
            variable=self.mode_var, value="transcribe", command=self._on_mode_change
        ).pack(anchor="w", pady=2)
        ctk.CTkRadioButton(
            mode_row, text="Texte connu (alignement forcé)",
            variable=self.mode_var, value="align", command=self._on_mode_change
        ).pack(anchor="w", pady=2)

        files_frame = ctk.CTkFrame(self)
        files_frame.pack(fill="x", **pad)
        ctk.CTkLabel(files_frame, text="Fichiers", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(10, 2))

        self.audio_label = build_file_row(files_frame, "Audio :", self._pick_audio)
        self.text_row_frame, self.text_label = build_file_row(files_frame, "Texte (.txt) :", self._pick_text, return_frame=True)
        self.output_label = build_file_row(files_frame, "Sortie (.srt) :", self._pick_output)
        ctk.CTkFrame(files_frame, height=4, fg_color="transparent").pack(pady=2)

        options_frame = ctk.CTkFrame(self)
        options_frame.pack(fill="x", **pad)
        ctk.CTkLabel(options_frame, text="Options", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(10, 2))

        row1 = ctk.CTkFrame(options_frame, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(row1, text="Modèle Whisper :", width=140, anchor="w").pack(side="left")
        self.model_var = ctk.StringVar(value="medium")
        ctk.CTkOptionMenu(row1, values=MODEL_SIZES, variable=self.model_var).pack(side="left", fill="x", expand=True)

        row2 = ctk.CTkFrame(options_frame, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkLabel(row2, text="Langue :", width=140, anchor="w").pack(side="left")
        self.lang_display_var = ctk.StringVar(value=LANGUAGES[0][0])
        ctk.CTkOptionMenu(row2, values=[l[0] for l in LANGUAGES], variable=self.lang_display_var).pack(side="left", fill="x", expand=True)

        self.run_button = ctk.CTkButton(self, text="Générer le SRT", height=42, font=ctk.CTkFont(size=14, weight="bold"), command=self._on_run)
        self.run_button.pack(fill="x", padx=16, pady=(16, 6))

        self.progress_bar = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 6))
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self, text="Prêt.", text_color="gray70")
        self.status_label.pack(pady=(0, 16))

        self._on_mode_change()

    def _on_mode_change(self):
        if self.mode_var.get() == "align":
            self.text_row_frame.pack(fill="x", padx=12, pady=4)
        else:
            self.text_row_frame.pack_forget()

    def _pick_audio(self):
        path = filedialog.askopenfilename(
            title="Choisir un fichier audio",
            filetypes=[("Audio", "*.mp3 *.wav *.m4a *.flac *.ogg"), ("Tous les fichiers", "*.*")],
        )
        if path:
            self.audio_path = Path(path)
            self.audio_label.configure(text=self.audio_path.name, text_color="white")
            if not self.output_path:
                guessed = self.audio_path.with_suffix(".srt")
                self.output_path = guessed
                self.output_label.configure(text=guessed.name, text_color="white")

    def _pick_text(self):
        path = filedialog.askopenfilename(
            title="Choisir le fichier texte des paroles",
            filetypes=[("Texte", "*.txt"), ("Tous les fichiers", "*.*")],
        )
        if path:
            self.text_path = Path(path)
            self.text_label.configure(text=self.text_path.name, text_color="white")

    def _pick_output(self):
        path = filedialog.asksaveasfilename(
            title="Enregistrer le fichier de sous-titres",
            defaultextension=".srt",
            filetypes=[("SubRip", "*.srt")],
        )
        if path:
            self.output_path = Path(path)
            self.output_label.configure(text=self.output_path.name, text_color="white")

    def _on_run(self):
        if self.is_running:
            return
        if not self.audio_path or not self.audio_path.exists():
            messagebox.showerror("Erreur", "Sélectionne un fichier audio valide.")
            return
        mode = self.mode_var.get()
        if mode == "align" and (not self.text_path or not self.text_path.exists()):
            messagebox.showerror("Erreur", "Sélectionne un fichier texte valide pour l'alignement.")
            return
        if not self.output_path:
            messagebox.showerror("Erreur", "Choisis un emplacement de sortie pour le .srt.")
            return

        self.is_running = True
        self.run_button.configure(state="disabled", text="Traitement en cours...")
        self.progress_bar.start()
        self.status_label.configure(text="Démarrage...", text_color="gray70")

        threading.Thread(target=self._run_worker, args=(mode,), daemon=True).start()

    def _run_worker(self, mode: str):
        try:
            model_size = self.model_var.get()
            lang_code = dict(LANGUAGES)[self.lang_display_var.get()]

            if self.model is None or self.model_size_loaded != model_size:
                self._set_status(f"Chargement du modèle Whisper '{model_size}'...")
                self.model = stable_whisper.load_model(model_size)
                self.model_size_loaded = model_size

            if mode == "align":
                self._set_status("Alignement du texte avec l'audio...")
                text = self.text_path.read_text(encoding="utf-8").strip()
                if not text:
                    raise ValueError("Le fichier texte est vide.")
                result = self.model.align(str(self.audio_path), text, language=lang_code)
            else:
                self._set_status("Transcription de l'audio...")
                result = self.model.transcribe(str(self.audio_path), language=lang_code)

            self._set_status("Écriture du fichier SRT...")
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            result.to_srt_vtt(str(self.output_path), word_level=False)

            self._on_success()
        except Exception as e:
            traceback.print_exc()
            self._on_error(str(e))

    def _set_status(self, text: str):
        self.after(0, lambda: self.status_label.configure(text=text, text_color="gray70"))

    def _on_success(self):
        def _update():
            self.progress_bar.stop()
            self.progress_bar.set(1)
            self.status_label.configure(text=f"Terminé : {self.output_path.name}", text_color="#4caf50")
            self.run_button.configure(state="normal", text="Générer le SRT")
            self.is_running = False
            messagebox.showinfo("Terminé", f"Sous-titres générés :\n{self.output_path}")
        self.after(0, _update)

    def _on_error(self, message: str):
        def _update():
            self.progress_bar.stop()
            self.progress_bar.set(0)
            self.status_label.configure(text="Erreur — voir détails", text_color="#e53935")
            self.run_button.configure(state="normal", text="Générer le SRT")
            self.is_running = False
            messagebox.showerror("Erreur", message)
        self.after(0, _update)


# ====================================================================== Onglet 2

class CorrectTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.srt_path: Path | None = None
        self.lyrics_path: Path | None = None
        self.output_path: Path | None = None
        self.is_running = False

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 16, "pady": 8}

        intro = ctk.CTkLabel(
            self,
            text="Corrige le texte d'un .srt déjà généré avec les vraies paroles,\n"
                 "sans toucher au timing. Insère aussi les répétitions sautées.",
            text_color="gray70", justify="left",
        )
        intro.pack(anchor="w", padx=20, pady=(12, 4))

        files_frame = ctk.CTkFrame(self)
        files_frame.pack(fill="x", **pad)
        ctk.CTkLabel(files_frame, text="Fichiers", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(10, 2))

        self.srt_label = build_file_row(files_frame, "SRT généré :", self._pick_srt)
        self.lyrics_label = build_file_row(files_frame, "Paroles (.txt) :", self._pick_lyrics)
        self.output_label = build_file_row(files_frame, "Sortie (.srt) :", self._pick_output)
        ctk.CTkFrame(files_frame, height=4, fg_color="transparent").pack(pady=2)

        note = ctk.CTkLabel(
            files_frame,
            text="Le fichier paroles : une ligne = un sous-titre attendu, dans l'ordre,\n"
                 "répétitions écrites explicitement (refrain x3 = la ligne écrite 3 fois).",
            text_color="gray60", justify="left", font=ctk.CTkFont(size=11),
        )
        note.pack(anchor="w", padx=12, pady=(0, 10))

        options_frame = ctk.CTkFrame(self)
        options_frame.pack(fill="x", **pad)
        ctk.CTkLabel(options_frame, text="Options", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(10, 2))

        row1 = ctk.CTkFrame(options_frame, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=4)
        self.embeddings_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            row1, text="Utiliser le petit modèle d'embeddings multilingue (~470 Mo, plus robuste au bruit)",
            variable=self.embeddings_var,
        ).pack(anchor="w")

        row2 = ctk.CTkFrame(options_frame, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkLabel(row2, text="Sensibilité aux trous :", width=160, anchor="w").pack(side="left")
        self.gap_penalty_var = ctk.DoubleVar(value=0.35)
        gap_slider = ctk.CTkSlider(row2, from_=0.1, to=0.8, variable=self.gap_penalty_var, number_of_steps=70)
        gap_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.gap_value_label = ctk.CTkLabel(row2, text="0.35", width=40)
        self.gap_value_label.pack(side="left")
        gap_slider.configure(command=lambda v: self.gap_value_label.configure(text=f"{v:.2f}"))

        self.run_button = ctk.CTkButton(self, text="Corriger les paroles", height=42, font=ctk.CTkFont(size=14, weight="bold"), command=self._on_run)
        self.run_button.pack(fill="x", padx=16, pady=(16, 6))

        self.progress_bar = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 6))
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self, text="Prêt.", text_color="gray70")
        self.status_label.pack(pady=(0, 8))

        self.summary_label = ctk.CTkLabel(self, text="", text_color="gray60", justify="left", font=ctk.CTkFont(size=11))
        self.summary_label.pack(pady=(0, 16))

    def _pick_srt(self):
        path = filedialog.askopenfilename(title="Choisir le SRT généré", filetypes=[("SubRip", "*.srt"), ("Tous les fichiers", "*.*")])
        if path:
            self.srt_path = Path(path)
            self.srt_label.configure(text=self.srt_path.name, text_color="white")
            if not self.output_path:
                guessed = self.srt_path.with_name(self.srt_path.stem + "_corrected.srt")
                self.output_path = guessed
                self.output_label.configure(text=guessed.name, text_color="white")

    def _pick_lyrics(self):
        path = filedialog.askopenfilename(title="Choisir le fichier des vraies paroles", filetypes=[("Texte", "*.txt"), ("Tous les fichiers", "*.*")])
        if path:
            self.lyrics_path = Path(path)
            self.lyrics_label.configure(text=self.lyrics_path.name, text_color="white")

    def _pick_output(self):
        path = filedialog.asksaveasfilename(title="Enregistrer le SRT corrigé", defaultextension=".srt", filetypes=[("SubRip", "*.srt")])
        if path:
            self.output_path = Path(path)
            self.output_label.configure(text=self.output_path.name, text_color="white")

    def _on_run(self):
        if self.is_running:
            return
        if not self.srt_path or not self.srt_path.exists():
            messagebox.showerror("Erreur", "Sélectionne un fichier .srt valide.")
            return
        if not self.lyrics_path or not self.lyrics_path.exists():
            messagebox.showerror("Erreur", "Sélectionne un fichier de paroles valide.")
            return
        if not self.output_path:
            messagebox.showerror("Erreur", "Choisis un emplacement de sortie.")
            return

        self.is_running = True
        self.run_button.configure(state="disabled", text="Traitement en cours...")
        self.progress_bar.start()
        self.status_label.configure(text="Démarrage...", text_color="gray70")
        self.summary_label.configure(text="")

        threading.Thread(target=self._run_worker, daemon=True).start()

    def _run_worker(self):
        try:
            use_embeddings = self.embeddings_var.get()
            gap_penalty = self.gap_penalty_var.get()

            self._set_status("Lecture des fichiers...")
            cues = lc.parse_srt(self.srt_path)
            ref_lines = lc.read_lyrics_lines(self.lyrics_path)

            if use_embeddings:
                self._set_status("Chargement du modèle d'embeddings (~470 Mo)...")
            sim = lc.Similarity(use_embeddings=use_embeddings)

            self._set_status("Alignement des paroles avec les sous-titres...")
            ops = lc.align_sequences(ref_lines, [c.text for c in cues], sim, gap_penalty=gap_penalty)

            n_match = sum(1 for o in ops if o[0] == "match")
            n_missing = sum(1 for o in ops if o[0] == "missing")
            n_extra = sum(1 for o in ops if o[0] == "extra")

            self._set_status("Application de la correction (timing préservé)...")
            corrected_cues = lc.apply_correction(cues, ref_lines, ops)

            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            lc.write_srt(corrected_cues, self.output_path)

            summary = (
                f"{n_match} correspondance(s), "
                f"{n_missing} répétition(s) manquante(s) insérée(s), "
                f"{n_extra} sous-titre(s) extra conservé(s)."
            )
            self._on_success(summary)
        except Exception as e:
            traceback.print_exc()
            self._on_error(str(e))

    def _set_status(self, text: str):
        self.after(0, lambda: self.status_label.configure(text=text, text_color="gray70"))

    def _on_success(self, summary: str):
        def _update():
            self.progress_bar.stop()
            self.progress_bar.set(1)
            self.status_label.configure(text=f"Terminé : {self.output_path.name}", text_color="#4caf50")
            self.summary_label.configure(text=summary)
            self.run_button.configure(state="normal", text="Corriger les paroles")
            self.is_running = False
            messagebox.showinfo("Terminé", f"SRT corrigé :\n{self.output_path}\n\n{summary}")
        self.after(0, _update)

    def _on_error(self, message: str):
        def _update():
            self.progress_bar.stop()
            self.progress_bar.set(0)
            self.status_label.configure(text="Erreur — voir détails", text_color="#e53935")
            self.run_button.configure(state="normal", text="Corriger les paroles")
            self.is_running = False
            messagebox.showerror("Erreur", message)
        self.after(0, _update)


# ====================================================================== App

class KhassidaSubtitlesApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Khassida Subtitles")
        self.geometry("680x760")
        self.minsize(580, 660)

        title = ctk.CTkLabel(self, text="Khassida Subtitles", font=ctk.CTkFont(size=22, weight="bold"))
        title.pack(pady=(20, 0))
        subtitle = ctk.CTkLabel(
            self,
            text="Génère et corrige des sous-titres pour tes enregistrements de khassidas",
            font=ctk.CTkFont(size=12), text_color="gray70",
        )
        subtitle.pack(pady=(0, 12))

        self.tabview = ctk.CTkTabview(self, width=640)
        self.tabview.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        tab1 = self.tabview.add("1. Générer SRT")
        tab2 = self.tabview.add("2. Corriger les paroles")

        GenerateTab(tab1).pack(fill="both", expand=True)
        CorrectTab(tab2).pack(fill="both", expand=True)


if __name__ == "__main__":
    app = KhassidaSubtitlesApp()
    app.mainloop()
