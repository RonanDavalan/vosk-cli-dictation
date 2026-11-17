# src/refine/pipeline.py
#
# File ordonnée de finition. Un énoncé fini est soumis avec son audio ; le
# moteur le traite dans un fil de travail pendant que Vosk continue, et un
# second fil rend les énoncés dans l'ordre où ils ont été soumis, au plus tard
# `timeout_ms` après leur soumission : passé ce délai, le texte de Vosk part tel
# quel. Un énoncé-commande traverse la même file sans être affiné, pour ne pas
# doubler un énoncé précédent encore en cours de finition.

import concurrent.futures
import queue
import threading
import time

from src import refine as _refine_pkg
from src.runtime_state import runtime_state

# Une parole tient en moins de ~20 caractères par seconde ; au-delà de cette
# marge le moteur boucle sur un mot (hallucination) et le texte de Vosk vaut mieux.
MAX_CHARS_PER_SECOND = 25
MAX_CHARS_SLACK = 20


def plausible(text: str, audio_seconds: float) -> bool:
    return (
        bool(text)
        and len(text) <= audio_seconds * MAX_CHARS_PER_SECOND + MAX_CHARS_SLACK
    )


class _Job:
    def __init__(
        self, text, words, language, future, submitted, deadline, audio_seconds, guard
    ):
        self.text = text
        self.words = words
        self.language = language
        self.future = future
        self.submitted = submitted
        self.deadline = deadline
        self.audio_seconds = audio_seconds
        self.guard = guard


class RefinePipeline:
    """`deliver(text, words, refined)` reçoit chaque énoncé dans l'ordre.
    `guard(text)` (facultatif) dit si un texte affiné est admissible (par
    exemple : n'introduit pas une phrase de commande) ; `report(kind, detail)`
    signale une erreur du moteur."""

    def __init__(self, deliver, timeout_ms=2000, report=None, clock=time.monotonic):
        self._deliver = deliver
        self._report = report
        self._clock = clock
        self.timeout_s = timeout_ms / 1000.0
        self._engine = None
        self._lock = threading.Lock()
        self._pending = 0
        self._jobs = queue.Queue()
        self._pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="refine"
        )
        self._worker = threading.Thread(
            target=self._run, name="refine-order", daemon=True
        )
        self._worker.start()

    # --- moteur ------------------------------------------------------------ #

    def set_engine(self, engine) -> None:
        with self._lock:
            self._engine = engine

    @property
    def engine(self):
        with self._lock:
            return self._engine

    def active(self) -> bool:
        return self.engine is not None

    # --- côté fil de reconnaissance ------------------------------------------ #

    def submit(self, text, words, pcm, language, refine=True, guard=None) -> None:
        """Met un énoncé dans la file. Sans moteur, ou pour un énoncé-commande
        (`refine=False`), il traverse la file tel quel."""
        engine = self.engine if refine else None
        now = self._clock()
        seconds = len(pcm) / 2.0 / _refine_pkg.SAMPLE_RATE if pcm else 0.0
        future = (
            self._pool.submit(engine.refine, pcm, language) if engine and pcm else None
        )
        if engine is not None and not pcm:
            runtime_state.note_refine("skipped")
        with self._lock:
            self._pending += 1
        self._jobs.put(
            _Job(
                text, words, language, future, now, now + self.timeout_s, seconds, guard
            )
        )

    def pending(self) -> int:
        """Énoncés soumis dont le texte n'est pas encore rendu."""
        with self._lock:
            return self._pending

    def shutdown(self) -> None:
        self._jobs.put(None)
        self._pool.shutdown(wait=False, cancel_futures=True)

    # --- fil d'ordre ------------------------------------------------------------ #

    def _run(self):
        while True:
            job = self._jobs.get()
            if job is None:
                return
            text, refined = job.text, False
            if job.future is not None:
                text, refined = self._outcome(job)
            try:
                self._deliver(text, job.words if not refined else [], refined)
            finally:
                with self._lock:
                    self._pending -= 1

    def _outcome(self, job):
        try:
            result = job.future.result(timeout=max(0.0, job.deadline - self._clock()))
        except concurrent.futures.TimeoutError:
            job.future.cancel()
            runtime_state.note_refine("timeout")
            return job.text, False
        except Exception as e:
            runtime_state.note_refine("error")
            if self._report:
                self._report("error", str(e))
            return job.text, False
        result = (result or "").strip()
        if not plausible(result, job.audio_seconds) or (
            job.guard and not job.guard(result)
        ):
            runtime_state.note_refine("rejected")
            return job.text, False
        runtime_state.note_refine("done", (self._clock() - job.submitted) * 1000.0)
        return result, True
