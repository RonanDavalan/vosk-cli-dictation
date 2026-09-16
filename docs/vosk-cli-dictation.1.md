% VOSK-CLI-DICTATION(1) vosk-cli-dictation | User Commands
% Ronan Davalan
% 2026-09-10

# NAME

vosk-cli-dictation - offline, system-wide voice dictation for the command line

# SYNOPSIS

**vosk-cli-dictation** [**-l** *LANG* | **\--lang** *LANG*]

**vosk-cli-dictation** **\--diagnose**

**vosk-cli-dictation** **\--download-model** [*LANG*]

**vosk-cli-dictation** {**\--status** | **\--toggle** | **\--dictation-on** | **\--dictation-off** | **\--finalize** | **\--cancel** | **\--sleep** | **\--wake** | **\--sleep-toggle** | **\--stop**}

# DESCRIPTION

**vosk-cli-dictation** is a command-line dictation tool for Linux, powered by
the offline Vosk speech recognition engine. It listens continuously through
the microphone and types the recognized text directly into whichever
application currently holds keyboard focus (terminal, browser, editor, or
any other window), so it can be used system-wide rather than inside a
single program.

All speech recognition runs locally: no audio or transcribed text is ever
sent to a remote service.

Dictation is started and stopped either by voice (a configurable two-word
wake phrase and stop phrase, per language) or through control subcommands
that can be bound to a desktop keyboard shortcut, and can additionally be
put to sleep to fully release the microphone and suspend recognition when
not needed, without quitting the program.

Only one session runs per user at a time. It opens a private Unix socket at
`$XDG_RUNTIME_DIR/vosk-cli-dictation.sock` (mode `0600`); the same command
invoked with a control flag (see CONTROLLING A RUNNING SESSION) connects to
that socket instead of starting a new session.

Text is injected by placing it on the clipboard and simulating a paste, so
two kinds of tool are needed: a keystroke simulator and a clipboard tool.
Under Wayland this is **wtype** plus **wl-clipboard**; if **wtype** is
missing the keystroke falls back to **ydotool** (which needs the
`ydotoold` daemon and access to `/dev/uinput`), but **wl-clipboard** is
still required. Under X11 it is **xdotool** plus **xclip**. The Debian
package depends on **wl-clipboard** and recommends **xclip**; a Git
checkout must install them itself. Without a clipboard tool the dictated
text never reaches the clipboard and the paste re-inserts whatever was
last copied by hand. Adding your user to the `input` group is required
only for the **ydotool** fallback; **wtype** and **xdotool** do not need
it. **vosk-cli-dictation \--diagnose** reports which tools, audio device
and clipboard access are present, then exits.

Global hotkeys via `pynput` watch the X server: under Wayland they reach
only windows running through XWayland, never a focused native-Wayland
window. Bind the control subcommands to your desktop's own shortcut
settings for control that works everywhere.

# OPTIONS

**-l** *LANG*, **\--lang** *LANG*
:   Force the interface and speech recognition language for this session
    (`en`, `fr`, `de` or `es`), overriding the `default_model` value from
    the configuration file. *LANG* must match the name of one of the
    models declared under `vosk_models` in the configuration file.

**\--diagnose**
:   Check the environment (session type, injection backend, tools, models,
    audio input, clipboard, control socket) and exit. Exit status is `0`
    when every check passes.

**\--download-model** [*LANG*]
:   Download the small Vosk model for *LANG* (or the current language when
    omitted) into `~/.local/share/vosk-models/`, verifying its checksum,
    then exit. A model is also offered interactively on the first run when
    none is installed.

# CONTROLLING A RUNNING SESSION

Each of the following flags connects to the socket of the running session,
performs the action, prints the resulting state (`OK DICTÉE`,
`OK ÉCOUTE`, `OK VEILLE`) or `ERR <reason>`, and exits. They are meant to
be bound to desktop keyboard shortcuts.

