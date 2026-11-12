"""Lancement de l'icône à l'ouverture de session (XDG Autostart).

L'état vit dans le mécanisme que le bureau affiche et modifie déjà : le paquet
installe l'entrée système `/etc/xdg/autostart/vosk-cli-dictation-tray.desktop` ;
une entrée utilisateur de même nom, `Hidden=true`, la masque. Depuis un clone,
sans entrée système, l'entrée utilisateur complète lance l'interpréteur en cours
(celui du venv, chemin non résolu : le résoudre sortirait du venv).
"""

import os
import sys
from pathlib import Path

ENTRY_NAME = "vosk-cli-dictation-tray.desktop"
SYSTEM_ENTRY = Path("/etc/xdg/autostart") / ENTRY_NAME

_CHARS_TO_QUOTE = set(' \t\n"\'\\><~|&;$*?#()`')


def user_entry() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "autostart" / ENTRY_NAME


def _exec_argument(argument: str) -> str:
    # Desktop Entry : un argument qui contient un caractère réservé est cité ;
    # dans la citation, " ` $ \ sont précédés d'un \, puis la règle des chaînes
    # double chaque \. « % » s'écrit « %% ».
    argument = argument.replace("%", "%%")
    if not _CHARS_TO_QUOTE.intersection(argument):
        return argument
    quoted = "".join("\\" + c if c in '"`$\\' else c for c in argument)
    return '"' + quoted.replace("\\", "\\\\") + '"'


def _read_entry(path: Path) -> dict:
    values = {}
    section = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("["):
            section = line
        elif section == "[Desktop Entry]" and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _hidden(values: dict) -> bool:
    return (values.get("Hidden", "").lower() == "true"
            or values.get("X-GNOME-Autostart-enabled", "").lower() == "false")


def _write(path: Path, lines: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(["[Desktop Entry]", *lines]) + "\n", encoding="utf-8")


def is_enabled() -> bool:
    entry = user_entry()
    if entry.is_file():
        return not _hidden(_read_entry(entry))
    return SYSTEM_ENTRY.is_file()


def enable(icon: str | None = None) -> None:
    entry = user_entry()
    if SYSTEM_ENTRY.is_file():
        entry.unlink(missing_ok=True)
        return
    command = [sys.executable, "-m", "vosk_cli_dictation_tray"]
    lines = [
        "Type=Application",
        "Name=vosk-cli-dictation-tray",
        "Comment=Microphone icon for vosk-cli-dictation",
        "Exec=" + " ".join(_exec_argument(a) for a in command),
        "Terminal=false",
        "X-GNOME-Autostart-enabled=true",
    ]
    if icon:
        lines.insert(3, "Icon=" + icon)
    _write(entry, lines)


def disable() -> None:
    _write(user_entry(), ["Type=Application", "Name=vosk-cli-dictation-tray",
                          "Exec=vosk-cli-dictation-tray", "Hidden=true"])
