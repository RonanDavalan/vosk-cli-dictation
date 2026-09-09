# Chantier stabilité v0.5.1, défaut 1 — le thread de reconnaissance survit à une
# trame malformée (json.JSONDecodeError sur Result()) : il journalise, repart
# d'un recognizer propre, continue à décoder les trames suivantes et ne pose
# jamais stop_event de lui-même.
#
# Le recognizer Vosk est remplacé par un faux ; aucun modèle n'est requis.

import json
import queue
import threading
import time

import pytest

import src.main as appmain
import src.recognition as rec
from config.config import config
from src.recognition import MODE_STOP
from src.runtime_state import runtime_state, STATE_DICTATING


@pytest.fixture(autouse=True)
def _diag_dir_to_tmp(tmp_path, monkeypatch):
    # Les captures de chaîne fautive ne doivent jamais toucher le vrai
    # répertoire de diagnostic pendant les tests.
    monkeypatch.setenv("VOSK_CLI_DIAG_DIR", str(tmp_path / "diag"))


class BadOnNthRec:
    """Final valide à chaque trame, sauf la Nᵉ dont Result() renvoie du JSON
    invalide — ce que json.loads() transforme en json.JSONDecodeError dans le
    thread."""

    def __init__(self, bad_frame, texts):
        self.calls = 0
        self.bad_frame = bad_frame
        self.texts = texts
        self.reset_calls = 0

    def AcceptWaveform(self, data):
        self.calls += 1
        return True  # chaque trame est un final

    def Result(self):
        if self.calls == self.bad_frame:
            return "{ ceci n'est pas du json"
        i = min(self.calls - 1, len(self.texts) - 1)
        return json.dumps({"text": self.texts[i], "result": []})

    def PartialResult(self):
        return json.dumps({"partial": ""})

    def Reset(self):
        self.reset_calls += 1

    def SetWords(self, flag):
        pass


class SilentStopRec:
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


def _drain(q):
    out = []
    try:
        while True:
            out.append(q.get_nowait())
    except queue.Empty:
        pass
    return out


def test_json_decode_error_on_a_frame_does_not_kill_the_thread(monkeypatch):
    config.set_language("fr")
    texts = ["mot1", "mot2", "mot3", "mot4", "mot5"]
    fake = BadOnNthRec(bad_frame=3, texts=texts)
    stop_fake = SilentStopRec()
    monkeypatch.setattr(
        rec, "build_recognizer",
        lambda model, mode: stop_fake if mode == MODE_STOP else fake,
    )

    audio_q = queue.Queue(maxsize=64)
    text_q = queue.Queue(maxsize=64)
    ctrl_q = queue.Queue(maxsize=32)
    stop = threading.Event()
    display = threading.Event()
    display.set()
    wake = threading.Event()
    wake.set()

    runtime_state.set_state(STATE_DICTATING)
    runtime_state._last_transition = 0.0

    for _ in range(len(texts)):
        audio_q.put_nowait(b"\x00\x00")

    t = threading.Thread(
        target=rec.recognition_thread,
        args=(object(), fake, audio_q, text_q, ctrl_q, stop, display, wake),
        daemon=True,
    )
    t.start()
    time.sleep(0.4)

    # Le thread n'a pas posé stop_event de lui-même, il est toujours vivant.
    assert not stop.is_set()
    assert t.is_alive()

    items = _drain(text_q)
    forwarded = [text for text, _words in items]
    # Toutes les trames sauf la 3ᵉ (malformée) sont remontées, dans l'ordre.
    assert forwarded == ["mot1", "mot2", "mot4", "mot5"]
    # Le recognizer a été réinitialisé au moins une fois par la reprise.
    assert fake.reset_calls >= 1

    stop.set()
    wake.set()
    t.join(timeout=2.0)


def test_repeated_decode_errors_keep_recovering(monkeypatch):
    # Une trame sur deux est malformée : le thread continue quand même de
    # transcrire les bonnes et ne meurt jamais.
    config.set_language("fr")

    class AlternatingRec(BadOnNthRec):
        def Result(self):
            if self.calls % 2 == 0:
                return "]]] pas du json"
            return json.dumps({"text": f"bon{self.calls}", "result": []})

    fake = AlternatingRec(bad_frame=-1, texts=[])
    stop_fake = SilentStopRec()
    monkeypatch.setattr(
        rec, "build_recognizer",
        lambda model, mode: stop_fake if mode == MODE_STOP else fake,
    )

    audio_q = queue.Queue(maxsize=64)
    text_q = queue.Queue(maxsize=64)
    ctrl_q = queue.Queue(maxsize=32)
    stop = threading.Event()
    display = threading.Event()
    display.set()
    wake = threading.Event()
    wake.set()

    runtime_state.set_state(STATE_DICTATING)
    runtime_state._last_transition = 0.0

    for _ in range(10):
        audio_q.put_nowait(b"\x00\x00")

    t = threading.Thread(
        target=rec.recognition_thread,
        args=(object(), fake, audio_q, text_q, ctrl_q, stop, display, wake),
        daemon=True,
    )
    t.start()
    time.sleep(0.4)

    assert not stop.is_set()
    assert t.is_alive()
    forwarded = [text for text, _w in _drain(text_q)]
    assert forwarded == ["bon1", "bon3", "bon5", "bon7", "bon9"]

    stop.set()
    wake.set()
    t.join(timeout=2.0)


