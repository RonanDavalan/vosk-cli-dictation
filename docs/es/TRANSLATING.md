# Cómo traducir el proyecto.

Gracias por tu interés en hacer que este proyecto sea accesible a más personas. Traducir la interfaz es una de las formas más valiosas de contribuir.

Esta guía le mostrará el proceso de agregar un nuevo idioma o mejorar uno existente.

## Resumen del flujo de trabajo de traducción.

El proyecto utiliza el sistema estándar `gettext` para la internacionalización. El proceso es el siguiente:
1.  **Extraer:** Las cadenas de texto originales (en inglés) se extraen del código Python y se guardan en un archivo de plantilla (`messages.pot`).
2.  **Actualizar:** Esta plantilla se utiliza para actualizar los archivos de idioma individuales (`messages.po`).
3.  **Traducir:** Editas el archivo de tu idioma `.po` para proporcionar las traducciones.
4.  **Compilar:** El archivo `.po` legible por humanos se compila en un archivo `.mo` legible por la máquina que utiliza la aplicación.

Un script de ayuda, `manage_translations.sh`, automatiza la mayoría de estos pasos para usted.

## Agregar o mejorar una traducción

### Requisitos previos

-   Una copia local del repositorio del proyecto.
-   El entorno virtual del proyecto configurado (ver `README.md`).
-   Un editor de texto que soporte la codificación UTF-8 (como VS Code, Kate, Gedit, etc.).

### Paso 1: Prepara tu archivo de idioma.

Primero, encuentra el código de dos letras de tu idioma (por ejemplo, `es` para español, `de` para alemán, `it` para italiano).

**Si estás mejorando un idioma existente (por ejemplo, francés `fr`):**
Solo debes asegurarte de que tus archivos locales estén actualizados. Ejecuta el comando de actualización:

```bash
./manage_translations.sh update 
```

Esto agregará cualquier nueva cadena de texto en inglés del código fuente a tu archivo de localización `.po`.

Si estás agregando un NUEVO idioma:
1. Activa el entorno virtual: `source vosk-env/bin/activate`
2. Utiliza el comando `pybabel init` para crear un nuevo archivo `.po` para tu idioma. Reemplaza `[lang]` con el código de tu idioma (por ejemplo, `es`):

    ```bash
    pybabel init -i locales/messages.pot -d locales -l [lang]
    ```

Esto crea una nueva carpeta y archivo, por ejemplo: `locales/es/LC_MESSAGES/messages.po`.

### Paso 2: Traducir los mensajes.

1.  Abra el archivo `.po` de su idioma, ubicado en `locales/[lang]/LC_MESSAGES/messages.po`.
2.  Verá bloques de texto como este:

    ```po
    #: src/main.py:34
    msgid "Checking external dependencies..."
    msgstr ""
    ```

3.  Su tarea es completar la línea `msgstr` con la traducción correcta de la línea `msgid` que está arriba.

    ```po
    #: src/main.py:34
    msgid "Checking external dependencies..."
    msgstr "Vérification des dépendances externes..."
    ```

4.  **Notas importantes:**
    *   Si ve marcadores de posición como `{model_name}`, asegúrese de incluirlos también en su traducción. Ejemplo:

        ```po
        msgid "Model '{model_name}' is already loaded."
        msgstr "Le modèle '{model_name}' est déjà chargé."
        ```

*   Conservar caracteres especiales como `\n` (salto de línea).
*   Guardar el archivo con codificación UTF-8.

### Paso 3: Compila y prueba tu traducción.

Una vez que hayas terminado de traducir, necesitas compilar tu `.po` archivo en un `.mo` archivo.

1.  Ejecuta el comando de compilación desde la raíz del proyecto:
    ```bash
    ./manage_translations.sh compile
    ```
2.  Ahora, puedes probar tus cambios ejecutando la aplicación y forzando tu idioma:

    ```bash
    python src/main.py --lang [lang]
    ```

Deberías ver tus mensajes traducidos en la consola.

### Paso 4: Envía tu contribución.

Una vez que estés satisfecho con tu traducción, por favor, envíala a través de una solicitud de extracción (Pull Request) en GitHub para que todos puedan beneficiarse de tu trabajo.

1.  Confirma (`commit`) tus cambios en el archivo `.po`.
    ```bash
    git add locales/[lang]/LC_MESSAGES/messages.po
    git commit -m "i18n: add/update [Language Name] translation"
    ```
    (p. ej., `i18n: add Spanish translation`)
2.  Sube tu rama y abre una solicitud de extracción (Pull Request).

¡Muchas gracias de nuevo por tu contribución!
