# Projektkonfigurationsanleitung

Dieses Dokument bietet eine detaillierte Erklärung aller verfügbaren Optionen in der `config/config.yaml` Datei. Die korrekte Konfiguration dieser Datei ist entscheidend, um die Anwendung an Ihre spezifischen Bedürfnisse, Ihre Sprache und Ihre Hardware anzupassen.

Wie Sprache bestimmt wird.

Die Anwendung wählt die zu verwendende Sprache anhand folgender Prioritätsreihenfolge aus:

1.  **Befehlszeilenargument (höchste Priorität):** Die Verwendung des Flags `-l` oder `--lang` (z. B. `python src/main.py -l en`) überschreibt immer alle anderen Einstellungen.

2. **Systemsprache (Automatische Erkennung):** Wenn kein Sprachparameter angegeben wird, erkennt die Anwendung automatisch die Sprache Ihres Betriebssystems.

3.  **`default_model` Einstellung (Fallback):** Wenn die Sprache des Systems nicht ermittelt werden kann, verwendet die Anwendung das in der `default_model` Einstellung angegebene Modell als letzte Ausweichoption.

## Allgemeine Struktur von `config.yaml`

Die Konfigurationsdatei ist in logische Abschnitte unterteilt:

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

## Konfigurationsbereiche im Detail

### `vosk_models`

Eine Liste, die die verfügbaren Vosk-Spracherkennungsmodelle definiert.

-   **`name`** (String): Ein eindeutiger, kurzer Name für das Modell (z.B. `fr`, `en`).
-   **`path_relative`** (String): Der relative Pfad zum entpackten Vosk-Modellordner.  Wird aufgelöst relativ zu, in der folgenden Reihenfolge: `$XDG_DATA_HOME/vosk-models/` (Standard: `~/.local/share/vosk-models/`),
    `/usr/share/vosk-models/`, dann das Projektverzeichnis, wenn es von einem Git-Checkout ausgeführt wird – der erste dieser Pfade, der tatsächlich den Ordner enthält, gewinnt. Kann auch als absoluter Pfad angegeben werden, welcher immer Vorrang hat.  Siehe die Manpage, Abschnitt KONFIGURATION, für die vollständige Auflösung.

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

Ein Modell, das deklariert, aber nicht auf der Festplatte vorhanden ist, wird beim Start gemeldet und übersprungen; der Startvorgang schlägt nur fehl, wenn überhaupt kein Modell geladen werden kann.

### `default_model`

The name of the Vosk model to load at startup. Must match a `name` in the `vosk_models` list.

```yaml
default_model: "en"
```

### `control_socket`

Boolean, Standardwert: `true`. Wenn aktiviert, hört die laufende Sitzung an einem Unix-Socket unter `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock` (Modus: `0600`) zu, sodass die Steuerungs-Unterbefehle (`--toggle`, `--sleep-toggle`, `--status`, `--stop`, ...) es steuern können. Setzen Sie den Wert auf `false`, um den Socket vollständig zu deaktivieren; das Tool bleibt dann zwar interaktiv nutzbar, kann aber nicht über einen zugewiesenen Tastenkombination gesteuert werden.

```yaml
control_socket: true
```

### `audio`

Parameter für Ihr Mikrofon.

-   **`sample_rate`** (Integer): Die Abtastrate, mit der Ihr Modell trainiert wurde (normalerweise `16000`).
-   **`channels`** (Integer): Anzahl der Audio-Kanäle (sollte `1` für Mono sein).
-   **`frames_per_buffer`** (Integer): `2048` oder `4096` sind übliche Werte.
-   **`buffer_size`** (Integer): Die Größe des Audio-Puffers.
-   **`queue_max_chunks`** (Integer): Maximale Tiefe der Audio-Warteschlange, in `buffer_size` Blöcken (`16` ≈ 2 Sekunden). Wenn die Erkennung hinterherhinkt, wird der älteste Block verworfen, anstatt die Latenz zu erhöhen; ein Überlaufzähler wird in `--status` und `--diagnose` angezeigt.

