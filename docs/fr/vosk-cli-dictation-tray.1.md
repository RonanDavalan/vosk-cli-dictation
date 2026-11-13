% VOSK-CLI-DICTATION-TRAY(1) vosk-cli-dictation | Commandes utilisateur
% Ronan Davalan
% 2026-11-12

# NOM

vosk-cli-dictation-tray - icône de micro de la zone de notification pour vosk-cli-dictation

# SYNOPSIS

**vosk-cli-dictation-tray** [**--socket** *CHEMIN*] [**--dictation-command** *COMMANDE*]

**vosk-cli-dictation-tray** **--version**

# DESCRIPTION

**vosk-cli-dictation-tray** affiche un micro dans la zone de notification du bureau (KDE Plasma nativement ; GNOME avec l'extension
« AppIndicator and KStatusNotifierItem Support ») et pilote une session **vosk-cli-dictation** en cours par sa socket de contrôle. C'est un
programme à part : la dictée n'en a jamais besoin, et lui ne demande que la socket. Il interroge la session par `info` quatre fois par
seconde ; une socket absente veut dire qu'aucune dictée ne tourne. Les libellés du menu suivent la langue de la dictée en cours, ou la
langue de la session quand aucune ne tourne, depuis les mêmes catalogues gettext que la dictée.

Sans zone de notification, il affiche une notification de bureau qui explique comment en activer une et continue de tourner : l'icône
apparaît si la zone arrive plus tard. Une seule icône tourne par socket.

# OPTIONS

**--socket** *CHEMIN*
:   Socket de contrôle à piloter. Par défaut : `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock`, celle de la dictée de l'utilisateur.

**--dictation-command** *COMMANDE*
:   Commande qui lance la dictée, découpée comme une ligne de commande de shell. Par défaut : la variable d'environnement
    `VOSK_CLI_DICTATION_COMMAND`, puis **vosk-cli-dictation** du `PATH`, puis la copie de la branche Git.

**--version**
:   Affiche la version et quitte.

# ÉTATS DE L'ICÔNE

La couleur et la forme disent l'état, si bien que l'icône reste lisible pour un daltonien.

micro rouge entouré d'ondes
:   `DICTÉE` : le micro est ouvert et la voix est tapée.

micro orange
:   `ÉCOUTE` : le micro est ouvert, la dictée est coupée, la phrase de réveil est attendue.

micro bleu sous un croissant de lune
:   `VEILLE` : le micro est libéré.

micro vert en contour
:   Aucune dictée ne tourne.

Un clic gauche lance la dictée si aucune ne tourne, et la bascule sinon. L'info-bulle reprend la ligne d'état et dit « chargement du
modèle… » pendant un chargement.

# MENU

Le menu du clic droit, dans cet ordre :

1.  une ligne d'état : état, langue, moteur ;
2.  démarrer ou arrêter la dictée ; mettre en veille ou réveiller ; terminer et copier le texte ; annuler la session ;
3.  **Langue** : suivre le système, ou français, anglais, allemand, espagnol ; une langue sans modèle installé se lit « à télécharger » ;
4.  **Modèle** : léger ou complet ; un modèle absent montre sa taille, et le choisir lance son téléchargement, avec une notification à la fin ;
5.  **Finition** : *Aucune* et les tailles de Whisper, chacune marquée `GPU` ou `CPU` ; grisée avec sa raison quand `faster-whisper` manque ; le premier usage d'une taille télécharge ses poids, avec une notification au début et à la fin. **Correction** : grisée avec sa raison tant que la dictée en cours n'annonce pas d'options ;
6.  revenir à la configuration (oublier le choix mémorisé) ;
7.  activer la dictée vocale ou la quitter (lancée détachée de tout terminal) ; lancer l'icône à l'ouverture de session ; quitter l'icône.

Pendant un chargement de modèle, les choix qui le changent sont grisés.

# FICHIERS

`~/.local/state/vosk-cli-dictation/instance.log`
:   Sortie de la dictée lancée par l'icône, et des téléchargements de modèle qu'elle démarre.

`~/.config/autostart/vosk-cli-dictation-tray.desktop`
:   L'entrée XDG Autostart qu'écrit « Lancer l'icône à l'ouverture de session » (`Hidden=true` quand la case est décochée).

`$XDG_RUNTIME_DIR/vosk-cli-dictation.sock`
:   La socket de contrôle de la dictée.

# VOIR ÉGALEMENT

**vosk-cli-dictation**(1)

# BUGS

Signalez les bugs dans le système de suivi des problèmes du projet :
*https://github.com/RonanDavalan/vosk-cli-dictation/issues*

# AUTEUR

Ronan Davalan, et les contributeurs mentionnés dans CONTRIBUTORS.md.
