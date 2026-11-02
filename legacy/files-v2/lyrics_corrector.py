#!/usr/bin/env python3
"""
lyrics_corrector.py
---------------------
Corrige le TEXTE d'un fichier .srt déjà généré (bon timing, texte approximatif)
en utilisant les paroles originales correctes, SANS toucher au timing existant.

Gère aussi les répétitions (refrains, etc.) que Whisper a parfois sautées :
si une ligne de parole n'a aucun sous-titre correspondant, un nouveau sous-titre
est inséré avec un timing estimé par interpolation dans le "trou" temporel.

Principe :
  - On aligne la séquence des paroles de référence (qui contient les répétitions
    écrites explicitement, ligne par ligne) avec la séquence des sous-titres
    générés (texte approximatif), via un alignement global pondéré par une
    similarité texte (façon Needleman-Wunsch, mais sur des phrases entières).
  - Ça permet de gérer : substitutions (texte faux -> corrigé), insertions
    (répétition manquante -> nouveau sous-titre), et extra (sous-titre sans
    parole correspondante -> conservé tel quel, ex: ad-libs/bruit).

Usage :
  python lyrics_corrector.py \
    --srt generated.srt \
    --lyrics paroles.txt \
    --output corrected.srt

  # Pour un matching plus robuste au bruit de transcription (texte faux mais
  # phonétiquement/sémantiquement proche), active le petit modèle d'embeddings :
  python lyrics_corrector.py --srt generated.srt --lyrics paroles.txt \
    --output corrected.srt --use-embeddings
"""

import argparse
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path


# --------------------------------------------------------------------- SRT

@dataclass
class Cue:
    start: float  # secondes
    end: float
    text: str


TIME_RE = re.compile(r"(\d+):(\d{2}):(\d{2}),(\d{3})")


def parse_timestamp(ts: str) -> float:
    m = TIME_RE.match(ts.strip())
    if not m:
        raise ValueError(f"Timestamp invalide : {ts}")
    h, mi, s, ms = map(int, m.groups())
    return h * 3600 + mi * 60 + s + ms / 1000


