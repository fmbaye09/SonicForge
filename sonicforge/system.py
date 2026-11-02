"""
Diagnostic matériel et détection des dépendances système (FFmpeg, CUDA, PyTorch, Demucs, Whisper).
"""

import os
import sys
import shutil
import subprocess
from typing import Dict, Any, Tuple


def check_ffmpeg() -> Tuple[bool, str]:
    """Vérifie si FFmpeg est disponible dans le PATH ou accessible."""
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        return False, "FFmpeg non trouvé dans le PATH système."
    try:
        proc = subprocess.run(
            [ffmpeg_path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5
        )
        first_line = proc.stdout.splitlines()[0] if proc.stdout else "FFmpeg détecté"
        return True, first_line
    except Exception as e:
        return False, f"Erreur lors de l'exécution de FFmpeg: {e}"


def check_ffprobe() -> Tuple[bool, str]:
    """Vérifie si FFprobe est disponible dans le PATH."""
    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        return False, "FFprobe non trouvé dans le PATH."
    try:
        proc = subprocess.run(
            [ffprobe_path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5
        )
        first_line = proc.stdout.splitlines()[0] if proc.stdout else "FFprobe détecté"
        return True, first_line
    except Exception as e:
        return False, f"Erreur FFprobe: {e}"


def check_cuda() -> Tuple[bool, str]:
    """Vérifie si CUDA (NVIDIA GPU) est disponible avec PyTorch."""
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            return True, f"NVIDIA GPU actif : {device_name} ({vram_gb:.1f} Go VRAM)"
        return False, "CUDA non disponible (Mode processeur CPU actif)"
    except Exception as e:
        return False, f"PyTorch non disponible ou erreur CUDA: {e}"


def check_pytorch() -> Tuple[bool, str]:
    """Vérifie la version de PyTorch."""
    try:
        import torch
        return True, f"PyTorch v{torch.__version__}"
    except ImportError:
        return False, "Non installé (pip install torch)"
    except Exception as e:
        return False, f"Erreur: {e}"


def check_demucs() -> Tuple[bool, str]:
    """Vérifie si Demucs est installé."""
    try:
        import demucs
        version = getattr(demucs, "__version__", "installé")
        return True, f"Demucs v{version}"
    except ImportError:
        return False, "Non installé (pip install demucs)"
    except Exception as e:
        return False, f"Erreur: {e}"


def check_whisper() -> Tuple[bool, str]:
    """Vérifie si stable-whisper ou openai-whisper est installé."""
    try:
        import stable_whisper
        return True, "stable-whisper prêt"
    except ImportError:
        try:
            import whisper
            return True, "openai-whisper installé (stable-whisper recommandé)"
        except ImportError:
            return False, "Non installé (pip install stable-ts)"
    except Exception as e:
        return False, f"Erreur: {e}"


def check_soundfile() -> Tuple[bool, str]:
    """Vérifie le backend audio soundfile."""
    try:
        import soundfile
        return True, f"soundfile v{soundfile.__version__}"
    except ImportError:
        return False, "Non installé (optionnel mais conseillé: pip install soundfile)"
    except Exception as e:
        return False, f"Erreur: {e}"


def check_sentence_transformers() -> Tuple[bool, str]:
    """Vérifie sentence-transformers pour les embeddings de sous-titres."""
    try:
        import sentence_transformers
        return True, "sentence-transformers prêt"
    except ImportError:
        return False, "Non installé (optionnel pour correction par IA: pip install sentence-transformers)"
    except Exception as e:
        return False, f"Erreur: {e}"


def get_full_diagnostics() -> Dict[str, Tuple[bool, str]]:
    """Génère un diagnostic complet du système."""
    return {
        "ffmpeg": check_ffmpeg(),
        "ffprobe": check_ffprobe(),
        "pytorch": check_pytorch(),
        "cuda": check_cuda(),
        "demucs": check_demucs(),
        "whisper": check_whisper(),
        "soundfile": check_soundfile(),
        "sentence_transformers": check_sentence_transformers(),
    }


def format_diagnostic_report() -> str:
    """Crée un rapport lisible en texte pour la console ou l'interface."""
    diag = get_full_diagnostics()
    lines = [
        "===========================================================",
        "            DIAGNOSTIC SYSTÈME - SONICFORGE                ",
        "===========================================================",
    ]
    for key, (ok, msg) in diag.items():
        status = "✅ OK      " if ok else "⚠️ MANQUANT"
        lines.append(f"[{status}] {key:<20} : {msg}")
    lines.append("===========================================================")
    return "\n".join(lines)


if __name__ == "__main__":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print(format_diagnostic_report())