def test_permanent_decode_errors_escalate_and_end_the_session(monkeypatch):
    # Toutes les trames sont malformées et la reconstruction ne rétablit rien
    # (cas `ada` du 09/09 : json.JSONDecodeError à chaque trame). Au-delà de
    # DECODE_ERROR_MAX_CONSECUTIVE, le thread pose stop_event lui-même et sort,
    # au lieu de boucler indéfiniment sur l'erreur.
    config.set_language("fr")

    class AlwaysBadRec(BadOnNthRec):
        def Result(self):
            return "{ jamais du json"

        def PartialResult(self):
            return "{ jamais du json"

    fake = AlwaysBadRec(bad_frame=-1, texts=[])
    stop_fake = SilentStopRec()
    monkeypatch.setattr(
        rec, "build_recognizer",
        lambda model, mode: stop_fake if mode == MODE_STOP else fake,
    )

    audio_q = queue.Queue(maxsize=64)
    text_q = queue.Queue(maxsize=64)
    ctrl_q = queue.Queue(maxsize=32)
    stop = threading.Event()
    display = threading.Event()
    display.set()
    wake = threading.Event()
    wake.set()

    runtime_state.set_state(STATE_DICTATING)
    runtime_state._last_transition = 0.0

    for _ in range(rec.DECODE_ERROR_MAX_CONSECUTIVE + 20):
        audio_q.put_nowait(b"\x00\x00")

    t = threading.Thread(
        target=rec.recognition_thread,
        args=(object(), fake, audio_q, text_q, ctrl_q, stop, display, wake),
        daemon=True,
    )
    t.start()
    t.join(timeout=2.0)

    # Le thread a posé stop_event de lui-même et s'est terminé.
    assert stop.is_set()
    assert not t.is_alive()
    # Rien n'a été transcrit et la session ne reste pas ouverte à vide.
    assert _drain(text_q) == []


def test_malformed_result_is_captured_to_a_file(monkeypatch, tmp_path):
    # À la première json.JSONDecodeError, la chaîne brute de Result() est
    # écrite telle quelle sous le répertoire de diagnostic (jamais /tmp, jamais
    # le dépôt). Le répertoire est fixé par la fixture autouse.
    config.set_language("fr")
    diag_dir = tmp_path / "diag"

    raw = '{\n  "result" : [{\n      "conf" : ,\n'
    texts = ["mot1", "mot2", "mot3"]

    class RawBadRec(BadOnNthRec):
        def Result(self):
            if self.calls == self.bad_frame:
                return raw
            i = min(self.calls - 1, len(self.texts) - 1)
            return json.dumps({"text": self.texts[i], "result": []})

    fake = RawBadRec(bad_frame=2, texts=texts)
    stop_fake = SilentStopRec()
    monkeypatch.setattr(
        rec, "build_recognizer",
        lambda model, mode: stop_fake if mode == MODE_STOP else fake,
    )

    audio_q = queue.Queue(maxsize=64)
    text_q = queue.Queue(maxsize=64)
    ctrl_q = queue.Queue(maxsize=32)
    stop = threading.Event()
    display = threading.Event()
    display.set()
    wake = threading.Event()
    wake.set()

    runtime_state.set_state(STATE_DICTATING)
    runtime_state._last_transition = 0.0
    for _ in range(len(texts)):
        audio_q.put_nowait(b"\x00\x00")

    t = threading.Thread(
        target=rec.recognition_thread,
        args=(object(), fake, audio_q, text_q, ctrl_q, stop, display, wake),
        daemon=True,
    )
    t.start()
    time.sleep(0.4)
    stop.set()
    wake.set()
    t.join(timeout=2.0)

    captures = list(diag_dir.glob("vosk-result-malforme_*.txt"))
    assert len(captures) == 1
    assert captures[0].read_text(encoding="utf-8") == raw


# --- défaut 1, seconde couche : supervision des threads par main.py -----------

def _blocker(hold):
    hold.wait(5.0)


def test_supervise_threads_detects_dead_core_thread_within_two_seconds():
    stop = threading.Event()
    hold = threading.Event()
    alive_rec = threading.Thread(target=_blocker, args=(hold,), daemon=True)
    alive_audio = threading.Thread(target=_blocker, args=(hold,), daemon=True)
    dying_ui = threading.Thread(target=lambda: None, daemon=True)
    for th in (alive_rec, alive_audio, dying_ui):
        th.start()
    supervised = {"recognition": alive_rec, "audio": alive_audio, "ui": dying_ui}

    t0 = time.monotonic()
    dead = None
    while time.monotonic() - t0 < 2.0:
        dead = appmain.supervise_threads(supervised, stop)
        if dead is not None:
            break
        time.sleep(0.05)

    assert dead == "ui"
    assert stop.is_set()
    assert time.monotonic() - t0 < 2.0
    hold.set()


def test_supervise_threads_quiet_while_all_alive():
    stop = threading.Event()
    hold = threading.Event()
    threads = {
        name: threading.Thread(target=_blocker, args=(hold,), daemon=True)
        for name in ("recognition", "audio", "ui")
    }
    for th in threads.values():
        th.start()

    assert appmain.supervise_threads(threads, stop) is None
    assert not stop.is_set()
    hold.set()


def test_supervise_threads_silent_when_stop_already_requested():
    stop = threading.Event()
    stop.set()
    dead = threading.Thread(target=lambda: None, daemon=True)
    dead.start()
    dead.join()
    # Arrêt déjà demandé : une mort de thread n'est plus un incident à signaler.
    assert appmain.supervise_threads({"ui": dead}, stop) is None
