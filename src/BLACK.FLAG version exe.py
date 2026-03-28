#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BLACK FLAG v1.4 — Upload automatique vers La Cale et Torr9
Version exécutable

Logique séries :
  - Scan par SAISON (dossier) : Référence/Saison 1/ → 1 torrent multi-fichiers
  - Identification via nom du dossier SÉRIE (dossier parent)
  - Release name : Titre.S01.MULTi.1080p.WEB-DL.x265-GROUPE
  - TMDb : recherche série par nom + extraction saison du dossier
"""

# ══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP requests
# ══════════════════════════════════════════════════════════════════════════════
from platform import release
import sys, subprocess, os

def _bootstrap_requests():
    try:
        import requests; return True
    except ImportError:
        pass
    try:
        # CREATE_NO_WINDOW (0x08000000) empêche la fenêtre console noire sur Windows
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "requests"],
            timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **kwargs)
        import requests; return True
    except Exception:
        return False

_REQUESTS_OK = _bootstrap_requests()


def _bootstrap_pygame():
    """Auto-installe pygame si absent — nécessaire pour la lecture audio."""
    try:
        import pygame; return True
    except ImportError:
        pass
    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "pygame"],
            timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **kwargs)
        import pygame; return True
    except Exception:
        return False

_PYGAME_OK = _bootstrap_pygame()
if _PYGAME_OK:
    import pygame


def _bootstrap_mediainfo():
    """Auto-installe pymediainfo si absent — nécessaire pour le NFO complet."""
    try:
        from pymediainfo import MediaInfo; return True
    except ImportError:
        pass
    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "pymediainfo"],
            timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **kwargs)
        from pymediainfo import MediaInfo; return True
    except Exception:
        return False

_MEDIAINFO_OK = _bootstrap_mediainfo()
if _MEDIAINFO_OK:
    from pymediainfo import MediaInfo as _MediaInfo


def _bootstrap_cryptography():
    """Auto-installe cryptography si absent — nécessaire pour le chiffrement de la config."""
    try:
        from cryptography.fernet import Fernet; return True
    except ImportError:
        pass
    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "cryptography"],
            timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **kwargs)
        from cryptography.fernet import Fernet; return True
    except Exception:
        return False

_CRYPTO_OK = _bootstrap_cryptography()
if _CRYPTO_OK:
    from cryptography.fernet import Fernet as _Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes as _crypto_hashes
    import base64 as _b64_crypto

# ══════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ══════════════════════════════════════════════════════════════════════════════
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading, json, hashlib, time, re, unicodedata
from pathlib import Path

if _REQUESTS_OK:
    import requests

# ══════════════════════════════════════════════════════════════════════════════
# CHEMINS (compatibles PyInstaller onedir)
# ══════════════════════════════════════════════════════════════════════════════
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent.resolve()

CONFIG_FILE  = APP_DIR / ".blackflag_config.json"
HIST_FILE    = APP_DIR / "uploaded_torrents.txt"
TORRENTS_DIR = APP_DIR / "torrents"
LOG_DIR      = APP_DIR / "logs"
MUSIC_DIR  = APP_DIR / "music"
ARR_FILE   = MUSIC_DIR / "arr.ogg"
ARR_URLS   = [
    "https://opengameart.org/sites/default/files/arr.ogg",
    "https://opengameart.org/sites/default/files/arr.mp3",
    "https://opengameart.org/sites/default/files/Arr.ogg",
]

# Playlist — (nom_fichier_local, url_directe)
PLAYLIST = [
    ("pirate_theme.mp3",
     "https://opengameart.org/sites/default/files/Pirate%20Theme.mp3"),
    ("battle_theme_1.mp3",
     "https://opengameart.org/sites/default/files/Battle%20Theme%201.mp3"),
    ("battle_theme_2.mp3",
     "https://opengameart.org/sites/default/files/Battle%20Theme%202.mp3"),
    ("battle_theme_3.mp3",
     "https://opengameart.org/sites/default/files/Battle%20Theme%203.mp3"),
    ("battle_theme_4.mp3",
     "https://opengameart.org/sites/default/files/Battle%20Theme%204.mp3"),
    ("battle_theme_5.mp3",
     "https://opengameart.org/sites/default/files/Battle%20Theme%205.mp3"),
    ("pirate.mp3",
     "https://opengameart.org/sites/default/files/pirate.mp3"),
]

APP_VERSION   = "1.4"
APP_NEW_UPDATES = "v1.4 : Remplacez juste le fichier.py!\n- Support clients Deluge 2.x (JSON-RPC) et Vuze (Web Remote)\n- 2 thèmes d'interface : Relief d'or / Naine Bleue\n- Chiffrement AES de la config (Fernet/PBKDF2, mot de passe maître au lancement)\n- Bouton mise à jour automatique depuis GitHub (Paramètres > Divers)\n- Logs path uniformisés pour tous les clients torrent\n- Génération curl désactivée par défaut\n- Lecture streaming GitHub pour vérification de version (lignes 100-250)"

# URL du fichier source sur GitHub pour vérification de version
_UPDATE_URL = (
    "https://raw.githubusercontent.com/theolddispatch/"
    "BLACK-FLAG-version-exe/refs/heads/main/src/"
    "BLACK.FLAG%20version%20exe.py"
)
_UPDATE_PAGE = (
    "https://github.com/theolddispatch/BLACK-FLAG-version-exe/blob/main/"
    "Script%20%C3%A0%20%C3%A9x%C3%A9cuter%20si%20vous%20avez%20Python%20"
    "(beaucoup%20l'ont%20par%20d%C3%A9faut)/BLACK.FLAG%20version%20exe.py"
)

def _check_update_available():
    """
    Lit en streaming le fichier source GitHub (lignes 100 a 250 uniquement).
    Ne telecharge pas le fichier entier — s arrete apres la ligne 250.
    Retourne (True, changelog) si une version plus recente est disponible,
    (False, "") sinon.
    """
    if not _REQUESTS_OK:
        return False, ""
    try:
        r = requests.get(
            _UPDATE_URL, timeout=10, stream=True,
            headers={"User-Agent": "BLACK-FLAG-updater/" + APP_VERSION})
        if r.status_code != 200:
            r.close()
            return False, ""
        remote_version   = ""
        remote_changelog = ""
        line_num = 0
        for raw_line in r.iter_lines(decode_unicode=True):
            line_num += 1
            if line_num < 100:
                continue
            if line_num > 250:
                break
            stripped = raw_line.strip()
            if stripped.startswith('APP_VERSION') and '=' in stripped:
                remote_version = stripped.split('=')[1].strip().strip("\"'")
            if stripped.startswith('APP_NEW_UPDATES') and '=' in stripped:
                remote_changelog = stripped.split('=', 1)[1].strip().strip("\"'")
            if remote_version and remote_changelog:
                break
        r.close()
        if not remote_version:
            return False, ""
        def _v(s):
            try: return tuple(int(x) for x in s.strip().split("."))
            except: return (0,)
        if _v(remote_version) > _v(APP_VERSION):
            return True, remote_changelog
    except Exception:
        pass
    return False, ""

# ── Code de bypass santé (obfusqué, ne pas modifier) ─────────────────────────
_BF_OBF = b"GAwwByAoHRYPDg1oOw=="
_BF_KEY = b"BLACKFLAG_KEY_X"

def _check_bypass(val: str) -> bool:
    """Vérifie si la valeur saisie correspond au code de bypass."""
    try:
        import base64 as _b64
        decoded = bytes(
            c ^ _BF_KEY[i % len(_BF_KEY)]
            for i, c in enumerate(_b64.b64decode(_BF_OBF))
        ).decode()
        return val.strip() == decoded
    except Exception:
        return False
VIDEO_EXTS  = {".mkv", ".mp4", ".avi", ".m4v", ".ts", ".mov"}
SUB_EXTS    = {".srt", ".ass", ".ssa", ".sub", ".idx"}


def _ensure_music():
    """Télécharge tous les morceaux manquants. Retourne True si au moins un est dispo."""
    if not _REQUESTS_OK:
        return False
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    any_ok = False
    for fname, url in PLAYLIST:
        dest = MUSIC_DIR / fname
        if dest.exists():
            any_ok = True
            continue
        try:
            r = requests.get(url, timeout=30,
                             headers={"User-Agent":
                                      "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            if r.status_code == 200 and len(r.content) > 10_000:
                dest.write_bytes(r.content)
                any_ok = True
        except Exception:
            pass
    return any_ok

# ══════════════════════════════════════════════════════════════════════════════
# THÈME
# ══════════════════════════════════════════════════════════════════════════════
C = dict(
    bg="#0d0d0d", panel="#111111", border="#1e1e1e",
    gold="#eab308", gold_dim="#7a5c00",
    text="#d4d4d4", muted="#4a4a4a",
    green="#22c55e", red="#ef4444",
    ibg="#141414", ifg="#e0e0e0",
)

# ── Palettes de thèmes ────────────────────────────────────────────────────────
THEMES = {
    "gold": dict(          # Relief d'or (thème original)
        bg="#0d0d0d", panel="#111111", border="#1e1e1e",
        gold="#eab308", gold_dim="#7a5c00",
        text="#d4d4d4", muted="#4a4a4a",
        green="#22c55e", red="#ef4444",
        cyan="#38bdf8",
        ibg="#141414", ifg="#e0e0e0",
    ),
    "blue": dict(          # Naine Bleue
        bg="#06080f", panel="#0d1117", border="#1a2332",
        gold="#38bdf8", gold_dim="#1e5f8a",
        text="#cdd9e5", muted="#3d5166",
        green="#22c55e", red="#ef4444",
        cyan="#7dd3fc",
        ibg="#0d1117", ifg="#cdd9e5",
    ),
}
THEME_NAMES = {"gold": "Relief d'or", "blue": "Naine Bleue"}
_current_theme = ["gold"]   # référence mutable
FM  = ("Courier New", 9)
FM8 = ("Courier New", 8)
FB  = ("Courier New", 9, "bold")
FL  = ("Courier New", 9)

GRADES    = ["Observateur (1)", "Initié (5)", "Matelot (10)",
             "Quartier-maître (20)", "Officier (50)", "Capitaine (100)"]
GRADE_MAX = [1, 5, 10, 20, 50, 100]

# Grades traduits par langue (même ordre que GRADE_MAX)
GRADES_I18N = {
    "fr": ["Observateur (1)", "Initié (5)", "Matelot (10)",
           "Quartier-maître (20)", "Officier (50)", "Capitaine (100)"],
    "en": ["Observer (1)", "Initiate (5)", "Sailor (10)",
           "Quartermaster (20)", "Officer (50)", "Captain (100)"],
    "es": ["Observador (1)", "Iniciado (5)", "Marinero (10)",
           "Contramaestre (20)", "Oficial (50)", "Capitán (100)"],
    "de": ["Beobachter (1)", "Eingeweihter (5)", "Matrose (10)",
           "Quartiermeister (20)", "Offizier (50)", "Kapitän (100)"],
    "it": ["Osservatore (1)", "Iniziato (5)", "Marinaio (10)",
           "Nostromo (20)", "Ufficiale (50)", "Capitano (100)"],
    "pt": ["Observador (1)", "Iniciado (5)", "Marinheiro (10)",
           "Contramestre (20)", "Oficial (50)", "Capitão (100)"],
    "ja": ["見習い (1)", "入門者 (5)", "水兵 (10)",
           "航海長 (20)", "士官 (50)", "艦長 (100)"],
}

def get_grades():
    """Retourne la liste des grades dans la langue UI courante."""
    return GRADES_I18N.get(_lang, GRADES)

ASCII_LOGO = """\
      ___           ___       ___           ___           ___     
     /\\  \\         /\\__\\     /\\  \\         /\\  \\         /\\__\\   
    /::\\  \\       /:/  /    /::\\  \\       /::\\  \\       /:/  /   
   /:/\\:\\  \\     /:/  /    /:/\\:\\  \\     /:/\\:\\  \\     /:/__/    
  /::\\~\\:\\__\\   /:/  /    /::\\~\\:\\  \\   /:/  \\:\\  \\   /::\\__\\____
 /:/\\:\\ \\:|__| /:/__/    /:/\\:\\ \\:\\__\\ /:/__/ \\:\\__\\ /:/\\:::::\\__\\
 \\:\\~\\:\\/:/  / \\:\\  \\    \\/__\\:\\/:/  / \\:\\  \\  \\/__/ \\/_|:|~~|~  
  \\:\\ \\::/  /   \\:\\  \\        \\::/  /   \\:\\  \\          |:|  |   
   \\:\\/:/  /     \\:\\  \\       /:/  /     \\:\\  \\         |:|  |   
    \\::/__/       \\:\\__\\     /:/  /       \\:\\__\\        |:|  |   
     ~~            \\/__/     \\/__/         \\/__/         \\|__|    
      ___           ___       ___           ___     
     /\\  \\         /\\__\\     /\\  \\         /\\  \\    
    /::\\  \\       /:/  /    /::\\  \\       /::\\  \\   
   /:/\\:\\  \\     /:/  /    /:/\\:\\  \\     /:/\\:\\  \\  
  /::\\~\\:\\  \\   /:/  /    /::\\~\\:\\  \\   /:/  \\:\\  \\ 
 /:/\\:\\ \\:\\__\\ /:/__/    /:/\\:\\ \\:\\__\\ /:/__/_\\:\\__\\
 \\/__\\:\\ \\/__/ \\:\\  \\    \\/__\\:\\/:/  / \\:\\  /\\ \\/__/
      \\:\\__\\    \\:\\  \\        \\::/  /   \\:\\ \\:\\__\\  
       \\/__/     \\:\\  \\       /:/  /     \\:\\/:/  /  
                  \\:\\__\\     /:/  /       \\::/  /   
                   \\/__/     \\/__/         \\/__/     \
"""

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════
DEFAULTS = {
    "films_dir":       r"\\NAS_IP\Films ou chemin du dossier",
    "max_movies":      "1",
    "series_dir":      r"\\NAS_IP\Séries ou chemin du dossier",
    "max_series":      "1",
    "min_quality":     "",
    "lacale_url":      "https://la-cale.space",
    "lacale_user":     "",
    "lacale_pass":     "",
    "lacale_passkey":  "",
    "conn_mode":       "web",   # "api" ou "web"
    "tracker_url":     "https://tracker.la-cale.space/announce?passkey=",
    "tmdb_token":      "",
    "tmdb_lang":       "fr-FR",
    "qb_url":          "Url de connexion Qbittorrent (même si locale)",
    "qb_user":         "admin",
    "qb_pass":         "",
    "qb_films_path":   "/Films",
    "qb_series_path":  "/Series",
    "active_tracker":  "lacale",         # "lacale" ou "torr9"
    "torr9_url":       "https://torr9.net/upload",
    "torr9_user":      "",
    "torr9_pass":      "",
    "torr9_token":     "",
    "torr9_announce":  "https://tracker.torr9.net/announce/****A CHANGER****",
    "mediainfo_dll":   "",
    "mediainfo_dylib": "",
    "mediainfo_so":    "",
    "torrent_client":  "qbittorrent",   # "qbittorrent" ou "transmission"
    "tr_url":          "http://192.168.1.x:9091",
    "tr_user":         "",
    "tr_pass":         "",
    "tr_films_path":   "/Films",
    "tr_series_path":  "/Series",
    "discord_webhook": "",
    "torrents_dir":    str(TORRENTS_DIR),
    "upload_delay":    "3",
    "notify_enabled":  False,
    "notify_interval": "10",   # minutes : "10", "20", "60"
    "save_logs":       True,
    "save_curl":       False,
    "check_updates":   True,
    "ui_lang":           "fr",
    "ui_theme":          "gold",
    "encrypt_cfg":       True,
    "seed_check":        True,
    "autosave_enabled":  True,
    "deluge_url":        "http://192.168.1.x:8112",
    "deluge_pass":       "",
    "deluge_films_path": "/Films",
    "deluge_series_path":"/Series",
    "vuze_url":          "http://192.168.1.x:9091",
    "vuze_user":         "vuze",
    "vuze_pass":         "",
    "vuze_films_path":   "/Films",
    "vuze_series_path":  "/Series",
}

# ── Chiffrement config ───────────────────────────────────────────────────────
_CRYPTO_SALT = b"BLACKFLAG_SALT_v14_2024"
CONFIG_ENC_FILE = APP_DIR / ".blackflag_config.enc"
# Mot de passe maître de session (défini par la popup au lancement)
_SESSION_MASTER_PW = [None]   # [str|None]


def _derive_key(password: str) -> bytes:
    """Dérive une clé Fernet 32 octets depuis le mot de passe maître (PBKDF2-SHA256)."""
    kdf = PBKDF2HMAC(
        algorithm=_crypto_hashes.SHA256(),
        length=32,
        salt=_CRYPTO_SALT,
        iterations=260_000,
    )
    raw = kdf.derive(password.encode("utf-8"))
    return _b64_crypto.urlsafe_b64encode(raw)


def _get_fernet():
    """Retourne un Fernet avec le mot de passe maître de session, ou None."""
    if not _CRYPTO_OK:
        return None
    pw = _SESSION_MASTER_PW[0]
    if pw is None:
        return None
    try:
        return _Fernet(_derive_key(pw))
    except Exception:
        return None


def _encrypt_cfg(data: dict) -> bytes | None:
    f = _get_fernet()
    if f is None:
        return None
    try:
        return f.encrypt(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    except Exception:
        return None


def _decrypt_cfg(blob: bytes) -> dict | None:
    f = _get_fernet()
    if f is None:
        return None
    try:
        return json.loads(f.decrypt(blob).decode("utf-8"))
    except Exception:
        return None


def load_cfg():
    d = dict(DEFAULTS)
    # 1. Essai config chiffrée (si mot de passe de session disponible)
    if CONFIG_ENC_FILE.exists() and _CRYPTO_OK and _SESSION_MASTER_PW[0]:
        try:
            dec = _decrypt_cfg(CONFIG_ENC_FILE.read_bytes())
            if dec is not None:
                d.update(dec)
                return d
            # mauvais mot de passe → on tombe sur le fallback JSON
        except Exception:
            pass
    # 2. Fallback JSON clair
    if CONFIG_FILE.exists():
        try:
            d.update(json.loads(CONFIG_FILE.read_text("utf-8")))
        except Exception:
            pass
    return d


def save_cfg(d):
    encrypt = d.get("encrypt_cfg", True)
    if encrypt and _CRYPTO_OK and _SESSION_MASTER_PW[0]:
        blob = _encrypt_cfg(d)
        if blob is not None:
            try:
                CONFIG_ENC_FILE.write_bytes(blob)
                if CONFIG_FILE.exists():
                    CONFIG_FILE.unlink(missing_ok=True)
                return
            except Exception:
                pass
    # JSON clair
    if CONFIG_ENC_FILE.exists():
        try:
            CONFIG_ENC_FILE.unlink(missing_ok=True)
        except Exception:
            pass
    try:
        CONFIG_FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
# PARSING — FILMS (fichier individuel)
# ══════════════════════════════════════════════════════════════════════════════
def _unc_to_linux(path: str) -> str:
    """
    Retourne le chemin QB tel quel s'il est déjà un chemin Linux absolu.
    Si c'est un chemin UNC Windows (//NAS/share/...), extrait uniquement
    le dernier segment comme nom de montage Docker (ex: /Films).
    
    Exemples :
      /Films                              → /Films  (inchangé)
      //192.168.1.x/Mediathèque/.../Films → /Films  (dernier segment)
    """
    p = path.replace("\\", "/").rstrip("/")
    # Déjà un chemin Linux absolu → retourner tel quel
    if not p.startswith("//"):
        return p
    # Chemin UNC → extraire le dernier segment comme point de montage Docker
    import re
    m = re.match(r'^//[^/]+/(.+)$', p)
    if m:
        # Prendre uniquement le dernier segment du chemin UNC
        segments = m.group(1).rstrip("/").split("/")
        return "/" + segments[-1]
    return p


def parse_filename(filename):
    stem = Path(filename).stem
    su   = stem.upper()
    su = re.sub(r'\.(FR|EN|ES|PT|IT|DE|RO|RU|NL|PL|HI|TR|AR|EL|SV|DA|NO|FI)$', '', su)
    su = su.replace("-SONARR", "").replace("-RADARR", "")

    # --- 1. Correction Bug 1900/1923 (Titres numériques) ---
    # Chercher d'abord une année entre parenthèses (ex: (1976))
    m_year = re.search(r'\(((?:19|20)\d{2})\)', stem)
    if m_year:
        year = m_year.group(1)
        raw = re.split(re.escape(f"({year})"), stem, flags=re.I, maxsplit=1)[0]
    else:
        # Sinon, chercher la DERNIÈRE occurrence d'une année pour éviter de confondre avec le titre
        years = re.findall(r'(?<!\d)((?:19|20)\d{2})(?!\d)', su)
        year = years[-1] if years else ""
        if year:
            raw = re.split(year, stem, flags=re.I)[0]
        else:
            raw = re.split(r'(?i)[._](?:1080p|720p|2160p|4k|bluray|web.?dl|webrip|hdtv|x264|x265|hevc)', stem)[0]
    
    title = re.sub(r'[._\-]', ' ', raw).strip()
    title = re.sub(r'^\s*\[.*?\]\s*', '', title)
    title = re.sub(r'^\s*\(.*?\)\s*', '', title)
    title = re.sub(r'\(?\s*$', '', title).strip()

    # --- 2. Détection Technique (Qualité, Codec, etc.) ---
    res = ""
    if   re.search(r'2160P|4K|UHD', su): res = "2160p"
    elif re.search(r'1080P', su):         res = "1080p"
    elif re.search(r'720P',  su):         res = "720p"
    elif re.search(r'480P',  su):         res = "480p"
    # AJOUT : Détection de la définition standard (SD)
    elif re.search(r'SDTV|SD\b|DVD(?:RIP|R)?\b', su): res = "SD"
    if not res: res = "SD"

    # --- Détection Technique (Source sécurisée) ---
    src = "WEB-DL" # Fallback standard pour les sorties streaming
    for pat, val in [
        (r'\bCOMPLETE\.UHD\.BLU\b',     "COMPLETE.UHD.BLURAY"),
        (r'\bCOMPLETE\.BLU\b',         "COMPLETE.BLURAY"),
        (r'\b(BLU.?RAY\.REMUX|BD\.REMUX)\b', "BluRay.REMUX"),
        (r'(?<!UHD)\bREMUX\b',         "REMUX"),
        (r'\b4KLIGHT\b',               "4KLight"),
        (r'\bHDLIGHT\b',               "HDLight"),
        (r'\b(BLU.?RAY|BDRIP|BRRIP)\b', "BluRay"),
        (r'\b(WEB.?DL|WEBDL)\b',       "WEB-DL"),
        (r'\bWEBRIP\b',                "WEBRip"),
        (r'\bDVDRIP\b',                "DVDRip"),
        (r'\bHDTV\b',                  "HDTV")
    ]:
        if re.search(pat, su): 
            src = val
            break

    vc = "x264"
    for pat, val in [(r'X265|H265|HEVC',"x265"),(r'X264|H264|AVC',"x264"),(r'AV1',"AV1"),(r'VC.?1',"VC-1")]:
        if re.search(pat, su): vc = val; break

    ac = "AAC"
    for pat, val in [(r'TRUEHD',"TrueHD"),(r'EAC3|E-AC3|DDP',"EAC3"),(r'AC3|\bDD\b',"AC3"),(r'DTS.?X\b',"DTS-X"),
                     (r'DTS.HD.MA',"DTS-HD.MA"),(r'DTS.HD',"DTS-HD"),(r'\bDTS\b',"DTS"),(r'\bFLAC\b',"FLAC"),(r'\bOPUS\b',"OPUS")]:
        if re.search(pat, su): ac = val; break

    ach   = next((v for p,v in [(r'7\.1',"7.1"),(r'5\.1',"5.1"),(r'2\.0',"2.0")] if re.search(p,su)),"")
    hdr   = "HDR10+" if re.search(r'HDR10\+|HDR10PLUS', su) else ("HDR" if re.search(r'HDR', su) else "")
    if re.search(r'\bDV\b|DOLBY.?VISION', su): hdr = (hdr+".DV") if hdr else "DV"

# --- 3. Détection des Langues (Généralisée) ---
    found_langs = []
    # Liste exhaustive avec frontières de mots (\b) pour éviter de matcher dans le titre (ex: THINGS -> HIN)
    lang_patterns = [
        (r'\b(FRENCH|FR|VFF|VFQ|TRUEFRENCH)\b', "FRENCH"),
        (r'\b(ENGLISH|EN|ENG|VO)\b', "ENGLISH"),
        (r'\b(SPANISH|ESP)\b', "SPANiSH"),
        (r'\b(ITALIAN|ITA)\b', "iTALiAN"),
        (r'\b(GERMAN|GER|DEU)\b', "GERMAN"),
        (r'\b(PORTUGUESE|POR)\b', "PORTUGUESE"),
        (r'\b(ROMANIAN|ROU|ROM)\b', "ROMANiAN"),
        (r'\b(RUSSIAN|RUS)\b', "RUSSiAN"),
        (r'\b(DUTCH|HOL|NED)\b', "DUTCH"),
        (r'\b(POLISH|POL)\b', "POLiSH"),
        (r'\b(CHINESE|CHI|ZHO|MANDARIN)\b', "CHiNESE"),
        (r'\b(JAPANESE|JAP|NIPPON)\b', "JAPANESE"),
        (r'\b(KOREAN|KOR)\b', "KOREAN"),
        (r'\b(HINDI|HIN)\b', "HiNDi"),
        (r'\b(TURKISH|TUR|TRK)\b', "TURKiSH"),
        (r'\b(ARABIC|ARA)\b', "ARABiC"),
        (r'\b(GREEK|GRE|ELL)\b', "GREEK"),
        (r'\b(SWEDISH|SWE)\b', "SWEDiSH"),
        (r'\b(DANISH|DAN)\b', "DANiSH"),
        (r'\b(NORWEGIAN|NOR)\b', "NORWEGiAN"),
        (r'\b(FINNISH|FIN)\b', "FiNNiSH"),
        (r'\b(PERSIAN|PER|FAR|FARSI)\b', "PERSiAN"),
    ]

    # On scanne d'abord toutes les langues présentes dans le nom
    for pat, val in lang_patterns:
        if re.search(pat, su):
            found_langs.append(val)

    # Détection MULTi : mot-clé explicite OU au moins 2 langues différentes détectées
    if re.search(r'\b(MULTI|DOUBLAGE|DUAL)\b|EN.*FR|FR.*EN', su) or len(set(found_langs)) >= 2:
        lang = "MULTi"
    elif found_langs:
        lang = found_langs[0]
    else:
        lang = "FRENCH" # Fallback par défaut

    # Edition et Groupe
    ed = ""
    for pat, tag in [(r'\.DC\.|DIRECTOR.?S.?CUT',".DC"),(r'EXTENDED',".EXTENDED"),(r'UNRATED',".UNRATED"),(r'REMASTER',".REMASTERED"),(r'CRITERION',".CRiTERION")]:
        if re.search(pat, su): ed += tag
    grp = ""
    m_grp = re.search(r'-([A-Za-z0-9]+)$', stem)
    if m_grp: grp = m_grp.group(1)

    return dict(title=title, year=year, res=res, src=src, vc=vc, ac=ac,
                ach=ach, lang=lang, edition=ed.lstrip("."), group=grp,
                ext=Path(filename).suffix.lower(), hdr=hdr,
                found_langs=found_langs) # AJOUTÉ ICI

def _clean_title(t):
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[''ʼ\":!?,;{}()\[\]]", "", t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = " ".join(w.capitalize() for w in t.split())
    return t.replace(" ", ".")


def build_release_name_movie(title, year, p):
    parts = [_clean_title(title), str(year)]
    if p.get("edition"): parts.append(p["edition"])
    if p.get("imax"):    parts.append(p["imax"])
    parts.append(p.get("lang", "FRENCH"))
    if p.get("hdr"):     parts.append(p["hdr"])
    if p.get("res"):     parts.append(p["res"])
    if p.get("plat"):    parts.append(p["plat"])
    parts.append(p.get("src", "WEB"))
    if p.get("ac"):      parts.append(p["ac"])
    if p.get("ach"):     parts.append(p["ach"])
    if p.get("atmos"):   parts.append(p["atmos"])
    parts.append(f"{p.get('vc','x264')}-{p.get('group') or 'NOGRP'}")
    return ".".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# PARSING — SÉRIES (dossier de saison)
# ══════════════════════════════════════════════════════════════════════════════
def parse_season_dir(season_dir: Path):
    series_dir  = season_dir.parent
    raw_dirname = series_dir.name if re.search(r'(?:saison|season|s\d)', season_dir.name, re.I) else season_dir.name
    
    # --- DÉTECTION DU NOM ET DE L'ANNÉE ---
    # On cherche l'année (ex: (2016))
    m_year = re.search(r'\(((?:19|20)\d{2})\)', raw_dirname)
    series_year = m_year.group(1) if m_year else ""
    
    # On nettoie le nom de la série
    series_name = re.sub(r'\s*\((?:19|20)\d{2}\)\s*$', '', raw_dirname).strip()

    # Nettoyage pour TMDb : points → espaces, coupe au tiret de saison (ex: "24 - S01" → "24")
    series_name = series_name.replace('.', ' ').strip()
    series_name = series_name.split(' - ')[0].split(' — ')[0].strip()

    # Numéro de saison depuis le nom du dossier
    season_num = 1
    m = re.search(r'(?:saison|season|s)\s*(\d{1,2})', season_dir.name, re.I)
    if m:
        season_num = int(m.group(1))

    files = sorted(f for f in season_dir.iterdir()
                   if f.is_file() and (f.suffix.lower() in VIDEO_EXTS or f.suffix.lower() in SUB_EXTS))

    # --- NOUVEAU : Compter uniquement les vrais épisodes (vidéos) ---
    video_count = sum(1 for f in files if f.suffix.lower() in VIDEO_EXTS)
    
    # On cherche le premier fichier vidéo pour extraire les tags
    video_files = [f for f in files if f.suffix.lower() in VIDEO_EXTS]
    ref_file = video_files[0] if video_files else (files[0] if files else None)
    tags = parse_filename(ref_file.name) if ref_file else {}

    total_size = sum(f.stat().st_size for f in files)

    return dict(
        series_name=series_name,
        series_year=series_year,
        season_num=season_num,
        season_tag=f"S{season_num:02d}",
        files=files,
        video_count=video_count, # AJOUTÉ
        total_size=total_size,
        tags=tags,
    )

def build_release_name_season(series_title, season_tag, p):
    """Construit le nom de release pour une saison : Titre.S01.MULTi.1080p.WEB-DL.x265-GRP"""
    parts = [_clean_title(series_title), season_tag]
    if p.get("edition"): parts.append(p["edition"])
    parts.append(p.get("lang", "FRENCH"))
    if p.get("hdr"):     parts.append(p["hdr"])
    if p.get("res"):     parts.append(p["res"])
    if p.get("plat"):    parts.append(p["plat"])
    parts.append(p.get("src", "WEB"))
    if p.get("ac"):      parts.append(p["ac"])
    if p.get("ach"):     parts.append(p["ach"])
    if p.get("atmos"):   parts.append(p["atmos"])
    parts.append(f"{p.get('vc','x264')}-{p.get('group') or 'NOGRP'}")
    return ".".join(parts)


def scan_seasons(series_root: Path, prog_cb=None):
    """
    Retourne la liste des dossiers de saison à traiter.
    Supporte :
      Series/Breaking Bad/Saison 1/  (structure standard)
      Series/Breaking Bad/E01.mkv    (pas de sous-dossier → saison unique synthétique)
    """
    seasons = []
    for show_dir in sorted(series_root.iterdir()):
        if not show_dir.is_dir():
            continue
        # Chercher les sous-dossiers de saisons
        sub_season_dirs = [d for d in sorted(show_dir.iterdir())
                           if d.is_dir() and re.search(
                               r'(?:saison|season|s\d)', d.name, re.I)]
        if sub_season_dirs:
            seasons.extend(sub_season_dirs)
        else:
            # Pas de sous-dossiers de saisons → considérer le dossier show comme S01
            has_video = any(f.suffix.lower() in VIDEO_EXTS
                            for f in show_dir.iterdir() if f.is_file())
            if has_video:
                seasons.append(show_dir)
        if prog_cb:
            prog_cb(len(seasons))
    return seasons


# ══════════════════════════════════════════════════════════════════════════════
# CRÉATION TORRENT
# ══════════════════════════════════════════════════════════════════════════════
def bencode(v):
    if isinstance(v, int):
        return b"i" + str(v).encode() + b"e"
    if isinstance(v, (bytes, bytearray)):
        return str(len(v)).encode() + b":" + bytes(v)
    if isinstance(v, str):
        e = v.encode("utf-8")
        return str(len(e)).encode() + b":" + e
    if isinstance(v, list):
        return b"l" + b"".join(bencode(i) for i in v) + b"e"
    if isinstance(v, dict):
        out = b"d"
        for k in sorted(v):
            bk = k.encode() if isinstance(k, str) else k
            out += str(len(bk)).encode() + b":" + bk + bencode(v[k])
        return out + b"e"


def _piece_length(total_size):
    if   total_size <  512 * 1024**2: return 256  * 1024
    elif total_size <    2 * 1024**3: return 512  * 1024
    elif total_size <    4 * 1024**3: return 1024 * 1024
    elif total_size <    8 * 1024**3: return 2048 * 1024
    else:                             return 4096 * 1024


def torrent_info_hash(torrent_bytes: bytes) -> str:
    """Calcule l'info-hash SHA1 d'un torrent à partir de ses bytes bencoded."""
    import re as _re
    # Trouver le début de la valeur 'info' dans le bencode
    # Format: ...4:infod...e... → on cherche '4:info' puis on extrait la valeur
    marker = b'4:info'
    idx = torrent_bytes.find(marker)
    if idx == -1:
        return ""
    info_start = idx + len(marker)
    # La valeur info est un dict bencoded — on trouve sa fin
    # On bencode/décode pour extraire précisément
    try:
        def _bdecode_len(data, pos):
            """Retourne la position de fin de la valeur bencoded à pos."""
            c = chr(data[pos])
            if c == 'i':
                end = data.index(ord('e'), pos + 1)
                return end + 1
            elif c == 'l' or c == 'd':
                pos += 1
                while chr(data[pos]) != 'e':
                    pos = _bdecode_len(data, pos)
                return pos + 1
            elif c.isdigit():
                colon = data.index(ord(':'), pos)
                n = int(data[pos:colon])
                return colon + 1 + n
            return pos + 1
        info_end = _bdecode_len(torrent_bytes, info_start)
        info_bytes = torrent_bytes[info_start:info_end]
        return hashlib.sha1(info_bytes).hexdigest()
    except Exception:
        return ""


def make_torrent_single(fp: Path, tracker: str, prog_cb=None, source: str = "lacale",
                        torrent_name: str = "") -> bytes:
    """
    Torrent single-file (films).
    torrent_name : nom dans le dict info (= release name + ext).
                   Si vide, utilise fp.name (nom fichier brut).
                   IMPORTANT : doit correspondre exactement au nom stocké
                   par le tracker pour que l'info-hash soit identique.
    """
    sz = fp.stat().st_size
    pl = _piece_length(sz)
    pieces = bytearray()
    read = 0
    with open(fp, "rb") as f:
        while True:
            chunk = f.read(pl)
            if not chunk: break
            pieces += hashlib.sha1(chunk).digest()
            read   += len(chunk)
            if prog_cb: prog_cb(read / sz)
    name = torrent_name if torrent_name else fp.name
    info = {"name": name, "piece length": pl, "pieces": bytes(pieces),
            "length": sz, "private": 1, "source": source}
    return bencode({"announce": tracker, "info": info,
                    "created by": "BLACK FLAG", "creation date": int(time.time())})


def make_torrent_multi(folder_name: str, files: list, tracker: str, prog_cb=None,
                       source: str = "lacale") -> bytes:
    """Version corrigée : hachage en flux continu pour éviter l'erreur libtorrent:12."""
    total_size = sum(f.stat().st_size for f in files)
    pl         = _piece_length(total_size)
    pieces     = bytearray()
    read       = 0
    buf        = bytearray()

    for fp in files:
        with open(fp, "rb") as fh:
            while True:
                needed = pl - len(buf)
                chunk = fh.read(needed)
                if not chunk:
                    break
                buf += chunk
                if len(buf) == pl:
                    pieces += hashlib.sha1(buf).digest()
                    read   += pl
                    buf.clear()
                    if prog_cb: prog_cb(read / total_size)
    if buf:
        pieces += hashlib.sha1(buf).digest()
        read   += len(buf)
        if prog_cb: prog_cb(read / total_size)

    file_list = [{"length": f.stat().st_size, "path": [f.name]} for f in files]
    info = {"name": folder_name, "piece length": pl, "pieces": bytes(pieces),
            "files": file_list, "private": 1, "source": source}
    return bencode({"announce": tracker, "info": info,
                    "created by": "BLACK FLAG", "creation date": int(time.time())})

