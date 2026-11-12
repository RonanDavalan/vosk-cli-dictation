"""État de la dictée -> fichiers d'icône de `assets/icons/tray/`."""

import os
from pathlib import Path

from PySide6.QtGui import QIcon

SIZES = (16, 22, 24, 32, 48, 64, 256)

# État annoncé par `info` -> nom de l'icône. Aucune dictée : « off ».
STATE_ICON = {"DICTÉE": "dictating", "ÉCOUTE": "listening", "VEILLE": "sleeping"}
OFF = "off"


def icon_name(state) -> str:
    return STATE_ICON.get(state, OFF)


def icon_dirs() -> list[Path]:
    dirs = []
    if os.environ.get("VOSK_TRAY_ICONS"):
        dirs.append(Path(os.environ["VOSK_TRAY_ICONS"]))
    dirs.append(Path(__file__).resolve().parents[2] / "assets" / "icons" / "tray")
    dirs.append(Path("/usr/share/vosk-cli-dictation/icons/tray"))
    return dirs


def icon_dir() -> Path | None:
    for directory in icon_dirs():
        if (directory / "mic-{}.svg".format(OFF)).is_file():
            return directory
    return None


def icon_files(name: str) -> list[Path]:
    directory = icon_dir()
    if directory is None:
        return []
    files = [directory / "mic-{}.svg".format(name)]
    files += [directory / "mic-{}-{}.png".format(name, size) for size in SIZES]
    return [f for f in files if f.is_file()]


def load_icon(name: str) -> QIcon:
    icon = QIcon()
    for path in icon_files(name):
        icon.addFile(str(path))
    return icon
