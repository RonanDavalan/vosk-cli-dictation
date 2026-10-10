# Vosk-CLI-Dictation

<p align="center">
  <a href="https://github.com/RonanDavalan/vosk-cli-dictation/blob/main/LICENSE"><img src="https://img.shields.io/badge/Lizenz-MIT-blue.svg" alt="Lizenz: MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/Version-v0.5.4--beta-yellow.svg" alt="Version: v0.5.4-beta"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+"></a>
  <a href="#"><img src="https://img.shields.io/badge/Linux-Debian_%C2%B7_Fedora_%C2%B7_openSUSE_%C2%B7_Arch-blue.svg" alt="Native Pakete für Debian, Fedora, openSUSE und Arch Linux"></a>
  <a href="#"><img src="https://img.shields.io/badge/Beiträge-Willkommen-brightgreen.svg" alt="Beiträge willkommen"></a>
</p>

[English](../../README.md) | [Français](../fr/README.md) | **Deutsch** | [Español](../es/README.md)

<p align="center">
  <a href="https://vosk.davalan.fr/"><strong>Besuchen Sie die offizielle Startseite für eine ausführliche Tour!</strong></a>
</p>

<p align="center">
  <a href="https://vosk.davalan.fr/"><strong>▶ Sehen Sie sich das Demonstrationsvideo auf der Startseite an</strong></a>
</p>

Ein leistungsfähiges und anpassbares Diktierwerkzeug für die Kommandozeile unter Linux, angetrieben von der Vosk-Engine. Verwandeln Sie Ihre Sprache direkt im Terminal in Text und lassen Sie ihn in jeder beliebigen Anwendung erscheinen.

---

## Warum dieses Projekt?

Dieses Werkzeug entstand aus dem Bedarf an einem robusten, lokal laufenden Diktiersystem unter GNU/Linux, das dem Benutzer die volle Kontrolle über seine Daten und das Verhalten der Software lässt. Anders als Cloud-Lösungen arbeitet es **zu 100 % offline** und garantiert so Ihre Privatsphäre.

## Hauptmerkmale

*   **Systemweite Integration:** Diktieren Sie in jede aktive Anwendung (Terminal, Browser, Code-Editor usw.).
*   **Mehrsprachig:** Funktioniert sofort mit **Englisch**, **Französisch**, **Deutsch** und **Spanisch**.
*   **Universelle Steuerung:** Eine laufende Sitzung wird über einen privaten Unix-Socket gesteuert; derselbe Befehl, an ein Desktop-Kürzel gebunden (`vosk-cli-dictation --toggle`, `--sleep`, `--status`), steuert sie auf jedem Desktop — auch unter nativem Wayland. Globale Tastenkürzel über `pynput` bleiben eine Komfortfunktion nach bestem Bemühen: Unter Wayland erreichen sie nur XWayland-Fenster, keine nativen Wayland-Fenster.
*   **Vollständig anpassbar:** Konfigurieren Sie Farben der Oberfläche, Tastenkürzel, Sprachauslöser, die Typografie je Sprache und Erkennungs-Aliase in einer einfachen Datei `config.yaml`.
*   **Vollständige Zeichensetzung:** Diktieren Sie das gesamte Spektrum der Satzzeichen mit natürlichen Sprachbefehlen.
*   **Privat und offline:** Läuft vollständig auf Ihrem Rechner. Ihre Stimme verlässt Ihren Computer nie.

