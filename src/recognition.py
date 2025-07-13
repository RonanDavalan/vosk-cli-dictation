# src/recognition.py

import json
import queue
import os
from vosk import Model, KaldiRecognizer
from config.config import config
from src.i18n import get_translation

def load_model(model_name: str):
    """
    Loads a Vosk model by its name (e.g., 'fr').
    Returns (recognizer, model_name_on_disk) or (None, None) if failed.
    """
    _ = get_translation()
    model_path = config.get_model_path_by_name(model_name)

    if not model_path:
        return None, None

    model_name_on_disk = os.path.basename(model_path)

    if not os.path.isdir(model_path):
        # UPDATE: Use theme colors from config
        print(f"{config.color_error}{_('Error: Model folder not found:')} {model_path}{config.RESET}")
        print(f"{config.color_info}{_('Please check your config.yaml and ensure the model is unzipped.')}{config.RESET}")
        return None, None

    try:
        # UPDATE: Use theme colors from config
        print(f"{config.color_info}{_('Attempting to load model:')} {model_name_on_disk}...{config.RESET}")
        model = Model(model_path)
        recognizer = KaldiRecognizer(model, config.audio['sample_rate'])
        recognizer.SetWords(True)
        print(f"{config.color_success}{_('Model loaded successfully:')} {model_name_on_disk}{config.RESET}")
        return recognizer, model_name_on_disk
    except Exception as e:
        error_msg = _("Fatal error while loading model '{model_name}': {error}").format(model_name=model_name_on_disk, error=e)
        # UPDATE: Use theme colors from config
        print(f"{config.color_error}{error_msg}{config.RESET}")
        return None, None

def recognition_thread(recognizer, audio_queue: queue.Queue, text_queue: queue.Queue, stop_event, display_partials_event):
    """
    Listens for audio data and puts only FINAL RESULTS into the text_queue.
    Displays partial results only when the display_partials_event is set.
    """
    _ = get_translation()
    last_partial_length = 0
    in_progress_label = _("[In progress]")

    while not stop_event.is_set():
        try:
            data = audio_queue.get(timeout=0.1)

            if recognizer.AcceptWaveform(data):
                result_json = recognizer.Result()
                result_dict = json.loads(result_json)
                text = result_dict.get("text", "")
                if text:
                    text_queue.put(text)
                    if last_partial_length > 0:
                        print(f"\r{' ' * last_partial_length}\r", end='', flush=True)
                        last_partial_length = 0
            else:
                partial_dict = json.loads(recognizer.PartialResult())
                partial_text = partial_dict.get("partial", "").strip()

                if display_partials_event.is_set() and partial_text:
                    print(f"\r{' ' * last_partial_length}\r", end='', flush=True)
                    # UPDATE: Use theme colors from config
                    display_text = f"{config.color_info}{in_progress_label} {partial_text}{config.RESET}"
                    print(display_text, end='', flush=True)
                    last_partial_length = len(in_progress_label) + 1 + len(partial_text)
                elif last_partial_length > 0:
                    print(f"\r{' ' * last_partial_length}\r", end='', flush=True)
                    last_partial_length = 0

        except queue.Empty:
            continue
        except Exception as e:
            if last_partial_length > 0:
                 print(f"\r{' ' * last_partial_length}\r", end='', flush=True)
            # UPDATE: Use theme colors from config
            print(f"\n{config.color_error}{_('Error in recognition thread:')} {e}{config.RESET}")
            break

    if last_partial_length > 0:
        print(f"\r{' ' * last_partial_length}\r", end='', flush=True)