# ══════════════════════════════════════════════════════════════════════════════
# LA CALE CLIENT
# ══════════════════════════════════════════════════════════════════════════════
class LaCale:
    LANG_TERMS = {
        "MULTi":      ["term_fd7d017b825ebf12ce579dacea342e9d",
                       "term_bf918c3858a7dfe3b44ca70232f50272",
                       "term_c87b5416341e6516baac12aa01fc5bc9"],
        "MULTi.VFF":  ["term_fd7d017b825ebf12ce579dacea342e9d",
                       "term_bf31bb0a956b133988c2514f62eb1535"],
        "MULTi.VFQ":  ["term_fd7d017b825ebf12ce579dacea342e9d",
                       "term_5fe7a76209bfc33e981ac5a2ca5a2e40"],
        "FRENCH":     ["term_bf918c3858a7dfe3b44ca70232f50272"],
        "TRUEFRENCH": ["term_bf31bb0a956b133988c2514f62eb1535"],
        "VOSTFR":     ["term_c87b5416341e6516baac12aa01fc5bc9",
                       "term_5557a0dc2dff9923f8665c96246e2964"],
    }
    EXT_TERMS = {".mkv": "term_513ee8e7d062c6868b092c9a4267da8a",
                 ".mp4": "term_069f4f60531ce23f9f2bfe4ce834d660",
                 ".avi": "term_79db12fca0a1e537f6185f7aee22b8d7"}
    SRC_QUAI  = {"WEB-DL": "WEB-DL", "WEB": "WEB-DL", "WEBRip": "WEBRip",
                 "BluRay": "BluRay", "COMPLETE.UHD.BLURAY": "BluRay",
                 "COMPLETE.BLURAY": "BluRay", "BluRay.REMUX": "REMUX",
                 "REMUX": "REMUX", "DVDRip": "DVDRip", "HDTV": "HDTV",
                 "HDLight": "WEB-DL", "4KLight": "WEB-DL", "mHD": "WEB-DL"}

    def __init__(self, url, log):
        self.url    = url.rstrip("/")
        self.log    = log
        self.sess   = requests.Session()
        self.sess.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        self.cat_film   = None
        self.cat_series = None
        self.cat_vo     = None
        self.quais      = {}

    def _get(self, p, **kw):  return self.sess.get(self.url + p,  timeout=20, **kw)
    def _post(self, p, **kw): return self.sess.post(self.url + p, timeout=60, **kw)

    def health_check(self):
        """
        Vérifie l'état de santé du site en deux passes.

        Passe 1 — Source externe (ipinfo.io) interroge la-cale.space via un
                   service tiers pour confirmer que le site est joignable depuis
                   l'internet public (et non juste depuis notre réseau local).
        Passe 2 — Requête directe HEAD sur la-cale.space pour vérifier
                   que le site répond correctement depuis notre machine.

        Retourne (ok: bool, message: str)
        """
        # ── Passe 1 : vérification via source externe ─────────────────────
        self.log("  Passe 1 — Vérification externe du site...", "muted")
        try:
            # On utilise l'API publique de status.io ou un simple HEAD via
            # un service tiers. On utilise ici l'API gratuite de updownio-like :
            # https://www.isitdownrightnow.com/ expose un endpoint JSON non documenté
            # On préfère passer par un checker fiable et simple :
            # https://api.codetabs.com/v1/proxy?quest=URL renvoie le contenu via proxy
            # Alternative simple : on HEAD une URL via requests avec un timeout court
            # depuis deux résolveurs différents (cloudflare DNS check style)
            #
            # Solution retenue : requête vers l'API publique open-source
            # https://api.uptimerobot.com n'est pas gratuit sans clé.
            # On utilise https://www.isitdownrightnow.com/check.php?domain=la-cale.space
            ext_url = "https://www.isitdownrightnow.com/check.php"
            r = requests.get(ext_url,
                             params={"domain": "la-cale.space"},
                             timeout=10,
                             headers={"User-Agent": self.sess.headers["User-Agent"]})
            body = r.text.lower()
            if r.status_code == 200:
                if "up" in body and "down" not in body:
                    self.log("  ✓ Passe 1 OK — site joignable depuis l'extérieur.", "ok")
                elif "down" in body:
                    self.log("  ✗ Passe 1 : le site semble hors ligne (détection externe).", "err")
                    return False, "La Cale est inaccessible depuis l'internet public."
                else:
                    # Réponse ambiguë — on continue prudemment
                    self.log("  ~ Passe 1 : réponse ambiguë, on continue.", "muted")
            else:
                self.log(f"  ~ Passe 1 : checker externe indisponible (HTTP {r.status_code}), on continue.", "muted")
        except Exception as e:
            # Si le checker externe est lui-même injoignable, on ne bloque pas
            self.log(f"  ~ Passe 1 : checker externe injoignable ({e}), on continue.", "muted")

        # ── Passe 2 : connexion directe au site ───────────────────────────
        self.log("  Passe 2 — Connexion directe à La Cale...", "muted")
        try:
            r = self.sess.head(self.url, timeout=10,
                               headers={"Accept": "text/html"})
            if r.status_code in (200, 301, 302, 307, 308):
                self.log(f"  ✓ Passe 2 OK — site répond (HTTP {r.status_code}).", "ok")
                return True, "OK"
            elif r.status_code == 403:
                self.log("  ✗ Passe 2 : accès refusé (403) — Cloudflare actif ?", "err")
                return False, f"La Cale bloque l'accès (HTTP 403 — protection Cloudflare possible)."
            elif r.status_code == 503:
                self.log("  ✗ Passe 2 : site en maintenance (503).", "err")
                return False, "La Cale est en maintenance (HTTP 503)."
            else:
                self.log(f"  ✗ Passe 2 : réponse inattendue (HTTP {r.status_code}).", "err")
                return False, f"La Cale répond HTTP {r.status_code}."
        except requests.exceptions.ConnectionError:
            self.log("  ✗ Passe 2 : impossible de joindre le site (erreur réseau).", "err")
            return False, "Impossible de joindre La Cale — vérifiez votre connexion internet."
        except requests.exceptions.Timeout:
            self.log("  ✗ Passe 2 : délai d'attente dépassé (timeout).", "err")
            return False, "La Cale ne répond pas (timeout)."
        except Exception as e:
            self.log(f"  ✗ Passe 2 : erreur inattendue : {e}", "err")
            return False, str(e)

    def login(self, email, pwd):
        self.log("Connexion à La Cale...", "gold")
        token = ""
        try:
            ch = self._get("/api/internal/auth/altcha/challenge?scope=login",
                           headers={"Accept": "application/json",
                                    "Referer": self.url + "/login"}).json()
            token = self._solve_altcha(ch)
            if token: self.log("  PoW Altcha résolu.", "muted")
        except Exception:
            pass
        payload = {"email": email, "password": pwd,
                   "formLoadedAt": int(time.time() * 1000)}
        if token: payload["altcha"] = token
        r = self._post("/api/internal/auth/login", json=payload,
                       headers={"Content-Type": "application/json",
                                "Accept": "application/json",
                                "Referer": self.url + "/login",
                                "Origin": self.url})
        ok = r.status_code == 200 or '"user"' in r.text
        self.log("  Connexion OK." if ok else f"  Erreur login (HTTP {r.status_code}).",
                 "ok" if ok else "err")
        return ok

    def _solve_altcha(self, ch):
        import base64, json as _j
        alg  = ch.get("algorithm", "SHA-256")
        salt = ch.get("salt", "")
        c_str= ch.get("challenge", "")
        maxn = int(ch.get("maxnumber", 1_000_000))
        sig  = ch.get("signature", "")
        for n in range(maxn + 1):
            if hashlib.sha256(f"{salt}{n}".encode()).hexdigest() == c_str:
                payload = _j.dumps({"algorithm": alg, "challenge": c_str,
                                    "number": n, "salt": salt, "signature": sig},
                                   separators=(",", ":"))
                return base64.b64encode(payload.encode()).decode()
        return ""

    def prepare(self):
        """Découvre les catégories Films et Séries + les termIds de quais."""
        try:
            r_cats = self._get("/api/internal/categories",
                             headers={"Accept": "application/json"})
            cats = r_cats.json()
            if not isinstance(cats, list):
                cats = cats.get("data") or cats.get("categories") or []
            for c in cats:
                name = (c.get("name") or "").lower()
                if re.search(r"film|movie", name) and not self.cat_film:
                    self.cat_film = c["id"]
                if re.search(r"serie|tv|show", name) and not self.cat_series:
                    self.cat_series = c["id"]
                if re.search(r"\bvo\b|version.?origin", name) and not self.cat_vo:
                    self.cat_vo = c["id"]
        except Exception as e:
            pass
        if not self.cat_film:   self.cat_film   = "cmjoyv2cd00027eryreyk39gz"
        if not self.cat_series: self.cat_series = self.cat_film   # fallback
        if not self.cat_vo:     self.cat_vo     = self.cat_film   # fallback : VO → Films si catégorie absente
        self.log(f"  Catégorie Films   : {self.cat_film}", "muted")
        self.log(f"  Catégorie Séries  : {self.cat_series}", "muted")
        self.log(f"  Catégorie VO      : {self.cat_vo}", "muted")

        # Quais depuis la catégorie films
        try:
            r_terms = self._get(f"/api/internal/categories/{self.cat_film}/terms",
                               headers={"Accept": "application/json"})
            groups = r_terms.json()
            if not isinstance(groups, list):
                groups = groups.get("data") or groups.get("termGroups") or []
            for g in groups:
                if "quai" in (g.get("name") or g.get("slug") or "").lower():
                    for t in g.get("terms", []):
                        n = (t.get("name") or "").lower()
                        if re.search(r"web.?dl|webdl", n):              self.quais["WEB-DL"] = t["id"]
                        elif "webrip" in n:                               self.quais["WEBRip"] = t["id"]
                        elif re.search(r"blu.?ray", n) and "remux" not in n:
                                                                          self.quais["BluRay"] = t["id"]
                        elif "remux" in n:                                self.quais["REMUX"]  = t["id"]
                        elif "dvd"   in n:                                self.quais["DVDRip"] = t["id"]
                        elif "hdtv"  in n:                                self.quais["HDTV"]   = t["id"]
        except Exception as e:
            pass

    def count(self, title, is_series=False):
        try:
            cat = "series" if is_series else "films"
            enc = requests.utils.quote(title)
            data = self._get(f"/api/internal/torrents/filter?search={enc}&category={cat}",
                             headers={"Accept": "application/json"}).json()
            return len(data) if isinstance(data, list) else len(data.get("data") or [])
        except Exception:
            return 0

    def build_terms(self, p, is_series=False):
        terms = set()
        qk = self.SRC_QUAI.get(p.get("src", "WEB"), "WEB-DL")
        if qk in self.quais: terms.add(self.quais[qk])
        lang = p.get("lang", "FRENCH")
        for lt in [lang, lang.split(".")[0]]:
            if lt in self.LANG_TERMS:
                terms.update(self.LANG_TERMS[lt]); break
        if p.get("ext") in self.EXT_TERMS:
            terms.add(self.EXT_TERMS[p["ext"]])
        return terms

    def login_api(self, passkey):
        """Mode API externe — vérifie le passkey via /api/user puis /api/external."""
        self.log("Connexion La Cale (mode API)...", "gold")
        passkey = passkey.strip()
        self._passkey = passkey
        if not passkey:
            self.log("  Erreur : passkey vide — renseignez-le dans les paramètres.", "err")
            return False
        # Endpoints à tester dans l'ordre
        for endpoint in [
            f"{self.url}/api/user",
            f"{self.url}/api/external",
            f"{self.url}/api/external/meta",
        ]:
            try:
                r = self.sess.get(endpoint, params={"apikey": passkey}, timeout=10)
                if r.status_code == 200:
                    self.log("  API OK — passkey valide.", "ok")
                    return True
            except Exception:
                continue
        self.log(f"  Erreur API (HTTP 401) — vérifiez le passkey.", "err")
        return False

    def prepare_api(self):
        """Récupère catégories via API externe."""
        try:
            r = self.sess.get(f"{self.url}/api/external/meta",
                              params={"apikey": self._passkey}, timeout=10)
            meta = r.json()
            cats = meta.get("categories") or []
            for c in cats:
                name = (c.get("name") or "").lower()
                if re.search(r"film|movie", name) and not self.cat_film:
                    self.cat_film = c.get("id") or c.get("slug")
                if re.search(r"serie|tv|show", name) and not self.cat_series:
                    self.cat_series = c.get("id") or c.get("slug")
                if re.search(r"\bvo\b|version.?origin", name) and not self.cat_vo:
                    self.cat_vo = c.get("id") or c.get("slug")
        except Exception:
            pass
        if not self.cat_film:   self.cat_film   = "cmjoyv2cd00027eryreyk39gz"
        if not self.cat_series: self.cat_series = self.cat_film
        if not self.cat_vo:     self.cat_vo     = self.cat_film   # fallback : VO → Films si catégorie absente
        self.log(f"  Catégorie Films   : {self.cat_film}", "muted")
        self.log(f"  Catégorie Séries  : {self.cat_series}", "muted")
        self.log(f"  Catégorie VO      : {self.cat_vo}", "muted")

    def upload_api(self, passkey, name, tb, nfo, desc,
                   tmdb_id=None, is_series=False, terms=None, lang="FRENCH"):
        """Upload via API externe /api/external/upload avec bascule automatique en catégorie VO."""
        french_variants = {"FRENCH", "MULTi", "MULTi.VFF", "MULTi.VFQ", "TRUEFRENCH"}
        if lang in french_variants:
            cat = self.cat_series if is_series else self.cat_film
        else:
            cat = self.cat_vo
            self.log(f"  La Cale : langue '{lang}' → catégorie VO ({cat})", "muted")
        files = {"file": (f"{name}.torrent", tb, "application/x-bittorrent")}
        if nfo: files["nfoFile"] = (f"{name}.nfo", nfo.encode("utf-8"), "text/plain")
        data  = {"title": name, "categoryId": cat}
        if tmdb_id:
            data["tmdbId"]   = str(tmdb_id)
            data["tmdbType"] = "TV" if is_series else "MOVIE"
        if desc: data["description"] = desc
        if nfo:  data["nfoText"]     = nfo
        tag_params = [("tags", tid) for tid in (terms or [])]
        r = self.sess.post(
            f"{self.url}/api/external/upload",
            params=[("apikey", passkey)] + tag_params,
            data=data, files=files,
            headers={"Accept": "application/json"},
            timeout=120)
        try:   body = r.json()
        except Exception: body = {}
        ok = bool(body.get("success") or body.get("id") or
                  body.get("slug") or (r.status_code == 200 and body))
        return ok, body

    def upload(self, name, tb, nfo, desc, tmdb_id=None, is_series=False, terms=None, lang="FRENCH"):
        """
        Envoie le torrent vers La Cale (mode Web — simulation navigateur)
        avec bascule automatique en catégorie VO.
        """
        french_variants = {"FRENCH", "MULTi", "MULTi.VFF", "MULTi.VFQ", "TRUEFRENCH"}
        if lang in french_variants:
            cat = self.cat_series if is_series else self.cat_film
        else:
            cat = self.cat_vo
            self.log(f"  La Cale : langue '{lang}' → catégorie VO ({cat})", "muted")
        files = {"file": (f"{name}.torrent", tb, "application/x-bittorrent")}
        if nfo: files["nfoFile"] = (f"{name}.nfo", nfo.encode("utf-8"), "text/plain")
        data  = {"title": name, "categoryId": cat, "isAnonymous": "false",
                 "nfoText": nfo or "", "description": desc or ""}
        if tmdb_id:
            data["tmdbId"]   = str(tmdb_id)
            data["tmdbType"] = "TV" if is_series else "MOVIE"
        r = self.sess.post(self.url + "/api/internal/torrents/upload",
                           data=data, files=files,
                           params=[(("termIds[]"), t) for t in (terms or [])],
                           headers={"Accept": "application/json",
                                    "Referer": self.url + "/upload",
                                    "Origin": self.url},
                           timeout=120)
        try:   body = r.json()
        except Exception: body = {}
        ok = bool(body.get("success") or body.get("torrentId") or
                  body.get("slug") or (r.status_code == 200 and body))
        return ok, body


# ══════════════════════════════════════════════════════════════════════════════
# TORR9 CLIENT  (Web only — JWT Bearer token via localStorage)
# ══════════════════════════════════════════════════════════════════════════════
class Torr9:
    """
    Client d'upload pour Torr9.
    Authentification : login form → JWT token via /api/v1/auth/login
                    OU token stocké directement dans la config.
    Upload : POST multipart vers https://api.torr9.net/api/v1/torrents/upload
             avec Authorization: Bearer <token>.
    """

    API_BASE    = "https://api.torr9.net"
    CAT_FILMS   = 1
    CAT_SERIES  = 4
    SUBCAT_FILM = 51
    SUBCAT_TV   = 5

    def __init__(self, url, log):
        self.url   = url.rstrip("/")
        self.log   = log
        self.sess  = requests.Session()
        self.sess.headers.update({
            "User-Agent":
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Origin":  "https://torr9.net",
            "Referer": "https://torr9.net/",
        })
        self._token = ""

    # ── Auth ─────────────────────────────────────────────────────────────────
    def set_token(self, token: str) -> bool:
        """Utilise un token JWT déjà connu (stocké dans la config)."""
        token = token.strip()
        if not token:
            return False
        self._token = token
        self.log("  Torr9 : token API chargé depuis la config.", "ok")
        return True

    def login(self, username: str, password: str) -> bool:
        """Obtient un JWT Bearer depuis /api/v1/auth/login."""
        self.log("Connexion à Torr9...", "gold")
        try:
            r = requests.post(
                f"{self.API_BASE}/api/v1/auth/login",
                json={"username": username, "password": password},
                headers={
                    "Content-Type": "application/json",
                    "Accept":       "application/json",
                    "Origin":       "https://torr9.net",
                    "Referer":      "https://torr9.net/login",
                },
                timeout=20)
            body = {}
            try:
                body = r.json()
            except Exception:
                pass
            token = body.get("token") or body.get("access_token") or ""
            if r.status_code == 200 and token:
                self._token = token
                self.log("  Connexion Torr9 OK.", "ok")
                return True
            err = body.get("error") or body.get("message") or f"HTTP {r.status_code}"
            self.log(f"  Erreur login Torr9 : {err}", "err")
            return False
        except Exception as e:
            self.log(f"  Erreur connexion Torr9 : {e}", "err")
            return False

    def _auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept":        "application/json",
            "Origin":        "https://torr9.net",
            "Referer":       "https://torr9.net/upload",
        }

    # ── Health check ─────────────────────────────────────────────────────────
    def health_check(self):
        """Vérifie que Torr9 répond (HEAD direct)."""
        self.log("  Passe — Connexion directe à Torr9...", "muted")
        try:
            r = requests.head(self.url, timeout=10,
                              headers={"User-Agent": self.sess.headers["User-Agent"]})
            if r.status_code in (200, 301, 302, 307, 308):
                self.log(f"  ✓ Torr9 répond (HTTP {r.status_code}).", "ok")
                return True, "OK"
            self.log(f"  ✗ Torr9 : HTTP {r.status_code}.", "err")
            return False, f"Torr9 répond HTTP {r.status_code}."
        except requests.exceptions.ConnectionError:
            self.log("  ✗ Torr9 inaccessible (erreur réseau).", "err")
            return False, "Impossible de joindre Torr9."
        except requests.exceptions.Timeout:
            self.log("  ✗ Torr9 timeout.", "err")
            return False, "Torr9 ne répond pas (timeout)."
        except Exception as e:
            self.log(f"  ✗ Torr9 : {e}", "err")
            return False, str(e)

    # ── Duplicate check ──────────────────────────────────────────────────────
    def check_duplicate(self, title: str) -> bool:
        """Retourne True si un doublon existe déjà sur Torr9."""
        try:
            r = requests.post(
                f"{self.API_BASE}/api/v1/torrents/check-duplicate",
                json={"title": title},
                headers=self._auth_headers() | {"Content-Type": "application/json"},
                timeout=10)
            if r.status_code == 200:
                body = r.json()
                return bool(body.get("has_duplicates"))
        except Exception:
            pass
        return False

    # ── Upload ───────────────────────────────────────────────────────────────
    def upload(self, name: str, tb: bytes, desc: str,
               is_series: bool = False, tmdb_id=None, nfo: str = "",
               lang: str = "FRENCH", genres: str = "") -> tuple:
        """
        Envoie le torrent vers Torr9 via /api/v1/torrents/upload.

        Catégories confirmées par test API réel :
          Films   → subcategory : "Films" | "Documentaires"
          Séries  → subcategory : "Séries TV" | "Séries Animées"
          VO      → subcategory : "Films" | "Séries"

        Sélection automatique de la subcatégorie via les genres TMDb :
          - "Animation" dans genres → Séries Animées
          - "Documentaire" dans genres → Documentaires
          - sinon → Films / Séries TV

        Champs FormData confirmés (test réel mai 2025) :
          torrent_file, title, description, nfo (texte), category,
          subcategory, tags, is_exclusive, is_anonymous, tmdb_id
        """
        genres_lower = genres.lower()
        french_variants = {"FRENCH", "MULTi", "MULTi.VFF", "MULTi.VFQ", "TRUEFRENCH"}

        if lang in french_variants:
            if is_series:
                cat_name    = "Séries"
                subcat_name = "Séries Animées" if "animation" in genres_lower else "Séries TV"
            else:
                cat_name    = "Films"
                subcat_name = "Documentaires" if "documentaire" in genres_lower else "Films"
        else:
            # VO : Films ou Séries selon le type
            cat_name    = "VO"
            subcat_name = "Séries" if is_series else "Films"

        self.log(f"  Torr9 catégorie : {cat_name} / {subcat_name}", "muted")

        data = {
            "title":        name,
            "description":  desc or "",
            "category":     cat_name,
            "subcategory":  subcat_name,
            "tags":         "",
            "is_exclusive": "false",
            "is_anonymous": "false",
        }
        if tmdb_id:
            data["tmdb_id"] = str(tmdb_id)
        if nfo:
            data["nfo"] = nfo   # texte brut MediaInfo, PAS un fichier multipart

        files = {"torrent_file": (f"{name}.torrent", tb, "application/x-bittorrent")}

        try:
            r = requests.post(f"{self.API_BASE}/api/v1/torrents/upload",
                data=data, files=files, headers=self._auth_headers(), timeout=600)
            body = {}
            try: body = r.json()
            except: pass

            if r.status_code == 201:
                # Succès confirmé : torrent reçu, en attente de validation modérateur
                ok = bool(body.get("torrent_id"))
                return ok, body
            elif r.status_code == 409:
                # Doublon détecté par le serveur
                return False, body
            elif r.status_code in (200,):
                # Succès alternatif
                ok = bool(body.get("torrent_id") or body.get("id") or body.get("success"))
                return ok, body
            else:
                return False, body
        except Exception as e:
            return False, {"error": str(e)}


class TMDb:
    BASE = "https://api.themoviedb.org/3"

    def __init__(self, token, lang, log):
        self.lang = lang; self.log = log
        self.sess = requests.Session()
        if token: self.sess.headers["Authorization"] = f"Bearer {token}"

    def _get(self, p, **kw):
        kw.setdefault("language", self.lang)
        return self.sess.get(self.BASE + p, params=kw, timeout=15)

    def search_movie(self, title, year=None):
        try:
            p = {"query": title}
            if year: p["primary_release_year"] = year
            r = self._get("/search/movie", **p).json().get("results", [])
            if not r and year:
                r = self._get("/search/movie", query=title).json().get("results", [])
            return r[0] if r else None
        except Exception: return None

    def movie_details(self, tid):
        try: return self._get(f"/movie/{tid}", append_to_response="credits,external_ids").json()
        except Exception: return None

    def search_tv(self, title, year=None):
        try:
            p = {"query": title}
            if year: p["first_air_date_year"] = year
            r = self._get("/search/tv", **p).json().get("results", [])
            if not r and year:
                r = self._get("/search/tv", query=title).json().get("results", [])
            return r[0] if r else None
        except Exception: return None

    def tv_details(self, tid, season_num=None):
        try:
            det = self._get(f"/tv/{tid}", append_to_response="credits").json()
            if season_num:
                try:
                    s = self._get(f"/tv/{tid}/season/{season_num}").json()
                    det["season_detail"] = s
                except Exception: pass
            return det
        except Exception: return None


