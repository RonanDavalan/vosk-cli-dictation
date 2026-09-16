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
        from pynput.keyboard import GlobalHotKeys, Key, KeyCode, Listener
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

    # Chantier 11, D2 : mode push-to-talk. GlobalHotKeys ne rend jamais le
    # relâchement d'une touche ; un Listener bas niveau dédié le fait, actif
    # seulement si interaction.mode == 'maintenue'. Cohabite avec le hotkey de
    # bascule ci-dessus (aucune fonctionnalité existante retirée, D6).
    ptt_listener = None
    if config.interaction_mode == 'maintenue':
        key_name = config.hotkeys.get('push_to_talk')
        target_key = _parse_single_key(key_name, Key, KeyCode) if key_name else None
        if target_key is None:
            warning = _('interaction.mode is "maintenue" but hotkeys.push_to_talk is missing or invalid; push-to-talk disabled.')
            print(f"{config.color_warning}{warning}{config.RESET}")
        else:
            pressed = [False]  # garde anti-répétition tant que la touche reste enfoncée

            def on_press(key):
                if key == target_key and not pressed[0]:
                    pressed[0] = True
                    submit('DICTATION_ON')

            def on_release(key):
                if key == target_key and pressed[0]:
                    pressed[0] = False
                    submit('FINALIZE_SESSION')

            try:
                ptt_listener = Listener(on_press=on_press, on_release=on_release)
                ptt_listener.start()
            except Exception as exc:
                ptt_listener = None
                print(f"{config.color_warning}"
                      f"{_('Push-to-talk listener could not start:')} {exc}"
                      f"{config.RESET}")

    # The main part of this thread will now block here until the main program
    # sets the stop_event, indicating it's time to shut down.
    stop_event.wait()

    # Stop the listener thread(s) when the program is exiting.
    hotkey_listener.stop()
    if ptt_listener is not None:
        ptt_listener.stop()


def _parse_single_key(name: str, Key, KeyCode):
    """Resolves a single-key config name (e.g. ``ctrl_r``, ``f9``, ``a``) to a
    pynput key object, for the push-to-talk listener (D2). Special keys are
    named after ``pynput.keyboard.Key`` members; anything else is treated as a
    single printable character. Returns None if the name is not a valid key."""
    try:
        return getattr(Key, name)
    except AttributeError:
        pass
    if isinstance(name, str) and len(name) == 1:
        return KeyCode.from_char(name)
    return None
