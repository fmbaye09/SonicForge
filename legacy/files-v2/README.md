# Khassida Subtitles

Génère des fichiers `.srt` pour des enregistrements de khassidas, avec deux approches selon ce que tu as déjà :

- **`align`** : tu connais déjà le texte exact (fichier `.txt`) → le programme cale juste le timing sur l'audio. **Mode recommandé**, surtout en wolof, car Whisper ne reconnaît pas officiellement cette langue.
- **`transcribe`** : tu n'as pas le texte → Whisper transcrit l'audio directement. Moins fiable selon la langue/dialecte récité.
- **`batch`** : traite un dossier entier, structuré comme ton pipeline d'import (`langue/titre.mp3` + `langue/titre.txt` optionnel). Détecte automatiquement si un texte existe pour chaque fichier et choisit le bon mode.

## Installation

```bash
pip install -r requirements.txt
```

Premier lancement : le modèle Whisper se télécharge automatiquement (peut prendre plusieurs minutes selon la taille choisie).

## Interface graphique

Une interface desktop est disponible (style identique à VideoSonic, CustomTkinter) :

```bash
python khassida_subtitles_gui.py
```

- Choisis le mode (texte connu / inconnu), sélectionne tes fichiers audio (et texte si besoin), choisis le modèle et la langue, puis clique sur "Générer le SRT".
- Le traitement tourne dans un thread séparé, donc l'interface ne se bloque pas pendant le chargement du modèle ou le traitement de l'audio.
- Le mode batch reste disponible uniquement en ligne de commande pour l'instant.

## Utilisation en ligne de commande

### 1. Texte déjà connu (recommandé)

```bash
python khassida_subtitles.py align \
  --audio chanson.mp3 \
  --text paroles.txt \
  --output chanson.srt \
  --language ar
```

### 2. Texte inconnu

```bash
python khassida_subtitles.py transcribe \
  --audio chanson.mp3 \
  --output chanson.srt \
  --language ar
```

Omets `--language` pour laisser Whisper deviner automatiquement (moins fiable).

### 3. Traitement par lot

```bash
python khassida_subtitles.py batch \
  --input-dir data/ \
  --output-dir subtitles/ \
  --language ar
```

Structure attendue (similaire à ton pipeline d'import existant) :

```
data/
  wolof/
    titre1.mp3
    titre1.txt      # si présent -> alignement forcé
  arabe/
    titre2.mp3      # pas de .txt -> transcription Whisper
```

## Choix du modèle

```bash
python khassida_subtitles.py align --model large-v3 --audio ... --text ... --output ...
```

| Modèle    | Vitesse | Précision | RAM/VRAM nécessaire |
|-----------|---------|-----------|----------------------|
| tiny      | ++++    | -         | ~1 Go                |
| base      | +++     | --        | ~1 Go                |
| small     | ++      | +         | ~2 Go                |
| medium    | +       | ++        | ~5 Go (par défaut)   |
| large-v3  | -       | +++       | ~10 Go               |

## Étape 2 : corriger les paroles sans toucher au timing

Une fois ton `.srt` généré (mode `transcribe`, donc bon timing mais texte approximatif et parfois des répétitions sautées), utilise **`lyrics_corrector.py`** avec le texte exact des paroles pour corriger le contenu sans jamais modifier le timing :

```bash
python lyrics_corrector.py \
  --srt generated.srt \
  --lyrics paroles.txt \
  --output corrected.srt
```

**Format du fichier `paroles.txt`** : une ligne de texte = un sous-titre attendu, **dans l'ordre exact de récitation, y compris les répétitions écrites explicitement**. Par exemple, si un refrain de 2 lignes revient 3 fois dans la chanson, il doit apparaître 3 fois (6 lignes) dans le fichier, pas une seule fois.

Comment ça marche :
- Le programme aligne la séquence des vraies paroles avec la séquence des sous-titres générés, via un algorithme d'alignement global (façon Needleman-Wunsch, appliqué à des phrases entières plutôt qu'à des caractères).
- Chaque sous-titre reconnu est réécrit avec la bonne ligne de parole correspondante, **timing inchangé**.
- Si une ligne de parole n'a aucun sous-titre correspondant (cas des répétitions que Whisper a sautées), un nouveau sous-titre est inséré avec un timing **estimé par interpolation** dans le trou temporel correspondant. Ces passages sont signalés dans la sortie console — à vérifier en priorité.
- Si un sous-titre généré n'a aucune ligne de parole correspondante (ad-libs, bruit), il est conservé tel quel.

Option `--use-embeddings` : active un petit modèle d'embeddings multilingue (~470 Mo, `paraphrase-multilingual-MiniLM-L12-v2`) au lieu de la similarité texte simple (`difflib`), pour un matching un peu plus robuste si le texte transcrit est très éloigné des vraies paroles. À tester au cas par cas — sur du texte fortement mal reconnu (script différent, mots sans rapport), aucune méthode texte ne fera de miracle ; c'est surtout l'ordre des lignes qui garantit un alignement correct.

Option `--gap-penalty` (défaut 0.35) : augmente cette valeur si le programme insère trop de répétitions "manquantes" qui n'existent pas vraiment ; diminue-la s'il ne détecte pas assez de répétitions réellement sautées.

## Notes importantes

- **Codes langue** : `ar` (arabe), `fr` (français), etc. Whisper ne supporte pas nativement le `wo` (wolof) — utiliser `ar` comme approximation si les khassidas sont récités avec une phonétique proche de l'arabe classique, sinon tester `fr` ou laisser en auto-détection et comparer les résultats.
- Le format SRT généré peut être directement réutilisé comme base pour ta fonctionnalité de synchronisation audio-texte / karaoké dans le Khassida API (les timestamps peuvent être réimportés en JSON si besoin — `result.to_dict()` dans stable-ts donne accès aux timestamps mot par mot).
- En mode `align`, le texte fourni doit suivre l'ordre exact de récitation ; les sauts de ligne ne sont pas nécessaires mais aident à la lisibilité du `.txt` source.
