# Chantier stabilité v0.5.1 — Vosk/Kaldi sérialise les flottants de
# SetWords(True) avec le séparateur décimal de LC_NUMERIC. Sous fr_FR.UTF-8
# (cas `ada`), Result() rend « "conf" : 1,000000 » et json.loads casse à chaque
# final avec mots. Le correctif force LC_NUMERIC du processus à « C » au
# démarrage (src/main.py) et défensivement dans build_recognizer().
#
# Ces tests exigent qu'une locale à virgule décimale soit installée sur la
# machine ; ils se sautent proprement sinon (CI, conteneur minimal).

import json
import locale

import pytest

import src.recognition as rec

_COMMA_LOCALES = ("fr_FR.UTF-8", "fr_FR.utf8", "de_DE.UTF-8", "de_DE.utf8")


def _set_a_comma_locale():
    """Positionne LC_NUMERIC sur une locale à virgule décimale disponible.
    Retourne son nom, ou None si aucune n'est installée."""
    for name in _COMMA_LOCALES:
        try:
            locale.setlocale(locale.LC_NUMERIC, name)
        except locale.Error:
            continue
        if locale.localeconv()["decimal_point"] == ",":
            return name
    return None


@pytest.fixture(autouse=True)
def _restore_numeric_locale():
    saved = locale.setlocale(locale.LC_NUMERIC)
    try:
        yield
    finally:
        try:
            locale.setlocale(locale.LC_NUMERIC, saved)
        except locale.Error:
            locale.setlocale(locale.LC_NUMERIC, "C")


def test_the_captured_ada_string_is_really_invalid_json():
    # La chaîne exacte capturée sur `ada` le 09/09 (virgule décimale) n'est pas
    # du JSON — c'est ce que le correctif de locale empêche Vosk de produire.
    raw = (
        '{\n  "result" : [{\n      "conf" : 1,000000,\n'
        '      "end" : 11,370000,\n      "start" : 10,710000,\n'
        '      "word" : "bonjour"\n    }],\n  "text" : "bonjour"\n}'
    )
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw)


def test_force_c_numeric_locale_resets_a_comma_locale():
    name = _set_a_comma_locale()
    if name is None:
        pytest.skip("aucune locale à virgule décimale installée sur ce système")
    assert locale.localeconv()["decimal_point"] == ","

    rec.force_c_numeric_locale()

    assert locale.localeconv()["decimal_point"] == "."
    # Un flottant formaté par la libc (ce que fait Kaldi) reprend le point.
    assert "%.6f" % 1.0 == "1.000000"


def test_force_c_numeric_locale_is_idempotent_and_safe_when_already_c():
    locale.setlocale(locale.LC_NUMERIC, "C")
    rec.force_c_numeric_locale()
    rec.force_c_numeric_locale()
    assert locale.localeconv()["decimal_point"] == "."


def test_build_recognizer_forces_c_locale_before_creating_the_kaldi_recognizer(monkeypatch):
    # Même si Model() ou une dépendance a repositionné la locale sur une virgule,
    # build_recognizer() la neutralise AVANT d'instancier KaldiRecognizer — donc
    # avant tout Result() ultérieur.
    name = _set_a_comma_locale()
    if name is None:
        pytest.skip("aucune locale à virgule décimale installée sur ce système")

    seen = {}

    class FakeKaldi:
        def __init__(self, *args):
            seen["decimal_point"] = locale.localeconv()["decimal_point"]

        def SetWords(self, flag):
            pass

    monkeypatch.setattr(rec, "KaldiRecognizer", FakeKaldi)

    rec.build_recognizer(object(), rec.MODE_FULL)

    assert seen["decimal_point"] == "."
