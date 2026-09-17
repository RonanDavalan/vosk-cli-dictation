# src/model_download.py
#
# Auto-téléchargement du petit modèle acoustique, jamais depuis le postinst
# Debian (un téléchargement binaire silencieux est proscrit par la politique
# du paquet). Deux couches d'appel : la sous-commande explicite
# --download-model, et un prompt interactif (isatty uniquement) au premier
# lancement sans modèle — voir src/main.py.

import hashlib
import os
import tempfile
import urllib.request
import zipfile

from src.i18n import get_translation

BASE_URL = "https://alphacephei.com/vosk/models/"

# Les quatre modèles small utilisés par le projet (Apache 2.0, licence
# vérifiée sur alphacephei.com/vosk/models — redistribution et
# téléchargement automatisé licites). SHA256 et taille calculés depuis un
# téléchargement de référence : alphacephei.com ne publie pas
# de somme officielle, la valeur fait donc foi depuis ce fichier, jamais
# récupérée en ligne.
MODELS = {
    "en": {
        "filename": "vosk-model-small-en-us-0.15.zip",
        "folder": "vosk-model-small-en-us-0.15",
        "sha256": "30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498",
        "size": 41205931,
    },
    "fr": {
        "filename": "vosk-model-small-fr-0.22.zip",
        "folder": "vosk-model-small-fr-0.22",
        "sha256": "cabf6180e177eb9b3a9a9d43a437bd5e549f3a7d09525e5d69a3fed787be12ad",
        "size": 42233323,
    },
    "de": {
        "filename": "vosk-model-small-de-0.15.zip",
        "folder": "vosk-model-small-de-0.15",
        "sha256": "b7e53c90b1f0a38456f4cd62b366ecd58803cd97cd42b06438e2c131713d5e43",
        "size": 46499967,
    },
    "es": {
        "filename": "vosk-model-small-es-0.42.zip",
        "folder": "vosk-model-small-es-0.42",
        "sha256": "09b239888f633ef2f0b4e09736e3d9936acfd810bc65d53fad45261762c6511f",
        "size": 39817833,
    },
}


def models_root() -> str:
    """$XDG_DATA_HOME/vosk-models/ : premier répertoire de la cascade de
    recherche (config.model_search_roots) — seul emplacement où un modèle
    téléchargé sans droits root est effectivement retrouvé au chargement."""
    xdg_data_home = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return os.path.join(xdg_data_home, "vosk-models")


def download_model(lang: str) -> bool:
    """Télécharge, vérifie et installe le petit modèle Vosk de `lang`.

    Annonce taille et source avant tout octet transféré (jamais de fetch
    silencieux). Vérifie le SHA256 contre la valeur figée dans MODELS.
    Déplacement atomique dans le répertoire final. Pas de retry automatique :
    un échec réseau ou de vérification retourne False, à relancer à la main.
    """
    _ = get_translation()
    info = MODELS.get(lang)
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
