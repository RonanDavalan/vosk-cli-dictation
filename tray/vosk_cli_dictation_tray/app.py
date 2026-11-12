"""Point d'entrée de `vosk-cli-dictation-tray`."""

import argparse
import hashlib
import sys

from vosk_cli_dictation_tray import __version__
from vosk_cli_dictation_tray.i18n import Translator, system_language


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="vosk-cli-dictation-tray")
    parser.add_argument("--version", action="version",
                        version="vosk-cli-dictation-tray " + __version__)
    parser.add_argument("--socket", metavar="PATH",
                        help="control socket of the dictation to drive (default: the user's own)")
    parser.add_argument("--dictation-command", metavar="COMMAND",
                        help="command that launches the dictation (default: vosk-cli-dictation)")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication, QSystemTrayIcon

    from vosk_cli_dictation_tray import launcher, notifier
    from vosk_cli_dictation_tray.client import ControlClient, default_socket_path
    from vosk_cli_dictation_tray.tray import APP_TITLE, DictationTray

    translator = Translator()
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_TITLE)

    socket_path = args.socket or default_socket_path()
    lock_dir = launcher.state_dir()
    lock_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(socket_path.encode()).hexdigest()[:12]
    lock = QLockFile(str(lock_dir / "tray-{}.lock".format(key)))
    if not lock.tryLock(100):
        print(translator("The icon is already running."), file=sys.stderr)
        return 1

    if not QSystemTrayIcon.isSystemTrayAvailable():
        notifier.notify(APP_TITLE, translator(
            "No notification area found. On GNOME, enable the "
            "'AppIndicator and KStatusNotifierItem Support' extension; "
            "desktop shortcuts on the control socket keep working."))

    client = ControlClient(socket_path)
    tray = DictationTray(client, translator, system_language(),
                         dictation_command=args.dictation_command)
    tray.show()
    client.start()
    code = app.exec()
    client.stop()
    lock.unlock()
    return code
