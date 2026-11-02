"""
Configuration globale et constantes pour Media Arsenal.
"""

from pathlib import Path
import sys
import os

APP_NAME = "SonicForge"
APP_VERSION = "2.0.0"

# Dossiers par défaut
DEFAULT_OUTPUT_DIR = Path.home() / "Music" / "SonicForge"
DEFAULT_CONVERT_DIR = DEFAULT_OUTPUT_DIR / "Converted"
DEFAULT_SEPARATE_DIR = DEFAULT_OUTPUT_DIR / "Separated"
DEFAULT_SUBTITLES_DIR = DEFAULT_OUTPUT_DIR / "Subtitles"

# Formats vidéo supportés pour la conversion
VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", 
    ".webm", ".m4v", ".ts", ".3gp", ".vob", ".ogv"
}

# Formats audio supportés en entrée et sortie
AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", 
    ".wma", ".opus", ".aiff"
}

# Tous les fichiers médias supportés en entrée pour la conversion
MEDIA_INPUT_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

# Formats de sortie audio disponibles
AUDIO_OUTPUT_FORMATS = {
    "mp3": {
        "ext": ".mp3",
        "codec": "libmp3lame",
        "name": "MP3 (Universel)",
        "bitrates": ["128k", "192k", "256k", "320k"],
        "default_bitrate": "320k"
    },
    "wav": {
        "ext": ".wav",
        "codec": "pcm_s16le",
        "name": "WAV (Non compressé / Studio)",
        "bitrates": [],
        "default_bitrate": None
    },
    "flac": {
        "ext": ".flac",
        "codec": "flac",
        "name": "FLAC (Sans perte / Haute Fidélité)",
        "bitrates": [],
        "default_bitrate": None
    },
    "aac": {
        "ext": ".m4a",
        "codec": "aac",
        "name": "AAC / M4A (Haute efficacité)",
        "bitrates": ["128k", "192k", "256k", "320k"],
        "default_bitrate": "256k"
    },
    "ogg": {
        "ext": ".ogg",
        "codec": "libvorbis",
        "name": "OGG Vorbis",
        "bitrates": ["128k", "192k", "256k", "320k"],
        "default_bitrate": "192k"
    },
    "copy": {
        "ext": ".m4a",  # fallback si détection échoue
        "codec": "copy",
        "name": "Extraction brute (Sans réencodage - Ultra Rapide)",
        "bitrates": [],
        "default_bitrate": None
    }
}

# Modèles Demucs disponibles
DEMUCS_MODELS = [
    "htdemucs",
    "htdemucs_ft",
    "htdemucs_6s",
    "hdemucs_mmi",
    "mdx",
    "mdx_extra",
    "mdx_q",
]

# Modèles Whisper disponibles
WHISPER_MODELS = [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3"
]

# Langues pour transcription / alignement
SUBTITLE_LANGUAGES = [
    ("Arabe", "ar"),
    ("Français", "fr"),
    ("Anglais", "en"),
    ("Wolof (recommandé: ar ou align)", "ar"),
    ("Auto-détection", None),
]