```yaml
audio:
  sample_rate: 16000
  channels: 1
  frames_per_buffer: 4096
  buffer_size: 2048
  queue_max_chunks: 16
```

### `recognition`

Parameter für die Vosk-Spracherkennungsengine.

-   **`confidence_threshold`** (float, 0.0-1.0, Standardwert `0.55`): Eine Sprachauslösephrase (Start oder Stopp) wird nur berücksichtigt, wenn die durchschnittliche Konfidenz ihrer Wörter diesen Wert erreicht. Darunter wird eine Startphrase als normaler Text behandelt; eine **Stopp**phrase wird verschluckt — weder ausgeführt noch in das Dokument eingegeben — und ein Hinweis wird ausgegeben. Pro Sprache mit einem gleichnamigen Schlüssel unter `language_settings.<lang>` überschreibbar.
-   **`restricted_grammar_in_listening`** (boolean, Standardwert: `true`): Während des Lauschens nach der Startphrase, wird die Spracherkennung mit einer Kaldi-Grammatik durchgeführt, die auf diese Phrase beschränkt ist. Der CPU-Verbrauch sinkt deutlich, allerdings wird beim Start die vollständige Spracherkennung neu aufgebaut. Setzen Sie den Wert auf `false`, um die vollständige Spracherkennung im "Listening"-Modus aktiv zu halten. Pro Sprache unter `language_settings.<lang>` überschreibbar — die Werkskonfiguration deaktiviert es für `es`, wo das kleine Modell die beschränkte Grammatik langsamer decodiert als die vollständige.
-   **`restricted_stop_in_dictation`** (boolean, Standardwert: `true`): Während des Diktierens läuft ein zweiter, auf die Stoppphrase beschränkter Erkenner neben dem vollständigen. Er liefert ein Stoppsignal mit hoher Konfidenz, unabhängig von `confidence_threshold` — derselbe Mechanismus wie für die Startphrase im Lauschzustand. Pro Sprache unter `language_settings.<lang>` überschreibbar; auf `false` setzen auf Hardware, wo die zusätzliche beschränkte Decodierung pro Audioblock zu teuer ist (sie ist etwa 5× günstiger als die vollständige Decodierung).

```yaml
recognition:
  confidence_threshold: 0.55
  restricted_grammar_in_listening: true
  restricted_stop_in_dictation: true
```

### `sleep`

-   **`releases_device`** (boolean, Standardwert: `true`): Im Ruhezustand den Audio-Stream schließen, sodass das Mikrofon vollständig freigegeben wird (die LED erlischt) und ein anderes Programm es verwenden kann; das erneute Öffnen beim Aufwachen dauert etwa 200 ms. Setzen Sie den Wert auf `false`, um den Stream nur anzuhalten, ohne ihn zu schließen – das Gerät bleibt belegt, aber das Aufwachen ist etwas schneller.

```yaml
sleep:
  releases_device: true
```

### `clipboard`

Der Text wird injiziert, indem er in die Zwischenablage kopiert und dann durch eine Simulation eingefügt wird.

-   **`restore`** (Boolean, Standardwert: `true`): Setzt den vorherigen Inhalt der Zwischenablage des Benutzers wieder ein, nachdem ein Einfügen stattgefunden hat. Inhalte der Zwischenablage, die keine Texte sind (z. B. ein Bild), werden niemals gespeichert oder überschrieben. Kann auch pro Ausführung deaktiviert werden (mit `--no-clipboard-restore`).
-   **`restore_delay_ms`** (Integer, Standardwert: `250`): Verzögerung vor dem Wiederherstellen, um der Zielanwendung Zeit zu geben, den eingefügten Text zu lesen.
-   **`confirm_timeout_ms`** (Integer, Standardwert: `500`): Maximale Wartezeit, bis bestätigt wird, dass die Zwischenablage tatsächlich unseren Text enthält, bevor der Einfügetaste-Befehl gesendet wird.

```yaml
clipboard:
  restore: true
  restore_delay_ms: 250
  confirm_timeout_ms: 500
```

### `injection`

