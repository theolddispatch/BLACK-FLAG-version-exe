#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BLACK FLAG v1.1 — Upload automatique vers La Cale
Développé par Theolddispatch & The40n8  ·  version exécutable

Logique séries :
  - Scan par SAISON (dossier) : Breaking Bad/Saison 1/ → 1 torrent multi-fichiers
  - Identification via nom du dossier SÉRIE (dossier parent)
  - Release name : Titre.S01.MULTi.1080p.WEB-DL.x265-GROUPE
  - TMDb : recherche série par nom + extraction saison du dossier
"""

# ══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP requests
# ══════════════════════════════════════════════════════════════════════════════
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

APP_VERSION = "1.1"

# URL du fichier source sur GitHub pour vérification de version
_UPDATE_URL = (
    "https://raw.githubusercontent.com/theolddispatch/"
    "BLACK-FLAG-version-exe/refs/heads/main/"
    "Script%20%C3%A0%20%C3%A9x%C3%A9cuter%20si%20vous%20avez%20Python%20"
    "(beaucoup%20l'ont%20par%20d%C3%A9faut)/BLACK.FLAG%20version%20exe.py"
)
_UPDATE_PAGE = (
    "https://github.com/theolddispatch/BLACK-FLAG-version-exe/blob/main/"
    "Script%20%C3%A0%20%C3%A9x%C3%A9cuter%20si%20vous%20avez%20Python%20"
    "(beaucoup%20l'ont%20par%20d%C3%A9faut)/BLACK.FLAG%20version%20exe.py"
)

def _check_update_available() -> bool:
    """
    Télécharge le fichier source GitHub et compare la version.
    Retourne True si une version plus récente est disponible.
    """
    if not _REQUESTS_OK:
        return False
    try:
        r = requests.get(_UPDATE_URL, timeout=10,
                         headers={"User-Agent": "BLACK-FLAG-updater/1.1"})
        if r.status_code != 200:
            return False
        # Scan les 150 premières lignes (APP_VERSION est ligne ~111)
        for line in r.text.splitlines()[:150]:
            stripped = line.strip()
            if stripped.startswith("APP_VERSION") and "=" in stripped:
                remote = stripped.split("=")[1].strip().strip("\"'")
                def _v(s):
                    try: return tuple(int(x) for x in s.strip().split("."))
                    except: return (0,)
                return _v(remote) > _v(APP_VERSION)
    except Exception:
        pass
    return False

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
    "save_curl":       True,
    "check_updates":   True,
}

def load_cfg():
    d = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        try: d.update(json.loads(CONFIG_FILE.read_text("utf-8")))
        except Exception: pass
    return d

def save_cfg(d):
    try: CONFIG_FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False), "utf-8")
    except Exception: pass

# ══════════════════════════════════════════════════════════════════════════════
# PARSING — FILMS (fichier individuel)
# ══════════════════════════════════════════════════════════════════════════════
def parse_filename(filename):
    stem = Path(filename).stem
    su   = stem.upper()

    m    = re.search(r'(?<!\d)((?:19|20)\d{2})(?!\d)', su)
    year = m.group(1) if m else ""
    if year:
        raw = re.split(re.escape(year), stem, flags=re.I, maxsplit=1)[0]
    else:
        raw = re.split(r'(?i)[._](?:1080p|720p|2160p|4k|bluray|web.?dl|webrip|hdtv|x264|x265|hevc)', stem)[0]
    title = re.sub(r'[._\-]', ' ', raw).strip()

    # Nettoyer les parasites scène : [Torrent911.vc], (Torrent911), préfixes sites
    title = re.sub(r'^\s*\[.*?\]\s*', '', title)          # supprimer [xxx] en début
    title = re.sub(r'^\s*\(.*?\)\s*', '', title)          # supprimer (xxx) en début
    title = re.sub(r'\(?\s*$', '', title).strip()          # supprimer parenthèse orpheline en fin
    title = title.strip()

    res = ""
    if   re.search(r'2160P|4K|UHD', su): res = "2160p"
    elif re.search(r'1080P', su):         res = "1080p"
    elif re.search(r'720P',  su):         res = "720p"
    elif re.search(r'480P',  su):         res = "480p"

    src = "WEB"
    for pat, val in [
        (r'COMPLETE.UHD.BLU', "COMPLETE.UHD.BLURAY"),
        (r'COMPLETE.BLU',     "COMPLETE.BLURAY"),
        (r'BLU.?RAY.REMUX|BD.REMUX', "BluRay.REMUX"),
        (r'(?<!UHD)REMUX',   "REMUX"),
        (r'4KLIGHT',         "4KLight"),
        (r'HDLIGHT',         "HDLight"),
        (r'BLU.?RAY|BDRIP',  "BluRay"),
        (r'WEB.?DL|WEBDL',   "WEB-DL"),
        (r'WEBRIP',          "WEBRip"),
        (r'DVDRIP',          "DVDRip"),
        (r'HDTV',            "HDTV"),
    ]:
        if re.search(pat, su): src = val; break

    vc = "x264"
    for pat, val in [(r'X265|H265|HEVC',"x265"),(r'X264|H264|AVC',"x264"),
                     (r'AV1',"AV1"),(r'VC.?1',"VC-1")]:
        if re.search(pat, su): vc = val; break

    ac = "AAC"
    for pat, val in [(r'TRUEHD',"TrueHD"),(r'EAC3|E-AC3|DDP',"EAC3"),
                     (r'AC3|\bDD\b',"AC3"),(r'DTS.?X\b',"DTS-X"),
                     (r'DTS.HD.MA',"DTS-HD.MA"),(r'DTS.HD',"DTS-HD"),
                     (r'\bDTS\b',"DTS"),(r'\bFLAC\b',"FLAC"),(r'\bOPUS\b',"OPUS")]:
        if re.search(pat, su): ac = val; break

    ach   = next((v for p,v in [(r'7\.1',"7.1"),(r'5\.1',"5.1"),(r'2\.0',"2.0")] if re.search(p,su)),"")
    atmos = "Atmos" if re.search(r'ATMOS', su) else ""

    hdr = ""
    if   re.search(r'HDR10\+|HDR10PLUS', su): hdr = "HDR10+"
    elif re.search(r'HDR', su):                hdr = "HDR"
    if   re.search(r'\bDV\b|DOLBY.?VISION', su): hdr = (hdr+".DV") if hdr else "DV"

    imax = "iMAX" if re.search(r'IMAX', su) else ""

    plat = ""
    for code, pat in [("NF",r'\.NF\.|NETFLIX'),("AMZN",r'AMZN|AMAZON'),
                      ("DSNP",r'DSNP|DISNEY'),("ATVP",r'ATVP'),
                      ("MAX",r'HMAX|\.MAX\.'),("ADN",r'\.ADN\.')]:
        if re.search(pat, su): plat = code; break

    lang = "FRENCH"
    for pat, val in [(r'MULTI.*VFF|MULTI.*TRUEFRENCH',"MULTi.VFF"),
                     (r'MULTI.*VFQ',"MULTi.VFQ"),(r'MULTI',"MULTi"),
                     (r'TRUEFRENCH|VFF',"TRUEFRENCH"),(r'VOSTFR',"VOSTFR"),
                     (r'FRENCH',"FRENCH"),(r'DUAL',"DUAL")]:
        if re.search(pat, su): lang = val; break

    ed = ""
    for pat, tag in [(r'\.DC\.|DIRECTOR.?S.?CUT',".DC"),(r'EXTENDED',".EXTENDED"),
                     (r'UNRATED',".UNRATED"),(r'REMASTER',".REMASTERED"),
                     (r'CRITERION',".CRiTERION")]:
        if re.search(pat, su): ed += tag
    ed = ed.lstrip(".")

    grp = ""
    m = re.search(r'-([A-Za-z0-9]+)$', stem)
    if m: grp = m.group(1)

    return dict(title=title, year=year, res=res, src=src, vc=vc, ac=ac,
                ach=ach, atmos=atmos, hdr=hdr, imax=imax, plat=plat,
                lang=lang, edition=ed, group=grp,
                ext=Path(filename).suffix.lower())


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
    """
    Analyse un dossier de saison et retourne ses métadonnées.
    Exemples de noms supportés :
      Saison 1 / Season 1 / S01 / Saison 01 / S1
    Retourne : { series_name, season_num, files, tags_from_episodes }
    """
    series_dir  = season_dir.parent
    # Si season_dir est directement le dossier de la série (pas de sous-dossier saison)
    # alors series_dir pointe vers la racine — on utilise season_dir.name comme nom
    # Détection : le dossier parent ne contient pas de dossiers de saison typiques
    if not re.search(r'(?:saison|season|s\d)', season_dir.name, re.I):
        # season_dir EST le dossier de la série
        series_name = re.sub(r'\s*\((?:19|20)\d{2}\)\s*$', '', season_dir.name).strip()
    else:
        series_name = re.sub(r'\s*\((?:19|20)\d{2}\)\s*$', '', series_dir.name).strip()

    # Numéro de saison depuis le nom du dossier
    season_num = 1
    m = re.search(r'(?:saison|season|s)\s*(\d{1,2})', season_dir.name, re.I)
    if m:
        season_num = int(m.group(1))

    # Fichiers vidéo dans ce dossier (pas récursif — les épisodes sont au même niveau)
    files = sorted(f for f in season_dir.iterdir()
                   if f.is_file() and f.suffix.lower() in VIDEO_EXTS)

    # Tags techniques : on les extrait du premier épisode trouvé
    tags = {}
    if files:
        tags = parse_filename(files[0].name)

    # Taille totale de la saison
    total_size = sum(f.stat().st_size for f in files)

    return dict(
        series_name=series_name,
        season_num=season_num,
        season_tag=f"S{season_num:02d}",
        files=files,
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


def scan_seasons(series_root: Path):
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


def make_torrent_single(fp: Path, tracker: str, prog_cb=None) -> bytes:
    """Torrent single-file (films)."""
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
    info = {"name": fp.name, "piece length": pl, "pieces": bytes(pieces),
            "length": sz, "private": 1, "source": "lacale"}
    return bencode({"announce": tracker, "info": info,
                    "created by": "BLACK FLAG", "creation date": int(time.time())})


def make_torrent_multi(folder_name: str, files: list, tracker: str, prog_cb=None) -> bytes:
    """
    Torrent multi-fichiers (saisons de séries).
    folder_name : nom du dossier racine dans le torrent (= release_name)
    files       : liste de Path, tous dans le même dossier physique
    """
    total_size = sum(f.stat().st_size for f in files)
    pl         = _piece_length(total_size)
    pieces     = bytearray()
    read       = 0

    for fp in files:
        with open(fp, "rb") as fh:
            buf = b""
            while True:
                chunk = fh.read(pl - len(buf))
                if not chunk:
                    break
                buf += chunk
                if len(buf) == pl:
                    pieces += hashlib.sha1(buf).digest()
                    read   += len(buf)
                    buf     = b""
                    if prog_cb: prog_cb(read / total_size)
        if buf:
            pieces += hashlib.sha1(buf).digest()
            read   += len(buf)
            if prog_cb: prog_cb(read / total_size)

    file_list = [{"length": f.stat().st_size,
                  "path":   [f.name]} for f in files]
    info = {
        "name":         folder_name,
        "piece length": pl,
        "pieces":       bytes(pieces),
        "files":        file_list,
        "private":      1,
        "source":       "lacale",
    }
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
            ch = self._get("/api/auth/altcha/challenge?scope=login",
                           headers={"Accept": "application/json",
                                    "Referer": self.url + "/login"}).json()
            token = self._solve_altcha(ch)
            if token: self.log("  PoW Altcha résolu.", "muted")
        except Exception:
            pass
        payload = {"email": email, "password": pwd,
                   "formLoadedAt": int(time.time() * 1000)}
        if token: payload["altcha"] = token
        r = self._post("/api/auth/login", json=payload,
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
            cats = self._get("/api/internal/categories",
                             headers={"Accept": "application/json"}).json()
            if not isinstance(cats, list):
                cats = cats.get("data") or cats.get("categories") or []
            for c in cats:
                name = (c.get("name") or "").lower()
                if re.search(r"film|movie", name) and not self.cat_film:
                    self.cat_film = c["id"]
                if re.search(r"serie|tv|show", name) and not self.cat_series:
                    self.cat_series = c["id"]
        except Exception:
            pass
        if not self.cat_film:   self.cat_film   = "cmjoyv2cd00027eryreyk39gz"
        if not self.cat_series: self.cat_series = self.cat_film   # fallback
        self.log(f"  Catégorie Films   : {self.cat_film}", "muted")
        self.log(f"  Catégorie Séries  : {self.cat_series}", "muted")

        # Quais depuis la catégorie films
        try:
            groups = self._get(f"/api/internal/categories/{self.cat_film}/terms",
                               headers={"Accept": "application/json"}).json()
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
        except Exception:
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
        except Exception:
            pass
        if not self.cat_film:   self.cat_film   = "cmjoyv2cd00027eryreyk39gz"
        if not self.cat_series: self.cat_series = self.cat_film
        self.log(f"  Catégorie Films   : {self.cat_film}", "muted")
        self.log(f"  Catégorie Séries  : {self.cat_series}", "muted")

    def upload_api(self, passkey, name, tb, nfo, desc,
                   tmdb_id=None, is_series=False, terms=None):
        """Upload via API externe /api/external/upload."""
        cat   = self.cat_series if is_series else self.cat_film
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

    def upload(self, name, tb, nfo, desc, tmdb_id=None, is_series=False, terms=None):
        """Upload via API interne (mode Web — simulation navigateur)."""
        cat   = self.cat_series if is_series else self.cat_film
        files = {"file": (f"{name}.torrent", tb, "application/x-bittorrent")}
        if nfo: files["nfoFile"] = (f"{name}.nfo", nfo.encode("utf-8"), "text/plain")
        data  = {"title": name, "categoryId": cat, "isAnonymous": "false",
                 "nfoText": nfo or "", "description": desc or ""}
        if tmdb_id:
            data["tmdbId"]   = str(tmdb_id)
            data["tmdbType"] = "TV" if is_series else "MOVIE"
        r = self.sess.post(self.url + "/api/internal/torrents/upload",
                           data=data, files=files,
                           params=[("termIds[]", t) for t in (terms or [])],
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
# TMDb CLIENT
# ══════════════════════════════════════════════════════════════════════════════
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

    def add(self, tb, save_path, torrent_name):
        try:
            r = self.sess.post(f"{self.url}/api/v2/torrents/add",
                               files={"torrents": (torrent_name + ".torrent", tb,
                                                   "application/x-bittorrent")},
                               data={"savepath": save_path,
                                     "skip_checking": "true", "paused": "false"},
                               timeout=30)
            return r.status_code == 200 and "ok" in r.text.lower()
        except Exception: return False


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
            r = requests.post(
                f"{self.url}/transmission/rpc",
                json=payload,
                headers={"X-Transmission-Session-Id": self._sid},
                auth=self._auth, timeout=30)
            data = r.json()
            result = data.get("result", "")
            return result == "success"
        except Exception:
            return False



def make_bbcode(title, year_or_tag, overview, poster, res, vc, ac, lang,
                size, rating, genres, cast, hdr, is_series=False, season_num=None):
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
    bb += f"[b]Langue :[/b] {lang}\n[b]Taille totale :[/b] {ss}"
    if cast:
        bb += "\n\n[color=#eab308][b]--- CASTING ---[/b][/color]\n\n"
        for a in cast[:5]:
            bb += f"[b]{a['name']}[/b] ({a.get('character', '')})\n"
    bb += "\n\n[i]Généré par BLACK FLAG[/i]\n[/center]"
    return bb


# ══════════════════════════════════════════════════════════════════════════════
# WORKER — Thread d'upload
# ══════════════════════════════════════════════════════════════════════════════
class Worker:
    def __init__(self, cfg, log, done, prog, start_watcher_cb=None, set_count_cb=None):
        self.cfg  = cfg
        self.log  = log
        self.done = done
        self.prog = prog
        self._start_watcher_cb = start_watcher_cb
        self._set_count        = set_count_cb or (lambda c, t: None)
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

        # ── Clients ──────────────────────────────────────────────────────────
        lc = LaCale(cfg["lacale_url"], self.log)

        # ── Health check (2 passes) ───────────────────────────────────────
        self.log("Vérification de l'état du site La Cale...", "gold")

        # Code de bypass : si le champ dev contient le code, on saute le check
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
        else:
            qb = QBit(cfg["qb_url"], cfg["qb_user"], cfg["qb_pass"], self.log)

        hist   = (set(HIST_FILE.read_text("utf-8", errors="ignore").splitlines())
                  if HIST_FILE.exists() else set())
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
                files = sorted(p for p in fp_root.rglob("*")
                               if p.is_file() and p.suffix.lower() in VIDEO_EXTS)
                self.log(f"  {len(files)} fichier(s) trouvé(s).", "muted")
                uploaded = 0

                for fp in files:
                    if self._stop.is_set() or uploaded >= max_films: break
                    fn = fp.name
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
                        self.log(f"  TMDb → \"{p['title']}\" ({year})...", "muted")
                        res = tmdb.search_movie(p["title"], year or None)
                        if res:
                            tmdb_id = res.get("id")
                            det     = tmdb.movie_details(tmdb_id)
                            if det:
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
                            self.log("  TMDb : non trouvé.", "muted")

                    # Release name
                    stem    = fp.stem
                    release = stem if not re.search(r'[ ()\[]', stem) \
                              else build_release_name_movie(title, year, p)
                    self.log(f"  Release : {release}", "muted")

                    if release in hist:
                        self.log("  SKIP : release déjà uploadée.", "muted"); continue

                    if lc.count(title) > 0:
                        self.log("  SKIP : déjà sur La Cale.", "muted"); continue

                    # Torrent
                    self.log("  Hash SHA1...", "muted")
                    self.prog(0.0, f"Hash : {fn[:50]}")
                    try:
                        tb = make_torrent_single(fp, cfg["tracker_url"],
                                                 lambda pct: self.prog(pct, f"Hash {int(pct*100)}%"))
                    except Exception as e:
                        self.log(f"  ERREUR torrent : {e}", "err"); continue
                    self.prog(1.0, "")
                    self.log(f"  Torrent : {len(tb)//1024} Ko", "ok")
                    (out / f"{release}.torrent").write_bytes(tb)

                    sz  = fp.stat().st_size
                    nfo = "\n".join([f"Complete name : {fn}",
                                     f"File size     : {sz/1024**3:.2f} GiB",
                                     f"Type          : Film",
                                     f"Video         : {p['vc']} / {p['res'] or 'N/A'} / {p['hdr'] or 'SDR'}",
                                     f"Audio         : {p['ac']} {p['ach']} {p['atmos']}",
                                     f"Source        : {p['src']}",
                                     f"Language      : {p['lang']}",
                                     f"TMDb ID       : {tmdb_id or 'N/A'}",
                                     f"IMDB ID       : {imdb_id or 'N/A'}",
                                     f"Note TMDb     : {rating}/10",
                                     f"Genres        : {genres or 'N/A'}"])
                    desc = make_bbcode(title, year, overview, poster, p["res"],
                                       p["vc"], p["ac"], p["lang"], sz, rating,
                                       genres, cast, p["hdr"], is_series=False)

                    self.log("  Upload...", "muted")
                    terms    = lc.build_terms(p, is_series=False)
                    if conn_mode == "api":
                        ok, body = lc.upload_api(passkey, release, tb, nfo, desc,
                                                  tmdb_id=tmdb_id, is_series=False, terms=terms)
                    else:
                        ok, body = lc.upload(release, tb, nfo, desc,
                                             tmdb_id=tmdb_id, is_series=False, terms=terms)
                    if not ok:
                        msg = body.get("message") or body.get("error") or str(body)[:200]
                        self.log(f"  ERREUR : {msg}", "err")
                        if "limite" in msg.lower():
                            self.log("  Limite atteinte — arrêt.", "err"); break
                        continue

                    slug = body.get("slug") or body.get("data", {}).get("slug", "")
                    link = f"{cfg['lacale_url']}/torrents/{slug}" if slug else ""
                    self.log(f"  OK !{' — '+link if link else ''}", "ok")

                    if qb.ok:
                        films_path = cfg.get("tr_films_path", "/Films") if client_type == "transmission" else cfg.get("qb_films_path", "/Films")
                        added = qb.add(tb, films_path, release)
                        self.log(f"  qBittorrent : {'seedé ✓' if added else 'ajout échoué'}",
                                 "ok" if added else "muted")

                    self._notify_discord(cfg, title, year, release, link)
                    self._save_history(hist, release, fn)
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
                seasons = scan_seasons(sr)
                self.log(f"  {len(seasons)} saison(s) trouvée(s).", "muted")
                uploaded = 0

                for season_dir in seasons:
                    if self._stop.is_set() or uploaded >= max_series: break

                    sd = parse_season_dir(season_dir)
                    if not sd["files"]:
                        self.log(f"  SKIP : {season_dir.name} (aucun fichier vidéo)", "muted")
                        continue

                    p         = sd["tags"]
                    series_name = sd["series_name"]
                    season_tag  = sd["season_tag"]
                    season_num  = sd["season_num"]

                    self.log(f"\n  ▸ {series_name} — {season_tag} ({len(sd['files'])} épisode(s))", "gold")

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
                        self.log(f"  TMDb → \"{series_name}\"...", "muted")
                        res = tmdb.search_tv(series_name)
                        if res:
                            tmdb_id = res.get("id")
                            det     = tmdb.tv_details(tmdb_id, season_num)
                            if det:
                                title    = det.get("name") or series_name
                                year     = (det.get("first_air_date", ""))[:4]
                                overview = det.get("overview", "")
                                poster   = det.get("poster_path", "")
                                # Poster de la saison si disponible
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
                            self.log("  TMDb : non trouvé.", "muted")

                    # Release name : Titre.S01.MULTi.1080p.WEB-DL.x265-GRP
                    release = build_release_name_season(title, season_tag, p)
                    self.log(f"  Release : {release}", "muted")

                    if release in hist:
                        self.log("  SKIP : release déjà uploadée.", "muted"); continue

                    if lc.count(title, is_series=True) > 0:
                        self.log(f"  SKIP : déjà sur La Cale.", "muted"); continue

                    # Torrent multi-fichiers
                    self.log(f"  Hash SHA1 ({len(sd['files'])} fichiers, {sd['total_size']/1024**3:.2f} GiB)...", "muted")
                    self.prog(0.0, f"Hash saison : {release[:50]}")
                    try:
                        tb = make_torrent_multi(
                            release, sd["files"], cfg["tracker_url"],
                            lambda pct: self.prog(pct, f"Hash {int(pct*100)}%"))
                    except Exception as e:
                        self.log(f"  ERREUR torrent : {e}", "err"); continue
                    self.prog(1.0, "")
                    self.log(f"  Torrent : {len(tb)//1024} Ko", "ok")
                    (out / f"{release}.torrent").write_bytes(tb)

                    sz  = sd["total_size"]
                    nfo = "\n".join([
                        f"Series name   : {title}",
                        f"Season        : {season_tag}",
                        f"Episodes      : {len(sd['files'])}",
                        f"Total size    : {sz/1024**3:.2f} GiB",
                        f"Type          : Série",
                        f"Video         : {p.get('vc','?')} / {p.get('res','N/A')} / {p.get('hdr','SDR')}",
                        f"Audio         : {p.get('ac','?')} {p.get('ach','')} {p.get('atmos','')}",
                        f"Source        : {p.get('src','WEB')}",
                        f"Language      : {p.get('lang','FRENCH')}",
                        f"TMDb ID       : {tmdb_id or 'N/A'}",
                        f"Note TMDb     : {rating}/10",
                        f"Genres        : {genres or 'N/A'}",
                        f"",
                        f"Episodes :"] + [f"  {f.name}" for f in sd["files"]])

                    desc = make_bbcode(title, f"{year} — {season_tag}", overview, poster,
                                       p.get("res", ""), p.get("vc", "x264"),
                                       p.get("ac", "AAC"), p.get("lang", "FRENCH"),
                                       sz, rating, genres, cast, p.get("hdr", ""),
                                       is_series=True, season_num=season_num)

                    self.log("  Upload...", "muted")
                    terms    = lc.build_terms(p, is_series=True)
                    if conn_mode == "api":
                        ok, body = lc.upload_api(passkey, release, tb, nfo, desc,
                                                  tmdb_id=tmdb_id, is_series=True, terms=terms)
                    else:
                        ok, body = lc.upload(release, tb, nfo, desc,
                                             tmdb_id=tmdb_id, is_series=True, terms=terms)
                    if not ok:
                        msg = body.get("message") or body.get("error") or str(body)[:200]
                        self.log(f"  ERREUR : {msg}", "err")
                        if "limite" in msg.lower():
                            self.log("  Limite atteinte — arrêt.", "err"); break
                        continue

                    slug = body.get("slug") or body.get("data", {}).get("slug", "")
                    link = f"{cfg['lacale_url']}/torrents/{slug}" if slug else ""
                    self.log(f"  OK !{' — '+link if link else ''}", "ok")

                    if qb.ok:
                        series_path = cfg.get("tr_series_path", "/Series") if client_type == "transmission" else cfg.get("qb_series_path", "/Series")
                        added = qb.add(tb, series_path, release)
                        self.log(f"  qBittorrent : {'seedé ✓' if added else 'ajout échoué'}",
                                 "ok" if added else "muted")

                    self._notify_discord(cfg, f"{title} {season_tag}", year, release, link)
                    self._save_history(hist, release, hist_key)
                    uploaded += 1; total += 1
                    if uploaded < max_series and not self._stop.is_set():
                        time.sleep(int(cfg.get("upload_delay", 3)))
                    self._set_count(total, grand_total)

        self.log(f"\n{'═'*60}", "gold")
        self.log(f"  TERMINÉ — {total} upload(s) effectué(s)", "gold")
        self.log(f"{'═'*60}", "gold")

    def _save_history(self, hist_set, *keys):
        with open(HIST_FILE, "a", encoding="utf-8") as hf:
            for k in keys:
                hf.write(k + "\n")
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
        subtitle="Développé par Theolddispatch & The40n8  ·  version exécutable  ·  v{v}",
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
        sec_tmdb="THE MOVIE DATABASE (TMDb)",
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
        tip_qb_url="ex: http://192.168.1.40:8080",
        tip_qb_path="chemin Linux sur le NAS",
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
        subtitle="Developed by Theolddispatch & The40n8  ·  executable release  ·  v{v}",
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
        sec_tmdb="THE MOVIE DATABASE (TMDb)",
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
        tip_qb_url="ex: http://192.168.1.40:8080",
        tip_qb_path="Linux path on the NAS",
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
        subtitle="Desarrollado por Theolddispatch & The40n8  ·  versión ejecutable  ·  v{v}",
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
        sec_tmdb="THE MOVIE DATABASE (TMDb)",
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
        tip_qb_url="ej: http://192.168.1.40:8080",
        tip_qb_path="ruta Linux en el NAS",
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
    ),
}
# Langues supplémentaires (basées sur fr, avec sous-titre traduit)
_SUBTITLES = {
    "de": "Entwickelt von Theolddispatch & The40n8  ·  ausführbare Version  ·  v{v}",
    "it": "Sviluppato da Theolddispatch & The40n8  ·  versione eseguibile  ·  v{v}",
    "pt": "Desenvolvido por Theolddispatch & The40n8  ·  versão executável  ·  v{v}",
    "ja": "Theolddispatch & The40n8 制作  ·  実行可能バージョン  ·  v{v}",
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
        subtitle="Theolddispatch & The40n8 制作  ·  実行可能バージョン  ·  v{v}",
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
        sec_tmdb="THE MOVIE DATABASE (TMDb)",
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
        tip_qb_url="例: http://192.168.1.40:8080",
        tip_qb_path="NAS上のLinuxパス",
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
    def __init__(self, url: str, interval_min: int, on_back_callback):
        self.url          = url.rstrip("/")
        self.interval     = interval_min * 60   # en secondes
        self.on_back      = on_back_callback    # appelé quand le site revient
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
                message = "La Cale de nouveau en ligne !"
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
        self._save_logs_enabled = bool(self.cfg.get("save_logs", False))
        self._save_curl_enabled = bool(self.cfg.get("save_curl", False))
        self._check_updates_enabled = bool(self.cfg.get("check_updates", True))

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
                         ("gold", C["gold"]), ("muted", C["muted"])]:
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

        lbl_grade = tk.Label(outer, text="", font=FL, bg=C["bg"], fg=C["muted"],
                             anchor="w")
        lbl_grade.grid(row=1, column=3, sticky="w", padx=(8, 4))
        self._dyn_labels["grade_lbl"] = (lbl_grade, "grade")

        self.grade_film_var = tk.StringVar()
        self._grade_combo = self._make_combo_widget(outer, self.grade_film_var, get_grades(), width=22)
        self._grade_combo.grid(row=1, column=4, sticky="w", padx=(0, 4))
        self.grade_film_var.trace_add("write", self._on_grade_film)

        # ── Ligne Séries : chemin + […] + "Max uploads :" + champ valeur ──────
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

        lbl_max = tk.Label(outer, text="", font=FL, bg=C["bg"], fg=C["muted"],
                           anchor="w")
        lbl_max.grid(row=2, column=3, sticky="w", padx=(8, 4))
        self._dyn_labels["max_uploads_lbl"] = (lbl_max, "max_uploads")

        self.vars["max_movies"] = tk.StringVar()
        self.vars["max_series"] = self.vars["max_movies"]
        tk.Entry(outer, textvariable=self.vars["max_movies"],
                 font=FM, bg=C["ibg"], fg=C["ifg"],
                 insertbackground=C["gold"], relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=C["border"], width=5
                 ).grid(row=2, column=4, sticky="w", padx=(0, 4))

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

        # ── Langue interface (en premier) ─────────────────────────────────────
        lbl_ul = tk.Label(p, text="", font=FL, bg=C["bg"], fg=C["muted"],
                           anchor="w", width=24)
        lbl_ul.grid(row=r, column=0, sticky="w", padx=(8, 0), pady=(6, 4))
        self._s_labels["row_lbl_ui_lang"] = (lbl_ul, "lbl_ui_lang")
        self.vars["ui_lang"] = tk.StringVar()
        self._ui_lang_combo = self._make_combo_widget(
            p, self.vars["ui_lang"], list(LANGS_UI.keys()), width=10)
        self._ui_lang_combo.grid(row=r, column=1, sticky="w", padx=4, pady=(6, 4))
        self.vars["ui_lang"].trace_add("write", self._on_ui_lang_change)
        r += 1

        r = sec(r, "sec_lacale")
        r = row(r, "lbl_lacale_url", "lacale_url", w=38)

        # ── Frame API (passkey) ───────────────────────────────────────────
        self._frame_api = tk.Frame(p, bg=C["bg"])
        self._frame_api.grid(row=r, column=0, columnspan=4, sticky="ew")

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

        # ── Frame Web (email + pass) ──────────────────────────────────────
        self._frame_web = tk.Frame(p, bg=C["bg"])
        self._frame_web.grid(row=r, column=0, columnspan=4, sticky="ew")

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

        r = row(r, "lbl_tracker", "tracker_url", w=52)

        # Appliquer la visibilité initiale selon le mode courant
        p.after(10, self._update_conn_btn)

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

        # Combo grade — mettre à jour les valeurs dans la langue courante
        if hasattr(self, "_grade_combo"):
            grades = get_grades()
            self._grade_combo.config(values=grades)
            # Préserver la valeur sélectionnée (par index dans GRADE_MAX)
            try:
                max_val = int(self.vars["max_movies"].get() or 1)
                idx = GRADE_MAX.index(max_val)
                self.grade_film_var.set(grades[idx])
            except (ValueError, IndexError):
                self.grade_film_var.set(grades[0])

    # ══════════════════════════════════════════════════════════════════════════
    # FENÊTRE HISTORIQUE
    # ══════════════════════════════════════════════════════════════════════════
    def _show_history(self):
        win = tk.Toplevel(self.root)
        win.title(t("hist_title"))
        win.configure(bg=C["bg"])
        win.geometry("720x500")
        win.resizable(True, True)
        win.transient(self.root)

        # Header
        hf = tk.Frame(win, bg=C["bg"])
        hf.pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(hf, text=t("hist_title"), font=FB,
                 bg=C["bg"], fg=C["gold"]).pack(side="left")
        tk.Frame(win, bg=C["gold_dim"], height=1).pack(
            fill="x", padx=14, pady=(4, 0))

        # Zone texte scrollable avec SlimScrollbar
        hist_frame = tk.Frame(win, bg=C["bg"])
        hist_frame.pack(fill="both", expand=True, padx=14, pady=8)
        hist_frame.columnconfigure(0, weight=1)
        hist_frame.rowconfigure(0, weight=1)

        txt = tk.Text(
            hist_frame, bg=C["ibg"], fg=C["text"], font=FM8,
            relief="flat", bd=0,
            highlightthickness=1, highlightbackground=C["border"],
            wrap="none", state="normal")
        txt.grid(row=0, column=0, sticky="nsew")
        _hist_vsb = SlimScrollbar(hist_frame, command=txt.yview)
        _hist_vsb.grid(row=0, column=1, sticky="ns")
        txt.configure(yscrollcommand=_hist_vsb.set)

        if HIST_FILE.exists():
            lines = HIST_FILE.read_text("utf-8", errors="ignore").splitlines()
            # Filtrer : une ligne sur deux est le nom de fichier, l'autre le release name
            # On affiche tout, avec un séparateur visuel tous les 2
            entries = []
            i = 0
            while i < len(lines):
                l = lines[i].strip()
                if l:
                    entries.append(l)
                i += 1
            if entries:
                for idx, entry in enumerate(entries, 1):
                    txt.insert("end", f"  {idx:>4}.  {entry}\n")
            else:
                txt.insert("end", f"\n  {t('hist_empty')}\n")
        else:
            txt.insert("end", f"\n  {t('hist_empty')}\n")

        txt.config(state="disabled")

        # Boutons
        bf = tk.Frame(win, bg=C["bg"])
        bf.pack(fill="x", padx=14, pady=(0, 10))

        def clear_hist():
            if messagebox.askyesno(t("hist_btn_clear"),
                                   t("hist_confirm_clear"),
                                   parent=win):
                HIST_FILE.write_text("", "utf-8")
                txt.config(state="normal")
                txt.delete("1.0", "end")
                txt.insert("end", f"\n  {t('hist_empty')}\n")
                txt.config(state="disabled")

        tk.Button(bf, text=t("hist_btn_clear"), command=clear_hist,
                  font=FM8, bg=C["panel"], fg=C["muted"],
                  relief="flat", bd=0, padx=8, pady=4, cursor="hand2",
                  highlightthickness=1, highlightbackground=C["border"]
                  ).pack(side="left")
        tk.Button(bf, text=t("hist_btn_close"), command=win.destroy,
                  font=FB, bg=C["panel"], fg=C["gold"],
                  relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                  highlightthickness=1, highlightbackground=C["gold"]
                  ).pack(side="right")

        win.focus_set()

    # ══════════════════════════════════════════════════════════════════════════
    # Grades
    # ══════════════════════════════════════════════════════════════════════════
    def _on_grade_film(self, *_):
        try:
            idx = get_grades().index(self.grade_film_var.get())
            self.vars["max_movies"].set(str(GRADE_MAX[idx]))
        except (ValueError, IndexError): pass

    def _on_grade_series(self, *_):
        pass  # plus utilisé — max_series = max_movies

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
        try:
            idx = GRADE_MAX.index(int(self.cfg.get("max_movies", 1)))
            self.grade_film_var.set(get_grades()[idx])
        except (ValueError, IndexError):
            self.grade_film_var.set(get_grades()[0])
        # Mode de connexion
        self._conn_mode = self.cfg.get("conn_mode", "web")
        self._update_conn_btn()
        # Client torrent
        self._torrent_client = self.cfg.get("torrent_client", "qbittorrent")
        self.root.after(20, self._update_client_ui)
        # Notification watcher
        self._notify_enabled = bool(self.cfg.get("notify_enabled", False))
        self.root.after(30, self._refresh_notify_ui)
        self._save_logs_enabled = bool(self.cfg.get("save_logs", False))
        self._save_curl_enabled = bool(self.cfg.get("save_curl", False))
        self.root.after(35, self._refresh_logs_curl_ui)
        self.root.after(40, self._refresh_check_updates_ui)
        # Langue UI
        self.vars["ui_lang"].set(self.cfg.get("ui_lang", "fr"))
        self._loading = False

        # Brancher l'autosave sur chaque variable APRÈS le chargement
        self._autosave_job = None
        for v in self.vars.values():
            v.trace_add("write", self._on_field_change)

        # Vérification MAJ au démarrage (en arrière-plan)
        self._check_updates_enabled = bool(self.cfg.get("check_updates", True))
        self.root.after(2000, self._run_update_check)   # 2s après démarrage

    # ══════════════════════════════════════════════════════════════════════════
    # WATCHER — Notification retour site
    # ══════════════════════════════════════════════════════════════════════════
    def _set_torrent_client(self, client):
        """Bascule entre qbittorrent et transmission."""
        self._torrent_client = client
        cfg = self._collect()
        cfg["torrent_client"] = client
        save_cfg(cfg); self.cfg = cfg
        self._update_client_ui()

    def _update_client_ui(self):
        """Met à jour les boutons et affiche les champs du client actif."""
        if not hasattr(self, "_btn_client_qb"):
            return
        is_qb = self._torrent_client == "qbittorrent"
        # Boutons : actif = or, inactif = gris
        self._btn_client_qb.config(
            fg=C["gold"] if is_qb else C["muted"],
            highlightthickness=1,
            highlightbackground=C["gold"] if is_qb else C["muted"])
        self._btn_client_tr.config(
            fg=C["muted"] if is_qb else C["gold"],
            highlightthickness=1,
            highlightbackground=C["muted"] if is_qb else C["gold"])
        # Afficher/masquer les champs
        for w in self._qb_rows:
            w.grid() if is_qb else w.grid_remove()
        for w in self._tr_rows:
            w.grid_remove() if is_qb else w.grid()

    def _toggle_check_updates(self):
        self._check_updates_enabled = not self._check_updates_enabled
        cfg = self._collect(); cfg["check_updates"] = self._check_updates_enabled
        save_cfg(cfg); self.cfg = cfg
        self._refresh_check_updates_ui()

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

    def _run_update_check(self):
        """Vérifie la MAJ en arrière-plan au démarrage."""
        if not self._check_updates_enabled:
            return
        def _check():
            available = _check_update_available()
            if available:
                self.root.after(0, self._show_update_badge)
        threading.Thread(target=_check, daemon=True).start()

    def _show_update_badge(self):
        """Affiche l'étiquette verte 'Mise à jour disponible' dans le header."""
        if hasattr(self, "_lbl_update"):
            self._lbl_update.config(text=f"  ↑ {t('lbl_update_available')}")
            self._lbl_update.pack(side="left", padx=(10, 0))

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
        self.root.after(0, lambda: self._health_var.set("Santé La Cale : ⚪"))
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
        url = self.cfg.get("lacale_url", "https://la-cale.space").rstrip("/")
        ok  = False
        p1_failed = False   # True si la passe 1 dit explicitement "down"

        # ── Passe 1 : checker externe ─────────────────────────────────────
        try:
            r1 = requests.get(
                "https://www.isitdownrightnow.com/check.php",
                params={"domain": "la-cale.space"},
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
        if ok:
            self._health_var.set("Santé La Cale : 🟢")
            self._health_lbl.config(fg=C["green"])
        else:
            self._health_var.set("Santé La Cale : 🔴")
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

        url      = self.cfg.get("lacale_url", "https://la-cale.space")
        interval = int(self.cfg.get("notify_interval", "10") or "10")

        self._watcher = SiteWatcher(url, interval, self._on_site_back)
        self._watcher.start()
        self._log(
            f"  Surveillance de la santé du site par un watcher extérieur activée — vérification toutes les {interval} min.", "muted")

    def _on_site_back(self):
        """Callback appelé par le watcher quand le site revient."""
        now = time.strftime("%Hh%M")
        self.root.after(0, self._log,
                        f"✓ Site de retour ({now}) — vous pouvez relancer l'upload.", "ok")
        self.root.after(0, self.status.set, f"  Site revenu à {now} ✓")
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
                highlightbackground=C["green"])
        else:
            self.b_conn.config(
                text=f"  {t('conn_web')}  ",
                fg=C["gold"], highlightthickness=1,
                highlightbackground=C["gold"])
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
        # Sauvegarder immédiatement
        cfg = self._collect()
        cfg["conn_mode"] = self._conn_mode
        save_cfg(cfg); self.cfg = cfg
        mode_name = t("conn_api") if self._conn_mode == "api" else t("conn_web")
        self._log(f"Mode de connexion : {mode_name}", "ok")

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
        cfg["autosave_enabled"]= getattr(self, "_autosave_enabled", True)
        cfg["notify_enabled"]  = getattr(self, "_notify_enabled", False)
        cfg["save_logs"]       = getattr(self, "_save_logs_enabled", True)
        cfg["save_curl"]       = getattr(self, "_save_curl_enabled", True)
        cfg["check_updates"]   = getattr(self, "_check_updates_enabled", True)
        # Champ dev (invisible) — jamais sauvegardé dans la config
        if hasattr(self, "_suffix_var"):
            cfg["_dev_field"] = self._suffix_var.get()
        return cfg

    def _browse(self, key):
        d = filedialog.askdirectory(title="…")
        if d: self.vars[key].set(d)

    # ── Log ───────────────────────────────────────────────────────────────────
    def _log(self, msg, tag=None):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n", tag or "")
        self.log_box.see("end")
        self.log_box.config(state="disabled")
        # Écriture sur disque uniquement si activée
        if getattr(self, "_save_logs_enabled", False):
            try:
                LOG_DIR.mkdir(parents=True, exist_ok=True)
                log_file = LOG_DIR / f"blackflag_{time.strftime('%Y-%m-%d')}.log"
                with open(log_file, "a", encoding="utf-8") as lf:
                    lf.write(msg + "\n")
            except Exception:
                pass

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
        self.prog_bar["value"] = pct * 100
        if pct > 0:
            # Garder le compteur s'il est déjà affiché
            current = self.prog_lbl.cget("text")
            count_part = current.split("·")[0].strip() if "·" in current else ""
            pct_str = f"{int(pct*100)}%"
            self.prog_lbl.config(text=f"{count_part} · {pct_str}" if count_part else pct_str)
            self._lbl_prog_above.grid()
        else:
            self.prog_lbl.config(text="")
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
        if not cfg.get("lacale_user"):  errs.append(t("err_no_user"))
        if not cfg.get("lacale_pass"):  errs.append(t("err_no_pass"))
        if not cfg.get("tracker_url"):  errs.append(t("err_no_tracker"))
        if not cfg.get("qb_url"):       errs.append(t("err_no_qb"))
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
        self.running = True
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
                                 0, self._set_prog_count, c, t))
        threading.Thread(target=self.worker.run, daemon=True).start()

    def _on_done(self):
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
    App(root)
    root.mainloop()
