% VOSK-CLI-DICTATION(1) vosk-cli-dictation | Benutzerbefehle
% Ronan Davalan
% 2026-08-28

# NAME

vosk-cli-dictation - Offline-Spracherkennung für die Kommandozeile, systemweit verfügbar.

# ZUSAMMENFASSUNG

**vosk-cli-dictation** [**-l** *LANG* | **--lang** *LANG*]

**vosk-cli-dictation** **\--diagnose**

**vosk-cli-dictation** **\--download-model** [*LANG*]

**vosk-cli-dictation** {**\--status** | **\--toggle** | **\--dictation-on** | **\--dictation-off** | **\--finalize** | **\--cancel** | **\--sleep** | **\--wake** | **\--sleep-toggle** | **\--stop**}

# BESCHREIBUNG

**vosk-cli-dictation** ist ein Kommandozeilen-Diktierwerkzeug für Linux, das von der Offline-Spracherkennungsengine Vosk angetrieben wird. Es nimmt kontinuierlich Audio über das Mikrofon auf und gibt den erkannten Text direkt in die aktuell aktive Anwendung ein (Terminal, Browser, Editor oder ein beliebiges anderes Fenster), sodass es systemweit verwendet werden kann, anstatt nur innerhalb eines einzelnen Programms.

Die gesamte Spracherkennung läuft lokal: weder Audio noch transkribierter Text werden jemals an einen externen Dienst gesendet.

Die Diktierfunktion wird entweder per Sprache (eine konfigurierbare, sprachspezifische Aktivierungs- und Stoppphrase) oder über Steuerungssubbefehle gestartet und gestoppt, die an eine Tastenkombination auf dem Desktop gebunden werden können. Außerdem kann die Funktion in einen Ruhezustand versetzt werden, um das Mikrofon vollständig freizugeben und die Spracherkennung zu deaktivieren, wenn sie nicht benötigt wird, ohne das Programm zu beenden.

Es läuft jeweils nur eine Sitzung pro Benutzer gleichzeitig. Sie öffnet eine private Unix-Socket-Verbindung an `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock` (Modus `0600`); derselbe Befehl, der mit einem Kontrollflag aufgerufen wird (siehe "EINE LAUFENDE SITZEUNG STEUEERN"), verbindet sich mit dieser Socket-Verbindung anstatt eine neue Sitzung zu starten.

Text wird injiziert, indem es in die Zwischenablage kopiert und ein Einfügen simuliert wird.
Unter Wayland werden **wtype** und **wl-clipboard** verwendet, wobei auf **ydotool** zurückgegriffen wird (welches den `ydotoold` Daemon und Zugriff auf `/dev/uinput` benötigt). Unter X11 wird **xdotool** verwendet. Mindestens ein Backend für den aktuellen Sitzungstyp muss installiert sein. Ihren Benutzer zur Gruppe `input` hinzuzufügen ist nur für den **ydotool**-Rückfall nötig; **wtype** und **xdotool** brauchen das nicht. **vosk-cli-dictation \--diagnose**
zeigt, welche Tools, Audio-Geräte und Zwischenablage-Zugriff verfügbar sind, und beendet dann das Programm.

Globale Hotkeys über `pynput` funktionieren nur unter einer reinen X11-Sitzung;
unter nativem Wayland sollten Sie die Kontroll-Unterbefehle stattdessen an die eigenen Tastenkombinationseinstellungen Ihres Desktops binden.

# OPTIONEN

**-l** *LANG*, **\--lang** *LANG*
:   Erzwingt die Schnittstellen- und Spracherkennungsprache für diese Sitzung
    (`en`, `fr`, `de` oder `es`), wobei der Wert `default_model` aus
    der Konfigurationsdatei überschrieben wird. *LANG* muss mit dem Namen eines
    der unter `vosk_models` in der Konfigurationsdatei definierten Modelle übereinstimmen.

**\--diagnose**
:   Überprüfen Sie die Umgebung (Sitzungstyp, Injektions-Backend, Tools, Modelle,
    Audioeingabe, Zwischenablage, Kontrollsocket) und beenden Sie das Programm. Der Exit-Status ist `0`
    wenn alle Prüfungen erfolgreich sind.

**\--download-model** [*LANG*]
:   Lädt das kleine Vosk-Modell für *LANG* (oder die aktuelle Sprache, wenn
    nicht angegeben) nach `~/.local/share/vosk-models/` herunter, prüft dessen
    Prüfsumme und beendet sich dann. Beim ersten Start wird ein Modell auch
    interaktiv angeboten, wenn keines installiert ist.

# STEUERUNG EINER LAUFENDEN SITZUNG

Jede der folgenden Flags verbindet sich mit dem Socket der laufenden Sitzung,
führt die Aktion aus, gibt den resultierenden Zustand aus (`OK DICTÉE`,
`OK ÉCOUTE`, `OK VEILLE`) oder `ERR <reason>`), und beendet sich. Sie sollen
an Tastenkombinationen auf dem Desktop gebunden werden.

