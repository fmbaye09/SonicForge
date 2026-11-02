# ⚡ SonicForge - AI Media Arsenal

**SonicForge** est une suite complète de traitement audio et vidéo assistée par intelligence artificielle.
Elle regroupe dans une interface unifiée : un **convertisseur vidéo/audio haute fidélité**, un **séparateur vocal/instrumental Demucs**, un **générateur de sous-titres Whisper** et un **correcteur intelligent de paroles**.

Accessible à la fois via une **interface graphique moderne (GUI)** et une **interface en ligne de commande (CLI)**.

---

## 🧰 Les Modules de SonicForge

| Outil | Description | Moteur / Technologie |
| :--- | :--- | :--- |
| 🎬 **Convertisseur Vidéo ➔ Audio** | Convertit n'importe quel fichier vidéo (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, etc.) en MP3 (jusqu'à 320 kbps), WAV studio, FLAC sans perte, AAC ou OGG. Gère la normalisation sonore EBU R128 et l'extraction brute ultra-rapide sans réencodage. | FFmpeg |
| 🎵 **Séparateur Vocal / Instrumental** | Isole la voix (chant, parole) et l'accompagnement instrumental en 2 pistes distinctes ou 4 pistes (batterie, basse, voix, autres). | Meta Demucs v4 (htdemucs) |
| 📝 **Générateur de Sous-titres (SRT)** | Génère des sous-titres synchronisés : mode transcription automatique ou mode **alignement forcé** avec un texte exact fourni (.txt), particulièrement efficace pour les chants et le wolof/arabe. | Stable-Whisper |
| ✍️ **Correcteur de Paroles & Synchronisation** | Aligne le texte d'un `.srt` avec les vraies paroles sans toucher aux timestamps, et **interpole automatiquement les refrains/répétitions** sautés par la transcription. | Needleman-Wunsch / Embeddings IA |
| 🩺 **Diagnostic Système & Matériel** | Analyse votre environnement (détection FFmpeg, GPU NVIDIA / CUDA, PyTorch, modules IA installés). | Intégré |

---

## 🚀 Démarrage Rapide

### 1. Interface Graphique (GUI)

- **Option 1 (Windows)** : Double-cliquez sur `launch_gui.bat`.
- **Option 2** : Dans un terminal, lancez :
  ```bash
  python main.py
  ```
  *(ou `python main.py gui`)*

L'application graphique propose 5 onglets dédiés, une navigation par explorateur de fichiers, des barres de progression précises et un journal de logs en temps réel.

---

### 2. Ligne de Commande (CLI)

#### 🎬 Convertisseur Vidéo ➔ Audio
```bash
# Conversion simple en MP3 320 kbps
python main.py convert -i video.mp4 -f mp3 -b 320k

# Extraction brute instantanée (sans réencodage, 0 perte)
python main.py convert -i film.mkv -f copy

# Conversion en WAV avec normalisation sonore (Loudnorm)
python main.py convert -i video.mp4 -f wav --normalize

# Traitement par lot d'un dossier entier
python main.py convert -i ./mes_videos/ -o ./mes_audios/ -f mp3 -b 320k
```

#### 🎵 Séparation Audio (Parole & Instrumental)
```bash
# Séparation en 2 pistes (voix + accompagnement) en MP3 320 kbps
python main.py separate -i chant.mp3 -m htdemucs

# Utilisation spécifique du GPU CUDA
python main.py separate -i audio.wav -d cuda
```

#### 📝 Sous-titres Whisper
```bash
# Mode alignement forcé (texte exact connu, recommandé en wolof/arabe)
python main.py subtitles align -a chant.mp3 -t paroles.txt -o chant.srt -l ar

# Mode transcription automatique (texte inconnu)
python main.py subtitles transcribe -a audio.mp3 -o audio.srt -l ar

# Traitement par lot d'un dossier
python main.py subtitles batch -i data/ -o subtitles/ -l ar
```

#### ✍️ Correction et Réalignement des Paroles
```bash
python main.py correct -s audio.srt -l vraies_paroles.txt -o audio_corrige.srt
```

#### 🩺 Diagnostic Système
```bash
python main.py doctor
```

---

## 📁 Organisation du Répertoire

```text
sonicforge/
│
├── main.py                     # Point d'entrée unique (CLI + GUI)
├── launch_gui.bat              # Raccourci 1-clic pour lancer la GUI Windows
├── requirements.txt            # Liste consolidée des dépendances
├── README.md                   # Documentation officielle
├── .gitignore                  # Fichiers et dossiers ignorés par Git
│
├── sonicforge/                 # Code source du package
│   ├── __init__.py
│   ├── config.py               # Paramètres, extensions et formats supportés
│   ├── system.py               # Diagnostic matériel (FFmpeg, CUDA, PyTorch)
│   ├── converter.py            # Moteur de conversion vidéo -> audio FFmpeg
│   ├── separator.py            # Moteur Demucs (isolation voix/musique)
│   ├── subtitles.py            # Moteur Whisper (transcription et alignement)
│   ├── lyrics_corrector.py     # Algorithme d'alignement intelligent et refrains
│   └── gui/                    # Interface graphique moderne
│       ├── app.py              # Fenêtre principale et navigation
│       ├── theme.py            # Thème sombre moderne (Cyber Slate)
│       ├── tab_converter.py    # Onglet Convertisseur Vidéo ➔ Audio
│       ├── tab_separator.py    # Onglet Séparateur Demucs
│       ├── tab_subtitles.py    # Onglet Sous-titres Whisper
│       ├── tab_corrector.py    # Onglet Correcteur de Paroles
│       └── tab_doctor.py       # Onglet Diagnostic & Santé Système
│
└── legacy/                     # Archives des scripts originaux (rétrocompatibilité)
    ├── audio_separator.py
    └── files-v2/
```

---

## 📦 Installation des dépendances

```bash
pip install -r requirements.txt
```

### Remarques sur le matériel :
- **FFmpeg** : Requis pour les conversions audio/vidéo (déjà disponible sur la machine).
- **Accélération GPU NVIDIA (CUDA)** :
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
  ```