def format_timestamp(t: float) -> str:
    if t < 0:
        t = 0
    h = int(t // 3600)
    t -= h * 3600
    mi = int(t // 60)
    t -= mi * 60
    s = int(t)
    ms = round((t - s) * 1000)
    if ms == 1000:
        ms = 0
        s += 1
    return f"{h:02d}:{mi:02d}:{s:02d},{ms:03d}"


def parse_srt(path: Path) -> list[Cue]:
    content = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", content.strip())
    cues = []
    for block in blocks:
        lines = [l for l in block.strip().splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        # ligne 0 = index, ligne 1 = timing, reste = texte
        time_line_idx = None
        for i, l in enumerate(lines):
            if "-->" in l:
                time_line_idx = i
                break
        if time_line_idx is None:
            continue
        start_str, end_str = [p.strip() for p in lines[time_line_idx].split("-->")]
        text = " ".join(lines[time_line_idx + 1:]).strip()
        cues.append(Cue(start=parse_timestamp(start_str), end=parse_timestamp(end_str), text=text))
    return cues


def write_srt(cues: list[Cue], path: Path):
    lines = []
    for i, cue in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{format_timestamp(cue.start)} --> {format_timestamp(cue.end)}")
        lines.append(cue.text)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ------------------------------------------------------------------ paroles

def read_lyrics_lines(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8").splitlines()
    lines = [l.strip() for l in raw if l.strip()]
    if not lines:
        sys.exit(f"[!] Le fichier de paroles est vide : {path}")
    return lines


# --------------------------------------------------------------- similarité

class Similarity:
    """Similarité texte. Par défaut : difflib (léger, aucune dépendance lourde).
    En option (--use-embeddings) : petit modèle d'embeddings multilingue,
    plus robuste au bruit de transcription (texte faux mais proche en sens)."""

    def __init__(self, use_embeddings: bool = False):
        self.use_embeddings = use_embeddings
        self._model = None
        self._cache = {}

        if use_embeddings:
            print("[*] Chargement du modèle d'embeddings multilingue (léger, ~470 Mo)...")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    def precompute(self, texts: list[str]):
        if not self.use_embeddings:
            return
        import numpy as np
        unique_texts = list(dict.fromkeys(texts))
        embeddings = self._model.encode(unique_texts, normalize_embeddings=True)
        for t, e in zip(unique_texts, embeddings):
            self._cache[t] = e
        self._np = np

    def score(self, a: str, b: str) -> float:
        a, b = a.strip(), b.strip()
        if not a or not b:
            return 0.0
        if self.use_embeddings:
            ea, eb = self._cache.get(a), self._cache.get(b)
            if ea is None or eb is None:
                return difflib.SequenceMatcher(None, a, b).ratio()
            return float(self._np.dot(ea, eb))  # cosinus (vecteurs normalisés)
        return difflib.SequenceMatcher(None, a, b).ratio()


# ------------------------------------------------------------------ alignement

GAP_PENALTY = 0.35  # coût de "sauter" une ligne de parole ou un sous-titre


def align_sequences(ref_lines: list[str], cue_texts: list[str], sim: Similarity, gap_penalty: float = GAP_PENALTY):
    """
    Alignement global (type Needleman-Wunsch) entre :
      - ref_lines : paroles de référence (vérité, avec répétitions explicites)
      - cue_texts : texte des sous-titres générés (approximatif, parfois incomplet)

    Retourne une liste d'opérations dans l'ordre :
      ("match", i, j)      -> ref_lines[i] correspond à cue_texts[j]
      ("missing", i, None) -> ref_lines[i] n'a aucun sous-titre correspondant (répétition sautée)
      ("extra", None, j)   -> cue_texts[j] n'a aucune parole de référence correspondante
    """
    n, m = len(ref_lines), len(cue_texts)
    sim.precompute(ref_lines + cue_texts)
    TIEBREAK = 1e-6  # quand plusieurs alignements ont un score identique (paroles dupliquées),
                      # on préfère différer les sauts plutôt que les placer au début

    # dp[i][j] = meilleur score en alignant ref_lines[:i] avec cue_texts[:j]
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] - gap_penalty + TIEBREAK * i
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] - gap_penalty + TIEBREAK * j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            match_score = dp[i - 1][j - 1] + sim.score(ref_lines[i - 1], cue_texts[j - 1])
            skip_ref = dp[i - 1][j] - gap_penalty + TIEBREAK * i   # parole sans sous-titre (répétition sautée)
            skip_cue = dp[i][j - 1] - gap_penalty + TIEBREAK * j  # sous-titre sans parole (extra)
            dp[i][j] = max(match_score, skip_ref, skip_cue)

    # backtrack
    ops = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and abs(dp[i][j] - (dp[i - 1][j - 1] + sim.score(ref_lines[i - 1], cue_texts[j - 1]))) < 1e-9:
            ops.append(("match", i - 1, j - 1))
            i -= 1
            j -= 1
        elif i > 0 and abs(dp[i][j] - (dp[i - 1][j] - gap_penalty + TIEBREAK * i)) < 1e-9:
            ops.append(("missing", i - 1, None))
            i -= 1
        else:
            ops.append(("extra", None, j - 1))
            j -= 1

    ops.reverse()
    return ops


# ------------------------------------------------------------------ correction

def apply_correction(cues: list[Cue], ref_lines: list[str], ops: list[tuple]) -> list[Cue]:
    result: list[Cue] = []

    # Index des ops "match"/"extra" -> position dans cues (j) pour retrouver start/end facilement
    pending_missing: list[str] = []  # paroles manquantes en attente d'insertion

    def flush_missing(prev_end: float | None, next_start: float | None):
        """Insère les paroles manquantes accumulées entre prev_end et next_start."""
        nonlocal pending_missing
        if not pending_missing:
            return
        count = len(pending_missing)
        if prev_end is None:
            prev_end = next_start - 2.0 * count if next_start is not None else 0.0
        if next_start is None:
            next_start = prev_end + 2.0 * count
        span = max(next_start - prev_end, 0.1)
        step = span / count
        for k, text in enumerate(pending_missing):
            seg_start = prev_end + k * step
            seg_end = prev_end + (k + 1) * step
            result.append(Cue(start=seg_start, end=seg_end, text=f"{text}"))
        pending_missing = []

    last_cue_end = None

    for op in ops:
        kind = op[0]
        if kind == "match":
            i, j = op[1], op[2]
            flush_missing(prev_end=last_cue_end, next_start=cues[j].start)
            corrected = Cue(start=cues[j].start, end=cues[j].end, text=ref_lines[i])
            result.append(corrected)
            last_cue_end = cues[j].end
        elif kind == "missing":
            i = op[1]
            pending_missing.append(ref_lines[i])
        elif kind == "extra":
            j = op[1]
            flush_missing(prev_end=last_cue_end, next_start=cues[j].start)
            result.append(Cue(start=cues[j].start, end=cues[j].end, text=cues[j].text))
            last_cue_end = cues[j].end

    flush_missing(prev_end=last_cue_end, next_start=None)

    result.sort(key=lambda c: c.start)
    return result


# ------------------------------------------------------------------------ main

def main():
    parser = argparse.ArgumentParser(description="Corrige le texte d'un SRT avec les vraies paroles, sans toucher au timing.")
    parser.add_argument("--srt", required=True, type=Path, help="Fichier .srt généré (bon timing, texte approximatif)")
    parser.add_argument("--lyrics", required=True, type=Path, help="Fichier .txt des vraies paroles (une ligne = un sous-titre, répétitions écrites explicitement)")
    parser.add_argument("--output", required=True, type=Path, help="Fichier .srt corrigé en sortie")
    parser.add_argument("--use-embeddings", action="store_true", help="Utiliser un petit modèle d'embeddings multilingue pour un matching plus robuste au bruit")
    parser.add_argument("--gap-penalty", type=float, default=GAP_PENALTY, help=f"Coût de saut dans l'alignement (défaut: {GAP_PENALTY})")

    args = parser.parse_args()

    if not args.srt.exists():
        sys.exit(f"[!] SRT introuvable : {args.srt}")
    if not args.lyrics.exists():
        sys.exit(f"[!] Fichier de paroles introuvable : {args.lyrics}")

    print(f"[*] Lecture de {args.srt.name}...")
    cues = parse_srt(args.srt)
    print(f"    -> {len(cues)} sous-titres trouvés")

    print(f"[*] Lecture de {args.lyrics.name}...")
    ref_lines = read_lyrics_lines(args.lyrics)
    print(f"    -> {len(ref_lines)} lignes de paroles trouvées")

    sim = Similarity(use_embeddings=args.use_embeddings)

    print("[*] Alignement des paroles avec les sous-titres...")
    ops = align_sequences(ref_lines, [c.text for c in cues], sim, gap_penalty=args.gap_penalty)

    n_match = sum(1 for o in ops if o[0] == "match")
    n_missing = sum(1 for o in ops if o[0] == "missing")
    n_extra = sum(1 for o in ops if o[0] == "extra")
    print(f"    -> {n_match} correspondances, {n_missing} répétition(s) manquante(s) insérée(s), {n_extra} sous-titre(s) extra conservé(s)")

    print("[*] Application de la correction (timing préservé)...")
    corrected_cues = apply_correction(cues, ref_lines, ops)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_srt(corrected_cues, args.output)
    print(f"[✓] SRT corrigé : {args.output} ({len(corrected_cues)} sous-titres)")

    if n_missing > 0:
        print("\n[!] Note : le timing des répétitions insérées est ESTIMÉ par interpolation")
        print("    (Whisper n'avait généré aucun sous-titre à cet endroit). Vérifie ces")
        print("    passages en priorité — ils sont marqués sans suffixe particulier mais")
        print("    correspondent aux lignes manquantes signalées ci-dessus.")


if __name__ == "__main__":
    main()
