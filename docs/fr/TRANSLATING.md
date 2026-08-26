# Comment traduire le projet

Merci de votre intérêt à rendre ce projet accessible à un public plus large ! Traduire l'interface est l'une des façons les plus précieuses de contribuer.

Ce guide vous accompagnera dans le processus d'ajout d'une nouvelle langue ou d'amélioration d'une langue existante.

Aperçu du processus de traduction.

Le projet utilise le système standard `gettext` pour la localisation. Le processus est le suivant :
1.  **Extraction :** Les chaînes de caractères sources (en anglais) sont extraites du code Python et enregistrées dans un fichier modèle (`messages.pot`).
2.  **Mise à jour :** Ce modèle est utilisé pour mettre à jour les fichiers de langue individuels (`messages.po`).
3.  **Traduction :** Vous modifiez le fichier `.po` de votre langue pour fournir les traductions.
4.  **Compilation :** Le fichier `.po` lisible par l'homme est compilé en un fichier `.mo` lisible par la machine que l'application utilise.

Un script d'aide, `manage_translations.sh`, automatise la plupart de ces étapes pour vous.

## Ajouter ou améliorer une traduction

Prérequis.

-   Une copie locale du dépôt du projet.
-   L'environnement virtuel du projet configuré (voir `README.md`).
-   Un éditeur de texte qui prend en charge l'encodage UTF-8 (comme VS Code, Kate, Gedit, etc.).

Étape 1 : Préparez votre fichier de langue.

Tout d'abord, trouvez le code de deux lettres de votre langue (par exemple, `es` pour l'espagnol, `de` pour l'allemand, `it` pour l'italien).

**Si vous améliorez une langue existante (par exemple, le français `fr`):**
Il vous suffit de vous assurer que vos fichiers locaux sont à jour. Exécutez la commande de mise à jour :

```bash
./manage_translations.sh update 
```

Cela ajoutera toutes les nouvelles chaînes de caractères anglais provenant du code source à votre fichier de langue `.po`.

Si vous ajoutez une NOUVELLE langue :
1.  Activez l'environnement virtuel : `source vosk-env/bin/activate`
2.  Utilisez la commande `pybabel init` pour créer un nouveau fichier `.po` pour votre langue. Remplacez `[lang]` par le code de votre langue (par exemple, `es`):

    ```bash
    pybabel init -i locales/messages.pot -d locales -l [lang]
    ```

Cela crée un nouveau dossier et un nouveau fichier, par exemple : `locales/es/LC_MESSAGES/messages.po`.

### Étape 2 : Traduire les messages.

1.  Ouvrez le fichier `.po` de votre langue, situé à `locales/[lang]/LC_MESSAGES/messages.po`.
2.  Vous verrez des blocs de texte comme ceci :

    ```po
    #: src/main.py:34
    msgid "Checking external dependencies..."
    msgstr ""
    ```

3.  Votre tâche consiste à remplir la ligne `msgstr` avec la traduction correcte de la ligne `msgid` qui se trouve au-dessus.

    ```po
    #: src/main.py:34
    msgid "Checking external dependencies..."
    msgstr "Vérification des dépendances externes..."
    ```

4.  **Remarques importantes :**
    *   Si vous voyez des espaces réservés comme `{model_name}`, assurez-vous de les inclure également dans votre traduction. Exemple :

        ```po
        msgid "Model '{model_name}' is already loaded."
        msgstr "Le modèle '{model_name}' est déjà chargé."
        ```

*   Conserver les caractères spéciaux comme `\n` (saut de ligne).
*   Enregistrer le fichier avec l'encodage UTF-8.

Étape 3 : Compilez et testez votre traduction.

Une fois que vous avez terminé de traduire, vous devez compiler votre `.po` en un fichier `.mo`.

Exécutez la commande de compilation depuis la racine du projet :

    ```bash
    ./manage_translations.sh compile
    ```

2.  Maintenant, vous pouvez tester vos modifications en exécutant l'application et en forçant votre langue :

    ```bash
    python src/main.py --lang [lang]
    ```

Vous devriez voir vos messages traduits dans la console.

Étape 4 : Soumettez votre contribution.

Une fois que vous êtes satisfait de votre traduction, veuillez la soumettre via une demande de tirage (Pull Request) sur GitHub afin que tout le monde puisse en bénéficier !

Enregistrez vos modifications dans le fichier `.po`.

    ```bash
    git add locales/[lang]/LC_MESSAGES/messages.po
    git commit -m "i18n: add/update [Language Name] translation"
    ```

2.  Poussez votre branche et ouvrez une requête de tirage. `i18n: add Spanish translation`

Merci encore pour votre contribution !
