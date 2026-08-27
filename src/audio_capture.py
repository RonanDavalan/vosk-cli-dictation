# src/audio_capture.py

import queue
import time
import pyaudio
from config.config import config
from src.i18n import get_translation
from src.runtime_state import runtime_state

def put_drop_oldest(q, item) -> bool:
    """Enqueue `item`; if the queue is full, drop its oldest entry first.

    Returns True iff an entry had to be dropped (overflow). This is the
    "jeter le plus ancien" policy of chantier 7 volet C, factored out so it
    can be unit-tested without PortAudio.
    """
    try:
        q.put_nowait(item)
        return False
    except queue.Full:
        try:
            q.get_nowait()
        except queue.Empty:
            pass
        try:
            q.put_nowait(item)
        except queue.Full:
            pass
        return True


def open_stream(p):
    """Opens an input stream on an existing PyAudio instance.

    Kept separate from initialize_audio() so the capture thread can reopen the
    stream after a deep-sleep close (chantier 7 volet D) without recreating the
    PyAudio instance.
    """
    return p.open(
        format=pyaudio.paInt16,
        channels=config.audio['channels'],
        rate=config.audio['sample_rate'],
        input=True,
        frames_per_buffer=config.audio['frames_per_buffer'],
    )


def initialize_audio():
    """
    Initializes and opens a PyAudio stream for audio input.
    """
    _ = get_translation()
    try:
        p = pyaudio.PyAudio()
        stream = open_stream(p)
        return p, stream
    except Exception as e:
        # UPDATE: Use theme colors from config
        print(f"{config.color_error}{_('Critical error during audio initialization:')} {e}{config.RESET}")
        if "Invalid input device" in str(e) or "No Default Input Device" in str(e):
            print(f"{config.color_info}{_('TIP: This can happen if no microphone is connected or selected.')}{config.RESET}")
            print(f"{config.color_info}{_('Check your system audio settings (e.g., with pavucontrol).')}{config.RESET}")
        return None, None

def audio_capture_thread(p, stream, audio_queue, stop_event, sleep_event, wake_event):
    """
    Captures audio and feeds the bounded queue.

    Bounded queue (chantier 7 volet C): when the recognition thread falls
    behind, the oldest chunk is dropped rather than letting latency drift. A
    read backlog inside PortAudio is detected and counted, since
    exception_on_overflow=False hides it.

    Deep sleep (chantier 7 volet D): on entering VEILLE the stream is stopped
    and, by default (`sleep.releases_device`), fully closed so the microphone
    is released and its LED goes off. On waking, the stream is reopened and
    the first ~200 ms of audio is discarded to avoid a stale-buffer artefact.
    `wake_event` gates the recognition thread symmetrically.
    """
    _ = get_translation()
    buffer_size = config.audio['buffer_size']
    releases_device = config.data.get('sleep', {}).get('releases_device', True)
    warmup_chunks = max(1, int(0.2 * config.audio['sample_rate'] / buffer_size)) + 1
    last_overflow_warning = 0.0

    def drain_queue():
        while True:
            try:
                audio_queue.get_nowait()
            except queue.Empty:
                return

    while not stop_event.is_set():
        try:
            if sleep_event.is_set():
                if stream is not None and _stream_active(stream):
                    try:
                        stream.stop_stream()
                        if releases_device:
                            stream.close()
                            stream = None
                    except Exception:
                        stream = None
                    drain_queue()
                time.sleep(0.1)
                continue

            # Sortie de VEILLE : rouvrir (périphérique relâché) ou redémarrer le
            # flux, puis jeter l'audio d'amorçage.
            if stream is None or not _stream_active(stream):
                if stream is None:
                    try:
                        stream = open_stream(p)
                    except Exception as e:
                        print(f"\n{config.color_error}"
                              f"{_('Could not reopen the audio device:')} {e}{config.RESET}")
                        stop_event.set()
                        break
                else:
                    stream.start_stream()
                for _i in range(warmup_chunks):
                    try:
                        stream.read(buffer_size, exception_on_overflow=False)
                    except Exception:
                        break

            try:
                available = stream.get_read_available()
            except Exception:
                available = 0
            if available > buffer_size * 4:
                runtime_state.bump_input_overflow()

            data = stream.read(buffer_size, exception_on_overflow=False)

            if put_drop_oldest(audio_queue, data):
                runtime_state.bump_audio_overflow()
                now = time.monotonic()
                if now - last_overflow_warning >= 1.0:
                    last_overflow_warning = now
                    print(f"\n{config.color_warning}"
                          f"{_('Recognition is falling behind; dropping audio.')}"
                          f"{config.RESET}")
        except IOError as e:
            # UPDATE: Use theme colors from config
            print(f"{config.color_error}{_('Audio read error (IOError):')} {e}{config.RESET}")
            stop_event.set()
            break
        except Exception as e:
            # UPDATE: Use theme colors from config
            print(f"{config.color_error}{_('Unexpected error in audio capture:')} {e}{config.RESET}")
            stop_event.set()
            break

    try:
        if stream is not None:
            if _stream_active(stream):
                stream.stop_stream()
            stream.close()
    except Exception:
        pass


def _stream_active(stream):
    try:
        return bool(stream.is_active())
    except Exception:
        return False
