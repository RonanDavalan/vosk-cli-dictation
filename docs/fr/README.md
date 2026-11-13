# Vosk-CLI-Dictation

<p align="center">
  <a href="https://github.com/RonanDavalan/vosk-cli-dictation/blob/main/LICENSE"><img src="https://img.shields.io/badge/Licence-MIT-blue.svg" alt="Licence : MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/Version-v0.5.4--beta-yellow.svg" alt="Version : v0.5.4-beta"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+"></a>
  <a href="#"><img src="https://img.shields.io/badge/Linux-Debian_%C2%B7_Fedora_%C2%B7_openSUSE_%C2%B7_Arch-blue.svg" alt="Paquets natifs pour Debian, Fedora, openSUSE et Arch Linux"></a>
  <a href="#"><img src="https://img.shields.io/badge/Contributions-Bienvenues-brightgreen.svg" alt="Contributions bienvenues"></a>
</p>

[English](../../README.md) | **Français** | [Deutsch](../de/README.md) | [Español](../es/README.md)

<p align="center">
  <a href="https://vosk.davalan.fr/"><strong>Visitez la page d'accueil officielle pour un tour complet !</strong></a>
</p>

<p align="center">
  <a href="https://vosk.davalan.fr/"><strong>▶ Regardez la vidéo de démonstration sur la page d'accueil</strong></a>
</p>

Un outil de dictée en ligne de commande puissant et personnalisable pour Linux, fondé sur le moteur Vosk. Transformez votre voix en texte directement dans votre terminal et faites-le apparaître dans n'importe quelle application.

---

## Pourquoi ce projet ?

Cet outil est né du besoin d'un système de dictée robuste, exécuté en local sous GNU/Linux, qui laisse à l'utilisateur la pleine maîtrise de ses données et du comportement du logiciel. Contrairement aux solutions dans le nuage, il fonctionne **100 % hors ligne**, ce qui garantit votre vie privée.

## Fonctionnalités principales

*   **Intégration à tout le système :** dictez dans n'importe quelle application active (terminal, navigateur, éditeur de code, etc.).
*   **Prise en charge de plusieurs langues :** fonctionne dès l'installation en **anglais**, **français**, **allemand** et **espagnol**.
*   **Contrôle universel :** une session en cours se pilote par un socket Unix privé ; la même commande liée à un raccourci du bureau (`vosk-cli-dictation --toggle`, `--sleep`, `--status`) la contrôle sur n'importe quel bureau, Wayland natif compris. Les raccourcis globaux via `pynput` restent une commodité au mieux : sous Wayland, ils n'atteignent que les fenêtres XWayland, pas les fenêtres Wayland natives.
*   **Entièrement personnalisable :** réglez les couleurs de l'interface, les raccourcis, les phrases de déclenchement vocal, la typographie par langue et les alias de reconnaissance dans un simple fichier `config.yaml`.
*   **Ponctuation complète :** dictez toute la gamme de ponctuation par des commandes vocales naturelles.
*   **Privé et hors ligne :** tout s'exécute sur votre machine. Votre voix ne quitte jamais votre ordinateur.