# ══════════════════════════════════════════════════════════════════════════════
# qBITTORRENT CLIENT
# ══════════════════════════════════════════════════════════════════════════════
class QBit:
    def __init__(self, url, user, pwd, log):
        self.url  = url.rstrip("/"); self.log = log
        self.sess = requests.Session(); self.ok = False
        try:
            r = self.sess.post(f"{self.url}/api/v2/auth/login",
                               data={"username": user, "password": pwd}, timeout=10)
            self.ok = r.status_code == 200 and "ok" in r.text.lower()
            self.log(f"  qBittorrent : {'connecté.' if self.ok else 'connexion échouée.'}",
                     "ok" if self.ok else "muted")
        except Exception as e:
            self.log(f"  qBittorrent : {e}", "muted")

    def is_seeding(self, file_path: str) -> bool:
        """
        Vérifie si un fichier peut être uploadé.

        Cycle Prowlarr/QB :
          1. Téléchargement → QB seed dans Torrents/complete/
          2. Après période de seed → Prowlarr déplace vers Films/ et supprime de QB

        Logique :
          - Fichier trouvé dans QB avec état missingFiles/error → BLOQUÉ (fichier cassé)
          - Fichier trouvé dans QB avec tout autre état → OK (en cours de seed)
          - Fichier absent de QB → OK (a déjà seedé, déplacé par Prowlarr)
        """
        if not self.ok:
            return True   # QB non connecté → on ne peut pas vérifier, on laisse passer
        try:
            r = self.sess.get(f"{self.url}/api/v2/torrents/info",
                              params={"filter": "all"}, timeout=10)
            if r.status_code != 200:
                return True   # QB ne répond pas → on laisse passer

            torrents = r.json()
            fname = Path(file_path).name.lower()
            fstem = Path(file_path).stem.lower()
            BAD_STATES = {"missingFiles", "error"}

            # ── Passe 1 : métadonnées ─────────────────────────────────────────
            for torrent in torrents:
                t_name    = (torrent.get("name")         or "").lower()
                t_content = (torrent.get("content_path") or "").lower()
                t_save    = (torrent.get("save_path")    or "").lower()
                constructed = t_save.rstrip("/") + "/" + t_name

                if (fname in t_content or fname in constructed
                        or fname == t_name or fstem == t_name):
                    state = torrent.get("state", "")
                    if state in BAD_STATES:
                        self.log(f"  [seed check] '{fname}' en erreur QB : {state}", "err")
                        return False
                    return True   # trouvé et état OK

            # ── Passe 2 : liste de fichiers par torrent ───────────────────────
            for torrent in torrents:
                t_hash = torrent.get("hash", "")
                if not t_hash:
                    continue
                try:
                    rf = self.sess.get(f"{self.url}/api/v2/torrents/files",
                                       params={"hash": t_hash}, timeout=5)
                    if rf.status_code != 200:
                        continue
                    for f in rf.json():
                        f_name = Path(f.get("name", "")).name.lower()
                        if f_name == fname or Path(f_name).stem == fstem:
                            state = torrent.get("state", "")
                            if state in BAD_STATES:
                                self.log(f"  [seed check] '{fname}' en erreur QB : {state}", "err")
                                return False
                            return True
                except Exception:
                    continue

            # Absent de QB → a déjà seedé et été déplacé par Prowlarr → OK
            return True
        except Exception as e:
            self.log(f"  [seed check] erreur API : {e}", "muted")
            return True

    def get_default_save_path(self) -> str:
        """Récupère le chemin de sauvegarde par défaut configuré dans qBittorrent."""
        try:
            r = self.sess.get(f"{self.url}/api/v2/app/preferences", timeout=10)
            if r.status_code == 200:
                path = r.json().get("save_path", "")
                if path:
                    return path.rstrip("/")
        except Exception:
            pass
        return ""

    def get_torrent_state(self, release_name: str) -> str:
        """
        Retourne l'état d'un torrent dans QB par son nom de release.
        Retourne '' si non trouvé.
        """
        try:
            r = self.sess.get(f"{self.url}/api/v2/torrents/info",
                              params={"filter": "all"}, timeout=10)
            if r.status_code != 200:
                return ""
            name_lower = release_name.lower()
            for torrent in r.json():
                t_name = (torrent.get("name") or "").lower()
                if name_lower in t_name or t_name in name_lower:
                    state = torrent.get("state", "")
                    cp    = torrent.get("content_path", "")
                    return state
        except Exception:
            pass
        return ""

    def get_torrent_state_by_hash(self, info_hash: str) -> tuple:
        """
        Retourne (state, content_path) d'un torrent par son info-hash SHA1.
        Plus fiable que la recherche par nom.
        """
        try:
            r = self.sess.get(f"{self.url}/api/v2/torrents/info",
                              params={"filter": "all", "hashes": info_hash}, timeout=10)
            if r.status_code != 200:
                return "", ""
            torrents = r.json()
            if torrents:
                t = torrents[0]
                state = t.get("state", "")
                cp    = t.get("content_path", "")
                if state == "missingFiles":
                    self.log(f"  QB cherche : {cp}", "err")
                return state, cp
        except Exception:
            pass
        return "", ""

    def is_seeding_by_name(self, release_name: str) -> bool:
        """
        Vérifie si un torrent est en seed dans QB par son release name.
        Retourne True si trouvé avec un état valide (pas missingFiles/error).
        """
        GOOD_STATES = {"uploading", "stalledUP", "forcedUP", "queuedUP",
                       "checkingUP", "stoppedUP", "pausedUP", "moving"}
        try:
            r = self.sess.get(f"{self.url}/api/v2/torrents/info",
                              params={"filter": "all"}, timeout=10)
            if r.status_code != 200:
                return False
            name_low = release_name.lower()
            for t in r.json():
                t_name = (t.get("name") or "").lower()
                if name_low in t_name or t_name in name_low:
                    return t.get("state", "") in GOOD_STATES
        except Exception:
            pass
        return False

    def find_error_torrent_by_name(self, name: str) -> str:
        """
        Cherche un torrent en erreur (missingFiles/error) par nom approximatif.
        Retourne l'info-hash si trouvé en erreur, sinon ''.
        """
        try:
            r = self.sess.get(f"{self.url}/api/v2/torrents/info",
                              params={"filter": "all"}, timeout=10)
            if r.status_code != 200:
                return ""
            name_low = name.lower()
            for t in r.json():
                if t.get("state", "") in ("missingFiles", "error"):
                    t_name = (t.get("name") or "").lower()
                    if name_low in t_name or t_name in name_low:
                        return t.get("hash", "")
        except Exception:
            pass
        return ""

    def delete_torrent(self, info_hash: str, delete_files: bool = False) -> bool:
        """Supprime un torrent de QB (sans supprimer les fichiers par défaut)."""
        try:
            r = self.sess.post(f"{self.url}/api/v2/torrents/delete",
                               data={"hashes": info_hash,
                                     "deleteFiles": "true" if delete_files else "false"},
                               timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def add(self, tb, save_path, torrent_name):
        """
        Ajoute un torrent dans qBittorrent.
        save_path doit pointer vers le dossier contenant le fichier existant.
        """
        try:
            r = self.sess.post(f"{self.url}/api/v2/torrents/add",
                               files={"torrents": (torrent_name + ".torrent", tb,
                                                   "application/x-bittorrent")},
                               data={"savepath":      save_path,
                                     "skip_checking": "true",
                                     "paused":        "false"},
                               timeout=30)
            ok = r.status_code == 200 and "ok" in r.text.lower()
            if not ok:
                if "fails" in r.text.lower():
                    # Torrent déjà présent dans QB (même hash) → on continue
                    self.log("  QB add → torrent déjà présent dans QB.", "muted")
                    return True
                self.log(f"  QB add → HTTP {r.status_code} : {r.text[:200]}", "err")
            return ok
        except Exception as e:
            self.log(f"  QB add → exception : {e}", "err")
            return False

    def set_location(self, info_hash: str, location: str) -> bool:
        """
        Force le chemin de sauvegarde d'un torrent via setLocation.
        Contourne la normalisation Unicode faite par QB lors de l'ajout.
        """
        try:
            r = self.sess.post(f"{self.url}/api/v2/torrents/setLocation",
                               data={"hashes": info_hash, "location": location},
                               timeout=10)
            return r.status_code == 200
        except Exception:
            return False


class Transmission:
    def __init__(self, url, user, pwd, log):
        self.url  = url.rstrip("/"); self.log = log
        self.ok   = False
        self._auth = (user, pwd) if user else None
        try:
            r = requests.post(
                f"{self.url}/transmission/rpc",
                headers={"X-Transmission-Session-Id": ""},
                auth=self._auth, timeout=10)
            # Transmission renvoie 409 avec le header session-id
            sid = r.headers.get("X-Transmission-Session-Id", "")
            if sid:
                self._sid = sid
                self.ok = True
                self.log("  Transmission : connecté.", "ok")
            else:
                self.log("  Transmission : connexion échouée.", "muted")
        except Exception as e:
            self.log(f"  Transmission : {e}", "muted")
            self._sid = ""

    def add(self, tb, save_path, torrent_name):
        try:
            import base64 as _b64
            torrent_b64 = _b64.b64encode(tb).decode()
            payload = {
                "method": "torrent-add",
                "arguments": {
                    "metainfo": torrent_b64,
                    "download-dir": save_path,
                    "paused": False
                }
            }
            # Tentative d'envoi
            r = requests.post(
                f"{self.url}/transmission/rpc",
                json=payload,
                headers={"X-Transmission-Session-Id": self._sid},
                auth=self._auth, timeout=30)

            # Gestion de l'expiration de session (Code 409)
            if r.status_code == 409:
                self._sid = r.headers.get("X-Transmission-Session-Id", "")
                r = requests.post(
                    f"{self.url}/transmission/rpc",
                    json=payload,
                    headers={"X-Transmission-Session-Id": self._sid},
                    auth=self._auth, timeout=30)

            data = r.json()
            result = data.get("result", "")
            if result != "success":
                self.log(f"  Transmission add → résultat : {result}", "err")
            return result == "success"
        except Exception as e:
            self.log(f"  Transmission add → exception : {e}", "err")
            return False

    def is_seeding(self, file_path: str) -> bool:
        """Vérifie si le fichier est en seed dans Transmission."""
        if not self.ok:
            return True
        try:
            fname = Path(file_path).name.lower()
            fstem = Path(file_path).stem.lower()
            payload = {"method": "torrent-get",
                       "arguments": {"fields": ["name", "status", "errorString", "percentDone"]}}
            r = requests.post(
                f"{self.url}/transmission/rpc",
                json=payload,
                headers={"X-Transmission-Session-Id": self._sid},
                auth=self._auth, timeout=10)
            torrents = r.json().get("arguments", {}).get("torrents", [])
            for t in torrents:
                t_name = (t.get("name") or "").lower()
                if fname in t_name or fstem == t_name:
                    # Si le fichier est à 100%, on ignore l'erreur
                    if t.get("percentDone") == 1:
                        return True
                    if t.get("status") == 16 or t.get("errorString"):
                        self.log(f"  [seed check Transmission] '{fname}' en erreur.", "err")
                        return False
                    return True
            return True
        except Exception as e:
            self.log(f"  [seed check Transmission] erreur : {e}", "muted")
            return True

    def get_torrent_state_by_hash(self, info_hash: str) -> tuple:
        """Retourne l'état en ignorant les erreurs de tracker si le fichier est complété."""
        if not self.ok:
            return "", ""
        try:
            payload = {"method": "torrent-get",
                       "arguments": {"ids": [info_hash],
                                     "fields": ["name", "status", "errorString",
                                                "downloadDir", "percentDone"]}}
            r = requests.post(
                f"{self.url}/transmission/rpc",
                json=payload,
                headers={"X-Transmission-Session-Id": self._sid},
                auth=self._auth, timeout=10)
            torrents = r.json().get("arguments", {}).get("torrents", [])
            if not torrents:
                return "", ""
            t = torrents[0]
            status       = t.get("status", -1)
            error_str    = t.get("errorString", "")
            download_dir = t.get("downloadDir", "")
            name         = t.get("name", "")
            percent      = t.get("percentDone", 0)

            # Force le seed si 100% (ignore l'erreur "Torrent not found" du tracker)
            if percent == 1:
                return "uploading", download_dir

            if error_str or status == 16:
                self.log(f"  Transmission cherche : {download_dir}/{name}", "err")
                return "error", download_dir
            STATUS_MAP = {0: "stoppedUP", 1: "checkingUP", 2: "checkingUP",
                          3: "queuedUP",  4: "downloading", 5: "queuedUP", 6: "uploading"}
            return STATUS_MAP.get(status, f"unknown_{status}"), download_dir
        except Exception:
            return "", ""

    def is_seeding_by_name(self, release_name: str) -> bool:
        """Vérifie si un torrent est en seed dans Transmission par son release name."""
        GOOD = {"uploading", "stalledUP", "forcedUP", "queuedUP",
                "checkingUP", "stoppedUP", "pausedUP", "moving"}
        if not self.ok:
            return False
        try:
            payload = {"method": "torrent-get",
                       "arguments": {"fields": ["name", "status", "errorString"]}}
            r = requests.post(
                f"{self.url}/transmission/rpc",
                json=payload,
                headers={"X-Transmission-Session-Id": self._sid},
                auth=self._auth, timeout=10)
            name_low = release_name.lower()
            for t in r.json().get("arguments", {}).get("torrents", []):
                t_name = (t.get("name") or "").lower()
                if name_low in t_name or t_name in name_low:
                    STATUS_MAP = {0: "stoppedUP", 1: "checkingUP", 2: "checkingUP",
                                  3: "queuedUP",  4: "downloading", 5: "queuedUP",
                                  6: "uploading"}
                    return STATUS_MAP.get(t.get("status", -1), "") in GOOD
        except Exception:
            pass
        return False


# ══════════════════════════════════════════════════════════════════════════════
# DELUGE CLIENT (JSON-RPC 2.x — endpoint /json, port 8112)
# ══════════════════════════════════════════════════════════════════════════════
class Deluge:
    """
    Client Deluge 2.x via l'API JSON-RPC interne.
    Authentification : auth.login(password) → True/False.
    Upload          : core.add_torrent_file(filename, base64, options).
    Seed check      : core.get_torrents_status() → parcourt les noms.
    """

    def __init__(self, url, password, log):
        self.url  = url.rstrip("/")
        self.log  = log
        self.ok   = False
        self._id  = 0
        self.sess = requests.Session()
        self.sess.headers.update({"Content-Type": "application/json",
                                   "Accept": "application/json"})
        try:
            r = self._rpc("auth.login", [password])
            self.ok = bool(r and r.get("result") is True)
            self.log(
                "  Deluge : connecté." if self.ok
                else "  Deluge : connexion échouée (mauvais mot de passe ?).",
                "ok" if self.ok else "muted")
        except Exception as e:
            self.log(f"  Deluge : {e}", "muted")

    def _rpc(self, method, params=None):
        """Appel JSON-RPC → dict réponse ou None."""
        self._id += 1
        try:
            r = self.sess.post(
                f"{self.url}/json",
                json={"method": method, "params": params or [], "id": self._id},
                timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def add(self, tb, save_path, torrent_name):
        """Ajoute un torrent dans Deluge et ignore l'erreur si déjà présent."""
        if not self.ok:
            return False
        try:
            import base64 as _b64
            tb64 = _b64.b64encode(tb).decode()
            opts = {
                "download_location": save_path,
                "add_paused": False,
                "seed_mode":  True,
            }
            r = self._rpc("core.add_torrent_file",
                          [torrent_name + ".torrent", tb64, opts])
            
            ok = bool(r and r.get("result"))
            if not ok:
                err = (r or {}).get("error")
                # Si le torrent est déjà dans Deluge, on considère cela comme un succès
                if err and "already in session" in str(err).lower():
                    self.log("  Deluge : torrent déjà présent, on continue.", "muted")
                    return True
                if err:
                    self.log(f"  Deluge add → erreur : {err}", "err")
            return ok
        except Exception as e:
            self.log(f"  Deluge add → exception : {e}", "err")
            return False

    def is_seeding(self, file_path: str) -> bool:
        """
        Vérifie si le fichier est présent dans Deluge.
        Même logique que QBit.is_seeding : absent = déjà seedé = OK.
        """
        if not self.ok:
            return True
        try:
            fname = Path(file_path).name.lower()
            fstem = Path(file_path).stem.lower()
            r = self._rpc("core.get_torrents_status",
                          [{}, ["name", "state"]])
            torrents = (r or {}).get("result") or {}
            for info_hash, t in torrents.items():
                t_name = (t.get("name") or "").lower()
                if fname in t_name or fstem == t_name:
                    state = t.get("state", "")
                    if state == "Error":
                        self.log(f"  [seed check] '{fname}' en erreur Deluge.", "err")
                        return False
                    return True
            return True   # absent → a déjà seedé
        except Exception as e:
            self.log(f"  [seed check Deluge] erreur : {e}", "muted")
            return True

    def get_torrent_state_by_hash(self, info_hash: str) -> tuple:
        """
        Retourne (state, save_path) d'un torrent Deluge par son info-hash.
        Équivalent de QBit.get_torrent_state_by_hash pour le seed check post-add.
        """
        if not self.ok:
            return "", ""
        try:
            r = self._rpc("core.get_torrent_status",
                          [info_hash, ["state", "save_path", "name"]])
            result = (r or {}).get("result") or {}
            if not result:
                return "", ""
            state     = result.get("state", "")
            save_path = result.get("save_path", "")
            if state == "Error":
                name = result.get("name", info_hash[:8])
                self.log(f"  Deluge cherche : {save_path}/{name}", "err")
            return state, save_path
        except Exception:
            return "", ""

    def is_seeding_by_name(self, release_name: str) -> bool:
        """Vérifie si un torrent est en seed dans Deluge par son release name."""
        GOOD = {"Seeding", "Checking", "Queued"}
        if not self.ok:
            return False
        try:
            r = self._rpc("core.get_torrents_status", [{}, ["name", "state"]])
            torrents = (r or {}).get("result") or {}
            name_low = release_name.lower()
            for info_hash, t in torrents.items():
                t_name = (t.get("name") or "").lower()
                if name_low in t_name or t_name in name_low:
                    return t.get("state", "") in GOOD
        except Exception:
            pass
        return False


# ══════════════════════════════════════════════════════════════════════════════
# VUZE CLIENT (protocole Transmission-compatible, plugin Vuze Web Remote)
# ══════════════════════════════════════════════════════════════════════════════
class Vuze:
    """
    Client Vuze (Azureus) via le plugin Vuze Web Remote.
    Vuze implemente le meme protocole RPC que Transmission (endpoint /transmission/rpc,
    port 9091 par defaut). Authentification : username "vuze" + code de pairing.

    Prerequis : installer le plugin "Vuze Web Remote" depuis
    Outils -> Plugins -> Installation depuis le depot -> "Vuze Web Remote".
    Le code de pairing s'affiche dans l'interface du plugin.
    """

    def __init__(self, url, user, pwd, log):
        self.url   = url.rstrip("/")
        self.log   = log
        self.ok    = False
        self._auth = (user, pwd) if user else None
        self._sid  = ""
        try:
            # Meme handshake que Transmission : POST -> 409 -> recuperer session-id
            r = requests.post(
                f"{self.url}/transmission/rpc",
                headers={"X-Transmission-Session-Id": ""},
                auth=self._auth, timeout=10)
            sid = r.headers.get("X-Transmission-Session-Id", "")
            if sid:
                self._sid = sid
                self.ok   = True
                self.log("  Vuze : connecte.", "ok")
            else:
                self.log(
                    "  Vuze : connexion echouee "
                    "(verifiez que le plugin Vuze Web Remote est actif).", "muted")
        except Exception as e:
            self.log(f"  Vuze : {e}", "muted")

    def add(self, tb, save_path, torrent_name):
        """Ajoute un torrent (bytes) dans Vuze via RPC Transmission-compatible."""
        if not self.ok:
            return False
        try:
            import base64 as _b64
            torrent_b64 = _b64.b64encode(tb).decode()
            payload = {
                "method": "torrent-add",
                "arguments": {
                    "metainfo":     torrent_b64,
                    "download-dir": save_path,
                    "paused":       False,
                }
            }
            r = requests.post(
                f"{self.url}/transmission/rpc",
                json=payload,
                headers={"X-Transmission-Session-Id": self._sid},
                auth=self._auth, timeout=30)
            data   = r.json()
            result = data.get("result", "")
            ok     = (result == "success")
            if not ok:
                self.log(f"  Vuze add -> resultat : {result}", "err")
            return ok
        except Exception as e:
            self.log(f"  Vuze add -> exception : {e}", "err")
            return False

    def is_seeding(self, file_path: str) -> bool:
        """Verifie si le fichier est en seed dans Vuze via torrent-get."""
        if not self.ok:
            return True
        try:
            fname = Path(file_path).name.lower()
            fstem = Path(file_path).stem.lower()
            payload = {
                "method": "torrent-get",
                "arguments": {"fields": ["name", "status", "errorString"]}
            }
            r = requests.post(
                f"{self.url}/transmission/rpc",
                json=payload,
                headers={"X-Transmission-Session-Id": self._sid},
                auth=self._auth, timeout=10)
            torrents = r.json().get("arguments", {}).get("torrents", [])
            for t in torrents:
                t_name = (t.get("name") or "").lower()
                if fname in t_name or fstem == t_name:
                    if t.get("status") == 16 or t.get("errorString"):
                        self.log(f"  [seed check Vuze] '{fname}' en erreur.", "err")
                        return False
                    return True
            return True
        except Exception as e:
            self.log(f"  [seed check Vuze] erreur : {e}", "muted")
            return True

    def get_torrent_state_by_hash(self, info_hash: str) -> tuple:
        """
        Retourne (state_str, download_dir) d'un torrent Vuze par son info-hash.
        Vuze utilise le meme protocole RPC que Transmission.
        """
        if not self.ok:
            return "", ""
        try:
            payload = {"method": "torrent-get",
                       "arguments": {"ids": [info_hash],
                                     "fields": ["name", "status",
                                                "errorString", "downloadDir"]}}
            r = requests.post(
                f"{self.url}/transmission/rpc",
                json=payload,
                headers={"X-Transmission-Session-Id": self._sid},
                auth=self._auth, timeout=10)
            torrents = r.json().get("arguments", {}).get("torrents", [])
            if not torrents:
                return "", ""
            t = torrents[0]
            status       = t.get("status", -1)
            error_str    = t.get("errorString", "")
            download_dir = t.get("downloadDir", "")
            name         = t.get("name", "")
            if error_str or status == 16:
                self.log(f"  Vuze cherche : {download_dir}/{name}", "err")
                return "error", download_dir
            STATUS_MAP = {0: "stoppedUP", 1: "checkingUP", 2: "checkingUP",
                          3: "queuedUP",  4: "downloading", 5: "queuedUP", 6: "uploading"}
            return STATUS_MAP.get(status, f"unknown_{status}"), download_dir
        except Exception:
            return "", ""

    def is_seeding_by_name(self, release_name: str) -> bool:
        """Vérifie si un torrent est en seed dans Vuze par son release name."""
        GOOD = {"uploading", "stalledUP", "forcedUP", "queuedUP",
                "checkingUP", "stoppedUP", "pausedUP", "moving"}
        if not self.ok:
            return False
        try:
            payload = {"method": "torrent-get",
                       "arguments": {"fields": ["name", "status", "errorString"]}}
            r = requests.post(
                f"{self.url}/transmission/rpc",
                json=payload,
                headers={"X-Transmission-Session-Id": self._sid},
                auth=self._auth, timeout=10)
            name_low = release_name.lower()
            for t in r.json().get("arguments", {}).get("torrents", []):
                t_name = (t.get("name") or "").lower()
                if name_low in t_name or t_name in name_low:
                    STATUS_MAP = {0: "stoppedUP", 1: "checkingUP", 2: "checkingUP",
                                  3: "queuedUP",  4: "downloading", 5: "queuedUP",
                                  6: "uploading"}
                    return STATUS_MAP.get(t.get("status", -1), "") in GOOD
        except Exception:
            pass
        return False


def _L(label, value):
    """Formate une ligne NFO style MediaInfo alignee."""
    return f"{label:<41}: {value}"


def _mediainfo_block(fp):
    """
    Retourne un dict avec toutes les pistes MediaInfo du fichier.
    Retourne None si pymediainfo n'est pas disponible ou échoue.
    """
    if not _MEDIAINFO_OK:
        return None
    try:
        mi = _MediaInfo.parse(str(fp))
        result = {"general": {}, "video": [], "audio": [], "text": []}
        for track in mi.tracks:
            t = track.track_type
            d = track.to_data()
            if t == "General":
                result["general"] = d
            elif t == "Video":
                result["video"].append(d)
            elif t == "Audio":
                result["audio"].append(d)
            elif t == "Text":
                result["text"].append(d)
        return result
    except Exception:
        return None


def _fmt_bitrate(bps):
    if not bps: return "N/A"
    try:
        bps = int(bps)
        if bps >= 1_000_000: return f"{bps/1_000_000:.1f} Mb/s"
        return f"{bps//1000} kb/s"
    except Exception: return str(bps)


def _fmt_size(b):
    try:
        b = int(b)
        if b >= 1024**3: return f"{b/1024**3:.2f} GiB"
        if b >= 1024**2: return f"{b/1024**2:.0f} MiB"
        return f"{b//1024} KiB"
    except Exception: return str(b)


def _fmt_duration(ms):
    try:
        ms = int(float(ms))
        h, rem = divmod(ms // 1000, 3600)
        m, s   = divmod(rem, 60)
        return f"{h} h {m:02d} min" if h else f"{m} min {s:02d} s"
    except Exception: return str(ms)


def make_nfo_film(fp, p, title, year, tmdb_id, imdb_id, rating, genres, sz):
    """Génère un NFO style MediaInfo complet pour un film."""
    mi = _mediainfo_block(fp)

    lines = ["General"]

    if mi:
        g = mi["general"]
        lines += [
            _L("Complete name",          fp.name),
            _L("Format",                 g.get("format", "Matroska")),
            _L("Format version",         g.get("format_version", "")),
            _L("File size",              _fmt_size(g.get("file_size", sz))),
            _L("Duration",               _fmt_duration(g.get("duration", ""))),
            _L("Overall bit rate mode",  g.get("overall_bit_rate_mode", "Variable")),
            _L("Overall bit rate",       _fmt_bitrate(g.get("overall_bit_rate", ""))),
            _L("Frame rate",             f"{float(g['frame_rate']):.3f} FPS" if g.get("frame_rate") else ""),
            _L("Writing application",    g.get("writing_application", "")),
        ]
        # Video
        for i, v in enumerate(mi["video"], 1):
            lines += ["", f"Video{' #'+str(i) if len(mi['video'])>1 else ''}"]
            lines += [
                _L("Format",              v.get("format", "")),
                _L("Format/Info",         v.get("format_info", "") or v.get("format_profile", "")),
                _L("Format profile",      v.get("format_profile", "")),
                _L("HDR format",          v.get("hdr_format", "") or v.get("hdr_format_commercial", "")),
                _L("Codec ID",            v.get("codec_id", "")),
                _L("Duration",            _fmt_duration(v.get("duration", ""))),
                _L("Bit rate",            _fmt_bitrate(v.get("bit_rate", ""))),
                _L("Width",               f"{int(v['width']):,} pixels".replace(",", " ") if v.get("width") else ""),
                _L("Height",              f"{int(v['height']):,} pixels".replace(",", " ") if v.get("height") else ""),
                _L("Display aspect ratio",v.get("display_aspect_ratio", "")),
                _L("Frame rate mode",     v.get("frame_rate_mode", "")),
                _L("Frame rate",          f"{float(v['frame_rate']):.3f} FPS" if v.get("frame_rate") else ""),
                _L("Bit depth",           f"{v['bit_depth']} bits" if v.get("bit_depth") else ""),
                _L("Color primaries",     v.get("color_primaries", "")),
                _L("Transfer char.",      v.get("transfer_characteristics", "")),
                _L("Original source",     v.get("original_source_medium", "")),
                _L("Language",            v.get("language", "")),
                _L("Stream size",         _fmt_size(v.get("stream_size", ""))),
            ]
        # Audio
        for i, a in enumerate(mi["audio"], 1):
            lines += ["", f"Audio{' #'+str(i) if len(mi['audio'])>1 else ''}"]
            lines += [
                _L("Format",              a.get("format", "")),
                _L("Format/Info",         a.get("format_info", "") or a.get("commercial_name", "") or a.get("format_commercial", "")),
                _L("Commercial name",     a.get("commercial_name", "") or a.get("format_commercial", "")),
                _L("Codec ID",            a.get("codec_id", "")),
                _L("Duration",            _fmt_duration(a.get("duration", ""))),
                _L("Bit rate mode",       a.get("bit_rate_mode", "")),
                _L("Bit rate",            _fmt_bitrate(a.get("bit_rate", ""))),
                _L("Channel(s)",          f"{a['channel_s']} channels" if a.get("channel_s") else ""),
                _L("Channel layout",      a.get("channel_layout", "")),
                _L("Sampling rate",       f"{int(a['sampling_rate'])//1000:.1f} kHz" if a.get("sampling_rate") else ""),
                _L("Bit depth",           f"{a['bit_depth']} bits" if a.get("bit_depth") else ""),
                _L("Compression mode",    a.get("compression_mode", "")),
                _L("Title",               a.get("title", "")),
                _L("Language",            a.get("language", "")),
                _L("Default",             a.get("default", "")),
                _L("Forced",              a.get("forced", "")),
                _L("Stream size",         _fmt_size(a.get("stream_size", ""))),
            ]
        # Subtitles
        for i, t in enumerate(mi["text"], 1):
            lines += ["", f"Text{' #'+str(i) if len(mi['text'])>1 else ''}"]
            lines += [
                _L("Format",     t.get("format", "")),
                _L("Codec ID",   t.get("codec_id", "")),
                _L("Language",   t.get("language", "")),
                _L("Default",    t.get("default", "")),
                _L("Forced",     t.get("forced", "")),
            ]
    else:
        # Fallback depuis le nom de fichier
        vc_map = {"x265": "HEVC", "x264": "AVC", "AV1": "AV1", "VC-1": "VC-1"}
        ac_map = {"TrueHD": "Dolby TrueHD", "EAC3": "Dolby Digital Plus",
                  "AC3": "Dolby Digital", "DTS-X": "DTS-X",
                  "DTS-HD.MA": "DTS-HD Master Audio", "DTS-HD": "DTS-HD",
                  "DTS": "DTS", "FLAC": "FLAC", "OPUS": "Opus", "AAC": "AAC"}
        res_map = {"2160p": "3 840 x 2 160", "1080p": "1 920 x 1 080",
                   "720p": "1 280 x 720", "480p": "720 x 480"}
        vc_full = vc_map.get(p.get("vc", "x264"), p.get("vc", "x264"))
        ac_full = ac_map.get(p.get("ac", "AAC"), p.get("ac", "AAC"))
        if p.get("atmos"): ac_full += " with Dolby Atmos"
        lines += [
            _L("Complete name",   fp.name),
            _L("Format",          "Matroska"),
            _L("File size",       f"{sz/1024**3:.2f} GiB"),
            _L("Overall bit rate", "N/A (MediaInfo non lu)"),
            "", "Video",
            _L("Format",          vc_full),
            _L("Width x Height",  res_map.get(p.get("res", ""), p.get("res", "SD"))),
            _L("HDR format",      p.get("hdr", "") or "SDR"),
            _L("Original source", p.get("src", "WEB")),
            "", "Audio",
            _L("Format",          ac_full),
            _L("Channel(s)",      p.get("ach", "N/A")),
            _L("Language",        p.get("lang", "FRENCH")),
        ]

    # Métadonnées TMDb
    lines += [
        "",
        "Metadata",
        _L("Title",     f"{title} ({year})"),
        _L("TMDb ID",   str(tmdb_id or "N/A")),
        _L("IMDB ID",   str(imdb_id or "N/A")),
        _L("Note TMDb", f"{rating}/10"),
        _L("Genres",    genres or "N/A"),
    ]

    # --- AJOUT : Liste des fichiers (pour voir les sous-titres externes) ---
    # On vérifie s'il y a des fichiers supplémentaires (subs) dans le dossier
    movie_subs = [s for s in fp.parent.iterdir() 
                 if s.is_file() and s.suffix.lower() in {".srt", ".ass", ".ssa", ".sub", ".idx"}]
    
    if movie_subs:
        lines += ["", "Included Files"]
        lines += [f"  {fp.name} (Main Video)"]
        for sub in movie_subs:
            lines += [f"  {sub.name}"]
    # -----------------------------------------------------------------------
    # Nettoyer les lignes vides consécutives et les valeurs vides
    clean = []
    for l in lines:
        if l and ": " in l and l.split(": ", 1)[1].strip() == "":
            continue  # ignorer les champs vides
        clean.append(l)

    return "\n".join(clean)


def make_nfo_series(files, p, title, year, season_tag, tmdb_id, rating, genres, sz):
    """Génère un NFO style MediaInfo complet pour une saison (analyse le 1er épisode)."""
    # Analyser le premier épisode comme référence
    # Chercher le premier fichier VIDÉO pour le NFO (évite de prendre un .srt comme référence)
    video_refs = [f for f in files if f.suffix.lower() in VIDEO_EXTS]
    ref_fp = video_refs[0] if video_refs else (files[0] if files else None)
    mi = _mediainfo_block(ref_fp) if ref_fp else None

    lines = [
        "General",
        _L("Series name",  title),
        _L("Season",       season_tag),
        _L("Episodes", str(sum(1 for f in files if f.suffix.lower() in VIDEO_EXTS))),
        _L("Total size",   f"{sz/1024**3:.2f} GiB"),
        _L("Format",       "Matroska"),
        _L("Source",       p.get("src", "WEB")),
    ]

    if mi:
        # Video depuis le 1er épisode
        for i, v in enumerate(mi["video"], 1):
            lines += ["", f"Video{' #'+str(i) if len(mi['video'])>1 else ''}"]
            lines += [
                _L("Format",              v.get("format", "")),
                _L("Bit rate",            _fmt_bitrate(v.get("bit_rate", ""))), # AJOUTÉ
                _L("HDR format",          v.get("hdr_format", "") or v.get("hdr_format_commercial", "")),
                _L("Width",               f"{int(v['width']):,} pixels".replace(",", " ") if v.get("width") else ""),
                _L("Height",              f"{int(v['height']):,} pixels".replace(",", " ") if v.get("height") else ""),
                _L("Frame rate",          f"{float(v['frame_rate']):.3f} FPS" if v.get("frame_rate") else ""),
                _L("Bit depth",           f"{v['bit_depth']} bits" if v.get("bit_depth") else ""),
                _L("Color primaries",     v.get("color_primaries", "")),
            ]
        # Audio
        for i, a in enumerate(mi["audio"], 1):
            lines += ["", f"Audio{' #'+str(i) if len(mi['audio'])>1 else ''}"]
            lines += [
                _L("Format",          a.get("format", "")),
                _L("Commercial name", a.get("commercial_name", "") or a.get("format_commercial", "")),
                _L("Bit rate",        _fmt_bitrate(a.get("bit_rate", ""))), # AJOUTÉ/VÉRIFIÉ
                _L("Channel(s)",      f"{a['channel_s']} channels" if a.get("channel_s") else ""),
                _L("Language",        a.get("language", "")),
                _L("Title",           a.get("title", "")),
            ]
        # Sous-titres
        for i, t in enumerate(mi["text"], 1):
            lines += ["", f"Text{' #'+str(i) if len(mi['text'])>1 else ''}"]
            lines += [
                _L("Format",   t.get("format", "")),
                _L("Language", t.get("language", "")),
                _L("Forced",   t.get("forced", "")),
            ]
    else:
        # Fallback si MediaInfo échoue
        vc_map = {"x265": "HEVC", "x264": "AVC", "AV1": "AV1", "VC-1": "VC-1"}
        ac_map = {"TrueHD": "Dolby TrueHD", "EAC3": "Dolby Digital Plus",
                  "AC3": "Dolby Digital", "DTS-X": "DTS-X",
                  "DTS-HD.MA": "DTS-HD Master Audio", "DTS-HD": "DTS-HD",
                  "DTS": "DTS", "FLAC": "FLAC", "OPUS": "Opus", "AAC": "AAC"}
        res_map = {"2160p": "3 840 x 2 160", "1080p": "1 920 x 1 080",
                   "720p": "1 280 x 720", "480p": "720 x 480"}
        vc_full = vc_map.get(p.get("vc", "x264"), p.get("vc", "x264"))
        ac_full = ac_map.get(p.get("ac", "AAC"), p.get("ac", "AAC"))
        if p.get("atmos"): ac_full += " with Dolby Atmos"
        lines += [
            "", "Video",
            _L("Format",         vc_full),
            _L("Width x Height", res_map.get(p.get("res", ""), p.get("res", "N/A"))),
            _L("HDR format",     p.get("hdr", "") or "SDR"),
            "", "Audio",
            _L("Format",         ac_full),
            _L("Channel(s)",     p.get("ach", "N/A")),
            _L("Language",       p.get("lang", "FRENCH")),
        ]

    lines += [
        "",
        "Metadata",
        _L("Title",     f"{title} — {season_tag}"),
        _L("TMDb ID",   str(tmdb_id or "N/A")),
        _L("Note TMDb", f"{rating}/10"),
        _L("Genres",    genres or "N/A"),
        "",
        "Episodes",
    ] + [f"  {f.name}" for f in files]

    clean = []
    for l in lines:
        if l and ": " in l and l.split(": ", 1)[1].strip() == "":
            continue
        clean.append(l)

    return "\n".join(clean)

def make_bbcode(title, year_or_tag, overview, poster, res, vc, ac, lang,
                size, rating, genres, cast, hdr, is_series=False, season_num=None, has_subs=False):
    pu = (f"https://image.tmdb.org/t/p/w500{poster}"
          if poster and not poster.startswith("http") else poster or "")
    rs  = f"{rating:.1f}" if isinstance(rating, float) else str(rating or "N/A")
    tp  = f"Série — Saison {season_num}" if (is_series and season_num) else ("Série" if is_series else "Film")

    parts_size = []
    if isinstance(size, (int, float)) and size:
        parts_size.append(f"{size/1024**3:.2f} GiB")
    ss = parts_size[0] if parts_size else "N/A"

    bb  = "[center]\n"
    if pu: bb += f"[img]{pu}[/img]\n\n"
    bb += f"[size=6][color=#eab308][b]{title} ({year_or_tag})[/b][/color][/size]\n\n"
    bb += f"[b]Type :[/b] {tp}\n[b]Note :[/b] {rs}/10\n[b]Genre :[/b] {genres or 'N/A'}\n\n"
    if overview: bb += f"[quote]{overview}[/quote]\n\n"
    bb += "[color=#eab308][b]--- DÉTAILS ---[/b][/color]\n\n"
    bb += f"[b]Qualité :[/b] {res or 'N/A'}\n[b]Codec Vidéo :[/b] {vc}\n"
    bb += f"[b]Codec Audio :[/b] {ac}\n"
    if hdr: bb += f"[b]HDR :[/b] {hdr}\n"
    bb += f"[b]Langue :[/b] {lang}\n"
    # --- AJOUT LIGNE SOUS-TITRES ---
    if has_subs:
        bb += "[b]Sous-titres :[/b] Externes inclus (.srt/.ass)\n"
    # -------------------------------
    bb += f"[b]Taille totale :[/b] {ss}"
    if cast:
        bb += "\n\n[color=#eab308][b]--- CASTING ---[/b][/color]\n\n"
        for a in cast[:5]:
            bb += f"[b]{a['name']}[/b] ({a.get('character', '')})\n"
    bb += "\n\n[/center]"
    return bb

# ══════════════════════════════════════════════════════════════════════════════
# WORKER — Thread d'upload
# ══════════════════════════════════════════════════════════════════════════════
class Worker:
    def __init__(self, cfg, log, done, prog, start_watcher_cb=None, set_count_cb=None, curl_cb=None):
        self.cfg  = cfg
        self.log  = log
        self.done = done
        self.prog = prog
        self._start_watcher_cb = start_watcher_cb
        self._set_count        = set_count_cb or (lambda c, t: None)
        self._curl_cb          = curl_cb or (lambda cmd: None)
        self._stop = threading.Event()

    def stop(self): self._stop.set()

    def run(self):
        try:
            self._run()
        except Exception as e:
            import traceback
            self.log(f"ERREUR inattendue : {e}", "err")
            self.log(traceback.format_exc(), "muted")
        self.done()

    def _run(self):
        cfg = self.cfg
        out = Path(cfg.get("torrents_dir") or str(TORRENTS_DIR))
        out.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        active_tracker = cfg.get("active_tracker", "lacale")
        use_torr9      = (active_tracker == "torr9")

        # ── Clients ──────────────────────────────────────────────────────────
        if use_torr9:
            # ── TORR9 ────────────────────────────────────────────────────────
            t9_url = cfg.get("torr9_url", "https://www.torr9.net")
            t9     = Torr9(t9_url, self.log)

            self.log("Vérification de l'état de Torr9...", "gold")
            if _check_bypass(cfg.get("_dev_field", "")):
                self.log("  ⚡ Mode bypass activé — vérification ignorée.", "gold")
            else:
                hc_ok, hc_msg = t9.health_check()
                if not hc_ok:
                    self.log(f"  Arrêt — {hc_msg}", "err")
                    if self._start_watcher_cb:
                        self._start_watcher_cb()
                    return

            # Connexion selon le mode choisi
            conn_mode = cfg.get("conn_mode", "web")
            if conn_mode == "api":
                # Mode API : utilise le token stocké
                stored_token = cfg.get("torr9_token", "").strip()
                if stored_token:
                    if not t9.set_token(stored_token):
                        self.log("Abandon — token Torr9 invalide.", "err"); return
                else:
                    self.log("  Mode API : aucun token trouvé — utilisez le bouton 'Récupérer' dans les paramètres.", "err"); return
            else:
                # Mode Web : login user/pass
                if not t9.login(cfg.get("torr9_user", ""), cfg.get("torr9_pass", "")):
                    self.log("Abandon — connexion Torr9 impossible.", "err"); return

            lc        = None
            conn_mode = "web"  # Torr9 = Web only
            passkey   = ""

        else:
            # ── LA CALE ──────────────────────────────────────────────────────
            lc = LaCale(cfg["lacale_url"], self.log)
            t9 = None

            self.log("Vérification de l'état du site La Cale...", "gold")
            if _check_bypass(cfg.get("_dev_field", "")):
                self.log("  ⚡ Mode bypass activé — vérification ignorée.", "gold")
                self.log("  Si vous avez piraté le code, félicitations! Vous êtes un vrais pirate!", "err")
            else:
                hc_ok, hc_msg = lc.health_check()
                if not hc_ok:
                    self.log(f"  Arrêt — {hc_msg}", "err")
                    self.log("  Configurez la notification dans les réglages pour être averti quand il sera de retour.", "muted")
                    self.log("  Relancez une fois le site accessible.", "muted")
                    if self._start_watcher_cb:
                        self._start_watcher_cb()
                    return

            conn_mode = cfg.get("conn_mode", "web")
            if conn_mode == "api":
                passkey = cfg.get("lacale_passkey", "")
                if not lc.login_api(passkey):
                    self.log("Abandon — vérifiez le passkey API.", "err"); return
                lc.prepare_api()
            else:
                passkey = ""
                if not lc.login(cfg["lacale_user"], cfg["lacale_pass"]):
                    self.log("Abandon.", "err"); return
                lc.prepare()

        self.log("  Vérification de la configuration en cours...", "muted")

        tmdb = (TMDb(cfg["tmdb_token"], cfg.get("tmdb_lang", "fr-FR"), self.log)
                if cfg.get("tmdb_token") else None)
        client_type = cfg.get("torrent_client", "qbittorrent")
        if client_type == "transmission":
            qb = Transmission(cfg["tr_url"], cfg.get("tr_user", ""),
                              cfg.get("tr_pass", ""), self.log)
        elif client_type == "deluge":
            qb = Deluge(cfg.get("deluge_url", "http://localhost:8112"),
                        cfg.get("deluge_pass", ""), self.log)
        elif client_type == "vuze":
            qb = Vuze(cfg.get("vuze_url", "http://localhost:9091"),
                      cfg.get("vuze_user", "vuze"),
                      cfg.get("vuze_pass", ""), self.log)
        else:
            qb = QBit(cfg["qb_url"], cfg["qb_user"], cfg["qb_pass"], self.log)

        # Helper : retourne le bon chemin de sauvegarde selon le client actif
        def _save_path(kind="films"):
            ct = cfg.get("torrent_client", "qbittorrent")
            if ct == "transmission":
                key = "tr_films_path" if kind == "films" else "tr_series_path"
            elif ct == "deluge":
                key = "deluge_films_path" if kind == "films" else "deluge_series_path"
            elif ct == "vuze":
                key = "vuze_films_path" if kind == "films" else "vuze_series_path"
            else:
                key = "qb_films_path" if kind == "films" else "qb_series_path"
            raw = cfg.get(key, "/Films" if kind == "films" else "/Series")
            return _unc_to_linux(raw) if ct == "qbittorrent" else raw

        hist = set()
        if HIST_FILE.exists():
            try:
                for line in HIST_FILE.read_text("utf-8", errors="ignore").splitlines():
                    if line.strip():
                        # On ne garde que la partie avant la première tabulation (le nom du torrent/fichier)
                        hist.add(line.split('\t')[0].strip())
            except Exception as e:
                self.log(f"  Erreur lecture historique : {e}", "muted")
        rank_q = {"": 0, "480p": 1, "720p": 2, "1080p": 3, "2160p": 4}
        min_q  = cfg.get("min_quality", "")
        total  = 0
        max_films  = int(cfg.get("max_movies") or 1)
        max_series = int(cfg.get("max_series") or max_films)
        grand_total = max_films + max_series
        self._set_count(0, grand_total)

        # ════════════════════════════════════════════════════════════════════
        # FILMS
        # ════════════════════════════════════════════════════════════════════
        films_dir = cfg.get("films_dir", "").strip()

        if films_dir and not self._stop.is_set():
            self.log(f"\n{'═'*60}", "gold")
            self.log(f"  FILMS — {films_dir}", "gold")
            self.log(f"{'═'*60}", "gold")

            fp_root = Path(films_dir)
            if not fp_root.exists():
                self.log(f"  Dossier inaccessible : {fp_root}", "err")
                self.log("  Vérifiez que le partage réseau est accessible.", "muted")
            else:
                self.log("  Détection des films en cours... (1 min pour ~2000 fichiers)", "muted")
                files = []
                for p_ in fp_root.rglob("*"):
                    if self._stop.is_set(): break
                    if p_.is_file() and p_.suffix.lower() in VIDEO_EXTS:
                        files.append(p_)
                        if len(files) % 50 == 0:
                            self.prog(-1, f"Scan films : {len(files)} fichiers...")
                files.sort()
                self.prog(0, "")
                self.log(f"  {len(files)} fichier(s) trouvé(s).", "muted")
                uploaded = 0

                for fp in files:
                    if self._stop.is_set() or uploaded >= max_films: break
                    fn = fp.name
                    
                    # --- SKIP IMMEDIAT HISTORIQUE ---
                    if fn in hist:
                        self.log(f"  SKIP : '{fn}' déjà dans l'historique — si l'upload a échoué à mi-chemin, supprimez cette entrée de uploaded_torrents.txt.", "muted")
                        continue
                    
                    self.log(f"\n  ▸ {fn}", "gold")
                    p  = parse_filename(fn)

                    if min_q and rank_q.get(p["res"], 0) < rank_q.get(min_q, 0):
                        self.log(f"  SKIP : qualité {p['res']} < {min_q}", "muted"); continue
                    if fn in hist:
                        self.log("  SKIP : historique.", "muted"); continue

                    # TMDb
                    tmdb_id  = None
                    title    = p["title"] or fp.stem
                    year     = p["year"]
                    overview = poster = genres = imdb_id = ""
                    rating   = 0.0; cast = []

                    if tmdb:
                        # Nettoyage du titre pour TMDb (pas de points traînants)
                        search_title = p["title"].replace('.', ' ').strip('. ')
                        self.log(f"  TMDb → \"{search_title}\" ({year})...", "muted")
                        res = tmdb.search_movie(search_title, year or None)
                        if res:
                            tmdb_id = res.get("id")
                            det     = tmdb.movie_details(tmdb_id)
                            if det:
                                # --- NOUVELLE LOGIQUE : Détection de la langue d'origine TMDb ---
                                # On récupère found_langs depuis le dictionnaire p
                                f_langs = p.get("found_langs", [])
                                
                                iso_map = {
                                    'fr': 'FRENCH',     'en': 'ENGLISH',    'es': 'SPANiSH',
                                    'it': 'iTALiAN',    'de': 'GERMAN',     'pt': 'PORTUGUESE',
                                    'ro': 'ROMANiAN',   'ru': 'RUSSiAN',    'nl': 'DUTCH',
                                    'pl': 'POLiSH',     'zh': 'CHiNESE',    'ja': 'JAPANESE',
                                    'ko': 'KOREAN',     'hi': 'HiNDi',      'tr': 'TURKiSH',
                                    'ar': 'ARABiC',     'fa': 'PERSiAN',    'el': 'GREEK',
                                    'sv': 'SWEDiSH',    'da': 'DANiSH',     'no': 'NORWEGiAN',
                                    'fi': 'FiNNiSH',    'cs': 'CZECH',      'hu': 'HUNGARiAN',
                                    'th': 'THAi'
                                }
                                
                                orig_lang_iso = det.get("original_language", "")
                                
                                if orig_lang_iso in iso_map and orig_lang_iso != 'fr':
                                    # On n'applique la VO que si le fichier n'est PAS MULTi (déjà bilingue)
                                    if p.get('lang') != "MULTi" and "FRENCH" not in f_langs:
                                        p['lang'] = iso_map[orig_lang_iso]
                                        self.log(f"  Info : Langue originale détectée ({orig_lang_iso}) → {p['lang']}", "ok")

                                # Titre original si film français, sinon titre FR
                                if det.get("original_language") == "fr":
                                    title = det.get("original_title") or det.get("title") or title
                                else:
                                    title    = det.get("title") or title
                                year     = (det.get("release_date", ""))[:4]
                                overview = det.get("overview", "")
                                poster   = det.get("poster_path", "")
                                rating   = det.get("vote_average", 0.0)
                                genres   = ", ".join(g["name"] for g in det.get("genres", []))
                                cast     = [{"name": a["name"], "character": a.get("character", "")}
                                            for a in det.get("credits", {}).get("cast", [])[:5]]
                                imdb_id  = det.get("external_ids", {}).get("imdb_id", "")
                                self.log(f"  TMDb OK : {title} ({year}) — {rating}/10", "ok")
                        else:
                            self.log(f"  SKIP : TMDb non trouvé pour '{p['title']}' (Recherche obligatoire).", "err")
                            continue

                    # Release name
                    stem    = fp.stem
                    release = stem if not re.search(r'[ ()\[]', stem) \
                              else build_release_name_movie(title, year, p)
                    self.log(f"  Release : {release}", "muted")

                    if release in hist or fn in hist:
                        self.log("  SKIP : Présent dans l'historique (uploaded_torrents.txt).", "muted")
                        continue

                    if lc is not None and lc.count(title) > 0:
                        self.log("  ◈ Doublon La Cale — déjà en ligne, laissez en seed.", "dup"); continue
                    # ── Vérification doublon Torr9 ────────────────────────────
                    if use_torr9 and t9.check_duplicate(release):
                        self.log("  ◈ Doublon Torr9 — déjà en ligne, laissez en seed.", "dup"); continue

                    # ── Génération torrent ────────────────────────────────────
                    # ── Détection des sous-titres associés ──
                    # On cherche tous les fichiers de sous-titres dans le même dossier que le film
                    movie_subs = [s for s in fp.parent.iterdir() 
                                 if s.is_file() and s.suffix.lower() in SUB_EXTS]
                    
                    # ── Génération torrent ──
                    self.log("  Hash SHA1...", "muted")
                    self.prog(0.0, f"Hash : {fn[:50]}")
                    try:
                        tracker_url    = cfg.get("torr9_announce", "") if use_torr9 else cfg.get("tracker_url", "")
                        torrent_source = "torr9" if use_torr9 else "lacale"
                        
                        if movie_subs:
                            # S'il y a des sous-titres, on bascule en torrent MULTI-FICHIERS
                            # IMPORTANT : On utilise le nom RÉEL du dossier sur le disque (ex: 28 Weeks Later (2007))
                            # pour que Deluge retrouve les fichiers sans erreur.
                            self.log(f"  Sous-titres détectés : {len(movie_subs)} fichier(s) inclus.", "ok")
                            all_files = [fp] + movie_subs
                            tb = make_torrent_multi(fp.parent.name, all_files, tracker_url,
                                                lambda pct: self.prog(pct, f"Hash {int(pct*100)}%"),
                                                 source=torrent_source)
                        else:
                            # Pas de sous-titres, on reste sur un torrent SINGLE-FILE classique
                            _tname = fp.name 
                            tb = make_torrent_single(fp, tracker_url,
                                                 lambda pct: self.prog(pct, f"Hash {int(pct*100)}%"),
                                                 source=torrent_source,
                                                 torrent_name=_tname)
                    except Exception as e:
                        self.log(f"  ERREUR torrent : {e}", "err"); continue

                    self.prog(1.0, "")
                    self.log(f"  Torrent : {len(tb)//1024} Ko", "ok")
                    (out / f"{release}.torrent").write_bytes(tb)        

                    # ── NFO ───────────────────────────────────────────────────
                    sz  = fp.stat().st_size
                    nfo = make_nfo_film(fp, p, title, year, tmdb_id, imdb_id,
                                        rating, genres, sz)
                    self.log(f"  NFO : {'MediaInfo complet' if _MEDIAINFO_OK else 'fallback nom de fichier'}", "muted")
                    # On utilise la variable movie_subs créée précédemment
                    desc = make_bbcode(title, year, overview, poster, p["res"],
                                       p["vc"], p["ac"], p["lang"], sz, rating,
                                       genres, cast, p["hdr"], is_series=False,
                                       has_subs=bool(movie_subs))

                    # ── Chargement dans client torrent + mise en seed ─────────
                    if qb.ok:
                        if client_type in ("transmission", "deluge", "vuze"):
                            # On récupère la racine configurée (ex: /Movies)
                            root_in_client = _save_path("films")
                            # On récupère le chemin local configuré dans l'UI
                            local_root = Path(cfg.get("films_dir", ""))
                            try:
                                # Calcul du chemin relatif
                                rel = fp.parent.relative_to(local_root)
                                rel_str = str(rel).replace("\\", "/")
                                
                                if movie_subs:
                                    # Pour un pack (film + subs), on pointe vers le PARENT du dossier du film
                                    # (ex: /Movies) car le torrent contient déjà le nom du dossier.
                                    actual_save_path = root_in_client if rel_str == "." else str(Path(f"{root_in_client}/{rel_str}").parent).replace("\\", "/")
                                else:
                                    # Torrent simple : on garde le comportement actuel
                                    actual_save_path = root_in_client if rel_str == "." else f"{root_in_client}/{rel_str}"
                            except ValueError:
                                actual_save_path = root_in_client
                            self.log(f"  {client_type.capitalize()} path config : '{actual_save_path}'", "muted")
                        else:
                            raw_path = cfg.get("qb_films_path", "/Films")
                            self.log(f"  QB path config brut : '{raw_path}'", "muted")
                            qb_films_root = _unc_to_linux(raw_path)
                            self.log(f"  QB path converti    : '{qb_films_root}'", "muted")
                            films_root = Path(cfg.get("films_dir", ""))
                            try:
                                rel     = fp.parent.relative_to(films_root)
                                rel_str = str(rel).replace("\\", "/")
                                actual_save_path = qb_films_root if rel_str == "." else f"{qb_films_root}/{rel_str}"
                            except ValueError:
                                actual_save_path = qb_films_root

                        ih = torrent_info_hash(tb)
                        self.log(f"  Client savepath \u2192 '{actual_save_path}'", "muted")
                        self.log(f"  Info-hash : {ih}", "muted")
                        added = qb.add(tb, actual_save_path, release)
                        if not added:
                            self.log(f"  ERREUR : ajout dans {client_type} \u00e9chou\u00e9.", "err")
                            self.log("  Arr\u00eat du processus.", "err")
                            self._stop.set(); break
                        time.sleep(1)
                        if client_type == "qbittorrent":
                            qb.set_location(ih, actual_save_path)

                        # \u2500\u2500 V\u00e9rification seed (QB + Deluge) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
                        seed_ok = False
                        if client_type in ("qbittorrent", "deluge",
                                           "transmission", "vuze"):
                          GOOD = {"uploading", "stalledUP", "forcedUP", "queuedUP",
                                  "checkingUP", "stoppedUP", "pausedUP", "moving",
                                  "Seeding", "Checking"}
                          BAD  = {"missingFiles", "error", "Error"}
                          for attempt in range(3):
                            for i in range(10, 0, -1):
                                if self._stop.is_set(): break
                                self.prog(-1, f"Mise en seed : {attempt*10+10-i}s...")
                                time.sleep(1)
                            if self._stop.is_set(): break
                            state, cp = qb.get_torrent_state_by_hash(ih)
                            if state in GOOD:
                                seed_ok = True
                                break
                            elif state in BAD:
                                self.log(f"  ERREUR seed : \u00e9tat '{state}'", "err")
                                self.log(f"  {client_type.capitalize()} cherche : {cp}", "err")
                                self._stop.set(); break
                            self.log(f"  [seed] \u00e9tat : {state or '?'} \u2014 attente...", "muted")
                          self.prog(0, "")
                          if self._stop.is_set(): break
                          if not seed_ok:
                            self.log("  ERREUR : seed non confirm\u00e9 apr\u00e8s 30s \u2014 arr\u00eat.", "err")
                            self._stop.set(); break
                          self.log(f"  {client_type.capitalize()} : seed\u00e9 \u2713", "ok")
                        else:
                          self.log(f"  {client_type.capitalize()} : ajout\u00e9 \u2713", "ok")


                    # ── Upload sur le tracker ─────────────────────────────────
                    self.log("  Upload...", "muted")
                    if use_torr9:
                        ok, body = t9.upload(release, tb, desc, is_series=False, tmdb_id=tmdb_id, nfo=nfo, lang=p.get('lang', 'FRENCH'), genres=genres)
                        t_id = body.get("torrent_id", "")
                        link = f"https://torr9.net/torrents/{t_id}" if t_id else ""
                        if ok:
                            status_msg = body.get("status", "")
                            self.log(f"  Torr9 : {body.get('message','OK')}", "ok")
                            if status_msg == "pending":
                                self.log("  ℹ️  En attente de validation par un modérateur.", "muted")
                    else:
                        terms = lc.build_terms(p, is_series=False)
                        if conn_mode == "api":
                            ok, body = lc.upload_api(passkey, release, tb, nfo, desc,
                                                      tmdb_id=tmdb_id, is_series=False, terms=terms,
                                                      lang=p.get('lang', 'FRENCH'))
                        else:
                            ok, body = lc.upload(release, tb, nfo, desc,
                                                 tmdb_id=tmdb_id, is_series=False, terms=terms,
                                                 lang=p.get('lang', 'FRENCH'))
                        slug = body.get("slug") or body.get("data", {}).get("slug", "")
                        link = f"{cfg['lacale_url']}/torrents/{slug}" if slug else ""

                    if not ok:
                        msg = body.get("message") or body.get("error") or (str(body) if body else "Timeout / Réponse vide du serveur")
                        if "dupliqu" in msg.lower() or "existe déjà" in msg.lower() or "already" in msg.lower():
                            self.log("  ◈ Doublon serveur — déjà en ligne, laissez en seed.", "dup")
                            continue
                        self.log(f"  ERREUR d'upload : {msg}", "err")
                        if "limite" in msg.lower():
                            self.log("  Limite atteinte — arrêt.", "err"); break
                        continue

                    self.log(f"  OK !{' — '+link if link else ''}", "ok")

                    self._notify_discord(cfg, title, year, release, link)
                    self._save_history(hist, release, fn, cfg=cfg)
                    uploaded += 1; total += 1
                    self._set_count(total, grand_total)
                    if uploaded < max_films and not self._stop.is_set():
                        time.sleep(int(cfg.get("upload_delay", 3)))

        # ════════════════════════════════════════════════════════════════════
        # SÉRIES — logique par saison
        # ════════════════════════════════════════════════════════════════════
        series_root = cfg.get("series_dir", "").strip()
        max_series  = int(cfg.get("max_series") or 1)

        if series_root and not self._stop.is_set():
            self.log(f"\n{'═'*60}", "gold")
            self.log(f"  SÉRIES — {series_root}", "gold")
            self.log(f"{'═'*60}", "gold")

            sr = Path(series_root)
            if not sr.exists():
                self.log(f"  Dossier inaccessible : {sr}", "err")
                self.log("  Vérifiez que le partage réseau est accessible.", "muted")
            else:
                self.log("  Détection des séries en cours... (1 min pour ~2000 fichiers)", "muted")
                seasons = scan_seasons(sr,
                    prog_cb=lambda n: self.prog(-1, f"Scan séries : {n} saison(s)..."))
                self.prog(0, "")
                self.log(f"  {len(seasons)} saison(s) trouvée(s).", "muted")
                uploaded = 0

                for season_dir in seasons:
                    if self._stop.is_set() or uploaded >= max_series: break
                    
                    # --- SKIP IMMEDIAT HISTORIQUE ---
                    # On vérifie si le dossier (ex: 1883 - S01) a déjà été traité
                    if season_dir.name in hist:
                        self.log(f"  SKIP : '{season_dir.name}' déjà dans l'historique — si l'upload a échoué à mi-chemin, supprimez cette entrée de uploaded_torrents.txt.", "muted")
                        continue

                    sd = parse_season_dir(season_dir)
                    if not sd["files"]:
                        self.log(f"  SKIP : {season_dir.name} (aucun fichier vidéo)", "muted")
                        continue

                    p         = sd["tags"]
                    series_name = sd["series_name"]
                    season_tag  = sd["season_tag"]
                    season_num  = sd["season_num"]

                    self.log(f"\n  ▸ {series_name} — {season_tag} ({sd['video_count']} épisode(s))", "gold")

                    if min_q and rank_q.get(p.get("res", ""), 0) < rank_q.get(min_q, 0):
                        self.log(f"  SKIP : qualité {p.get('res')} < {min_q}", "muted"); continue

                    # Historique basé sur le dossier de saison
                    hist_key = f"{series_name}_{season_tag}"
                    if hist_key in hist:
                        self.log("  SKIP : historique.", "muted"); continue

                    # TMDb — recherche par nom de série
                    tmdb_id  = None
                    title    = series_name
                    year     = ""
                    overview = poster = genres = ""
                    rating   = 0.0; cast = []

                    if tmdb:
                        self.log(f"  TMDb → \"{series_name}\" ({sd.get('series_year','—')})...", "muted")
                        res = tmdb.search_tv(series_name, sd.get("series_year") or None)
                        if res:
                            tmdb_id = res.get("id")
                            det     = tmdb.tv_details(tmdb_id, season_num)
                            if det:
                                # --- NOUVELLE LOGIQUE : Détection de la langue d'origine TMDb ---
                                f_langs = p.get("found_langs", []) # p est sd["tags"] ici
                                
                                iso_map = {
                                    'fr': 'FRENCH',     'en': 'ENGLISH',    'es': 'SPANiSH',
                                    'it': 'iTALiAN',    'de': 'GERMAN',     'pt': 'PORTUGUESE',
                                    'ro': 'ROMANiAN',   'ru': 'RUSSiAN',    'nl': 'DUTCH',
                                    'pl': 'POLiSH',     'zh': 'CHiNESE',    'ja': 'JAPANESE',
                                    'ko': 'KOREAN',     'hi': 'HiNDi',      'tr': 'TURKiSH',
                                    'ar': 'ARABiC',     'fa': 'PERSiAN',    'el': 'GREEK',
                                    'sv': 'SWEDiSH',    'da': 'DANiSH',     'no': 'NORWEGiAN',
                                    'fi': 'FiNNiSH',    'cs': 'CZECH',      'hu': 'HUNGARiAN',
                                    'th': 'THAi'
                                }
                                
                                orig_lang_iso = det.get("original_language", "")
                                
                                if orig_lang_iso in iso_map and orig_lang_iso != 'fr':
                                    # On n'applique la VO que si le fichier n'est PAS MULTi (déjà bilingue)
                                    if p.get('lang') != "MULTi" and "FRENCH" not in f_langs:
                                        p['lang'] = iso_map[orig_lang_iso]
                                        self.log(f"  Info : Langue originale détectée ({orig_lang_iso}) → {p['lang']}", "ok")

                                # Nom original si série française, sinon nom FR
                                if det.get("original_language") == "fr":
                                    title = det.get("original_name") or det.get("name") or series_name
                                else:
                                    title    = det.get("name") or series_name
                                year     = (det.get("first_air_date", ""))[:4]
                                overview = det.get("overview", "")
                                poster   = det.get("poster_path", "")
                                s_det    = det.get("season_detail", {})
                                if s_det.get("poster_path"):
                                    poster = s_det["poster_path"]
                                if s_det.get("overview"):
                                    overview = s_det["overview"]
                                rating   = det.get("vote_average", 0.0)
                                genres   = ", ".join(g["name"] for g in det.get("genres", []))
                                cast     = [{"name": a["name"], "character": a.get("character", "")}
                                            for a in det.get("credits", {}).get("cast", [])[:5]]
                                self.log(f"  TMDb OK : {title} — {season_tag} ({year}) — {rating}/10", "ok")
                        else:
                            self.log(f"  SKIP : TMDb non trouvé pour '{series_name}' (Recherche obligatoire).", "err")
                            continue

                    # Release name : Titre.S01.MULTi.1080p.WEB-DL.x265-GRP
                    release = build_release_name_season(title, season_tag, p)
                    self.log(f"  Release : {release}", "muted")

                    if release in hist or hist_key in hist:
                        self.log(f"  SKIP : {series_name} {season_tag} déjà dans l'historique.", "muted")
                        continue

                    if lc is not None and lc.count(title, is_series=True) > 0:
                        self.log(f"  ◈ Doublon La Cale — déjà en ligne, laissez en seed.", "dup"); continue

                    # ── Vérification doublon Torr9 ────────────────────────────
                    if use_torr9 and t9.check_duplicate(release):
                        self.log("  ◈ Doublon Torr9 — déjà en ligne, laissez en seed.", "dup"); continue

                    # ── Génération torrent ────────────────────────────────────
                    self.log(f"  Hash SHA1 ({len(sd['files'])} fichiers)...", "muted")
                    self.prog(0.0, f"Hash saison : {release[:50]}")
                    try:
                        tracker_url    = cfg.get("torr9_announce", "") if use_torr9 else cfg.get("tracker_url", "")
                        torrent_source = "torr9" if use_torr9 else "lacale"
                        # IMPORTANT : On utilise season_dir.name ("Season 1") comme nom interne
                        # pour que Deluge trouve les fichiers sans chercher un sous-dossier release.
                        tb = make_torrent_multi(
                            season_dir.name, sd["files"], tracker_url,
                            lambda pct: self.prog(pct, f"Hash {int(pct*100)}%"),
                            source=torrent_source)
                    except Exception as e:
                        self.log(f"  ERREUR torrent : {e}", "err"); continue
                    self.prog(1.0, "")
                    self.log(f"  Torrent : {len(tb)//1024} Ko", "ok")
                    (out / f"{release}.torrent").write_bytes(tb)

                    # ── Chargement dans client torrent + mise en seed ─────────
                    if qb.ok:
                        if client_type in ("transmission", "deluge", "vuze"):
                            root_in_client = _save_path("series")
                            local_root = Path(cfg.get("series_dir", ""))
                            try:
                                # On pointe vers le dossier PARENT de "Season 1" (ex: /Series/1883)
                                rel = season_dir.parent.relative_to(local_root)
                                rel_str = str(rel).replace("\\", "/")
                                actual_save_path = root_in_client if rel_str == "." else f"{root_in_client}/{rel_str}"
                            except ValueError:
                                actual_save_path = root_in_client
                        else:
                            # Logique qBittorrent classique
                            qb_series_root   = _unc_to_linux(cfg.get("qb_series_path", "/Series"))
                            series_root_path = Path(cfg.get("series_dir", ""))
                            try:
                                season_dir_path  = sd["files"][0].parent
                                show_dir         = season_dir_path.parent
                                rel              = show_dir.relative_to(series_root_path)
                                rel_str          = str(rel).replace("\\", "/")
                                actual_save_path = f"{qb_series_root}/{rel_str}" if rel_str != "." else qb_series_root
                            except (ValueError, IndexError):
                                actual_save_path = qb_series_root

                    # ── NFO ───────────────────────────────────────────────────
                    sz  = sd["total_size"]
                    nfo = make_nfo_series(sd["files"], p, title, year, season_tag,
                                          tmdb_id, rating, genres, sz)
                    self.log(f"  NFO : {'MediaInfo complet' if _MEDIAINFO_OK else 'fallback nom de fichier'}", "muted")

                    # On vérifie si un des fichiers de la saison est un sous-titre
                    has_external_subs = any(f.suffix.lower() in SUB_EXTS for f in sd["files"])

                    desc = make_bbcode(title, f"{year} — {season_tag}", overview, poster,
                                       p.get("res", ""), p.get("vc", "x264"),
                                       p.get("ac", "AAC"), p.get("lang", "FRENCH"),
                                       sz, rating, genres, cast, p.get("hdr", ""),
                                       is_series=True, season_num=season_num,
                                       has_subs=has_external_subs)

                    # ── Chargement dans client torrent + mise en seed ─────────
                    if qb.ok:
                        if client_type in ("transmission", "deluge", "vuze"):
                            root_in_client = _save_path("series")
                            local_root = Path(cfg.get("series_dir", ""))
                            try:
                                # On calcule le chemin relatif du dossier contenant le dossier Saison
                                rel = season_dir.parent.relative_to(local_root)
                                rel_str = str(rel).replace("\\", "/")
                                # On pointe Deluge vers le dossier PARENT du dossier "Season 1" (ex: /Series/1883)
                                # Le client torrent ajoutera automatiquement "/Season 1" grâce au nom interne du torrent.
                                actual_save_path = root_in_client if rel_str == "." else f"{root_in_client}/{rel_str}"
                            except ValueError:
                                actual_save_path = root_in_client
                            self.log(f"  {client_type.capitalize()} path config : '{actual_save_path}'", "muted")

                        ih = torrent_info_hash(tb)
                        self.log(f"  Client savepath \u2192 '{actual_save_path}'", "muted")
                        self.log(f"  Info-hash : {ih}", "muted")
                        added = qb.add(tb, actual_save_path, release)
                        if not added:
                            self.log(f"  ERREUR : ajout dans {client_type} \u00e9chou\u00e9.", "err")
                            self.log("  Arr\u00eat du processus.", "err")
                            self._stop.set(); break
                        time.sleep(1)
                        if client_type == "qbittorrent":
                            qb.set_location(ih, actual_save_path)

                        # \u2500\u2500 V\u00e9rification seed (QB + Deluge) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
                        seed_ok = False
                        if client_type in ("qbittorrent", "deluge",
                                           "transmission", "vuze"):
                          GOOD = {"uploading", "stalledUP", "forcedUP", "queuedUP",
                                  "checkingUP", "stoppedUP", "pausedUP", "moving",
                                  "Seeding", "Checking"}
                          BAD  = {"missingFiles", "error", "Error"}
                          for attempt in range(3):
                            for i in range(10, 0, -1):
                                if self._stop.is_set(): break
                                self.prog(-1, f"Mise en seed : {attempt*10+10-i}s...")
                                time.sleep(1)
                            if self._stop.is_set(): break
                            state, cp = qb.get_torrent_state_by_hash(ih)
                            if state in GOOD:
                                seed_ok = True
                                break
                            elif state in BAD:
                                self.log(f"  ERREUR seed : \u00e9tat '{state}'", "err")
                                self.log(f"  {client_type.capitalize()} cherche : {cp}", "err")
                                self._stop.set(); break
                            self.log(f"  [seed] \u00e9tat : {state or '?'} \u2014 attente...", "muted")
                          self.prog(0, "")
                          if self._stop.is_set(): break
                          if not seed_ok:
                            self.log("  ERREUR : seed non confirm\u00e9 apr\u00e8s 30s \u2014 arr\u00eat.", "err")
                            self._stop.set(); break
                          self.log(f"  {client_type.capitalize()} : seed\u00e9 \u2713", "ok")
                        else:
                          self.log(f"  {client_type.capitalize()} : ajout\u00e9 \u2713", "ok")


                    # ── Upload sur le tracker ─────────────────────────────────
                    self.log("  Upload...", "muted")
                    if use_torr9:
                        ok, body = t9.upload(release, tb, desc, is_series=True, tmdb_id=tmdb_id, nfo=nfo, lang=p.get('lang', 'FRENCH'), genres=genres)
                        t_id = body.get("torrent_id", "")
                        link = f"https://torr9.net/torrents/{t_id}" if t_id else ""
                        if ok:
                            status_msg = body.get("status", "")
                            self.log(f"  Torr9 : {body.get('message','OK')}", "ok")
                            if status_msg == "pending":
                                self.log("  ℹ️  En attente de validation par un modérateur.", "muted")
                    else:
                        terms = lc.build_terms(p, is_series=True)
                        if conn_mode == "api":
                            ok, body = lc.upload_api(passkey, release, tb, nfo, desc,
                                                      tmdb_id=tmdb_id, is_series=True, terms=terms,
                                                      lang=p.get('lang', 'FRENCH'))
                        else:
                            ok, body = lc.upload(release, tb, nfo, desc,
                                                 tmdb_id=tmdb_id, is_series=True, terms=terms,
                                                 lang=p.get('lang', 'FRENCH'))
                        slug = body.get("slug") or body.get("data", {}).get("slug", "")
                        link = f"{cfg['lacale_url']}/torrents/{slug}" if slug else ""

                    if not ok:
                        msg = body.get("message") or body.get("error") or (str(body) if body else "Timeout / Réponse vide du serveur")
                        if "dupliqu" in msg.lower() or "existe déjà" in msg.lower() or "already" in msg.lower():
                            self.log("  ◈ Doublon serveur — déjà en ligne, laissez en seed.", "dup")
                            continue
                        self.log(f"  ERREUR d'upload : {msg}", "err")
                        if "limite" in msg.lower():
                            self.log("  Limite atteinte — arrêt.", "err"); break
                        continue

                    self.log(f"  OK !{' — '+link if link else ''}", "ok")

                    self._notify_discord(cfg, f"{title} {season_tag}", year, release, link)
                    self._save_history(hist, release, hist_key, cfg=cfg)
                    uploaded += 1; total += 1
                    if uploaded < max_series and not self._stop.is_set():
                        time.sleep(int(cfg.get("upload_delay", 3)))
                    self._set_count(total, grand_total)

        self.log(f"\n{'═'*60}", "gold")
        self.log(f"  TERMINÉ — {total} upload(s) effectué(s)", "gold")
        self.log(f"{'═'*60}", "gold")

    def _save_history(self, hist_set, *keys, cfg=None):
        # Lire le tracker depuis cfg passé en argument, ou self.cfg en fallback
        _cfg     = cfg or self.cfg
        tracker  = _cfg.get("active_tracker", "lacale")
        tag      = "TORR9" if tracker == "torr9" else "LACALE"
        date_str = __import__("datetime").date.today().strftime("%d/%m/%y")
        with open(HIST_FILE, "a", encoding="utf-8") as hf:
            for k in keys:
                hf.write(f"{k}\t[{tag}]\t[DATE:{date_str}]\n")
        hist_set.update(keys)

    def _notify_discord(self, cfg, title, year, release, link):
        if not cfg.get("discord_webhook"): return
        try:
            requests.post(cfg["discord_webhook"], timeout=10,
                json={"embeds": [{"title": f"Upload OK — {title} ({year})",
                                  "description": f"{release}\n{link}",
                                  "color": 5763719}]})
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# INTERFACE GRAPHIQUE
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# INTERNATIONALISATION — labels de l'interface
# ══════════════════════════════════════════════════════════════════════════════
LANGS_UI = {
    "fr": "Français",
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "it": "Italiano",
    "pt": "Português",
    "ja": "日本語",
}

T = {
    "fr": dict(
        title="BLACK FLAG v{v}",
        subtitle="Version exécutable  ·  v{v}",
        log_header="  JOURNAL DE BORD",
        btn_clear="Effacer log",
        btn_history="Historique des uploads",
        films="Films :",
        series="Séries :",
        max="Max :",
        grade="Grade :",
        max_uploads="Max uploads :",
        quality="Qualité min. :",
        btn_settings_open="▶  PARAMÈTRES",
        btn_settings_close="▼  PARAMÈTRES",
        btn_save="SAUVEGARDER CONFIGURATION",
        btn_autosave_on="⏺ Autosave ON",
        btn_autosave_off="⏹ Autosave OFF",
        btn_clear_cfg="Effacer config",
        confirm_clear_cfg="Effacer toute la configuration sauvegardée ?",
        btn_stop="■  STOPPER",
        btn_launch="⚑  APPAREILLER",
        status_ready="  Prêt à appareiller",
        status_running="  Navigation en cours...",
        status_saved="  Configuration sauvegardée",
        status_done="  Terminé",
        status_stopping="  Arrêt en cours...",
        lbl_conn_mode="Mode de connexion :",
        conn_api="API",
        conn_web="Web",
        lbl_passkey="Passkey API :",
        lbl_passkey_hint="la-cale.space/settings/api-keys",
        sec_lacale="LA CALE",
        sec_tmdb="THE MOVIE DATABASE (TMDb) & MediaInfo",
        sec_qb="QBITTORRENT",
        sec_misc="DIVERS",
        lbl_lacale_url="URL La Cale :",
        lbl_email="Email :",
        lbl_pass="Mot de passe :",
        lbl_tracker="Tracker URL :",
        lbl_tmdb_key="Bearer Token :",
        lbl_tmdb_lang="Langue TMDb :",
        lbl_ui_lang="Langue interface :",
        lbl_qb_url="URL WebUI :",
        lbl_qb_user="Utilisateur :",
        lbl_qb_pass="Mot de passe :",
        lbl_qb_films="Save path Films :",
        lbl_qb_series="Save path Séries :",
        lbl_tr_url="URL WebUI :",
        lbl_tr_user="Utilisateur :",
        lbl_tr_pass="Mot de passe :",
        lbl_tr_films="Save path Films :",
        lbl_tr_series="Save path Séries :",
        tip_tr_url="ex: http://192.168.1.x:9091",
        lbl_discord="Discord Webhook :",
        lbl_torrents="Dossier torrents :",
        lbl_delay="Délai uploads (s) :",
        lbl_notify="Notification si HTTP 200 :",
        lbl_save_logs="Sauvegarde des logs :",
        lbl_check_updates="Vérif. mises à jour :",
        check_updates_on="ACTIF",
        check_updates_off="NON ACTIF",
        lbl_seed_check="Vérif. seed QB :",
        seed_check_on="OBLIGATOIRE",
        seed_check_off="DÉSACTIVÉE",
        lbl_update_available="Mise à jour disponible",
        lbl_save_curl="Génération fichiers curl Web :",
        save_logs_on="ACTIF",
        save_logs_off="NON ACTIF",
        save_curl_on="ACTIF",
        save_curl_off="NON ACTIF",
        notify_on="ACTIF",
        notify_off="NON ACTIF",
        lbl_notify_interval="Intervalle de vérification :",
        notify_hint="Activé auto si le site est KO",
        tip_qb_url="ex: http://192.168.1.x:8080",
        tip_qb_path="Chemin des fichiers, vu par Qbittorrent en local.\n(Normalement identique aux deux premiers champs en \\.)\nPour Nas/Serveurs, variable selon container, juste dupliquer l'avant dossier en /\n(exemple: /Films/Films)",
        btn_qb_fetch="↺ Récupérer",
        tmdb_link="Clé gratuite → themoviedb.org/settings/api",
        hist_title="Historique des uploads",
        hist_empty="Aucun upload enregistré.",
        hist_btn_close="Fermer",
        hist_btn_clear="Vider l'historique",
        hist_confirm_clear="Vider tout l'historique ?",
        err_no_dir="Au moins un dossier Films ou Séries est requis",
        err_no_user="Email La Cale requis",
        err_no_pass="Mot de passe La Cale requis",
        err_no_tracker="Tracker URL requise",
        err_no_qb="URL qBittorrent requise",
        err_no_requests="Module 'requests' non disponible",
        err_title="Manque à l'appel !",
        quit_msg="Navigation en cours. Quitter quand même ?",
        quit_title="Quitter",
        req_title="Module manquant",
        req_msg="'requests' n'a pas pu être installé.\n\nRéessayer maintenant ? (Internet requis)",
        log_start="⚑  Appareillage en cours...",
        log_films="   Films  : {d}  (max {m})",
        log_series="   Séries : {d}  (max {m})",
        log_saved="Configuration sauvegardée.",
        log_stop="■  Arrêt demandé...",
    ),
    "en": dict(
        title="BLACK FLAG v{v}",
        subtitle="Executable release  ·  v{v}",
        log_header="  LOG",
        btn_clear="Clear log",
        btn_history="Upload history",
        films="Movies :",
        series="Series :",
        max="Max :",
        grade="Grade :",
        max_uploads="Max uploads :",
        quality="Min quality :",
        btn_settings_open="▶  SETTINGS",
        btn_settings_close="▼  SETTINGS",
        btn_save="SAVE CONFIGURATION",
        btn_autosave_on="⏺ Autosave ON",
        btn_autosave_off="⏹ Autosave OFF",
        btn_clear_cfg="Clear config",
        confirm_clear_cfg="Clear all saved configuration?",
        btn_stop="■  STOP",
        btn_launch="⚑  LAUNCH",
        status_ready="  Ready",
        status_running="  Running...",
        status_saved="  Settings saved",
        status_done="  Done",
        status_stopping="  Stopping...",
        lbl_conn_mode="Connection mode :",
        conn_api="API",
        conn_web="Web",
        lbl_passkey="API Passkey :",
        lbl_passkey_hint="la-cale.space/settings/api-keys",
        sec_lacale="LA CALE",
        sec_tmdb="THE MOVIE DATABASE (TMDb) & MediaInfo",
        sec_qb="QBITTORRENT",
        sec_misc="MISC",
        lbl_lacale_url="La Cale URL :",
        lbl_email="Email :",
        lbl_pass="Password :",
        lbl_tracker="Tracker URL :",
        lbl_tmdb_key="Bearer Token :",
        lbl_tmdb_lang="TMDb language :",
        lbl_ui_lang="UI language :",
        lbl_qb_url="WebUI URL :",
        lbl_qb_user="Username :",
        lbl_qb_pass="Password :",
        lbl_qb_films="Movies save path :",
        lbl_qb_series="Series save path :",
        lbl_tr_url="WebUI URL :",
        lbl_tr_user="Username :",
        lbl_tr_pass="Password :",
        lbl_tr_films="Movies save path :",
        lbl_tr_series="Series save path :",
        tip_tr_url="ex: http://192.168.1.x:9091",
        lbl_discord="Discord Webhook :",
        lbl_torrents="Torrents folder :",
        lbl_delay="Upload delay (s) :",
        lbl_notify="Notify on HTTP 200 :",
        lbl_save_logs="Log backup :",
        lbl_check_updates="Check for updates :",
        check_updates_on="ACTIVE",
        check_updates_off="INACTIVE",
        lbl_seed_check="QB seed check :",
        seed_check_on="REQUIRED",
        seed_check_off="DISABLED",
        lbl_update_available="Update available",
        lbl_save_curl="Web curl file generation :",
        save_logs_on="ACTIVE",
        save_logs_off="INACTIVE",
        save_curl_on="ACTIVE",
        save_curl_off="INACTIVE",
        notify_on="ACTIVE",
        notify_off="INACTIVE",
        lbl_notify_interval="Check interval :",
        notify_hint="Auto-enabled when site is down",
        tip_qb_url="ex: http://192.168.1.x:8080",
        tip_qb_path="File path as seen by qBittorrent locally.\n(Normally identical to the first two fields, using \\.)\nFor NAS/Servers, varies by container — just duplicate the parent folder in /\n(example: /Movies/Movies)",
        btn_qb_fetch="↺ Fetch",
        tmdb_link="Free key → themoviedb.org/settings/api",
        hist_title="Upload history",
        hist_empty="No uploads recorded.",
        hist_btn_close="Close",
        hist_btn_clear="Clear history",
        hist_confirm_clear="Clear all history?",
        err_no_dir="At least one Movies or Series folder is required",
        err_no_user="La Cale email required",
        err_no_pass="La Cale password required",
        err_no_tracker="Tracker URL required",
        err_no_qb="qBittorrent URL required",
        err_no_requests="Python module 'requests' not available",
        err_title="Missing fields!",
        quit_msg="Upload in progress. Quit anyway?",
        quit_title="Quit",
        req_title="Missing module",
        req_msg="'requests' could not be installed.\n\nRetry now? (Internet required)",
        log_start="⚑  Starting...",
        log_films="   Movies : {d}  (max {m})",
        log_series="   Series : {d}  (max {m})",
        log_saved="Settings saved.",
        log_stop="■  Stop requested...",
    ),
    "es": dict(
        title="BLACK FLAG v{v}",
        subtitle="Versión ejecutable  ·  v{v}",
        log_header="  REGISTRO",
        btn_clear="Borrar log",
        btn_history="Historial de uploads",
        films="Películas :",
        series="Series :",
        max="Máx :",
        grade="Grado :",
        max_uploads="Máx uploads :",
        quality="Calidad mín. :",
        btn_settings_open="▶  AJUSTES",
        btn_settings_close="▼  AJUSTES",
        btn_save="GUARDAR CONFIGURACIÓN",
        btn_autosave_on="⏺ Autosave ON",
        btn_autosave_off="⏹ Autosave OFF",
        btn_clear_cfg="Borrar config",
        confirm_clear_cfg="¿Borrar toda la configuración guardada?",
        btn_stop="■  DETENER",
        btn_launch="⚑  LANZAR",
        status_ready="  Listo",
        status_running="  En curso...",
        status_saved="  Configuración guardada",
        status_done="  Terminado",
        status_stopping="  Deteniendo...",
        lbl_conn_mode="Modo de conexión :",
        conn_api="API",
        conn_web="Web",
        lbl_passkey="Passkey API :",
        lbl_passkey_hint="la-cale.space/settings/api-keys",
        sec_lacale="LA CALE",
        sec_tmdb="THE MOVIE DATABASE (TMDb) & MediaInfo",
        sec_qb="QBITTORRENT",
        sec_misc="MISC",
        lbl_lacale_url="URL La Cale :",
        lbl_email="Email :",
        lbl_pass="Contraseña :",
        lbl_tracker="Tracker URL :",
        lbl_tmdb_key="Bearer Token :",
        lbl_tmdb_lang="Idioma TMDb :",
        lbl_ui_lang="Idioma interfaz :",
        lbl_qb_url="URL WebUI :",
        lbl_qb_user="Usuario :",
        lbl_qb_pass="Contraseña :",
        lbl_qb_films="Ruta películas :",
        lbl_qb_series="Ruta series :",
        lbl_tr_url="URL WebUI :",
        lbl_tr_user="Usuario :",
        lbl_tr_pass="Contraseña :",
        lbl_tr_films="Ruta películas :",
        lbl_tr_series="Ruta series :",
        tip_tr_url="ex: http://192.168.1.x:9091",
        lbl_discord="Discord Webhook :",
        lbl_torrents="Carpeta torrents :",
        lbl_delay="Retraso uploads (s) :",
        lbl_notify="Notif. si HTTP 200 :",
        lbl_save_logs="Guardar logs :",
        lbl_check_updates="Buscar actualizaciones :",
        check_updates_on="ACTIVO",
        check_updates_off="INACTIVO",
        lbl_update_available="Actualización disponible",
        lbl_save_curl="Generar archivos curl Web :",
        save_logs_on="ACTIVO",
        save_logs_off="INACTIVO",
        save_curl_on="ACTIVO",
        save_curl_off="INACTIVO",
        notify_on="ACTIVO",
        notify_off="INACTIVO",
        lbl_notify_interval="Intervalo :",
        notify_hint="Activado auto si el sitio está caído",
        tip_qb_url="ej: http://192.168.1.x:8080",
        tip_qb_path="Ruta de archivos vista por qBittorrent en local.\n(Normalmente idéntica a los dos primeros campos, con \\.)\nPara NAS/Servidores, varía según container — duplicar la carpeta padre en /\n(ejemplo: /Peliculas/Peliculas)",
        btn_qb_fetch="↺ Obtener",
        tmdb_link="Clave gratuita → themoviedb.org/settings/api",
        hist_title="Historial de uploads",
        hist_empty="Sin uploads registrados.",
        hist_btn_close="Cerrar",
        hist_btn_clear="Vaciar historial",
        hist_confirm_clear="¿Vaciar todo el historial?",
        err_no_dir="Se requiere al menos una carpeta de Películas o Series",
        err_no_user="Email de La Cale requerido",
        err_no_pass="Contraseña de La Cale requerida",
        err_no_tracker="Tracker URL requerida",
        err_no_qb="URL de qBittorrent requerida",
        err_no_requests="Módulo 'requests' no disponible",
        err_title="¡Campos faltantes!",
        quit_msg="Upload en curso. ¿Salir de todos modos?",
        quit_title="Salir",
        req_title="Módulo faltante",
        req_msg="'requests' no pudo instalarse.\n\n¿Reintentar? (Internet requerido)",
        log_start="⚑  Iniciando...",
        log_films="   Películas : {d}  (max {m})",
        log_series="   Series : {d}  (max {m})",
        log_saved="Configuración guardada.",
        log_stop="■  Detención solicitada...",
        lbl_seed_check="Verificación seed QB :",
        seed_check_on="OBLIGATORIO",
        seed_check_off="DESACTIVADO",
    ),
}
# Langues supplémentaires (basées sur fr, avec sous-titre traduit)
_SUBTITLES = {
    "de": "Ausführbare Version  ·  v{v}",
    "it": "Versione eseguibile  ·  v{v}",
    "pt": "Versão executável  ·  v{v}",
    "ja": "実行可能バージョン  ·  v{v}",
}
_OVERRIDES = {
    "de": dict(btn_clear="Log leeren",    btn_history="Upload-Verlauf",    btn_save="KONFIGURATION SPEICHERN",
               grade="Stufe :",           max_uploads="Max uploads :",
               lbl_conn_mode="Verbindungsmodus :", lbl_passkey="API Passkey :",
               lbl_notify="Benachrichtigung :", notify_on="AKTIV", notify_off="INAKTIV",
               lbl_notify_interval="Prüfintervall :"),
    "it": dict(btn_clear="Cancella log",  btn_history="Cronologia upload", btn_save="SALVA CONFIGURAZIONE",
               grade="Grado :",           max_uploads="Max upload :",
               lbl_conn_mode="Modalità connessione :", lbl_passkey="Passkey API :",
               lbl_notify="Notifica HTTP 200 :", notify_on="ATTIVO", notify_off="INATTIVO",
               lbl_notify_interval="Intervallo :"),
    "pt": dict(btn_clear="Limpar log",    btn_history="Histórico uploads", btn_save="GUARDAR CONFIGURAÇÃO",
               grade="Grau :",            max_uploads="Máx uploads :",
               lbl_conn_mode="Modo de ligação :", lbl_passkey="Passkey API :",
               lbl_notify="Notif. HTTP 200 :", notify_on="ATIVO", notify_off="INATIVO",
               lbl_notify_interval="Intervalo :"),
    "ja": dict(
        title="BLACK FLAG v{v}",
        subtitle="実行可能バージョン  ·  v{v}",
        log_header="  ログ",
        btn_clear="ログ消去",
        btn_history="アップロード履歴",
        films="映画 :",
        series="シリーズ :",
        max="最大 :",
        grade="グレード :",
        max_uploads="最大アップロード数 :",
        quality="最低画質 :",
        btn_settings_open="▶  設定",
        btn_settings_close="▼  設定",
        btn_save="設定を保存",
        btn_stop="■  停止",
        btn_launch="⚑  アップロード開始",
        status_ready="  準備完了",
        status_running="  実行中...",
        status_saved="  設定を保存しました",
        status_done="  完了",
        status_stopping="  停止中...",
        sec_lacale="LA CALE",
        sec_tmdb="THE MOVIE DATABASE (TMDb) & MediaInfo",
        sec_qb="QBITTORRENT",
        sec_misc="その他",
        lbl_lacale_url="La Cale URL :",
        lbl_email="メール :",
        lbl_pass="パスワード :",
        lbl_tracker="トラッカー URL :",
        lbl_tmdb_key="Bearer トークン :",
        lbl_tmdb_lang="TMDb 言語 :",
        lbl_ui_lang="表示言語 :",
        lbl_qb_url="WebUI URL :",
        lbl_qb_user="ユーザー名 :",
        lbl_qb_pass="パスワード :",
        lbl_qb_films="映画の保存先 :",
        lbl_qb_series="シリーズの保存先 :",
        lbl_discord="Discord Webhook :",
        lbl_torrents="トレントフォルダー :",
        lbl_delay="アップロード間隔 (秒) :",
        lbl_notify="HTTP 200 通知 :",
        notify_on="有効",
        notify_off="無効",
        lbl_notify_interval="確認間隔 :",
        notify_hint="サイトがダウン時に自動有効",
        tip_qb_url="例: http://192.168.1.x:8080",
        tip_qb_path="qBittorrentがローカルで認識するファイルパス。\n(通常、最初の2つのフィールドと同じで \\. 形式。)\nNAS/サーバーの場合、コンテナによって異なる — 親フォルダを / で複製するだけ\n(例: /Movies/Movies)",
        btn_qb_fetch="↺ 取得",
        tmdb_link="無料キー取得 → themoviedb.org/settings/api",
        hist_title="アップロード履歴",
        hist_empty="アップロード記録なし。",
        hist_btn_close="閉じる",
        hist_btn_clear="履歴を消去",
        hist_confirm_clear="履歴をすべて消去しますか？",
        err_no_dir="映画またはシリーズのフォルダーが必要です",
        err_no_user="La Cale メールアドレスが必要です",
        err_no_pass="La Cale パスワードが必要です",
        err_no_tracker="トラッカー URL が必要です",
        err_no_qb="qBittorrent URL が必要です",
        err_no_requests="Python モジュール 'requests' が利用できません",
        err_title="入力エラー",
        quit_msg="アップロード中です。終了しますか？",
        quit_title="終了",
        req_title="モジュール不足",
        req_msg="'requests' を自動インストールできませんでした。\n\n今すぐ再試行しますか？（インターネット接続が必要）",
        log_start="⚑  アップロード開始...",
        log_films="   映画 : {d}  (最大 {m})",
        log_series="   シリーズ : {d}  (最大 {m})",
        log_saved="設定を保存しました。",
        log_stop="■  停止をリクエストしました...",
        btn_autosave_on="⏺ Autosave ON",
        btn_autosave_off="⏹ Autosave OFF",
        btn_clear_cfg="設定を消去",
        confirm_clear_cfg="保存された設定をすべて消去しますか？",
        conn_api="API",
        conn_web="Web",
        lbl_conn_mode="接続モード :",
        lbl_passkey="API Passkey :",
        lbl_passkey_hint="la-cale.space/settings/api-keys",
        lbl_save_logs="ログ保存 :",
        lbl_save_curl="curlファイル生成 :",
        save_logs_on="有効",
        save_logs_off="無効",
        save_curl_on="有効",
        save_curl_off="無効",
        lbl_check_updates="アップデート確認 :",
        check_updates_on="有効",
        check_updates_off="無効",
        lbl_seed_check="シード確認 QB :",
        seed_check_on="必須",
        seed_check_off="無効",
        lbl_update_available="アップデートあり",
        lbl_tr_url="WebUI URL :",
        lbl_tr_user="ユーザー名 :",
        lbl_tr_pass="パスワード :",
        lbl_tr_films="映画保存先 :",
        lbl_tr_series="シリーズ保存先 :",
        tip_tr_url="例: http://192.168.1.x:9091",
    ),
}
for _lc, _sub in _SUBTITLES.items():
    T[_lc] = dict(T["fr"])
    T[_lc]["subtitle"] = _sub
    T[_lc].update(_OVERRIDES.get(_lc, {}))

# Shorthand accessor — updated when language changes
_lang = "fr"
def t(key, **kw):
    s = T.get(_lang, T["fr"]).get(key, T["fr"].get(key, key))
    return s.format(**kw) if kw else s


# ══════════════════════════════════════════════════════════════════════════════
# ASCII LOGO (version une seule ligne horizontale, police 8)
# ══════════════════════════════════════════════════════════════════════════════
ASCII_LOGO = """\
      ___           ___       ___           ___           ___                    ___           ___       ___           ___     
     /\\  \\         /\\__\\     /\\  \\         /\\  \\         /\\__\\                  /\\  \\         /\\__\\     /\\  \\         /\\  \\    
    /::\\  \\       /:/  /    /::\\  \\       /::\\  \\       /:/  /                 /::\\  \\       /:/  /    /::\\  \\       /::\\  \\   
   /:/\\:\\  \\     /:/  /    /:/\\:\\  \\     /:/\\:\\  \\     /:/__/                 /:/\\:\\  \\     /:/  /    /:/\\:\\  \\     /:/\\:\\  \\  
  /::\\~\\:\\__\\   /:/  /    /::\\~\\:\\  \\   /:/  \\:\\  \\   /::\\__\\____            /::\\~\\:\\  \\   /:/  /    /::\\~\\:\\  \\   /:/  \\:\\  \\ 
 /:/\\:\\ \\:|__| /:/__/    /:/\\:\\ \\:\\__\\ /:/__/ \\:\\__\\ /:/\\:::::\\__\\          /:/\\:\\ \\:\\__\\ /:/__/    /:/\\:\\ \\:\\__\\ /:/__/_\\:\\__\\
 \\:\\~\\:\\/:/  / \\:\\  \\    \\/__\\:\\/:/  / \\:\\  \\  \\/__/ \\/_|:|~~|~             \\/__\\:\\ \\/__/ \\:\\  \\    \\/__\\:\\/:/  / \\:\\  /\\ \\/__/
  \\:\\ \\::/  /   \\:\\  \\        \\::/  /   \\:\\  \\          |:|  |                   \\:\\__\\    \\:\\  \\        \\::/  /   \\:\\ \\:\\__\\  
   \\:\\/:/  /     \\:\\  \\       /:/  /     \\:\\  \\         |:|  |                    \\/__/     \\:\\  \\       /:/  /     \\:\\/:/  /  
    \\::/__/       \\:\\__\\     /:/  /       \\:\\__\\        |:|  |                               \\:\\__\\     /:/  /       \\::/  /   
     ~~            \\/__/     \\/__/         \\/__/         \\|__|                                \\/__/     \\/__/         \\/__/     \
"""


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION WINDOWS (toast natif, sans dépendance externe)
# ══════════════════════════════════════════════════════════════════════════════
def _windows_toast(title: str, message: str):
    """Affiche une notification toast Windows native via ctypes/WinAPI."""
    try:
        import ctypes
        # Méthode 1 : MessageBox en mode non-bloquant via thread (fallback fiable)
        # Méthode principale : notification via Windows Script Host si disponible
        try:
            import subprocess
            # Utilise PowerShell pour afficher un toast Windows 10/11 natif
            ps_script = (
                f"Add-Type -AssemblyName System.Windows.Forms;"
                f"$n = New-Object System.Windows.Forms.NotifyIcon;"
                f"$n.Icon = [System.Drawing.SystemIcons]::Information;"
                f"$n.BalloonTipIcon = 'Info';"
                f"$n.BalloonTipTitle = '{title.replace(chr(39), '')}';"
                f"$n.BalloonTipText = '{message.replace(chr(39), '')}';"
                f"$n.Visible = $true;"
                f"$n.ShowBalloonTip(8000);"
                f"Start-Sleep -Seconds 9;"
                f"$n.Dispose()"
            )
            kwargs = {"creationflags": 0x08000000} if sys.platform == "win32" else {}
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden",
                 "-NonInteractive", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **kwargs)
        except Exception:
            # Fallback : MessageBox Windows si PowerShell échoue
            if sys.platform == "win32":
                threading.Thread(
                    target=lambda: ctypes.windll.user32.MessageBoxW(
                        0, message, title, 0x40 | 0x1000),
                    daemon=True).start()
    except Exception:
        pass   # Silencieux si hors Windows


# ══════════════════════════════════════════════════════════════════════════════
# WATCHER — Thread de surveillance du site
# ══════════════════════════════════════════════════════════════════════════════
class SiteWatcher:
    """
    Surveille La Cale en arrière-plan quand le site est KO.
    Poll toutes les N minutes, notifie Windows quand le site revient,
    puis s'arrête automatiquement.
    Se réactive automatiquement si le site retombe.
    """
    def __init__(self, url: str, interval_min: int, on_back_callback, site_label: str = "La Cale"):
        self.url          = url.rstrip("/")
        self.interval     = interval_min * 60   # en secondes
        self.on_back      = on_back_callback    # appelé quand le site revient
        self.site_label   = site_label
        self._stop_evt    = threading.Event()
        self._thread      = None
        self._active      = False

    def start(self):
        if self._active:
            return
        self._active  = True
        self._stop_evt.clear()
        self._thread  = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_evt.set()
        self._active = False

    @property
    def active(self):
        return self._active

    def _check_direct(self) -> bool:
        """Passe 2 allégée : HEAD direct sur le site."""
        try:
            r = requests.head(self.url, timeout=8,
                              headers={"User-Agent":
                                       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                                       "Chrome/124.0.0.0 Safari/537.36"})
            return r.status_code in (200, 301, 302, 307, 308)
        except Exception:
            return False

    def _run(self):
        while not self._stop_evt.is_set():
            # Attendre l'intervalle configuré (interruptible toutes les 5s)
            for _ in range(self.interval // 5):
                if self._stop_evt.is_set():
                    return
                time.sleep(5)

            if self._stop_evt.is_set():
                return

            # Vérifier si le site est revenu
            if self._check_direct():
                now = time.strftime("%Hh%M")
                title   = f"Notification de vérification tierce à {now} :"
                message = f"{self.site_label} de nouveau en ligne !"
                _windows_toast(title, message)
                self._active = False
                if self.on_back:
                    self.on_back()
                return   # Watcher s'arrête — le site est revenu




# ══════════════════════════════════════════════════════════════════════════════
# SCROLLBAR FINE — style Claude (fine, sombre, discrète)
# ══════════════════════════════════════════════════════════════════════════════
class SlimScrollbar(tk.Canvas):
    """
    Scrollbar fine inspirée de l'interface Claude.
    Remplace tk.Scrollbar — même API : command + set().
    Apparence : 4px de large, thumb arrondi, couleur C["border"] au repos,
    C["muted"] au survol.
    """
    W = 8   # largeur totale en pixels
    R = 4   # rayon du thumb arrondi

    def __init__(self, parent, command=None, **kw):
        super().__init__(parent,
                         width=self.W, bg=C["bg"],
                         highlightthickness=0, bd=0, **kw)
        self._cmd    = command
        self._top    = 0.0
        self._bot    = 1.0
        self._drag_y = None
        self._thumb  = self.create_rectangle(
            2, 0, self.W - 2, 20,
            fill=C["border"], outline="", width=0)
        self.bind("<Configure>",       self._redraw)
        self.bind("<ButtonPress-1>",   self._on_press)
        self.bind("<B1-Motion>",       self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>",  lambda e: self.itemconfig(self._thumb, fill=C["muted"]))
        self.bind("<Leave>",  lambda e: self.itemconfig(self._thumb, fill=C["border"]))
        self.bind("<MouseWheel>", self._on_wheel)

    def set(self, top, bot):
        self._top = float(top); self._bot = float(bot)
        self._redraw()

    def _redraw(self, *_):
        h = self.winfo_height() or 1
        y0 = max(2, int(self._top * h))
        y1 = min(h - 2, int(self._bot * h))
        if y1 - y0 < 12: y1 = y0 + 12
        self.coords(self._thumb, 2, y0, self.W - 2, y1)

    def _on_press(self, e):
        self._drag_y = e.y

    def _on_drag(self, e):
        if self._drag_y is None or not self._cmd:
            return
        h = self.winfo_height() or 1
        delta = (e.y - self._drag_y) / h
        self._drag_y = e.y
        self._cmd("moveto", self._top + delta)

    def _on_release(self, e):
        self._drag_y = None

    def _on_wheel(self, e):
        if self._cmd:
            self._cmd("scroll", int(-1 * (e.delta / 120)), "units")


# ══════════════════════════════════════════════════════════════════════════════
# INTERFACE GRAPHIQUE
# ══════════════════════════════════════════════════════════════════════════════
class App:
    def __init__(self, root):
        self.root    = root
        self.root.configure(bg=C["bg"])
        self.root.resizable(True, True)

        # ── Mot de passe maître SYNCHRONE avant tout le reste ────────────────
        # On demande le mot de passe AVANT load_cfg(), _build(), _load() etc.
        # pour que toute la session soit correctement chiffrée dès le départ.
        if _CRYPTO_OK:
            self._ask_master_password_sync()

        # Charger la config APRÈS avoir le mot de passe
        self.cfg     = load_cfg()
        self.worker  = None
        self.running = False
        self.vars    = {}
        self._settings_open = False
        self._loading       = True
        self._autosave_job  = None
        self._autosave_enabled = self.cfg.get("autosave_enabled", True)

        # Watcher de surveillance du site
        self._notify_enabled = bool(self.cfg.get("notify_enabled", False))
        self._watcher: SiteWatcher | None = None
        self._active_tracker = self.cfg.get("active_tracker", "lacale")
        self._save_logs_enabled = bool(self.cfg.get("save_logs", False))
        self._save_curl_enabled = bool(self.cfg.get("save_curl", False))
        self._check_updates_enabled = bool(self.cfg.get("check_updates", True))
        self._seed_check_enabled    = bool(self.cfg.get("seed_check", True))
        self._encrypt_cfg_enabled   = bool(self.cfg.get("encrypt_cfg", True))
        self._torrent_client        = self.cfg.get("torrent_client", "qbittorrent")

        # Fix combos invisibles sur Windows : forcer foreground sur les combobox
        # Le thème "clam" ne répercute pas correctement foreground en mode readonly
        root.option_add("*TCombobox*Listbox.foreground",   C["ifg"])
        root.option_add("*TCombobox*Listbox.background",   C["ibg"])
        root.option_add("*TCombobox*Listbox.selectForeground", C["gold"])
        root.option_add("*TCombobox*Listbox.selectBackground", C["border"])
        root.option_add("*TCombobox*Listbox.relief",        "flat")
        root.option_add("*TCombobox*Listbox.borderWidth",   "0")
        # Forcer la couleur de fond du popup (Windows ignore parfois option_add)
        root.tk.eval(f"""
            ttk::style configure BF.TCombobox \
                -fieldbackground {C['ibg']} \
                -background {C['ibg']} \
                -foreground {C['ifg']}
        """)

        # Thème UI (appliqué avant le build pour que les widgets naissent avec les bonnes couleurs)
        _saved_theme = self.cfg.get("ui_theme", "gold")
        if _saved_theme in THEMES:
            _current_theme[0] = _saved_theme
            C.update(THEMES[_saved_theme])

        # Langue UI (chargée depuis config, défaut fr)
        global _lang
        _lang = self.cfg.get("ui_lang", "fr")

        # Widgets à relabelliser dynamiquement
        self._dyn_labels   = {}
        self._dyn_combos   = {}
        self._settings_widgets = []

        self._build()
        self._load()
        self._center()
        self._apply_lang()   # applique les textes dans la bonne langue
        if not _REQUESTS_OK:
            self.root.after(400, self._ask_requests)

    def _ask_master_password_sync(self):
        """
        Popup synchrone mot de passe - bloque avant load_cfg.
        En cas de mauvais mot de passe : affiche l'erreur dans la dialog
        et redemande — ne sort JAMAIS silencieusement vers une session vierge.
        Seul le bouton explicite "Session sans chiffrement" permet de bypasser.
        """
        import tkinter as _tk
        first_launch = not CONFIG_ENC_FILE.exists()

        self.root.withdraw()

        while True:
            # ── Construire la dialog ──────────────────────────────────────────
            dlg = _tk.Toplevel(self.root)
            dlg.title("BLACK FLAG - Creer un mot de passe" if first_launch
                      else "BLACK FLAG - Mot de passe requis")
            dlg.configure(bg=C["bg"])
            dlg.resizable(False, False)
            dlg.update_idletasks()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            h  = 230 if first_launch else 200
            dlg.geometry(f"440x{h}+{(sw-440)//2}+{(sh-h)//2}")
            dlg.grab_set()
            dlg.lift()
            dlg.focus_force()

            _result = [None]   # None = skip, str = mot de passe

            if first_launch:
                lbl_title = "Creation du mot de passe maitre"
                lbl_hint  = "Ce mot de passe protege votre configuration.\nChoisissez-le bien - impossible a recuperer."
            else:
                lbl_title = "Config chiffree - Mot de passe requis"
                lbl_hint  = "Entrez votre mot de passe maitre\npour dechiffrer la configuration BLACK FLAG."

            _tk.Label(dlg, text=lbl_title, font=FB,
                      bg=C["bg"], fg=C["gold"]).pack(pady=(14, 2))
            _tk.Label(dlg, text=lbl_hint, font=FM8,
                      bg=C["bg"], fg=C["muted"], justify="center").pack(pady=(0, 8))

            frame_e = _tk.Frame(dlg, bg=C["bg"])
            frame_e.pack()

            _tk.Label(frame_e, text="Mot de passe :", font=FL,
                      bg=C["bg"], fg=C["text"]).grid(row=0, column=0, padx=(0, 6), pady=3)
            e1 = _tk.Entry(frame_e, show="*", font=FM, width=24,
                           bg=C["ibg"], fg=C["ifg"], insertbackground=C["gold"],
                           relief="flat", highlightthickness=1,
                           highlightbackground=C["border"])
            e1.grid(row=0, column=1, pady=3)
            e1.focus_set()

            e2 = None
            if first_launch:
                _tk.Label(frame_e, text="Confirmer :", font=FL,
                          bg=C["bg"], fg=C["text"]).grid(row=1, column=0, padx=(0, 6), pady=3)
                e2 = _tk.Entry(frame_e, show="*", font=FM, width=24,
                               bg=C["ibg"], fg=C["ifg"], insertbackground=C["gold"],
                               relief="flat", highlightthickness=1,
                               highlightbackground=C["border"])
                e2.grid(row=1, column=1, pady=3)

            lbl_err = _tk.Label(dlg, text="", font=FM8, bg=C["bg"], fg=C["red"])
            lbl_err.pack()

            def _validate(e1=e1, e2=e2, result=_result, err=lbl_err, d=dlg):
                pw = e1.get()
                if not pw:
                    err.config(text="Le mot de passe ne peut pas etre vide.")
                    return
                if e2 is not None and pw != e2.get():
                    err.config(text="Les mots de passe ne correspondent pas.")
                    return
                result[0] = pw
                d.destroy()

            def _skip(result=_result, d=dlg):
                result[0] = None
                d.destroy()

            bf = _tk.Frame(dlg, bg=C["bg"])
            bf.pack(pady=8)
            _tk.Button(bf, text="Valider", font=FB,
                       bg=C["panel"], fg=C["gold"], relief="flat",
                       padx=16, cursor="hand2",
                       command=_validate).pack(side="left", padx=8)
            _tk.Button(bf, text="Session sans chiffrement", font=FL,
                       bg=C["panel"], fg=C["muted"], relief="flat",
                       padx=8, cursor="hand2",
                       command=_skip).pack(side="left", padx=8)

            dlg.bind("<Return>", lambda e, v=_validate: v())
            dlg.bind("<Escape>", lambda e, s=_skip: s())
            dlg.protocol("WM_DELETE_WINDOW", _skip)

            self.root.wait_window(dlg)

            pw = _result[0]

            # ── Utilisateur a cliqué "Session sans chiffrement" ───────────────
            if pw is None:
                self._encrypt_cfg_enabled = False
                _SESSION_MASTER_PW[0] = None
                break   # sortie explicite de la boucle

            # ── Premier lancement : créer le mot de passe ─────────────────────
            if first_launch:
                _SESSION_MASTER_PW[0] = pw
                self._encrypt_cfg_enabled = True
                existing = load_cfg()
                existing["encrypt_cfg"] = True
                save_cfg(existing)
                if CONFIG_FILE.exists():
                    try:
                        CONFIG_FILE.unlink(missing_ok=True)
                    except Exception:
                        pass
                break   # mot de passe créé, on continue

            # ── Lancement suivant : vérifier le déchiffrement ─────────────────
            _SESSION_MASTER_PW[0] = pw
            test = _decrypt_cfg(CONFIG_ENC_FILE.read_bytes())
            if test is not None:
                # Succès
                self._encrypt_cfg_enabled = True
                break   # sortie de boucle, on continue le chargement
            else:
                # Mauvais mot de passe → afficher erreur et REBOUCLER
                _SESSION_MASTER_PW[0] = None
                import tkinter.messagebox as _mb
                retry = _mb.askretrycancel(
                    "Mot de passe incorrect",
                    "Le mot de passe est incorrect.\n\n"
                    "Réessayer ? (Annuler = session sans chiffrement)",
                    parent=self.root)
                if not retry:
                    # L'utilisateur renonce explicitement
                    self._encrypt_cfg_enabled = False
                    _SESSION_MASTER_PW[0] = None
                    break
                # Sinon on reboucle automatiquement

        # Réafficher la fenêtre principale dans tous les cas
        self.root.deiconify()

    def _prompt_master_password_on_start(self):
        """
        Appelee au lancement si crypto disponible.
        - Premier lancement (pas de .enc) : migre l'eventuelle config JSON en
          config chiffree, puis cree le mot de passe (confirm=True).
        - Lancements suivants (.enc existe) : demande le mot de passe et
          recharge la config dechiffree sans declencher les callbacks.
        - Annulation : session sans chiffrement (config JSON clair).
        """
        first_launch = not CONFIG_ENC_FILE.exists()

        if first_launch:
            # ── Premier lancement ─────────────────────────────────────────────
            pw = self._ask_master_password(
                confirm=True,
                title="Creer un mot de passe maitre — Protection de la config")
            if pw is None:
                self._encrypt_cfg_enabled = False
                self._log("  Chiffrement : annule — config en clair pour cette session.", "err")
                self._log("  Activez-le dans Parametres > Divers pour proteger vos donnees.", "muted")
                return
            _SESSION_MASTER_PW[0] = pw
            self._encrypt_cfg_enabled = True
            # Migrer la config actuelle (JSON clair ou DEFAULTS) vers .enc
            # self.cfg a deja ete charge depuis le .json si il existait
            self.cfg["encrypt_cfg"] = True
            save_cfg(self.cfg)
            # Supprimer le .json clair s'il existe encore
            if CONFIG_FILE.exists():
                try:
                    CONFIG_FILE.unlink(missing_ok=True)
                except Exception:
                    pass
            self._log("  Mot de passe maitre cree — config migree et chiffree ✓", "ok")
            if CONFIG_FILE.exists():
                self._log("  Ancien fichier .json supprime ✓", "ok")
        else:
            # ── Lancements suivants ───────────────────────────────────────────
            pw = self._ask_master_password(
                confirm=False,
                title="Config chiffree — Mot de passe requis")
            if pw is None:
                self._encrypt_cfg_enabled = False
                _SESSION_MASTER_PW[0] = None
                self._log("  Mot de passe annule — config par defaut chargee.", "err")
                return
            _SESSION_MASTER_PW[0] = pw
            self._encrypt_cfg_enabled = True
            # Dechiffrer la config — bloquer les callbacks pendant le rechargement
            new_cfg = load_cfg()
            if new_cfg.get("encrypt_cfg") or new_cfg != dict(DEFAULTS):
                # Rechargement reussi : repeupler l'UI sans declencher autosave
                self._loading = True
                self.cfg = new_cfg
                try:
                    self._load()
                finally:
                    self._loading = False
                self._log("  Config chiffree chargee ✓", "ok")
            else:
                # Dechiffrement echoue → mauvais mot de passe
                _SESSION_MASTER_PW[0] = None
                self._encrypt_cfg_enabled = False
                messagebox.showerror(
                    "Mot de passe incorrect",
                    "Impossible de dechiffrer la config.\n"
                    "Verifiez le mot de passe ou supprimez .blackflag_config.enc\n"
                    "pour repartir d'une config vierge.")

    def _center(self):
        self.root.update_idletasks()
        w, h   = self.root.winfo_width(), self.root.winfo_height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw-w)//2}+{max(0, (sh-h)//2 - 75)}")

    # ══════════════════════════════════════════════════════════════════════════
    def _build(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)   # logo
        self.root.rowconfigure(1, weight=1)   # log
        self.root.rowconfigure(2, weight=0)   # panneau fixe
        self.root.rowconfigure(3, weight=0)   # bottom bar

        self._build_logo()
        self._build_log()
        self._build_main()
        self._build_bottom()
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    # ── Logo centré ───────────────────────────────────────────────────────────
    def _build_logo(self):
        f = tk.Frame(self.root, bg=C["bg"])
        f.grid(row=0, column=0, sticky="ew", padx=14, pady=(8, 0))
        f.columnconfigure(0, weight=1)

        self._logo_lbl = tk.Label(
            f, text=ASCII_LOGO,
            font=("Courier New", 7),
            bg=C["bg"], fg=C["gold"],
            justify="center", anchor="center")
        self._logo_lbl.grid(row=0, column=0, sticky="ew")

        self._subtitle_lbl = tk.Label(
            f, text="",
            font=("Courier New", 8, "italic"),
            bg=C["bg"], fg=C["gold_dim"],
            anchor="center", justify="center")
        self._subtitle_lbl.grid(row=1, column=0, sticky="ew")

        tk.Frame(f, bg=C["gold_dim"], height=1).grid(
            row=2, column=0, sticky="ew", pady=(5, 0))

    # ── Journal de bord ───────────────────────────────────────────────────────
    def _build_log(self):
        f = tk.Frame(self.root, bg=C["bg"])
        f.grid(row=1, column=0, sticky="nsew", padx=14, pady=(6, 0))
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        hdr = tk.Frame(f, bg=C["bg"])
        hdr.grid(row=0, column=0, sticky="ew")

        self._lbl_log_header = tk.Label(
            hdr, text="", font=FB, bg=C["bg"], fg=C["gold"], anchor="w")
        self._lbl_log_header.pack(side="left")

        # Étiquette "Mise à jour disponible" — cachée par défaut
        self._lbl_update = tk.Label(
            hdr, text="", font=FM8,
            bg=C["bg"], fg=C["green"],
            cursor="hand2")
        self._lbl_update.pack(side="left", padx=(10, 0))
        self._lbl_update.bind("<Button-1>", lambda e: __import__("webbrowser").open(_UPDATE_PAGE))
        self._lbl_update.pack_forget()   # invisible jusqu'à détection MAJ

        # ── Boutons header — tous justifiés à droite ──────────────────────
        # Ordre d'ajout inversé pour pack(side="right") :
        # dernier ajouté = le plus à droite visuellement
        # Résultat : [Effacer log]  [Historique des uploads]  ▶  ⏭  ■

        # ■ (le plus à droite)
        self._music_playing = False
        self._music_ready   = False
        self._music_idx     = 0

        self._btn_music_stop = tk.Button(
            hdr, text="■", font=FM8, bg=C["panel"], fg=C["muted"],
            relief="flat", bd=0, padx=6, cursor="hand2",
            command=self._stop_music,
            highlightthickness=1, highlightbackground=C["border"])
        self._btn_music_stop.pack(side="right", pady=1, padx=(0, 0))

        # ⏭
        self._btn_music_next = tk.Button(
            hdr, text="⏭", font=FM8, bg=C["panel"], fg=C["muted"],
            relief="flat", bd=0, padx=6, cursor="hand2",
            command=self._next_music,
            highlightthickness=1, highlightbackground=C["border"])
        self._btn_music_next.pack(side="right", pady=1, padx=(0, 2))

        # ▶
        self._btn_music_play = tk.Button(
            hdr, text="▶", font=FM8, bg=C["panel"], fg=C["gold_dim"],
            relief="flat", bd=0, padx=6, cursor="hand2",
            command=self._play_music,
            highlightthickness=1, highlightbackground=C["border"])
        self._btn_music_play.pack(side="right", pady=1, padx=(0, 2))

        # [Historique des uploads]
        self._btn_history = tk.Button(
            hdr, text="", font=FM8, bg=C["panel"], fg=C["gold_dim"],
            relief="flat", bd=0, padx=8, cursor="hand2",
            command=self._show_history,
            highlightthickness=1, highlightbackground=C["border"])
        self._btn_history.pack(side="right", pady=1, padx=(0, 6))

        # [Effacer log]
        self._btn_clear_log = tk.Button(
            hdr, text="", font=FM8, bg=C["panel"], fg=C["muted"],
            relief="flat", bd=0, padx=6, cursor="hand2",
            command=self._clear_log,
            highlightthickness=1, highlightbackground=C["border"])
        self._btn_clear_log.pack(side="right", pady=1)

        # Zone de log avec SlimScrollbar
        log_frame = tk.Frame(f, bg=C["bg"])
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_box = tk.Text(
            log_frame, bg=C["ibg"], fg=C["text"], font=FM8, height=10,
            state="disabled", relief="flat", bd=0,
            highlightthickness=1, highlightbackground=C["border"], wrap="word",
            cursor="arrow", yscrollcommand=lambda *a: _log_vsb.set(*a))
        self.log_box.grid(row=0, column=0, sticky="nsew")

        _log_vsb = SlimScrollbar(log_frame, command=self.log_box.yview)
        _log_vsb.grid(row=0, column=1, sticky="ns")
        self.log_box.configure(yscrollcommand=_log_vsb.set)

        for tag, col in [("ok", C["green"]), ("err", C["red"]),
                         ("gold", C["gold"]), ("muted", C["muted"]),
                         ("dup", C["cyan"])]:
            self.log_box.tag_config(tag, foreground=col)
        self.log_box.bind("<Button-1>", lambda e: self.log_box.config(state="normal") or
                          self.log_box.after(0, lambda: self.log_box.config(state="disabled")))
        self.log_box.bind("<Button-3>", self._on_log_right_click)

        # Préparer le fichier audio en arrière-plan
        threading.Thread(target=self._prepare_music, daemon=True).start()

    # ── Panneau fixe (sources + toggle settings) ──────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════
    # LECTEUR AUDIO — Playlist pirate
    # ══════════════════════════════════════════════════════════════════════════
    def _prepare_music(self):
        """Télécharge les morceaux un par un.
        Lance le play automatiquement dès que le premier est disponible,
        continue à télécharger les suivants en arrière-plan."""
        if not _PYGAME_OK:
            return
        MUSIC_DIR.mkdir(parents=True, exist_ok=True)
        first_played = False

        for fname, url in PLAYLIST:
            dest = MUSIC_DIR / fname
            # Télécharger si absent
            if not dest.exists():
                try:
                    r = requests.get(url, timeout=30,
                                     headers={"User-Agent":
                                              "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                    if r.status_code == 200 and len(r.content) > 10_000:
                        dest.write_bytes(r.content)
                    else:
                        continue   # échec — passer au suivant
                except Exception:
                    continue       # réseau KO — passer au suivant

            # Premier morceau disponible → initialiser pygame et lancer le play
            if not first_played:
                try:
                    pygame.mixer.init()
                    self._music_ready = True
                    self._music_idx   = 0   # commence toujours par le premier
                    self.root.after(0, self._on_first_track_ready)
                    first_played = True
                except Exception:
                    pass

        # Mettre à jour les boutons next une fois tous les morceaux prêts
        self.root.after(0, lambda: self._btn_music_next.config(
            fg=C["gold_dim"], highlightbackground=C["gold_dim"]))

    def _on_first_track_ready(self):
        """Appelé dans le thread UI quand le premier morceau est prêt."""
        pygame.mixer.music.set_volume(0.5)   # volume à 50%
        self._btn_music_play.config(fg=C["gold"],
                                     highlightbackground=C["gold_dim"])
        # Pas d'autoplay — l'utilisateur lance manuellement

    def _available_tracks(self):
        """Retourne la liste des fichiers téléchargés dans l'ordre de la playlist."""
        return [MUSIC_DIR / fname for fname, _ in PLAYLIST
                if (MUSIC_DIR / fname).exists()]

    def _play_music(self):
        if not _PYGAME_OK or not self._music_ready:
            return
        tracks = self._available_tracks()
        if not tracks:
            return
        self._music_idx = self._music_idx % len(tracks)
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(str(tracks[self._music_idx]))
            pygame.mixer.music.play()
            # Enchaîner automatiquement à la fin du morceau
            pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)
            self._music_playing = True
            self._btn_music_play.config(fg=C["green"],
                                         highlightbackground=C["green"])
            self._btn_music_stop.config(fg=C["red"],
                                         highlightbackground=C["red"])
            # Vérifier l'enchaînement toutes les secondes
            self._check_music_end()
        except Exception:
            pass

    def _check_music_end(self):
        """Vérifie si le morceau est terminé et passe au suivant."""
        if not self._music_playing:
            return
        try:
            if not pygame.mixer.music.get_busy():
                self._next_music()
                return
        except Exception:
            pass
        self.root.after(1000, self._check_music_end)

    def _next_music(self):
        """Passe au morceau suivant dans la playlist."""
        if not _PYGAME_OK or not self._music_ready:
            return
        tracks = self._available_tracks()
        if not tracks:
            return
        was_playing = self._music_playing
        self._music_idx = (self._music_idx + 1) % len(tracks)
        if was_playing:
            self._play_music()

    def _stop_music(self):
        if not _PYGAME_OK:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self._music_playing = False
        self._btn_music_play.config(fg=C["gold_dim"],
                                     highlightbackground=C["border"])
        self._btn_music_stop.config(fg=C["muted"],
                                     highlightbackground=C["border"])

    def _build_main(self):
        outer = tk.Frame(self.root, bg=C["bg"])
        outer.grid(row=2, column=0, sticky="ew", padx=14, pady=(6, 0))
        outer.columnconfigure(1, weight=1)
        outer.columnconfigure(3, minsize=90)   # largeur fixe pour aligner Grade/Max

        tk.Frame(outer, bg=C["gold_dim"], height=1).grid(
            row=0, column=0, columnspan=6, sticky="ew", pady=(0, 6))

        # ── Ligne Films : chemin + […] + "Grade :" + combo grade ─────────────
        lbl_films = tk.Label(outer, text="", font=FB, bg=C["bg"],
                             fg=C["gold"], anchor="w", width=10)
        lbl_films.grid(row=1, column=0, sticky="w", padx=(8, 0), pady=3)
        self._dyn_labels["row_label_films"] = (lbl_films, "films")

        self.vars["films_dir"] = tk.StringVar()
        tk.Entry(outer, textvariable=self.vars["films_dir"],
                 font=FM, bg=C["ibg"], fg=C["ifg"],
                 insertbackground=C["gold"], relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=C["border"], width=40
                 ).grid(row=1, column=1, sticky="ew", padx=4, pady=2)
        tk.Button(outer, text="…", font=FM8, bg=C["panel"], fg=C["gold_dim"],
                  relief="flat", bd=0, padx=5, cursor="hand2",
                  highlightthickness=1, highlightbackground=C["border"],
                  command=lambda: self._browse("films_dir")
                  ).grid(row=1, column=2, sticky="w", padx=(0, 6))

        # Grade Films
        lbl_grade_f = tk.Label(outer, text="Grade :", font=FL, bg=C["bg"], fg=C["muted"], anchor="w")
        lbl_grade_f.grid(row=1, column=3, sticky="w", padx=(8, 4))

        self.grade_film_var = tk.StringVar()
        self._grade_f_combo = self._make_combo_widget(outer, self.grade_film_var, get_grades(), width=22)
        self._grade_f_combo.grid(row=1, column=4, sticky="w", padx=(0, 4))
        self.grade_film_var.trace_add("write", self._on_grade_film)

        # Max Films (indépendant)
        self.vars["max_movies"] = tk.StringVar()
        tk.Entry(outer, textvariable=self.vars["max_movies"],
                 font=FM, bg=C["ibg"], fg=C["ifg"],
                 insertbackground=C["gold"], relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=C["border"], width=5
                 ).grid(row=1, column=5, sticky="w", padx=(0, 4))

        # ── Ligne Séries : chemin + […] + grade + max ────────────────────────
        lbl_series = tk.Label(outer, text="", font=FB, bg=C["bg"],
                              fg=C["gold"], anchor="w", width=10)
        lbl_series.grid(row=2, column=0, sticky="w", padx=(8, 0), pady=3)
        self._dyn_labels["row_label_series"] = (lbl_series, "series")

        self.vars["series_dir"] = tk.StringVar()
        tk.Entry(outer, textvariable=self.vars["series_dir"],
                 font=FM, bg=C["ibg"], fg=C["ifg"],
                 insertbackground=C["gold"], relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=C["border"], width=40
                 ).grid(row=2, column=1, sticky="ew", padx=4, pady=2)
        tk.Button(outer, text="…", font=FM8, bg=C["panel"], fg=C["gold_dim"],
                  relief="flat", bd=0, padx=5, cursor="hand2",
                  highlightthickness=1, highlightbackground=C["border"],
                  command=lambda: self._browse("series_dir")
                  ).grid(row=2, column=2, sticky="w", padx=(0, 6))

        # Grade Séries (indépendant)
        lbl_grade_s = tk.Label(outer, text="Grade :", font=FL, bg=C["bg"], fg=C["muted"], anchor="w")
        lbl_grade_s.grid(row=2, column=3, sticky="w", padx=(8, 4))
        self.grade_series_var = tk.StringVar()
        self._grade_s_combo = self._make_combo_widget(outer, self.grade_series_var, get_grades(), width=22)
        self._grade_s_combo.grid(row=2, column=4, sticky="w", padx=(0, 4))
        self.grade_series_var.trace_add("write", self._on_grade_series)

        # Max Séries (indépendant)
        self.vars["max_series"] = tk.StringVar()
        tk.Entry(outer, textvariable=self.vars["max_series"],
                 font=FM, bg=C["ibg"], fg=C["ifg"],
                 insertbackground=C["gold"], relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=C["border"], width=5
                 ).grid(row=2, column=5, sticky="w", padx=(0, 4))

        # ── Panneau paramètres avec Canvas scrollable ─────────────────────────
        self._settings_outer = tk.Frame(outer, bg=C["bg"])
        self._settings_outer.grid(row=3, column=0, columnspan=6,
                                   sticky="ew", pady=(4, 0))
        self._settings_outer.columnconfigure(0, weight=1)

        self._toggle_btn = tk.Button(
            self._settings_outer,
            text="", font=FB, bg=C["panel"], fg=C["gold_dim"],
            relief="flat", bd=0, padx=10, pady=4, anchor="w",
            cursor="hand2",
            highlightthickness=1, highlightbackground=C["border"],
            command=self._toggle_settings)
        self._toggle_btn.grid(row=0, column=0, sticky="ew", pady=(0, 2))

        # Canvas + scrollbar pour les paramètres
        self._settings_canvas_frame = tk.Frame(self._settings_outer, bg=C["bg"])
        # Ne pas grid ici — géré par _toggle_settings

        self._s_canvas = tk.Canvas(
            self._settings_canvas_frame, bg=C["bg"],
            highlightthickness=0, height=260)
        self._s_vsb = SlimScrollbar(
            self._settings_canvas_frame,
            command=self._s_canvas.yview)
        self._s_canvas.configure(yscrollcommand=self._s_vsb.set)
        self._s_vsb.pack(side="right", fill="y")
        self._s_canvas.pack(side="left", fill="both", expand=True)

        self._s_inner = tk.Frame(self._s_canvas, bg=C["bg"])
        self._s_win   = self._s_canvas.create_window(
            (0, 0), window=self._s_inner, anchor="nw")
        self._s_inner.bind("<Configure>", lambda e: self._s_canvas.configure(
            scrollregion=self._s_canvas.bbox("all")))
        self._s_canvas.bind("<Configure>", lambda e: self._s_canvas.itemconfig(
            self._s_win, width=e.width))

        # Scroll handler — compatible souris ET trackpad deux doigts (Windows)
        def _scroll(event):
            # Windows : delta est un multiple de 120
            # Trackpad deux doigts génère aussi <MouseWheel> mais avec des deltas plus petits
            if event.delta:
                self._s_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Binder récursivement sur TOUS les widgets enfants du panneau settings
        # car le trackpad envoie l'event sur le widget sous le curseur, pas sur le canvas
        def _bind_scroll_recursive(widget):
            widget.bind("<MouseWheel>", _scroll, add="+")
            for child in widget.winfo_children():
                _bind_scroll_recursive(child)

        self._s_canvas.bind("<MouseWheel>", _scroll)
        self._s_inner.bind("<MouseWheel>", _scroll)
        # On stocke la fonction pour la rappeler après _build_settings
        self._bind_scroll_recursive = _bind_scroll_recursive

        self._build_settings(self._s_inner)
        # Propager le binding à tous les widgets créés dans _build_settings
        self._bind_scroll_recursive(self._s_inner)

        self._settings_canvas_frame.columnconfigure(0, weight=1)

    def _film_row(self, parent, row, path_key, max_key, grade_attr, label_key, on_grade):
        lbl = tk.Label(parent, text="", font=FB, bg=C["bg"],
                       fg=C["gold"], anchor="w", width=10)
        lbl.grid(row=row, column=0, sticky="w", padx=(8, 0), pady=3)
        self._dyn_labels[f"row_label_{label_key}"] = (lbl, label_key)

        var = tk.StringVar(); self.vars[path_key] = var
        tk.Entry(parent, textvariable=var, font=FM, bg=C["ibg"], fg=C["ifg"],
                 insertbackground=C["gold"], relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=C["border"], width=36
                 ).grid(row=row, column=1, sticky="ew", padx=4, pady=2)

        tk.Button(parent, text="…", font=FM8, bg=C["panel"], fg=C["gold_dim"],
                  relief="flat", bd=0, padx=5, cursor="hand2",
                  highlightthickness=1, highlightbackground=C["border"],
                  command=lambda k=path_key: self._browse(k)
                  ).grid(row=row, column=2, sticky="w", padx=(0, 8))

        lbl_max = tk.Label(parent, text="", font=FL, bg=C["bg"], fg=C["muted"])
        lbl_max.grid(row=row, column=3, sticky="e", padx=(0, 4))
        self._dyn_labels[f"max_{row}"] = (lbl_max, "max")

        mvar = tk.StringVar(); self.vars[max_key] = mvar
        tk.Entry(parent, textvariable=mvar, font=FM, bg=C["ibg"], fg=C["ifg"],
                 insertbackground=C["gold"], relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=C["border"], width=4
                 ).grid(row=row, column=4, sticky="w", padx=(0, 4))

        gvar = tk.StringVar()
        setattr(self, grade_attr, gvar)
        self._mk_combo(parent, None, GRADES, row=row, col=5, width=20, extvar=gvar)
        gvar.trace_add("write", on_grade)

    def _mk_combo(self, parent, key, values, row, col, width=10, extvar=None):
        var = extvar
        if key:
            var = tk.StringVar(); self.vars[key] = var
        cb = self._make_combo_widget(parent, var, values, width)
        cb.grid(row=row, column=col, sticky="w", padx=4, pady=1)
        return cb

    def _make_combo_widget(self, parent, var, values, width=10):
        """Crée un Combobox avec le style BF et force la visibilité du texte sur Windows."""
        st = ttk.Style()
        st.theme_use("clam")
        st.configure("BF.TCombobox",
                     fieldbackground=C["ibg"], background=C["ibg"],
                     foreground=C["ifg"], selectbackground=C["ibg"],
                     selectforeground=C["gold"],
                     bordercolor=C["border"],
                     lightcolor=C["border"], darkcolor=C["border"],
                     borderwidth=1,
                     arrowcolor=C["gold"], insertcolor=C["ifg"],
                     relief="flat")
        st.map("BF.TCombobox",
               fieldbackground=[("readonly", C["ibg"])],
               foreground=[("readonly", C["ifg"]), ("disabled", C["muted"])],
               selectbackground=[("readonly", C["ibg"])],
               selectforeground=[("readonly", C["gold"])],
               bordercolor=[("readonly", C["border"]), ("focus", C["border"])],
               lightcolor=[("readonly", C["border"]), ("focus", C["border"])],
               darkcolor=[("readonly", C["border"]), ("focus", C["border"])])
        cb = ttk.Combobox(parent, textvariable=var, values=values,
                          width=width, style="BF.TCombobox", state="readonly")
        # Force le rafraîchissement du texte affiché après création
        def _force_display(*_):
            cb.configure(state="readonly")
        cb.bind("<<ComboboxSelected>>", _force_display)
        # Déclenche l'affichage initial après que le widget est rendu
        parent.after(50, lambda: var.set(var.get()))
        return cb

    def _toggle_settings(self):
        if self._settings_open:
            self._settings_canvas_frame.grid_remove()
            self._toggle_btn.config(text=t("btn_settings_open"))
            self._settings_open = False
        else:
            self._settings_canvas_frame.grid(row=1, column=0, sticky="ew")
            self._toggle_btn.config(text=t("btn_settings_close"))
            self._settings_open = True
        self.root.update_idletasks()

    # ── Paramètres (dans le canvas scrollable) ────────────────────────────────
    def _build_settings(self, p):
        p.columnconfigure(1, weight=1)

        # Référence pour relabelliser dynamiquement
        self._s_labels = {}   # clé_T → Label widget

        def sec(r, key):
            lbl = tk.Label(p, text="", font=FB, bg=C["bg"],
                           fg=C["gold"], anchor="w")
            lbl.grid(row=r, column=0, columnspan=4, sticky="w", pady=(8, 0))
            self._s_labels[f"sec_{key}"] = (lbl, key)
            tk.Frame(p, bg=C["gold_dim"], height=1).grid(
                row=r, column=0, columnspan=4, sticky="ew", pady=(0, 3))
            return r + 1

        def row(r, label_key, cfg_key, show=None, w=36, tip_key=None):
            lbl = tk.Label(p, text="", font=FL, bg=C["bg"], fg=C["muted"],
                           anchor="w", width=24)
            lbl.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=1)
            self._s_labels[f"row_{label_key}"] = (lbl, label_key)
            var = tk.StringVar(); self.vars[cfg_key] = var
            kw  = dict(textvariable=var, font=FM, bg=C["ibg"], fg=C["ifg"],
                       insertbackground=C["gold"], relief="flat", bd=0,
                       highlightthickness=1, highlightbackground=C["border"], width=w)
            if show: kw["show"] = show
            tk.Entry(p, **kw).grid(row=r, column=1, sticky="ew", padx=4, pady=1)
            if tip_key:
                tip_lbl = tk.Label(p, text="", font=FM8, bg=C["bg"], fg=C["muted"])
                tip_lbl.grid(row=r, column=2, sticky="w")
                self._s_labels[f"tip_{tip_key}"] = (tip_lbl, tip_key)
            return r + 1

        def link(r, key, url):
            lbl = tk.Label(p, text="", font=("Courier New", 8, "underline"),
                           bg=C["bg"], fg=C["gold_dim"], cursor="hand2", anchor="w")
            lbl.grid(row=r, column=0, columnspan=4, sticky="w", padx=8)
            lbl.bind("<Button-1>", lambda e, u=url: __import__("webbrowser").open(u))
            self._s_labels[f"link_{key}"] = (lbl, key)
            return r + 1

        r = 0

        # ── Langue interface + Thème interface (même ligne) ─────────────────
        lbl_ul = tk.Label(p, text="", font=FL, bg=C["bg"], fg=C["muted"],
                           anchor="w", width=24)
        lbl_ul.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=(6, 4))
        self._s_labels["row_lbl_ui_lang"] = (lbl_ul, "lbl_ui_lang")

        # Frame inline colonne 1 : combo langue + label thème + combo thème collés
        _lang_theme_frame = tk.Frame(p, bg=C["bg"])
        _lang_theme_frame.grid(row=r, column=1, sticky="w", pady=(6, 4))

        self.vars["ui_lang"] = tk.StringVar()
        self._ui_lang_combo = self._make_combo_widget(
            _lang_theme_frame, self.vars["ui_lang"], list(LANGS_UI.keys()), width=10)
        self._ui_lang_combo.pack(side="left", padx=(4, 0))
        self.vars["ui_lang"].trace_add("write", self._on_ui_lang_change)

        # Label thème — texte fixe, pas dans _s_labels (pas de traduction)
        tk.Label(_lang_theme_frame, text="     Thème d'interface :", font=FL,
                 bg=C["bg"], fg=C["muted"]).pack(side="left")

        # Combo thème — collé au label
        self.vars["ui_theme"] = tk.StringVar()
        self._ui_theme_combo = self._make_combo_widget(
            _lang_theme_frame, self.vars["ui_theme"],
            list(THEME_NAMES.values()), width=14)
        self._ui_theme_combo.pack(side="left", padx=(4, 0))
        self.vars["ui_theme"].trace_add("write", self._on_ui_theme_change)
        r += 1

        # ── Section tracker : LA CALE ↔ TORR9 ───────────────────────────────
        # En-tête avec les deux boutons tracker (remplace le simple sec_lacale)
        tracker_hdr = tk.Frame(p, bg=C["bg"])
        tracker_hdr.grid(row=r, column=0, columnspan=4, sticky="w", pady=(8, 0))

        self._btn_tracker_lacale = tk.Button(
            tracker_hdr, text="LA CALE", font=FB,
            bg=C["panel"], relief="flat", bd=0, padx=10, pady=3,
            cursor="hand2", command=lambda: self._set_active_tracker("lacale"))
        self._btn_tracker_lacale.pack(side="left")

        self._btn_tracker_torr9 = tk.Button(
            tracker_hdr, text="TORR9", font=FB,
            bg=C["panel"], relief="flat", bd=0, padx=10, pady=3,
            cursor="hand2", command=lambda: self._set_active_tracker("torr9"))
        self._btn_tracker_torr9.pack(side="left", padx=(4, 0))

        # Bouton "+" inactif — Pour la v2.0
        btn_future = tk.Label(
            tracker_hdr, text="  +  ", font=FB,
            bg=C["panel"], fg=C["muted"],
            relief="flat", bd=0, padx=10, pady=3,
            cursor="arrow",
            highlightthickness=0)
        btn_future.pack(side="left", padx=(4, 0))
        self._add_tooltip(btn_future, "Pour la v2.0")

        tk.Frame(p, bg=C["gold_dim"], height=1).grid(
            row=r, column=0, columnspan=4, sticky="ew", pady=(0, 3))
        r += 1

        # ── Champs LA CALE ────────────────────────────────────────────────
        self._lacale_rows = []

        lbl_lcurl = tk.Label(p, text="", font=FL, bg=C["bg"], fg=C["muted"],
                             anchor="w", width=24)
        lbl_lcurl.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=1)
        self._s_labels["row_lbl_lacale_url"] = (lbl_lcurl, "lbl_lacale_url")
        self.vars["lacale_url"] = tk.StringVar()
        lc_url_entry = tk.Entry(p, textvariable=self.vars["lacale_url"], font=FM,
                                bg=C["ibg"], fg=C["ifg"], insertbackground=C["gold"],
                                relief="flat", bd=0, highlightthickness=1,
                                highlightbackground=C["border"], width=38)
        lc_url_entry.grid(row=r, column=1, sticky="ew", padx=4, pady=1)
        self._lacale_rows.extend([lbl_lcurl, lc_url_entry])
        r += 1

        # ── Frame API (passkey) ───────────────────────────────────────────
        self._frame_api = tk.Frame(p, bg=C["bg"])
        self._frame_api.grid(row=r, column=0, columnspan=4, sticky="ew")
        self._lacale_rows.append(self._frame_api)

        lbl_pk = tk.Label(self._frame_api, text="", font=FL, bg=C["bg"],
                          fg=C["muted"], anchor="w", width=24)
        lbl_pk.grid(row=0, column=0, sticky="w", padx=(8, 0), pady=1)
        self._s_labels["row_lbl_passkey"] = (lbl_pk, "lbl_passkey")
        self.vars["lacale_passkey"] = tk.StringVar()
        pk_entry = tk.Entry(self._frame_api, textvariable=self.vars["lacale_passkey"],
                            show="*", font=FM, bg=C["ibg"], fg=C["ifg"],
                            insertbackground=C["gold"], relief="flat", bd=0,
                            highlightthickness=1, highlightbackground=C["border"], width=38)
        pk_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=1)
        self._frame_api.columnconfigure(1, weight=1)
        pk_link = tk.Label(self._frame_api, text="", font=("Courier New", 8, "underline"),
                           bg=C["bg"], fg=C["gold_dim"], cursor="hand2")
        pk_link.grid(row=0, column=2, sticky="w")
        pk_link.bind("<Button-1>", lambda e: __import__("webbrowser").open(
            "https://la-cale.space/settings/api-keys"))
        self._s_labels["lbl_passkey_hint_lbl"] = (pk_link, "lbl_passkey_hint")
        r += 1

        # ── Frame Web (email + pass La Cale) ──────────────────────────────
        self._frame_web = tk.Frame(p, bg=C["bg"])
        self._frame_web.grid(row=r, column=0, columnspan=4, sticky="ew")
        self._lacale_rows.append(self._frame_web)

        lbl_em = tk.Label(self._frame_web, text="", font=FL, bg=C["bg"],
                          fg=C["muted"], anchor="w", width=24)
        lbl_em.grid(row=0, column=0, sticky="w", padx=(8, 0), pady=1)
        self._s_labels["row_lbl_email"] = (lbl_em, "lbl_email")
        self.vars["lacale_user"] = tk.StringVar()
        tk.Entry(self._frame_web, textvariable=self.vars["lacale_user"],
                 font=FM, bg=C["ibg"], fg=C["ifg"],
                 insertbackground=C["gold"], relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=C["border"], width=30
                 ).grid(row=0, column=1, sticky="w", padx=4, pady=1)

        lbl_pw = tk.Label(self._frame_web, text="", font=FL, bg=C["bg"],
                          fg=C["muted"], anchor="w", width=24)
        lbl_pw.grid(row=1, column=0, sticky="w", padx=(8, 0), pady=1)
        self._s_labels["row_lbl_pass"] = (lbl_pw, "lbl_pass")
        self.vars["lacale_pass"] = tk.StringVar()
        tk.Entry(self._frame_web, textvariable=self.vars["lacale_pass"],
                 show="*", font=FM, bg=C["ibg"], fg=C["ifg"],
                 insertbackground=C["gold"], relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=C["border"], width=24
                 ).grid(row=1, column=1, sticky="w", padx=4, pady=1)
        r += 1

        lbl_tr = tk.Label(p, text="", font=FL, bg=C["bg"], fg=C["muted"],
                          anchor="w", width=24)
        lbl_tr.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=1)
        self._s_labels["row_lbl_tracker"] = (lbl_tr, "lbl_tracker")
        self.vars["tracker_url"] = tk.StringVar()
        lc_tr_entry = tk.Entry(p, textvariable=self.vars["tracker_url"], font=FM,
                               bg=C["ibg"], fg=C["ifg"], insertbackground=C["gold"],
                               relief="flat", bd=0, highlightthickness=1,
                               highlightbackground=C["border"], width=52)
        lc_tr_entry.grid(row=r, column=1, sticky="ew", padx=4, pady=1)
        self._lacale_rows.extend([lbl_tr, lc_tr_entry])
        r += 1

        # Appliquer la visibilité initiale selon le mode courant
        p.after(10, self._update_conn_btn)

        # ── Champs TORR9 ──────────────────────────────────────────────────
        self._torr9_rows = []

        def torr9_row(r, label_txt, cfg_key, show=None, w=36, placeholder=None):
            lbl = tk.Label(p, text=label_txt, font=FL, bg=C["bg"],
                           fg=C["muted"], anchor="w", width=24)
            lbl.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=1)
            var = tk.StringVar(); self.vars[cfg_key] = var
            e = tk.Entry(p, textvariable=var, font=FM, show=show or "",
                         bg=C["ibg"], fg=C["ifg"], insertbackground=C["gold"],
                         relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=C["border"], width=w)
            e.grid(row=r, column=1, sticky="ew", padx=4, pady=1)
            if placeholder:
                def _update_color(*_):
                    e.config(fg=C["muted"] if var.get() == placeholder else C["ifg"])
                var.trace_add("write", _update_color)
                _update_color()
            self._torr9_rows.extend([lbl, e])
            return r + 1

        r = torr9_row(r, "Torr9 URL :",    "torr9_url",  w=38,
                      placeholder="https://torr9.net/upload")
        r = torr9_row(r, "Pseudonyme :",   "torr9_user", w=30)
        r = torr9_row(r, "Mot de passe :", "torr9_pass", show="*", w=24)

        # ── Champ Token API + bouton Récupérer ───────────────────────────────
        lbl_tok = tk.Label(p, text="Token API :", font=FL, bg=C["bg"],
                           fg=C["muted"], anchor="w", width=24)
        lbl_tok.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=1)
        self.vars["torr9_token"] = tk.StringVar()
        tok_entry = tk.Entry(p, textvariable=self.vars["torr9_token"],
                             font=FM,
                             bg=C["ibg"], fg=C["ifg"], insertbackground=C["gold"],
                             relief="flat", bd=0, highlightthickness=1,
                             highlightbackground=C["border"], width=36)
        tok_entry.grid(row=r, column=1, sticky="ew", padx=4, pady=1)
        self._btn_torr9_token = tk.Button(
            p, text="↺ Récupérer", font=FM8,
            bg=C["panel"], fg=C["gold_dim"],
            relief="flat", bd=0, padx=6, pady=2, cursor="hand2",
            highlightthickness=1, highlightbackground=C["border"],
            command=self._fetch_torr9_token)
        self._btn_torr9_token.grid(row=r, column=2, sticky="w", padx=(0, 4), pady=1)
        self._torr9_rows.extend([lbl_tok, tok_entry, self._btn_torr9_token])
        r += 1

        # ── Champ URL de publication + bouton Récupérer ───────────────────────
        lbl_ann = tk.Label(p, text="URL de publication :", font=FL, bg=C["bg"],
                           fg=C["muted"], anchor="w", width=24)
        lbl_ann.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=1)
        self.vars["torr9_announce"] = tk.StringVar(
            value="https://tracker.torr9.net/announce/****A CHANGER****")
        ann_entry = tk.Entry(p, textvariable=self.vars["torr9_announce"],
                             font=FM, bg=C["ibg"], fg=C["ifg"],
                             insertbackground=C["gold"],
                             relief="flat", bd=0, highlightthickness=1,
                             highlightbackground=C["border"], width=36)
        ann_entry.grid(row=r, column=1, sticky="ew", padx=4, pady=1)

        self._btn_torr9_fetch = tk.Button(
            p, text="↺ Récupérer", font=FM8,
            bg=C["panel"], fg=C["gold_dim"],
            relief="flat", bd=0, padx=6, pady=2, cursor="hand2",
            highlightthickness=1, highlightbackground=C["border"],
            command=self._fetch_torr9_announce)
        self._btn_torr9_fetch.grid(row=r, column=2, sticky="w", padx=(0, 4), pady=1)

        self._torr9_rows.extend([lbl_ann, ann_entry, self._btn_torr9_fetch])
        r += 1

        # Appliquer la visibilité tracker initiale
        p.after(12, self._update_tracker_fields)

        r = sec(r, "sec_tmdb")
        r = link(r, "tmdb_link", "https://www.themoviedb.org/settings/api")
        r = row(r, "lbl_tmdb_key",  "tmdb_token", show="*", w=50)

        # TMDb lang
        lbl_tl = tk.Label(p, text="", font=FL, bg=C["bg"], fg=C["muted"],
                           anchor="w", width=24)
        lbl_tl.grid(row=r, column=0, sticky="w", padx=(8, 0))
        self._s_labels["row_lbl_tmdb_lang"] = (lbl_tl, "lbl_tmdb_lang")
        self.vars["tmdb_lang"] = tk.StringVar()
        self._make_combo_widget(
            p, self.vars["tmdb_lang"],
            ["fr-FR","en-US","de-DE","es-ES","it-IT","pt-PT"], width=10
        ).grid(row=r, column=1, sticky="w", padx=4)
        r += 1

        # ── Lien Windows MediaInfo.dll ────────────────────────────────────────
        lbl_mi_link = tk.Label(
            p, text="WINDOWS: Fichier MediaInfo.dll → mediaarea.net/en/MediaInfo/Download/Windows",
            font=("Courier New", 8, "underline"),
            bg=C["bg"], fg=C["gold_dim"], cursor="hand2", anchor="w")
        lbl_mi_link.grid(row=r, column=0, columnspan=4, sticky="w", padx=8)
        lbl_mi_link.bind("<Button-1>", lambda e: __import__("webbrowser").open(
            "https://mediaarea.net/en/MediaInfo/Download/Windows"))
        r += 1

        # ── Champ MediaInfo.dll (Windows) ────────────────────────────────────
        def _make_mi_row(row, label_txt, cfg_key, default_name, browse_title, filetypes):
            lbl = tk.Label(p, text=label_txt, font=FL,
                           bg=C["bg"], fg=C["muted"], anchor="w", width=24)
            lbl.grid(row=row, column=0, sticky="w", padx=(8, 0), pady=1)

            fr = tk.Frame(p, bg=C["bg"])
            fr.grid(row=row, column=1, columnspan=3, sticky="ew", padx=4, pady=1)
            fr.columnconfigure(0, weight=1)  # entry s'étire

            default_val = str(APP_DIR / default_name)
            var = tk.StringVar(value=default_val)
            self.vars[cfg_key] = var

            entry = tk.Entry(fr, textvariable=var, font=FM,
                             bg=C["ibg"], fg=C["muted"],
                             insertbackground=C["gold"], relief="flat", bd=0,
                             highlightthickness=1, highlightbackground=C["border"])
            entry.grid(row=0, column=0, sticky="ew", padx=(0, 2))

            def _update_color(*_):
                from pathlib import Path as _P
                entry.config(fg=C["muted"] if var.get() == default_val else C["ifg"])
            var.trace_add("write", _update_color)

            def _check(sl_ref=[], v=var):
                from pathlib import Path as _P
                sl = sl_ref[0] if sl_ref else None
                if sl is None: return
                if _P(v.get().strip()).exists():
                    sl.config(text="● Chargé", fg=C["green"])
                else:
                    sl.config(text="● Manquant", fg=C["red"])

            def _browse(v=var, c=_check):
                from tkinter import filedialog
                path = filedialog.askopenfilename(
                    title=browse_title, filetypes=filetypes,
                    initialdir=str(APP_DIR))
                if path:
                    v.set(path); c()

            tk.Button(fr, text="…", font=FM8, bg=C["panel"], fg=C["gold_dim"],
                      relief="flat", bd=0, padx=5, cursor="hand2",
                      highlightthickness=1, highlightbackground=C["border"],
                      command=_browse
                      ).grid(row=0, column=1, padx=(0, 2), sticky="w")

            status_lbl = tk.Label(fr, text="", font=FM8, bg=C["bg"], width=9, anchor="w")
            status_lbl.grid(row=0, column=2, sticky="w", padx=(0, 2))

            # Patch _check pour accéder au status_lbl après création
            _sl_ref = [status_lbl]
            def _check_real(sl=status_lbl, v=var):
                from pathlib import Path as _P
                if _P(v.get().strip()).exists():
                    sl.config(text="● Chargé",   fg=C["green"])
                else:
                    sl.config(text="● Manquant", fg=C["red"])

            tk.Button(fr, text="↺", font=FM8, bg=C["panel"], fg=C["gold_dim"],
                      relief="flat", bd=0, padx=5, pady=2, cursor="hand2",
                      highlightthickness=1, highlightbackground=C["border"],
                      command=_check_real
                      ).grid(row=0, column=3, sticky="w", padx=(0, 0))

            p.after(200, _check_real)
            return row + 1

        r = _make_mi_row(r,
            "Fichier MediaInfo.dll :", "mediainfo_dll", "MediaInfo.dll",
            "Sélectionner MediaInfo.dll",
            [("DLL", "*.dll"), ("Tous", "*.*")])

        # ── Lien macOS libmediainfo.dylib ─────────────────────────────────────
        lbl_dylib_link = tk.Label(
            p, text="macOS: Fichier libmediainfo.dylib → mediaarea.net/en/MediaInfo/Download/Mac_OS",
            font=("Courier New", 8, "underline"),
            bg=C["bg"], fg=C["gold_dim"], cursor="hand2", anchor="w")
        lbl_dylib_link.grid(row=r, column=0, columnspan=4, sticky="w", padx=8)
        lbl_dylib_link.bind("<Button-1>", lambda e: __import__("webbrowser").open(
            "https://mediaarea.net/en/MediaInfo/Download/Mac_OS"))
        r += 1

        # ── Champ libmediainfo.dylib (macOS) ──────────────────────────────────
        r = _make_mi_row(r,
            "Fichier .dylib :", "mediainfo_dylib", "libmediainfo.dylib",
            "Sélectionner libmediainfo.dylib",
            [("dylib", "*.dylib"), ("Tous", "*.*")])

        # ── Lien Linux libmediainfo.so ────────────────────────────────────────
        lbl_so_link = tk.Label(
            p, text="Linux: Fichier libmediainfo.so → mediaarea.net/en/MediaInfo/Download/Ubuntu",
            font=("Courier New", 8, "underline"),
            bg=C["bg"], fg=C["gold_dim"], cursor="hand2", anchor="w")
        lbl_so_link.grid(row=r, column=0, columnspan=4, sticky="w", padx=8)
        lbl_so_link.bind("<Button-1>", lambda e: __import__("webbrowser").open(
            "https://mediaarea.net/en/MediaInfo/Download/Ubuntu"))
        r += 1

        # ── Champ libmediainfo.so (Linux) ─────────────────────────────────────
        r = _make_mi_row(r,
            "Fichier .so :", "mediainfo_so", "libmediainfo.so",
            "Sélectionner libmediainfo.so",
            [("so", "*.so*"), ("Tous", "*.*")])

        # ── Toggle QB / Transmission ──────────────────────────────────────
        # Ligne de titre avec les deux boutons côte à côte
        self._torrent_client = self.cfg.get("torrent_client", "qbittorrent")

        hdr_frame = tk.Frame(p, bg=C["bg"])
        hdr_frame.grid(row=r, column=0, columnspan=4, sticky="w", pady=(8, 0))

        self._btn_client_qb = tk.Button(
            hdr_frame, text="QBITTORRENT", font=FB,
            bg=C["panel"], relief="flat", bd=0, padx=10, pady=3,
            cursor="hand2", command=lambda: self._set_torrent_client("qbittorrent"))
        self._btn_client_qb.pack(side="left")

        self._btn_client_tr = tk.Button(
            hdr_frame, text="TRANSMISSION", font=FB,
            bg=C["panel"], relief="flat", bd=0, padx=10, pady=3,
            cursor="hand2", command=lambda: self._set_torrent_client("transmission"))
        self._btn_client_tr.pack(side="left", padx=(4, 0))

        self._btn_client_de = tk.Button(
            hdr_frame, text="DELUGE", font=FB,
            bg=C["panel"], relief="flat", bd=0, padx=10, pady=3,
            cursor="hand2", command=lambda: self._set_torrent_client("deluge"))
        self._btn_client_de.pack(side="left", padx=(4, 0))

        self._btn_client_vz = tk.Button(
            hdr_frame, text="VUZE", font=FB,
            bg=C["panel"], relief="flat", bd=0, padx=10, pady=3,
            cursor="hand2", command=lambda: self._set_torrent_client("vuze"))
        self._btn_client_vz.pack(side="left", padx=(4, 0))

        tk.Frame(p, bg=C["gold_dim"], height=1).grid(
            row=r, column=0, columnspan=4, sticky="ew", pady=(0, 3))
        r += 1

        # ── Champs QBITTORRENT ────────────────────────────────────────────
        self._qb_rows = []

        def qb_row(r, label_key, cfg_key, show=None, w=36, tip_key=None):
            lbl = tk.Label(p, text=t(label_key), font=FL, bg=C["bg"],
                           fg=C["muted"], anchor="w", width=24)
            lbl.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=1)
            self._s_labels[f"qb_{label_key}"] = (lbl, label_key)
            var = tk.StringVar(); self.vars[cfg_key] = var
            e = tk.Entry(p, textvariable=var, font=FM, show=show or "",
                         bg=C["ibg"], fg=C["ifg"], insertbackground=C["gold"],
                         relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=C["border"], width=w)
            e.grid(row=r, column=1, sticky="ew", padx=4, pady=1)
            self._qb_rows.extend([lbl, e])
            if tip_key:
                tip = tk.Label(p, text=t(tip_key), font=FM8,
                               bg=C["bg"], fg=C["muted"])
                tip.grid(row=r, column=2, sticky="w")
                self._qb_rows.append(tip)
            return r + 1

        r = qb_row(r, "lbl_qb_url",   "qb_url",       w=32, tip_key="tip_qb_url")
        r = qb_row(r, "lbl_qb_user",  "qb_user",      w=16)
        r = qb_row(r, "lbl_qb_pass",  "qb_pass",      show="*", w=20)
        r = qb_row(r, "lbl_qb_films", "qb_films_path", w=30, tip_key="tip_qb_path")

        lbl_ser = tk.Label(p, text=t("lbl_qb_series"), font=FL, bg=C["bg"],
                           fg=C["muted"], anchor="w", width=24)
        lbl_ser.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=1)
        self._s_labels["row_lbl_qb_series"] = (lbl_ser, "lbl_qb_series")
        self.vars["qb_series_path"] = tk.StringVar()
        qb_ser_entry = tk.Entry(p, textvariable=self.vars["qb_series_path"], font=FM,
                 bg=C["ibg"], fg=C["ifg"], insertbackground=C["gold"],
                 relief="flat", bd=0, highlightthickness=1,
                 highlightbackground=C["border"], width=30)
        qb_ser_entry.grid(row=r, column=1, sticky="ew", padx=4, pady=1)
        self._btn_qb_fetch = tk.Button(
            p, text="", font=FM8,
            bg=C["panel"], fg=C["gold_dim"],
            relief="flat", bd=0, padx=6, cursor="hand2",
            highlightthickness=1, highlightbackground=C["border"],
            command=self._fetch_qb_paths)
        self._btn_qb_fetch.grid(row=r, column=2, sticky="w", padx=(0, 4), pady=1)
        self._s_labels["btn_qb_fetch"] = (self._btn_qb_fetch, "btn_qb_fetch")
        self._qb_rows.extend([lbl_ser, qb_ser_entry, self._btn_qb_fetch])
        r += 1

        # ── Champs TRANSMISSION ───────────────────────────────────────────
        self._tr_rows = []

        def tr_row(r, label_key, cfg_key, show=None, w=36, tip_key=None):
            lbl = tk.Label(p, text=t(label_key), font=FL, bg=C["bg"],
                           fg=C["muted"], anchor="w", width=24)
            lbl.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=1)
            self._s_labels[f"tr_{label_key}"] = (lbl, label_key)
            var = tk.StringVar(); self.vars[cfg_key] = var
            e = tk.Entry(p, textvariable=var, font=FM, show=show or "",
                         bg=C["ibg"], fg=C["ifg"], insertbackground=C["gold"],
                         relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=C["border"], width=w)
            e.grid(row=r, column=1, sticky="ew", padx=4, pady=1)
            self._tr_rows.extend([lbl, e])
            if tip_key:
                tip = tk.Label(p, text=t(tip_key), font=FM8,
                               bg=C["bg"], fg=C["muted"])
                tip.grid(row=r, column=2, sticky="w")
                self._tr_rows.append(tip)
            return r + 1

        r = tr_row(r, "lbl_tr_url",    "tr_url",        w=32, tip_key="tip_tr_url")
        r = tr_row(r, "lbl_tr_user",   "tr_user",       w=16)
        r = tr_row(r, "lbl_tr_pass",   "tr_pass",       show="*", w=20)
        r = tr_row(r, "lbl_tr_films",  "tr_films_path", w=30)
        r = tr_row(r, "lbl_tr_series", "tr_series_path", w=30)

        # ── Champs DELUGE ────────────────────────────────────────────────
        self._de_rows = []

        def de_row(r, label_txt, cfg_key, show=None, w=36, tip_txt=None):
            lbl = tk.Label(p, text=label_txt, font=FL, bg=C["bg"],
                           fg=C["muted"], anchor="w", width=24)
            lbl.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=1)
            var = tk.StringVar(); self.vars[cfg_key] = var
            e = tk.Entry(p, textvariable=var, font=FM, show=show or "",
                         bg=C["ibg"], fg=C["ifg"], insertbackground=C["gold"],
                         relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=C["border"], width=w)
            e.grid(row=r, column=1, sticky="ew", padx=4, pady=1)
            self._de_rows.extend([lbl, e])
            if tip_txt:
                tip = tk.Label(p, text=tip_txt, font=FM8, bg=C["bg"], fg=C["muted"])
                tip.grid(row=r, column=2, sticky="w")
                self._de_rows.append(tip)
            return r + 1

        r = de_row(r, "URL Deluge :",        "deluge_url",          w=32,
                   tip_txt="ex: http://192.168.1.x:8112")
        r = de_row(r, "Mot de passe :",      "deluge_pass",         show="*", w=20)
        r = de_row(r, "Save path Films :",   "deluge_films_path",   w=30)
        r = de_row(r, "Save path Séries :",  "deluge_series_path",  w=30)

        # ── Champs VUZE ──────────────────────────────────────────────────
        self._vz_rows = []

        def vz_row(r, label_txt, cfg_key, show=None, w=36, tip_txt=None):
            lbl = tk.Label(p, text=label_txt, font=FL, bg=C["bg"],
                           fg=C["muted"], anchor="w", width=24)
            lbl.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=1)
            var = tk.StringVar(); self.vars[cfg_key] = var
            e = tk.Entry(p, textvariable=var, font=FM, show=show or "",
                         bg=C["ibg"], fg=C["ifg"], insertbackground=C["gold"],
                         relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=C["border"], width=w)
            e.grid(row=r, column=1, sticky="ew", padx=4, pady=1)
            self._vz_rows.extend([lbl, e])
            if tip_txt:
                tip = tk.Label(p, text=tip_txt, font=FM8, bg=C["bg"], fg=C["muted"])
                tip.grid(row=r, column=2, sticky="w")
                self._vz_rows.append(tip)
            return r + 1

        r = vz_row(r, "URL Vuze :",          "vuze_url",         w=32,
                   tip_txt="ex: http://192.168.1.x:9091")
        r = vz_row(r, "Utilisateur :",       "vuze_user",        w=16,
                   tip_txt="'vuze' par defaut")
        r = vz_row(r, "Code de pairing :",   "vuze_pass",        show="*", w=24,
                   tip_txt="Affiché dans le plugin Vuze Web Remote")
        r = vz_row(r, "Save path Films :",   "vuze_films_path",  w=30)
        r = vz_row(r, "Save path Series :",  "vuze_series_path", w=30)

        # Appliquer la visibilité initiale
        p.after(15, self._update_client_ui)

        r = sec(r, "sec_misc")
        r = row(r, "lbl_discord",  "discord_webhook", w=50)
        r = row(r, "lbl_torrents", "torrents_dir",    w=40)
        r = row(r, "lbl_delay",    "upload_delay",    w=5)

        # ── Logs + Curl toggles — alignés comme la ligne notification ────
        # Label "Sauvegarde des logs :" en column=0 (même que lbl_notify)
        lbl_sl_outer = tk.Label(p, text="", font=FL, bg=C["bg"], fg=C["muted"],
                                anchor="w", width=24)
        lbl_sl_outer.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=(6, 2))
        self._s_labels["lbl_save_logs_inline"] = (lbl_sl_outer, "lbl_save_logs")

        # Frame inline column=1 : toggle logs + séparateur + toggle curl + hint
        logs_curl_row = tk.Frame(p, bg=C["bg"])
        logs_curl_row.grid(row=r, column=1, columnspan=3, sticky="w", pady=(6, 2))

        # Toggle logs
        self._save_logs_enabled = bool(self.cfg.get("save_logs", False))
        self._btn_save_logs = tk.Button(
            logs_curl_row, text="", font=FB,
            bg=C["panel"], relief="flat", bd=0, padx=8, pady=3,
            cursor="hand2", command=self._toggle_save_logs)
        self._btn_save_logs.pack(side="left")

        # Séparateur 5 espaces
        tk.Label(logs_curl_row, text="     ", bg=C["bg"]).pack(side="left")

        # Label curl
        lbl_sc = tk.Label(logs_curl_row, text="", font=FL,
                          bg=C["bg"], fg=C["muted"])
        lbl_sc.pack(side="left", padx=(0, 4))
        self._s_labels["lbl_save_curl_inline"] = (lbl_sc, "lbl_save_curl")

        # Toggle curl
        self._save_curl_enabled = bool(self.cfg.get("save_curl", False))
        self._btn_save_curl = tk.Button(
            logs_curl_row, text="", font=FB,
            bg=C["panel"], relief="flat", bd=0, padx=8, pady=3,
            cursor="hand2", command=self._toggle_save_curl)
        self._btn_save_curl.pack(side="left")

        # Hint "(Sauvegardés dans le sous-dossier logs)"
        tk.Label(logs_curl_row, text="  (Sauvegardés dans le sous-dossier logs)",
                 font=FM8, bg=C["bg"], fg=C["muted"]).pack(side="left")
        r += 1

        # Appliquer l'état visuel initial des toggles
        p.after(25, self._refresh_logs_curl_ui)

        # ── Chiffrement de la configuration ──────────────────────────────────
        lbl_enc = tk.Label(p, text="Chiffrement config :", font=FL,
                           bg=C["bg"], fg=C["muted"], anchor="w", width=24)
        lbl_enc.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=(6, 2))

        enc_row = tk.Frame(p, bg=C["bg"])
        enc_row.grid(row=r, column=1, columnspan=3, sticky="w", pady=(6, 2))

        self._encrypt_cfg_enabled = bool(self.cfg.get("encrypt_cfg", True))
        self._btn_encrypt_cfg = tk.Button(
            enc_row, text="", font=FB,
            bg=C["panel"], relief="flat", bd=0, padx=8, pady=3,
            cursor="hand2", command=self._toggle_encrypt_cfg)
        self._btn_encrypt_cfg.pack(side="left")

        _enc_hint = "  (AES-256 via Fernet/PBKDF2 — mot de passe saisi au lancement)"
        if not _CRYPTO_OK:
            _enc_hint = "  ⚠ cryptography non installé — chiffrement indisponible"
        tk.Label(enc_row, text=_enc_hint, font=FM8,
                 bg=C["bg"], fg=C["muted"]).pack(side="left")
        r += 1
        p.after(30, self._refresh_encrypt_cfg_ui)

        # ── Notification HTTP 200 ─────────────────────────────────────────
        lbl_n = tk.Label(p, text="", font=FL, bg=C["bg"], fg=C["muted"],
                         anchor="w", width=24)
        lbl_n.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=(6, 2))
        self._s_labels["row_lbl_notify"] = (lbl_n, "lbl_notify")

        # Frame inline col 1 : toggle + intervalle + hint tous côte à côte
        notify_row = tk.Frame(p, bg=C["bg"])
        notify_row.grid(row=r, column=1, columnspan=3, sticky="w", pady=(6, 2))

        # Toggle ACTIF / NON ACTIF
        self._notify_enabled = bool(self.cfg.get("notify_enabled", False))
        self._btn_notify = tk.Button(
            notify_row, text="", font=FB,
            bg=C["panel"], relief="flat", bd=0, padx=8, pady=3,
            cursor="hand2", command=self._toggle_notify)
        self._btn_notify.pack(side="left")

        # Intervalle — juste à droite du toggle
        self._notify_interval_frame = tk.Frame(notify_row, bg=C["bg"])
        self._notify_interval_frame.pack(side="left", padx=(8, 0))

        self._lbl_notify_interval = tk.Label(
            self._notify_interval_frame, text="", font=FL,
            bg=C["bg"], fg=C["muted"])
        self._lbl_notify_interval.pack(side="left", padx=(0, 4))
        self._s_labels["row_lbl_notify_interval"] = (
            self._lbl_notify_interval, "lbl_notify_interval")

        self.vars["notify_interval"] = tk.StringVar()
        self._combo_notify_interval = self._make_combo_widget(
            self._notify_interval_frame,
            self.vars["notify_interval"],
            ["10", "20", "60"], width=5)
        self._combo_notify_interval.pack(side="left")

        tk.Label(self._notify_interval_frame, text="min",
                 font=FM8, bg=C["bg"], fg=C["muted"]
                 ).pack(side="left", padx=(4, 0))

        # Hint discret à droite
        lbl_hint = tk.Label(notify_row, text="", font=FM8,
                            bg=C["bg"], fg=C["muted"])
        lbl_hint.pack(side="left", padx=(12, 0))
        self._s_labels["notify_hint_lbl"] = (lbl_hint, "notify_hint")
        r += 1

        # Appliquer l'état visuel initial
        p.after(20, self._refresh_notify_ui)

        # ── Vérification des mises à jour ─────────────────────────────────
        lbl_cu = tk.Label(p, text="", font=FL, bg=C["bg"], fg=C["muted"],
                          anchor="w", width=24)
        lbl_cu.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=(6, 2))
        self._s_labels["row_lbl_check_updates"] = (lbl_cu, "lbl_check_updates")

        self._check_updates_enabled = bool(self.cfg.get("check_updates", True))
        self._seed_check_enabled = bool(self.cfg.get("seed_check", True))
        cu_frame = tk.Frame(p, bg=C["bg"])
        cu_frame.grid(row=r, column=1, columnspan=3, sticky="w", pady=(6, 2))

        self._btn_check_updates = tk.Button(
            cu_frame, text="", font=FB,
            bg=C["panel"], relief="flat", bd=0, padx=8, pady=3,
            cursor="hand2", command=self._toggle_check_updates)
        self._btn_check_updates.pack(side="left")

        tk.Label(cu_frame,
                 text="  (Vérifie sur Github du num. de version du raw en début de session)",
                 font=FM8, bg=C["bg"], fg=C["muted"]
                 ).pack(side="left")

        p.after(30, self._refresh_check_updates_ui)
        r += 1

        # ── Mise à jour automatique depuis GitHub (visible seulement si MAJ dispo) ─
        self._upd_sep = tk.Frame(p, bg=C["gold_dim"], height=1)
        self._upd_sep.grid(row=r, column=0, columnspan=4, sticky="ew", pady=(10, 6))
        r += 1

        self._upd_frame = tk.Frame(p, bg=C["bg"])
        self._upd_frame.grid(row=r, column=0, columnspan=4, sticky="w",
                              padx=(8, 0), pady=(0, 10))

        self._btn_self_update = tk.Button(
            self._upd_frame, text="⬇  Installer la dernière version (GitHub)", font=FB,
            bg=C["panel"], fg=C["gold"], relief="flat", bd=0,
            padx=12, pady=5, cursor="hand2",
            highlightthickness=1, highlightbackground=C["gold_dim"],
            command=self._self_update)
        self._btn_self_update.pack(side="left")

        tk.Label(self._upd_frame,
                 text="  Remplace le fichier .py courant puis relancez.",
                 font=FM8, bg=C["bg"], fg=C["muted"]).pack(side="left")
        r += 1

        # Masqué par défaut — affiché par _show_update_badge si MAJ détectée
        p.after(10, self._hide_update_install_btn)

    # ── Barre du bas ──────────────────────────────────────────────────────────
    def _build_bottom(self):
        f = tk.Frame(self.root, bg=C["bg"])
        f.grid(row=3, column=0, sticky="ew", padx=14, pady=(4, 10))
        f.columnconfigure(0, weight=1)

        # ── Row 0 : ligne supérieure avec champ suffixe + barre ──────────
        pf = tk.Frame(f, bg=C["bg"])
        pf.grid(row=0, column=0, columnspan=5, sticky="ew", pady=(0, 3))
        pf.columnconfigure(1, weight=1)

        # Champ texte suffixe (17 car., prérempli "_dev") — col 0, à gauche
        self._suffix_var = tk.StringVar(value="zone pour dev")
        tk.Entry(pf, textvariable=self._suffix_var, font=FM8,
                 bg=C["bg"], fg=C["bg"], insertbackground=C["bg"],
                 relief="flat", bd=0, width=17,
                 highlightthickness=1, highlightbackground=C["bg"]
                 ).grid(row=0, column=0, sticky="w", padx=(0, 6))

        # Label "Progression :" — col 2, au-dessus du bouton Effacer config
        # (affiché/masqué par _set_prog)
        self._lbl_prog_above = tk.Label(f, text="Progression :", font=FM8,
                                         bg=C["bg"], fg=C["muted"], anchor="w")
        self._lbl_prog_above.grid(row=0, column=2, sticky="sw", padx=4, pady=(0, 1))
        self._lbl_prog_above.grid_remove()

        # Barre — col 3, taille et position d'origine length=220, sticky="e"
        st = ttk.Style()
        st.configure("BF.Horizontal.TProgressbar",
                     troughcolor=C["border"], background=C["gold"],
                     bordercolor=C["border"], lightcolor=C["gold"], darkcolor=C["gold"])
        self.prog_bar = ttk.Progressbar(
            pf, style="BF.Horizontal.TProgressbar",
            length=220, mode="determinate")
        self.prog_bar.grid(row=0, column=2, sticky="e")

        # Label compteur + % — texte simple à gauche de la barre
        self.prog_lbl = tk.Label(pf, text="", font=FM8,
                                  bg=C["bg"], fg=C["muted"], anchor="e")
        self.prog_lbl.grid(row=0, column=1, sticky="e", padx=(0, 4))

        # ── Ligne boutons (row 1) ─────────────────────────────────────────
        status_frame = tk.Frame(f, bg=C["bg"])
        status_frame.grid(row=1, column=0, sticky="w")

        self._lbl_conn_mode = tk.Label(status_frame, text="", font=FL,
                                       bg=C["bg"], fg=C["muted"])
        self._lbl_conn_mode.pack(side="left", padx=(0, 4))

        self._conn_mode = self.cfg.get("conn_mode", "web")
        self.b_conn = tk.Button(
            status_frame, text="", font=FB,
            bg=C["panel"], relief="flat", bd=0, padx=8, pady=3,
            cursor="hand2", command=self._toggle_conn_mode)
        self.b_conn.pack(side="left", padx=(0, 12))
        self._update_conn_btn()

        self.status = tk.StringVar()
        tk.Label(status_frame, textvariable=self.status, font=FL,
                 bg=C["bg"], fg=C["muted"], anchor="w").pack(side="left")

        # ── Indicateur de santé La Cale
        self._health_var = tk.StringVar(value="Santé La Cale : ⚪")
        self._health_lbl = tk.Label(
            status_frame, textvariable=self._health_var,
            font=("Courier New", 9), bg=C["bg"], fg=C["muted"])
        self._health_lbl.pack(side="left", padx=(16, 0))

        # Bouton autosave ON/OFF
        self.b_autosave = self._btn(
            f, "", self._toggle_autosave,
            C["green"] if self._autosave_enabled else C["muted"])
        self.b_autosave.grid(row=1, column=1, padx=4)

        # Bouton effacer config
        self.b_clear_cfg = self._btn(f, "", self._clear_config, C["muted"])
        self.b_clear_cfg.grid(row=1, column=2, padx=4)

        self.b_stop   = self._btn(f, "", self._stop,   C["red"])
        self.b_launch = self._btn(f, "", self._launch, C["gold"])
        self.b_stop  .grid(row=1, column=3, padx=4)
        self.b_launch.grid(row=1, column=4)
        self.b_stop.config(state="disabled")

        # Démarrer le loop de santé en arrière-plan (toutes les 10 min)
        self._health_loop()

    def _btn(self, p, txt, cmd, fg):
        return tk.Button(p, text=txt, command=cmd, font=FB,
                         bg=C["panel"], fg=fg,
                         activebackground=C["border"], activeforeground=fg,
                         relief="flat", bd=0, padx=10, pady=5,
                         cursor="hand2",
                         highlightthickness=1, highlightbackground=fg)

    # ══════════════════════════════════════════════════════════════════════════
    # LANGUE — application dynamique
    # ══════════════════════════════════════════════════════════════════════════
    def _on_ui_theme_change(self, *_):
        """Appelée quand l'utilisateur change de thème dans le combo."""
        label = self.vars["ui_theme"].get().strip()
        # Retrouver la clé interne depuis le label affiché
        key = next((k for k, v in THEME_NAMES.items() if v == label), None)
        if key and key != _current_theme[0]:
            self._apply_theme(key)
            cfg = self._collect()
            cfg["ui_theme"] = key
            save_cfg(cfg); self.cfg = cfg
            theme_label = THEME_NAMES.get(key, key)
            self._log(f"  Thème changé : {theme_label}", "ok")
            self._log("  Relancez BLACK FLAG !", "ok")

    def _apply_theme(self, theme_key: str):
        """
        Change le thème en cours :
        1. Met à jour le dict global C avec la nouvelle palette.
        2. Parcourt récursivement tous les widgets et reconfigure les couleurs.
        3. Reapplique le style ttk (Combobox) avec les nouvelles couleurs.
        """
        if theme_key not in THEMES:
            return
        _current_theme[0] = theme_key
        palette = THEMES[theme_key]
        C.update(palette)

        def _recolor(widget):
            """Reconfigure récursivement les couleurs d'un widget."""
            cls = widget.winfo_class()
            try:
                kw = {}
                # Fond général
                if cls in ("Frame", "Label", "Toplevel"):
                    kw["bg"] = C["bg"]
                elif cls == "Button":
                    cur_fg = widget.cget("fg")
                    # Conserver la couleur sémantique : or/vert/rouge/gris
                    if cur_fg in ("#eab308", "#7a5c00",  # gold thème précédent
                                  "#38bdf8", "#1e5f8a"):  # gold thème bleu
                        kw["fg"] = C["gold"]
                    elif cur_fg in ("#22c55e",):
                        kw["fg"] = C["green"]
                    elif cur_fg in ("#ef4444",):
                        kw["fg"] = C["red"]
                    else:
                        kw["fg"] = C["muted"]
                    kw["bg"]                  = C["panel"]
                    kw["highlightbackground"] = C["border"]
                    kw["activebackground"]    = C["border"]
                    kw["activeforeground"]    = C["gold"]
                elif cls == "Entry":
                    kw["bg"]              = C["ibg"]
                    kw["fg"]              = C["ifg"]
                    kw["insertbackground"]= C["gold"]
                    kw["highlightbackground"] = C["border"]
                elif cls == "Text":
                    kw["bg"] = C["ibg"]
                    kw["fg"] = C["ifg"]
                    kw["insertbackground"] = C["gold"]
                    # Retags log
                    try:
                        widget.tag_config("gold",  foreground=C["gold"])
                        widget.tag_config("ok",    foreground=C["green"])
                        widget.tag_config("err",   foreground=C["red"])
                        widget.tag_config("muted", foreground=C["muted"])
                        widget.tag_config("dup",   foreground=C["cyan"])
                    except Exception:
                        pass
                elif cls == "Canvas":
                    kw["bg"] = C["bg"]
                if kw:
                    widget.config(**kw)
            except Exception:
                pass
            # Récursion sur les enfants
            for child in widget.winfo_children():
                _recolor(child)

        _recolor(self.root)

        # ── Barre de progression ─────────────────────────────────────────────
        try:
            st = ttk.Style()
            st.configure("BF.Horizontal.TProgressbar",
                         troughcolor=C["panel"],
                         background=C["gold"],
                         bordercolor=C["border"])
        except Exception:
            pass

        # ── Combobox style ───────────────────────────────────────────────────
        try:
            st = ttk.Style()
            st.configure("BF.TCombobox",
                         fieldbackground=C["ibg"], background=C["ibg"],
                         foreground=C["ifg"], selectbackground=C["ibg"],
                         selectforeground=C["gold"],
                         bordercolor=C["border"],
                         lightcolor=C["border"], darkcolor=C["border"],
                         arrowcolor=C["gold"], insertcolor=C["ifg"])
            st.map("BF.TCombobox",
                   fieldbackground=[("readonly", C["ibg"])],
                   foreground=[("readonly", C["ifg"]), ("disabled", C["muted"])],
                   selectbackground=[("readonly", C["ibg"])],
                   selectforeground=[("readonly", C["gold"])],
                   bordercolor=[("readonly", C["border"]), ("focus", C["border"])],
                   lightcolor=[("readonly", C["border"]), ("focus", C["border"])],
                   darkcolor=[("readonly", C["border"]), ("focus", C["border"])])
            self.root.option_add("*TCombobox*Listbox.foreground",   C["ifg"])
            self.root.option_add("*TCombobox*Listbox.background",   C["ibg"])
            self.root.option_add("*TCombobox*Listbox.selectForeground", C["gold"])
            self.root.option_add("*TCombobox*Listbox.selectBackground", C["border"])
        except Exception:
            pass

        # ── Séparateurs (Frame height=1) — recolorer en gold_dim ────────────
        # On cherche les Frame de hauteur 1 (séparateurs) dans le panneau settings
        def _recolor_separators(widget):
            try:
                if (widget.winfo_class() == "Frame"
                        and widget.winfo_height() <= 2
                        and widget.cget("bg") not in (C["bg"], C["panel"])):
                    widget.config(bg=C["gold_dim"])
            except Exception:
                pass
            for child in widget.winfo_children():
                _recolor_separators(child)
        self.root.after(50, lambda: _recolor_separators(self.root))

        # ── Titre fenêtre barre sombre (Windows) ─────────────────────────────
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int))
        except Exception:
            pass

        # Forcer un rafraîchissement visuel
        self.root.update_idletasks()

    def _on_ui_lang_change(self, *_):
        global _lang
        new = self.vars["ui_lang"].get().strip()
        if new in T:
            _lang = new
            self._apply_lang()

    def _apply_lang(self):
        """Rafraîchit tous les textes de l'interface dans la langue courante."""
        # Police adaptée : le japonais nécessite une police système qui supporte CJK
        # Sur Windows, "Yu Gothic UI" ou "Meiryo" couvrent les caractères japonais
        if _lang == "ja":
            _font_ui  = ("Yu Gothic UI", 9)
            _font_ui8 = ("Yu Gothic UI", 8)
            _font_bold= ("Yu Gothic UI", 9, "bold")
        else:
            _font_ui  = FM
            _font_ui8 = FM8
            _font_bold= FB

        # Titre fenêtre
        self.root.title(t("title", v=APP_VERSION))

        # Sous-titre logo
        self._subtitle_lbl.config(text=t("subtitle", v=APP_VERSION), font=_font_ui8)

        # Log header + boutons header
        self._lbl_log_header.config(text=t("log_header"), font=_font_bold)
        self._btn_clear_log.config(text=t("btn_clear"), font=_font_ui8)
        self._btn_history.config(text=t("btn_history"), font=_font_ui8)

        # Labels dynamiques principaux
        for key, (widget, label_key) in self._dyn_labels.items():
            widget.config(text=t(label_key))

        # Toggle settings
        txt = t("btn_settings_close") if self._settings_open \
              else t("btn_settings_open")
        self._toggle_btn.config(text=txt)

        # Boutons bottom
        # Bouton save : préserver l'indicateur ● si non sauvegardé
        # Bouton save : supprimé (autosave actif)
        pass
        self.b_stop  .config(text=t("btn_stop"))
        self.b_launch.config(text=t("btn_launch"))
        # Label + toggle mode de connexion
        self._lbl_conn_mode.config(text=t("lbl_conn_mode"))
        self._update_conn_btn()
        # Boutons autosave et effacer config
        as_key = "btn_autosave_on" if self._autosave_enabled else "btn_autosave_off"
        as_col = C["green"] if self._autosave_enabled else C["muted"]
        self.b_autosave.config(text=t(as_key), fg=as_col, highlightbackground=as_col)
        self.b_clear_cfg.config(text=t("btn_clear_cfg"))
        # Toggle notification
        self._refresh_notify_ui()
        self._refresh_logs_curl_ui()
        self._refresh_check_updates_ui()
        self._refresh_seed_check_ui()
        # Étiquette MAJ
        if hasattr(self, "_lbl_update") and self._lbl_update.winfo_ismapped():
            self._lbl_update.config(text=f"  ↑ {t('lbl_update_available')}")
        if not self.running:
            self.status.set(t("status_ready"))

        # Labels du panneau settings
        for key, (widget, label_key) in self._s_labels.items():
            widget.config(text=t(label_key))

        # Combo langue UI
        self._ui_lang_combo.config(values=list(LANGS_UI.keys()))

        # Combo grade Films — mettre à jour les valeurs dans la langue courante
        if hasattr(self, "_grade_f_combo"):
            grades = get_grades()
            self._grade_f_combo.config(values=grades)
            try:
                max_val = int(self.vars["max_movies"].get() or 1)
                idx = GRADE_MAX.index(max_val)
                self.grade_film_var.set(grades[idx])
            except (ValueError, IndexError):
                self.grade_film_var.set(grades[0])

        # Combo grade Séries — mettre à jour les valeurs dans la langue courante
        if hasattr(self, "_grade_s_combo"):
            grades = get_grades()
            self._grade_s_combo.config(values=grades)
            try:
                max_val = int(self.vars["max_series"].get() or 1)
                idx = GRADE_MAX.index(max_val)
                self.grade_series_var.set(grades[idx])
            except (ValueError, IndexError):
                self.grade_series_var.set(grades[0])

    # ══════════════════════════════════════════════════════════════════════════
    # FENÊTRE HISTORIQUE
    # ══════════════════════════════════════════════════════════════════════════
    def _show_history(self):
        if hasattr(self, "_history_win") and self._history_win and \
                self._history_win.winfo_exists():
            self._history_win.destroy()
            self._history_win = None
            return

        from tkinter import ttk

        win = tk.Toplevel(self.root)
        self._history_win = win
        win.title(t("hist_title"))
        win.configure(bg=C["bg"])
        win.geometry("530x560")
        win.resizable(True, True)
        win.transient(self.root)
        win.bind("<Destroy>", lambda e: setattr(self, "_history_win", None))

        # Layout grid sur win
        win.columnconfigure(0, weight=1)
        win.rowconfigure(2, weight=1)  # treeview seul s'agrandit

        # ── Style ─────────────────────────────────────────────────────────────
        style = ttk.Style()
        style.configure("History.Treeview",
                        background=C["ibg"], foreground=C["text"],
                        fieldbackground=C["ibg"], borderwidth=0,
                        rowheight=22, font=FM8)
        style.configure("History.Treeview.Heading",
                        background=C["panel"], foreground=C["muted"],
                        borderwidth=0, relief="flat", font=FM8)
        style.map("History.Treeview",
                  background=[("selected", C["border"])],
                  foreground=[("selected", C["gold"])])
        style.map("History.Treeview.Heading",
                  background=[("active", C["border"])])
        style.layout("History.Treeview",
                     [("History.Treeview.treearea", {"sticky": "nswe"})])

        # ── Row 0 : header ────────────────────────────────────────────────────
        hf = tk.Frame(win, bg=C["bg"])
        hf.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))
        tk.Label(hf, text=t("hist_title"), font=FB,
                 bg=C["bg"], fg=C["gold"]).pack(side="left")

        # ── Row 1 : séparateur ────────────────────────────────────────────────
        tk.Frame(win, bg=C["gold_dim"], height=1).grid(
            row=1, column=0, sticky="ew", padx=14, pady=(4, 0))

        # ── Row 2 : treeview ──────────────────────────────────────────────────
        tv_frame = tk.Frame(win, bg=C["bg"])
        tv_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=(4, 0))
        tv_frame.columnconfigure(0, weight=1)
        tv_frame.rowconfigure(0, weight=1)

        COLS = ("#", "Titre", "Date d'upload", "ÉTAT", "Tracker", " ")
        COL_WIDTHS = {"#": 40, "Titre": 340, "Date d'upload": 90,
                      "ÉTAT": 80, "Tracker": 70, " ": 24}
        col_visible = {"Date d'upload": [True], "ÉTAT": [True], "Tracker": [True]}

        tv = ttk.Treeview(tv_frame, style="History.Treeview",
                          columns=COLS, show="headings", selectmode="browse")
        tv.grid(row=0, column=0, sticky="nsew")
        vsb = SlimScrollbar(tv_frame, command=tv.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        tv.configure(yscrollcommand=vsb.set)
        tv.bind("<MouseWheel>", lambda e: tv.yview_scroll(int(-1*(e.delta/120)), "units"))

        tv.tag_configure("seeding", foreground=C["green"],  background=C["ibg"])
        tv.tag_configure("error",   foreground=C["red"],    background=C["ibg"])
        tv.tag_configure("deleted", foreground="#9ca3af",   background=C["ibg"])
        tv.tag_configure("odd",     background="#161616",   foreground=C["text"])
        tv.tag_configure("even",    background=C["ibg"],    foreground=C["text"])

        # ── Row 3 : barre bas ─────────────────────────────────────────────────
        bf = tk.Frame(win, bg=C["bg"])
        bf.grid(row=3, column=0, sticky="ew", padx=14, pady=(4, 10))

        sort_col = ["#"]
        sort_asc = [True]
        entries_cache = []

        def parse_lines():
            if not HIST_FILE.exists():
                return []
            entries = []
            for raw in HIST_FILE.read_text("utf-8", errors="ignore").splitlines():
                raw = raw.strip()
                if not raw: continue
                parts       = raw.split("\t")
                title       = parts[0].strip()
                tracker_key = ""
                date_val    = ""
                for part in parts[1:]:
                    p = part.strip().strip("[]")
                    if p in ("TORR9", "LACALE"):
                        tracker_key = p
                    elif p.startswith("DATE:"):
                        date_val = p[5:]
                entries.append({"title": title, "tracker": tracker_key, "date": date_val})
            return entries

        def get_seed_state(title):
            try:
                cfg_local   = self.cfg
                if cfg_local.get("torrent_client", "qbittorrent") != "qbittorrent":
                    return ""
                url  = cfg_local.get("qb_url", "").strip()
                user = cfg_local.get("qb_user", "").strip()
                pwd  = cfg_local.get("qb_pass", "").strip()
                if not url: return ""
                import requests as _req
                sess = _req.Session()
                r = sess.post(f"{url.rstrip('/')}/api/v2/auth/login",
                              data={"username": user, "password": pwd}, timeout=5)
                if r.status_code != 200 or "ok" not in r.text.lower(): return ""
                r2 = sess.get(f"{url.rstrip('/')}/api/v2/torrents/info",
                              params={"filter": "all"}, timeout=10)
                if r2.status_code != 200: return ""
                GOOD = {"uploading","stalledUP","forcedUP","queuedUP",
                        "checkingUP","stoppedUP","pausedUP","moving"}
                name_low = title.lower()
                for t2 in r2.json():
                    t_name = (t2.get("name") or "").lower()
                    if name_low in t_name or t_name in name_low:
                        st = t2.get("state", "")
                        if st in GOOD: return "seeding"
                        if st in ("missingFiles","error"): return "error"
                        return ""
            except Exception:
                pass
            return "deleted"

        def build_columns():
            visible = ["#", "Titre"] + [
                c for c in ("Date d'upload", "ÉTAT", "Tracker")
                if col_visible[c][0]] + [" "]
            tv.configure(displaycolumns=visible)
            for col in visible:
                arrow = (" ▲" if sort_asc[0] else " ▼") if col == sort_col[0] else ""
                tv.heading(col, text=col+arrow, command=lambda c=col: _sort_by(c))
                anchor = "e" if col == "#" else "w" if col == "Titre" else "center"
                tv.column(col, width=COL_WIDTHS.get(col, 80),
                          stretch=(col == "Titre"),
                          anchor=anchor)
            tv.column(" ", width=24, stretch=False, anchor="center")

        def _sort_by(col):
            if col == " ": return
            sort_asc[0] = not sort_asc[0] if sort_col[0]==col else True
            sort_col[0] = col
            build_columns(); _populate()

        def _populate():
            tv.delete(*tv.get_children())
            entries_cache.clear()
            entries = parse_lines()
            # Debug : afficher le chemin et nb entrées dans le titre de la fenêtre
            win.title(f"{t('hist_title')} — {HIST_FILE} ({len(entries)} entrées)")
            if not entries: return
            col = sort_col[0]
            key_fn = {"Titre": lambda e: e["title"].lower(),
                      "Date d'upload": lambda e: e["date"],
                      "Tracker": lambda e: e["tracker"]}.get(col)
            sorted_entries = sorted(entries, key=key_fn, reverse=not sort_asc[0]) \
                             if key_fn else (entries if sort_asc[0] else list(reversed(entries)))
            for idx, entry in enumerate(sorted_entries):
                tracker_key = entry["tracker"]
                tk_disp = {"TORR9": "🔵 Torr9", "LACALE": "🟡 La Cale"}.get(
                            tracker_key, tracker_key or "?")
                row_bg = "odd" if idx % 2 else "even"
                tv.insert("", "end", iid=str(idx), tags=(row_bg,),
                    values=(f"{idx+1:>4}", entry["title"],
                            entry["date"] if col_visible["Date d'upload"][0] else "",
                            "…" if col_visible["ÉTAT"][0] else "",
                            tk_disp if col_visible["Tracker"][0] else "",
                            "🗑"))
                entries_cache.append(entry)
                if col_visible["ÉTAT"][0]:
                    def _fetch(i=idx, tit=entry["title"], tg=row_bg):
                        def _bg():
                            s = get_seed_state(tit)
                            disp = {"seeding": "🟢 seed", "error": "🔴 error",
                                    "deleted": "⚫ absent", "": "?"}.get(s, "?")
                            tag  = {"seeding": "seeding", "error": "error",
                                    "deleted": "deleted"}.get(s, tg)
                            def _up():
                                if str(i) not in tv.get_children(): return
                                v = list(tv.item(str(i), "values"))
                                v[3] = disp
                                tv.item(str(i), values=v, tags=(tag,))
                            try: tv.after(0, _up)
                            except Exception: pass
                        threading.Thread(target=_bg, daemon=True).start()
                    _fetch()

        def _on_click(e):
            col_id = tv.identify_column(e.x)
            row_id = tv.identify_row(e.y)
            if not row_id or col_id != f"#{len(tv['displaycolumns'])}": return
            idx = int(row_id)
            if idx >= len(entries_cache): return
            entry = entries_cache[idx]
            dlg = tk.Toplevel(win)
            dlg.title("Confirmer"); dlg.configure(bg=C["bg"])
            dlg.resizable(False, False); dlg.transient(win)
            fr = tk.Frame(dlg, bg=C["bg"]); fr.pack(padx=20, pady=14)
            tk.Label(fr, text=f"Supprimer '{entry['title'][:60]}' ?",
                     font=FM8, bg=C["bg"], fg=C["text"], wraplength=380).pack(pady=(0,10))
            def _confirm():
                dlg.destroy()
                ls = [l for l in HIST_FILE.read_text("utf-8", errors="ignore").splitlines()
                      if entry["title"] not in l]
                HIST_FILE.write_text("\n".join(ls), "utf-8"); _populate()
            tk.Button(fr, text="Supprimer 🗑", command=_confirm, font=FB,
                      bg=C["panel"], fg=C["red"], relief="flat", bd=0,
                      padx=14, pady=5, cursor="hand2",
                      highlightthickness=1, highlightbackground=C["red"]
                      ).pack(side="left", padx=(0,10))
            tk.Button(fr, text="Annuler", command=dlg.destroy, font=FB,
                      bg=C["panel"], fg=C["gold"], relief="flat", bd=0,
                      padx=14, pady=5, cursor="hand2",
                      highlightthickness=1, highlightbackground=C["gold"]
                      ).pack(side="left")
            dlg.focus_set()

        tv.bind("<ButtonRelease-1>", _on_click)

        # Boutons barre bas
        def clear_hist():
            dlg = tk.Toplevel(win)
            dlg.title(t("hist_btn_clear")); dlg.configure(bg=C["bg"])
            dlg.resizable(False, False); dlg.transient(win)
            fr = tk.Frame(dlg, bg=C["bg"]); fr.pack(padx=20, pady=14)
            tk.Label(fr, text=t("hist_confirm_clear"),
                     font=FM8, bg=C["bg"], fg=C["text"]).pack(pady=(0,10))
            def _confirm():
                dlg.destroy()
                HIST_FILE.write_text("", "utf-8"); _populate()
            tk.Button(fr, text="Vider 🗑", command=_confirm, font=FB,
                      bg=C["panel"], fg=C["red"], relief="flat", bd=0,
                      padx=14, pady=5, cursor="hand2",
                      highlightthickness=1, highlightbackground=C["red"]
                      ).pack(side="left", padx=(0,10))
            tk.Button(fr, text="Annuler", command=dlg.destroy, font=FB,
                      bg=C["panel"], fg=C["gold"], relief="flat", bd=0,
                      padx=14, pady=5, cursor="hand2",
                      highlightthickness=1, highlightbackground=C["gold"]
                      ).pack(side="left")
            dlg.focus_set()

        tk.Button(bf, text=t("hist_btn_clear"), command=clear_hist,
                  font=FM8, bg=C["panel"], fg=C["muted"], relief="flat", bd=0,
                  padx=8, pady=4, cursor="hand2",
                  highlightthickness=1, highlightbackground=C["border"]
                  ).pack(side="left")

        tk.Button(bf, text=t("hist_btn_close"), command=win.destroy,
                  font=FB, bg=C["panel"], fg=C["gold"], relief="flat", bd=0,
                  padx=12, pady=4, cursor="hand2",
                  highlightthickness=1, highlightbackground=C["gold"]
                  ).pack(side="right", padx=(4, 0))

        def _make_col_toggle(lbl, col_ref):
            btn = tk.Button(bf, text=lbl, font=FM8, bg=C["panel"], fg=C["muted"],
                            relief="flat", bd=0, padx=8, pady=4, cursor="hand2",
                            highlightthickness=1, highlightbackground=C["muted"])
            btn.pack(side="right", padx=(4, 0))
            def _toggle():
                col_ref[0] = not col_ref[0]
                c = C["gold"] if col_ref[0] else C["muted"]
                btn.config(fg=c, highlightbackground=c)
                build_columns(); _populate()
            btn.config(command=_toggle,
                       fg=C["gold"] if col_ref[0] else C["muted"],
                       highlightbackground=C["gold"] if col_ref[0] else C["muted"])

        _make_col_toggle("Tracker",       col_visible["Tracker"])
        _make_col_toggle("ÉTAT",          col_visible["ÉTAT"])
        _make_col_toggle("Date d'upload", col_visible["Date d'upload"])

        build_columns()
        _populate()
        win.focus_set()

    def _on_grade_film(self, *_):
        try:
            idx = get_grades().index(self.grade_film_var.get())
            self.vars["max_movies"].set(str(GRADE_MAX[idx]))
        except (ValueError, IndexError): pass

    def _on_grade_series(self, *_):
        try:
            idx = get_grades().index(self.grade_series_var.get())
            self.vars["max_series"].set(str(GRADE_MAX[idx]))
        except (ValueError, IndexError):
            pass

    def _fetch_torr9_announce(self):
        """Récupère l'URL d'annonce Torr9 depuis le passkey utilisateur."""
        url  = self.vars.get("torr9_url",  tk.StringVar()).get().strip().rstrip("/")
        user = self.vars.get("torr9_user", tk.StringVar()).get().strip()
        pwd  = self.vars.get("torr9_pass", tk.StringVar()).get().strip()

        if not url or not user or not pwd:
            messagebox.showwarning("Torr9",
                "Renseignez d'abord l'URL, le pseudonyme et le mot de passe Torr9.")
            return

        self._btn_torr9_fetch.config(state="disabled", text="...")

        def _do():
            result = None
            error  = None
            try:
                import requests as _req
                # Login
                r = _req.post(f"https://api.torr9.net/api/v1/auth/login",
                              json={"username": user, "password": pwd}, timeout=10)
                body = r.json()
                token = body.get("token", "")
                if not token:
                    error_msg = body.get("error", "Connexion échouée")
                    raise Exception(error_msg)
                # Récupérer le passkey depuis le profil utilisateur
                passkey = body.get("user", {}).get("passkey", "")
                if passkey:
                    result = f"https://tracker.torr9.net/announce/{passkey}"
                else:
                    # Essayer via /api/v1/user/profile
                    sess = _req.Session()
                    sess.headers["Authorization"] = f"Bearer {token}"
                    r2 = sess.get("https://api.torr9.net/api/v1/user/profile", timeout=10)
                    passkey = r2.json().get("passkey", "")
                    if passkey:
                        result = f"https://tracker.torr9.net/announce/{passkey}"
                    else:
                        raise Exception("Passkey introuvable dans le profil.")
            except Exception as e:
                error = str(e)
            self.root.after(0, lambda: self._on_torr9_fetch_done(result, error))

        threading.Thread(target=_do, daemon=True).start()

    def _on_torr9_fetch_done(self, result, error):
        self._btn_torr9_fetch.config(state="normal", text="↺ Récupérer")
        if error:
            messagebox.showerror("Torr9", f"Erreur : {error}")
            return
        if result:
            self.vars["torr9_announce"].set(result)
            self._log(f"Torr9 → URL d'annonce récupérée.", "ok")

    def _fetch_torr9_token(self):
        """Récupère le token API Torr9 depuis le login user/pass et le stocke."""
        user = self.vars.get("torr9_user", tk.StringVar()).get().strip()
        pwd  = self.vars.get("torr9_pass", tk.StringVar()).get().strip()

        if not user or not pwd:
            messagebox.showwarning("Torr9",
                "Renseignez d'abord le pseudonyme et le mot de passe Torr9.")
            return

        self._btn_torr9_token.config(state="disabled", text="...")

        def _do():
            result = None
            error  = None
            try:
                import requests as _req
                r = _req.post(
                    "https://api.torr9.net/api/v1/auth/login",
                    json={"username": user, "password": pwd},
                    headers={"Content-Type": "application/json",
                             "Accept": "application/json"},
                    timeout=15)
                body = r.json()
                token = body.get("token") or body.get("access_token") or ""
                if r.status_code == 200 and token:
                    result = token
                else:
                    error = body.get("error") or body.get("message") or f"HTTP {r.status_code}"
            except Exception as e:
                error = str(e)
            self.root.after(0, lambda: self._on_torr9_token_done(result, error))

        threading.Thread(target=_do, daemon=True).start()

    def _on_torr9_token_done(self, result, error):
        self._btn_torr9_token.config(state="normal", text="↺ Récupérer")
        if error:
            messagebox.showerror("Torr9", f"Erreur : {error}")
            return
        if result:
            self.vars["torr9_token"].set(result)
            self._log("Torr9 → Token API récupéré et sauvegardé.", "ok")
            messagebox.showinfo("Torr9",
                "Token récupéré ✓\n\nIl sera utilisé à la prochaine connexion.\n"
                "Vous pouvez le renouveler à tout moment avec ce bouton.")

    def _fetch_qb_paths(self):
        """Interroge qBittorrent pour récupérer le save_path par défaut."""
        url  = self.vars.get("qb_url",  tk.StringVar()).get().strip()
        user = self.vars.get("qb_user", tk.StringVar()).get().strip()
        pwd  = self.vars.get("qb_pass", tk.StringVar()).get().strip()

        if not url:
            messagebox.showwarning("qBittorrent",
                "Renseignez d'abord l'URL WebUI de qBittorrent.")
            return

        self._btn_qb_fetch.config(state="disabled", text="...")

        def do_fetch():
            result = None
            error  = None
            try:
                import requests as _req
                s = _req.Session()
                # Login
                r = s.post(f"{url.rstrip('/')}/api/v2/auth/login",
                           data={"username": user, "password": pwd},
                           timeout=8)
                if r.status_code == 200 and "ok" in r.text.lower():
                    # Récupérer les préférences
                    prefs = s.get(f"{url.rstrip('/')}/api/v2/app/preferences",
                                  timeout=8).json()
                    result = prefs.get("save_path", "")
            except Exception as e:
                error = str(e)
            self.root.after(0, self._on_qb_fetch_done, result, error)

        threading.Thread(target=do_fetch, daemon=True).start()

    def _on_qb_fetch_done(self, save_path, error):
        self._btn_qb_fetch.config(state="normal", text=t("btn_qb_fetch"))
        if error:
            messagebox.showerror("qBittorrent",
                f"Connexion impossible :\n{error}\n\n"
                "Vérifiez l'URL, l'utilisateur et le mot de passe.")
            return
        if not save_path:
            messagebox.showwarning("qBittorrent",
                "Save path introuvable dans les préférences qBittorrent.\n"
                "Renseignez les chemins manuellement.")
            return
        # Pré-remplir les deux champs avec le save_path récupéré
        self.vars["qb_films_path"].set(save_path)
        self.vars["qb_series_path"].set(save_path)
        self._log(f"qBittorrent → save path récupéré : {save_path}", "ok")

    # ── Load / collect ────────────────────────────────────────────────────────
    def _load(self):
        self._loading = True
        for k, v in self.vars.items():
            v.set(self.cfg.get(k, ""))
        # Quota Films
        try:
            idx_f = GRADE_MAX.index(int(self.cfg.get("max_movies", 1)))
            self.grade_film_var.set(get_grades()[idx_f])
        except (ValueError, IndexError):
            self.grade_film_var.set(get_grades()[0])
        # Quota Séries (indépendant)
        try:
            idx_s = GRADE_MAX.index(int(self.cfg.get("max_series", 1)))
            self.grade_series_var.set(get_grades()[idx_s])
        except (ValueError, IndexError):
            self.grade_series_var.set(get_grades()[0])
        # Mode de connexion
        self._conn_mode = self.cfg.get("conn_mode", "web")
        self._update_conn_btn()
        # Client torrent
        self._torrent_client = self.cfg.get("torrent_client", "qbittorrent")
        # Tracker actif
        self._active_tracker = self.cfg.get("active_tracker", "lacale")
        self.root.after(20, self._update_client_ui)
        self.root.after(22, self._update_torr9_btn)
        self.root.after(24, self._update_tracker_fields)
        self.root.after(26, self._update_health_label)
        # Notification watcher
        self._notify_enabled = bool(self.cfg.get("notify_enabled", False))
        self.root.after(30, self._refresh_notify_ui)
        self._save_logs_enabled = bool(self.cfg.get("save_logs", False))
        self._save_curl_enabled = bool(self.cfg.get("save_curl", False))
        self.root.after(35, self._refresh_logs_curl_ui)
        self.root.after(40, self._refresh_check_updates_ui)
        # Langue UI
        self.vars["ui_lang"].set(self.cfg.get("ui_lang", "fr"))
        # Thème UI
        theme_key = self.cfg.get("ui_theme", "gold")
        theme_label = THEME_NAMES.get(theme_key, THEME_NAMES["gold"])
        if "ui_theme" in self.vars:
            self.vars["ui_theme"].set(theme_label)
        if theme_key != _current_theme[0]:
            self.root.after(60, lambda k=theme_key: self._apply_theme(k))
        self._loading = False

        # Brancher l'autosave sur chaque variable APRÈS le chargement
        self._autosave_job = None
        for v in self.vars.values():
            v.trace_add("write", self._on_field_change)

        # Vérification MAJ au démarrage (en arrière-plan)
        self._check_updates_enabled = bool(self.cfg.get("check_updates", True))
        self._seed_check_enabled = bool(self.cfg.get("seed_check", True))
        self.root.after(2000, self._run_update_check)   # 2s après démarrage

    # ══════════════════════════════════════════════════════════════════════════
    # WATCHER — Notification retour site
    # ══════════════════════════════════════════════════════════════════════════
    def _set_torrent_client(self, client):
        """Bascule entre qbittorrent, transmission, deluge et vuze."""
        self._torrent_client = client
        cfg = self._collect()
        cfg["torrent_client"] = client
        save_cfg(cfg); self.cfg = cfg
        self._update_client_ui()
        self._log_active_config()

    def _update_client_ui(self):
        """Met à jour les boutons et affiche les champs du client actif."""
        if not hasattr(self, "_btn_client_qb"):
            return
        ct = self._torrent_client
        is_qb = (ct == "qbittorrent")
        is_tr = (ct == "transmission")
        is_de = (ct == "deluge")
        is_vz = (ct == "vuze")

        def _btn_state(btn, active):
            btn.config(fg=C["gold"] if active else C["muted"],
                       highlightthickness=1,
                       highlightbackground=C["gold"] if active else C["muted"])

        _btn_state(self._btn_client_qb, is_qb)
        _btn_state(self._btn_client_tr, is_tr)
        if hasattr(self, "_btn_client_de"):
            _btn_state(self._btn_client_de, is_de)
        if hasattr(self, "_btn_client_vz"):
            _btn_state(self._btn_client_vz, is_vz)

        # Afficher/masquer les champs selon le client actif
        for w in self._qb_rows:
            w.grid() if is_qb else w.grid_remove()
        for w in self._tr_rows:
            w.grid() if is_tr else w.grid_remove()
        if hasattr(self, "_de_rows"):
            for w in self._de_rows:
                w.grid() if is_de else w.grid_remove()
        if hasattr(self, "_vz_rows"):
            for w in self._vz_rows:
                w.grid() if is_vz else w.grid_remove()

    def _set_active_tracker(self, tracker):
        """Bascule le tracker actif entre lacale et torr9."""
        self._active_tracker = tracker
        if tracker == "torr9":
            # Torr9 = Web uniquement → forcer le mode Web
            if self._conn_mode != "web":
                self._conn_mode = "web"
        cfg = self._collect()
        cfg["active_tracker"] = self._active_tracker
        save_cfg(cfg); self.cfg = cfg
        self._update_torr9_btn()
        self._update_conn_btn()
        self._update_tracker_fields()
        self._update_health_label()
        self._log_active_config()

    def _update_tracker_fields(self):
        """Affiche les champs La Cale ou Torr9 selon le tracker actif."""
        is_torr9 = getattr(self, "_active_tracker", "lacale") == "torr9"
        for w in getattr(self, "_lacale_rows", []):
            w.grid_remove() if is_torr9 else w.grid()
        # _frame_api / _frame_web sont gérés dans _update_conn_btn — on les force ici aussi
        if hasattr(self, "_frame_api") and hasattr(self, "_frame_web"):
            if is_torr9:
                self._frame_api.grid_remove()
                self._frame_web.grid_remove()
            else:
                if self._conn_mode == "api":
                    self._frame_api.grid()
                    self._frame_web.grid_remove()
                else:
                    self._frame_api.grid_remove()
                    self._frame_web.grid()
        for w in getattr(self, "_torr9_rows", []):
            w.grid() if is_torr9 else w.grid_remove()

    def _update_torr9_btn(self):
        """Met à jour le visuel des boutons LA CALE et TORR9."""
        is_torr9 = getattr(self, "_active_tracker", "lacale") == "torr9"
        if hasattr(self, "_btn_tracker_lacale"):
            self._btn_tracker_lacale.config(
                fg=C["muted"] if is_torr9 else C["gold"],
                highlightthickness=1,
                highlightbackground=C["muted"] if is_torr9 else C["gold"])
        if hasattr(self, "_btn_tracker_torr9"):
            self._btn_tracker_torr9.config(
                fg=C["gold"] if is_torr9 else C["muted"],
                highlightthickness=1,
                highlightbackground=C["gold"] if is_torr9 else C["muted"])

    def _update_health_label(self):
        """Adapte le texte du label de santé selon le tracker actif."""
        if not hasattr(self, "_health_var"):
            return
        is_torr9 = getattr(self, "_active_tracker", "lacale") == "torr9"
        # Mettre à jour le texte (garder la bille actuelle)
        current = self._health_var.get()
        # Extraire la bille (dernier caractère émoji)
        bille = current.split()[-1] if current else "⚪"
        if is_torr9:
            self._health_var.set(f"Santé Torr9 : {bille}")
        else:
            self._health_var.set(f"Santé La Cale : {bille}")

    def _self_update(self):
        """
        Telecharge la derniere version depuis GitHub et remplace le fichier .py courant.
        Ecriture atomique via un .tmp pour eviter la corruption.
        """
        if not _REQUESTS_OK:
            self._log("  Mise a jour : impossible (requests non disponible).", "err")
            return
        if hasattr(self, "_btn_self_update"):
            self._btn_self_update.config(state="disabled", fg=C["muted"])

        def _do_update():
            self._log("─" * 60, "muted")
            self._log("  Mise a jour — Connexion a GitHub...", "gold")
            try:
                r = requests.get(
                    _UPDATE_URL, timeout=20,
                    headers={"User-Agent": "BLACK-FLAG-updater/" + APP_VERSION})
                if r.status_code != 200:
                    self._log(
                        f"  Echec de connexion — HTTP {r.status_code}.", "err")
                    return
                new_src = r.text
                if "APP_VERSION" not in new_src or "class App" not in new_src:
                    self._log(
                        "  Fichier distant invalide — mise a jour annulee.", "err")
                    return
                remote_ver = ""
                for line in new_src.splitlines()[:200]:
                    s = line.strip()
                    if s.startswith("APP_VERSION") and "=" in s:
                        remote_ver = s.split("=")[1].strip().strip("\"'")
                        break
                self._log(
                    f"  Fichier distant valide — version {remote_ver or '?'}.", "gold")
                self._log("  Remplacement du fichier en cours...", "gold")
                if getattr(sys, "frozen", False):
                    target = Path(sys.executable).parent / "BLACK.FLAG version exe.py"
                else:
                    target = Path(__file__).resolve()
                tmp = target.with_suffix(".tmp")
                tmp.write_text(new_src, encoding="utf-8")
                tmp.replace(target)
                self._log(f"  Fichier mis a jour : {target.name}", "ok")
                self._log("  Relancez BLACK FLAG !", "ok")
            except requests.exceptions.ConnectionError:
                self._log(
                    "  Echec — impossible de joindre GitHub (reseau KO).", "err")
            except requests.exceptions.Timeout:
                self._log(
                    "  Echec — delai de connexion depasse (timeout).", "err")
            except PermissionError:
                self._log(
                    "  Echec — permission refusee lors de l'ecriture du fichier.", "err")
                self._log(
                    "  Essayez de lancer BLACK FLAG en administrateur.", "err")
            except Exception as e:
                self._log(f"  Echec de la mise a jour : {e}", "err")
            finally:
                self.root.after(0, self._restore_update_btn)

        threading.Thread(target=_do_update, daemon=True).start()

    def _restore_update_btn(self):
        if hasattr(self, "_btn_self_update"):
            self._btn_self_update.config(state="normal", fg=C["gold"])

    def _toggle_check_updates(self):
        self._check_updates_enabled = not self._check_updates_enabled
        cfg = self._collect(); cfg["check_updates"] = self._check_updates_enabled
        save_cfg(cfg); self.cfg = cfg
        self._refresh_check_updates_ui()
        # Si on désactive, masquer immédiatement l'étiquette de mise à jour
        if not self._check_updates_enabled:
            if hasattr(self, "_lbl_update") and self._lbl_update.winfo_ismapped():
                self._lbl_update.pack_forget()

    def _refresh_check_updates_ui(self):
        if not hasattr(self, "_btn_check_updates"):
            return
        if self._check_updates_enabled:
            self._btn_check_updates.config(
                text=t("check_updates_on"), fg=C["green"],
                highlightthickness=1, highlightbackground=C["green"])
        else:
            self._btn_check_updates.config(
                text=t("check_updates_off"), fg=C["muted"],
                highlightthickness=1, highlightbackground=C["muted"])

    def _toggle_seed_check(self):
        self._seed_check_enabled = not self._seed_check_enabled
        cfg = self._collect(); cfg["seed_check"] = self._seed_check_enabled
        save_cfg(cfg); self.cfg = cfg
        self._refresh_seed_check_ui()

    def _refresh_seed_check_ui(self):
        if not hasattr(self, "_btn_seed_check"):
            return
        if self._seed_check_enabled:
            self._btn_seed_check.config(
                text=t("seed_check_on"), fg=C["gold"],
                highlightthickness=1, highlightbackground=C["gold"])
        else:
            self._btn_seed_check.config(
                text=t("seed_check_off"), fg=C["muted"],
                highlightthickness=1, highlightbackground=C["muted"])

    def _run_update_check(self):
        """Vérifie la MAJ en arrière-plan au démarrage."""
        if not self._check_updates_enabled:
            return
        def _check():
            available, changelog = _check_update_available()
            if available:
                self.root.after(0, self._show_update_badge, changelog)
        threading.Thread(target=_check, daemon=True).start()

    def _hide_update_install_btn(self):
        """Cache le bouton d'installation GitHub et son séparateur."""
        for w in ("_upd_sep", "_upd_frame"):
            widget = getattr(self, w, None)
            if widget:
                try:
                    widget.grid_remove()
                except Exception:
                    pass

    def _show_update_install_btn(self):
        """Affiche le bouton d'installation GitHub et son séparateur."""
        for w in ("_upd_sep", "_upd_frame"):
            widget = getattr(self, w, None)
            if widget:
                try:
                    widget.grid()
                except Exception:
                    pass

    def _show_update_badge(self, changelog=""):
        """Affiche l'étiquette verte 'Mise à jour disponible' avec tooltip."""
        if not hasattr(self, "_lbl_update"):
            return
        # Ne pas afficher si les vérifications de MAJ sont désactivées
        if not self._check_updates_enabled:
            return
        self._lbl_update.config(text=f"  ↑ {t('lbl_update_available')}")
        self._lbl_update.pack(side="left", padx=(10, 0))
        # Afficher aussi le bouton d'installation dans les paramètres
        self.root.after(0, self._show_update_install_btn)
        # Tooltip au survol
        if changelog:
            self._add_tooltip(self._lbl_update, changelog)

    def _add_tooltip(self, widget, text):
        """Affiche un petit popup au survol du widget."""
        tip = {"win": None}

        def _show(e):
            x = widget.winfo_rootx() + 10
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            w = tk.Toplevel(self.root)
            w.wm_overrideredirect(True)
            w.wm_geometry(f"+{x}+{y}")
            w.configure(bg=C["border"])
            tk.Label(w, text=text, font=FM8,
                     bg=C["panel"], fg=C["gold"],
                     relief="flat", bd=0, padx=8, pady=4,
                     wraplength=500, justify="left"
                     ).pack()
            tip["win"] = w

        def _hide(e):
            if tip["win"]:
                tip["win"].destroy()
                tip["win"] = None

        widget.bind("<Enter>", _show)
        widget.bind("<Leave>", _hide)

    def _toggle_save_logs(self):
        self._save_logs_enabled = not self._save_logs_enabled
        cfg = self._collect(); cfg["save_logs"] = self._save_logs_enabled
        save_cfg(cfg); self.cfg = cfg
        self._refresh_logs_curl_ui()

    def _toggle_save_curl(self):
        self._save_curl_enabled = not self._save_curl_enabled
        cfg = self._collect(); cfg["save_curl"] = self._save_curl_enabled
        save_cfg(cfg); self.cfg = cfg
        self._refresh_logs_curl_ui()

    def _refresh_logs_curl_ui(self):
        if not hasattr(self, "_btn_save_logs"):
            return
        for enabled, btn, on_key, off_key in [
            (self._save_logs_enabled, self._btn_save_logs, "save_logs_on", "save_logs_off"),
            (self._save_curl_enabled, self._btn_save_curl, "save_curl_on", "save_curl_off"),
        ]:
            if enabled:
                btn.config(text=t(on_key), fg=C["green"],
                           highlightthickness=1, highlightbackground=C["green"])
            else:
                btn.config(text=t(off_key), fg=C["muted"],
                           highlightthickness=1, highlightbackground=C["muted"])

    def _toggle_encrypt_cfg(self):
        """Active ou désactive le chiffrement de la config."""
        if not _CRYPTO_OK:
            messagebox.showwarning(
                "Chiffrement indisponible",
                "La bibliotheque 'cryptography' n'est pas installee.\n"
                "Redemarrez l'application pour qu'elle s'installe automatiquement.")
            return
        if not self._encrypt_cfg_enabled:
            # Activation : demander le mot de passe maître
            pw = self._ask_master_password(confirm=True)
            if pw is None:
                return   # annulé
            _SESSION_MASTER_PW[0] = pw
            self._encrypt_cfg_enabled = True
        else:
            # Désactivation : repasser en JSON clair
            self._encrypt_cfg_enabled = False
            _SESSION_MASTER_PW[0] = None
        cfg = self._collect()
        cfg["encrypt_cfg"] = self._encrypt_cfg_enabled
        save_cfg(cfg); self.cfg = cfg
        self._refresh_encrypt_cfg_ui()

    def _refresh_encrypt_cfg_ui(self):
        if not hasattr(self, "_btn_encrypt_cfg"):
            return
        enabled = self._encrypt_cfg_enabled
        if enabled:
            self._btn_encrypt_cfg.config(
                text="ACTIF", fg=C["green"],
                highlightthickness=1, highlightbackground=C["green"])
        else:
            self._btn_encrypt_cfg.config(
                text="INACTIF", fg=C["muted"],
                highlightthickness=1, highlightbackground=C["muted"])

    @staticmethod
    def _ask_master_password(confirm=False, title="Mot de passe maître"):
        """
        Popup tkinter demandant le mot de passe maître.
        Si confirm=True, demande deux fois (création).
        Retourne le mot de passe str, ou None si annulé/vide.
        """
        import tkinter as _tk
        from tkinter import simpledialog as _sd

        class _PwDialog(_tk.Toplevel):
            def __init__(self, parent, confirm):
                super().__init__(parent)
                self.title(title)
                self.resizable(False, False)
                self.configure(bg=C["bg"])
                self.grab_set()
                self.result = None

                _tk.Label(self, text="Mot de passe maître :", font=FM,
                          bg=C["bg"], fg=C["text"]).grid(
                    row=0, column=0, padx=12, pady=(14, 4), sticky="w")
                self._e1 = _tk.Entry(self, show="*", font=FM,
                                     bg=C["ibg"], fg=C["ifg"],
                                     insertbackground=C["gold"],
                                     relief="flat", width=28)
                self._e1.grid(row=0, column=1, padx=(4, 12), pady=(14, 4))
                self._e1.focus_set()

                if confirm:
                    _tk.Label(self, text="Confirmer :", font=FM,
                              bg=C["bg"], fg=C["text"]).grid(
                        row=1, column=0, padx=12, pady=4, sticky="w")
                    self._e2 = _tk.Entry(self, show="*", font=FM,
                                         bg=C["ibg"], fg=C["ifg"],
                                         insertbackground=C["gold"],
                                         relief="flat", width=28)
                    self._e2.grid(row=1, column=1, padx=(4, 12), pady=4)
                else:
                    self._e2 = None

                self._lbl_err = _tk.Label(self, text="", font=FM8,
                                          bg=C["bg"], fg=C["red"])
                self._lbl_err.grid(row=2, column=0, columnspan=2, pady=(0, 4))

                btn_f = _tk.Frame(self, bg=C["bg"])
                btn_f.grid(row=3, column=0, columnspan=2, pady=(4, 12))
                _tk.Button(btn_f, text="OK", font=FB,
                           bg=C["panel"], fg=C["gold"], relief="flat",
                           padx=16, command=self._ok).pack(side="left", padx=6)
                _tk.Button(btn_f, text="Annuler", font=FL,
                           bg=C["panel"], fg=C["muted"], relief="flat",
                           padx=10, command=self.destroy).pack(side="left", padx=6)

                self.bind("<Return>", lambda e: self._ok())
                self.bind("<Escape>", lambda e: self.destroy())
                self.protocol("WM_DELETE_WINDOW", self.destroy)

            def _ok(self):
                pw = self._e1.get()
                if not pw:
                    self._lbl_err.config(text="Le mot de passe ne peut pas être vide.")
                    return
                if self._e2 is not None and pw != self._e2.get():
                    self._lbl_err.config(text="Les mots de passe ne correspondent pas.")
                    return
                self.result = pw
                self.destroy()

        # Trouver la fenêtre root active
        try:
            root = _tk._default_root
        except Exception:
            root = None
        dlg = _PwDialog(root, confirm)
        if root:
            root.wait_window(dlg)
        return dlg.result

    def _toggle_notify(self):
        """Active ou désactive la notification de retour du site."""
        self._notify_enabled = not self._notify_enabled
        cfg = self._collect()
        cfg["notify_enabled"] = self._notify_enabled
        save_cfg(cfg); self.cfg = cfg
        self._refresh_notify_ui()
        # Arrêter le watcher si on désactive
        if not self._notify_enabled and self._watcher:
            self._watcher.stop()
            self._watcher = None

    # ══════════════════════════════════════════════════════════════════════════
    # INDICATEUR DE SANTÉ — vérification externe toutes les 10 min
    # ══════════════════════════════════════════════════════════════════════════
    def _health_loop(self):
        """Lance une vérification en arrière-plan puis replanifie dans 10 min."""
        is_torr9 = getattr(self, "_active_tracker", "lacale") == "torr9"
        label = "Santé Torr9 : ⚪" if is_torr9 else "Santé La Cale : ⚪"
        self.root.after(0, lambda: self._health_var.set(label))
        self.root.after(0, lambda: self._health_lbl.config(fg=C["muted"]))
        threading.Thread(target=self._do_health_check, daemon=True).start()

    def _do_health_check(self):
        """
        Vérification en deux passes identiques au health_check complet,
        mais silencieuse (pas de log). Met à jour le voyant.

        Passe 1 — checker externe (isitdownrightnow)
        Passe 2 — HEAD direct sur le site

        Le voyant est 🟢 seulement si les deux passes sont OK.
        Si la passe 1 est ambiguë/indisponible, on se fie uniquement à la passe 2.
        """
        is_torr9 = getattr(self, "_active_tracker", "lacale") == "torr9"
        if is_torr9:
            url    = self.cfg.get("torr9_url", "https://www.torr9.net").rstrip("/")
            domain = "torr9.net"
        else:
            url    = self.cfg.get("lacale_url", "https://la-cale.space").rstrip("/")
            domain = "la-cale.space"

        ok  = False
        p1_failed = False   # True si la passe 1 dit explicitement "down"

        # ── Passe 1 : checker externe ─────────────────────────────────────
        try:
            r1 = requests.get(
                "https://www.isitdownrightnow.com/check.php",
                params={"domain": domain},
                timeout=8,
                headers={"User-Agent":
                         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/124.0.0.0 Safari/537.36"})
            body = r1.text.lower()
            if r1.status_code == 200 and "down" in body and "up" not in body:
                p1_failed = True   # checker dit explicitement "down"
        except Exception:
            pass   # checker injoignable → on ignore la passe 1

        if p1_failed:
            ok = False
        else:
            # ── Passe 2 : HEAD direct ─────────────────────────────────────
            try:
                r2 = requests.head(url, timeout=8,
                                   headers={"User-Agent":
                                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                                            "Chrome/124.0.0.0 Safari/537.36"})
                ok = r2.status_code in (200, 301, 302, 307, 308)
            except Exception:
                ok = False

        # Mise à jour dans le thread tkinter
        self.root.after(0, self._update_health_indicator, ok)
        # Replanifier dans 10 minutes (600 000 ms)
        self.root.after(60_000, self._health_loop)

    def _update_health_indicator(self, ok: bool):
        """Met à jour la boule verte/rouge dans la barre du bas."""
        is_torr9 = getattr(self, "_active_tracker", "lacale") == "torr9"
        label_ok  = "Santé Torr9 : 🟢"  if is_torr9 else "Santé La Cale : 🟢"
        label_ko  = "Santé Torr9 : 🔴"  if is_torr9 else "Santé La Cale : 🔴"
        if ok:
            self._health_var.set(label_ok)
            self._health_lbl.config(fg=C["green"])
        else:
            self._health_var.set(label_ko)
            self._health_lbl.config(fg=C["red"])
            # Déclencher le watcher si la notification est activée
            if self._notify_enabled and (
                    not self._watcher or not self._watcher.active):
                self._start_watcher()

    def _refresh_notify_ui(self):
        """Met à jour l'aspect visuel du toggle et de l'intervalle."""
        if not hasattr(self, "_btn_notify"):
            return
        if self._notify_enabled:
            self._btn_notify.config(
                text=t("notify_on"), fg=C["green"],
                highlightthickness=1, highlightbackground=C["green"])
        else:
            self._btn_notify.config(
                text=t("notify_off"), fg=C["muted"],
                highlightthickness=1, highlightbackground=C["muted"])
        # Afficher/masquer le frame intervalle
        if hasattr(self, "_notify_interval_frame"):
            if self._notify_enabled:
                self._notify_interval_frame.pack(side="left", padx=(8, 0))
            else:
                self._notify_interval_frame.pack_forget()

    def _start_watcher(self):
        """Démarre le watcher si la notification est activée (ou l'active auto)."""
        # Activer automatiquement la notification si elle ne l'était pas
        if not self._notify_enabled:
            self._notify_enabled = True
            cfg = self._collect()
            cfg["notify_enabled"] = True
            save_cfg(cfg); self.cfg = cfg
            if hasattr(self, "_btn_notify"):
                self.root.after(0, self._refresh_notify_ui)

        # Arrêter un watcher précédent si actif
        if self._watcher and self._watcher.active:
            self._watcher.stop()

        is_torr9 = getattr(self, "_active_tracker", "lacale") == "torr9"
        if is_torr9:
            url      = self.cfg.get("torr9_url", "https://www.torr9.net")
            site_lbl = "Torr9"
        else:
            url      = self.cfg.get("lacale_url", "https://la-cale.space")
            site_lbl = "La Cale"
        interval = int(self.cfg.get("notify_interval", "10") or "10")

        self._watcher = SiteWatcher(url, interval, self._on_site_back, site_label=site_lbl)
        self._watcher.start()
        self._log(
            f"  Surveillance de la santé de {site_lbl} par un watcher extérieur activée"
            f" — vérification toutes les {interval} min.", "muted")

    def _on_site_back(self):
        """Callback appelé par le watcher quand le site revient."""
        is_torr9 = getattr(self, "_active_tracker", "lacale") == "torr9"
        site_lbl = "Torr9" if is_torr9 else "La Cale"
        now = time.strftime("%Hh%M")
        self.root.after(0, self._log,
                        f"✓ {site_lbl} de retour ({now}) — vous pouvez relancer l'upload.", "ok")
        self.root.after(0, self.status.set, f"  {site_lbl} revenu à {now} ✓")
        # Jouer le son ARR! (hors lecteur, une seule fois, en parallèle)
        threading.Thread(target=self._play_arr, daemon=True).start()

    def _ensure_arr(self):
        """Télécharge arr.ogg si absent."""
        if ARR_FILE.exists():
            return True
        if not _REQUESTS_OK:
            return False
        MUSIC_DIR.mkdir(parents=True, exist_ok=True)
        for url in ARR_URLS:
            try:
                r = requests.get(url, timeout=15,
                                 headers={"User-Agent":
                                          "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                if r.status_code == 200 and len(r.content) > 1000:
                    ARR_FILE.write_bytes(r.content)
                    return True
            except Exception:
                pass
        return False

    def _play_arr(self):
        """Joue arr.ogg sur un channel séparé — simultané avec le lecteur."""
        if not _PYGAME_OK:
            return
        if not self._ensure_arr():
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            sound = pygame.mixer.Sound(str(ARR_FILE))
            # Channel 1 réservé au son ARR (channel 0 = musique de fond)
            ch = pygame.mixer.Channel(7)
            ch.play(sound)   # play une seule fois (pas de loop)
        except Exception:
            pass
        # Le watcher s'est arrêté de lui-même — rester prêt à se réactiver
        # si le site retombe (géré par _start_watcher au prochain health check KO)

    def _on_field_change(self, *_):
        """Appelée à chaque modification d'un champ."""
        if self._loading:
            return
        if self._autosave_job:
            self.root.after_cancel(self._autosave_job)
        self._set_dirty(True)
        # Sauvegarde auto seulement si activée
        if self._autosave_enabled:
            self._autosave_job = self.root.after(800, self._autosave)

    def _autosave(self):
        """Sauvegarde silencieuse automatique."""
        self._autosave_job = None
        if not self._autosave_enabled:
            return
        cfg = self._collect()
        save_cfg(cfg)
        self.cfg = cfg
        self._set_dirty(False)

    def _update_conn_btn(self):
        """Met à jour le visuel du bouton toggle API/Web."""
        if self._conn_mode == "api":
            self.b_conn.config(
                text=f"  {t('conn_api')}  ",
                fg=C["green"], highlightthickness=1,
                highlightbackground=C["green"],
                cursor="hand2")
        else:
            self.b_conn.config(
                text=f"  {t('conn_web')}  ",
                fg=C["gold"], highlightthickness=1,
                highlightbackground=C["gold"],
                cursor="hand2")
        # Afficher/masquer les frames selon le mode
        if hasattr(self, "_frame_api") and hasattr(self, "_frame_web"):
            if self._conn_mode == "api":
                self._frame_api.grid()
                self._frame_web.grid_remove()
            else:
                self._frame_api.grid_remove()
                self._frame_web.grid()

    def _toggle_conn_mode(self):
        """Bascule entre mode API et mode Web."""
        self._conn_mode = "api" if self._conn_mode == "web" else "web"
        self._update_conn_btn()
        cfg = self._collect()
        cfg["conn_mode"] = self._conn_mode
        save_cfg(cfg); self.cfg = cfg
        self._log_active_config()

    def _log_active_config(self):
        """Affiche la configuration active dans le log."""
        active = getattr(self, "_active_tracker", "lacale")
        conn   = "API" if self._conn_mode == "api" else "Web"
        tracker_name = "Torr9" if active == "torr9" else "La Cale"
        client = getattr(self, "_torrent_client", "qbittorrent").upper()
        self._log(f"  Configuration active : {tracker_name}/{conn}/{client}", "ok")

    def _toggle_autosave(self):
        """Active ou désactive la sauvegarde automatique."""
        self._autosave_enabled = not self._autosave_enabled
        # Sauvegarder l'état dans la config
        cfg = self._collect()
        cfg["autosave_enabled"] = self._autosave_enabled
        save_cfg(cfg); self.cfg = cfg
        # Mettre à jour le bouton
        if self._autosave_enabled:
            self.b_autosave.config(fg=C["green"],
                                   text=t("btn_autosave_on"),
                                   highlightbackground=C["green"])
            self._log("Sauvegarde automatique activée.", "ok")
        else:
            self.b_autosave.config(fg=C["muted"],
                                   text=t("btn_autosave_off"),
                                   highlightbackground=C["muted"])
            self._log("Sauvegarde automatique désactivée.", "muted")

    def _clear_config(self):
        """Efface la configuration sauvegardée (fichier .json)."""
        if not messagebox.askyesno("", t("confirm_clear_cfg")):
            return
        # Supprimer le fichier config
        try:
            if CONFIG_FILE.exists():
                CONFIG_FILE.unlink()
        except Exception as e:
            self._log(f"Erreur suppression config : {e}", "err")
            return
        # Recharger les valeurs par défaut
        self._loading = True
        self.cfg = load_cfg()
        for k, v in self.vars.items():
            v.set(self.cfg.get(k, ""))
        self.grade_film_var.set(get_grades()[0])
        self._loading = False
        self._set_dirty(False)
        self.status.set(t("status_saved"))
        self._log("Configuration effacée — valeurs par défaut restaurées.", "ok")

    def _set_dirty(self, dirty):
        """Indicateur de modifications non sauvegardées (bouton save supprimé)."""
        pass  # autosave gère tout — le bouton SAUVEGARDER n'existe plus

    def _collect(self):
        cfg = {k: v.get().strip() for k, v in self.vars.items()}
        # États gérés hors self.vars
        cfg["conn_mode"]       = getattr(self, "_conn_mode", "web")
        cfg["torrent_client"]  = getattr(self, "_torrent_client", "qbittorrent")
        cfg["active_tracker"]  = getattr(self, "_active_tracker", "lacale")
        cfg["autosave_enabled"]= getattr(self, "_autosave_enabled", True)
        cfg["notify_enabled"]  = getattr(self, "_notify_enabled", False)
        cfg["save_logs"]       = getattr(self, "_save_logs_enabled", True)
        cfg["save_curl"]       = getattr(self, "_save_curl_enabled", False)
        cfg["check_updates"]   = getattr(self, "_check_updates_enabled", True)
        cfg["encrypt_cfg"]     = getattr(self, "_encrypt_cfg_enabled", True)
        # Thème : on stocke la clé interne, pas le label affiché
        if "ui_theme" in self.vars:
            label = self.vars["ui_theme"].get().strip()
            cfg["ui_theme"] = next((k for k,v in THEME_NAMES.items() if v == label), "gold")
        # Clés Deluge (peuvent ne pas être dans self.vars si UI non initialisée)
        for k in ("deluge_url", "deluge_pass", "deluge_films_path", "deluge_series_path",
                  "vuze_url", "vuze_user", "vuze_pass", "vuze_films_path", "vuze_series_path"):
            if k not in cfg:
                cfg[k] = DEFAULTS.get(k, "")
        # Champ dev (invisible) — jamais sauvegardé dans la config
        if hasattr(self, "_suffix_var"):
            cfg["_dev_field"] = self._suffix_var.get()
        return cfg

    def _browse(self, key):
        """
        Ouvre le sélecteur de dossier.
        Note : le sélecteur tkinter ne peut pas naviguer vers les partages UNC
        (\\\\NAS\\...). Dans ce cas, saisir le chemin directement dans le champ.
        Le chemin est normalisé en backslashes Windows avant stockage.
        """
        d = filedialog.askdirectory(title="…")
        if d:
            # tkinter retourne des forward slashes — normaliser en backslashes
            # pour les chemins UNC Windows (\NAS\...) afin que Path().exists() fonctionne
            import os
            d_norm = os.path.normpath(d)
            self.vars[key].set(d_norm)

    # ── Log ───────────────────────────────────────────────────────────────────
    def _log(self, msg, tag=None):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n", tag or "")
        self.log_box.see("end")
        self.log_box.config(state="disabled")
        # Accumuler dans le buffer de session (pour export en fin de session)
        if not hasattr(self, "_session_log_buf"):
            self._session_log_buf = []
        self._session_log_buf.append(msg)

    def _on_log_right_click(self, event):
        """Menu contextuel clic droit sur le log."""
        menu = tk.Menu(self.root, tearoff=0,
                       bg=C["panel"], fg=C["text"],
                       activebackground=C["border"],
                       activeforeground=C["gold"],
                       relief="flat", bd=0)
        # Copier la sélection si elle existe, sinon tout copier
        try:
            sel = self.log_box.get("sel.first", "sel.last")
        except tk.TclError:
            sel = ""
        if sel:
            menu.add_command(label="Copier la sélection",
                             command=lambda: self.root.clipboard_clear() or
                             self.root.clipboard_append(sel))
        menu.add_command(label="Tout copier",
                         command=lambda: self.root.clipboard_clear() or
                         self.root.clipboard_append(
                             self.log_box.get("1.0", "end")))
        menu.tk_popup(event.x_root, event.y_root)

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    def _set_prog(self, pct, lbl=""):
        if pct < 0:
            # Mode label seul : afficher le texte sans toucher à la barre
            if lbl:
                self.prog_lbl.config(text=lbl)
                self._lbl_prog_above.grid()
            return
        self.prog_bar["value"] = pct * 100
        if pct > 0:
            # Garder le compteur s'il est déjà affiché
            current = self.prog_lbl.cget("text")
            count_part = current.split("·")[0].strip() if "·" in current else ""
            pct_str = f"{int(pct*100)}%"
            self.prog_lbl.config(text=f"{count_part} · {pct_str}" if count_part else pct_str)
            self._lbl_prog_above.grid()
        else:
            self.prog_lbl.config(text=lbl if lbl else "")
            if lbl:
                self._lbl_prog_above.grid()
            else:
                self._lbl_prog_above.grid_remove()

    def _set_prog_count(self, current, total):
        if total > 0:
            pct_part = ""
            existing = self.prog_lbl.cget("text")
            if "·" in existing:
                pct_part = " · " + existing.split("·")[-1].strip()
            elif existing:
                pct_part = " · " + existing
            self.prog_lbl.config(text=f"{current}/{total}{pct_part}")
        else:
            self.prog_lbl.config(text="")

    # ── Actions ───────────────────────────────────────────────────────────────
    def _ask_requests(self):
        if messagebox.askyesno(t("req_title"), t("req_msg")):
            threading.Thread(target=self._install_requests, daemon=True).start()

    def _install_requests(self):
        self.root.after(0, self._log, "Installation de 'requests'...", "gold")
        try:
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--quiet", "requests"],
                timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                **kwargs)
            self.root.after(0, self._log,
                            "'requests' installé. Redémarrez BLACK FLAG.", "ok")
        except Exception as e:
            self.root.after(0, self._log,
                            f"Échec : {e}\npip install requests", "err")

    def _save(self):
        cfg = self._collect()
        save_cfg(cfg); self.cfg = cfg
        self._set_dirty(False)
        self.status.set(t("status_saved"))
        self._log(t("log_saved"), "ok")

    def _validate(self, cfg):
        errs = []
        if not cfg.get("films_dir") and not cfg.get("series_dir"):
            errs.append(t("err_no_dir"))

        is_torr9 = (cfg.get("active_tracker", "lacale") == "torr9")

        if is_torr9:
            if not cfg.get("torr9_user"):  errs.append("Pseudonyme Torr9 requis")
            if not cfg.get("torr9_pass"):  errs.append("Mot de passe Torr9 requis")
        else:
            if not cfg.get("lacale_user"):  errs.append(t("err_no_user"))
            if not cfg.get("lacale_pass"):  errs.append(t("err_no_pass"))
            if not cfg.get("tracker_url"):  errs.append(t("err_no_tracker"))

        client_type = cfg.get("torrent_client", "qbittorrent")
        if client_type == "qbittorrent":
            if not cfg.get("qb_url"):   errs.append(t("err_no_qb"))
        elif client_type == "transmission":
            if not cfg.get("tr_url"):   errs.append("URL Transmission requise")
        elif client_type == "deluge":
            if not cfg.get("deluge_url"):  errs.append("URL Deluge requise")
            if not cfg.get("deluge_pass"): errs.append("Mot de passe Deluge requis")
        elif client_type == "vuze":
            if not cfg.get("vuze_url"):    errs.append("URL Vuze requise")
            if not cfg.get("vuze_pass"):   errs.append("Code de pairing Vuze requis")
        if not _REQUESTS_OK:            errs.append(t("err_no_requests"))
        return errs

    def _launch(self):
        if self.running: return
        cfg  = self._collect()
        errs = self._validate(cfg)
        if errs:
            messagebox.showerror(t("err_title"), "\n".join(f"• {e}" for e in errs))
            return
        save_cfg(cfg); self.cfg = cfg
        self._clear_log()
        self._log(t("log_start"), "gold")
        self._log(t("log_films",  d=cfg.get("films_dir","—"),  m=cfg.get("max_movies",1)), "muted")
        self._log(t("log_series", d=cfg.get("series_dir","—"), m=cfg.get("max_series",1)), "muted")
        self._log("─" * 60, "muted")

        # ── Vérification TMDb Bearer Token ────────────────────────────────────
        if cfg.get("tmdb_token", "").strip():
            self._log("  TMDb Bearer Token : Chargé ✓", "ok")
        else:
            self._log("  TMDb Bearer Token : Manquant — les métadonnées ne seront pas récupérées.", "err")
            self.running = False
            self.b_launch   .config(state="normal")
            self.b_stop     .config(state="disabled")
            self.b_autosave .config(state="normal")
            self.b_clear_cfg.config(state="normal")
            self.status.set(t("status_ready"))
            return

        # ── Vérification MediaInfo ────────────────────────────────────────────
        import platform as _platform
        _os = _platform.system()

        # Chemins configurés pour chaque OS
        _mi_candidates = {
            "MediaInfo.dll":      Path(cfg.get("mediainfo_dll",   str(APP_DIR / "MediaInfo.dll"))).resolve(),
            "libmediainfo.dylib": Path(cfg.get("mediainfo_dylib", str(APP_DIR / "libmediainfo.dylib"))).resolve(),
            "libmediainfo.so":    Path(cfg.get("mediainfo_so",    str(APP_DIR / "libmediainfo.so"))).resolve(),
        }

        # Fichier attendu selon l'OS courant
        _mi_expected = {
            "Windows": "MediaInfo.dll",
            "Darwin":  "libmediainfo.dylib",
            "Linux":   "libmediainfo.so",
        }.get(_os, "MediaInfo.dll")

        _mi_found = next((n for n, p in _mi_candidates.items() if p.exists()), None)

        if _mi_found:
            self._log(f"  MediaInfo ({_mi_found}) : Chargé ✓", "ok")
        else:
            _mi_url = {
                "Windows": "mediaarea.net/en/MediaInfo/Download/Windows",
                "Darwin":  "mediaarea.net/en/MediaInfo/Download/Mac_OS",
                "Linux":   "mediaarea.net/en/MediaInfo/Download/Ubuntu",
            }.get(_os, "mediaarea.net/en/MediaInfo/Download/Windows")
            self._log(f"  MediaInfo ({_mi_expected}) : Manquant — téléchargez-le sur {_mi_url}", "err")
            self.running = False
            self.b_launch   .config(state="normal")
            self.b_stop     .config(state="disabled")
            self.b_autosave .config(state="normal")
            self.b_clear_cfg.config(state="normal")
            self.status.set(t("status_ready"))
            return
        self.running = True
        self._start_session()
        self.b_launch   .config(state="disabled")
        self.b_stop     .config(state="normal")
        self.b_autosave .config(state="disabled")
        self.b_clear_cfg.config(state="disabled")
        self.status.set(t("status_running"))

        def prog(pct, lbl): self.root.after(0, self._set_prog, pct, lbl)
        def done():         self.root.after(0, self._on_done)
        def log(m, tx=None): self.root.after(0, self._log, m, tx)

        self.worker = Worker(cfg, log, done, prog,
                             start_watcher_cb=self._start_watcher,
                             set_count_cb=lambda c, t: self.root.after(
                                 0, self._set_prog_count, c, t),
                             curl_cb=lambda cmd: self._session_curl_buf.append(cmd))
        threading.Thread(target=self.worker.run, daemon=True).start()

    def _start_session(self):
        """Réinitialise le buffer log et curl pour la nouvelle session."""
        self._session_log_buf  = []
        self._session_curl_buf = []   # rempli par Worker via callback
        # Timestamp à la seconde pour éviter les écrasements
        self._session_ts       = time.strftime("%Y-%m-%d_%Hh%M%S")

    def _export_session_files(self):
        """
        Exporte le log et/ou le fichier curl de la session courante.
        Appelé à chaque fin de session (stop ou fin naturelle).
        """
        ts       = getattr(self, "_session_ts", time.strftime("%Y-%m-%d_%Hh%M%S"))
        exported = []
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)

            # ── Fichier LOG ───────────────────────────────────────────────────
            if getattr(self, "_save_logs_enabled", False):
                buf = getattr(self, "_session_log_buf", [])
                if buf:
                    log_path = LOG_DIR / f"blackflag_{ts}.log"
                    log_path.write_text("\n".join(buf) + "\n", encoding="utf-8")
                    exported.append(("log", str(log_path)))

            # ── Fichier CURL ──────────────────────────────────────────────────
            if getattr(self, "_save_curl_enabled", False):
                curl_buf = getattr(self, "_session_curl_buf", [])
                if curl_buf:
                    curl_path = LOG_DIR / f"blackflag_{ts}.curl.sh"
                    curl_path.write_text(
                        "#!/bin/bash\n# BLACK FLAG — commandes curl de la session\n\n"
                        + "\n\n".join(curl_buf) + "\n",
                        encoding="utf-8")
                    exported.append(("curl", str(curl_path)))
        except Exception as e:
            self._log(f"  Erreur export fichiers : {e}", "err")
            return

        # Messages dans le log UI en rouge
        for kind, path in exported:
            fname = Path(path).name
            if kind == "log":
                self._log(f"  Fichier log généré  →  {fname}", "err")
            else:
                self._log(f"  Fichier curl généré →  {fname}", "err")

    def _on_done(self):
        self._export_session_files()
        self.running = False; self.worker = None
        self.b_launch   .config(state="normal")
        self.b_stop     .config(state="disabled")
        self.b_autosave .config(state="normal")
        self.b_clear_cfg.config(state="normal")
        self._set_prog(0, "")
        self.status.set(t("status_done"))

    def _stop(self):
        if self.worker and self.running:
            self.worker.stop()
            self.running = False
            self.b_stop.config(state="disabled")
            self._log(t("log_stop"), "err")
            self.status.set(t("status_stopping"))
            # L'export est géré par _on_done quand le Worker se termine

    def _close(self):
        if self.running and not messagebox.askyesno(
                t("quit_title"), t("quit_msg")): return
        if self.worker: self.worker.stop()
        if self._watcher: self._watcher.stop()
        try:
            if _PYGAME_OK and pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.quit()
        except Exception:
            pass
        self.root.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    root.minsize(900, 600)
    root.geometry("1100x750")
    try:
        ico = APP_DIR / "blackflag.ico"
        if ico.exists(): root.iconbitmap(str(ico))
    except Exception:
        pass
    # Barre de titre sombre (Windows 10 build 19041+ / Windows 11)
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int))
    except Exception:
        pass
    App(root)
    root.mainloop()
