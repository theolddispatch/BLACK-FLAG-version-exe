# BLACK-FLAG-version-exe
# v1.4

**Outil d'upload automatique vers [La Cale](https://la-cale.space) et [Torr9](https://torr9.net)**  
*Développé par Theolddispatch & The40n8*  
Pour les mises à jour, vous avez juste à remplacer le fichier PY, vous ne perdrez pas vos configurations 🦜

---

## 📋 Description

BLACK FLAG est une application de bureau qui automatise l'upload de torrents de films et de séries vers les trackers privés français **La Cale** et **Torr9**. Il scanne un dossier NAS ou local, génère les torrents, récupère les métadonnées via TMDb, et les uploade directement — le tout sans intervention manuelle.

---

## ✨ Fonctionnalités

### Upload automatique
- Scan de dossiers Films et Séries (local ou réseau NAS/UNC)
- Génération de torrents SHA1 en Python pur (films et séries multi-fichiers par saison)
- Parsing automatique du nom de fichier scène (titre, année, résolution, codec, langue, source, HDR…)
- Récupération des métadonnées depuis **TMDb** (titre, synopsis, affiche, note, genres, casting)
- Génération de la description BBCode et NFO style MediaInfo complet
- Upload vers **La Cale** en mode **API** (passkey) ou **Web** (email + mot de passe)
- Upload vers **Torr9** (mode Web, JWT Bearer token)
- Vérification des doublons par info_hash avant upload
- Historique des uploads pour éviter les re-uploads
- **Vérification TMDb Bearer Token et MediaInfo au lancement** (bloquant si manquant)

### Clients torrent supportés
- **qBittorrent** — ajout automatique via WebUI (API v2), vérification seed par hash avant upload
- **Transmission** — ajout automatique via RPC (port 9091)
- **Deluge 2.x** — ajout automatique via JSON-RPC (`/json`, port 8112), skip hash check (seed_mode)
- Toggle exclusif entre les trois clients dans les paramètres

### Surveillance et notifications
- **Voyant de santé** La Cale / Torr9 en temps réel
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
- **Fenêtre historique** des uploads : date, état seed, tracker (colonnes triables/redimensionnables)
- Scrollbars fines style moderne

### Configuration
- Sauvegarde automatique de la configuration (autosave)
- **Chiffrement AES de la config** (Fernet/PBKDF2-SHA256, 260 000 itérations) — opt-in avec mot de passe maître saisi au lancement
- Panneau de paramètres dépliable et scrollable
- Notifications Discord webhook
- Génération de fichiers logs et curl horodatés (activable/désactivable, un fichier par session)
- Toggle vérification des mises à jour (GitHub)

---

## 🗂️ Structure des dossiers

```
BLACK FLAG/
├── BLACK.FLAG version exe.py   ← script principal (version PY)
├── BLACK FLAG.exe               ← exécutable Windows (version .exe)
├── .blackflag_config.json       ← configuration JSON (créé automatiquement)
├── .blackflag_config.enc        ← configuration chiffrée AES (si chiffrement activé)
├── MediaInfo.dll                ← requis pour NFO complet (Windows)
├── music/                       ← musiques téléchargées automatiquement
├── logs/                        ← fichiers logs et curl horodatés
├── torrents/                    ← torrents générés
└── uploaded_torrents.txt        ← historique des uploads
```

---

## 🚀 Installation

### Version PY (nécessite Python)

**Prérequis :** Python 3.9 ou supérieur

```bash
# Lancer directement
python "BLACK.FLAG version exe.py"
```

> `requests`, `pygame`, `pymediainfo` et `cryptography` s'installent automatiquement au premier lancement.

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
| TORR9 | Pseudonyme + mdp | Identifiants Torr9 |
| TMDb | Bearer Token | Clé API TMDb v4 |
| QBITTORRENT | URL + identifiants | WebUI locale (`http://...`) |
| TRANSMISSION | URL + identifiants | RPC locale (`http://...:9091`) |
| DELUGE | URL + mot de passe | WebUI locale (`http://...:8112`) |
| DIVERS | Dossier torrents | Où sauvegarder les `.torrent` générés |
| DIVERS | Chiffrement config | Activer le chiffrement AES du fichier de config |

