# src/keyboard_listener.py

import queue
from pynput.keyboard import GlobalHotKeys
from config.config import config
from src.i18n import get_translation

def keyboard_listener_thread(control_queue: queue.Queue, stop_event):
    """
    Thread function that listens for pre-defined global hotkeys.
    FINAL CORRECTION: This version uses pynput.keyboard.GlobalHotKeys,
    which is the correct class for listening to a dictionary of hotkeys.
    """
    _ = get_translation()

    def on_toggle():
        """Callback for the toggle recording hotkey."""
        control_queue.put('TOGGLE_RECORDING')

    def on_finalize():
        """Callback for the finalize session hotkey."""
        control_queue.put('FINALIZE_SESSION')

    # Map action names from the config file to their callback functions.
    actions = {
        'toggle_recording': on_toggle,
        'finalize_session': on_finalize,
    }

    def format_hotkey_string(keys: list) -> str:
        """
        Formats a list of key names into a string that pynput can parse.
        Example: ['alt_l', 'h'] -> '<alt_l>+h'
        """
        # A key name is considered a "special" key if its name is longer than one character.
        # These need to be wrapped in angle brackets.
        formatted_keys = [f'<{k}>' if len(k) > 1 else k for k in keys]
        return "+".join(formatted_keys)

    # Dynamically build the hotkeys dictionary for the listener.
    # The format required by GlobalHotKeys is {'<key_combo>': callback_function}
    hotkeys_to_listen = {}
    for action, hotkey_config in config.hotkeys.items():
        if action in actions:
            try:
                # pynput_keys is a list from config, e.g., ['alt_l', 'h']
                pynput_keys = hotkey_config.get('pynput_keys', [])
                if pynput_keys:
                    hotkey_string = format_hotkey_string(pynput_keys)
                    hotkeys_to_listen[hotkey_string] = actions[action]
            except (TypeError, KeyError, AttributeError) as e:
                # This handles cases where config might be malformed.
                print(f"{config.RED}Could not create hotkey for action '{action}': {e}{config.RESET}")

    if not hotkeys_to_listen:
        print(f"{config.YELLOW}No valid hotkeys found in configuration. Keyboard listener will not run.{config.RESET}")
        return

    # Create and run the listener with the defined hotkeys.
    # GlobalHotKeys runs in its own thread.
    hotkey_listener = GlobalHotKeys(hotkeys_to_listen)
    hotkey_listener.start()

    # The main part of this thread will now block here until the main program
    # sets the stop_event, indicating it's time to shut down.
    stop_event.wait()

    # Stop the listener thread when the program is exiting.
    hotkey_listener.stop()
