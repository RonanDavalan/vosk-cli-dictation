# Chantier stabilité v0.5.1 — Vosk/Kaldi sérialise les flottants de
# SetWords(True) avec le séparateur décimal de LC_NUMERIC. Sous fr_FR.UTF-8
# (locale à virgule), Result() rend « "conf" : 1,000000 » et json.loads casse à chaque
# final avec mots. Le correctif force LC_NUMERIC du processus à « C » au
# démarrage (src/main.py) et défensivement dans build_recognizer().
#
# Ces tests exigent qu'une locale à virgule décimale soit installée sur la
# machine ; ils se sautent proprement sinon (CI, conteneur minimal).

import json
import locale
import queue
import threading
import time

import pytest

import src.recognition as rec
from config.config import config
from src.recognition import MODE_STOP
from src.runtime_state import runtime_state, STATE_DICTATING

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


def test_the_captured_comma_locale_string_is_really_invalid_json():
    # La chaîne exacte capturée en conditions réelles (virgule décimale) n'est pas
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


class _LocaleSensitiveRec:
    """Recognizer bouché qui sérialise ses flottants selon la locale numérique
    du moment — comme Vosk/Kaldi. Sous une locale à virgule, Result() renvoie du
    JSON invalide ; sous « C », du JSON valide."""

    def __init__(self, texts):
        self.texts = texts
        self.calls = 0

    def AcceptWaveform(self, data):
        self.calls += 1
        return True

    def _floats(self):
        dp = locale.localeconv()["decimal_point"]
        return f'"conf" : 0{dp}82, "start" : 1{dp}5, "end" : 2{dp}0'

    def Result(self):
        i = min(self.calls - 1, len(self.texts) - 1)
        return ('{\n  "result" : [{ ' + self._floats()
                + ', "word" : "' + self.texts[i] + '" }],\n'
                + '  "text" : "' + self.texts[i] + '"\n}')

    def PartialResult(self):
        return json.dumps({"partial": ""})

    def Reset(self):
        pass

    def SetWords(self, flag):
        pass


class _SilentStopRec:
    """Recognizer d'arrêt bouché : ne déclenche jamais."""

    def AcceptWaveform(self, data):
        return False

    def PartialResult(self):
        return json.dumps({"partial": ""})

    def Result(self):
        return json.dumps({"text": "", "result": []})

    def Reset(self):
        pass

    def SetWords(self, flag):
        pass


def test_recognition_loop_guards_a_late_locale_flip(monkeypatch):
    # Essai interactif en conditions réelles : LC_NUMERIC bascule sur une
    # virgule APRÈS build_recognizer(). La garde par trame de la boucle de
    # reconnaissance neutralise la locale avant chaque Result() : aucun final
    # n'est perdu, aucune json.JSONDecodeError.
    name = _set_a_comma_locale()
    if name is None:
        pytest.skip("aucune locale à virgule décimale installée sur ce système")

    config.set_language("fr")
    texts = ["un", "deux", "trois", "quatre"]
    fake = _LocaleSensitiveRec(texts)
    stop_fake = _SilentStopRec()
    monkeypatch.setattr(
        rec, "build_recognizer",
        lambda model, mode: stop_fake if mode == MODE_STOP else fake,
    )

    audio_q = queue.Queue(maxsize=64)
    text_q = queue.Queue(maxsize=64)
    ctrl_q = queue.Queue(maxsize=32)
    stop = threading.Event()
    display = threading.Event()
    wake = threading.Event()
    wake.set()

    runtime_state.set_state(STATE_DICTATING)
    runtime_state._last_transition = 0.0
    for _ in range(len(texts)):
        audio_q.put_nowait(b"\x00\x00")

    # La locale est déjà à la virgule au démarrage du thread (flip « tardif »).
    assert locale.localeconv()["decimal_point"] == ","

    t = threading.Thread(
        target=rec.recognition_thread,
        args=(object(), fake, audio_q, text_q, ctrl_q, stop, display, wake),
        daemon=True,
    )
    t.start()
    time.sleep(0.4)

    assert not stop.is_set()
    forwarded = [txt for txt, _w in _drain(text_q)]
    assert forwarded == texts  # tous les finaux remontés, aucun perdu

    stop.set()
    wake.set()
    t.join(timeout=2.0)


def _drain(q):
    out = []
    try:
        while True:
            out.append(q.get_nowait())
    except queue.Empty:
        pass
    return out