**\--status**
:   Print the current state without changing it.

**\--toggle**
:   Toggle dictation between DICTÉE and ÉCOUTE.

**\--dictation-on**, **\--dictation-off**
:   Force dictation on or off.

**\--finalize**
:   Stop the dictation and copy the accumulated text — equivalent to the
    stop phrase.

**\--cancel**
:   Discard the current session buffer without typing anything.

**\--sleep**, **\--wake**, **\--sleep-toggle**
:   Enter, leave, or toggle sleep mode (VEILLE).

**\--stop**
:   Shut the running session down cleanly.

# VOICE COMMANDS

The wake phrase and stop phrase are two words each, configurable per
language under `language_settings.<lang>.voice_commands`. Two words rather
than one so an ordinary sentence never triggers them. With the factory
configuration:

English
:   Say **"start dictation"** to begin, **"stop dictation"** to finish and
    copy the result to the clipboard.

French
:   **"active dictée"** / **"stop dictée"**.

German
:   **"diktat starten"** / **"diktat stoppen"**.

Spanish
:   **"iniciar dictado"** / **"terminar dictado"**.

A trigger phrase is only acted on when the average recognition confidence
of its words clears `recognition.confidence_threshold` (default `0.55`,
overridable per language). A stop phrase heard below the threshold is
swallowed — neither acted on nor typed into the document — and a hint is
printed; repeat it, or use `--finalize`. While dictating, a second
lightweight recogniser restricted to the stop phrase provides a
high-confidence stop independent of that threshold
(`recognition.restricted_stop_in_dictation`, on by default, overridable per
language). Saying a phrase twice in immediate succession types it literally
rather than triggering.

Punctuation and layout words (comma, period, new line, and so on) are
dictated by voice as well; the full, per-language list is defined under
`language_settings.<lang>.punctuation` in the configuration file, and is
printed by the program itself at startup.

# TRIGGER MODES

`interaction.mode` in the configuration file selects how a dictation session
starts and stops. Default `toggle`, unchanged from earlier releases: one
gesture starts, a separate gesture stops (voice phrase, hotkey, or control
subcommand). Two other modes:

**maintenue**
:   Push-to-talk. The dictation lasts exactly as long as the key configured
    under `hotkeys.push_to_talk` (default `Ctrl_R`, a single key, not a
    chord) is held down. Best-effort X11/XWayland, like the hotkeys below;
    under native Wayland, bind a shortcut tool able to tell key-down from
    key-up (`sway bindsym --release`, `xbindkeys`) to
    **\--dictation-on** / **\--finalize** instead.

**silence**
:   A single press (or the wake phrase) starts the session; it stops and
    copies itself once `interaction.silence_timeout_ms` (default `700`,
    overridable per language) passes with no decoder output, as soon as at
    least one word has been captured — a hesitation before speaking never
    finalizes an empty session.

In every mode, the spoken stop phrase and **\--finalize** / **\--cancel**
keep working as a safety net.

# HOTKEYS

`pynput` global hotkeys are started whenever an X server is reachable and
`hotkeys.pynput_enabled` is true. `pynput` watches the X server, so under
Wayland the hotkeys reach only windows running through XWayland (many
Electron and legacy apps), never a focused native-Wayland window; the
control subcommands bound to a desktop shortcut cover every window. The
`pynput` listener also does not consume the key event: the combination also
reaches the focused window, so pressing it while the cursor is in a
terminal inserts an escape sequence (for example `^[s` for **Alt+S**). For
a clean stop from any window, bind **\--finalize** (or **\--toggle**,
**\--sleep-toggle**) to a desktop keyboard shortcut instead. The factory
configuration defines:

**Alt+H**
:   Toggle dictation on or off. This only pauses or resumes; it does **not**
    copy anything to the clipboard, unlike **Alt+S** and the stop phrase.
    While paused, the microphone stays active and the wake phrase still
    works.

