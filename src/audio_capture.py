# src/audio_capture.py

import pyaudio
from config.config import config
from src.i18n import get_translation

def initialize_audio():
    """
    Initializes and opens a PyAudio stream for audio input.
    """
    _ = get_translation()
    try:
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=config.audio['channels'],
            rate=config.audio['sample_rate'],
            input=True,
            frames_per_buffer=config.audio['frames_per_buffer']
        )
        return p, stream
    except Exception as e:
        # UPDATE: Use theme colors from config
        print(f"{config.color_error}{_('Critical error during audio initialization:')} {e}{config.RESET}")
        if "Invalid input device" in str(e) or "No Default Input Device" in str(e):
            print(f"{config.color_info}{_('TIP: This can happen if no microphone is connected or selected.')}{config.RESET}")
            print(f"{config.color_info}{_('Check your system audio settings (e.g., with pavucontrol).')}{config.RESET}")
        return None, None

def audio_capture_thread(stream, audio_queue, stop_event):
    """
    A thread that continuously captures audio data from the stream and puts
    it into a queue for the recognition thread to process.
    """
    _ = get_translation()
    while not stop_event.is_set():
        try:
            data = stream.read(config.audio['buffer_size'], exception_on_overflow=False)
            audio_queue.put(data)
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