-   **`paste_combo`** (String, Standardwert: `ctrl+v`) und **`terminal_paste_combo`** (Standardwert: `ctrl+shift+v`): Die Tastenkombination, die zum Einfügen verwendet wird. Unter X11 wird die Fensterklasse des fokussierten Fensters mit `terminal_window_classes` verglichen, um automatisch die richtige Kombination auszuwählen; unter Wayland gibt es keine API für fokussierte Fenster, daher wird `paste_combo` verwendet, es sei denn, Sie überschreiben sie.
-   **`terminal_window_classes`** (Liste): Fensterklassen, die als Terminals behandelt werden (nur X11).
-   **`ydotool_keycodes`** (Zuordnung): Physische Linux-Tastencodes, die nur auf dem `ydotool` Fallback-Pfad verwendet werden. Überschreiben Sie diese unter einer nicht-QWERTY-Tastaturbelegung, wenn dieser Fallback tatsächlich verwendet wird; der Standard-Wayland-Pfad (`wtype`) funktioniert mit Keysyms und ist unabhängig von der Tastaturbelegung.

```yaml
injection:
  paste_combo: "ctrl+v"
  terminal_paste_combo: "ctrl+shift+v"
  terminal_window_classes: ["konsole", "gnome-terminal-server", "xterm", "st", "alacritty", "kitty", "foot"]
  ydotool_keycodes: {}
```

### `language_settings`

Dieser Abschnitt enthält Einstellungen, die für eine bestimmte Sprache gelten. Die Werkskonfiguration enthält vier: `en`, `fr`, `de`, `es`.

-   **`voice_commands`**: die zwei Wörter `wake_phrase` und `stop_phrase` für diese Sprache. Zwei Wörter, sodass ein normaler Satz sie nie auslöst. (Die vorherigen, einwortigen Schlüssel `start_word` / `stop_word` werden weiterhin gelesen, falls vorhanden, zur Abwärtskompatibilität.)
-   **`punctuation`**: Ein Wörterbuch, um automatisch Satzzeichen einzufügen, das in logische Gruppen organisiert ist. Spanische Satzzeichen `¿` und `¡` werden nur durch explizite Befehle (`"abrir interrogación"`, `"abrir exclamación"`) eingefügt, niemals automatisch.
-   **`typography`**: Sprachspezifische Ausgaberegeln – siehe unten.
-   **`recognition_aliases`**: Korrigiert häufige Erkennungsfehler von Vosk. Die mitgelieferte Tabelle enthält nur allgemeine, unumstrittene Korrekturen (z. B. `"de points": "deux points"`); die französische Tabelle enthält außerdem `"tirez": "tiret"`, weil das kleine französische Modell den Gedankenstrich-Befehl systematisch so ausgibt. Korpus-spezifische Korrekturen befinden sich in `config/config.example.yaml`, zum Kopieren und Anpassen.
-   **`custom_vocabulary`**: Ein Wörterbuch für korrektursensible Korrekturen, die nach Aliasen angewendet werden (z. B. `"ia": "IA"`).

```yaml
language_settings:
  fr: # Settings for French
    voice_commands:
      wake_phrase: "active dictée"
      stop_phrase: "stop dictée"
    punctuation:
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

Ersetzt eine bisher fest codierte französische Version. Pro Sprache:

-   **`thin_space`** (boolean): Fügt einen schmalen, nicht-umbruchbaren Abstand (U+202F) vor den in `space_before` aufgeführten Symbolen ein. `true` für Französisch, `false` ansonsten. Deaktivieren Sie diese Option, wenn der schmale Abstand `grep` oder Ihr Terminal beeinträchtigt.
-   **`space_before`** (liste): Symbole, die einen führenden Trenner (einen schmalen Abstand, wenn `thin_space`, andernfalls ein normales Leerzeichen) benötigen. Leer für Englisch, Deutsch und Spanisch.
-   **`space_after`** (liste): Symbole, denen ein Leerzeichen folgt.
-   **`capitalize_sentence_start`** (boolean): Setzt den ersten Wort jedes Satzes groß. Im Deutschen werden nur Satzanfänge großgeschrieben; Eigennamen bleiben unverändert, da eine zuverlässige Großschreibung von Substantiven einen morphologischen Analysator erfordern würde.
-   **`quote_open`** / **`quote_close`**: öffnende und schließende Anführungszeichen (`« »` für Französisch, `„ "` für Deutsch).

