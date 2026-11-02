#!/usr/bin/env python3
"""
khassida_subtitles.py
----------------------
Génère des fichiers de sous-titres (.srt) pour des enregistrements de khassidas.

Deux modes :
  1. align       -> tu connais déjà le texte exact des paroles (fichier .txt).
                    Le programme aligne ce texte avec l'audio (timing) -> SRT.
                    C'est le mode RECOMMANDÉ et le plus fiable (surtout en wolof,
                    que Whisper ne reconnaît pas nativement).
  2. transcribe  -> tu n'as pas le texte. Le programme transcrit l'audio
                    directement avec Whisper (moins fiable selon la langue/dialecte).

Usage :
  # Mode alignement (texte connu)
  python khassida_subtitles.py align --audio chanson.mp3 --text paroles.txt --output chanson.srt

  # Mode transcription (texte inconnu)
  python khassida_subtitles.py transcribe --audio chanson.mp3 --output chanson.srt --language ar

  # Traitement par lot d'un dossier structuré comme ton pipeline d'import
  # (ex: data/<langue>/<titre>.mp3 + data/<langue>/<titre>.txt si dispo)
  python khassida_subtitles.py batch --input-dir data/ --output-dir subtitles/
"""

import argparse
import sys
from pathlib import Path

import stable_whisper

DEFAULT_MODEL = "medium"  # tiny/base/small/medium/large-v3 - plus gros = plus précis mais plus lent


def load_model(model_size: str = DEFAULT_MODEL):
    print(f"[*] Chargement du modèle Whisper '{model_size}'...")
    return stable_whisper.load_model(model_size)


def mode_align(audio_path: Path, text_path: Path, output_path: Path, language: str, model_size: str):
    """Alignement forcé : on connaît déjà les paroles, on cale juste le timing."""
    if not text_path.exists():
        sys.exit(f"[!] Fichier texte introuvable : {text_path}")

    text = text_path.read_text(encoding="utf-8").strip()
    if not text:
        sys.exit(f"[!] Fichier texte vide : {text_path}")

    model = load_model(model_size)
    print(f"[*] Alignement de '{audio_path.name}' avec le texte fourni...")
    result = model.align(str(audio_path), text, language=language)

    result.to_srt_vtt(str(output_path), word_level=False)
    print(f"[✓] SRT généré (alignement) : {output_path}")


def mode_transcribe(audio_path: Path, output_path: Path, language: str, model_size: str):
    """Transcription pure : on ne connaît pas le texte, Whisper le devine."""
    model = load_model(model_size)
    print(f"[*] Transcription de '{audio_path.name}' (langue: {language or 'auto-détection'})...")
    result = model.transcribe(str(audio_path), language=language)

    result.to_srt_vtt(str(output_path), word_level=False)
    print(f"[✓] SRT généré (transcription) : {output_path}")
    print("    ⚠ Vérifie la qualité du résultat : Whisper peut être peu fiable")
    print("      sur du wolof ou de l'arabe classique récité.")


def mode_batch(input_dir: Path, output_dir: Path, language: str, model_size: str):
    """
    Traite un dossier structuré par langue, comme ton pipeline d'import existant :
        input_dir/
          wolof/
            titre1.mp3
            titre1.txt   <- si présent, on aligne. Sinon, on transcrit.
          arabe/
            titre2.mp3
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_extensions = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}

    model = load_model(model_size)

    audio_files = [p for p in input_dir.rglob("*") if p.suffix.lower() in audio_extensions]
    if not audio_files:
        sys.exit(f"[!] Aucun fichier audio trouvé dans {input_dir}")

    print(f"[*] {len(audio_files)} fichier(s) audio trouvé(s).")

    for audio_path in audio_files:
        relative = audio_path.relative_to(input_dir)
        text_path = audio_path.with_suffix(".txt")
        out_path = output_dir / relative.with_suffix(".srt")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Langue déduite du sous-dossier si possible, sinon valeur par défaut fournie
        lang_for_file = language
        print(f"\n--- {relative} ---")

        try:
            if text_path.exists() and text_path.read_text(encoding="utf-8").strip():
                text = text_path.read_text(encoding="utf-8").strip()
                print(f"[*] Texte trouvé -> alignement forcé")
                result = model.align(str(audio_path), text, language=lang_for_file)
            else:
                print(f"[*] Pas de texte -> transcription Whisper")
                result = model.transcribe(str(audio_path), language=lang_for_file)

            result.to_srt_vtt(str(out_path), word_level=False)
            print(f"[✓] {out_path}")
        except Exception as e:
            print(f"[!] Échec sur {relative} : {e}")


def main():
    parser = argparse.ArgumentParser(description="Génération de sous-titres SRT pour khassidas")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                         help="Taille du modèle Whisper (tiny/base/small/medium/large-v3). Défaut: medium")

    sub = parser.add_subparsers(dest="mode", required=True)

    p_align = sub.add_parser("align", help="Alignement forcé (texte déjà connu)")
    p_align.add_argument("--audio", required=True, type=Path)
    p_align.add_argument("--text", required=True, type=Path)
    p_align.add_argument("--output", required=True, type=Path)
    p_align.add_argument("--language", default="ar", help="Code langue (ex: ar, fr). Défaut: ar")

    p_trans = sub.add_parser("transcribe", help="Transcription pure (texte inconnu)")
    p_trans.add_argument("--audio", required=True, type=Path)
    p_trans.add_argument("--output", required=True, type=Path)
    p_trans.add_argument("--language", default=None, help="Code langue (ex: ar, fr). Défaut: auto-détection")

    p_batch = sub.add_parser("batch", help="Traitement par lot d'un dossier")
    p_batch.add_argument("--input-dir", required=True, type=Path)
    p_batch.add_argument("--output-dir", required=True, type=Path)
    p_batch.add_argument("--language", default="ar", help="Code langue par défaut. Défaut: ar")

    args = parser.parse_args()

    if args.mode == "align":
        if not args.audio.exists():
            sys.exit(f"[!] Audio introuvable : {args.audio}")
        mode_align(args.audio, args.text, args.output, args.language, args.model)

    elif args.mode == "transcribe":
        if not args.audio.exists():
            sys.exit(f"[!] Audio introuvable : {args.audio}")
        mode_transcribe(args.audio, args.output, args.language, args.model)

    elif args.mode == "batch":
        if not args.input_dir.exists():
            sys.exit(f"[!] Dossier introuvable : {args.input_dir}")
        mode_batch(args.input_dir, args.output_dir, args.language, args.model)


if __name__ == "__main__":
    main()
