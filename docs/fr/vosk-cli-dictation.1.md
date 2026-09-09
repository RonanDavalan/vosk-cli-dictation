% VOSK-CLI-DICTATION(1) vosk-cli-dictation | Commandes utilisateur
% Ronan Davalan
% 2026-08-28

# NOM

vosk-cli-dictation - dictée vocale hors ligne, disponible pour tout le système, pour la ligne de commande.

# SYNOPSIS

**vosk-cli-dictation** [**-l** *LANG* | **--lang** *LANG*]

vosk-cli-dictation **\--diagnose**

vosk-cli-dictation **\--download-model** [*LANG*]

vosk-cli-dictation {**\--status** | **\--toggle** | **\--dictation-on** | **\--dictation-off** | **\--finalize** | **\--cancel** | **\--sleep** | **\--wake** | **\--sleep-toggle** | **\--stop**}

# DESCRIPTION

**vosk-cli-dictation** est un outil de dictée en ligne de commande pour Linux, qui utilise le moteur de reconnaissance vocale hors ligne Vosk. Il écoute en continu via le microphone et tape le texte reconnu directement dans l'application qui a actuellement le focus du clavier (terminal, navigateur, éditeur ou toute autre fenêtre), ce qui lui permet d'être utilisé à l'échelle du système plutôt qu'à l'intérieur d'un seul programme.

La reconnaissance vocale s'effectue entièrement localement : aucun audio ni aucun texte transcrit n'est jamais envoyé à un service distant.

La dictée peut être démarrée et arrêtée soit par la voix (à l'aide d'une phrase d'activation et d'une phrase d'arrêt configurables, spécifiques à chaque langue), soit par des sous-commandes qui peuvent être associées à un raccourci clavier, et peut également être mise en veille pour libérer complètement le microphone et suspendre la reconnaissance lorsqu'elle n'est pas nécessaire, sans pour autant quitter le programme.

Une seule session s'exécute par utilisateur à la fois. Elle ouvre une socket Unix privée à
`$XDG_RUNTIME_DIR/vosk-cli-dictation.sock` (en mode `0600`); la même commande
utilisée avec un indicateur de contrôle (voir GÉRER UNE SESSION EN COURS) se connecte
à cette socket au lieu de démarrer une nouvelle session.

Sous Wayland, cela utilise **wtype** et **wl-clipboard**, avec une solution de repli vers **ydotool** (qui nécessite le démon `ydotoold` et un accès à `/dev/uinput`). Sous X11, cela utilise **xdotool**. Au moins un backend pour le type de session actuel doit être installé. L'ajout de votre utilisateur au groupe `input` n'est nécessaire que pour le repli **ydotool** ; **wtype** et **xdotool** n'en ont pas besoin. **vosk-cli-dictation \--diagnose** indique quels outils, quel périphérique audio et quel accès au presse-papiers sont disponibles, puis se termine.

Les raccourcis globaux via `pynput` observent le serveur X : sous Wayland ils
n'atteignent que les fenêtres passant par XWayland, jamais une fenêtre Wayland
native active. Associez les sous-commandes de contrôle aux paramètres de
raccourcis de votre environnement de bureau pour un contrôle qui marche partout.

# OPTIONS

**-l** *LANG*, **\--lang** *LANG*
:   Force la langue de l'interface et de la reconnaissance vocale pour cette session
    (`en`, `fr`, `de` ou `es`), en remplaçant la valeur de `default_model`
    depuis le fichier de configuration. *LANG* doit correspondre au nom d'un des
    modèles déclarés sous `vosk_models` dans le fichier de configuration.

**\--diagnose**
:   Vérifiez l'environnement (type de session, backend d'injection, outils, modèles,
    entrée audio, presse-papiers, socket de contrôle) et quittez. Le code de sortie est `0`
    lorsque toutes les vérifications sont réussies.

