"""Notification de bureau par `notify-send`, indépendante de la zone de notification.

Sans zone de notification (GNOME sans extension), `QSystemTrayIcon` ne peut pas
afficher de message ; `notify-send` parle directement au service de
notifications. Un échec est ignoré : il n'interrompt jamais le programme.
"""

import shutil
import subprocess

_TIMEOUT_S = 2.0


def notify(title: str, message: str) -> None:
    if shutil.which("notify-send") is None:
        return
    try:
        subprocess.run(["notify-send", title, message], capture_output=True, check=False,
                       stdin=subprocess.DEVNULL, timeout=_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        pass
