# src/keyboard_listener.py

import os
import queue
import textwrap
from config.config import config
from src.i18n import get_translation


def _notice(text: str, color=None) -> None:
    """Affiche un avis d'un paragraphe, enrobé à 76 colonnes."""
    colour = config.color_info if color is None else color
    print(f"{colour}{textwrap.fill(text, width=76)}{config.RESET}")


def keyboard_listener_thread(control_queue: queue.Queue, stop_event):
    """
    Écoute des raccourcis globaux via pynput.

    Sous Linux, pynput observe le serveur X. Dans une session Wayland, un
    serveur XWayland est presque toujours présent et relaie les touches des
    fenêtres qui y transitent (la plupart des applis Electron et X11
    historiques), jamais celles d'une surface Wayland native focalisée.
    L'écoute est donc un confort best-effort qui démarre dès qu'un serveur X
    est joignable, quel que soit le type de session ; la voie de contrôle
    universelle reste la socket Unix et ses sous-commandes CLI (--toggle /
    --finalize / --sleep-toggle / --status).

    Le garde qui limitait l'écoute aux sessions X11 est retiré : il écartait
    le cas XWayland qui fonctionnait déjà. `hotkeys.pynput_enabled: false`
    coupe toujours l'écoute, désormais sur tout type de session.
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
        """Pousse une commande de contrôle sans jamais bloquer le rappel pynput.

        La file de contrôle est bornée ; une file pleine signifie que le
        thread UI est bloqué. Le signaler bruyamment plutôt que geler
        l'écoute ou jeter la commande en silence.
        """
        try:
            control_queue.put_nowait(command)
        except queue.Full:
            print(f"\n{config.color_error}"
                  f"{_('Control queue full; the UI thread is not responding.')}"
                  f"{config.RESET}")

    def on_toggle():
        """Rappel du raccourci de bascule d'enregistrement."""
        submit('TOGGLE_RECORDING')

    def on_finalize():
        """Rappel du raccourci de finalisation de session."""
        submit('FINALIZE_SESSION')

    def on_sleep_toggle():
        """Rappel du raccourci de bascule de veille."""
        submit('TOGGLE_SLEEP')

    # Associe les noms d'actions du fichier de configuration à leurs rappels.
    actions = {
        'toggle_recording': on_toggle,
        'finalize_session': on_finalize,
        'sleep_toggle': on_sleep_toggle,
    }

    def format_hotkey_string(keys: list) -> str:
        """
        Formate une liste de noms de touches en chaîne lisible par pynput.
        Exemple : ['alt_l', 'h'] -> '<alt_l>+h'
        """
        # Un nom de touche est "spécial" s'il fait plus d'un caractère.
        # Ceux-là s'enveloppent dans des chevrons.
        formatted_keys = [f'<{k}>' if len(k) > 1 else k for k in keys]
        return "+".join(formatted_keys)

    # Construit dynamiquement le dictionnaire des raccourcis pour l'écoute.
    # Le format exigé par GlobalHotKeys est {'<combo_touches>': fonction_rappel}
    hotkeys_to_listen = {}
    for action, hotkey_config in config.hotkeys.items():
        if action in actions:
            try:
                # pynput_keys est une liste venue de la config, p. ex. ['alt_l', 'h']
                pynput_keys = hotkey_config.get('pynput_keys', [])
                if pynput_keys:
                    hotkey_string = format_hotkey_string(pynput_keys)
                    hotkeys_to_listen[hotkey_string] = actions[action]
            except (TypeError, KeyError, AttributeError) as e:
                # Couvre les cas de configuration malformée.
                print(f"{config.color_error}Could not create hotkey for action '{action}': {e}{config.RESET}")

    if not hotkeys_to_listen:
        print(f"{config.color_warning}No valid hotkeys found in configuration. Keyboard listener will not run.{config.RESET}")
        return

    # Crée et lance l'écoute avec les raccourcis définis.
    # GlobalHotKeys tourne dans son propre thread.
    try:
        hotkey_listener = GlobalHotKeys(hotkeys_to_listen)
        hotkey_listener.start()
    except Exception as exc:
        _notice(_('Global hotkeys via pynput are not available on this session; use the CLI subcommands bound to your desktop shortcuts.'), color=config.color_error)
        print(f"{config.color_info}  ({exc}){config.RESET}")
        stop_event.wait()
        return

    # Mode appui-pour-parler : GlobalHotKeys ne rend jamais le relâchement
    # d'une touche ; un Listener bas niveau dédié le fait, actif seulement si
    # interaction.mode == 'maintenue'. Cohabite avec le raccourci de bascule
    # ci-dessus (aucune fonctionnalité existante retirée).
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

    # Le corps de ce thread bloque ici jusqu'à ce que le programme principal
    # pose stop_event pour demander l'arrêt.
    stop_event.wait()

    # Arrête le ou les threads d'écoute à la sortie du programme.
    hotkey_listener.stop()
    if ptt_listener is not None:
        ptt_listener.stop()


def _parse_single_key(name: str, Key, KeyCode):
    """Résout un nom de touche de configuration (p. ex. ``ctrl_r``, ``f9``,
    ``a``) en objet touche pynput pour l'écoute appui-pour-parler. Les
    touches spéciales portent le nom des membres de ``pynput.keyboard.Key`` ;
    tout le reste est traité comme un caractère imprimable unique. Retourne
    None si le nom n'est pas une touche valide."""
    try:
        return getattr(Key, name)
    except AttributeError:
        pass
    if isinstance(name, str) and len(name) == 1:
        return KeyCode.from_char(name)
    return None
