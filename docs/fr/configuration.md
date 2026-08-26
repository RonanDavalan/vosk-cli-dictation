Guide de configuration du projet.

Ce document fournit une explication détaillée de toutes les options disponibles dans le fichier `config/config.yaml`. La configuration correcte de ce fichier est essentielle pour adapter l'application à vos besoins spécifiques, à votre langue et à votre matériel.

Comment la langue est déterminée.

L'application choisit la langue à utiliser en fonction de l'ordre de priorité suivant :

1.  **Argument en ligne de commande (priorité la plus élevée) :** L'utilisation de l'indicateur `-l` ou `--lang` (par exemple, `python src/main.py -l en`) remplacera toujours tous les autres paramètres.

2. **Langue du système (détection automatique) :** Si aucun paramètre n'est fourni, l'application détecte automatiquement la langue de votre système d'exploitation.

3. **`default_model` Paramètre (solution de repli) :** Si la langue de votre système ne peut pas être déterminée, l'application utilisera le modèle spécifié dans le paramètre `default_model` comme solution de repli finale.

## Structure générale de `config.yaml`

Le fichier de configuration est organisé en sections logiques :

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

Sections de configuration détaillées.

### `vosk_models`

Une liste qui définit les modèles de reconnaissance vocale Vosk disponibles.

-   **`name`** (chaîne de caractères) : Un nom unique et court pour le modèle (par exemple, `fr`, `en`).
-   **`path_relative`** (chaîne de caractères) : Le chemin relatif vers le dossier du modèle Vosk décompressé. Résolu, dans l'ordre, contre `$XDG_DATA_HOME/vosk-models/` (par défaut `~/.local/share/vosk-models/`), `/usr/share/vosk-models/`, puis la racine du projet lors d'une exécution depuis un dépôt Git — le premier de ces répertoires qui contient réellement le dossier l'emporte. Peut aussi être donné en chemin absolu, qui prime toujours. Voir la manpage, section CONFIGURATION, pour la cascade complète.

```yaml
vosk_models:
  - name: "en"
    path_relative: "vosk-model/vosk-model-small-en-us-0.15"
  - name: "fr"
    path_relative: "vosk-model/vosk-model-small-fr-0.22"
```

### `default_model`

Le nom du modèle Vosk à charger au démarrage. Doit correspondre à un `name` dans la liste `vosk_models`.

```yaml
default_model: "en"
```

### `audio`

Paramètres de votre microphone.

-   **`sample_rate`** (entier) : Le taux d'échantillonnage utilisé pour l'entraînement de votre modèle (généralement `16000`).
-   **`channels`** (entier) : Nombre de canaux audio (devrait être `1` pour le mono).
-   **`frames_per_buffer`** (entier) : `2048` ou `4096` sont des valeurs courantes.
-   **`buffer_size`** (entier) : La taille du tampon audio.

```yaml
audio:
  sample_rate: 16000
  channels: 1
  frames_per_buffer: 4096
  buffer_size: 2048
```

### `recognition`

Paramètres du moteur de reconnaissance Vosk.

-   **`confidence_threshold`** (flottant, 0,0-1,0) : Les mots dont le score de confiance est inférieur à cette valeur seront ignorés.

```yaml
recognition:
  confidence_threshold: 0.85
```

### `language_settings`

Cette section contient des paramètres spécifiques à une langue.

-   **`voice_commands`**: Mots-clés pour contrôler l'application.
-   **`punctuation`**: Un dictionnaire pour insérer automatiquement la ponctuation. Il est organisé en groupes logiques pour plus de clarté.
-   **`recognition_aliases`**: Corrige les erreurs de reconnaissance courantes de Vosk (par exemple, `"sauna": "sonna"`).
-   **`custom_vocabulary`**: Un dictionnaire pour les corrections sensibles à la casse, appliquées après les alias (par exemple, `"ia": "IA"`).

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

Raccourcis clavier globaux pour contrôler l'application.

-   **`pynput_keys`**: Une liste de touches Pynput pour le raccourci.
-   **`display_name`**: Une chaîne de caractères affichée dans le message d'aide.

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

-   **`toggle_recording`** (par défaut `Alt+H`): démarre ou met en pause la dictée en cours.
    Pendant la pause, le microphone reste actif et le mot de réveil vocal fonctionne toujours.
-   **`finalize_session`** (par défaut `Alt+S`): arrête la dictée et copie le texte accumulé
    dans le presse-papiers.
-   **`sleep_toggle`** (par défaut `Alt+W`): active/désactive le **mode veille**, un troisième état distinct
    des deux précédents. En mode veille, la capture audio et la reconnaissance vocale sont complètement
    suspendues — la consommation de CPU du moteur de reconnaissance diminue considérablement (proche de zéro) —
    mais cela signifie également que le mot de réveil vocal (`start_word`) ne peut pas être entendu
    tant que le mode veille n'est pas désactivé. Seul le raccourci clavier
    `Alt+W` lui-même continue de fonctionner en mode veille, car il ne dépend pas de l'audio.
    L'activation du mode veille pendant une dictée en cours l'arrête proprement (comme si
    `Alt+H` avait été pressé), de sorte qu'aucun audio n'est perdu au milieu d'une phrase.

    ```bash
    # How to test / how to run
    cd ~/git/vosk-cli-dictation/vosk-cli-dictation
    source vosk-env/bin/activate
    python3 src/main.py
    # Alt+W toggles sleep mode; Alt+H toggles dictation; Alt+S finalizes and copies.
    ```

### `sound_file`

Le chemin absolu vers un fichier de son de notification (par exemple, `.oga`, `.wav`).

```yaml
sound_file: "/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga"
```

### `theme`

Cette section vous permet de personnaliser les couleurs de l'application dans la console. Les valeurs doivent être des noms de couleurs valides `colorama` (par exemple, `GREEN`, `RED`, `BLUE`).

-   **`ready_message`**: Couleur du message "Le script est prêt".
-   **`help_text`**: Couleur principale pour le bloc du message d'aide.
-   **`help_title`**: Couleur pour les titres dans le message d'aide.
-   **`info`**, **`success`**, **`warning`**, **`error`**: Couleurs pour les messages de statut.

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
