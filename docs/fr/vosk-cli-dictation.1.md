% VOSK-CLI-DICTATION(1) vosk-cli-dictation | Commandes utilisateur
% Ronan Davalan
% 2026-08-26

# NOM

vosk-cli-dictation - dictée vocale hors ligne, système complet, pour la ligne de commande.

# SYNOPSIS

**vosk-cli-dictation** [**-l** *LANG* | **--lang** *LANG*]

# DESCRIPTION

**vosk-cli-dictation** est un outil de dictée en ligne de commande pour Linux, qui utilise le moteur de reconnaissance vocale hors ligne Vosk. Il écoute en continu via le microphone et tape le texte reconnu directement dans l'application qui a actuellement le focus du clavier (terminal, navigateur, éditeur ou toute autre fenêtre), ce qui lui permet d'être utilisé à l'échelle du système, plutôt que dans un seul programme.

La reconnaissance vocale s'effectue entièrement localement : aucun audio ni aucun texte transcrit n'est jamais envoyé à un service distant.

La dictée peut être démarrée et arrêtée soit par la voix (un mot de réveil et un mot d'arrêt configurables), soit par des touches de raccourci globales, et peut également être mise en veille pour suspendre complètement la capture audio et la reconnaissance lorsque cela n'est pas nécessaire, sans pour autant fermer le programme.

La simulation de texte est effectuée via **ydotool**, si disponible, ou **xdotool** comme solution de secours. **ydotool** prend en charge à la fois Wayland et X11 via l'interface `/dev/uinput` ; **xdotool** prend en charge uniquement X11 (ou Wayland via XWayland). Au moins l'un des deux doit être installé.

# OPTIONS

**-l** *LANG*, **\--lang** *LANG*
:   Force la langue de l'interface et de la reconnaissance vocale pour cette session
    (par exemple `en` ou `fr`), en remplaçant la valeur de `default_model`
    provenant du fichier de configuration. *LANG* doit correspondre au nom
    d'un des modèles déclarés dans la section `vosk_models` du fichier de configuration.

# COMMANDES VOCALES

Le mot de réveil et le mot d'arrêt sont configurables par langue. Avec la configuration par défaut :

Anglais
:   Dites **« start »** pour commencer à dicter, **« oops »** pour arrêter et
    copier le résultat dans le presse-papiers.

Français
:   Dites **« démarre »** pour commencer à dicter, **« zut »** pour arrêter et
    copier le résultat dans le presse-papiers.

La ponctuation et la mise en forme sont également dictées par la voix ; la liste complète, par langue, est définie dans `language_settings.<lang>.punctuation` dans le fichier de configuration, et est affichée par le programme au démarrage.

# TOUCHE RAPIDE

Les touches de raccourci globales fonctionnent quel que soit le programme qui a le focus. La configuration par défaut définit :

**Alt+H**
:   Active ou désactive la dictée. Bascule seulement une pause/reprise ; ne copie **jamais**
    dans le presse-papiers, contrairement à **Alt+S** et au mot d'arrêt ci-dessous. Pendant
    la pause, le microphone reste actif et le mot de réveil vocal fonctionne toujours.

**Alt+S**
:   Arrête la dictée en cours et copie le texte accumulé dans le presse-papiers — équivalent
    au mot d'arrêt.

**Alt+W**
:   Active/désactive le mode veille, un troisième état distinct des deux précédents. En mode veille, l'acquisition audio et la reconnaissance vocale sont complètement suspendues - l'utilisation du processeur diminue presque à zéro - mais le mot de réveil vocal ne peut être détecté tant que le mode veille n'est pas désactivé. Le raccourci clavier **Alt+W** lui-même continue de fonctionner en mode veille, car il ne dépend pas de l'audio. L'activation du mode veille pendant une dictée la stoppe proprement, ce qui évite toute perte de données au milieu d'une phrase.

**Ctrl+C**
:   Quitter le programme.

Les trois premiers raccourcis clavier peuvent être configurés dans la section `hotkeys` du fichier de configuration. **Ctrl+C** ne l'est pas : c'est le signal d'interruption standard, toujours actif, jamais reconfigurable.

# COMMANDES MANUELLES

Pendant l'exécution du programme, la saisie de l'une des commandes suivantes dans sa fenêtre de terminal, suivie de la touche Entrée, permet également de le contrôler.

**/cancel**
:   Arrête la session d'enregistrement en cours sans afficher de texte.

**/delete-word**
:   Supprime le dernier mot saisi.

**/nl**
:   Insérer une nouvelle ligne (simule l'appui sur la touche Entrée).

# CONFIGURATION

Le comportement au moment de l'exécution est contrôlé par un fichier de configuration YAML : il définit les modèles de reconnaissance vocale disponibles, les paramètres audio, le seuil de confiance de la reconnaissance, les commandes vocales et la ponctuation spécifiques à chaque langue, les touches de raccourci, le son de notification et le thème de couleur de la console.

Le fichier de configuration est localisé en fonction de la première règle correspondante ci-dessous ; une fois qu'une règle est trouvée, les règles restantes ne sont pas consultées.

1. Le chemin spécifié dans la variable d'environnement **VOSK_CONFIG**, si elle est définie. Utilisé tel quel ; jamais créé automatiquement.
2. `config/config.yaml`, par rapport au répertoire du projet, lors de l'exécution
   depuis une branche Git (mode développement).
3. `$XDG_CONFIG_HOME/vosk-cli-dictation/config.yaml` (par défaut
   `~/.config/vosk-cli-dictation/config.yaml`). Créé automatiquement lors de la première exécution, à partir du modèle par défaut, lorsque installé depuis le paquet Debian.
4. Le modèle par défaut fourni par le paquet, en lecture seule.

La langue active est choisie, dans l'ordre suivant : l'**\--lang** option, si elle est spécifiée ;
sinon, la langue détectée par le système d'exploitation ; sinon, la
valeur **`default_model`** provenant du fichier de configuration.

Consultez **configuration.md** dans la documentation du projet pour obtenir la liste complète de toutes les clés de configuration.

# FICHIERS

`~/.config/vosk-cli-dictation/config.yaml`
:   Fichier de configuration par utilisateur (installation du paquet Debian).

`/usr/share/vosk-cli-dictation/config.yaml`
:   Modèle de configuration d'usine (installation du paquet Debian), en lecture seule.

`~/.local/share/vosk-models/`
:   Emplacement par défaut où les modèles acoustiques de Vosk sont recherchés (installation du paquet Debian).

`config/config.yaml`
:   Fichier de configuration utilisé lors de l'exécution à partir d'un dépôt Git.

`vosk-model/`
:   Emplacement par défaut où les modèles acoustiques de Vosk sont recherchés lorsqu'ils sont utilisés à partir d'une branche Git.

# CODE DE SORTIE

**0**
:   Le programme s'est terminé correctement, y compris après l'utilisation de **Ctrl+C**.

Non nul
:   Lancement échoué : ni **ydotool** ni **xdotool** ne sont disponibles, aucun modèle de reconnaissance vocale n'a pu être chargé, ou le périphérique audio n'a pas pu être ouvert.

# EXEMPLES

Démarrer avec la langue par défaut du fichier de configuration :

```
vosk-cli-dictation
```

Forcez l'anglais pour cette session.

```
vosk-cli-dictation --lang en
```

# VOIR ÉGALEMENT

Modèles et téléchargements de Vosk : *https://alphacephei.com/vosk/models*

Page d'accueil du projet : *https://vosk.davalan.fr/*

# BUGS

Signalez les problèmes sur le système de suivi des problèmes du projet :
*https://github.com/RonanDavalan/vosk-cli-dictation/issues*

# AUTEUR

Ronan Davalan, et les contributeurs mentionnés dans CONTRIBUTORS.md.
