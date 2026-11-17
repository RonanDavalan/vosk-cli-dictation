# --version : affiche « vosk-cli-dictation <version> » et sort avant tout
# chargement de modèle ; le texte d'aide de l'option existe dans les quatre
# langues.

import re
import subprocess
import sys
from pathlib import Path

import pytest

from src.version import __version__

RACINE = Path(__file__).resolve().parent.parent


def _lancer(*args):
    return subprocess.run(
        [sys.executable, str(RACINE / "src" / "main.py"), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_version_sort_avec_le_nom_et_le_numero():
    r = _lancer("--version")
    assert r.returncode == 0
    assert r.stdout.strip() == f"vosk-cli-dictation {__version__}"


def test_numero_de_version_bien_forme():
    assert re.fullmatch(r"\d+\.\d+\.\d+(-(alpha|beta))?", __version__)


@pytest.mark.parametrize("lang", ["en", "fr", "de", "es"])
def test_aide_de_l_option_dans_chaque_langue(lang):
    r = _lancer("--lang", lang, "--help")
    assert r.returncode == 0
    ligne = next(l for l in r.stdout.splitlines() if "--version" in l)
    assert ligne.strip() != "--version"
