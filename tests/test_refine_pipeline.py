# Finition des énoncés : file ordonnée, délai, énoncés-commandes, moteur absent,
# tampon audio du fil de reconnaissance et attente des commandes de fin dans l'UI.
# Le moteur de finition est un faux ; aucun modèle n'est requis.

import json
import queue
import threading
import time

import pytest

import src.recognition as rec
import src.ui as ui
from config.config import config
from src.refine import RefineEngine
from src.refine.pipeline import RefinePipeline, plausible
from src.runtime_state import REFINE_OUTCOMES, runtime_state, STATE_DICTATING
from src.text_processing import TextProcessor

PCM = b"\x01\x00" * 16000  # une seconde


class FakeEngine(RefineEngine):
    spec = "whisper:fake"

    def __init__(self, answers=None, delay=0.0, error=None):
        self.answers = answers or {}
        self.delay = delay
        self.error = error
        self.calls = []

    def refine(self, pcm, language):
        self.calls.append((len(pcm), language))
        if self.error:
            raise self.error
        time.sleep(
            self.delay if not callable(self.delay) else self.delay(len(self.calls))
        )
        return self.answers.get(len(self.calls), "texte affiné")


@pytest.fixture(autouse=True)
def clean_counters():
    runtime_state.refine_counts = dict.fromkeys(REFINE_OUTCOMES, 0)
    runtime_state.refine_mean_ms = 0.0
    config.set_language("fr")
    yield


class Sink:
    def __init__(self):
        self.items = queue.Queue()

    def __call__(self, text, words, refined):
        self.items.put((text, words, refined))

    def take(self, n, timeout=3.0):
        out = []
        end = time.monotonic() + timeout
        while len(out) < n and time.monotonic() < end:
            try:
                out.append(self.items.get(timeout=0.05))
            except queue.Empty:
                pass
        return out


def make(engine, timeout_ms=1000, report=None):
    sink = Sink()
    pipe = RefinePipeline(sink, timeout_ms, report)
    pipe.set_engine(engine)
    return pipe, sink


def counts():
    return runtime_state.snapshot()["refine"]


def test_refined_text_replaces_vosk_text():
    pipe, sink = make(FakeEngine({1: "Bonjour, monde."}))
    pipe.submit("bonjour monde", [{"w": 1}], PCM, "fr")
    assert sink.take(1) == [("Bonjour, monde.", [], True)]
    assert counts()["done"] == 1 and counts()["mean_ms"] >= 0


def test_typing_order_is_the_order_of_utterances():
    # Le premier énoncé est le plus lent : le second, déjà fini, attend son tour.
    engine = FakeEngine(
        {1: "premier", 2: "second"}, delay=lambda n: 0.3 if n == 1 else 0.0
    )
    pipe, sink = make(engine, timeout_ms=2000)
    pipe.submit("un", [], PCM, "fr")
    pipe.submit("deux", [], PCM, "fr")
    assert [t for t, _w, _r in sink.take(2)] == ["premier", "second"]


def test_timeout_types_the_vosk_text_and_counts_it():
    pipe, sink = make(FakeEngine(delay=0.6), timeout_ms=100)
    t0 = time.monotonic()
    pipe.submit("texte de vosk", [{"w": 1}], PCM, "fr")
    assert sink.take(1) == [("texte de vosk", [{"w": 1}], False)]
    assert time.monotonic() - t0 < 0.5
    assert counts()["timeout"] == 1 and counts()["done"] == 0


def test_a_stuck_engine_does_not_reorder_later_utterances():
    engine = FakeEngine({2: "deux affiné"}, delay=lambda n: 0.5 if n == 1 else 0.0)
    pipe, sink = make(engine, timeout_ms=150)
    pipe.submit("un", [], PCM, "fr")
    pipe.submit("deux", [], PCM, "fr")
    got = [t for t, _w, _r in sink.take(2)]
    assert got == ["un", "deux"]
    assert counts()["timeout"] == 2


def test_command_utterance_is_not_refined_but_keeps_its_place():
    engine = FakeEngine({1: "premier affiné"}, delay=0.2)
    pipe, sink = make(engine, timeout_ms=2000)
    pipe.submit("bonjour", [], PCM, "fr")
    pipe.submit("stop dictée", [{"w": 2}], PCM, "fr", refine=False)
    got = sink.take(2)
    assert got == [("premier affiné", [], True), ("stop dictée", [{"w": 2}], False)]
    assert len(engine.calls) == 1


def test_engine_error_falls_back_and_is_reported():
    seen = []
    pipe, sink = make(
        FakeEngine(error=RuntimeError("boom")), report=lambda k, d: seen.append((k, d))
    )
    pipe.submit("texte", [], PCM, "fr")
    assert sink.take(1) == [("texte", [], False)]
    assert counts()["error"] == 1 and seen == [("error", "boom")]


