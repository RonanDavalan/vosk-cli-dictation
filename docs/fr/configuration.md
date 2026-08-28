Guide de configuration du projet.

Ce document fournit une explication détaillée de toutes les options disponibles dans le fichier `config/config.yaml`. La configuration correcte de ce fichier est essentielle pour adapter l'application à vos besoins spécifiques, à votre langue et à votre matériel.

Comment la langue est déterminée.

L'application choisit la langue à utiliser en fonction de l'ordre de priorité suivant :

1.  **Argument de ligne de commande (priorité la plus élevée) :** L'utilisation du paramètre `-l` ou `--lang` (par exemple, `python src/main.py -l en`) annulera toujours tous les autres paramètres.

2. **Langue du système (détection automatique) :** Si aucun paramètre n'est spécifié, l'application détecte automatiquement la langue de votre système d'exploitation.

3. **`default_model` Paramétrage (solution de secours) :** Si la langue de votre système ne peut pas être déterminée, l'application utilisera le modèle spécifié dans le paramètre `default_model` comme solution de secours.

## Structure générale de `config.yaml`

Le fichier de configuration est organisé en sections logiques :

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

Sections de configuration détaillées.

### `vosk_models`

Une liste qui définit les modèles de reconnaissance vocale Vosk disponibles.

-   **`name`** (string) : Un nom unique et court pour le modèle (par exemple, `fr`, `en`).
-   **`path_relative`** (string) : Le chemin relatif vers le dossier du modèle Vosk décompressé. Résolu
    par ordre de priorité suivant : `$XDG_DATA_HOME/vosk-models/` (par défaut `~/.local/share/vosk-models/`),
    `/usr/share/vosk-models/`, puis la racine du projet lors de l'exécution à partir d'un dépôt Git ; le premier de ces chemins qui contient réellement le dossier a la priorité. Il peut également être spécifié sous forme de chemin absolu, ce qui a toujours la priorité. Consultez la page de manuel, la section CONFIGURATION, pour connaître la cascade complète.

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

Un modèle qui est déclaré mais qui n'est pas présent sur le disque est signalé au démarrage et ignoré ; le démarrage échoue uniquement si aucun modèle ne peut être chargé.

### `default_model`

The name of the Vosk model to load at startup. Must match a `name` in the `vosk_models` list.

```yaml
default_model: "en"
```

### `control_socket`

Booléen, par défaut `true`. Lorsque cette option est activée, la session en cours écoute sur une socket Unix à `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock` (mode `0600`), ce qui permet aux sous-commandes de contrôle (`--toggle`, `--sleep-toggle`, `--status`, `--stop`, ...) de la piloter. Définissez la valeur sur `false` pour désactiver complètement la socket ; l'outil reste alors utilisable en mode interactif, mais ne peut pas être contrôlé à partir d'un raccourci.

```yaml
control_socket: true
```

### `audio`

Paramètres de votre microphone.

-   **`sample_rate`** (entier) : Le taux d'échantillonnage sur lequel votre modèle a été entraîné (généralement `16000`).
-   **`channels`** (entier) : Nombre de canaux audio (devrait être `1` pour le mono).
-   **`frames_per_buffer`** (entier) : `2048` ou `4096` sont des valeurs courantes.
-   **`buffer_size`** (entier) : La taille du tampon audio.
-   **`queue_max_chunks`** (entier) : Profondeur maximale de la file d'attente audio, en blocs de `buffer_size`.  `16` ≈ 2 secondes. Lorsqu'il y a un retard dans la reconnaissance, le bloc le plus ancien est supprimé plutôt que de laisser le délai s'accumuler ; un compteur de débordement est affiché dans `--status` et `--diagnose`.

```yaml
audio:
  sample_rate: 16000
  channels: 1
  frames_per_buffer: 4096
  buffer_size: 2048
  queue_max_chunks: 16
```

### `recognition`

Paramètres pour le moteur de reconnaissance Vosk.

