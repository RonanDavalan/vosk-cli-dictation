# Project Configuration Guide

This document provides a detailed explanation of all available options in the `config/config.yaml` file. Properly configuring this file is key to tailoring the application to your specific needs, language, and hardware.

## How Language is Determined

The application chooses which language to use based on this priority order:

1.  **Command-Line Argument (Highest Priority):** Using the `-l` or `--lang` flag (e.g., `python src/main.py -l en`) will always override all other settings.

2.  **System Language (Automatic Detection):** If no flag is provided, the application automatically detects your operating system's language.

3.  **`default_model` Setting (Fallback):** If your system's language cannot be determined, the application will use the model specified in the `default_model` setting as a final fallback.

## General Structure of `config.yaml`

The configuration file is organized into logical sections:

```yaml
# Example of the main sections
vosk_models: [...]
default_model: "..."
control_socket: true
audio: [...]
recognition: [...]
sleep: [...]
clipboard: [...]
injection: [...]
language_settings: [...]
hotkeys: [...]
sound_file: "..."
theme: [...]
```

## Configuration Sections in Detail

### `vosk_models`

A list that defines the available Vosk speech recognition models.

-   **`name`** (string): A unique, short name for the model (e.g., `fr`, `en`).
-   **`path_relative`** (string): The relative path to the unzipped Vosk model folder. Resolved
    against, in order, `$XDG_DATA_HOME/vosk-models/` (default `~/.local/share/vosk-models/`),
    `/usr/share/vosk-models/`, then the project root when running from a Git checkout — the
    first of these that actually contains the folder wins. Can also be given as an absolute
    path, which always takes priority. See the manpage, CONFIGURATION section, for the full
    cascade.

```yaml
vosk_models:
  - name: "en"
    path_relative: "vosk-model/vosk-model-small-en-us-0.15"
  - name: "fr"
    path_relative: "vosk-model/vosk-model-small-fr-0.22"
  - name: "de"
    path_relative: "vosk-model/vosk-model-small-de-0.15"
  - name: "es"
    path_relative: "vosk-model/vosk-model-small-es-0.42"
```

A model that is declared but not present on disk is reported at startup and skipped; startup only fails if no model at all can be loaded.

### `default_model`

The name of the Vosk model to load at startup. Must match a `name` in the `vosk_models` list.

```yaml
default_model: "en"
```

### `control_socket`

Boolean, default `true`. When enabled, the running session listens on a Unix socket at `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock` (mode `0600`) so the control subcommands (`--toggle`, `--sleep-toggle`, `--status`, `--stop`, …) can drive it. Set to `false` to disable the socket entirely; the tool then remains usable interactively but cannot be controlled from a bound shortcut.

```yaml
control_socket: true
```

### `audio`

Parameters for your microphone.

-   **`sample_rate`** (integer): The sample rate your model was trained on (usually `16000`).
-   **`channels`** (integer): Number of audio channels (should be `1` for mono).
-   **`frames_per_buffer`** (integer): `2048` or `4096` are common values.
-   **`buffer_size`** (integer): The size of the audio buffer.
-   **`queue_max_chunks`** (integer): Maximum depth of the audio queue, in `buffer_size` chunks (`16` ≈ 2 s). When recognition falls behind, the oldest chunk is dropped rather than letting latency drift; an overflow counter is surfaced in `--status` and `--diagnose`.

```yaml
audio:
  sample_rate: 16000
  channels: 1
  frames_per_buffer: 4096
  buffer_size: 2048
  queue_max_chunks: 16
```

### `recognition`

Parameters for the Vosk recognition engine.

-   **`confidence_threshold`** (float, 0.0-1.0, default `0.55`): a voice trigger phrase (wake or stop) is only acted on when the average confidence of its words reaches this value. Below it, a wake phrase is treated as ordinary text; a **stop** phrase is swallowed — neither acted on nor typed into the document — and a hint is printed. Can be overridden per language with a key of the same name under `language_settings.<lang>`.
-   **`restricted_grammar_in_listening`** (boolean, default `true`): while listening for the wake phrase, decode with a Kaldi grammar restricted to that phrase. CPU at rest drops sharply for most models, at the cost of rebuilding the full recognizer on wake. Set to `false` to keep the full recognizer running in the listening state. Can be overridden per language with a key of the same name under `language_settings.<lang>` — the factory config disables it for `es`, where the small model decodes the restricted grammar more slowly than the full one.
-   **`restricted_stop_in_dictation`** (boolean, default `true`): while dictating, run a second lightweight recognizer restricted to the stop phrase, alongside the full one. It provides a high-confidence stop signal independent of `confidence_threshold` — the same mechanism used for the wake phrase while listening. Overridable per language under `language_settings.<lang>`; set to `false` on hardware where the extra restricted decode per audio block is too costly (it is roughly 5× cheaper than the full decode).

