Guía de configuración del proyecto.

Este documento proporciona una explicación detallada de todas las opciones disponibles en el archivo `config/config.yaml`. Configurar correctamente este archivo es clave para adaptar la aplicación a sus necesidades específicas, idioma y hardware.

## ¿Cómo se determina el idioma?

La aplicación elige qué idioma usar según el siguiente orden de prioridad:

1.  **Argumento de línea de comandos (mayor prioridad):** El uso de la bandera `-l` o `--lang` (por ejemplo, `python src/main.py -l en`) siempre anulará todas las demás configuraciones.

2. **Idioma del sistema (detección automática):** Si no se proporciona ninguna indicación, la aplicación detecta automáticamente el idioma de tu sistema operativo.

3.  **`default_model` Configuración (Respaldo):** Si el idioma de su sistema no puede determinarse, la aplicación utilizará el modelo especificado en la configuración `default_model` como último recurso.

## Estructura general de `config.yaml`

El archivo de configuración está organizado en secciones lógicas:

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

## Secciones de configuración en detalle.

### `vosk_models`

Una lista que define los modelos de reconocimiento de voz disponibles de Vosk.

-   **`name`** (cadena de texto): Un nombre único y corto para el modelo (por ejemplo, `fr`, `en`).
-   **`path_relative`** (cadena de texto): La ruta relativa a la carpeta del modelo Vosk descomprimida, desde la raíz del proyecto.

```yaml
vosk_models:
  - name: "en"
    path_relative: "vosk-model/vosk-model-small-en-us-0.15"
  - name: "fr"
    path_relative: "vosk-model/vosk-model-small-fr-0.22"
```

El nombre del modelo de Vosk que se cargará al inicio. Debe coincidir con un `name` en la lista de `vosk_models`.

```yaml
default_model: "en"
```

Parámetros para tu micrófono.

-   **`sample_rate`** (entero): La frecuencia de muestreo con la que se entrenó su modelo (normalmente `16000`).
-   **`channels`** (entero): Número de canales de audio (debe ser `1` para mono).
-   **`frames_per_buffer`** (entero): `2048` o `4096` son valores comunes.
-   **`buffer_size`** (entero): El tamaño del búfer de audio.

```yaml
audio:
  sample_rate: 16000
  channels: 1
  frames_per_buffer: 4096
  buffer_size: 2048
```

### `recognition`

Parámetros para el motor de reconocimiento de Vosk.

-   **`confidence_threshold`** (float, 0.0-1.0): Las palabras con una puntuación de confianza inferior a este valor se ignorarán.

```yaml
recognition:
  confidence_threshold: 0.85
```

### `language_settings`

Esta sección contiene configuraciones específicas de un idioma.

-   **`voice_commands`**: Palabras clave para controlar la aplicación.
-   **`punctuation`**: Un diccionario para insertar automáticamente la puntuación. Está organizado en grupos lógicos para mayor claridad.
-   **`recognition_aliases`**: Corrige errores de reconocimiento comunes de Vosk (por ejemplo, `"sauna": "sonna"`).
-   **`custom_vocabulary`**: Un diccionario para correcciones sensibles a mayúsculas y minúsculas, aplicado después de los alias (por ejemplo, `"ia": "IA"`).

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

Atajos de teclado globales para controlar la aplicación.

-   **`pynput_keys`**: Una lista de teclas de Pynput para el atajo.
-   **`display_name`**: Una cadena de texto que se muestra en el mensaje de ayuda.

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

-   **`toggle_recording`** (por defecto `Alt+H`): inicia o pausa la dictado en curso. Mientras
    está en pausa, el micrófono permanece activo y la palabra de activación por voz sigue funcionando.
-   **`finalize_session`** (por defecto `Alt+S`): detiene la dictado y copia el texto acumulado
    al portapapeles.
-   **`sleep_toggle`** (por defecto `Alt+W`): activa/desactiva el **modo de suspensión**, un tercer estado distinto
    de los dos anteriores. En modo de suspensión, la captura de audio y el reconocimiento de voz están completamente
    suspendidos — el uso de CPU del motor de reconocimiento cae casi a cero — pero esto también significa que la
    palabra de activación (`start_word`) no puede ser escuchada hasta que el modo de suspensión se desactive de nuevo. Solo
    el atajo `Alt+W` sigue funcionando mientras está en suspensión, ya que no depende del audio.
    Activar el modo de suspensión mientras una dictado está en curso la detiene de forma limpia primero (como si
    se hubiera pulsado `Alt+H`), de modo que no se pierde audio a mitad de una frase.

    ```bash
    # How to test / how to run
    cd ~/git/vosk-cli-dictation/vosk-cli-dictation
    source vosk-env/bin/activate
    python3 src/main.py
    # Alt+W toggles sleep mode; Alt+H toggles dictation; Alt+S finalizes and copies.
    ```

### `sound_file`

La ruta absoluta a un archivo de sonido de notificación (por ejemplo, `.oga`, `.wav`).

```yaml
sound_file: "/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga"
```

### `theme`

Esta sección le permite personalizar los colores de la aplicación en la consola. Los valores deben ser nombres de colores `colorama` válidos (por ejemplo, `GREEN`, `RED`, `BLUE`).

-   **`ready_message`**: Color del mensaje "El script está listo".
-   **`help_text`**: Color principal para el bloque del mensaje de ayuda.
-   **`help_title`**: Color para los títulos dentro del mensaje de ayuda.
-   **`info`**, **`success`**, **`warning`**, **`error`**: Colores para los mensajes de estado.

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
