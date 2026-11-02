#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SONICFORGE - Point d'entrée principal unifié (CLI & GUI).
=========================================================
Lancez sans argument pour ouvrir l'interface graphique :
    python main.py

Ou utilisez en ligne de commande :
    python main.py convert --input video.mp4 --format mp3 --bitrate 320k
    python main.py separate --input chanson.mp3 --model htdemucs
    python main.py subtitles align --audio chanson.mp3 --text paroles.txt --output chanson.srt
    python main.py subtitles transcribe --audio chanson.mp3 --output chanson.srt
    python main.py correct --srt chanson.srt --lyrics paroles.txt --output chanson_corrigé.srt
    python main.py doctor
"""

import sys
import argparse
from pathlib import Path

# Assure l'encodage UTF-8 sous Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="SONICFORGE : Suite unifiée d'outils de traitement vidéo et audio par IA",
        epilog="Exécutez sans arguments pour lancer l'interface graphique."
    )
    sub = parser.add_subparsers(dest="command")

    # --- Commande GUI ---
    sub.add_parser("gui", help="Lance l'interface graphique unifiée (par défaut)")

    # --- Commande Convert ---
    p_conv = sub.add_parser("convert", help="Convertit une vidéo ou un fichier média en audio")
    p_conv.add_argument("-i", "--input", required=True, type=Path, help="Fichier vidéo/audio source ou dossier")
    p_conv.add_argument("-o", "--output", type=Path, default=None, help="Fichier ou dossier de sortie")
    p_conv.add_argument("-f", "--format", default="mp3", choices=["mp3", "wav", "flac", "aac", "ogg", "copy"], help="Format audio cible (défaut: mp3)")
    p_conv.add_argument("-b", "--bitrate", default="320k", help="Débit audio (ex: 320k, 256k, 192k)")
    p_conv.add_argument("--channels", type=int, choices=[1, 2], default=None, help="Nombre de canaux: 1 (mono) ou 2 (stéréo)")
    p_conv.add_argument("--sample-rate", type=int, default=None, help="Fréquence d'échantillonnage en Hz (ex: 44100, 48000)")
    p_conv.add_argument("--normalize", action="store_true", help="Normalise le volume sonore (EBU R128)")
    p_conv.add_argument("--volume", type=float, default=None, help="Multiplicateur de volume (ex: 1.5 pour +50%%)")
    p_conv.add_argument("--start", type=str, default=None, help="Point de départ du découpage (ex: 00:01:30)")
    p_conv.add_argument("--end", type=str, default=None, help="Point de fin du découpage")

    # --- Commande Separate (Demucs) ---
    p_sep = sub.add_parser("separate", help="Sépare la voix et l'instrumental avec Demucs")
    p_sep.add_argument("-i", "--input", required=True, type=Path, help="Fichier audio à séparer")
    p_sep.add_argument("-o", "--output", type=Path, default=None, help="Dossier de destination")
    p_sep.add_argument("-m", "--model", default="htdemucs", help="Modèle Demucs (défaut: htdemucs)")
    p_sep.add_argument("-d", "--device", default=None, choices=["cuda", "cpu"], help="Périphérique de calcul")
    p_sep.add_argument("--all-stems", action="store_true", help="Sépare en 4 pistes (au lieu de 2 pistes voix/instrumental)")
    p_sep.add_argument("--wav", action="store_true", help="Génère en format WAV plutôt que MP3")

    # --- Commande Subtitles (Whisper) ---
    p_sub = sub.add_parser("subtitles", help="Génère des sous-titres SRT (transcription ou alignement)")
    sub_subs = p_sub.add_subparsers(dest="sub_mode", required=True)

    # Subtitles align
    p_s_align = sub_subs.add_parser("align", help="Alignement forcé avec paroles connues")
    p_s_align.add_argument("-a", "--audio", required=True, type=Path, help="Fichier audio")
    p_s_align.add_argument("-t", "--text", required=True, type=Path, help="Fichier texte des paroles")
    p_s_align.add_argument("-o", "--output", type=Path, default=None, help="Fichier SRT en sortie")
    p_s_align.add_argument("-l", "--language", default="ar", help="Code langue (défaut: ar)")
    p_s_align.add_argument("--model", default="medium", help="Modèle Whisper (tiny/base/small/medium/large-v3)")

    # Subtitles transcribe
    p_s_trans = sub_subs.add_parser("transcribe", help="Transcription Whisper automatique")
    p_s_trans.add_argument("-a", "--audio", required=True, type=Path, help="Fichier audio")
    p_s_trans.add_argument("-o", "--output", type=Path, default=None, help="Fichier SRT en sortie")
    p_s_trans.add_argument("-l", "--language", default=None, help="Code langue (auto si omis)")
    p_s_trans.add_argument("--model", default="medium", help="Modèle Whisper")

    # Subtitles batch
    p_s_batch = sub_subs.add_parser("batch", help="Traitement d'un dossier entier")
    p_s_batch.add_argument("-i", "--input-dir", required=True, type=Path, help="Dossier d'entrée")
    p_s_batch.add_argument("-o", "--output-dir", required=True, type=Path, help="Dossier de sortie")
    p_s_batch.add_argument("-l", "--language", default="ar", help="Langue par défaut")
    p_s_batch.add_argument("--model", default="medium", help="Modèle Whisper")

    # --- Commande Correct (Lyrics Corrector) ---
    p_cor = sub.add_parser("correct", help="Corrige le texte d'un SRT avec les vraies paroles sans toucher aux timestamps")
    p_cor.add_argument("-s", "--srt", required=True, type=Path, help="Fichier .srt existant")
    p_cor.add_argument("-l", "--lyrics", required=True, type=Path, help="Fichier .txt des vraies paroles")
    p_cor.add_argument("-o", "--output", required=True, type=Path, help="Fichier .srt corrigé")
    p_cor.add_argument("--use-embeddings", action="store_true", help="Active le modèle d'embeddings multilingue")
    p_cor.add_argument("--gap-penalty", type=float, default=0.35, help="Pénalité de saut (défaut: 0.35)")

    # --- Commande Doctor ---
    sub.add_parser("doctor", help="Diagnostic complet du système et des dépendances")

    # Si aucun argument n'est fourni, on lance l'interface graphique
    if len(sys.argv) == 1:
        from sonicforge.gui.app import run_gui
        run_gui()
        return

    args = parser.parse_args()

    if args.command == "gui" or args.command is None:
        from sonicforge.gui.app import run_gui
        run_gui()

    elif args.command == "doctor":
        from sonicforge.system import format_diagnostic_report
        print(format_diagnostic_report())

    elif args.command == "convert":
        from sonicforge.converter import convert_video_to_audio, batch_convert, VIDEO_EXTENSIONS, AUDIO_EXTENSIONS
        in_path = args.input
        if in_path.is_dir():
            files = [p for p in in_path.iterdir() if p.suffix.lower() in (VIDEO_EXTENSIONS | AUDIO_EXTENSIONS)]
            print(f"[*] Traitement par lot de {len(files)} fichiers...")
            out_dir = args.output or in_path / "Converted"
            res = batch_convert(
                input_paths=files,
                output_dir=out_dir,
                output_format=args.format,
                bitrate=args.bitrate,
                channels=args.channels,
                sample_rate=args.sample_rate,
                normalize=args.normalize,
                volume=args.volume,
                on_log=print
            )
            print(f"[✓] {len(res)} fichier(s) converti(s) dans {out_dir}")
        else:
            res = convert_video_to_audio(
                input_file=in_path,
                output_file=args.output,
                output_format=args.format,
                bitrate=args.bitrate,
                channels=args.channels,
                sample_rate=args.sample_rate,
                normalize=args.normalize,
                volume=args.volume,
                start_time=args.start,
                end_time=args.end,
                on_log=print
            )
            print(f"[✓] Fichier audio créé : {res}")

    elif args.command == "separate":
        from sonicforge.separator import separate_audio
        results = separate_audio(
            input_file=args.input,
            output_dir=args.output,
            model=args.model,
            device=args.device,
            two_stems=not args.all_stems,
            mp3_output=not args.wav,
            on_log=print
        )
        print(f"[✓] Séparation terminée. Fichiers générés : {list(results.keys())}")

    elif args.command == "subtitles":
        from sonicforge.subtitles import align_subtitles, transcribe_audio, batch_subtitles
        if args.sub_mode == "align":
            out = align_subtitles(
                audio_path=args.audio,
                text_path=args.text,
                output_path=args.output,
                language=args.language,
                model_size=args.model,
                on_log=print
            )
            print(f"[✓] Sous-titres alignés : {out}")
        elif args.sub_mode == "transcribe":
            out = transcribe_audio(
                audio_path=args.audio,
                output_path=args.output,
                language=args.language,
                model_size=args.model,
                on_log=print
            )
            print(f"[✓] Sous-titres transcrits : {out}")
        elif args.sub_mode == "batch":
            outs = batch_subtitles(
                input_dir=args.input_dir,
                output_dir=args.output_dir,
                language=args.language,
                model_size=args.model,
                on_log=print
            )
            print(f"[✓] {len(outs)} fichiers traités.")

    elif args.command == "correct":
        from sonicforge.lyrics_corrector import correct_srt_file
        res = correct_srt_file(
            srt_path=args.srt,
            lyrics_path=args.lyrics,
            output_path=args.output,
            use_embeddings=args.use_embeddings,
            gap_penalty=args.gap_penalty,
            on_log=print
        )
        print(f"[✓] SRT corrigé avec succès : {res['output_path']}")


if __name__ == "__main__":
    main()