**Alt+S**
:   Stop the current dictation and copy the accumulated text to the
    clipboard — equivalent to the stop phrase. The chord also leaks into
    the focused window (see above) and misses native-Wayland windows;
    prefer **\--finalize** bound to a desktop shortcut.

**Alt+W**
:   Toggle sleep mode, a third state distinct from the two above. In sleep
    mode the audio stream is closed (the microphone is released) and
    recognition is blocked, so CPU use drops to near zero; the wake phrase
    cannot be heard until sleep mode is toggled off. **Alt+W** itself keeps
    working while asleep, since it does not depend on audio. Triggering
    sleep mode during a dictation stops it cleanly first, so no audio is
    lost mid-sentence.

**Ctrl+C**
:   Quit the program.

The first three hotkeys are configurable under the `hotkeys` section of the
configuration file. **Ctrl+C** is not: it is the standard interrupt signal, always active,
never remapped through configuration.

`hotkeys.push_to_talk` (default `ctrl_r`) is a fourth, single-key entry used
only when `interaction.mode` is `maintenue` — see TRIGGER MODES above.

# MANUAL COMMANDS

While the program is running, typing one of the following commands in its
terminal window and pressing Enter also controls it:

**/cancel**
:   Stop the current recording session without outputting any text.

**/delete-word**
:   Delete the last word that was typed.

**/nl**
:   Insert a new line (simulates pressing the Enter key).

# CONFIGURATION

Runtime behavior is controlled by a YAML configuration file: available
speech models, audio parameters, recognition confidence threshold,
per-language voice commands and punctuation, hotkeys, notification sound,
and console color theme.

The configuration file is located by the first matching rule below; once a
rule matches, the remaining rules are not consulted.

1. The path given in the **VOSK_CONFIG** environment variable, if set. Used
   as-is; never created automatically.
2. `config/config.yaml`, relative to the project directory, when running
   from a Git checkout (development mode).
3. `$XDG_CONFIG_HOME/vosk-cli-dictation/config.yaml` (default
   `~/.config/vosk-cli-dictation/config.yaml`). Created automatically on
   first run, from the factory template, when installed from the Debian
   package.
4. The factory template shipped by the package, read-only.

The active language is chosen, in order: the **\--lang** option, if given;
otherwise the operating system's detected language; otherwise the
`default_model` value from the configuration file.

See **configuration.md** in the project documentation for the full
reference of every configuration key.

# FILES

`~/.config/vosk-cli-dictation/config.yaml`
:   Per-user configuration file (Debian package install).

`/usr/share/vosk-cli-dictation/config.yaml`
:   Factory configuration template (Debian package install), read-only.

`~/.local/share/vosk-models/`
:   Default location searched for Vosk acoustic models (Debian package
    install).

`config/config.yaml`
:   Configuration file used when running from a Git checkout.

`vosk-model/`
:   Default location searched for Vosk acoustic models when running from
    a Git checkout.

`$XDG_RUNTIME_DIR/vosk-cli-dictation.sock`
:   Control socket of the running session (mode `0600`). Removed on a clean
    exit; a stale socket left by a crash is detected and replaced at the
    next start.

# EXIT STATUS

**0**
:   The program exited cleanly, including after **Ctrl+C**.

Non-zero
:   Startup failed: neither **ydotool** nor **xdotool** is available, no
    speech recognition model could be loaded, or the audio device could
    not be opened.

# EXAMPLES

Start with the default language from the configuration file:

```
vosk-cli-dictation
```

Force English for this session:

```
vosk-cli-dictation --lang en
```

# SEE ALSO

Vosk models and downloads: *https://alphacephei.com/vosk/models*

Project homepage: *https://vosk.davalan.fr/*

# BUGS

Report bugs on the project's issue tracker:
*https://github.com/RonanDavalan/vosk-cli-dictation/issues*

# AUTHOR

Ronan Davalan, and contributors listed in CONTRIBUTORS.md.
