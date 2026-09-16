Guía de configuración del proyecto.

Este documento proporciona una explicación detallada de todas las opciones disponibles en el archivo `config/config.yaml`. Configurar correctamente este archivo es clave para adaptar la aplicación a sus necesidades específicas, idioma y hardware.

¿Cómo se determina el idioma?

La aplicación elige qué idioma usar según el siguiente orden de prioridad:

1.  **Argumento de línea de comandos (mayor prioridad):** El uso de la opción `-l` o `--lang` (por ejemplo, `python src/main.py -l en`) siempre anulará todas las demás configuraciones.

2. **Idioma del sistema (Detección automática):** Si no se proporciona ninguna configuración, la aplicación detecta automáticamente el idioma de tu sistema operativo.

3.  **`default_model` Configuración (Respaldo):** Si el idioma de su sistema no puede determinarse, la aplicación utilizará el modelo especificado en la configuración `default_model` como último recurso.

## Estructura general de `config.yaml`

El archivo de configuración está organizado en secciones lógicas:

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

## Secciones de configuración en detalle.

### `vosk_models`

Una lista que define los modelos de reconocimiento de voz disponibles de Vosk.

-   **`name`** (string): Un nombre único y corto para el modelo (por ejemplo, `fr`, `en`).
-   **`path_relative`** (string): La ruta relativa a la carpeta del modelo Vosk descomprimido. Se resuelve, en orden, contra `$XDG_DATA_HOME/vosk-models/` (por defecto `~/.local/share/vosk-models/`),
    `/usr/share/vosk-models/`, y luego la raíz del proyecto al ejecutar desde un repositorio Git; el primero de estos que realmente contenga la carpeta tiene prioridad. También se puede proporcionar como una ruta absoluta, que siempre tiene prioridad. Consulte la página del manual, la sección CONFIGURACIÓN, para ver la secuencia completa.

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

Un modelo que se declara pero no está presente en el disco se informa al inicio y se omite; el inicio solo falla si no se puede cargar ningún modelo.

### `default_model`

El nombre del modelo de Vosk que se cargará al inicio. Debe coincidir con un `name` en la lista de `vosk_models`.

```yaml
default_model: "en"
```

### `control_socket`

Booleano, valor predeterminado `true`. Cuando está habilitado, la sesión en ejecución escucha en un socket Unix en `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock` (modo `0600`), de modo que los subcomandos de control (`--toggle`, `--sleep-toggle`, `--status`, `--stop`, …) pueden controlarla. Establezca en `false` para deshabilitar completamente el socket; en este caso, la herramienta sigue siendo utilizable de forma interactiva, pero no se puede controlar desde un atajo.

```yaml
control_socket: true
```

### `audio`

Parámetros para tu micrófono.

-   **`sample_rate`** (entero): La tasa de muestreo con la que se entrenó su modelo (generalmente `16000`).
-   **`channels`** (entero): Número de canales de audio (debería ser `1` para mono).
-   **`frames_per_buffer`** (entero): `2048` o `4096` son valores comunes.
-   **`buffer_size`** (entero): El tamaño del búfer de audio.
-   **`queue_max_chunks`** (entero): Profundidad máxima de la cola de audio, en bloques de `buffer_size`.  `16` ≈ 2 segundos. Cuando el reconocimiento se retrasa, el bloque más antiguo se descarta en lugar de permitir que la latencia se desvíe; un contador de desbordamiento se muestra en `--status` y `--diagnose`.

```yaml
audio:
  sample_rate: 16000
  channels: 1
  frames_per_buffer: 4096
  buffer_size: 2048
  queue_max_chunks: 16
```

### `recognition`

Parámetros para el motor de reconocimiento de Vosk.

-   **`confidence_threshold`** (flotante, 0.0-1.0, valor predeterminado `0.55`): Una frase de activación de voz (activar o detener) solo se procesa cuando la confianza promedio de sus palabras alcanza este valor. Por debajo, una frase de activación se interpreta como texto normal; una frase de **parada** se descarta — ni se ejecuta ni se escribe en el documento — y se muestra una indicación. Redefinible por idioma con una clave del mismo nombre bajo `language_settings.<lang>`.
-   **`restricted_grammar_in_listening`** (booleano, valor predeterminado `true`): mientras se escucha la frase de activación, decodifica utilizando una gramática de Kaldi restringida a esa frase. El consumo de CPU se reduce significativamente, pero a costa de reconstruir el reconocedor completo al activar. Establece en `false` para mantener el reconocedor completo en funcionamiento en el estado de escucha. Redefinible por idioma bajo `language_settings.<lang>` — la configuración de fábrica lo desactiva para `es`, donde el modelo pequeño decodifica la gramática restringida más despacio que la completa.
-   **`restricted_stop_in_dictation`** (booleano, valor predeterminado `true`): durante el dictado, ejecuta un segundo reconocedor ligero restringido a la frase de parada, junto al completo. Proporciona una señal de parada de alta confianza independiente de `confidence_threshold` — el mismo mecanismo usado para la frase de activación durante la escucha. Redefinible por idioma bajo `language_settings.<lang>`; ponlo en `false` en hardware donde la decodificación restringida adicional por bloque de audio sea demasiado costosa (es unas 5× más barata que la decodificación completa).