**\--download-model** [*LANG*]
:   Télécharge le petit modèle Vosk pour *LANG* (ou la langue courante si
    l'argument est omis) dans `~/.local/share/vosk-models/`, en vérifiant sa
    somme de contrôle, puis se termine. Un modèle est également proposé de
    façon interactive au premier lancement si aucun n'est installé.

# GESTION D'UNE SESSION EN COURS

Chacun des drapeaux suivants se connecte à la socket de la session en cours,
effectue l'action, affiche l'état résultant (`OK DICTÉE`,
`OK ÉCOUTE`, `OK VEILLE`) ou `ERR <reason>`, puis se termine. Ils sont destinés à être
associés à des raccourcis clavier de bureau.

**\--status**
:   Afficher l'état actuel sans le modifier.

**--toggle**
:   Alterner entre la dictée (DICTÉE) et l'écoute (ÉCOUTE).

**\--dictation-on**, **\--dictation-off**
:   Activer ou désactiver la dictée vocale.

**\--finalize**
:   Arrêtez la dictée et copiez le texte accumulé — équivalent à la phrase de fin.

**\--cancel**
:   Supprimer le tampon de session actuel sans taper quoi que ce soit.

**\--sleep**, **\--wake**, **\--sleep-toggle**
:   Activer, désactiver ou basculer le mode veille (VEILLE).

**\--stop**
:   Fermez proprement la session en cours.

# COMMANDES VOCALES

La phrase de veille et la phrase d'arrêt sont constituées de deux mots chacune et sont configurables pour chaque langue dans `language_settings.<lang>.voice_commands`. Deux mots plutôt qu'un seul afin qu'une phrase ordinaire ne les déclenche pas. Avec la configuration par défaut :

Dites "**démarrer la dictée**" pour commencer, "**arrêter la dictée**" pour terminer, et copiez le résultat dans le presse-papiers.

"active la dictée" / "arrêter la dictée".

"démarrer le dictée" / "arrêter le dictée".

:   **"commencer l'enregistrement"** / **"arrêter l'enregistrement"**.

Une phrase de déclenchement n'est activée que lorsque la moyenne de la confiance de reconnaissance de ses mots dépasse `recognition.confidence_threshold` (valeur par défaut `0.55`, surchargeable par langue). Une phrase d'arrêt entendue sous le seuil est absorbée — ni exécutée, ni écrite dans le document — et un indice est affiché ; répétez-la, ou utilisez `--finalize`. Pendant la dictée, un second reconnaisseur léger restreint à la phrase d'arrêt fournit un arrêt de haute confiance indépendant de ce seuil (`recognition.restricted_stop_in_dictation`, actif par défaut, surchargeable par langue). Prononcer une phrase deux fois de suite la transcrit littéralement plutôt que de déclencher une action.

La ponctuation et la mise en forme sont également déterminées par la voix ; la liste complète, spécifique à chaque langue, est définie dans `language_settings.<lang>.punctuation` du fichier de configuration, et est affichée par le programme au démarrage.

# TOUCHE DE RACCORTAGE

Les raccourcis globaux `pynput` sont activés dès qu'un serveur X est joignable et quand `hotkeys.pynput_enabled` est vrai. `pynput` observe le serveur X : sous Wayland les raccourcis n'atteignent que les fenêtres passant par XWayland (beaucoup d'applications Electron et anciennes), jamais une fenêtre Wayland native active ; les sous-commandes de contrôle liées à un raccourci de bureau couvrent toutes les fenêtres. L'écouteur `pynput` ne consomme pas non plus l'événement clavier : la combinaison atteint aussi la fenêtre active, donc l'utiliser alors que le curseur est dans un terminal insère une séquence d'échappement (par exemple `^[s` pour **Alt+S**). Pour un arrêt propre depuis n'importe quelle fenêtre, liez plutôt **\--finalize** (ou **\--toggle**, **\--sleep-toggle**) à un raccourci clavier de bureau. La configuration par défaut définit :

**Alt+H**
:   Activez ou désactivez la dictée. Cela met simplement en pause ou reprend la dictée ; cela **ne** copie **rien** dans le presse-papiers, contrairement à **Alt+S** et à la phrase d'arrêt.
    Pendant la pause, le microphone reste actif et la phrase d'activation continue de fonctionner.

**Alt+S**
: Arrête la dictée en cours et copie le texte accumulé dans le presse-papiers – équivalent à la phrase d'arrêt. La combinaison fuit aussi dans la fenêtre active (voir ci-dessus) et manque les fenêtres Wayland natives ; préférez **\--finalize** lié à un raccourci de bureau.

**Alt+W**
:   Active/désactive le mode veille, un troisième état distinct des deux précédents. En mode veille, le flux audio est interrompu (le microphone est désactivé) et la reconnaissance est bloquée, ce qui réduit l'utilisation du processeur à presque zéro. La phrase de réveil ne peut être entendue tant que le mode veille n'est pas désactivé. La fonction **Alt+W** elle-même continue de fonctionner même en mode veille, car elle ne dépend pas de l'audio. L'activation du mode veille pendant une dictée l'interrompt proprement, ce qui évite toute perte de données au milieu d'une phrase.

**Ctrl+C**
:   Quitter le programme.

Les trois premiers raccourcis clavier sont configurables dans la section `hotkeys` du fichier de configuration. **Ctrl+C** ne l'est pas : c'est le signal d'interruption standard, toujours actif et qui ne peut jamais être modifié via la configuration.

# COMMANDES MANUELLES

Pendant l'exécution du programme, taper l'une des commandes suivantes dans sa fenêtre de terminal et appuyer sur Entrée permet également de le contrôler :

**/cancel**
:   Interrompez la session d'enregistrement en cours sans afficher aucun texte.

**/delete-word**
:   Supprime le dernier mot saisi.

: Insérer une nouvelle ligne (simule l'appui sur la touche Entrée).

# CONFIGURATION

Le comportement au moment de l'exécution est contrôlé par un fichier de configuration YAML : il permet de configurer les modèles de reconnaissance vocale disponibles, les paramètres audio, le seuil de confiance de la reconnaissance, les commandes vocales et la ponctuation spécifiques à chaque langue, les touches de raccourci, le son de notification et le thème de couleurs de la console.

Le fichier de configuration est trouvé selon la première règle correspondante ci-dessous ; une fois qu'une règle est trouvée, les règles restantes ne sont pas consultées.

1. Le chemin spécifié dans la variable d'environnement **VOSK_CONFIG**, si elle est définie. Utilisé tel quel ; jamais créé automatiquement.
2. `config/config.yaml`, par rapport au répertoire du projet, lors de l'exécution
   depuis une copie Git (mode développement).
3. `$XDG_CONFIG_HOME/vosk-cli-dictation/config.yaml` (par défaut
   `~/.config/vosk-cli-dictation/config.yaml`). Créé automatiquement lors de la première exécution, à partir du modèle par défaut, lorsque installé à partir du paquet Debian.
4. Le modèle par défaut fourni par le paquet, en lecture seule.

La langue active est choisie, dans l'ordre suivant : l'**\--lang** option, si elle est spécifiée ;
sinon, la langue détectée par le système d'exploitation ; sinon, la
valeur **`default_model`** provenant du fichier de configuration.

Consultez **configuration.md** dans la documentation du projet pour obtenir la
référence complète de chaque clé de configuration.

# FICHIERS

`~/.config/vosk-cli-dictation/config.yaml`
:   Fichier de configuration par utilisateur (installation du paquet Debian).

`/usr/share/vosk-cli-dictation/config.yaml`
:   Modèle de configuration d'usine (installation du paquet Debian), en lecture seule.

`~/.local/share/vosk-models/`
:   Emplacement par défaut où les modèles acoustiques de Vosk sont recherchés (installation via le paquet Debian).

`config/config.yaml`
:   Fichier de configuration utilisé lors de l'exécution à partir d'une copie de dépôt Git.

`vosk-model/`
:   Emplacement par défaut recherché pour les modèles acoustiques Vosk lorsqu'ils sont utilisés
    à partir d'une branche Git.

`$XDG_RUNTIME_DIR/vosk-cli-dictation.sock`
:   Socket de contrôle de la session en cours (mode `0600`). Supprimé lors d'une
    sortie propre ; un socket obsolète laissé par un crash est détecté et
    remplacé au démarrage suivant.

# CODE DE RETOUR

**0**
: Le programme s'est terminé correctement, y compris après l'utilisation de **Ctrl+C**.

Non nul
:   Échec du démarrage : ni **ydotool** ni **xdotool** ne sont disponibles, aucun modèle de reconnaissance vocale n'a pu être chargé, ou le périphérique audio n'a pas pu être ouvert.

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

Signalez les bugs dans le système de suivi des problèmes du projet :
*https://github.com/RonanDavalan/vosk-cli-dictation/issues*

# AUTEUR

Ronan Davalan, et les contributeurs mentionnés dans CONTRIBUTORS.md.