> [!NOTE]
>
> **Prise en charge de X11 et de Wayland.** Le texte est injecté en le copiant dans le presse-papiers puis en simulant un collage. Sous Wayland, l'outil utilise `wtype` et `wl-clipboard`, avec `ydotool` en repli (qui exige le démon `ydotoold` et l'accès à `/dev/uinput`, en général par le groupe `input` — `sudo usermod -aG input $USER`, puis fermez la session et rouvrez-la). Sous X11, il utilise `xdotool`. Au moins un moteur pour le type de session courant doit être installé ; `vosk-cli-dictation --diagnose` indique ce qui est disponible.
>
> **Raccourcis globaux.** `pynput` surveille le serveur X : sous Wayland, il ne voit les touches que pour les fenêtres qui passent par XWayland (beaucoup d'applications Electron et anciennes), jamais pour une fenêtre Wayland native qui a le focus. Il ne consomme pas non plus les événements : la combinaison de touches atteint aussi la fenêtre qui a le focus, de sorte que l'appuyer en tapant dans un terminal y insère une séquence d'échappement (`^[s` pour `Alt+S`). Pour un contrôle qui marche partout, liez plutôt les réglages de raccourcis de votre bureau aux sous-commandes de contrôle (`vosk-cli-dictation --toggle`, `--finalize`, `--sleep-toggle`). Voir *Contrôler une session en cours* plus bas. Sous Debian, `ydotool` est empaqueté dans `trixie-backports`, pas dans la version stable.

## Pour commencer

### Installer le paquet natif (recommandé)

Installez le paquet construit pour votre distribution depuis la
[page de téléchargements](https://vosk.davalan.fr/) — aucune installation manuelle,
aucun environnement virtuel à créer :

```bash
# Debian 12+ et dérivées (Ubuntu 24.04+, Mint 22+...)
sudo apt install ./vosk-cli-dictation_0.5.4~beta_all.deb

# Fedora
sudo dnf install ./vosk-cli-dictation-0.5.4~beta-1.fc42.noarch.rpm

# openSUSE (Leap)
sudo zypper install ./vosk-cli-dictation-0.5.4~beta-1.leap156.noarch.rpm

# Arch Linux
sudo pacman -U ./vosk-cli-dictation-0.5.4_beta-1-any.pkg.tar.zst
```

À la première configuration du paquet, un environnement virtuel privé est construit et le moteur Vosk y est installé (cette étape a besoin d'un accès au réseau).

Récupérez ensuite un modèle vocal et commencez à dicter :

```bash
vosk-cli-dictation --download-model fr   # aussi : en, de, es
vosk-cli-dictation -l fr
```

Ajoutez `--model-size big` pour le modèle complet (`vosk-cli-dictation --download-model fr --model-size big`) : de 1,4 à 1,9 Go selon la langue, et environ trois fois plus d'espace disque libre pendant la décompression.

Si vous lancez l'outil sans modèle installé, il propose le téléchargement de façon interactive. Un modèle manquant est signalé sans être fatal, tant qu'une langue se charge. Les modèles téléchargés sont vérifiés par SHA256 et rangés sous `~/.local/share/vosk-models/`.

Le paquet tire `xdotool` (X11) ou `ydotool` (repli Wayland) pour l'injection du texte. Pour Wayland natif, installez aussi le moteur préféré avec le gestionnaire de paquets de votre distribution (exemple Debian) :

```bash
sudo apt install wtype wl-clipboard
```

`ydotool` exige que votre utilisateur soit dans le groupe `input` (`sudo usermod -aG input $USER`, puis fermez la session et rouvrez-la) ; `xdotool` et `wtype` ne l'exigent pas. Lancez `vosk-cli-dictation --diagnose` pour voir quel moteur, quelle entrée audio et quel accès au presse-papiers sont disponibles.

> [!NOTE]
> Si `apt` affiche un avertissement de bac à sable ou de permission `_apt`, c'est que le `.deb` se trouve sous votre répertoire personnel, que l'utilisateur `_apt` ne peut pas lire. Copiez-le d'abord dans `/tmp/` et installez-le de là. L'installation réussit dans les deux cas.

### Installer depuis les sources (pour le développement)

Ce chemin exécute le code directement depuis une copie de travail git. Les paquets système ci-dessous sont ceux de Debian ; sous Fedora, openSUSE ou Arch, installez les équivalents avec votre gestionnaire de paquets.

```bash
sudo apt-get update && sudo apt-get install python3-pip python3-venv portaudio19-dev gettext xdotool pulseaudio-utils
# Wayland, facultatif : sudo apt-get install wtype wl-clipboard ydotool

git clone https://github.com/RonanDavalan/vosk-cli-dictation.git
cd vosk-cli-dictation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Récupérez un modèle et lancez le script :

```bash
python3 src/main.py --download-model fr   # aussi : en, de, es
python3 src/main.py -l fr                 # la langue par défaut vient de config.yaml
python3 src/main.py --diagnose            # vérifier l'environnement sans démarrer de session
```

Les modèles téléchargés ainsi atterrissent aussi dans `~/.local/share/vosk-models/`. En repli, un dossier de modèle (par exemple `vosk-model-small-fr-0.22`) déposé directement dans le répertoire `vosk-model/` du projet est aussi pris en compte.

Une seule session s'exécute à la fois par utilisateur ; un second lancement est refusé et vous renvoie vers `--status`.

### Astuce : créer une commande de lancement rapide (facultatif)

Pour y accéder plus facilement, vous pouvez ajouter une fonction au fichier de configuration de votre interpréteur de commandes (par exemple `~/.bashrc` ou `~/.zshrc`).

1.  Ouvrez votre fichier de configuration : `nano ~/.bashrc`
2.  Ajoutez les lignes suivantes à la fin. **N'oubliez pas de remplacer `/path/to/your/vosk-cli-dictation` par le chemin absolu réel du répertoire du projet.**

    ```bash
    # Définit une commande 'vosk' pour lancer facilement le script de dictée.
    vosk() {
        # Vérifie que le répertoire du projet existe
        if [ -d "/path/to/your/vosk-cli-dictation" ]; then
            cd "/path/to/your/vosk-cli-dictation" && \
            source venv/bin/activate && \
            python3 src/main.py "$@" && \
            deactivate
        else
            echo "Erreur : répertoire du projet introuvable : /path/to/your/vosk-cli-dictation"
        fi
    }
    ```

3.  Appliquez les changements avec `source ~/.bashrc` ou en ouvrant un nouveau terminal.
4.  Vous pouvez désormais lancer l'application de n'importe où en tapant simplement `vosk` ou `vosk -l en`.

## Utilisation et configuration

### Choix de la langue

Le modèle de langue est choisi selon l'ordre de priorité suivant :

1.  **Option de ligne de commande (priorité la plus haute) :** utilisez `-l en`, `-l fr`, `-l de` ou `-l es` pour imposer une langue à la session.
2.  **Choix mémorisé :** une langue ou un modèle choisi pendant qu'une session tourne (`set-lang`, `set-model`, voir plus bas) est conservé dans `~/.local/state/vosk-cli-dictation/selection.yaml` et repris au lancement suivant.
3.  **`default_model` de `config.yaml` :** un code de langue, ou `system` — valeur d'usine, aussi utilisée quand la clé manque — qui suit la langue de la session (`LC_ALL`, `LC_MESSAGES`, puis `LANG`) si un modèle de cette langue est installé, l'anglais sinon.

### Phrases de déclenchement vocal

Chaque langue a une **phrase de réveil** et une **phrase d'arrêt** de deux mots (valeurs d'usine : `start dictation` / `stop dictation` en anglais). Deux mots plutôt qu'un, pour qu'une phrase ordinaire ne les déclenche jamais par accident. Dites la phrase de réveil pour commencer à dicter, la phrase d'arrêt pour terminer et copier le résultat. Dire une phrase deux fois de suite (`stop dictation stop dictation`) la tape littéralement au lieu de la déclencher. Si la phrase d'arrêt est entendue avec une confiance de reconnaissance faible, elle est avalée plutôt que tapée dans votre document : répétez-la, ou utilisez `--finalize`. Les phrases se configurent par langue sous `language_settings.<lang>.voice_commands`.

### Modes de déclenchement

`interaction.mode` (par défaut `toggle`, inchangé par rapport aux versions précédentes) choisit comment une session démarre et s'arrête : un geste démarre, un autre geste arrête. Deux autres modes : `maintenue` (appuyer pour parler : la dictée dure tant que `hotkeys.push_to_talk` reste enfoncé) et `silence` (un seul appui démarre ; la session s'arrête et copie le texte d'elle-même quand `interaction.silence_timeout_ms` s'écoule sans sortie du décodeur, dès qu'un mot a été capté). La phrase d'arrêt parlée et `--finalize`/`--cancel` restent disponibles comme filet de sécurité dans tous les modes. Voir [`configuration.md`](configuration.md#interaction) pour la référence complète.

### Contrôler une session en cours

La session ouvre un socket Unix privé à `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock` (mode `0600`). Lancer la **même commande** avec une option de contrôle s'y connecte, exécute l'action, affiche l'état et se termine :

```bash
vosk-cli-dictation --status          # -> OK ÉCOUTE
vosk-cli-dictation --info            # -> OK {"state":"ÉCOUTE","lang":"fr",…}  (état complet, une ligne JSON)
vosk-cli-dictation --toggle          # démarrer/arrêter la dictée
vosk-cli-dictation --sleep-toggle    # entrer dans le mode veille ou en sortir (libère le microphone)
vosk-cli-dictation --finalize        # arrêter et copier le texte accumulé
vosk-cli-dictation --stop            # arrêter la session
```

Liez ces commandes aux réglages de raccourcis clavier de votre bureau (KDE, GNOME, Sway, labwc…) pour un contrôle global qui marche partout, y compris dans les fenêtres Wayland natives que `pynput` ne peut pas voir. Les raccourcis `pynput` de la section `hotkeys` fonctionnent aussi comme commodité au mieux — sous Wayland, seulement sur les fenêtres XWayland.

### Changer de langue et de modèle sans relancer

Une session en cours change de langue ou de modèle sans redémarrer, et le texte déjà tapé reste. Deux requêtes le font : `set-lang fr|en|de|es|system` et `set-model <dossier du modèle>` (un nom de dossier de la liste `models` qu'affiche `--info`). Le nouveau modèle se charge en arrière-plan pendant que l'actuel continue de servir, puis le remplace entre deux énoncés ; si le chargement échoue, le modèle actuel reste et `last_error` dans `--info` en donne la raison. Le choix est mémorisé dans `selection.yaml` (voir la sélection de la langue). Les requêtes s'envoient directement à la socket ; tout outil qui écrit une ligne dans une socket Unix convient, ici `socat` :

```bash
printf 'set-lang en\n' | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/vosk-cli-dictation.sock   # -> OK ÉCOUTE
vosk-cli-dictation --info            # lang, model, models, loading, last_error…
```

Erreurs : `ERR bad-argument` (argument inconnu), `ERR no-model` (aucun modèle installé pour la demande), `ERR busy` (un chargement est en cours). Une troisième requête, sans argument, `reset-selection`, oublie le choix mémorisé et revient à ce que donnent `config.yaml` ou la langue du système.

### Affiner chaque énoncé avec Whisper (facultatif)

Vosk continue de découper et d'afficher le texte au fil de la voix. Avec la finition active, chaque énoncé fini part aussi, en audio, à `faster-whisper`, dont le texte, avec ses majuscules et sa ponctuation, remplace celui de Vosk juste avant la frappe. Une phrase de commande (arrêt, réveil) n'est jamais affinée ; les énoncés sont tapés dans l'ordre où ils ont été dits ; et quand Whisper met plus de `refine.timeout_ms` (2000 ms) après la fin de l'énoncé, ou ne rend rien d'utilisable, le texte de Vosk est tapé à sa place. `vosk-cli-dictation --status` (une seconde ligne), `--diagnose` et `--info` comptent ces replis. Rien ne change tant que `refine.engine` vaut `none`, la valeur d'usine.

**Prérequis :** `faster-whisper` dans l'environnement Python de la dictée : le paquet optionnel `vosk-cli-dictation-whisper`, de la même version que le paquet principal, l'y ajoute (`sudo apt install ./vosk-cli-dictation-whisper_0.5.4~beta_all.deb` ; les mêmes noms de fichier avec `-whisper` sous Fedora, openSUSE et Arch), ou `pip install faster-whisper` depuis une copie du dépôt Git. Sans lui, le menu de l'icône grise l'entrée avec cette raison et `--diagnose` le dit. Les poids se téléchargent au premier usage sous `~/.local/share/vosk-cli-dictation/whisper-models` (environ 75 Mo pour `tiny`, 1,6 Go pour `large-v3-turbo`) ; l'icône annonce le premier téléchargement, et le texte de Vosk est tapé en attendant.

```yaml
refine:
  engine: whisper      # none (valeur d'usine) | whisper
  model: auto          # auto | tiny | base | small | medium | large-v3-turbo
  device: auto         # auto | cpu | cuda
  compute_type: auto   # auto : float16 sur cuda, int8 sur cpu
  timeout_ms: 2000
```

*   **Sur une carte graphique (NVIDIA) :** CTranslate2 a besoin de la bibliothèque CUDA 12 `libcublas.so.12` (Debian et Ubuntu : `sudo apt install libcublas12 libcublaslt12`). `device: auto` se sert de la carte quand elle est détectée et que la bibliothèque se charge ; une carte sans la bibliothèque replie sur le processeur et la dictée affiche ce remède ; `device: cuda` est alors refusé avec le même remède. `--diagnose` montre le matériel retenu et l'état de la bibliothèque. `model: auto` donne `large-v3-turbo`, la plus grande taille dont la latence au 95e centile par énoncé reste sous 500 ms (environ 310 ms sur une RTX 3060).
*   **Sur un processeur :** aucune taille ne reste sous 500 ms par énoncé (`tiny` demande 3,4 s au 95e centile sur un Raspberry Pi 4 et 1,3 s sur un x86 à 8 cœurs), et `tiny` comme `base` abîment le texte français. `model: auto` ne donne donc aucune finition ; choisissez une taille à la main dans `config.yaml` ou au menu de l'icône, et relevez `timeout_ms` en conséquence. Un cœur reste à Vosk.
*   **À quoi s'attendre :** sur le banc de parole synthétique du projet (il compare des moteurs, il ne promet pas un taux réel), les erreurs sur les mots français passent de 15,4 % à 12,0 % avec le modèle Vosk léger et `large-v3-turbo` ; avec le modèle Vosk complet les mots ne sont pas meilleurs (10,1 % contre 12,2 %) et la finition apporte surtout majuscules et ponctuation.

Une session en cours change la finition sans redémarrer, depuis le menu de l'icône ou sur la socket : `set-refine whisper:small` ou `set-refine none`. La taille se charge en arrière-plan pendant que le texte de Vosk est tapé ; le choix est mémorisé dans `selection.yaml` (clé `refine`), et `reset-selection` revient à la configuration. Erreurs : `ERR bad-argument` (taille inconnue), `ERR busy` (un chargement est en cours), `ERR unsupported` (`faster-whisper` manque). `--info` donne `refine`, `refine_options`, `refine_reason`, `device`, `refine_download` et `refine_stats` (`done`, `timeout`, `error`, `rejected`, `skipped`, `mean_ms`).

### Commandes manuelles

Pendant que le script s'exécute dans un terminal, vous pouvez aussi saisir ces commandes et appuyer sur Entrée :

*   `/cancel` : arrête la session d'enregistrement en cours sans produire de texte.
*   `/delete-word` : supprime le dernier mot tapé.
*   `/nl` : insère un saut de ligne (simule l'appui sur la touche Entrée).

### Icône de zone de notification (facultatif)

`vosk-cli-dictation-tray` est un programme à part (Python et PySide6) qui affiche un micro dans la zone de notification et pilote la session en cours par sa socket de contrôle. La dictée n'en a jamais besoin et fonctionne de la même façon sans lui. La couleur et la forme disent l'état, si bien que l'icône reste lisible pour un daltonien :

*   **micro rouge entouré d'ondes** : `DICTÉE`, la voix est tapée ;
*   **micro orange** : `ÉCOUTE`, le micro est ouvert, la dictée est coupée, la phrase de réveil est attendue ;
*   **micro bleu sous un croissant de lune** : `VEILLE`, le micro est libéré ;
*   **micro vert en contour** : aucune dictée ne tourne ; un clic la lance.

Un clic gauche lance la dictée si elle est éteinte et la bascule sinon. Le menu du clic droit démarre ou arrête la dictée, la met en veille ou la réveille, termine et copie le texte, annule la session, et choisit la langue (suivre le système ou l'une des quatre ; une langue sans modèle est marquée « à télécharger »), le modèle (léger ou complet, avec sa taille s'il manque ; le téléchargement part du menu et une notification dit quand il finit), la finition par Whisper (proposée quand `faster-whisper` est installé, grisée avec sa raison sinon ; le premier usage d'une taille télécharge ses poids et une notification dit quand cela commence et finit) et la correction (grisée, avec sa raison, tant que la dictée en cours ne l'annonce pas), puis « Revenir à la configuration », activer la dictée vocale ou la quitter, « Lancer l'icône à l'ouverture de session » (une entrée XDG Autostart) et quitter l'icône. La dictée lancée par l'icône tourne détachée de tout terminal ; sa sortie va dans `~/.local/state/vosk-cli-dictation/instance.log`. Sur un bureau sans zone de notification (GNOME sans extension), l'icône dit une fois, par une notification de bureau, comment activer « AppIndicator and KStatusNotifierItem Support » ; les sous-commandes de contrôle ci-dessus continuent de fonctionner.

Avec les paquets natifs, l'icône est un second paquet de la même version que le paquet principal :

```bash
# Debian 12+, Ubuntu 24.04+, Mint 22+...
sudo apt install ./vosk-cli-dictation-tray_0.5.4~beta_all.deb
# Fedora
sudo dnf install ./vosk-cli-dictation-tray-0.5.4~beta-1.fc42.noarch.rpm
# openSUSE Leap
sudo zypper install ./vosk-cli-dictation-tray-0.5.4~beta-1.leap156.noarch.rpm
# Arch Linux
sudo pacman -U ./vosk-cli-dictation-tray-0.5.4_beta-1-any.pkg.tar.zst
```

Sa bibliothèque graphique, PySide6, s'installe avec `pip` dans un environnement virtuel privé à la première configuration (accès réseau nécessaire à ce moment-là seulement) ; le paquet ajoute aussi une entrée de menu et une entrée système d'ouverture de session (décocher « Lancer l'icône à l'ouverture de session » dans le menu la retire pour votre compte). Depuis une copie du dépôt Git :

```bash
cd ~/git/vosk-cli-dictation/vosk-cli-dictation/tray
python3 -m venv venv && venv/bin/pip install -e .
venv/bin/vosk-cli-dictation-tray
```

Options : `--socket CHEMIN` (piloter la socket d'une autre dictée), `--dictation-command COMMANDE` (comment l'icône lance la dictée), `--version`. Voir `man vosk-cli-dictation-tray` (`docs/fr/vosk-cli-dictation-tray.1.md`).

### Personnalisation

Tous les réglages se modifient dans le fichier `config/config.yaml` : raccourcis, couleurs de l'interface, phrases de déclenchement vocal, typographie par langue et alias de reconnaissance. Des exemples d'alias propres à un corpus sont dans `config/config.example.yaml`. Voir [`configuration.md`](configuration.md) pour la référence complète.

## Contribuer

Ce projet est libre et les contributions sont vivement encouragées ! Consultez notre **[Guide de contribution](../../CONTRIBUTING.md)** et n'hésitez pas à ouvrir un ticket sur la [page des tickets](https://github.com/RonanDavalan/vosk-cli-dictation/issues).

Ce projet est construit dans une collaboration asymétrique humain-LLM — voir [CONTRIBUTORS.md](../../CONTRIBUTORS.md) pour les rôles concernés.

## Crédits

Ce projet est construit dans une collaboration humain-LLM, dont les rôles sont écrits tels qu'ils ont été réellement tenus. La liste complète est dans [CONTRIBUTORS.md](../../CONTRIBUTORS.md).

*   **Ronan Davalan** — Architecte et arbitre : vision, exigences de sécurité, validation et essais.
*   **Claude Code (Anthropic)** — Ingénieur systèmes et développeur principal : auteur principal du code source depuis la v0.5.0-alpha, du paquetage Debian et de l'outillage.
*   **Gemini (Google)** — Synthétiseur et conseiller stratégique.
*   **Grok (xAI)** — Validateur externe.
*   **GLM-5.3** — Auditeur du cœur d'interaction (audit croisé à l'aveugle).
*   **DeepSeek V4 Flash (via OpenCode)** — Relecteur de la documentation et du site, testeur.

## Licence

Ce projet est distribué sous **licence MIT**. Voir le fichier [LICENSE](../../LICENSE) pour les détails.