---

## 📁 Sources & Films

- **Films** : un fichier vidéo = un torrent
- **Séries** : un dossier saison = un torrent multi-fichiers
  ```
  Séries/Breaking Bad/Saison 1/   → Breaking.Bad.S01.MULTi.1080p.WEB-DL.x265-GROUPE.torrent
  ```

**Formats supportés :** `.mkv` `.mp4` `.avi` `.m4v` `.ts` `.mov`

---

## 🔒 Chiffrement de la configuration

Depuis la v1.4, la configuration peut être chiffrée avec **AES-256 via Fernet** (PBKDF2-SHA256, 260 000 itérations).

- Activer dans **PARAMÈTRES → DIVERS → Chiffrement config**
- Un mot de passe maître est demandé à la création, puis à chaque lancement
- Le fichier `.blackflag_config.json` est remplacé par `.blackflag_config.enc`
- Pour désactiver : basculer le toggle — la config repasse en JSON clair
- En cas d'oubli du mot de passe : supprimer `.blackflag_config.enc` pour repartir vierge

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
- MediaInfo requis pour la génération NFO complète : `MediaInfo.dll` (Windows), `libmediainfo.dylib` (macOS), `libmediainfo.so` (Linux) — à placer à côté de l'exécutable
- La configuration est sauvegardée à côté de l'exécutable (`.json` ou `.enc` selon le mode)
- Les logs horodatés sont dans le sous-dossier `logs/`

---

## 📜 Historique des versions

### v1.4
- **Support client Deluge 2.x** (JSON-RPC `/json`, port 8112) — ajout avec skip hash check (`seed_mode`)
- **Chiffrement AES de la configuration** (Fernet/PBKDF2-SHA256, 260 000 itérations)
- Popup mot de passe maître au lancement si config chiffrée détectée
- Toggle « Chiffrement config » dans les paramètres Divers
- Bootstrap `cryptography` auto-install silencieux
- Bouton DELUGE dans la sélection du client torrent (aux côtés de QB et Transmission)
- `_save_path()` helper : chaque client utilise ses propres chemins de sauvegarde
- Seed check par hash limité à qBittorrent (Deluge et Transmission : skip)

### v1.3
- Login La Cale corrigé (`/api/internal/auth/login`)
- **Support Torr9** (Web, JWT Bearer token)
- **Support MediaInfo** pour génération NFO complet (`.dll` Windows / `.dylib` macOS / `.so` Linux)
- Fenêtre historique des uploads : date, état seed, tracker (Treeview triable)
- Génération torrent + mise en seed qBittorrent avant upload
- Logs horodatés — un fichier par session ou erreur
- Toggle vérification des mises à jour (GitHub)
- Vérification TMDb Bearer Token et MediaInfo au lancement (bloquant si manquant)
- Tooltip QB path mis à jour

### v1.2
- **Vérification du seed avant upload** — le Worker attend que le torrent soit confirmé en seed dans qBittorrent (vérification par info-hash, 3 tentatives × 10 s) avant de lancer l'upload sur le tracker

### v1.1
- Release initiale publique
- Upload automatique vers La Cale (API + Web)
- Support qBittorrent et Transmission
- Interface tkinter sombre 7 langues
- Lecteur audio intégré (playlist pirate)
- Health check en deux passes + watcher

---

## ⚠️ Disclaimer

Cet outil est destiné à faciliter l'upload de contenu **dont vous êtes l'auteur ou disposez des droits** sur des trackers privés. Respectez les règles de La Cale et de Torr9, ainsi que les lois en vigueur dans votre pays.

---

*BLACK FLAG v1.4 — Theolddispatch & The40n8 — 2026*