**\--status**
:   Geben Sie den aktuellen Zustand aus, ohne ihn zu ändern.

**\--toggle**
:   Wechselt zwischen Diktat (DICTÉE) und Zuhören (ÉCOUTE).

**\--dictation-on**, **\--dictation-off**
:   Erzwinge Diktierfunktion ein oder aus.

**\--finalize**
:   Die Diktierfunktion beenden und den akkumulierten Text kopieren – entspricht dem Stopp-Befehl.

**\--cancel**
:   Die aktuelle Sitzungspuffer löschen, ohne etwas einzugeben.

**\--sleep**, **\--wake**, **\--sleep-toggle**
:   Einschalten, Ausschalten oder Umschalten des Energiesparmodus (VEILLE).

**\--stop**
:   Beenden Sie die laufende Sitzung sauber.

# SPRACHBEFEHLE

Der Aktivierungsausdruck und der Stoppausdruck bestehen jeweils aus zwei Wörtern und können pro Sprache unter `language_settings.<lang>.voice_commands` konfiguriert werden. Es werden zwei Wörter anstelle von einem verwendet, damit ein normaler Satz diese nicht auslöst. Mit der Werkseinstellung:

Sagen Sie "**start Diktat**", um zu beginnen, "**Stopp Diktat**", um zu beenden, und kopieren Sie das Ergebnis in die Zwischenablage.

"aktive Diktierfunktion" / "Diktierfunktion pausieren".

"Diktat starten" / "Diktat stoppen".

"Start des Diktats" / "Ende des Diktats".

Eine Auslösephrase wird nur berücksichtigt, wenn die durchschnittliche
Erkennungsgenauigkeit ihrer Wörter `recognition.confidence_threshold` überschreitet
(Standardwert `0.55`, pro Sprache überschreibbar). Eine Stoppphrase, die unter dem
Schwellenwert erkannt wird, wird verschluckt — weder ausgeführt noch in das Dokument
eingegeben — und ein Hinweis wird ausgegeben; wiederholen Sie sie oder verwenden Sie
`--finalize`. Während des Diktierens liefert ein zweiter, auf die Stoppphrase
beschränkter Erkenner ein Stoppsignal mit hoher Konfidenz, unabhängig von diesem
Schwellenwert (`recognition.restricted_stop_in_dictation`, standardmäßig aktiv, pro
Sprache überschreibbar). Wenn eine Phrase zweimal hintereinander ausgesprochen wird,
wird sie wörtlich eingegeben, anstatt einen Auslöser zu aktivieren.

Die Zeichensetzung und Anordnung von Wörtern (Komma, Punkt, Zeilenumbruch usw.) werden ebenfalls durch Sprache vorgegeben; die vollständige, sprachspezifische Liste ist unter `language_settings.<lang>.punctuation` in der Konfigurationsdatei definiert und wird vom Programm selbst beim Start ausgegeben.

# TASTENBELEGUNGEN

`pynput` Globale Hotkeys werden nur unter einer reinen X11-Sitzung und nur
wenn `hotkeys.pynput_enabled` wahr ist, aktiviert; auf nativen Wayland-Systemen werden sie nicht
aktiviert, und die Kontroll-Unterbefehle, die an eine Desktop-Verknüpfung gebunden sind, übernehmen deren Funktion. Selbst unter X11 verbraucht der `pynput`-Listener das Tastenereignis nicht: die Kombination erreicht auch das fokussierte Fenster, sodass ihre Verwendung bei einem Cursor in einem Terminal eine Escape-Sequenz einfügt (zum Beispiel `^[s` für **Alt+S**). Für einen sauberen Stopp aus einem beliebigen Fenster binden Sie stattdessen **\--finalize** (oder **\--toggle**, **\--sleep-toggle**) an eine Desktop-Tastenkombination. Die Werkseinstellungen definieren:

**Alt+H**
:   Aktiviert oder deaktiviert die Diktierfunktion. Dies pausiert oder setzt die Diktierfunktion fort; es wird **nichts**
    in die Zwischenablage kopiert, im Gegensatz zu **Alt+S** und der Stoppphrase.
    Während der Pause bleibt das Mikrofon aktiv und die Aktivierungsphrase funktioniert weiterhin.

**Alt+S:**
Hält die aktuelle Diktierfunktion an und kopiert den erfassten Text in die Zwischenablage – entspricht der Stopp-Phrase. Nur X11, und die Kombination gelangt in das fokussierte Fenster (siehe oben); bevorzugen Sie **\--finalize**, an eine Desktop-Tastenkombination gebunden.

