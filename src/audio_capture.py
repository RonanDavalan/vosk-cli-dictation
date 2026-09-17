# src/audio_capture.py

import queue
import time
import pyaudio
from config.config import config
from src.i18n import get_translation
from src.runtime_state import runtime_state

def put_drop_oldest(q, item) -> bool:
    """Met `item` en file ; si la file est pleine, jette d'abord son entrée
    la plus ancienne.

    Retourne True si une entrée a dû être jetée (débordement). Quand le
    thread de reconnaissance prend du retard, le bloc le plus ancien est
    jeté plutôt que de laisser la latence dériver. Extraite pour pouvoir
    être testée sans PortAudio.
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
    """Ouvre un flux d'entrée sur une instance PyAudio existante.

    Séparée de initialize_audio() pour que le thread de capture puisse
    rouvrir le flux après une fermeture en veille profonde sans recréer
    l'instance PyAudio.
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
    Initialise et ouvre un flux PyAudio pour l'entrée audio.
    """
    _ = get_translation()
    try:
        p = pyaudio.PyAudio()
        stream = open_stream(p)
        return p, stream
    except Exception as e:
        # Couleurs du thème depuis la configuration
        print(f"{config.color_error}{_('Critical error during audio initialization:')} {e}{config.RESET}")
        if "Invalid input device" in str(e) or "No Default Input Device" in str(e):
            print(f"{config.color_info}{_('TIP: This can happen if no microphone is connected or selected.')}{config.RESET}")
            print(f"{config.color_info}{_('Check your system audio settings (e.g., with pavucontrol).')}{config.RESET}")
        return None, None

def audio_capture_thread(p, stream, audio_queue, stop_event, sleep_event, wake_event):
    """
    Capture l'audio et alimente la file bornée.

    File bornée : quand le thread de reconnaissance prend du retard, le bloc
    le plus ancien est jeté plutôt que de laisser la latence dériver. Un
    retard de lecture interne à PortAudio est détecté et compté, car
    exception_on_overflow=False le masque.

    Veille profonde : à l'entrée en VEILLE le flux est arrêté puis, par
    défaut (`sleep.releases_device`), entièrement fermé pour libérer le
    micro (sa LED s'éteint). Au réveil, le flux est rouvert et les ~200
    premières ms d'audio sont jetées pour éviter un artefact de tampon
    périmé. `wake_event` cadence symétriquement le thread de reconnaissance.
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
            # Couleurs du thème depuis la configuration
            print(f"{config.color_error}{_('Audio read error (IOError):')} {e}{config.RESET}")
            stop_event.set()
            break
        except Exception as e:
            # Couleurs du thème depuis la configuration
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
