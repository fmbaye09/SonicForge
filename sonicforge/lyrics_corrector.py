"""
Moteur de correction de paroles pour fichiers SRT.
Aligne le texte d'un fichier .srt généré (bon timing, texte approximatif)
avec les paroles réelles et exactes, sans modifier les timings existants.
Gère également l'insertion et l'interpolation temporelle des répétitions (refrains).
"""

import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, List, Tuple, Dict, Any


@dataclass
class Cue:
    start: float  # en secondes
    end: float
    text: str


TIME_RE = re.compile(r"(\d+):(\d{2}):(\d{2}),(\d{3})")


def parse_timestamp(ts: str) -> float:
    m = TIME_RE.match(ts.strip())
    if not m:
        raise ValueError(f"Timestamp SRT invalide : '{ts}'")
    h, mi, s, ms = map(int, m.groups())
    return h * 3600 + mi * 60 + s + ms / 1000.0


def format_timestamp(t: float) -> str:
    if t < 0:
        t = 0.0
    h = int(t // 3600)
    t -= h * 3600
    mi = int(t // 60)
    t -= mi * 60
    s = int(t)
    ms = round((t - s) * 1000)
    if ms >= 1000:
        ms = 0
        s += 1
    return f"{h:02d}:{mi:02d}:{s:02d},{ms:03d}"


def parse_srt(path: Path) -> List[Cue]:
    """Lit un fichier SRT et retourne la liste des cues (timing + texte)."""
    content = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", content.strip())
    cues = []
    for block in blocks:
        lines = [l for l in block.strip().splitlines() if l.strip()]
        if len(lines) < 2:
            continue
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


def write_srt(cues: List[Cue], path: Path):
    """Écrit les cues dans un fichier .srt."""
    lines = []
    for i, cue in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{format_timestamp(cue.start)} --> {format_timestamp(cue.end)}")
        lines.append(cue.text)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def read_lyrics_lines(path: Path) -> List[str]:
    """Lit le fichier texte des paroles."""
    raw = path.read_text(encoding="utf-8").splitlines()
    lines = [l.strip() for l in raw if l.strip()]
    if not lines:
        raise ValueError(f"Le fichier de paroles est vide : {path}")
    return lines


class Similarity:
    def __init__(self, use_embeddings: bool = False):
        self.use_embeddings = use_embeddings
        self._model = None
        self._cache = {}

        if use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            except ImportError:
                print("⚠️ sentence-transformers non installé. Utilisation de la similarité standard.")
                self.use_embeddings = False

    def precompute(self, texts: List[str]):
        if not self.use_embeddings or self._model is None:
            return
        try:
            import numpy as np
            unique_texts = list(dict.fromkeys(texts))
            embeddings = self._model.encode(unique_texts, normalize_embeddings=True)
            for t, e in zip(unique_texts, embeddings):
                self._cache[t] = e
            self._np = np
        except Exception:
            self.use_embeddings = False

    def score(self, a: str, b: str) -> float:
        a, b = a.strip(), b.strip()
        if not a or not b:
            return 0.0
        if self.use_embeddings and self._model is not None:
            ea, eb = self._cache.get(a), self._cache.get(b)
            if ea is not None and eb is not None:
                return float(self._np.dot(ea, eb))
        return difflib.SequenceMatcher(None, a, b).ratio()


GAP_PENALTY = 0.35


def align_sequences(
    ref_lines: List[str], 
    cue_texts: List[str], 
    sim: Similarity, 
    gap_penalty: float = GAP_PENALTY
) -> List[Tuple[str, Optional[int], Optional[int]]]:
    """
    Alignement global (Needleman-Wunsch) entre paroles de référence et sous-titres générés.
    """
    n, m = len(ref_lines), len(cue_texts)
    sim.precompute(ref_lines + cue_texts)
    tiebreak = 1e-6

    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] - gap_penalty + tiebreak * i
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] - gap_penalty + tiebreak * j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            match_score = dp[i - 1][j - 1] + sim.score(ref_lines[i - 1], cue_texts[j - 1])
            skip_ref = dp[i - 1][j] - gap_penalty + tiebreak * i
            skip_cue = dp[i][j - 1] - gap_penalty + tiebreak * j
            dp[i][j] = max(match_score, skip_ref, skip_cue)

    ops = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and abs(dp[i][j] - (dp[i - 1][j - 1] + sim.score(ref_lines[i - 1], cue_texts[j - 1]))) < 1e-9:
            ops.append(("match", i - 1, j - 1))
            i -= 1
            j -= 1
        elif i > 0 and abs(dp[i][j] - (dp[i - 1][j] - gap_penalty + tiebreak * i)) < 1e-9:
            ops.append(("missing", i - 1, None))
            i -= 1
        else:
            ops.append(("extra", None, j - 1))
            j -= 1

    ops.reverse()
    return ops


def apply_correction(
    cues: List[Cue], 
    ref_lines: List[str], 
    ops: List[Tuple[str, Optional[int], Optional[int]]]
) -> List[Cue]:
    """Applique les corrections et interpole les répétitions sautées."""
    result: List[Cue] = []
    pending_missing: List[str] = []

    def flush_missing(prev_end: Optional[float], next_start: Optional[float]):
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
            result.append(Cue(start=seg_start, end=seg_end, text=text))
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


def correct_srt_file(
    srt_path: Path,
    lyrics_path: Path,
    output_path: Path,
    use_embeddings: bool = False,
    gap_penalty: float = GAP_PENALTY,
    on_log: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Corrige un fichier SRT avec un fichier de paroles."""
    srt_file = Path(srt_path).resolve()
    lyrics_file = Path(lyrics_path).resolve()
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if on_log:
        on_log(f"📖 Lecture du sous-titre : {srt_file.name}")
    cues = parse_srt(srt_file)

    if on_log:
        on_log(f"📜 Lecture des paroles : {lyrics_file.name}")
    ref_lines = read_lyrics_lines(lyrics_file)

    sim = Similarity(use_embeddings=use_embeddings)
    if on_log:
        on_log("⚡ Alignement intelligent des paroles avec le timing existant...")

    ops = align_sequences(ref_lines, [c.text for c in cues], sim, gap_penalty=gap_penalty)

    n_match = sum(1 for o in ops if o[0] == "match")
    n_missing = sum(1 for o in ops if o[0] == "missing")
    n_extra = sum(1 for o in ops if o[0] == "extra")

    if on_log:
        on_log(f"   🎯 {n_match} correspondance(s) exacte(s)")
        on_log(f"   🔄 {n_missing} répétition(s) manquante(s) interpolée(s)")
        on_log(f"   ➕ {n_extra} élément(s) conservé(s) (ad-libs/bruits)")

    corrected_cues = apply_correction(cues, ref_lines, ops)
    write_srt(corrected_cues, out_file)

    if on_log:
        on_log(f"✅ SRT corrigé enregistré dans : {out_file} ({len(corrected_cues)} sous-titres)")

    return {
        "output_path": out_file,
        "matches": n_match,
        "inserted_repeats": n_missing,
        "extras_kept": n_extra,
        "total_cues": len(corrected_cues),
    }

