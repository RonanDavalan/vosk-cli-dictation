% VOSK-CLI-DICTATION(1) vosk-cli-dictation | User Commands
% Ronan Davalan
% 2026-08-26

# NAME

vosk-cli-dictation - offline, system-wide voice dictation for the command line

# SYNOPSIS

**vosk-cli-dictation** [**-l** *LANG* | **\--lang** *LANG*]

# DESCRIPTION

**vosk-cli-dictation** is a command-line dictation tool for Linux, powered by
the offline Vosk speech recognition engine. It listens continuously through
the microphone and types the recognized text directly into whichever
application currently holds keyboard focus (terminal, browser, editor, or
any other window), so it can be used system-wide rather than inside a
single program.

All speech recognition runs locally: no audio or transcribed text is ever
sent to a remote service.

Dictation is started and stopped either by voice (a configurable wake word
and stop word) or by global hotkeys, and can additionally be put to sleep
to fully suspend audio capture and recognition when not needed, without
quitting the program.

Text simulation is performed through **ydotool**, when available, or
**xdotool** as a fallback. **ydotool** supports both Wayland and X11 through
the `/dev/uinput` interface; **xdotool** supports X11 only (or Wayland
through XWayland). At least one of the two must be installed.

# OPTIONS

**-l** *LANG*, **\--lang** *LANG*
:   Force the interface and speech recognition language for this session
    (for example `en` or `fr`), overriding the `default_model` value from
    the configuration file. *LANG* must match the name of one of the
    models declared under `vosk_models` in the configuration file.

# VOICE COMMANDS

The wake word and stop word are configurable per language. With the
factory configuration:

English
:   Say **"start"** to begin dictating, **"oops"** to stop and copy the
    result to the clipboard.

French
:   Say **"démarre"** to begin dictating, **"zut"** to stop and copy the
    result to the clipboard.

Punctuation and layout words (comma, period, new line, and so on) are
dictated by voice as well; the full, per-language list is defined under
`language_settings.<lang>.punctuation` in the configuration file, and is
printed by the program itself at startup.

# HOTKEYS

Global hotkeys work regardless of which window currently has focus. The
factory configuration defines:

**Alt+H**
:   Toggle dictation on or off (equivalent to the wake/stop words). While
    paused, the microphone stays active and the voice wake word still
    works.

**Alt+S**
:   Stop the current dictation and copy the accumulated text to the
    clipboard.

**Alt+W**
:   Toggle sleep mode, a third state distinct from the two above. In sleep
    mode, audio capture and speech recognition are fully suspended - CPU
    usage drops to near zero - but the voice wake word cannot be heard
    until sleep mode is toggled off again. The **Alt+W** hotkey itself
    keeps working while asleep, since it does not depend on audio.
    Triggering sleep mode while a dictation is in progress stops it
    cleanly first, so no audio is lost mid-sentence.

**Ctrl+C**
:   Quit the program.

All three hotkeys are configurable under the `hotkeys` section of the
configuration file.

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