-   **`confidence_threshold`** (float, 0.0-1.0, valeur par défaut `0.55`) : une phrase de déclenchement vocal (d'activation ou d'arrêt) n'est prise en compte que lorsque la confiance moyenne de ses mots atteint cette valeur. En dessous, une phrase d'activation est traitée comme du texte ordinaire ; une phrase d'**arrêt** est absorbée — ni exécutée, ni écrite dans le document — et un indice est affiché. Surchargeable par langue avec une clé du même nom sous `language_settings.<lang>`.
-   **`restricted_grammar_in_listening`** (booléen, valeur par défaut `true`): Pendant l'écoute de la phrase d'activation, utilisez une grammaire Kaldi restreinte à cette phrase. La consommation du processeur est considérablement réduite, mais cela se fait au prix de la reconstruction complète du reconnaisseur lors de l'activation. Définissez sur `false` pour maintenir le reconnaisseur complet en état d'écoute. Surchargeable par langue sous `language_settings.<lang>` — la config par défaut la désactive pour `es`, où le petit modèle décode la grammaire restreinte plus lentement que la grammaire complète.
-   **`restricted_stop_in_dictation`** (booléen, valeur par défaut `true`): pendant la dictée, exécute un second reconnaisseur léger restreint à la phrase d'arrêt, en parallèle du reconnaisseur complet. Il fournit un signal d'arrêt de haute confiance indépendant de `confidence_threshold` — le même mécanisme que celui utilisé pour la phrase d'activation pendant l'écoute. Surchargeable par langue sous `language_settings.<lang>` ; mettez `false` sur un matériel où le décodage restreint supplémentaire par bloc audio est trop coûteux (il est environ 5× moins cher que le décodage complet).

```yaml
recognition:
  confidence_threshold: 0.55
  restricted_grammar_in_listening: true
  restricted_stop_in_dictation: true
```

### `sleep`

-   **`releases_device`** (booléen, valeur par défaut `true`): lorsque l'appareil est en mode veille, fermez le flux audio pour libérer complètement le microphone (sa LED s'éteint) et permettre à un autre programme de l'utiliser. La réouverture prend environ 200 ms. Définissez sur `false` pour simplement arrêter le flux sans le fermer : l'appareil reste "claimé", mais le réveil est légèrement plus rapide.

```yaml
sleep:
  releases_device: true
```

### `clipboard`

Le texte est injecté en le plaçant dans le presse-papiers et en simulant un copier-coller.

-   **`restore`** (booléen, par défaut `true`): restaure le contenu précédent du presse-papiers de l'utilisateur après le collage. Un contenu du presse-papiers non textuel (par exemple, une image) n'est jamais enregistré ni écrasé. Peut également être désactivé pour chaque exécution avec `--no-clipboard-restore`.
-   **`restore_delay_ms`** (entier, par défaut `250`): délai avant de restaurer, pour permettre à l'application cible de lire le résultat du collage.
-   **`confirm_timeout_ms`** (entier, par défaut `500`): temps maximum d'attente pour confirmer que le presse-papiers contient bien notre texte avant d'envoyer la frappe de touche pour le collage.

```yaml
clipboard:
  restore: true
  restore_delay_ms: 250
  confirm_timeout_ms: 500
```

### `injection`

-   **`paste_combo`** (chaîne, valeur par défaut `ctrl+v`) et **`terminal_paste_combo`** (valeur par défaut `ctrl+shift+v`): la combinaison de touches utilisée pour coller. Sous X11, la classe de fenêtre de la fenêtre active est vérifiée par rapport à `terminal_window_classes` pour sélectionner automatiquement la bonne ; sous Wayland, il n'y a pas d'API pour la fenêtre active, donc `paste_combo` est utilisé, sauf si vous la remplacez.
-   **`terminal_window_classes`** (liste): classes de fenêtres traitées comme des terminaux (uniquement pour X11).
-   **`ydotool_keycodes`** (mapping): codes de touches physiques de Linux, utilisés uniquement dans le chemin de secours `ydotool`. Remplacez ces valeurs si vous utilisez une disposition autre que QWERTY et que ce chemin de secours est effectivement utilisé ; le chemin Wayland nominal (`wtype`) fonctionne par keysym et est indépendant de la disposition.

```yaml
injection:
  paste_combo: "ctrl+v"
  terminal_paste_combo: "ctrl+shift+v"
  terminal_window_classes: ["konsole", "gnome-terminal-server", "xterm", "st", "alacritty", "kitty", "foot"]
  ydotool_keycodes: {}
```

### `language_settings`

Cette section contient des paramètres spécifiques à une langue. La configuration par défaut comprend quatre options : `en`, `fr`, `de`, `es`.

