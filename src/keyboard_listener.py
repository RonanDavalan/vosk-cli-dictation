# src/keyboard_listener.py

import os
import queue
import textwrap
from config.config import config
from src.i18n import get_translation

def keyboard_listener_thread(control_queue: queue.Queue, stop_event):
    """
    Global-hotkey listener via pynput.

    Chantier 7 volet A : pynput n'écoute réellement que sous X11 (sous Wayland
    natif il est aveugle aux fenêtres non-XWayland). Ce thread ne démarre donc
    le listener que si la session est X11 et si `hotkeys.pynput_enabled` n'a pas
    été mis à false. Sinon, le contrôle passe par les sous-commandes CLI liées
    aux raccourcis du bureau (voir --toggle / --sleep / --status).
    """
    _ = get_translation()

    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session != "x11" or not config.hotkeys.get('pynput_enabled', True):
        notice = _('Global hotkeys via pynput are disabled on this session; use the CLI subcommands bound to your desktop shortcuts.')
        print(f"{config.color_info}{textwrap.fill(notice, width=76)}{config.RESET}")
        stop_event.wait()
        return

    from pynput.keyboard import GlobalHotKeys

    def submit(command):
        """Push a control command without ever blocking the pynput callback.

        The queue is bounded (chantier 7 volet C); a full control queue means
        the UI thread is stuck. Surface it loudly rather than freeze the
        listener or drop the command in silence.
        """
        try:
            control_queue.put_nowait(command)
        except queue.Full:
            print(f"\n{config.color_error}"
                  f"{_('Control queue full; the UI thread is not responding.')}"
                  f"{config.RESET}")

    def on_toggle():
        """Callback for the toggle recording hotkey."""
        submit('TOGGLE_RECORDING')

    def on_finalize():
        """Callback for the finalize session hotkey."""
        submit('FINALIZE_SESSION')

    def on_sleep_toggle():
        """Callback for the sleep mode toggle hotkey."""
        submit('TOGGLE_SLEEP')

    # Map action names from the config file to their callback functions.
    actions = {
        'toggle_recording': on_toggle,
        'finalize_session': on_finalize,
        'sleep_toggle': on_sleep_toggle,
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