def test_empty_or_runaway_text_is_rejected():
    pipe, sink = make(FakeEngine({1: "", 2: "mot " * 200}))
    pipe.submit("un", [], PCM, "fr")
    pipe.submit("deux", [], PCM, "fr")
    assert [(t, r) for t, _w, r in sink.take(2)] == [("un", False), ("deux", False)]
    assert counts()["rejected"] == 2


def test_plausible_scales_with_the_audio_duration():
    assert plausible("bonjour tout le monde", 2.0)
    assert not plausible("", 2.0)
    assert not plausible("ha " * 100, 1.0)
    assert plausible("ha " * 100, 15.0)


def test_guard_can_refuse_a_refined_text():
    pipe, sink = make(FakeEngine({1: "stop dictée"}))
    pipe.submit("texte", [], PCM, "fr", guard=lambda refined: "stop" not in refined)
    assert sink.take(1) == [("texte", [], False)]
    assert counts()["rejected"] == 1


def test_without_engine_utterances_pass_through_in_order():
    pipe, sink = make(None)
    assert not pipe.active()
    pipe.submit("un", [], b"", "fr")
    pipe.submit("deux", [], b"", "fr")
    assert [t for t, _w, _r in sink.take(2)] == ["un", "deux"]
    assert pipe.pending() == 0


def test_missing_audio_counts_as_skipped():
    pipe, sink = make(FakeEngine())
    pipe.submit("texte", [], b"", "fr")
    assert sink.take(1) == [("texte", [], False)]
    assert counts()["skipped"] == 1


def test_pending_counts_until_delivery():
    pipe, sink = make(FakeEngine(delay=0.3), timeout_ms=2000)
    pipe.submit("un", [], PCM, "fr")
    assert pipe.pending() == 1
    sink.take(1)
    time.sleep(0.05)
    assert pipe.pending() == 0


# --- fil de reconnaissance ------------------------------------------------- #


class FakeRec:
    def __init__(self, script):
        self.script = list(script)
        self.i = 0
        self.step = ("partial", {"partial": ""})

    def AcceptWaveform(self, data):
        if self.i < len(self.script):
            self.step = self.script[self.i]
            self.i += 1
        else:
            self.step = ("partial", {"partial": ""})
        return self.step[0] == "final"

    def Result(self):
        return json.dumps(self.step[1])

    def PartialResult(self):
        return json.dumps(self.step[1])

    def Reset(self):
        pass

    def SetWords(self, flag):
        pass


def run_recognition(script, monkeypatch, pipeline, chunks=None):
    fake = FakeRec(script)
    monkeypatch.setattr(rec, "build_recognizer", lambda model, mode: fake)
    audio_q = queue.Queue(maxsize=1024)
    text_q = queue.Queue(maxsize=64)
    stop = threading.Event()
    wake = threading.Event()
    wake.set()
    runtime_state.set_state(STATE_DICTATING)
    runtime_state._last_transition = 0.0
    for _ in range(chunks or len(script) + 1):
        audio_q.put_nowait(b"\x01\x00" * 2048)
    t = threading.Thread(
        target=rec.recognition_thread,
        args=(
            object(),
            fake,
            audio_q,
            text_q,
            queue.Queue(maxsize=32),
            stop,
            threading.Event(),
            wake,
            None,
            pipeline,
        ),
        daemon=True,
    )
    t.start()
    time.sleep(0.6)
    stop.set()
    wake.set()
    t.join(timeout=2.0)
    out = []
    while True:
        try:
            out.append(text_q.get_nowait())
        except queue.Empty:
            return out


def final(text):
    return (
        "final",
        {"text": text, "result": [{"word": w, "conf": 1.0} for w in text.split()]},
    )


PARTIAL = ("partial", {"partial": "bon"})
SILENCE = ("partial", {"partial": ""})


def test_recognition_hands_refined_text_to_the_ui(monkeypatch):
    engine = FakeEngine({1: "Bonjour à tous."})
    pipe, sink = make(engine)
    out = run_recognition([PARTIAL, final("bonjour à tous")], monkeypatch, pipe)
    assert out == []
    assert sink.take(1) == [("Bonjour à tous.", [], True)]
    assert engine.calls and engine.calls[0][1] == "fr"


def test_audio_is_kept_from_just_before_the_first_partial(monkeypatch):
    engine = FakeEngine()
    pipe, sink = make(engine)
    chunk = 2048 * 2
    script = [SILENCE] * 20 + [PARTIAL, final("bonjour")]
    run_recognition(script, monkeypatch, pipe)
    sink.take(1)
    pcm_len = engine.calls[0][0]
    preroll = (
        int(
            rec.REFINE_PREROLL_S
            / (config.audio["buffer_size"] / config.audio["sample_rate"])
        )
        + 1
    )
    assert pcm_len == (preroll + 2) * chunk