-   **`voice_commands`**: les deux mots `wake_phrase` et `stop_phrase` pour cette langue. Deux mots de sorte qu'une phrase ordinaire ne les déclenche jamais. (Les anciennes clés à un seul mot `start_word` / `stop_word` sont toujours lues si elles sont présentes, pour assurer la compatibilité descendante.)
-   **`punctuation`**: Un dictionnaire pour insérer automatiquement la ponctuation, organisé en groupes logiques. Les caractères `¿` et `¡` espagnols ne sont insérés que par des commandes explicites (`"abrir interrogación"`, `"abrir exclamación"`), et jamais automatiquement.
-   **`typography`**: règles de sortie spécifiques à chaque langue — voir ci-dessous.
-   **`recognition_aliases`**: Corrige les erreurs de reconnaissance courantes provenant de Vosk. Le tableau fourni contient uniquement des corrections génériques et non controversées (par exemple, `"de points": "deux points"`); les corrections spécifiques au corpus se trouvent dans `config/config.example.yaml`, à copier et à adapter.
-   **`custom_vocabulary`**: Un dictionnaire pour les corrections sensibles à la casse, appliquées après les alias (par exemple, `"ia": "IA"`).

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

Remplace une branche française codée en dur. Pour chaque langue :

-   **`thin_space`** (booléen) : insère un espace insécable étroit (U+202F) avant les symboles listés dans `space_before`. Utilisez `true` pour le français, et `false` ailleurs. Désactivez cette option si l'espace étroit perturbe `grep` ou votre terminal.
-   **`space_before`** (liste) : symboles qui nécessitent un séparateur initial (un espace étroit lorsque `thin_space`, sinon un espace simple). Vide pour l'anglais, l'allemand et l'espagnol.
-   **`space_after`** (liste) : symboles suivis d'un espace.
-   **`capitalize_sentence_start`** (booléen) : met en majuscule le premier mot de chaque phrase. En allemand, seules les phrases commencent par une majuscule ; les noms communs restent tels quels, car une capitalisation fiable des noms nécessiterait un analyseur morphologique.
-   **`quote_open`** / **`quote_close`** : guillemets ouvrants et fermants (utilisez `« »` pour le français, `„ "` pour l'allemand).

### `hotkeys`

Raccourcis clavier globaux via `pynput`. Ceux-ci ne fonctionnent que dans une session X11 simple, et même là l'écouteur `pynput` ne consomme pas l'événement clavier : la combinaison atteint aussi la fenêtre active, donc l'utiliser alors que le curseur est dans un terminal insère une séquence d'échappement (`^[s` pour `Alt+S`). Pour un arrêt propre depuis n'importe quelle fenêtre — et pour Wayland natif, où `pynput` ne voit rien — associez plutôt les sous-commandes de contrôle (`--toggle`, `--finalize`, `--sleep-toggle`) aux propres paramètres de raccourcis de votre bureau.

-   **`pynput_enabled`** (booléen, par défaut `true`): activé uniquement sous X11. Définissez-le sur `false` pour empêcher le démarrage du service d'écoute `pynput`.
-   **`pynput_keys`**: Une liste de touches Pynput pour le raccourci.
-   **`display_name`**: Une chaîne de caractères affichée dans le message d'aide.

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

-   **`toggle_recording`** (par défaut `Alt+H`): démarre ou met en pause la dictée en cours.
    Pendant la pause, le microphone reste actif et la phrase de réveil vocale continue de fonctionner.
-   **`finalize_session`** (par défaut `Alt+S`): arrête la dictée et copie le texte accumulé
    dans le presse-papiers. X11 uniquement, et la combinaison fuit dans la fenêtre active
    (voir ci-dessus) — préférez `vosk-cli-dictation --finalize` lié à un raccourci de bureau.
-   **`sleep_toggle`** (par défaut `Alt+W`): active/désactive le **mode veille**, un troisième état
    distinct des deux précédents. En mode veille, le flux audio est fermé (le microphone est libéré) et
    la reconnaissance est bloquée, ce qui réduit l'utilisation du processeur à presque zéro. Cependant,
    la phrase de réveil ne peut pas être détectée tant que le mode veille n'est pas désactivé. Seul le
    raccourci clavier `Alt+W` lui-même continue de fonctionner, car il ne dépend pas de l'audio.
    L'activation du mode veille pendant une dictée en cours l'arrête proprement (comme si `Alt+H` avait
    été pressé), de sorte qu'aucun audio n'est perdu au milieu d'une phrase.

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
