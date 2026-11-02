#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio Separator - Séparation Parole / Instrumental
=================================================
Outil avec interface graphique pour séparer un fichier audio
en deux pistes : voix (parole) et accompagnement (instrumental).

Utilise le modèle Demucs de Meta AI.

Installation des dépendances:
    pip install demucs torchaudio soundfile

Usage:
    python audio_separator.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
import subprocess
import shutil
from pathlib import Path


def check_cuda_available():
    """Vérifie si CUDA est disponible avec PyTorch"""
    try:
        import torch
        return torch.cuda.is_available()
    except:
        return False


def check_soundfile():
    """Vérifie si soundfile est installé (backend audio)"""
    try:
        import soundfile
        return True
    except ImportError:
        return False


class AudioSeparatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 Audio Separator - Parole & Instrumental")
        self.root.geometry("700x600")
        self.root.minsize(600, 500)

        # Détections
        self.cuda_available = check_cuda_available()
        self.soundfile_ok = check_soundfile()

        # Variables
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.home() / "Music" / "Separated"))
        self.model = tk.StringVar(value="htdemucs")
        self.device = tk.StringVar(value="cuda" if self.cuda_available else "cpu")
        self.progress = tk.DoubleVar(value=0)
        self.status = tk.StringVar(value="Prêt")

        self.setup_ui()
        self.check_dependencies()

    def setup_ui(self):
        """Configuration de l'interface utilisateur"""

        style = ttk.Style()
        style.configure("Title.TLabel", font=("Helvetica", 16, "bold"))
        style.configure("Subtitle.TLabel", font=("Helvetica", 10), foreground="gray")
        style.configure("Status.TLabel", font=("Helvetica", 10, "italic"))

        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Titre
        ttk.Label(main_frame, text="🎵 Audio Separator", style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, pady=(0, 5), sticky=tk.W)
        ttk.Label(main_frame, text="Sépare la parole et l'instrumental d'un fichier audio", 
                  style="Subtitle.TLabel").grid(row=1, column=0, columnspan=3, pady=(0, 20), sticky=tk.W)

        # === Section Fichier Source ===
        file_frame = ttk.LabelFrame(main_frame, text=" Fichier Audio Source ", padding="10")
        file_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)

        ttk.Label(file_frame, text="Fichier:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Entry(file_frame, textvariable=self.input_file).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(file_frame, text="📁 Parcourir", command=self.browse_input).grid(row=0, column=2)

        # === Section Options ===
        options_frame = ttk.LabelFrame(main_frame, text=" Options de Séparation ", padding="10")
        options_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        options_frame.columnconfigure(1, weight=1)

        # Modèle
        ttk.Label(options_frame, text="Modèle:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        model_combo = ttk.Combobox(options_frame, textvariable=self.model, state="readonly", width=30)
        model_combo["values"] = [
            "htdemucs",
            "htdemucs_ft",
            "htdemucs_6s",
            "hdemucs_mmi",
            "mdx",
            "mdx_extra",
            "mdx_q",
            "demucs",
            "demucs_quantized"
        ]
        model_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)

        model_info = ttk.Label(options_frame, text="htdemucs = meilleur rapport qualité/vitesse", 
                               foreground="gray", font=("Helvetica", 9))
        model_info.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))

        # Device
        ttk.Label(options_frame, text="Processeur:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        device_frame = ttk.Frame(options_frame)
        device_frame.grid(row=2, column=1, sticky=tk.W, pady=5)

        self.cpu_radio = ttk.Radiobutton(device_frame, text="CPU", variable=self.device, value="cpu")
        self.cpu_radio.pack(side=tk.LEFT, padx=(0, 15))

        self.gpu_radio = ttk.Radiobutton(device_frame, text="GPU (CUDA)", variable=self.device, value="cuda")
        self.gpu_radio.pack(side=tk.LEFT)

        # Label d'avertissement CUDA
        if not self.cuda_available:
            self.gpu_radio.config(state=tk.DISABLED)
            cuda_warning = ttk.Label(options_frame, 
                text="⚠️ CUDA non détecté - PyTorch CPU installé. Pour utiliser le GPU: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118", 
                foreground="orange", font=("Helvetica", 8), wraplength=500)
            cuda_warning.grid(row=3, column=1, sticky=tk.W, pady=(0, 5))
        else:
            cuda_ok = ttk.Label(options_frame, text="✅ CUDA détecté et prêt", foreground="green", font=("Helvetica", 9))
            cuda_ok.grid(row=3, column=1, sticky=tk.W, pady=(0, 5))

        # === Section Dossier de Sortie ===
        output_frame = ttk.LabelFrame(main_frame, text=" Dossier de Sortie ", padding="10")
        output_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)

        ttk.Label(output_frame, text="Dossier:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Entry(output_frame, textvariable=self.output_dir).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(output_frame, text="📁 Choisir", command=self.browse_output).grid(row=0, column=2)

        # === Barre de progression ===
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 5))
        progress_frame.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress, maximum=100, mode="determinate")
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        ttk.Label(progress_frame, textvariable=self.status, style="Status.TLabel").grid(
            row=0, column=1, sticky=tk.E)

        # === Boutons d'action ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=6, column=0, columnspan=3, pady=(10, 10))

        self.separate_btn = ttk.Button(btn_frame, text="🚀 Lancer la Séparation", 
                                       command=self.start_separation, width=25)
        self.separate_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="📂 Ouvrir le Dossier", 
                   command=self.open_output_folder, width=20).pack(side=tk.LEFT, padx=5)

        # === Console/Logs ===
        log_frame = ttk.LabelFrame(main_frame, text=" Logs ", padding="5")
        log_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD, 
                                                   font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.log_text.config(state=tk.DISABLED)

        # === Barre de statut ===
        status_bar = ttk.Frame(main_frame)
        status_bar.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        self.dep_status = ttk.Label(status_bar, text="🔍 Vérification des dépendances...", 
                                    foreground="orange")
        self.dep_status.pack(side=tk.LEFT)

    def log(self, message, tag=""):
        """Ajoute un message dans la console"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def check_dependencies(self):
        """Vérifie que demucs est installé"""
        def check():
            try:
                import demucs
                self.dep_status.config(text="✅ Demucs installé - Prêt à l'emploi", foreground="green")
                self.log("✅ Demucs détecté et prêt à l'emploi")
                if not self.cuda_available:
                    self.log("⚠️ Mode CPU activé (CUDA non disponible)")
                if not self.soundfile_ok:
                    self.log("⚠️ soundfile non détecté - tentative d'utilisation du backend par défaut")
            except ImportError:
                self.dep_status.config(text="❌ Demucs non installé", foreground="red")
                self.log("❌ Demucs n'est pas installé!")
                self.log("💡 Installez-le avec: pip install demucs")
                messagebox.showwarning(
                    "Dépendance manquante",
                    "Demucs n'est pas installé.\n\n"
                    "Installez-le avec la commande:\n"
                    "pip install demucs"
                )

        threading.Thread(target=check, daemon=True).start()

    def browse_input(self):
        """Sélection du fichier audio d'entrée"""
        filetypes = [
            ("Fichiers audio", "*.mp3 *.wav *.flac *.ogg *.m4a *.wma *.aac"),
            ("MP3", "*.mp3"),
            ("WAV", "*.wav"),
            ("FLAC", "*.flac"),
            ("OGG", "*.ogg"),
            ("M4A", "*.m4a"),
            ("Tous les fichiers", "*.*")
        ]
        filename = filedialog.askopenfilename(
            title="Sélectionner un fichier audio",
            filetypes=filetypes
        )
        if filename:
            self.input_file.set(filename)
            input_path = Path(filename)
            default_output = input_path.parent / f"{input_path.stem}_separated"
            self.output_dir.set(str(default_output))
            self.log(f"📁 Fichier sélectionné: {filename}")

    def browse_output(self):
        """Sélection du dossier de sortie"""
        directory = filedialog.askdirectory(title="Choisir le dossier de sortie")
        if directory:
            self.output_dir.set(directory)
            self.log(f"📂 Dossier de sortie: {directory}")

    def open_output_folder(self):
        """Ouvre le dossier de sortie dans l'explorateur"""
        output_path = self.output_dir.get()
        if os.path.exists(output_path):
            if sys.platform == "win32":
                os.startfile(output_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", output_path])
            else:
                subprocess.run(["xdg-open", output_path])
        else:
            messagebox.showinfo("Info", "Le dossier de sortie n'existe pas encore.")

    def start_separation(self):
        """Lance la séparation dans un thread séparé"""
        input_file = self.input_file.get()
        output_dir = self.output_dir.get()

        if not input_file:
            messagebox.showerror("Erreur", "Veuillez sélectionner un fichier audio.")
            return

        if not os.path.exists(input_file):
            messagebox.showerror("Erreur", "Le fichier sélectionné n'existe pas.")
            return

        # Forcer CPU si CUDA non disponible
        selected_device = self.device.get()
        if selected_device == "cuda" and not self.cuda_available:
            self.log("⚠️ CUDA sélectionné mais non disponible. Basculement vers CPU...")
            self.device.set("cpu")
            selected_device = "cpu"

        self.separate_btn.config(state=tk.DISABLED)
        self.progress.set(0)
        self.status.set("Séparation en cours...")
        self.log("\n" + "="*50)
        self.log("🚀 Démarrage de la séparation audio")
        self.log(f"   Fichier: {input_file}")
        self.log(f"   Modèle: {self.model.get()}")
        self.log(f"   Device: {selected_device}")
        self.log("="*50)

        thread = threading.Thread(target=self.run_separation, args=(input_file, output_dir, selected_device))
        thread.daemon = True
        thread.start()

    def run_separation(self, input_file, output_dir, device):
        """Exécute la séparation avec demucs"""
        try:
            os.makedirs(output_dir, exist_ok=True)

            # Arguments pour demucs
            args = [
                "-n", self.model.get(),
                "--device", device,
                "-o", output_dir,
                "--filename", "{track}/{stem}.{ext}",
                input_file
            ]

            self.log(f"\n⚙️  Commande: demucs {' '.join(args)}")
            self.log("⏳ Séparation en cours... (cela peut prendre plusieurs minutes)\n")

            # Exécuter via subprocess avec les bonnes variables d'environnement
            env = os.environ.copy()

            # Forcer soundfile comme backend si disponible
            if self.soundfile_ok:
                env["TORCHAUDIO_BACKEND"] = "soundfile"
                self.log("🔧 Backend audio: soundfile")
            else:
                self.log("⚠️ soundfile non disponible, utilisation du backend par défaut")

            cmd = [sys.executable, "-m", "demucs.separate"] + args

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                env=env
            )

            for line in process.stdout:
                line = line.strip()
                if line:
                    self.log(line)
                    if "%" in line:
                        try:
                            import re
                            match = re.search(r'(\d+(?:\.\d+)?)%', line)
                            if match:
                                pct = float(match.group(1))
                                self.progress.set(pct)
                                self.status.set(f"{pct:.0f}%")
                                self.root.update_idletasks()
                        except:
                            pass

            process.wait()

            if process.returncode == 0:
                self.progress.set(100)
                self.status.set("Terminé ✓")

                self.log("\n" + "="*50)
                self.log("✅ Séparation terminée avec succès!")
                self.log(f"📂 Fichiers sauvegardés dans: {output_dir}")

                output_path = Path(output_dir)
                for root_dir, dirs, files in os.walk(output_path):
                    for file in files:
                        file_path = os.path.join(root_dir, file)
                        rel_path = os.path.relpath(file_path, output_path)
                        self.log(f"   📄 {rel_path}")

                self.log("="*50)

                self.root.after(0, lambda: messagebox.showinfo(
                    "Succès",
                    f"Séparation terminée avec succès!\n\n"
                    f"Les fichiers ont été sauvegardés dans:\n{output_dir}\n\n"
                    f"Vous trouverez les pistes 'vocals' (parole) et 'no_vocals' (instrumental)."
                ))
            else:
                raise Exception(f"Le processus a retourné le code {process.returncode}")

        except Exception as e:
            self.progress.set(0)
            self.status.set("Erreur ❌")
            self.log(f"\n❌ ERREUR: {str(e)}")

            # Message d'aide spécifique pour l'erreur de backend
            if "backend" in str(e).lower():
                self.log("\n💡 SOLUTION: Installez soundfile avec:")
                self.log("   pip install soundfile")
                self.root.after(0, lambda: messagebox.showerror(
                    "Erreur - Backend audio manquant",
                    f"La séparation a échoué car le backend audio est manquant.\n\n"
                    f"Erreur: {str(e)}\n\n"
                    f"Solution: Exécutez cette commande dans votre terminal:\n"
                    f"pip install soundfile\n\n"
                    f"Puis relancez l'application."
                ))
            else:
                self.root.after(0, lambda: messagebox.showerror("Erreur", f"La séparation a échoué:\n{str(e)}"))

        finally:
            self.root.after(0, lambda: self.separate_btn.config(state=tk.NORMAL))


def main():
    root = tk.Tk()
    try:
        root.iconbitmap("")
    except:
        pass

    app = AudioSeparatorApp(root)

    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    root.mainloop()


if __name__ == "__main__":
    main()
