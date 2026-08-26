# Projektkonfigurationsanleitung

Dieses Dokument bietet eine detaillierte Erklärung aller verfügbaren Optionen in der `config/config.yaml` Datei. Eine korrekte Konfiguration dieser Datei ist entscheidend, um die Anwendung an Ihre spezifischen Bedürfnisse, Sprache und Hardware anzupassen.

Wie Sprache entsteht.

Die Anwendung wählt die zu verwendende Sprache anhand folgender Prioritätsreihenfolge aus:

1.  **Befehlszeilenargument (höchste Priorität):** Die Verwendung des Flags `-l` oder `--lang` (z. B. `python src/main.py -l en`) überschreibt immer alle anderen Einstellungen.

2. **Systemsprache (Automatische Erkennung):** Wenn kein Sprachparameter angegeben wird, erkennt die Anwendung automatisch die Sprache Ihres Betriebssystems.

3.  **`default_model` Einstellung (Fallback):** Wenn die Sprache Ihres Systems nicht ermittelt werden kann, verwendet die Anwendung das im `default_model` Einstellung angegebene Modell als letzte Möglichkeit.

## Allgemeine Struktur von `config.yaml`

Die Konfigurationsdatei ist in logische Abschnitte unterteilt:

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

## Konfigurationsabschnitte im Detail

### `vosk_models`

Eine Liste, die die verfügbaren Vosk-Spracherkennungsmodelle definiert.

-   **`name`** (String): Ein eindeutiger, kurzer Name für das Modell (z.B. `fr`, `en`).
-   **`path_relative`** (String): Der relative Pfad zum entpackten Vosk-Modellordner, relativ zum Projektstammverzeichnis.

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

Parameter für Ihr Mikrofon.

-   **`sample_rate`** (Integer): Die Samplerate, mit der Ihr Modell trainiert wurde (normalerweise `16000`).
-   **`channels`** (Integer): Anzahl der Audiokanäle (sollte für Mono `1` sein).
-   **`frames_per_buffer`** (Integer): `2048` oder `4096` sind übliche Werte.
-   **`buffer_size`** (Integer): Die Größe des Audio-Puffers.

```yaml
audio:
  sample_rate: 16000
  channels: 1
  frames_per_buffer: 4096
  buffer_size: 2048
```

### `recognition`

Parameter für die Vosk-Spracherkennungs-Engine.

-   **`confidence_threshold`** (float, 0.0-1.0): Wörter mit einem Konfidenzwert unter diesem Wert werden ignoriert.

```yaml
recognition:
  confidence_threshold: 0.85
```

### `language_settings`

Dieser Abschnitt enthält Einstellungen, die für eine bestimmte Sprache gelten.

-   **`voice_commands`**: Schlüsselwörter zur Steuerung der Anwendung.
-   **`punctuation`**: Ein Wörterbuch zur automatischen Einfügung von Satzzeichen. Es ist in logische Gruppen zur besseren Übersichtlichkeit unterteilt.
-   **`recognition_aliases`**: Korrigiert häufige Erkennungsfehler von Vosk (z.B. `"sauna": "sonna"` ).
-   **`custom_vocabulary`**: Ein Wörterbuch für korrekturlesen unter Berücksichtigung der Groß-/Kleinschreibung, das nach Aliasen angewendet wird (z.B. `"ia": "IA"` ).

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

Globale Tastenkombinationen zur Steuerung der Anwendung.

-   **`pynput_keys`**: Eine Liste von Pynput-Tasten für die Tastenkombination.
-   **`display_name`**: Ein String, der in der Hilfenachricht angezeigt wird.

```yaml
hotkeys:
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

-   **`toggle_recording`** (Standard: `Alt+H`): Startet oder pausiert die aktuelle Diktierfunktion. Während
    der Pause bleibt das Mikrofon aktiv und das Sprachaktivierungswort funktioniert weiterhin.
-   **`finalize_session`** (Standard: `Alt+S`): Stoppt die Diktierfunktion und kopiert den
    gesammelten Text in die Zwischenablage.
-   **`sleep_toggle`** (Standard: `Alt+W`): Schaltet den **Energiesparmodus** ein, einen dritten Zustand,
    der sich von den beiden oben genannten unterscheidet. Im Energiesparmodus werden Audioaufnahme
    und Spracherkennung vollständig unterbrochen – die CPU-Belastung des
    Erkennungsprogramms sinkt auf nahezu null – aber das bedeutet auch, dass das
    Sprachaktivierungswort (`start_word`) nicht erkannt werden kann, bis der Energiesparmodus
    wieder deaktiviert wird. Nur die **`Alt+W`**-Tastenkombination selbst funktioniert weiterhin
    im Energiesparmodus, da sie nicht vom Audio abhängt. Das Aktivieren des
    Energiesparmodus während einer laufenden Diktierfunktion stoppt diese sauber (als ob
    **`Alt+H`** gedrückt worden wäre), sodass kein Audio während eines Satzes verloren geht.

    ```bash
    # How to test / how to run
    cd ~/git/vosk-cli-dictation/vosk-cli-dictation
    source vosk-env/bin/activate
    python3 src/main.py
    # Alt+W toggles sleep mode; Alt+H toggles dictation; Alt+S finalizes and copies.
    ```

### `sound_file`

Der absolute Pfad zu einer Sounddatei für Benachrichtigungen (z. B. `.oga`, `.wav`).

```yaml
sound_file: "/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga"
```

### `theme`

Dieser Abschnitt ermöglicht es Ihnen, die Farben der Anwendung in der Konsole anzupassen. Die Werte müssen gültige `colorama` Farbnamen sein (z. B. `GREEN`, `RED`, `BLUE`).

-   **`ready_message`**: Farbe der Meldung "Skript ist bereit".
-   **`help_text`**: Hauptfarbe für den Hilfe-Meldungsbereich.
-   **`help_title`**: Farbe für Überschriften innerhalb der Hilfe-Meldung.
-   **`info`**, **`success`**, **`warning`**, **`error`**: Farben für Statusmeldungen.

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
