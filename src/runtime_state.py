# src/runtime_state.py
#
# État partagé de session, protégé par un verrou. Écrit par les threads audio et
# reconnaissance (compteurs, facteur temps réel), lu par l'UI et — chantier 7
# volet A — par le thread de contrôle pour répondre à `--status` / `--diagnose`.
#
# Un seul objet pour tout le processus : `runtime_state`, sur le modèle de
# `config`.

import threading
import time

# États exposés côté CLI (chantier 7 volet D). Les identifiants d'action de
# configuration (`toggle_recording`, `sleep_toggle`, …) restent inchangés.
STATE_DICTATING = "DICTÉE"
STATE_LISTENING = "ÉCOUTE"
STATE_SLEEPING = "VEILLE"

_RTF_WINDOW = 30  # taille de fenêtre de la moyenne glissante du RTF
_DEBOUNCE_S = 0.5  # anti-rebond après une transition d'état (chantier 7 volet E)


class RuntimeState:
    def __init__(self):
        self._lock = threading.Lock()
        self.state = STATE_LISTENING
        # Blocs audio jetés parce que la file de reconnaissance était pleine.
        self.audio_overflow_count = 0
        # Retards de lecture PortAudio détectés (tampon interne qui se remplit).
        self.input_overflow_count = 0
        # Facteur temps réel du décodage : temps mur d'AcceptWaveform / durée
        # audio du bloc. > 1 = le décodage est plus lent que le temps réel.
        self.rtf_mean = 0.0
        self._rtf_samples = 0
        # Horodatage de la dernière transition d'état, pour l'anti-rebond des
        # déclenchements vocaux (chantier 7 volet E).
        self._last_transition = 0.0

    def set_state(self, state):
        with self._lock:
            changed = state != self.state
            self.state = state
            if changed:
                self._last_transition = time.monotonic()

    def in_debounce(self, window_s: float = _DEBOUNCE_S) -> bool:
        """True si une transition d'état a eu lieu il y a moins de `window_s`."""
        with self._lock:
            return (time.monotonic() - self._last_transition) < window_s

    def bump_audio_overflow(self):
        with self._lock:
            self.audio_overflow_count += 1

    def bump_input_overflow(self):
        with self._lock:
            self.input_overflow_count += 1

    def update_rtf(self, sample):
        """Moyenne glissante exponentielle sur ~`_RTF_WINDOW` blocs."""
        alpha = 2.0 / (_RTF_WINDOW + 1)
        with self._lock:
            if self._rtf_samples == 0:
                self.rtf_mean = sample
            else:
                self.rtf_mean = alpha * sample + (1.0 - alpha) * self.rtf_mean
            self._rtf_samples += 1

    def rtf_over(self, threshold):
        with self._lock:
            return self._rtf_samples > 0 and self.rtf_mean > threshold

    def snapshot(self):
        with self._lock:
            return {
                "state": self.state,
                "audio_overflow_count": self.audio_overflow_count,
                "input_overflow_count": self.input_overflow_count,
                "rtf_mean": round(self.rtf_mean, 3),
            }


runtime_state = RuntimeState()
