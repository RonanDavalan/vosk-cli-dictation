% VOSK-CLI-DICTATION-TRAY(1) vosk-cli-dictation | User Commands
% Ronan Davalan
% 2026-11-12

# NAME

vosk-cli-dictation-tray - notification-area microphone icon for vosk-cli-dictation

# SYNOPSIS

**vosk-cli-dictation-tray** [**\--socket** *PATH*] [**\--dictation-command** *COMMAND*]

**vosk-cli-dictation-tray** **\--version**

# DESCRIPTION

**vosk-cli-dictation-tray** shows a microphone in the desktop notification area (KDE Plasma natively; GNOME with the
"AppIndicator and KStatusNotifierItem Support" extension) and drives a running **vosk-cli-dictation** session through its control
socket. It is a separate program: the dictation never needs it, and it needs only the socket. It asks the session for `info` four
times a second; an absent socket means that no dictation is running. Menu labels follow the language of the running dictation, or the
language of the session when none runs, from the same gettext catalogs as the dictation.

Without a notification area, it shows one desktop notification explaining how to enable one and keeps running, so the icon appears if
the area comes up later. Only one icon runs per socket.

# OPTIONS

**\--socket** *PATH*
:   Control socket to drive. Default: `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock`, the one of the user's own dictation.

**\--dictation-command** *COMMAND*
:   Command that launches the dictation, split like a shell command line. Default: the environment variable
    `VOSK_CLI_DICTATION_COMMAND`, then **vosk-cli-dictation** from the `PATH`, then the Git checkout's own copy.

**\--version**
:   Print the version and exit.

# STATES

Colour and shape give the state, so the icon stays readable for colour-blind users.

red microphone with sound waves
:   `DICTÉE`: the microphone is open and the voice is typed.

orange microphone
:   `ÉCOUTE`: the microphone is open, dictation is off, the wake phrase is awaited.

blue microphone under a crescent moon
:   `VEILLE`: the microphone is released.

green outlined microphone
:   No dictation is running.

A left click launches the dictation when none runs, and toggles it otherwise. The tooltip repeats the status line and says "Loading
model…" while a model loads.

# MENU

The right-click menu, in this order:

1.  a status line: state, language, engine;
2.  turn dictation on or off; enter or leave deep sleep; finish and copy the text; cancel the session;
3.  **Language**: follow the system, or French, English, German, Spanish; a language without an installed model reads "to download";
4.  **Model**: light or full; a missing model shows its size, and choosing it starts its download, with a notification when it ends;
5.  **Refinement** and **Correction**: greyed with their reason until the running dictation announces options;
6.  revert to the configuration (forget the remembered choice);
7.  launch or quit the dictation (launched detached from any terminal); launch the icon at login; quit the icon.

While a model loads, the choices that change it are greyed.

# FILES

`~/.local/state/vosk-cli-dictation/instance.log`
:   Output of the dictation launched from the icon, and of the model downloads it starts.

`~/.config/autostart/vosk-cli-dictation-tray.desktop`
:   The XDG Autostart entry that "Launch the icon at login" writes (`Hidden=true` when unchecked).

`$XDG_RUNTIME_DIR/vosk-cli-dictation.sock`
:   The control socket of the dictation.

# SEE ALSO

**vosk-cli-dictation**(1)

# BUGS

Report bugs on the project's issue tracker:
*https://github.com/RonanDavalan/vosk-cli-dictation/issues*

# AUTHOR

Ronan Davalan, and contributors listed in CONTRIBUTORS.md.
