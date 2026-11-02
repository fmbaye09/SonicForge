"""
Moteur de conversion Vidéo vers Audio haute performance basé sur FFmpeg.
Supporte l'extraction brute, le réencodage (MP3, WAV, FLAC, AAC, OGG),
la normalisation audio, le découpage et le traitement par lot.
"""

import os
import sys
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

from .config import (
    VIDEO_EXTENSIONS, AUDIO_EXTENSIONS, AUDIO_OUTPUT_FORMATS, 
    DEFAULT_CONVERT_DIR
)


def get_media_duration(file_path: Path) -> Optional[float]:
    """Récupère la durée en secondes d'un fichier média via ffprobe."""
    ffprobe_cmd = shutil.which("ffprobe")
    if not ffprobe_cmd:
        return None

    try:
        cmd = [
            ffprobe_cmd,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            return float(res.stdout.strip())
    except Exception:
        pass
    return None


def get_media_info(file_path: Path) -> Dict[str, Any]:
    """Récupère les métadonnées audio et vidéo du fichier."""
    ffprobe_cmd = shutil.which("ffprobe")
    info: Dict[str, Any] = {
        "file_name": file_path.name,
        "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2) if file_path.exists() else 0,
        "duration_sec": 0,
        "duration_formatted": "00:00:00",
        "has_audio": False,
        "has_video": False,
        "audio_codec": "Inconnu",
        "audio_sample_rate": None,
        "audio_channels": None,
        "video_codec": None,
    }

    if not ffprobe_cmd or not file_path.exists():
        return info

    try:
        cmd = [
            ffprobe_cmd,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(file_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            duration = float(data.get("format", {}).get("duration", 0) or 0)
            info["duration_sec"] = duration
            
            hours = int(duration // 3600)
            mins = int((duration % 3600) // 60)
            secs = int(duration % 60)
            info["duration_formatted"] = f"{hours:02d}:{mins:02d}:{secs:02d}"

            for s in data.get("streams", []):
                codec_type = s.get("codec_type")
                if codec_type == "audio" and not info["has_audio"]:
                    info["has_audio"] = True
                    info["audio_codec"] = s.get("codec_name", "Inconnu")
                    info["audio_sample_rate"] = s.get("sample_rate")
                    info["audio_channels"] = s.get("channels")
                elif codec_type == "video" and not info["has_video"]:
                    info["has_video"] = True
                    info["video_codec"] = s.get("codec_name")
    except Exception:
        pass

    return info


def convert_video_to_audio(
    input_file: Path,
    output_file: Optional[Path] = None,
    output_format: str = "mp3",
    bitrate: Optional[str] = "320k",
    channels: Optional[int] = None,
    sample_rate: Optional[int] = None,
    normalize: bool = False,
    volume: Optional[float] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    on_progress: Optional[Callable[[float], None]] = None,
    on_log: Optional[Callable[[str], None]] = None,
) -> Path:
    """
    Convertit un fichier vidéo (ou audio) vers un format audio cible avec FFmpeg.
    
    :param input_file: Chemin vers le fichier source
    :param output_file: Chemin vers le fichier de destination (si omis, créé auto)
    :param output_format: 'mp3', 'wav', 'flac', 'aac', 'ogg', ou 'copy'
    :param bitrate: Débit binaire (ex: '320k', '256k', '192k', '128k')
    :param channels: 1 (mono), 2 (stéréo) ou None (original)
    :param sample_rate: Fréquence d'échantillonnage en Hz (ex: 44100, 48000)
    :param normalize: Active la normalisation EBU R128 (loudnorm)
    :param volume: Multiplicateur de volume (ex: 1.5 pour 150%)
    :param start_time: Point de départ optionnel (HH:MM:SS ou secondes)
    :param end_time: Point de fin optionnel (HH:MM:SS ou secondes)
    :param on_progress: Callback appelé avec le pourcentage (0 à 100)
    :param on_log: Callback recevant les lignes de logs
    :return: Chemin du fichier audio créé
    """
    ffmpeg_cmd = shutil.which("ffmpeg")
    if not ffmpeg_cmd:
        raise RuntimeError("FFmpeg n'a pas été trouvé sur ce système. Veuillez l'installer.")

    input_path = Path(input_file).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Le fichier source n'existe pas : {input_path}")

    fmt_info = AUDIO_OUTPUT_FORMATS.get(output_format.lower())
    if not fmt_info:
        raise ValueError(f"Format de sortie inconnu : {output_format}")

    # Détermination du fichier de sortie
    if output_file is None:
        target_dir = DEFAULT_CONVERT_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        ext = fmt_info["ext"]
        output_path = target_dir / f"{input_path.stem}{ext}"
    else:
        output_path = Path(output_file).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Récupération de la durée pour le calcul de progression
    total_duration = get_media_duration(input_path) or 0.0

    # Construction de la commande FFmpeg
    cmd: List[str] = [ffmpeg_cmd, "-y"]

    if start_time:
        cmd.extend(["-ss", str(start_time)])

    cmd.extend(["-i", str(input_path)])

    if end_time:
        cmd.extend(["-to", str(end_time)])

    # Exclusion de la vidéo
    cmd.append("-vn")

    # Filtres audio (volume, normalisation)
    audio_filters: List[str] = []
    if volume and volume != 1.0:
        audio_filters.append(f"volume={volume:.2f}")
    if normalize:
        audio_filters.append("loudnorm")

    if audio_filters:
        cmd.extend(["-filter:a", ",".join(audio_filters)])

    # Codec audio et options spécifiques
    if output_format.lower() == "copy":
        cmd.extend(["-c:a", "copy"])
    else:
        cmd.extend(["-c:a", fmt_info["codec"]])
        if bitrate and fmt_info["bitrates"]:
            cmd.extend(["-b:a", bitrate])
        if channels:
            cmd.extend(["-ac", str(channels)])
        if sample_rate:
            cmd.extend(["-ar", str(sample_rate)])

    cmd.append(str(output_path))

    if on_log:
        on_log(f"🎬 Début conversion : {input_path.name} -> {output_path.name}")
        on_log(f"⚙️ Commande FFmpeg : {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )

    time_pattern = re.compile(r"time=(\d+):(\d{2}):(\d{2})\.(\d+)")

    for line in iter(process.stdout.readline, ""):
        line_clean = line.strip()
        if not line_clean:
            continue

        if on_log:
            # Ne pas polluer les logs avec chaque micro-tick
            if not line_clean.startswith("size=") and not line_clean.startswith("frame="):
                on_log(line_clean)

        if total_duration > 0:
            match = time_pattern.search(line_clean)
            if match:
                h, m, s, ms = map(int, match.groups())
                current_sec = h * 3600 + m * 60 + s + ms / 100
                progress_pct = min(99.0, max(0.0, (current_sec / total_duration) * 100))
                if on_progress:
                    on_progress(progress_pct)

    process.wait()

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg a échoué avec le code d'erreur {process.returncode}")

    if on_progress:
        on_progress(100.0)

    if on_log:
        on_log(f"✅ Conversion terminée : {output_path}")

    return output_path


def batch_convert(
    input_paths: List[Path],
    output_dir: Path,
    output_format: str = "mp3",
    bitrate: Optional[str] = "320k",
    channels: Optional[int] = None,
    sample_rate: Optional[int] = None,
    normalize: bool = False,
    volume: Optional[float] = None,
    on_file_progress: Optional[Callable[[int, int, str], None]] = None,
    on_log: Optional[Callable[[str], None]] = None,
) -> List[Path]:
    """Convertit plusieurs fichiers par lot."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Path] = []
    total = len(input_paths)

    fmt_info = AUDIO_OUTPUT_FORMATS.get(output_format.lower(), AUDIO_OUTPUT_FORMATS["mp3"])
    ext = fmt_info["ext"]

    for idx, path in enumerate(input_paths, 1):
        if on_file_progress:
            on_file_progress(idx, total, path.name)

        target_file = output_dir / f"{path.stem}{ext}"
        try:
            converted = convert_video_to_audio(
                input_file=path,
                output_file=target_file,
                output_format=output_format,
                bitrate=bitrate,
                channels=channels,
                sample_rate=sample_rate,
                normalize=normalize,
                volume=volume,
                on_log=on_log
            )
            results.append(converted)
        except Exception as e:
            if on_log:
                on_log(f"❌ Erreur sur {path.name} : {e}")

    return results