**Alt+W**
:   Aktiviert den Energiesparmodus, einen dritten Zustand, der sich von den beiden oben genannten unterscheidet. Im Energiesparmodus wird der Audio-Stream beendet (das Mikrofon wird freigegeben) und die Spracherkennung wird deaktiviert, wodurch die CPU-Auslastung auf nahezu Null sinkt; die Aktivierungsphrase kann erst gehört werden, wenn der Energiesparmodus wieder deaktiviert wird. **Alt+W** selbst funktioniert weiterhin im Energiesparmodus, da es nicht von Audio abhängig ist. Die Aktivierung des Energiesparmodus während einer Diktierfunktion beendet diese sauber, sodass kein Audio während eines Satzes verloren geht.

**Strg+C**
:   Das Programm beenden.

Die ersten drei Hotkeys können im Abschnitt `hotkeys` der Konfigurationsdatei konfiguriert werden. **Strg+C** ist jedoch nicht konfigurierbar: Es ist das Standard-Interrupt-Signal, das immer aktiv ist und niemals über die Konfiguration neu belegt wird.

# MANUELLE BEDIENUNGSANWEISUNGEN

Während das Programm läuft, kann es auch über das Terminalfenster gesteuert werden, indem man einen der folgenden Befehle eingibt und die Eingabetaste drückt:

**/cancel**
:   Beendet die aktuelle Aufnahme ohne jegliche Textausgabe.

**/delete-word**:
   Löscht das zuletzt eingegebene Wort.

**/nl**
:   Eine neue Zeile einfügen (simuliert das Drücken der Eingabetaste).

# KONFIGURATION

Das Laufzeitverhalten wird durch eine YAML-Konfigurationsdatei gesteuert: Sie enthält verfügbare Sprachmodelle, Audio-Parameter, den Erkennungssicherheits-Schwellenwert, sprachspezifische Sprachbefehle und Satzzeichen, Hotkeys, Benachrichtigungstöne und das Konsolen-Farbthema.

Die Konfigurationsdatei wird anhand der ersten passenden Regel gefunden; sobald eine Regel zutrifft, werden die restlichen Regeln nicht mehr berücksichtigt.

1. Der Pfad, der in der Umgebungsvariablen **VOSK_CONFIG** angegeben ist, falls diese gesetzt ist. Wird unverändert verwendet; wird niemals automatisch erstellt.
2. `config/config.yaml`, relativ zum Projektverzeichnis, wenn die Ausführung von einem Git-Checkout (Entwicklungsmodus) erfolgt.
3. `$XDG_CONFIG_HOME/vosk-cli-dictation/config.yaml` (Standard: `~/.config/vosk-cli-dictation/config.yaml`). Wird beim ersten Ausführen automatisch aus der Vorlage erstellt, wenn die Installation über das Debian-Paket erfolgt.
4. Die vom Paket mitgelieferte Vorlage, schreibgeschützt.

Die aktive Sprache wird in folgender Reihenfolge ausgewählt: zuerst die **\--lang** Option, falls angegeben;
ansonsten die vom Betriebssystem erkannte Sprache; andernfalls der
`default_model` Wert aus der Konfigurationsdatei.

Siehe **configuration.md** in der Projektdokumentation für die vollständige
Referenz aller Konfigurationsschlüssel.

# DATEIEN

`~/.config/vosk-cli-dictation/config.yaml`
:   Konfigurationsdatei pro Benutzer (Installation des Debian-Pakets).

`/usr/share/vosk-cli-dictation/config.yaml`
:   Konfigurationsvorlage für die Fabrik (Installation als Debian-Paket), schreibgeschützt.

`~/.local/share/vosk-models/`
:   Standardmäßiger Suchpfad für Vosk-Akustikmodelle (Installation über Debian-Paket).

`config/config.yaml`
:   Konfigurationsdatei, die verwendet wird, wenn die Anwendung von einem Git-Repository ausgeführt wird.

`vosk-model/`
:   Standardmäßiger Speicherort, an dem nach Vosk-Spracherkennungsmodellen gesucht wird, wenn die Ausführung von einem Git-Checkout erfolgt.

`$XDG_RUNTIME_DIR/vosk-cli-dictation.sock`
:   Kontroll-Socket der laufenden Sitzung (Modus `0600`). Wird bei einem sauberen
    Beendigungsvorgang entfernt; ein veralteter Socket, der durch einen Absturz
    verbleibt, wird erkannt und beim nächsten Start ersetzt.

# AUSGANGSZUSTAND

**0**
:   Das Programm wurde sauber beendet, auch nach dem Drücken von **Strg+C**.

Nicht Null.
:   Startvorgang fehlgeschlagen: weder **ydotool** noch **xdotool** sind verfügbar, kein
    Spracherkennungsmodell konnte geladen werden oder das Audio-Gerät
    konnte nicht geöffnet werden.

# BEISPIELE

Mit der Standardsprache aus der Konfigurationsdatei starten:

```
vosk-cli-dictation
```

Englisch für diese Sitzung erzwingen:

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
