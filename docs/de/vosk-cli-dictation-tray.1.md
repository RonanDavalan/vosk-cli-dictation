% VOSK-CLI-DICTATION-TRAY(1) vosk-cli-dictation | Benutzerbefehle
% Ronan Davalan
% 2026-11-12

# NAME

vosk-cli-dictation-tray - Mikrofonsymbol im Benachrichtigungsbereich für vosk-cli-dictation

# ZUSAMMENFASSUNG

**vosk-cli-dictation-tray** [**--socket** *PFAD*] [**--dictation-command** *BEFEHL*]

**vosk-cli-dictation-tray** **--version**

# BESCHREIBUNG

**vosk-cli-dictation-tray** zeigt ein Mikrofon im Benachrichtigungsbereich des Desktops (KDE Plasma nativ; GNOME mit der Erweiterung
„AppIndicator and KStatusNotifierItem Support“) und bedient eine laufende **vosk-cli-dictation**-Sitzung über ihren Steuer-Socket. Es ist
ein eigenständiges Programm: Das Diktat braucht es nie, und es braucht nur den Socket. Es fragt die Sitzung viermal pro Sekunde mit `info`
ab; ein fehlender Socket bedeutet, dass kein Diktat läuft. Die Menübeschriftungen folgen der Sprache des laufenden Diktats, sonst der
Sprache der Sitzung, aus denselben gettext-Katalogen wie das Diktat.

Ohne Benachrichtigungsbereich zeigt es eine Desktop-Benachrichtigung, die erklärt, wie man einen aktiviert, und läuft weiter: Das Symbol
erscheint, wenn der Bereich später kommt. Pro Socket läuft nur ein Symbol.

# OPTIONEN

**--socket** *PFAD*
:   Zu bedienender Steuer-Socket. Standard: `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock`, der des eigenen Diktats des Benutzers.

**--dictation-command** *BEFEHL*
:   Befehl, der das Diktat startet, wie eine Shell-Befehlszeile zerlegt. Standard: die Umgebungsvariable
    `VOSK_CLI_DICTATION_COMMAND`, dann **vosk-cli-dictation** aus dem `PATH`, dann die Kopie des Git-Zweigs.

**--version**
:   Gibt die Version aus und beendet das Programm.

# SYMBOLZUSTÄNDE

Farbe und Form geben den Zustand an, sodass das Symbol auch für Farbfehlsichtige lesbar bleibt.

rotes Mikrofon mit Schallwellen
:   `DICTÉE`: Das Mikrofon ist offen und die Stimme wird getippt.

orangefarbenes Mikrofon
:   `ÉCOUTE`: Das Mikrofon ist offen, das Diktat ist aus, die Weckphrase wird erwartet.

blaues Mikrofon unter einer Mondsichel
:   `VEILLE`: Das Mikrofon ist freigegeben.

grünes Mikrofon als Umriss
:   Es läuft kein Diktat.

Ein Linksklick startet das Diktat, wenn keines läuft, und schaltet es sonst um. Der Tooltip wiederholt die Statuszeile und sagt „Modell
wird geladen…“, solange ein Modell lädt.

# MENÜ

Das Menü des Rechtsklicks, in dieser Reihenfolge:

1.  eine Statuszeile: Zustand, Sprache, Engine;
2.  Diktat ein- oder ausschalten; in den Tiefschlaf wechseln oder ihn verlassen; beenden und Text kopieren; Sitzung abbrechen;
3.  **Sprache**: dem System folgen, oder Französisch, Englisch, Deutsch, Spanisch; eine Sprache ohne installiertes Modell steht als „zum Herunterladen“ da;
4.  **Modell**: leicht oder vollständig; ein fehlendes Modell zeigt seine Größe, und seine Wahl startet den Download, mit einer Benachrichtigung am Ende;
5.  **Verfeinerung**: *Keine* und die Whisper-Größen, jede mit `GPU` oder `CPU` gekennzeichnet; mit ihrem Grund ausgegraut, wenn `faster-whisper` fehlt; beim ersten Gebrauch einer Größe werden ihre Gewichte geladen, mit einer Benachrichtigung am Anfang und am Ende. **Korrektur**: ausgegraut mit ihrem Grund, solange das laufende Diktat keine Optionen ankündigt;
6.  zur Konfiguration zurückkehren (die gespeicherte Auswahl vergessen);
7.  das Diktat starten oder beenden (ohne Terminal gestartet); das Symbol beim Anmelden starten; das Symbol beenden.

Während ein Modell lädt, sind die Auswahlen, die es ändern, ausgegraut.

# DATEIEN

`~/.local/state/vosk-cli-dictation/instance.log`
:   Ausgabe des vom Symbol gestarteten Diktats und der Modell-Downloads, die es startet.

`~/.config/autostart/vosk-cli-dictation-tray.desktop`
:   Der XDG-Autostart-Eintrag, den „Symbol beim Anmelden starten“ schreibt (`Hidden=true`, wenn das Häkchen fehlt).

`$XDG_RUNTIME_DIR/vosk-cli-dictation.sock`
:   Der Steuer-Socket des Diktats.

# SIEHE AUCH

**vosk-cli-dictation**(1)

# FEHLER

Melden Sie Fehler im Fehlerverfolgungssystem des Projekts:
*https://github.com/RonanDavalan/vosk-cli-dictation/issues*

# AUTOR

Ronan Davalan und die in CONTRIBUTORS.md aufgeführten Mitwirkenden.
