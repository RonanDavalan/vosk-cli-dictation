% VOSK-CLI-DICTATION(1) vosk-cli-dictation | Benutzerbefehle
% Ronan Davalan
% 2026-08-26

# NAME

vosk-cli-dictation - Offline-Spracherkennung für die Kommandozeile, systemweit verfügbar.

# ZUSAMMENFASSUNG

**vosk-cli-dictation** [**-l** *LANG* | **--lang** *LANG*]

# BESCHREIBUNG

**vosk-cli-dictation** ist ein Kommandozeilen-Diktierwerkzeug für Linux, das von der Offline-Spracherkennungsengine Vosk betrieben wird. Es hört kontinuierlich über das Mikrofon und gibt den erkannten Text direkt in die aktuell aktive Anwendung ein (Terminal, Browser, Editor oder ein anderes Fenster), sodass es systemweit verwendet werden kann und nicht nur innerhalb eines einzelnen Programms.

Die gesamte Spracherkennung läuft lokal: Audio- oder transkribierter Text werden niemals an einen externen Dienst gesendet.

Die Diktierfunktion wird entweder per Sprache (ein konfigurierbares Aktivierungswort und ein Stoppwort) oder über globale Hotkeys gestartet und beendet. Außerdem kann sie in den Schlafmodus versetzt werden, um die Audioaufnahme und Spracherkennung vollständig zu deaktivieren, wenn sie nicht benötigt wird, ohne das Programm zu beenden.

Die Textsimulation wird über **ydotool** durchgeführt, falls verfügbar, oder
**xdotool** als Alternative. **ydotool** unterstützt sowohl Wayland als auch X11 über
die `/dev/uinput` Schnittstelle; **xdotool** unterstützt nur X11 (oder Wayland
über XWayland). Mindestens eines der beiden Programme muss installiert sein.

# OPTIONEN

**-l** *LANG*, **--lang** *LANG*
:   Erzwingt die Schnittstellen- und Spracherkennungsprache für diese Sitzung
    (z. B. `en` oder `fr`), wobei der Wert von `default_model` aus
    der Konfigurationsdatei überschrieben wird. *LANG* muss mit dem Namen
    eines der unter `vosk_models` in der Konfigurationsdatei deklarierten Modelle
    übereinstimmen.

# SPRACHBEFEHLE

Das Aktivierungswort und das Stoppwort sind pro Sprache konfigurierbar. Mit der
Werkseinstellung:

Englisch
:   Sagen Sie **„start"**, um mit der Diktierfunktion zu beginnen, **„oops"**,
    um sie zu beenden und das Ergebnis in die Zwischenablage zu kopieren.

Französisch
:   Sagen Sie **„démarre"**, um mit der Diktierfunktion zu beginnen, **„zut"**,
    um sie zu beenden und das Ergebnis in die Zwischenablage zu kopieren.

Die Zeichensetzung und das Layout werden ebenfalls durch die Sprache bestimmt; die vollständige, sprachspezifische Liste ist unter `language_settings.<lang>.punctuation` in der Konfigurationsdatei definiert und wird von dem Programm selbst beim Start ausgegeben.

# TASTENBELEGUNGEN

Globale Hotkeys funktionieren unabhängig davon, welches Fenster gerade den Fokus hat. Die
Werkseinstellungen definieren:

**Alt+H**
:   Aktiviert oder deaktiviert die Diktierfunktion (entspricht den Aktivierungs-/Stoppwörtern). Während die Diktierfunktion pausiert ist, bleibt das Mikrofon aktiv und die Sprachaktivierung funktioniert weiterhin.

**Alt+S**
:   Stoppt die aktuelle Diktierfunktion und kopiert den erfassten Text in die Zwischenablage.

**Alt+W**
:   Aktiviert/Deaktiviert den Energiesparmodus, einen dritten Zustand, der sich von den beiden oben genannten unterscheidet. Im Energiesparmodus werden Audioaufnahme und Spracherkennung vollständig unterbrochen – die CPU-Auslastung sinkt auf nahezu Null – aber das akustische Auslöswort kann erst wieder erkannt werden, wenn der Energiesparmodus erneut deaktiviert wird. Der Tastenkürzel **Alt+W** selbst funktioniert weiterhin im Energiesparmodus, da er nicht von Audio abhängt. Das Aktivieren des Energiesparmodus während einer Diktierfunktion beendet diese sauber, sodass kein Audio während eines Satzes verloren geht.