```yaml
recognition:
  confidence_threshold: 0.55
  restricted_grammar_in_listening: true
  restricted_stop_in_dictation: true
```

### `sleep`

-   **`releases_device`** (boolean, default `true`): in sleep mode, close the audio stream so the microphone is fully released (its LED goes off) and another program can use it; reopening on wake takes about 200 ms. Set to `false` to only stop the stream without closing it — the device stays claimed but wake is marginally faster.

```yaml
sleep:
  releases_device: true
```

### `clipboard`

Text is injected by placing it on the clipboard and simulating a paste.

-   **`restore`** (boolean, default `true`): put the user's previous clipboard content back after pasting. A non-text clipboard (an image, for instance) is never saved or overwritten. Can also be disabled per run with `--no-clipboard-restore`.
-   **`restore_delay_ms`** (integer, default `250`): delay before restoring, to let the target application read the paste.
-   **`confirm_timeout_ms`** (integer, default `500`): maximum time to wait for confirmation that the clipboard actually holds our text before sending the paste keystroke.

```yaml
clipboard:
  restore: true
  restore_delay_ms: 250
  confirm_timeout_ms: 500
```

### `injection`

-   **`paste_combo`** (string, default `ctrl+v`) and **`terminal_paste_combo`** (default `ctrl+shift+v`): the key combination used to paste. Under X11 the window class of the focused window is checked against `terminal_window_classes` to pick the right one automatically; under Wayland there is no focused-window API, so `paste_combo` is used unless you override it.
-   **`terminal_window_classes`** (list): window classes treated as terminals (X11 only).
-   **`ydotool_keycodes`** (mapping): physical Linux keycodes, used only on the `ydotool` fallback path. Override these under a non-QWERTY layout if that fallback is actually in use; the nominal Wayland path (`wtype`) works by keysym and is layout-independent.

```yaml
injection:
  paste_combo: "ctrl+v"
  terminal_paste_combo: "ctrl+shift+v"
  terminal_window_classes: ["konsole", "gnome-terminal-server", "xterm", "st", "alacritty", "kitty", "foot"]
  ydotool_keycodes: {}
```

### `language_settings`

This section contains settings that are specific to a language. The factory
configuration ships four: `en`, `fr`, `de`, `es`.

-   **`voice_commands`**: the two-word `wake_phrase` and `stop_phrase` for this language. Two words so an ordinary sentence never triggers them. (The former single-word `start_word` / `stop_word` keys are still read if present, for backward compatibility.)
-   **`punctuation`**: A dictionary to automatically insert punctuation, organized into logical groups. Spanish `¿` and `¡` are inserted only by explicit commands (`"abrir interrogación"`, `"abrir exclamación"`), never automatically. Two optional keys, set per language under `language_settings.<lang>.punctuation`, control the recognition mode: **`mode`** (`"inline"` by default, or `"explicit"`) and **`trigger`** (the word that gates punctuation in `explicit` mode, e.g. `"ponctuation"` for French, `"punctuation"` for English). In `explicit` mode a punctuation command is only converted when the `trigger` immediately precedes it — the trigger is then consumed and never typed; otherwise the words are typed literally (`"ponctuation virgule"` → `,`, but a bare `"virgule"` stays a word). The trigger word is only consumed when a known command follows it, so it can still be dictated as an ordinary word elsewhere. Use `explicit` when you dictate prose that mentions punctuation by name; keep `inline` for fast formal dictation.
-   **`typography`**: per-language output rules — see below.
-   **`recognition_aliases`**: Corrects common recognition errors from Vosk. The shipped table holds only generic, uncontroversial fixes (e.g. `"de points": "deux points"`); corpus-specific corrections live in `config/config.example.yaml`, to copy and adapt.
-   **`custom_vocabulary`**: A dictionary for case-sensitive corrections, applied after aliases (e.g., `"ia": "IA"`).

#### Per-language overrides of `recognition.*`

Any of these keys, normally set once under the global `recognition` block, can
be overridden for a single language by repeating it under
`language_settings.<lang>` — the per-language value wins. The factory config
uses this for `es` (`restricted_grammar_in_listening: false`).

| key | effect when overridden per language |
|---|---|
| `confidence_threshold` | trigger-phrase confidence gate for that language |
| `restricted_grammar_in_listening` | restricted-grammar decoding while listening |
| `restricted_stop_in_dictation` | experimental second stop recogniser while dictating |
| `wake_discard_ms` | audio discarded right after a wake, to drop a stray word |

```yaml
language_settings:
  es:
    restricted_grammar_in_listening: false   # per-language override
    confidence_threshold: 0.5                 # per-language override
    voice_commands: [...]
```