def test_audio_is_capped_to_thirty_seconds(monkeypatch):
    engine = FakeEngine()
    pipe, sink = make(engine)
    chunk_s = config.audio["buffer_size"] / config.audio["sample_rate"]
    n = int(rec.REFINE_MAX_AUDIO_S / chunk_s) + 40
    run_recognition(
        [PARTIAL] + [SILENCE] * (n - 2) + [final("long")], monkeypatch, pipe, chunks=n
    )
    sink.take(1)
    assert engine.calls[0][0] <= int(rec.REFINE_MAX_AUDIO_S / chunk_s) * 2048 * 2


def test_stop_phrase_utterance_is_not_refined(monkeypatch):
    engine = FakeEngine({1: "premier"})
    pipe, sink = make(engine)
    run_recognition(
        [PARTIAL, final("bonjour"), PARTIAL, final("stop dictée")], monkeypatch, pipe
    )
    got = sink.take(2)
    assert [(t, r) for t, _w, r in got] == [("premier", True), ("stop dictée", False)]
    assert len(engine.calls) == 1
    assert counts()["skipped"] == 1


def test_refined_text_that_adds_a_command_is_refused(monkeypatch):
    pipe, sink = make(FakeEngine({1: "Bonjour, stop dictée."}))
    run_recognition([PARTIAL, final("bonjour")], monkeypatch, pipe)
    assert sink.take(1) == [("bonjour", [{"word": "bonjour", "conf": 1.0}], False)]


def test_without_engine_text_goes_straight_to_the_ui_and_no_audio_is_kept(monkeypatch):
    pipe, sink = make(None)
    out = run_recognition([PARTIAL, final("bonjour")], monkeypatch, pipe)
    assert [item[0] for item in out] == ["bonjour"] and len(out[0]) == 2
    assert sink.take(1, timeout=0.2) == []


def test_without_pipeline_the_recognition_is_unchanged(monkeypatch):
    out = run_recognition([PARTIAL, final("bonjour")], monkeypatch, None)
    assert [item[0] for item in out] == ["bonjour"] and len(out[0]) == 2


# --- UI ------------------------------------------------------------------------- #


class FakeRefiner:
    timeout_s = 0.3

    def __init__(self, pending):
        self._pending = pending

    def pending(self):
        return self._pending


@pytest.fixture
def ui_harness(monkeypatch):
    typed, copied = [], []
    monkeypatch.setattr(ui, "type_text", lambda s: (typed.append(s), True)[1])
    monkeypatch.setattr(ui, "press_key", lambda *a, **k: True)
    monkeypatch.setattr(ui, "play_sound", lambda: None)

    class _Clip:
        @staticmethod
        def copy(text):
            copied.append(text)

    monkeypatch.setattr(ui, "pyperclip", _Clip)
    started = []

    def start(refiner):
        text_q, ctrl_q = queue.Queue(maxsize=64), queue.Queue(maxsize=32)
        stop, wake = threading.Event(), threading.Event()
        wake.set()
        t = threading.Thread(
            target=ui.ui_thread,
            args=(
                text_q,
                ctrl_q,
                stop,
                TextProcessor("fr"),
                threading.Event(),
                threading.Event(),
                wake,
                refiner,
            ),
            daemon=True,
        )
        t.start()
        ctrl_q.put_nowait("DICTATION_ON")
        time.sleep(0.5)
        runtime_state._last_transition = 0.0
        started.append((stop, t))
        return text_q, ctrl_q

    yield start, typed, copied
    for stop, t in started:
        stop.set()
        t.join(timeout=2.0)


def test_refined_text_keeps_its_case_and_french_spacing(ui_harness):
    start, typed, _copied = ui_harness
    text_q, _ctrl = start(None)
    text_q.put_nowait(("Bonjour Marie, ça va ?", [], True))
    text_q.put_nowait(("vosk reste en minuscules", []))
    time.sleep(0.5)
    assert typed[0] == "Bonjour Marie, ça va ?"
    assert typed[1].strip() == "Vosk reste en minuscules"


def test_finalize_waits_for_the_utterances_still_being_refined(ui_harness):
    start, typed, copied = ui_harness
    refiner = FakeRefiner(pending=1)
    text_q, ctrl_q = start(refiner)
    ctrl_q.put_nowait("FINALIZE_SESSION")
    time.sleep(0.15)
    assert copied == []
    text_q.put_nowait(("Dernier énoncé.", [], True))
    refiner._pending = 0
    time.sleep(0.4)
    assert copied and "Dernier énoncé." in copied[0]
    assert any("Dernier" in t for t in typed)


def test_finalize_does_not_wait_forever(ui_harness):
    start, _typed, copied = ui_harness
    text_q, ctrl_q = start(FakeRefiner(pending=1))
    text_q.put_nowait(("Avant.", [], True))
    time.sleep(0.2)
    ctrl_q.put_nowait("FINALIZE_SESSION")
    time.sleep(1.2)
    assert copied and "Avant." in copied[0]