```yaml
recognition:
  confidence_threshold: 0.55
  restricted_grammar_in_listening: true
  restricted_stop_in_dictation: true
```

### `sleep`

-   **`releases_device`** (booleano, valor predeterminado `true`): en modo de suspensión, cierra el flujo de audio para liberar completamente el micrófono (su LED se apaga) y permitir que otro programa lo utilice; la reapertura al despertar tarda aproximadamente 200 ms. Establece en `false` para detener solo el flujo sin cerrarlo; el dispositivo permanece bloqueado, pero el tiempo de activación es ligeramente más rápido.

```yaml
sleep:
  releases_device: true
```

### `clipboard`

El texto se inyecta insertándolo en el portapapeles y simulando un pegado.

-   **`restore`** (booleano, valor predeterminado: `true`): Restaura el contenido anterior del portapapeles del usuario después de pegar. Un portapapeles que no contenga texto (por ejemplo, una imagen) nunca se guarda ni se sobrescribe. También se puede desactivar por sesión con `--no-clipboard-restore`.
-   **`restore_delay_ms`** (entero, valor predeterminado: `400`): Ventana máxima, sondeada en tramos cortos, que se deja a la aplicación de destino para leer la selección antes de restaurar el portapapeles. La espera termina antes si el portapapeles ya ha cambiado (otro propietario ha tomado el control).
-   **`defer_restore`** (booleano, valor predeterminado: `false`): Con `true`, el portapapeles no se restaura entre los segmentos dictados; el contenido original se restablece una sola vez al final de la sesión (pausa, `--finalize`, suspensión o salida). Esto elimina la condición de carrera por la que se pega el contenido anterior del portapapeles, observada en Wayland con aplicaciones GTK, a costa de un portapapeles no restaurado durante el dictado.
-   **`confirm_timeout_ms`** (entero, valor predeterminado: `500`): Tiempo máximo de espera para confirmar que el portapapeles realmente contiene nuestro texto antes de enviar la pulsación de tecla para pegar.

```yaml
clipboard:
  restore: true
  restore_delay_ms: 400
  defer_restore: false
  confirm_timeout_ms: 500
```

### `injection`

-   **`paste_combo`** (cadena, valor predeterminado `ctrl+v`) y **`terminal_paste_combo`** (valor predeterminado `ctrl+shift+v`): la combinación de teclas utilizada para pegar. En X11, se verifica la clase de ventana de la ventana enfocada con respecto a `terminal_window_classes` para seleccionar la correcta automáticamente; en Wayland, no hay una API para la ventana enfocada, por lo que `paste_combo` se utiliza a menos que la anule.
-   **`terminal_window_classes`** (lista): clases de ventanas que se tratan como terminales (solo en X11).
-   **`ydotool_keycodes`** (mapeo): códigos de tecla físicos de Linux, utilizados solo en la ruta de respaldo de `ydotool`. Anule estos valores si utiliza una distribución que no es QWERTY y la ruta de respaldo se está utilizando; la ruta de Wayland nominal (`wtype`) funciona con keysym y es independiente de la distribución.

```yaml
injection:
  paste_combo: "ctrl+v"
  terminal_paste_combo: "ctrl+shift+v"
  terminal_window_classes: ["konsole", "gnome-terminal-server", "xterm", "st", "alacritty", "kitty", "foot"]
  ydotool_keycodes: {}
```

### `language_settings`

Esta sección contiene configuraciones específicas para un idioma. La configuración de fábrica incluye cuatro: `en`, `fr`, `de`, `es`.

-   **`voice_commands`**: Las dos palabras `wake_phrase` y `stop_phrase` para este idioma. Dos palabras para que una oración normal nunca las active. (Las antiguas claves de una sola palabra `start_word` / `stop_word` se siguen leyendo si están presentes, para compatibilidad con versiones anteriores.)
-   **`punctuation`**: Un diccionario para insertar automáticamente la puntuación, organizado en grupos lógicos. Los signos `¿` y `¡` en español solo se insertan mediante comandos explícitos (`"abrir interrogación"`, `"abrir exclamación"`), nunca automáticamente.
-   **`typography`**: Reglas de salida específicas para cada idioma; véase más abajo.
-   **`recognition_aliases`**: Corrige errores de reconocimiento comunes de Vosk. La tabla incluida contiene solo correcciones genéricas y no controvertidas (por ejemplo, `"de points": "deux points"`); la tabla francesa también incluye los homófonos de la raya `"tirer"`, `"tirés"`, `"tirait"`, `"tirez"` (todos mapeados a `"tiret"`), porque el pequeño modelo francés transcribe así el comando de la raya. Las correcciones específicas del corpus se encuentran en `config/config.example.yaml`, para copiar y adaptar.
-   **`custom_vocabulary`**: Un diccionario para correcciones sensibles a mayúsculas y minúsculas, aplicado después de los alias (por ejemplo, `"ia": "IA"`).

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

