# Chantier « lisibilité de la sortie de démarrage » — la colonne de droite du
# tableau de ponctuation de print_help_message() est alignée sur une seule
# abscisse dans les quatre langues. Régression : le calcul de largeur se faisait
# avec len() (points de code), alors qu'un terminal rend « „ » « — » « … » sur
# deux cellules, ce qui décalait la seconde colonne en escalier en de/fr.

import re

import pytest

from config.config import config
from src.i18n import set_ui_language
from src.main import _display_width, print_help_message

ANSI = re.compile(r"\x1b\[[0-9;]*m")
GAP = re.compile(r" {2,}")
ENTRY = re.compile(r".+\(.*\)\s*$")


@pytest.mark.parametrize("lang", ["en", "fr", "de", "es"])
def test_punctuation_right_column_is_aligned(lang, capsys):
    config.set_language(lang)
    set_ui_language(lang)

    print_help_message()
    lines = capsys.readouterr().out.splitlines()

    right_column_starts = []
    for line in lines:
        plain = ANSI.sub("", line).rstrip()
        if not plain.startswith("  "):
            continue
        parts = GAP.split(plain.strip(), maxsplit=1)
        if len(parts) != 2 or not (ENTRY.match(parts[0]) and ENTRY.match(parts[1])):
            continue
        before_right = plain[: plain.rindex(parts[1])]
        right_column_starts.append(_display_width(before_right))

    assert len(right_column_starts) >= 3, f"{lang}: tableau de ponctuation introuvable"
    assert len(set(right_column_starts)) == 1, (
        f"{lang}: colonne de droite non alignée, abscisses {sorted(set(right_column_starts))}"
    )


def test_display_width_counts_wide_glyphs_as_two():
    assert _display_width("abc") == 3
    assert _display_width("a„c") == 4
    assert _display_width("—…«»") == 8
