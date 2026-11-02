"""
Moteur de génération et alignement de sous-titres (SRT) basé sur Whisper / stable-whisper.
Supporte la transcription brute, l'alignement forcé texte-audio et le traitement par lot.
"""

import sys
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any

from .config import DEFAULT_SUBTITLES_DIR, AUDIO_EXTENSIONS


def is_whisper_available() -> bool:
    """Vérifie si stable-whisper ou whisper est présent."""
    try:
        import stable_whisper
        return True
    except ImportError:
        try:
            import whisper
            return True
        except ImportError:
            return False


def load_whisper_model(model_size: str = "medium", on_log: Optional[Callable[[str], None]] = None):
    """Charge le modèle Whisper via stable-whisper."""
    try:
        import stable_whisper
    except ImportError:
        raise ImportError(
            "Le module 'stable-whisper' n'est pas installé.\n"
            "Installez-le avec : pip install stable-ts"
        )

    if on_log:
        on_log(f"🧠 Chargement du modèle Whisper '{model_size}'...")
    return stable_whisper.load_model(model_size)


def align_subtitles(
    audio_path: Path,
    text_path: Path,
    output_path: Optional[Path] = None,
    language: Optional[str] = "ar",
    model_size: str = "medium",
    on_log: Optional[Callable[[str], None]] = None,
) -> Path:
    """
    Alignement forcé : cale le timing sur un texte exact connu.
    Idéal pour les chants, khassidas et langues non reconnues nativement (wolof).
    """
    audio_file = Path(audio_path).resolve()
    text_file = Path(text_path).resolve()

    if not audio_file.exists():
        raise FileNotFoundError(f"Fichier audio introuvable : {audio_file}")
    if not text_file.exists():
        raise FileNotFoundError(f"Fichier texte introuvable : {text_file}")

    text_content = text_file.read_text(encoding="utf-8").strip()
    if not text_content:
        raise ValueError(f"Le fichier de paroles est vide : {text_file}")

    if output_path is None:
        target_dir = DEFAULT_SUBTITLES_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        out_file = target_dir / f"{audio_file.stem}.srt"
    else:
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

    model = load_whisper_model(model_size, on_log=on_log)

    if on_log:
        on_log(f"📝 Alignement de '{audio_file.name}' avec le texte fourni...")
        on_log(f"🌍 Langue configurée : {language or 'auto'}")

    result = model.align(str(audio_file), text_content, language=language)
    result.to_srt_vtt(str(out_file), word_level=False)

    if on_log:
        on_log(f"✅ Fichier SRT généré avec succès : {out_file}")

    return out_file


def transcribe_audio(
    audio_path: Path,
    output_path: Optional[Path] = None,
    language: Optional[str] = None,
    model_size: str = "medium",
    on_log: Optional[Callable[[str], None]] = None,
) -> Path:
    """
    Transcription directe : Whisper écoute et génère le texte et le timing.
    """
    audio_file = Path(audio_path).resolve()
    if not audio_file.exists():
        raise FileNotFoundError(f"Fichier audio introuvable : {audio_file}")

    if output_path is None:
        target_dir = DEFAULT_SUBTITLES_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        out_file = target_dir / f"{audio_file.stem}.srt"
    else:
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

    model = load_whisper_model(model_size, on_log=on_log)

    if on_log:
        on_log(f"🎙️ Transcription de '{audio_file.name}' (langue: {language or 'auto-détection'})...")

    result = model.transcribe(str(audio_file), language=language)
    result.to_srt_vtt(str(out_file), word_level=False)

    if on_log:
        on_log(f"✅ Fichier SRT transcrit : {out_file}")
        on_log("💡 Conseil : Si le texte a des imperfections, utilisez le 'Correcteur de Paroles'.")

    return out_file


def batch_subtitles(
    input_dir: Path,
    output_dir: Path,
    language: Optional[str] = "ar",
    model_size: str = "medium",
    on_log: Optional[Callable[[str], None]] = None,
) -> List[Path]:
    """
    Traite un dossier entier :
    - Si un fichier .txt du même nom existe -> alignement forcé
    - Sinon -> transcription Whisper automatique
    """
    in_dir = Path(input_dir).resolve()
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    audio_files = [p for p in in_dir.rglob("*") if p.suffix.lower() in AUDIO_EXTENSIONS]
    if not audio_files:
        raise ValueError(f"Aucun fichier audio trouvé dans {in_dir}")

    if on_log:
        on_log(f"📁 {len(audio_files)} fichier(s) audio détecté(s) dans {in_dir.name}")

    model = load_whisper_model(model_size, on_log=on_log)
    generated: List[Path] = []

    for audio_path in audio_files:
        relative = audio_path.relative_to(in_dir)
        text_path = audio_path.with_suffix(".txt")
        out_path = out_dir / relative.with_suffix(".srt")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if on_log:
            on_log(f"\n--- Traitement : {relative} ---")

        try:
            if text_path.exists() and text_path.read_text(encoding="utf-8").strip():
                text = text_path.read_text(encoding="utf-8").strip()
                if on_log:
                    on_log("📄 Texte trouvé -> mode alignement forcé")
                result = model.align(str(audio_path), text, language=language)
            else:
                if on_log:
                    on_log("🎙️ Pas de texte -> mode transcription automatique")
                result = model.transcribe(str(audio_path), language=language)

            result.to_srt_vtt(str(out_path), word_level=False)
            generated.append(out_path)
            if on_log:
                on_log(f"✅ Enregistré : {out_path.name}")
        except Exception as e:
            if on_log:
                on_log(f"❌ Échec sur {relative} : {e}")

    return generated