Reemplaza lo que antes era una rama francesa codificada de forma rígida. Por idioma:

-   **`thin_space`** (booleano): inserta un espacio delgado sin ruptura (U+202F) antes de los símbolos listados en `space_before`. Usa `true` para francés, y `false` en otros casos. Desactívalo si el espacio delgado causa problemas en `grep` o en tu terminal.
-   **`space_before`** (lista): símbolos que tienen un separador al principio (un espacio delgado cuando se usa `thin_space`, de lo contrario, un espacio normal). Vacío para inglés, alemán y español.
-   **`space_after`** (lista): símbolos seguidos de un espacio.
-   **`capitalize_sentence_start`** (booleano): capitaliza la primera palabra de cada oración. En alemán, solo se capitalizan los inicios de las oraciones; los sustantivos comunes se dejan como están, ya que la capitalización de sustantivos confiable requeriría un analizador morfológico.
-   **`quote_open`** / **`quote_close`**: comillas de apertura y cierre (usa `« »` para francés, `„ "` para alemán).

### `interaction`

Cómo empieza y termina una sesión de dictado. Tres modos, uno activo a la vez:

```yaml
interaction:
  mode: toggle
  silence_timeout_ms: 700
```

-   **`mode`** (`toggle` | `maintenue` | `silence`, valor predeterminado `toggle`): el valor de fábrica no cambia respecto a versiones anteriores — un gesto inicia, un gesto distinto detiene (frase de voz, `--dictation-on` / `--dictation-off` / `--finalize`).
    -   **`maintenue`** (pulsar para hablar): el dictado dura exactamente el tiempo que se mantiene pulsada la tecla configurada en `hotkeys.push_to_talk`. Véase `hotkeys` más abajo.
    -   **`silence`**: una sola pulsación (o la frase de activación) inicia la sesión; se detiene y se copia sola una vez transcurrido `silence_timeout_ms` sin salida del decodificador, siempre que ya se haya capturado al menos una palabra. Una vacilación antes de hablar nunca finaliza una sesión vacía.
-   **`silence_timeout_ms`** (entero, valor predeterminado `700`): retraso de silencio para el modo `silence`. Se puede sobrescribir por idioma en `language_settings.<lang>.silence_timeout_ms`, con el mismo patrón que `recognition.confidence_threshold`.

En los tres modos, la frase de parada hablada y `--finalize` / `--cancel` siguen funcionando como red de seguridad — ningún modo elimina una forma existente de detener la sesión.

### `hotkeys`

Atajos de teclado globales a través de `pynput`. `pynput` observa el servidor X: se inicia en cuanto hay uno accesible y, en Wayland, solo ve las teclas de las ventanas que pasan por XWayland (muchas aplicaciones Electron y antiguas), nunca las de una ventana Wayland nativa enfocada. El listener tampoco consume el evento de teclado: la combinación llega también a la ventana enfocada, por lo que usarla con el cursor en un terminal inserta una secuencia de escape (`^[s` para `Alt+S`). Para un control que funcione en todas partes, vincule en su lugar los subcomandos de control (`--toggle`, `--finalize`, `--sleep-toggle`) a la configuración de atajos propios de su escritorio.

-   **`pynput_enabled`** (booleano, valor predeterminado `true`): Se aplica en cualquier tipo de sesión. Establecer en `false` para que el listener de `pynput` nunca se inicie.
-   **`push_to_talk`** (nombre de una sola tecla, valor predeterminado `ctrl_r`): la tecla mantenida pulsada en `interaction.mode: maintenue` (pulsar para hablar). Una sola tecla, no una combinación — soltar una tecla de una combinación es ambiguo. Mismo alcance best-effort X11/XWayland que los atajos de abajo; en Wayland nativo, vincule en su lugar una herramienta de atajos capaz de distinguir pulsación de liberación (`sway bindsym --release`, `xbindkeys`) a `vosk-cli-dictation --dictation-on` / `--finalize`.
-   **`pynput_keys`**: Una lista de teclas de Pynput para el atajo.
-   **`display_name`**: Una cadena que se muestra en el mensaje de ayuda.

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

-   **`toggle_recording`** (default `Alt+H`): starts or pauses the current dictation. While
    paused, the microphone stays active and the voice wake phrase still works.
-   **`finalize_session`** (predeterminado `Alt+S`): detiene el dictado y copia el texto
    acumulado al portapapeles. La combinación se filtra a la ventana enfocada y no llega a
    las ventanas Wayland nativas (véase más arriba) — prefiera `vosk-cli-dictation --finalize` vinculado a un atajo del escritorio.
-   **`sleep_toggle`** (default `Alt+W`): toggles **sleep mode**, a third state distinct from
    the two above. In sleep mode the audio stream is closed (the microphone is released) and
    recognition is blocked, so CPU use drops to near zero — but the wake phrase cannot be
    heard until sleep mode is toggled off again. Only the `Alt+W` hotkey itself keeps working
    while asleep, since it does not depend on audio. Triggering sleep mode while a dictation
    is in progress stops it cleanly first (as if `Alt+H` had been pressed), so no audio is
    lost mid-sentence.

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
