# How to Translate the Project

Thank you for your interest in making this project accessible to more people! Translating the interface is one of the most valuable ways to contribute.

This guide will walk you through the process of adding a new language or improving an existing one.

## Translation Workflow Overview

The project uses the standard `gettext` system for internationalization. The process is as follows:
1.  **Extract:** Source strings (in English) are extracted from the Python code into a template file (`messages.pot`).
2.  **Update:** This template is used to update individual language files (`messages.po`).
3.  **Translate:** You edit your language's `.po` file to provide translations.
4.  **Compile:** The human-readable `.po` file is compiled into a machine-readable `.mo` file that the application uses.

A helper script, `manage_translations.sh`, automates most of these steps for you.

## Adding or Improving a Translation

### Prerequisites

-   A local clone of the project repository.
-   The project's virtual environment set up (see `README.md`).
-   A text editor that supports UTF-8 encoding (like VS Code, Kate, Gedit, etc.).

### Step 1: Prepare Your Language File

First, find your language's two-letter code (e.g., `es` for Spanish, `de` for German, `it` for Italian).

**If you are improving an existing language (e.g., French `fr`):**
All you need to do is ensure your local files are up-to-date. Run the update command:
```bash
./manage_translations.sh update 
```

This will add any new English strings from the source code to your language's `.po` file.

**If you are adding a NEW language:**
1.  Activate the virtual environment: `source vosk-env/bin/activate`
2.  Use the `pybabel init` command to create a new `.po` file for your language. Replace `[lang]` with your language code (e.g., `es`):
    ```bash
    pybabel init -i locales/messages.pot -d locales -l [lang]
    ```
    This creates a new folder and file, for example: `locales/es/LC_MESSAGES/messages.po`.

### Step 2: Translate the Messages

1.  Open your language's `.po` file located at `locales/[lang]/LC_MESSAGES/messages.po`.
2.  You will see blocks of text like this:

    ```po
    #: src/main.py:34
    msgid "Checking external dependencies..."
    msgstr ""
    ```
3.  Your task is to fill in the `msgstr` line with the correct translation for the `msgid` line above it.

    ```po
    #: src/main.py:34
    msgid "Checking external dependencies..."
    msgstr "Vérification des dépendances externes..."
    ```
4.  **Important Notes:**
    *   If you see placeholders like `{model_name}`, make sure to include them in your translation as well. Example:
        ```po
        msgid "Model '{model_name}' is already loaded."
        msgstr "Le modèle '{model_name}' est déjà chargé."
        ```
    *   Preserve special characters like `\n` (newline).
    *   Save the file with UTF-8 encoding.

### Step 3: Compile and Test Your Translation

Once you have finished translating, you need to compile your `.po` file into a `.mo` file.

1.  Run the compile command from the project root:
    ```bash
    ./manage_translations.sh compile
    ```
2.  Now, you can test your changes by running the application and forcing your language:
    ```bash
    python src/main.py --lang [lang]
    ```
    You should see your translated messages in the console.

### Step 4: Submit Your Contribution

Once you are happy with your translation, please submit it via a Pull Request on GitHub so everyone can benefit from your work!

1.  Commit your changes to the `.po` file.
    ```bash
    git add locales/[lang]/LC_MESSAGES/messages.po
    git commit -m "i18n: add/update [Language Name] translation"
    ```
    (e.g., `i18n: add Spanish translation`)
2.  Push your branch and open a Pull Request.

Thank you again for your contribution!

