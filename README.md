# BLACK-FLAG-version-exe
# v1.1

**Outil d'upload automatique vers [La Cale](https://la-cale.space)**  
*Développé par Theolddispatch & The40n8*

---

## 📋 Description

BLACK FLAG est une application de bureau qui automatise l'upload de torrents de films et de séries vers le tracker privé français **La Cale**. Il scanne un dossier NAS ou local, génère les torrents, récupère les métadonnées via TMDb, et les uploade directement sur La Cale — le tout sans intervention manuelle.

---

## ✨ Fonctionnalités

### Upload automatique
- Scan de dossiers Films et Séries (local ou réseau NAS/UNC)
- Génération de torrents SHA1 en Python pur (films et séries multi-fichiers par saison)
- Parsing automatique du nom de fichier scène (titre, année, résolution, codec, langue, source, HDR…)
- Récupération des métadonnées depuis **TMDb** (titre, synopsis, affiche, note, genres, casting)
- Génération de la description BBCode au format La Cale
- Upload vers **La Cale** en mode **API** (passkey) ou **Web** (email + mot de passe)
- Vérification des doublons par info_hash avant upload
- Historique des uploads pour éviter les re-uploads

### Clients torrent supportés
- **qBittorrent** — ajout automatique via WebUI (API v2)
- **Transmission** — ajout automatique via RPC (port 9091)
- Toggle exclusif entre les deux clients dans les paramètres

### Surveillance et notifications
- **Voyant de santé** La Cale en temps réel (vérification toutes les minutes depuis un watcher exterieur pour ne pas saturer l'infrastructure)
- **Health check en deux passes** avant chaque upload :
  - Passe 1 : vérification via source externe (isitdownrightnow.com)
  - Passe 2 : connexion directe HEAD au site
- **Watcher** automatique : surveillance toutes les 10/20/60 min quand le site est KO
- **Notification Windows** toast natif quand le site revient en ligne
- Notification sonore **"Arr!"** au retour du site

### Interface
- Interface graphique **tkinter** sombre (thème pirate ⚓)
- **7 langues** : Français, English, Español, Deutsch, Italiano, Português, 日本語
- Logo ASCII animé
- Journal de bord scrollable avec clic droit (copier)
- Barre de progression SHA1 avec compteur uploads et pourcentage
- **Lecteur audio** intégré — playlist de 7 morceaux pirate (téléchargés automatiquement)
- Scrollbars fines style moderne

### Configuration
- Sauvegarde automatique de la configuration (autosave)
- Panneau de paramètres dépliable et scrollable
- Notifications Discord webhook
- Génération de fichiers logs et curl (activable/désactivable)

---

## 🗂️ Structure des dossiers

```
BLACK FLAG/
├── BLACK.FLAG version exe.py   ← script principal (version PY)
├── BLACK FLAG.exe               ← exécutable Windows (version .exe)
├── .blackflag_config.json       ← configuration (créé automatiquement)
├── music/                       ← musiques téléchargées automatiquement
├── logs/                        ← fichiers logs journaliers
├── torrents/                    ← torrents générés
└── logs/                        ← historique des uploads
```

---

## 🚀 Installation

### Version PY (nécessite Python)

**Prérequis :** Python 3.9 ou supérieur

```bash
# Lancer directement
python "BLACK.FLAG version exe.py"
```

> `requests` et `pygame` s'installent automatiquement au premier lancement.

### Version .exe (sans Python)

1. Télécharger le dossier `dist/BLACK FLAG/`
2. Double-cliquer sur `BLACK FLAG.exe`
3. Aucune installation requise

---

## ⚙️ Configuration

Au premier lancement, renseigner dans **▶ PARAMÈTRES** :

| Section | Champ | Description |
|---|---|---|
| LA CALE | URL | `https://la-cale.space` |
| LA CALE | Mode | **API** (passkey) ou **Web** (email + mdp) |
| TMDb | Bearer Token | Clé API TMDb v4 |
| QBITTORRENT / TRANSMISSION | URL + identifiants | WebUI locale |
| DIVERS | Dossier torrents | Où sauvegarder les `.torrent` générés |

---

## 📁 Sources & Films

- **Films** : un fichier vidéo = un torrent
- **Séries** : un dossier saison = un torrent multi-fichiers
  ```
  Séries/Breaking Bad/Saison 1/   → Breaking.Bad.S01.MULTi.1080p.WEB-DL.x265-GROUPE.torrent
  ```

**Formats supportés :** `.mkv` `.mp4` `.avi` `.m4v` `.ts` `.mov`

---

## 🎵 Musiques intégrées

Téléchargées automatiquement depuis [OpenGameArt.org](https://opengameart.org) au premier lancement :

| Fichier | Auteur | Licence |
|---|---|---|
| Pirate Theme | loliver1814 | CC-BY 3.0 |
| Battle Theme 1–5 | Alexandr Zhelanov | CC-BY 4.0 |
| Pirate | Ivy Fae (lalanl) | CC-BY-SA 3.0 |
| Arr! | bart | CC-BY 3.0 |

---

## 🔧 Compiler le .exe

```bash
# Installer PyInstaller
pip install pyinstaller

# Compiler (Windows)
BUILD.bat
# ou
pyinstaller blackflag.spec --clean --noconfirm
```

Le résultat se trouve dans `dist/BLACK FLAG/`.

---

## 📝 Notes

- Fonctionne sur **Windows**, **Linux** et **macOS** (version PY)
- Les notifications Windows toast ne fonctionnent que sur Windows
- La configuration est sauvegardée dans `.blackflag_config.json` à côté de l'exécutable
- Les logs journaliers sont dans le sous-dossier `logs/`

---

## ⚠️ Disclaimer

Cet outil est destiné à faciliter l'upload de contenu **dont vous êtes l'auteur ou disposez des droits** sur des trackers privés. Respectez les règles de La Cale et les lois en vigueur dans votre pays.

---

*BLACK FLAG v1.1 — Theolddispatch & The40n8 — 2026*
