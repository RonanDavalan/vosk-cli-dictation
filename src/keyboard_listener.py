# src/keyboard_listener.py

import os
import queue
import textwrap
from config.config import config
from src.i18n import get_translation


def _notice(text: str, color=None) -> None:
    """Print a one-paragraph notice, wrapped to 76 columns."""
    colour = config.color_info if color is None else color
    print(f"{colour}{textwrap.fill(text, width=76)}{config.RESET}")


def keyboard_listener_thread(control_queue: queue.Queue, stop_event):
    """
    Global-hotkey listener via pynput.

    pynput on Linux watches the X server. Under a Wayland session an XWayland
    server is almost always present and relays key events for the windows that
    run through it (most Electron and legacy X11 apps), but never for a focused
    native-Wayland surface. The listener is therefore a best-effort convenience
    that starts whenever an X server is reachable, on any session type; the
    universal control path stays the Unix socket and its CLI subcommands
    (--toggle / --finalize / --sleep-toggle / --status).

    v0.5.1-alpha (COMPATIBILITE_WAYLAND.md §5): the earlier
    `XDG_SESSION_TYPE == "x11"` gate is gone -- it dropped the XWayland case
    that already worked in v0.0.4-alpha. `hotkeys.pynput_enabled: false` still
    disables the listener, now on every session type.
    """
    _ = get_translation()

    session = os.environ.get("XDG_SESSION_TYPE", "").lower()

    if not config.hotkeys.get('pynput_enabled', True):
        _notice(_('Global hotkeys via pynput are disabled on this session; use the CLI subcommands bound to your desktop shortcuts.'))
        stop_event.wait()
        return

    if not os.environ.get("DISPLAY"):
        _notice(_('Global hotkeys via pynput are not available on this session; use the CLI subcommands bound to your desktop shortcuts.'))
        stop_event.wait()
        return

    try:
        from pynput.keyboard import GlobalHotKeys
    except Exception as exc:  # ImportError, or an Xlib backend failure at import
        _notice(_('Global hotkeys via pynput are not available on this session; use the CLI subcommands bound to your desktop shortcuts.'))
        print(f"{config.color_info}  ({exc}){config.RESET}")
        stop_event.wait()
        return

    if session != "x11":
        _notice(_('Global hotkeys via pynput only reach windows running through XWayland; bind the CLI subcommands to your desktop shortcuts for native Wayland windows.'))

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
                print(f"{config.color_error}Could not create hotkey for action '{action}': {e}{config.RESET}")

    if not hotkeys_to_listen:
        print(f"{config.color_warning}No valid hotkeys found in configuration. Keyboard listener will not run.{config.RESET}")
        return

    # Create and run the listener with the defined hotkeys.
    # GlobalHotKeys runs in its own thread.
    try:
        hotkey_listener = GlobalHotKeys(hotkeys_to_listen)
        hotkey_listener.start()
    except Exception as exc:
        _notice(_('Global hotkeys via pynput are not available on this session; use the CLI subcommands bound to your desktop shortcuts.'), color=config.color_error)
        print(f"{config.color_info}  ({exc}){config.RESET}")
        stop_event.wait()
        return

    # The main part of this thread will now block here until the main program
    # sets the stop_event, indicating it's time to shut down.
    stop_event.wait()

    # Stop the listener thread when the program is exiting.
    hotkey_listener.stop()
