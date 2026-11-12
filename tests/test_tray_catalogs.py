# Les libellés du programme de l'icône (tray/) sont dans les quatre catalogues
# compilés, et sa table de tailles suit le catalogue de modèles.

import ast
import gettext
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TRAY_PACKAGE = ROOT / "tray" / "vosk_cli_dictation_tray"
TRANSLATOR_NAMES = {"t", "_t", "translator"}


def tray_msgids():
    ids = set()
    for source in TRAY_PACKAGE.glob("*.py"):
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            first = node.args[0]
            if name in TRANSLATOR_NAMES and isinstance(first, ast.Constant) and isinstance(first.value, str):
                ids.add(first.value)
    return ids


def test_the_tray_has_translatable_strings():
    assert len(tray_msgids()) >= 40


@pytest.mark.parametrize("lang", ["en", "fr", "de", "es"])
def test_every_tray_string_is_translated_in_the_compiled_catalog(lang):
    catalog = gettext.translation("messages", localedir=str(ROOT / "locales"), languages=[lang])
    missing = [m for m in sorted(tray_msgids()) if not catalog.gettext(m) or
               (lang != "en" and catalog.gettext(m) == m and m not in ("Correction",))]
    assert missing == []


def test_tray_size_table_matches_the_model_catalog():
    sys.path.insert(0, str(ROOT / "tray"))
    try:
        from vosk_cli_dictation_tray.sizes import ARCHIVE_BYTES
    finally:
        sys.path.remove(str(ROOT / "tray"))
    from src.model_download import CATALOG
    assert ARCHIVE_BYTES == {key: info["size"] for key, info in CATALOG.items()}
