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
audio: [...]
recognition: [...]
language_settings: [...]
hotkeys: [...]
sound_file: "..."
theme: [...]
```

## Configuration Sections in Detail

### `vosk_models`

A list that defines the available Vosk speech recognition models.

-   **`name`** (string): A unique, short name for the model (e.g., `fr`, `en`).
-   **`path_relative`** (string): The relative path to the unzipped Vosk model folder, from the project root.

```yaml
vosk_models:
  - name: "en"
    path_relative: "vosk-model/vosk-model-small-en-us-0.15"
  - name: "fr"
    path_relative: "vosk-model/vosk-model-small-fr-0.22"
```

### `default_model`

The name of the Vosk model to load at startup. Must match a `name` in the `vosk_models` list.

```yaml
default_model: "en"
```

### `audio`

Parameters for your microphone.

-   **`sample_rate`** (integer): The sample rate your model was trained on (usually `16000`).
-   **`channels`** (integer): Number of audio channels (should be `1` for mono).
-   **`frames_per_buffer`** (integer): `2048` or `4096` are common values.
-   **`buffer_size`** (integer): The size of the audio buffer.

```yaml
audio:
  sample_rate: 16000
  channels: 1
  frames_per_buffer: 4096
  buffer_size: 2048
```

### `recognition`

Parameters for the Vosk recognition engine.

-   **`confidence_threshold`** (float, 0.0-1.0): Words with a confidence score below this value will be ignored.

```yaml
recognition:
  confidence_threshold: 0.85```

### `language_settings`

This section contains settings that are specific to a language.

-   **`voice_commands`**: Keywords to control the application.
-   **`punctuation`**: A dictionary to automatically insert punctuation. It is organized into logical groups for clarity.
-   **`recognition_aliases`**: Corrects common recognition errors from Vosk (e.g., `"sauna": "sonna"`).
-   **`custom_vocabulary`**: A dictionary for case-sensitive corrections, applied after aliases (e.g., `"ia": "IA"`).

```yaml
language_settings:
  fr: # Settings for French
    voice_commands:
      start_word: "démarre"
      stop_word: "zut"
    punctuation:
      simple:
        "virgule": ","
      double:
        "point d'exclamation": "!"
      layout:
        "nouvelle ligne": "\n"
      special:
        "ouvrez la parenthèse": "("
    recognition_aliases:
      "sauna": "sonna"
    custom_vocabulary:
      "ia": "IA"
```


### `hotkeys`

Global keyboard shortcuts to control the application.

-   **`pynput_keys`**: A list of Pynput keys for the shortcut.
-   **`display_name`**: A string shown in the help message.

```yaml
hotkeys:
  toggle_recording:
    pynput_keys: ["alt_l", "h"]
    display_name: "[Alt+H]"
  finalize_session:
    pynput_keys: ["alt_l", "s"]
    display_name: "[Alt+S]"
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