> [!NOTE]
>
> **Unterstützung für X11 und Wayland.** Der Text wird eingefügt, indem er in die Zwischenablage kopiert und ein Einfügen simuliert wird. Unter Wayland verwendet das Werkzeug `wtype` und `wl-clipboard`, mit `ydotool` als Ersatz (das den Dienst `ydotoold` und Zugriff auf `/dev/uinput` braucht, in der Regel über die Gruppe `input` — `sudo usermod -aG input $USER`, danach ab- und wieder anmelden). Unter X11 verwendet es `xdotool`. Mindestens ein Backend für den aktuellen Sitzungstyp muss installiert sein; `vosk-cli-dictation --diagnose` zeigt, was verfügbar ist.
>
> **Globale Tastenkürzel.** `pynput` beobachtet den X-Server: Unter Wayland sieht es Tastenereignisse nur für Fenster, die über XWayland laufen (viele Electron- und ältere Anwendungen), nie für ein fokussiertes natives Wayland-Fenster. Es verbraucht die Ereignisse außerdem nicht — die Tastenkombination erreicht auch das fokussierte Fenster, sodass ihr Drücken beim Tippen in ein Terminal eine Escape-Sequenz einfügt (`^[s` für `Alt+S`). Für eine Steuerung, die überall funktioniert, binden Sie stattdessen die Kürzel-Einstellungen Ihres Desktops an die Steuer-Unterbefehle (`vosk-cli-dictation --toggle`, `--finalize`, `--sleep-toggle`). Siehe *Eine laufende Sitzung steuern* weiter unten. Unter Debian ist `ydotool` in `trixie-backports` paketiert, nicht in stable.

## Erste Schritte

### Das native Paket installieren (empfohlen)

