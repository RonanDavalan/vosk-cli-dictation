# Wie man das Projekt übersetzt

Vielen Dank für Ihr Interesse, dieses Projekt für mehr Menschen zugänglich zu machen! Das Übersetzen der Benutzeroberfläche ist eine der wertvollsten Möglichkeiten, einen Beitrag zu leisten.

Dieser Leitfaden führt Sie durch den Prozess des Hinzufügens einer neuen Sprache oder der Verbesserung einer bestehenden Sprache.

## Übersichtsartikel zum Übersetzungsprozess

Das Projekt verwendet das Standard-`gettext` System für die Internationalisierung. Der Prozess ist wie folgt:
1.  **Extrahieren:** Quelltexte (in Englisch) werden aus dem Python-Code in eine Vorlagendatei (`messages.pot`) extrahiert.
2.  **Aktualisieren:** Diese Vorlage wird verwendet, um einzelne Sprachdateien (`messages.po`) zu aktualisieren.
3.  **Übersetzen:** Sie bearbeiten Ihre Sprach-`.po` Datei, um Übersetzungen bereitzustellen.
4.  **Kompilieren:** Die für Menschen lesbare `.po` Datei wird in eine für Maschinen lesbare `.mo` Datei kompiliert, die von der Anwendung verwendet wird.

Ein Hilfsskript, `manage_translations.sh`, automatisiert die meisten dieser Schritte für Sie.

## Übersetzen oder eine Übersetzung verbessern

### Voraussetzungen

-   Ein lokales Klond des Projekt-Repositories.
-   Die für das Projekt eingerichtete virtuelle Umgebung (siehe `README.md`).
-   Ein Texteditor, der UTF-8-Kodierung unterstützt (z. B. VS Code, Kate, Gedit usw.).

### Schritt 1: Bereiten Sie Ihre Sprachdatei vor.

Zuerst finden Sie den zweistelligen Code Ihrer Sprache (z. B. `es` für Spanisch, `de` für Deutsch, `it` für Italienisch).

**Wenn Sie eine bestehende Sprache verbessern (z. B. Französisch `fr`):**
Sie müssen lediglich sicherstellen, dass Ihre lokalen Dateien auf dem neuesten Stand sind. Führen Sie den Aktualisierungsbefehl aus:

```bash
./manage_translations.sh update 
```

Dies fügt alle neuen englischen Zeichenketten aus dem Quellcode zu Ihrer Sprachdatei `.po` hinzu.

**Wenn Sie eine NEUE Sprache hinzufügen:**
1.  Aktivieren Sie die virtuelle Umgebung: `source vosk-env/bin/activate`
2.  Verwenden Sie den `pybabel init` Befehl, um eine neue `.po` Datei für Ihre Sprache zu erstellen. Ersetzen Sie `[lang]` durch Ihren Sprachcode (z.B. `es`):

    ```bash
    pybabel init -i locales/messages.pot -d locales -l [lang]
    ```

Dies erstellt einen neuen Ordner und eine neue Datei, zum Beispiel: `locales/es/LC_MESSAGES/messages.po`.

### Schritt 2: Übersetzen Sie die Nachrichten.

1.  Öffnen Sie die `.po` Datei Ihrer Sprache, die sich unter `locales/[lang]/LC_MESSAGES/messages.po` befindet.
2.  Sie werden Textblöcke sehen, die wie dieser aussehen:

    ```po
    #: src/main.py:34
    msgid "Checking external dependencies..."
    msgstr ""
    ```

3.  Ihre Aufgabe ist es, die `msgstr` Zeile mit der korrekten Übersetzung für die `msgid` Zeile oben zu füllen.

    ```po
    #: src/main.py:34
    msgid "Checking external dependencies..."
    msgstr "Vérification des dépendances externes..."
    ```

4.  **Wichtige Hinweise:**
    *   Wenn Sie Platzhalter wie `{model_name}` sehen, stellen Sie sicher, dass Sie diese auch in Ihre Übersetzung einfügen. Beispiel:

        ```po
        msgid "Model '{model_name}' is already loaded."
        msgstr "Le modèle '{model_name}' est déjà chargé."
        ```

*   Behalten Sie Sonderzeichen wie `\n` (Zeilenumbruch) bei.
*   Speichern Sie die Datei mit UTF-8-Kodierung.

### Schritt 3: Kompilieren und Testen Sie Ihre Übersetzung.

Sobald Sie die Übersetzung abgeschlossen haben, müssen Sie Ihre `.po` Datei in eine `.mo` Datei kompilieren.

Führen Sie den Kompilierungsbefehl vom Projektstammverzeichnis aus:

    ```bash
    ./manage_translations.sh compile
    ```

2. Jetzt können Sie Ihre Änderungen testen, indem Sie die Anwendung ausführen und Ihre bevorzugte Sprache erzwingen:

    ```bash
    python src/main.py --lang [lang]
    ```

Sie sollten Ihre übersetzten Nachrichten in der Konsole sehen.

### Schritt 4: Senden Sie Ihren Beitrag.

Sobald Sie mit Ihrer Übersetzung zufrieden sind, reichen Sie diese bitte über einen Pull Request auf GitHub ein, damit jeder davon profitieren kann!

Speichern Sie Ihre Änderungen in der `.po` Datei.

    ```bash
    git add locales/[lang]/LC_MESSAGES/messages.po
    git commit -m "i18n: add/update [Language Name] translation"
    ```

    (e.g., `i18n: add Spanish translation`)
2.  Push your branch and open a Pull Request.

Vielen Dank noch einmal für Ihren Beitrag!