**Strg+C**
:   Das Programm beenden.

Die ersten drei Tastenkombinationen können im Abschnitt `hotkeys` der Konfigurationsdatei konfiguriert werden. **Strg+C** ist es nicht: es ist das Standard-Interrupt-Signal, immer aktiv, niemals über die Konfiguration neu belegbar.

# MANUELLE BEDIENUNGSANWEISUNGEN

Während das Programm läuft, können Sie es auch über das Terminalfenster steuern, indem Sie einen der folgenden Befehle eingeben und die Eingabetaste drücken:

**/cancel**
:  Bricht die aktuelle Aufnahme ohne Ausgabe von Text ab.

**/delete-word**
:   Löscht das zuletzt eingegebene Wort.

**/nl**
:   Fügt eine neue Zeile ein (simuliert das Drücken der Eingabetaste).

# KONFIGURATION

Das Laufzeitverhalten wird durch eine YAML-Konfigurationsdatei gesteuert: Sie enthält verfügbare Sprachmodelle, Audio-Parameter, den Erkennungssicherheits-Schwellenwert, sprachspezifische Sprachbefehle und Interpunktion, Tastenkombinationen, Benachrichtigungstöne und das Konsolen-Farbthema.

Die Konfigurationsdatei wird anhand der ersten passenden Regel gefunden; sobald eine Regel zutrifft, werden die restlichen Regeln nicht mehr berücksichtigt.

1. Der Pfad, der in der Umgebungsvariablen **VOSK_CONFIG** angegeben ist, falls diese gesetzt ist. Wird unverändert verwendet; wird nie automatisch erstellt.
2. `config/config.yaml`, relativ zum Projektverzeichnis, wenn die Anwendung von einem Git-Checkout (Entwicklungsmodus) ausgeführt wird.
3. `$XDG_CONFIG_HOME/vosk-cli-dictation/config.yaml` (Standard: `~/.config/vosk-cli-dictation/config.yaml`). Wird beim ersten Start automatisch aus der Vorlage erstellt, wenn die Anwendung aus dem Debian-Paket installiert wurde.
4. Die vom Paket mitgelieferte Vorlage, schreibgeschützt.

Die aktive Sprache wird in folgender Reihenfolge ausgewählt: zuerst die **--lang**-Option, falls diese angegeben ist;
ansonsten die vom Betriebssystem erkannte Sprache; andernfalls der `default_model` Wert aus der Konfigurationsdatei.

Siehe **configuration.md** in der Projektdokumentation für die vollständige
Referenz aller Konfigurationsschlüssel.

# DATEIEN

`~/.config/vosk-cli-dictation/config.yaml`
:   Konfigurationsdatei pro Benutzer (Installation des Debian-Pakets).

`/usr/share/vosk-cli-dictation/config.yaml`
:   Konfigurationsvorlage für die Fabrik (Installation des Debian-Pakets), schreibgeschützt.

`~/.local/share/vosk-models/`
:   Standard-Suchpfad für Vosk-Akustikmodelle (Installation über das Debian-Paket).

`config/config.yaml`
:   Konfigurationsdatei, die verwendet wird, wenn von einem Git-Checkout aus ausgeführt wird.

`vosk-model/`
:   Standardmäßiger Suchpfad für Vosk-Akustikmodelle, wenn die Ausführung von einem Git-Checkout erfolgt.

# AUSGANGSZUSTAND

**0**
: Das Programm wurde sauber beendet, auch nach dem Drücken von **Strg+C**.

Nicht-Null.
:   Start fehlgeschlagen: weder **ydotool** noch **xdotool** sind verfügbar, kein
    Spracherkennungsmodell konnte geladen werden oder das Audio-Gerät
    konnte nicht geöffnet werden.

# BEISPIELE

Beginne mit der Standardeinstellung aus der Konfigurationsdatei:

```
vosk-cli-dictation
```

Englisch erzwingen für diese Sitzung:

```
vosk-cli-dictation --lang en
```

# SIEHE AUCH

Vosk-Modelle und Downloads: *https://alphacephei.com/vosk/models*

Projekt-Homepage: *https://vosk.davalan.fr/*

# FEHLER

Melden Sie Fehler im Fehlerverfolgungssystem des Projekts:
*https://github.com/RonanDavalan/vosk-cli-dictation/issues*

# AUTOR

Ronan Davalan und die in CONTRIBUTORS.md aufgeführten Mitwirkenden.
