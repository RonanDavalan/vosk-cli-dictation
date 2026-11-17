# src/model_download.py
#
# Auto-téléchargement d'un modèle acoustique (petit ou complet), jamais depuis le postinst
# Debian (un téléchargement binaire silencieux est proscrit par la politique
# du paquet). Deux couches d'appel : la sous-commande explicite
# --download-model, et un prompt interactif (isatty uniquement) au premier
# lancement sans modèle — voir src/main.py.

import hashlib
import os
import shutil
import tempfile
import urllib.request
import zipfile

from src.i18n import get_translation

BASE_URL = "https://alphacephei.com/vosk/models/"

# Le catalogue : huit archives, clé (langue, taille), taille « small » ou
# « big » (Apache 2.0, licence vérifiée sur alphacephei.com/vosk/models —
# redistribution et téléchargement licites). alphacephei.com ne publie aucune
# somme officielle : SHA256 et taille en octets sont calculés sur l'archive
# elle-même, à la date inscrite dans « checked ».
CATALOG = {
    ("en", "small"): {
        "filename": "vosk-model-small-en-us-0.15.zip",
        "folder": "vosk-model-small-en-us-0.15",
        "sha256": "30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498",
        "size": 41205931,
    },
    ("fr", "small"): {
        "filename": "vosk-model-small-fr-0.22.zip",
        "folder": "vosk-model-small-fr-0.22",
        "sha256": "cabf6180e177eb9b3a9a9d43a437bd5e549f3a7d09525e5d69a3fed787be12ad",
        "size": 42233323,
    },
    ("de", "small"): {
        "filename": "vosk-model-small-de-0.15.zip",
        "folder": "vosk-model-small-de-0.15",
        "sha256": "b7e53c90b1f0a38456f4cd62b366ecd58803cd97cd42b06438e2c131713d5e43",
        "size": 46499967,
    },
    ("es", "small"): {
        "filename": "vosk-model-small-es-0.42.zip",
        "folder": "vosk-model-small-es-0.42",
        "sha256": "09b239888f633ef2f0b4e09736e3d9936acfd810bc65d53fad45261762c6511f",
        "size": 39817833,
    },
    ("en", "big"): {
        "filename": "vosk-model-en-us-0.22.zip",
        "folder": "vosk-model-en-us-0.22",
        "sha256": "47f9a81ebb039dbb0bd319175c36ac393c0893b796c2b6303e64cf58c27b69f6",
        "size": 1913365522,
        "checked": "2026-11-12",
    },
    ("fr", "big"): {
        "filename": "vosk-model-fr-0.22.zip",
        "folder": "vosk-model-fr-0.22",
        "sha256": "b26c34e5ea1b9f9dee6cef5e910a1d93e9adb60f1a0a3f85c069976aec481e46",
        "size": 1523026348,
        "checked": "2026-11-12",
    },
    ("de", "big"): {
        "filename": "vosk-model-de-0.21.zip",
        "folder": "vosk-model-de-0.21",
        "sha256": "245060756f8d8394fc5b13639cf220b7620205795f30f37b6823878d4f603b2a",
        "size": 2031717803,
        "checked": "2026-11-12",
    },
    ("es", "big"): {
        "filename": "vosk-model-es-0.42.zip",
        "folder": "vosk-model-es-0.42",
        "sha256": "bbbfaf9239bed5dcb0d140886b5834fcc13c13c7fb2f2799ae790f03ff20bfce",
        "size": 1484681703,
        "checked": "2026-11-12",
    },
}

SIZES = ("small", "big")

# Vue des quatre petits modèles par langue, clé historique du catalogue.
MODELS = {lang: info for (lang, size), info in CATALOG.items() if size == "small"}


def known_folders() -> dict:
    """Dossier de chaque modèle du catalogue -> (langue, taille)."""
    return {info["folder"]: key for key, info in CATALOG.items()}


def models_root() -> str:
    """$XDG_DATA_HOME/vosk-models/ : premier répertoire de la cascade de
    recherche (config.model_search_roots) — seul emplacement où un modèle
    téléchargé sans droits root est effectivement retrouvé au chargement."""
    xdg_data_home = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return os.path.join(xdg_data_home, "vosk-models")


def download_model(lang: str, size: str = "small") -> bool:
    """Télécharge, vérifie et installe le modèle Vosk de `lang`, petit ou complet
    (`size` : « small » ou « big »).

    Annonce taille et source avant tout octet transféré (jamais de fetch
    silencieux). Vérifie le SHA256 contre la valeur figée dans MODELS.
    Déplacement atomique dans le répertoire final. Pas de retry automatique :
    un échec réseau ou de vérification retourne False, à relancer à la main.
    """
    _ = get_translation()
    info = CATALOG.get((lang, size))
    if not info:
        print(_("No download available for language: {lang}").format(lang=lang))
        print(_("Available languages: {langs}").format(langs=", ".join(sorted(MODELS))))
        return False

    root = models_root()
    dest = os.path.join(root, info["folder"])
    if os.path.isdir(dest):
        print(_("Model already installed: {path}").format(path=dest))
        return True

    url = BASE_URL + info["filename"]
    size_mb = info["size"] / (1024 * 1024)
    print(_("Downloading {url} ({size:.0f} MB)...").format(url=url, size=size_mb))

    os.makedirs(root, exist_ok=True)
    # L'archive et son contenu décompressé coexistent un moment.
    needed = info["size"] * 3
    free = shutil.disk_usage(root).free
    if free < needed:
        print(
            _(
                "Not enough disk space in {path}: {free:.0f} MB free, {needed:.0f} MB needed."
            ).format(
                path=root, free=free / (1024 * 1024), needed=needed / (1024 * 1024)
            )
        )
        return False
    fd, tmp_zip = tempfile.mkstemp(dir=root, suffix=".zip.part")
    os.close(fd)
    try:
        try:
            urllib.request.urlretrieve(url, tmp_zip)
        except OSError as e:
            print(_("Download failed: {error}").format(error=e))
            return False

        digest = hashlib.sha256()
        with open(tmp_zip, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != info["sha256"]:
            print(_("Checksum mismatch; the download was discarded."))
            return False

        with tempfile.TemporaryDirectory(dir=root) as extract_dir:
            with zipfile.ZipFile(tmp_zip) as z:
                z.extractall(extract_dir)
            extracted = os.path.join(extract_dir, info["folder"])
            if not os.path.isdir(extracted):
                print(_("Unexpected archive layout; aborting."))
                return False
            os.rename(extracted, dest)

        print(_("Model installed: {path}").format(path=dest))
        return True
    finally:
        if os.path.exists(tmp_zip):
            os.remove(tmp_zip)