```yaml
language_settings:
  fr: # Settings for French
    voice_commands:
      wake_phrase: "active dictée"
      stop_phrase: "stop dictée"
    punctuation:
      mode: inline
      trigger: ponctuation
      simple:
        "virgule": ","
      double:
        "point d'exclamation": "!"
      layout:
        "nouvelle ligne": "\n"
      special:
        "ouvrez la parenthèse": "("
    typography:
      thin_space: true
      space_before: ["?", "!", ":", ";", "»"]
      space_after: [",", ".", ";", ":", "?", "!"]
      capitalize_sentence_start: true
      quote_open: "« "
      quote_close: "»"
    recognition_aliases:
      "de points": "deux points"
    custom_vocabulary:
      "ia": "IA"
```

#### `typography`

Replaces what used to be a hard-coded French branch. Per language:

-   **`thin_space`** (boolean): insert a narrow no-break space (U+202F) before the symbols listed in `space_before`. `true` for French, `false` elsewhere. Disable it if the thin space breaks `grep` or your terminal.
-   **`space_before`** (list): symbols that take a leading separator (a thin space when `thin_space`, otherwise a plain space). Empty for English, German and Spanish.
-   **`space_after`** (list): symbols followed by a space.
-   **`capitalize_sentence_start`** (boolean): capitalize the first word of each sentence. German capitalizes only sentence starts — common nouns are left as recognized, since reliable noun capitalization would need a morphological analyzer.
-   **`quote_open`** / **`quote_close`**: opening and closing quotation marks (`« »` for French, `„ "` for German).


### `hotkeys`

Global keyboard shortcuts via `pynput`. These are only started under a plain
X11 session, and even there the `pynput` listener does not consume the key
event: the combination also reaches the focused window, so pressing it while
the cursor is in a terminal inserts an escape sequence (`^[s` for `Alt+S`).
For a clean stop from any window — and for native Wayland, where `pynput`
sees nothing — bind the control subcommands (`--toggle`, `--finalize`,
`--sleep-toggle`) to your desktop's own shortcut settings instead.

-   **`pynput_enabled`** (boolean, default `true`): honoured only under X11. Set to `false` to never start the `pynput` listener.
-   **`pynput_keys`**: A list of Pynput keys for the shortcut.
-   **`display_name`**: A string shown in the help message.

```yaml
hotkeys:
  pynput_enabled: true
  toggle_recording:
    pynput_keys: ["alt_l", "h"]
    display_name: "[Alt+H]"
  finalize_session:
    pynput_keys: ["alt_l", "s"]
    display_name: "[Alt+S]"
  sleep_toggle:
    pynput_keys: ["alt_l", "w"]
    display_name: "[Alt+W]"
```

-   **`toggle_recording`** (default `Alt+H`): starts or pauses the current dictation. While
    paused, the microphone stays active and the voice wake phrase still works.
-   **`finalize_session`** (default `Alt+S`): stops the dictation and copies the accumulated
    text to the clipboard. X11 only, and the chord leaks into the focused window (see above) —
    prefer `vosk-cli-dictation --finalize` bound to a desktop shortcut.
-   **`sleep_toggle`** (default `Alt+W`): toggles **sleep mode**, a third state distinct from
    the two above. In sleep mode the audio stream is closed (the microphone is released) and
    recognition is blocked, so CPU use drops to near zero — but the wake phrase cannot be
    heard until sleep mode is toggled off again. Only the `Alt+W` hotkey itself keeps working
    while asleep, since it does not depend on audio. Triggering sleep mode while a dictation
    is in progress stops it cleanly first (as if `Alt+H` had been pressed), so no audio is
    lost mid-sentence.

    ```bash
    # How to test / how to run
    cd ~/git/vosk-cli-dictation/vosk-cli-dictation
    source vosk-env/bin/activate
    python3 src/main.py
    # Alt+W toggles sleep mode; Alt+H toggles dictation; Alt+S finalizes and copies.
    ```

### `sound_file`

The absolute path to a notification sound file (e.g., `.oga`, `.wav`).

```yaml
sound_file: "/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga"
```

### `theme`

This section allows you to customize the application's colors in the console. The values must be valid `colorama` color names (e.g., `GREEN`, `RED`, `BLUE`).

-   **`ready_message`**: Color of the "Script is ready" message.
-   **`help_text`**: Main color for the help message block.
-   **`help_title`**: Color for titles within the help message.
-   **`info`**, **`success`**, **`warning`**, **`error`**: Colors for status messages.

```yaml
theme:
  ready_message: "GREEN"
  help_text: "BLUE"
  help_title: "CYAN"
  info: "BLUE"
  success: "GREEN"
  warning: "YELLOW"
  error: "RED"
```
