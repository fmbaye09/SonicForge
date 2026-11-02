"""
Moteur de séparation Audio (Voix / Instrumental) basé sur Meta Demucs.
Permet d'isoler la parole/le chant et l'accompagnement instrumental.
"""

import os
import sys
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

from .config import DEMUCS_MODELS, DEFAULT_SEPARATE_DIR
from .system import check_cuda, check_soundfile


def separate_audio(
    input_file: Path,
    output_dir: Optional[Path] = None,
    model: str = "htdemucs",
    device: Optional[str] = None,
    two_stems: bool = True,
    mp3_output: bool = True,
    mp3_bitrate: int = 320,
    on_progress: Optional[Callable[[float], None]] = None,
    on_log: Optional[Callable[[str], None]] = None,
) -> Dict[str, Path]:
    """
    Sépare un fichier audio en pistes voix et instrumental via Demucs.
    
    :param input_file: Fichier audio à séparer
    :param output_dir: Dossier de destination
    :param model: Modèle Demucs ('htdemucs', 'htdemucs_ft', etc.)
    :param device: 'cuda' ou 'cpu' (si None, auto-détecté)
    :param two_stems: Si True, sépare en vocals et no_vocals (instrumental)
    :param mp3_output: Si True, convertit les stems en MP3 haute qualité
    :param mp3_bitrate: Débit MP3 (défaut 320 kbps)
    :param on_progress: Callback de progression (0 à 100)
    :param on_log: Callback recevant les lignes de logs
    :return: Dictionnaire des fichiers générés {stem_name: path}
    """
    input_path = Path(input_file).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Fichier audio introuvable : {input_path}")

    # Détection CUDA
    cuda_ok, _ = check_cuda()
    if device is None:
        device = "cuda" if cuda_ok else "cpu"
    elif device == "cuda" and not cuda_ok:
        if on_log:
            on_log("⚠️ CUDA non disponible, basculement automatique sur CPU.")
        device = "cpu"

    # Dossier de sortie
    if output_dir is None:
        target_dir = DEFAULT_SEPARATE_DIR / input_path.stem
    else:
        target_dir = Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    # Paramètres Demucs
    args = [
        "-n", model,
        "--device", device,
        "-o", str(target_dir),
        "--filename", "{track}/{stem}.{ext}",
    ]

    if two_stems:
        args.extend(["--two-stems", "vocals"])

    if mp3_output:
        args.extend(["--mp3", f"--mp3-bitrate={mp3_bitrate}"])

    args.append(str(input_path))

    # Préparation environnement avec soundfile si disponible
    env = os.environ.copy()
    soundfile_ok, _ = check_soundfile()
    if soundfile_ok:
        env["TORCHAUDIO_BACKEND"] = "soundfile"

    if on_log:
        on_log(f"🎵 Début séparation audio Demucs : {input_path.name}")
        on_log(f"🧠 Modèle : {model} | Device : {device}")
        on_log(f"📂 Destination : {target_dir}")
        on_log(f"⚙️ Commande : demucs {' '.join(args)}")

    cmd = [sys.executable, "-m", "demucs.separate"] + args

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env
    )

    pct_pattern = re.compile(r"(\d+(?:\.\d+)?)%")

    for line in iter(process.stdout.readline, ""):
        line_clean = line.strip()
        if not line_clean:
            continue

        if on_log:
            on_log(line_clean)

        match = pct_pattern.search(line_clean)
        if match:
            try:
                pct = float(match.group(1))
                if on_progress:
                    on_progress(pct)
            except Exception:
                pass

    process.wait()

    if process.returncode != 0:
        raise RuntimeError(f"Demucs a échoué avec le code de sortie {process.returncode}")

    if on_progress:
        on_progress(100.0)

    # Recherche des fichiers générés
    found_files: Dict[str, Path] = {}
    for p in target_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in [".mp3", ".wav"]:
            stem_name = p.stem.lower()
            found_files[stem_name] = p
            if on_log:
                on_log(f"   ✨ Fichier prêt : {p.name}")

    if on_log:
        on_log(f"✅ Séparation terminée avec succès dans : {target_dir}")

    return found_files

