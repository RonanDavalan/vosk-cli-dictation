"""Libellés : les catalogues gettext du projet (`locales/<langue>/LC_MESSAGES/messages.mo`)."""

import gettext
import os
from pathlib import Path

LANGS = ("en", "fr", "de", "es")


def locale_dirs() -> list[Path]:
    dirs = []
    if os.environ.get("VOSK_LOCALE_DIR"):
        dirs.append(Path(os.environ["VOSK_LOCALE_DIR"]))
    dirs.append(Path(__file__).resolve().parents[2] / "locales")
    dirs.append(Path("/usr/lib/vosk-cli-dictation/locales"))
    dirs.append(Path("/usr/share/vosk-cli-dictation/locales"))
    return dirs


def system_language() -> str:
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = (os.environ.get(name) or "").strip()
        if value:
            code = value.split(".")[0].split("@")[0].split("_")[0].lower()
            return code if code in LANGS else "en"
    return "en"


class Translator:
    def __init__(self, lang: str | None = None):
        self.lang = "en"
        self._gettext = lambda text: text
        self.set_language(lang or system_language())

    def set_language(self, lang: str) -> None:
        self.lang = lang if lang in LANGS else "en"
        for directory in locale_dirs():
            if (directory / self.lang / "LC_MESSAGES" / "messages.mo").is_file():
                self._gettext = gettext.translation(
                    "messages", localedir=str(directory), languages=[self.lang]).gettext
                return
        self._gettext = lambda text: text

    def __call__(self, text: str) -> str:
        return self._gettext(text)