### `hotkeys`

Globale Tastenkombinationen über `pynput`. Diese werden nur unter einer reinen X11-Sitzung gestartet, und selbst dort verbraucht der `pynput`-Listener das Tastenereignis nicht: die Kombination erreicht auch das fokussierte Fenster, sodass ihre Verwendung bei einem Cursor in einem Terminal eine Escape-Sequenz einfügt (`^[s` für `Alt+S`). Für einen sauberen Stopp aus einem beliebigen Fenster — und für natives Wayland, wo `pynput` nichts sieht — binden Sie stattdessen die Kontroll-Unterbefehle (`--toggle`, `--finalize`, `--sleep-toggle`) an die eigenen Tastenkombinationseinstellungen Ihres Desktops.

-   **`pynput_enabled`** (boolesch, Standardwert: `true`): Wird nur unter X11 berücksichtigt. Setzen Sie den Wert auf `false`, um den `pynput` Listener nie zu starten.
-   **`pynput_keys`**: Eine Liste von Pynput-Tasten für die Tastenkombination.
-   **`display_name`**: Ein String, der in der Hilfenachricht angezeigt wird.

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

-   **`toggle_recording`** (Standard: `Alt+H`): Startet oder pausiert die aktuelle Diktierfunktion. Während
    der Pause bleibt das Mikrofon aktiv und die Sprachaktivierungsphrase funktioniert weiterhin.
-   **`finalize_session`** (Standard: `Alt+S`): Stoppt die Diktierfunktion und kopiert den
    gesammelten Text in die Zwischenablage. Nur X11, und die Kombination gelangt in das
    fokussierte Fenster (siehe oben) — bevorzugen Sie `vosk-cli-dictation --finalize`, an
    eine Desktop-Tastenkombination gebunden.
-   **`sleep_toggle`** (Standard: `Alt+W`): Schaltet den **Energiesparmodus** ein, einen dritten Zustand,
    der sich von den beiden oben genannten unterscheidet. Im Energiesparmodus wird der
    Audiostream geschlossen (das Mikrofon wird freigegeben) und die Spracherkennung wird
    blockiert, sodass die CPU-Auslastung auf nahezu Null sinkt – aber die
    Sprachaktivierungsphrase kann erst wieder erkannt werden, wenn der Energiesparmodus
    wieder ausgeschaltet wird. Nur die **`Alt+W`**-Tastenkombination selbst funktioniert
    weiter, da sie nicht vom Audio abhängt. Das Aktivieren des Energiesparmodus während
    einer laufenden Diktierfunktion stoppt diese sauber (als ob **`Alt+H`** gedrückt
    worden wäre), sodass kein Audio während eines Satzes verloren geht.

    ```bash
    # How to test / how to run
    cd ~/git/vosk-cli-dictation/vosk-cli-dictation
    source vosk-env/bin/activate
    python3 src/main.py
    # Alt+W toggles sleep mode; Alt+H toggles dictation; Alt+S finalizes and copies.
    ```

### `sound_file`

Der absolute Pfad zu einer Sounddatei für Benachrichtigungen (z.B. `.oga`, `.wav`).

```yaml
sound_file: "/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga"
```

### `theme`

Dieser Abschnitt ermöglicht es Ihnen, die Farben der Anwendung in der Konsole anzupassen. Die Werte müssen gültige `colorama` Farbnamen sein (z. B. `GREEN`, `RED`, `BLUE`).

-   **`ready_message`**: Farbe der Meldung "Skript ist bereit".
-   **`help_text`**: Hauptfarbe für den Hilfe-Meldungsbereich.
-   **`help_title`**: Farbe für Titel innerhalb der Hilfe-Meldung.
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