Installieren Sie das für Ihre Distribution gebaute Paket von der
[Download-Seite](https://vosk.davalan.fr/) — keine manuelle Einrichtung, keine
virtuelle Umgebung anzulegen:

```bash
# Debian 12+ und Ableger (Ubuntu 24.04+, Mint 22+...)
sudo apt install ./vosk-cli-dictation_0.5.4~beta_all.deb

# Fedora
sudo dnf install ./vosk-cli-dictation-0.5.4~beta-1.fc42.noarch.rpm

# openSUSE (Leap)
sudo zypper install ./vosk-cli-dictation-0.5.4~beta-1.leap156.noarch.rpm

# Arch Linux
sudo pacman -U ./vosk-cli-dictation-0.5.4_beta-1-any.pkg.tar.zst
```

Bei der ersten Konfiguration des Pakets wird eine private virtuelle Umgebung aufgebaut und die Vosk-Engine darin installiert (dieser Schritt braucht Netzwerkzugriff).

Laden Sie dann ein Sprachmodell herunter und beginnen Sie zu diktieren:

```bash
vosk-cli-dictation --download-model fr   # auch: en, de, es
vosk-cli-dictation -l fr
```

Starten Sie das Werkzeug ohne installiertes Modell, bietet es den Download interaktiv an. Ein fehlendes Modell wird gemeldet, ist aber nicht fatal, solange eine Sprache geladen wird. Heruntergeladene Modelle werden per SHA256 geprüft und unter `~/.local/share/vosk-models/` abgelegt.

Das Paket zieht `xdotool` (X11) oder `ydotool` (Wayland-Ersatz) für die Texteingabe nach. Für natives Wayland installieren Sie zusätzlich das bevorzugte Backend mit dem Paketmanager Ihrer Distribution (Beispiel Debian):

```bash
sudo apt install wtype wl-clipboard
```

`ydotool` verlangt, dass Ihr Benutzer in der Gruppe `input` ist (`sudo usermod -aG input $USER`, danach ab- und wieder anmelden); `xdotool` und `wtype` nicht. Führen Sie `vosk-cli-dictation --diagnose` aus, um zu sehen, welches Backend, welcher Audioeingang und welcher Zwischenablage-Zugriff verfügbar sind.

> [!NOTE]
> Gibt `apt` eine Sandbox- oder `_apt`-Berechtigungswarnung aus, liegt das daran, dass sich das `.deb` in Ihrem Home-Verzeichnis befindet, das der Benutzer `_apt` nicht lesen kann. Kopieren Sie es zuerst nach `/tmp/` und installieren Sie es von dort. Die Installation gelingt in beiden Fällen.

### Aus den Quellen installieren (für die Entwicklung)

Dieser Weg führt den Code direkt aus einer Git-Arbeitskopie aus. Die unten genannten Systempakete sind die von Debian; unter Fedora, openSUSE oder Arch installieren Sie die Entsprechungen mit Ihrem Paketmanager.

```bash
sudo apt-get update && sudo apt-get install python3-pip python3-venv portaudio19-dev gettext xdotool pulseaudio-utils
# Wayland, optional: sudo apt-get install wtype wl-clipboard ydotool

git clone https://github.com/RonanDavalan/vosk-cli-dictation.git
cd vosk-cli-dictation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Laden Sie ein Modell herunter und starten Sie das Skript:

```bash
python3 src/main.py --download-model fr   # auch: en, de, es
python3 src/main.py -l fr                 # die Standardsprache kommt aus config.yaml
python3 src/main.py --diagnose            # die Umgebung prüfen, ohne eine Sitzung zu starten
```

Auf diese Weise heruntergeladene Modelle landen ebenfalls in `~/.local/share/vosk-models/`. Ersatzweise wird auch ein Modellordner (zum Beispiel `vosk-model-small-fr-0.22`) berücksichtigt, der direkt im Verzeichnis `vosk-model/` des Projekts liegt.

Pro Benutzer läuft immer nur eine Sitzung; ein zweiter Start wird abgelehnt und verweist auf `--status`.

### Tipp: einen Schnellstart-Befehl anlegen (optional)

Für den bequemeren Zugriff können Sie der Konfigurationsdatei Ihrer Shell (zum Beispiel `~/.bashrc` oder `~/.zshrc`) eine Funktion hinzufügen.

1.  Öffnen Sie Ihre Konfigurationsdatei: `nano ~/.bashrc`
2.  Fügen Sie am Ende die folgenden Zeilen hinzu. **Ersetzen Sie unbedingt `/path/to/your/vosk-cli-dictation` durch den tatsächlichen, absoluten Pfad zum Projektverzeichnis.**

    ```bash
    # Definiert einen Befehl 'vosk', der das Diktierskript einfach startet.
    vosk() {
        # Prüft, ob das Projektverzeichnis existiert
        if [ -d "/path/to/your/vosk-cli-dictation" ]; then
            cd "/path/to/your/vosk-cli-dictation" && \
            source venv/bin/activate && \
            python3 src/main.py "$@" && \
            deactivate
        else
            echo "Fehler: Projektverzeichnis nicht gefunden: /path/to/your/vosk-cli-dictation"
        fi
    }
    ```

3.  Übernehmen Sie die Änderungen mit `source ~/.bashrc` oder indem Sie ein neues Terminal öffnen.
4.  Sie können die Anwendung nun von überall starten, indem Sie einfach `vosk` oder `vosk -l en` eingeben.

## Verwendung und Konfiguration

### Sprachauswahl

Das Sprachmodell wird nach folgender Priorität gewählt:

1.  **Kommandozeilenoption (höchste Priorität):** Mit `-l en`, `-l fr`, `-l de` oder `-l es` erzwingen Sie eine bestimmte Sprache für die Sitzung.
2.  **Standardwert in `config.yaml` (Rückfall):** Ohne Option wird der `default_model` aus `config/config.yaml` geladen.

### Sprachauslöser

Jede Sprache hat eine **Weckphrase** und eine **Stopp-Phrase** aus zwei Wörtern (Werkseinstellung: `start dictation` / `stop dictation` im Englischen). Zwei Wörter statt eines, damit ein gewöhnlicher Satz sie nie versehentlich auslöst. Sagen Sie die Weckphrase, um mit dem Diktieren zu beginnen, die Stopp-Phrase, um das Ergebnis abzuschließen und zu kopieren. Wird eine Phrase zweimal hintereinander gesagt (`stop dictation stop dictation`), wird sie wörtlich getippt statt ausgelöst. Wird die Stopp-Phrase mit geringer Erkennungssicherheit gehört, wird sie verschluckt, statt in Ihr Dokument getippt zu werden — wiederholen Sie sie oder verwenden Sie `--finalize`. Die Phrasen sind je Sprache unter `language_settings.<lang>.voice_commands` konfigurierbar.

### Auslösemodi

`interaction.mode` (Standard `toggle`, gegenüber früheren Versionen unverändert) legt fest, wie eine Sitzung beginnt und endet: Eine Geste startet, eine andere beendet. Zwei weitere Modi: `maintenue` (Drücken-zum-Sprechen — das Diktat dauert, solange `hotkeys.push_to_talk` gedrückt bleibt) und `silence` (ein einziges Drücken startet; die Sitzung endet und kopiert sich selbst, sobald `interaction.silence_timeout_ms` ohne Ausgabe des Dekoders vergeht, nachdem ein Wort erfasst wurde). Die gesprochene Stopp-Phrase und `--finalize`/`--cancel` bleiben in jedem Modus als Sicherheitsnetz erhalten. Die vollständige Referenz steht in [`configuration.md`](configuration.md#interaction).

### Eine laufende Sitzung steuern

Die Sitzung öffnet einen privaten Unix-Socket unter `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock` (Modus `0600`). Derselbe **Befehl** mit einer Steueroption verbindet sich mit ihm, führt die Aktion aus, gibt den Zustand aus und beendet sich:

```bash
vosk-cli-dictation --status          # -> OK ÉCOUTE
vosk-cli-dictation --toggle          # Diktat starten/stoppen
vosk-cli-dictation --sleep-toggle    # Ruhemodus betreten/verlassen (gibt das Mikrofon frei)
vosk-cli-dictation --finalize        # anhalten und den angesammelten Text kopieren
vosk-cli-dictation --stop            # die Sitzung beenden
```

Binden Sie diese Befehle an die Tastenkürzel-Einstellungen Ihres Desktops (KDE, GNOME, Sway, labwc…), um eine globale Steuerung zu erhalten, die überall funktioniert, auch in den nativen Wayland-Fenstern, die `pynput` nicht sehen kann. Die `pynput`-Kürzel im Abschnitt `hotkeys` funktionieren ebenfalls als Komfortfunktion nach bestem Bemühen — unter Wayland nur über XWayland-Fenster.

### Manuelle Befehle

Solange das Skript in einem Terminal läuft, können Sie auch diese Befehle eingeben und die Eingabetaste drücken:

*   `/cancel`: Beendet die laufende Aufnahmesitzung, ohne Text auszugeben.
*   `/delete-word`: Löscht das zuletzt getippte Wort.
*   `/nl`: Fügt einen Zeilenumbruch ein (simuliert die Eingabetaste).

### Anpassung

Alle Einstellungen lassen sich in der Datei `config/config.yaml` ändern: Tastenkürzel, Farben der Oberfläche, Sprachauslöser, Typografie je Sprache und Erkennungs-Aliase. Beispiele für korpusspezifische Aliase stehen in `config/config.example.yaml`. Die vollständige Referenz steht in [`configuration.md`](configuration.md).

## Mitwirken

Dieses Projekt ist quelloffen, und Beiträge sind ausdrücklich willkommen! Lesen Sie unseren **[Beitragsleitfaden](../../CONTRIBUTING.md)** und eröffnen Sie gern ein Ticket auf der [Ticket-Seite](https://github.com/RonanDavalan/vosk-cli-dictation/issues).

Dieses Projekt entsteht in einer asymmetrischen Zusammenarbeit von Mensch und LLM — die beteiligten Rollen stehen in [CONTRIBUTORS.md](../../CONTRIBUTORS.md).

## Danksagungen

Dieses Projekt entsteht in einer Zusammenarbeit von Mensch und LLM; die Rollen sind so festgehalten, wie sie tatsächlich ausgeübt wurden. Die vollständige Liste steht in [CONTRIBUTORS.md](../../CONTRIBUTORS.md).

*   **Ronan Davalan** — Architekt und Schiedsrichter: Vision, Sicherheitsanforderungen, Abnahme und Tests.
*   **Claude Code (Anthropic)** — Systemingenieur und Hauptentwickler: Hauptautor des Quellcodes seit v0.5.0-alpha, der Debian-Paketierung und der Werkzeuge.
*   **Gemini (Google)** — Synthetisierer und strategischer Berater.
*   **Grok (xAI)** — Externer Validator.
*   **GLM-5.3** — Prüfer des Interaktionskerns (blindes Kreuz-Audit).
*   **DeepSeek V4 Flash (über OpenCode)** — Prüfer der Dokumentation und der Website, Tester.

## Lizenz

Dieses Projekt steht unter der **MIT-Lizenz**. Einzelheiten stehen in der Datei [LICENSE](../../LICENSE).
