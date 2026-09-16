% VOSK-CLI-DICTATION(1) vosk-cli-dictation | Comandos de usuario
% Ronan Davalan
% 2026-09-10

# NOMBRE

vosk-cli-dictation: dictado de voz sin conexión para la línea de comandos, disponible a nivel de sistema.

# SINOPSIS

**vosk-cli-dictation** [**-l** *LANG* | **--lang** *LANG*]

**vosk-cli-dictation** **\--diagnose**

**vosk-cli-dictation** **\--download-model** [*LANG*]

**vosk-cli-dictation** {**\--status** | **\--toggle** | **\--dictation-on** | **\--dictation-off** | **\--finalize** | **\--cancel** | **\--sleep** | **\--wake** | **\--sleep-toggle** | **\--stop**}

# DESCRIPCIÓN

**vosk-cli-dictation** es una herramienta de dictado de línea de comandos para Linux, impulsada por el motor de reconocimiento de voz offline Vosk. Escucha continuamente a través del micrófono y escribe el texto reconocido directamente en la aplicación que actualmente tiene el foco del teclado (terminal, navegador, editor o cualquier otra ventana), lo que permite que se utilice a nivel de sistema en lugar de dentro de un solo programa.

Todo el reconocimiento de voz se realiza localmente: ni el audio ni el texto transcrito se envían nunca a un servicio remoto.

La función de dictado se inicia y se detiene mediante la voz (una frase de activación y una frase de detención configurables, según el idioma) o a través de subcomandos que se pueden asignar a un atajo de teclado en el escritorio. Además, se puede poner en modo de espera para liberar completamente el micrófono y suspender el reconocimiento cuando no sea necesario, sin tener que cerrar el programa.

Solo una sesión se ejecuta por usuario a la vez. Abre un socket Unix privado en `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock` (modo `0600`); el mismo comando
invocado con una bandera de control (ver CONTROLANDO UNA SESIÓN EN EJECUCIÓN) se conecta a ese socket en lugar de iniciar una nueva sesión.

El texto se inyecta colocándolo en el portapapeles y simulando un pegado, por lo que se necesitan dos tipos de herramienta: un simulador de pulsaciones y una herramienta de portapapeles.
Bajo Wayland son **wtype** y **wl-clipboard**; si falta **wtype**, la pulsación recurre a **ydotool** (que necesita el demonio `ydotoold` y acceso a `/dev/uinput`), pero **wl-clipboard** sigue siendo necesario. Bajo X11 son **xdotool** y **xclip**. El paquete Debian depende de **wl-clipboard** y recomienda **xclip**; una copia de Git debe instalarlos por su cuenta. Sin una herramienta de portapapeles, el texto dictado nunca llega al portapapeles y el pegado reinserta lo último que se copió a mano. Añadir su usuario al grupo `input` solo es necesario para el respaldo de **ydotool**; **wtype** y **xdotool** no lo necesitan. **vosk-cli-dictation \--diagnose**
informa qué herramientas, dispositivo de audio y acceso al portapapeles están disponibles, y luego finaliza.

Las combinaciones de teclas globales a través de `pynput` observan el servidor
X: en Wayland solo alcanzan las ventanas que pasan por XWayland, nunca una
ventana Wayland nativa enfocada. Vincule los subcomandos de control a la
configuración de acceso directo propia de su escritorio para un control que
funcione en todas partes.

# OPCIONES

**-l** *LANG*, **--lang** *LANG*
:   Fuerza el idioma de la interfaz y el reconocimiento de voz para esta sesión
    (`en`, `fr`, `de` o `es`), sobrescribiendo el valor de `default_model`
    del archivo de configuración. *LANG* debe coincidir con el nombre de uno de los
    modelos declarados en `vosk_models` en el archivo de configuración.

**\--diagnose**
:   Verifique el entorno (tipo de sesión, backend de inyección, herramientas, modelos,
    entrada de audio, portapapeles, socket de control) y salga. El código de salida es `0`
    cuando todas las verificaciones se aprueban.

**\--download-model** [*LANG*]
:   Descarga el modelo pequeño de Vosk para *LANG* (o el idioma actual si se
    omite) en `~/.local/share/vosk-models/`, verificando su suma de
    comprobación, y luego sale. También se ofrece un modelo de forma
    interactiva en el primer inicio cuando no hay ninguno instalado.

# CONTROLANDO UNA SESIÓN EN CURSO

Cada una de las siguientes opciones de configuración se conecta al socket de la sesión en ejecución,
realiza la acción, imprime el estado resultante (`OK DICTÉE`,
`OK ÉCOUTE`, `OK VEILLE`) o `ERR <reason>`, y finaliza. Están diseñadas para
ser asignadas a atajos de teclado del escritorio.

**\--status**
:   Imprimir el estado actual sin modificarlo.

**\--toggle**
:   Alterna entre el modo de dictado (DICTÉE) y el modo de escucha (ÉCOUTE).

**\--dictation-on**, **\--dictation-off**
:   Activar o desactivar el dictado por voz.

**\--finalize**
:   Detenga la dictación y copie el texto acumulado; equivalente a la
    frase de parada.

**\--cancel**
:   Descartar el búfer de la sesión actual sin escribir nada.

**\--sleep**, **\--wake**, **\--sleep-toggle**
:   Entrar, salir o activar/desactivar el modo de suspensión (VEILLE).

**\--stop**
:   Cerrar la sesión en ejecución de forma limpia.

# COMANDOS DE VOZ

La frase de activación y la frase de detención constan de dos palabras cada una, y son configurables por idioma en `language_settings.<lang>.voice_commands`. Se utilizan dos palabras en lugar de una para evitar que una oración común las active accidentalmente. Con la configuración de fábrica:

Inglés
:   Diga **"start dictation"** para comenzar y **"stop dictation"** para terminar y copiar el resultado al portapapeles.

Francés
:   **"active dictée"** / **"stop dictée"**.

Alemán
:   **"diktat starten"** / **"diktat stoppen"**.

Español
:   **"iniciar dictado"** / **"terminar dictado"**.

Una frase disparadora solo se activa cuando la confianza promedio de reconocimiento
de sus palabras supera el umbral `recognition.confidence_threshold` (valor predeterminado
`0.55`, redefinible por idioma). Una frase de parada oída por debajo del umbral se
descarta — ni se ejecuta ni se escribe en el documento — y se muestra una indicación;
repítala o use `--finalize`. Durante el dictado, un segundo reconocedor ligero
restringido a la frase de parada proporciona una parada de alta confianza independiente
de ese umbral (`recognition.restricted_stop_in_dictation`, activo de forma predeterminada,
redefinible por idioma). Decir una frase dos veces consecutivas la transcribe
literalmente en lugar de activarla.

La puntuación y la disposición también se dictan mediante la voz; la lista completa, específica para cada idioma, se define en `language_settings.<lang>.punctuation` en el archivo de configuración, y se imprime por el propio programa al iniciarse.

# MODOS DE ACTIVACIÓN

`interaction.mode` en el archivo de configuración elige cómo empieza y termina una sesión de dictado. Por defecto `toggle`, sin cambios respecto a versiones anteriores: un gesto inicia, un gesto distinto detiene (frase de voz, atajo o subcomando de control). Otros dos modos:

**maintenue**
:   Pulsar para hablar. El dictado dura exactamente el tiempo que se mantiene pulsada la tecla configurada en `hotkeys.push_to_talk` (por defecto `ctrl_r`, una sola tecla, no una combinación). Alcance best-effort X11/XWayland, como los atajos de abajo; en Wayland nativo, vincule en su lugar una herramienta de atajos capaz de distinguir pulsación de liberación (`sway bindsym --release`, `xbindkeys`) a **\--dictation-on** / **\--finalize**.

**silence**
:   Una sola pulsación (o la frase de activación) inicia la sesión; se detiene y se copia sola una vez transcurrido `interaction.silence_timeout_ms` (por defecto `700`, sobrescribible por idioma) sin salida del decodificador, siempre que ya se haya capturado al menos una palabra — una vacilación antes de hablar nunca finaliza una sesión vacía.

En los tres modos, la frase de parada hablada y **\--finalize** / **\--cancel** siguen funcionando como red de seguridad.

# TECLAS DE ACCESO RÁPIDO

Los atajos de teclado globales de `pynput` se inician en cuanto un servidor X está accesible y `hotkeys.pynput_enabled` es verdadero. `pynput` observa el servidor X, así que en Wayland los atajos solo alcanzan las ventanas que pasan por XWayland (muchas aplicaciones Electron y antiguas), nunca una ventana Wayland nativa enfocada; los subcomandos de control asociados a un acceso directo del escritorio cubren todas las ventanas. El listener de `pynput` tampoco consume el evento de teclado: la combinación llega también a la ventana enfocada, por lo que usarla con el cursor en un terminal inserta una secuencia de escape (por ejemplo `^[s` para **Alt+S**). Para una parada limpia desde cualquier ventana, vincule en su lugar **\--finalize** (o **\--toggle**, **\--sleep-toggle**) a un atajo de teclado del escritorio. La configuración predeterminada define:

**Alt+H**
:   Activa o desactiva el dictado. Esto solo pausa o reanuda; **no**
    copia nada al portapapeles, a diferencia de **Alt+S** y la frase de parada.
    Mientras está pausado, el micrófono permanece activo y la frase de activación
    sigue funcionando.

**Alt+S**
: Detiene el dictado actual y copia el texto acumulado al portapapeles; equivalente a la frase de parada. La combinación también se filtra a la ventana enfocada (véase más arriba) y no llega a las ventanas Wayland nativas; prefiera **\--finalize** vinculado a un atajo del escritorio.

**Alt+W**
:   Activa/desactiva el modo de suspensión, un tercer estado distinto de los dos anteriores. En el modo de suspensión, el flujo de audio se cierra (el micrófono se libera) y el reconocimiento se bloquea, por lo que el uso de la CPU disminuye hasta casi cero; la frase de activación no se puede escuchar hasta que el modo de suspensión se desactiva. **Alt+W** sigue funcionando mientras está en modo de suspensión, ya que no depende del audio. Activar el modo de suspensión durante una dictado la detiene limpiamente primero, para que no se pierda audio en medio de una frase.

**Ctrl+C**
:   Salir del programa.

Las tres primeras teclas de acceso directo son configurables en la sección `hotkeys` del
archivo de configuración. **Ctrl+C** no lo es: es la señal de interrupción estándar, siempre activa y
nunca remapeada a través de la configuración.

`hotkeys.push_to_talk` (por defecto `ctrl_r`) es una cuarta entrada, de una sola tecla, usada solo cuando `interaction.mode` vale `maintenue` — véase MODOS DE ACTIVACIÓN más arriba.

# COMANDOS MANUALES

Mientras el programa se está ejecutando, escribir uno de los siguientes comandos en su ventana de terminal y presionar Enter también le permite controlarlo:

**/cancel**
:   Detener la sesión de grabación actual sin generar ninguna salida de texto.

**/delete-word**
: Elimina la última palabra que se escribió.

**/nl**
:   Insertar una nueva línea (simula presionar la tecla Enter).

# CONFIGURACIÓN

El comportamiento en tiempo de ejecución se controla mediante un archivo de configuración YAML: modelos de voz disponibles, parámetros de audio, umbral de confianza de reconocimiento, comandos de voz y puntuación específicos para cada idioma, atajos de teclado, sonido de notificación y tema de color de la consola.

El archivo de configuración se encuentra mediante la primera regla que coincida; una vez que una regla coincide, las reglas restantes no se consultan.

1. La ruta especificada en la variable de entorno **VOSK_CONFIG**, si está definida. Se utiliza tal cual; nunca se crea automáticamente.
2. `config/config.yaml`, relativa al directorio del proyecto, cuando se ejecuta desde un repositorio Git (modo de desarrollo).
3. `$XDG_CONFIG_HOME/vosk-cli-dictation/config.yaml` (predeterminado
   `~/.config/vosk-cli-dictation/config.yaml`). Se crea automáticamente en la primera ejecución, a partir de la plantilla predeterminada, cuando se instala desde el paquete Debian.
4. La plantilla predeterminada incluida en el paquete, de solo lectura.

El idioma activo se elige, en el siguiente orden: la opción **--lang**, si se proporciona; de lo contrario, el idioma detectado por el sistema operativo; de lo contrario, el valor **`default_model`** del archivo de configuración.

Consulte **configuration.md** en la documentación del proyecto para obtener la
referencia completa de cada clave de configuración.

# ARCHIVOS

`~/.config/vosk-cli-dictation/config.yaml`
:   Archivo de configuración por usuario (instalación del paquete Debian).

`/usr/share/vosk-cli-dictation/config.yaml`
:   Plantilla de configuración de fábrica (instalación de paquete Debian), de solo lectura.

`~/.local/share/vosk-models/`
:   Ubicación predeterminada donde se buscan los modelos acústicos de Vosk (instalación del paquete Debian).

`config/config.yaml`
:   Archivo de configuración utilizado al ejecutar desde un repositorio Git.

`vosk-model/`
:   Ubicación predeterminada donde se buscan los modelos acústicos de Vosk cuando se ejecuta desde un repositorio Git.

`$XDG_RUNTIME_DIR/vosk-cli-dictation.sock`
:   Socket de control de la sesión en ejecución (modo `0600`). Se elimina al
    salir correctamente; un socket obsoleto dejado por un fallo se detecta y
    se reemplaza al iniciar la próxima vez.

# ESTADO DE SALIDA

**0**
: El programa finalizó correctamente, incluso después de presionar **Ctrl+C**.

No nulo.
:   Error al iniciar: ni **ydotool** ni **xdotool** están disponibles, no se pudo cargar ningún modelo de reconocimiento de voz, o no se pudo abrir el dispositivo de audio.

# EJEMPLOS

Comience con el idioma predeterminado del archivo de configuración:

```
vosk-cli-dictation
```

Fuerza en inglés para esta sesión:

```
vosk-cli-dictation --lang en
```

# VEA TAMBIÉN

Modelos de Vosk y descargas: *https://alphacephei.com/vosk/models*

Página de inicio del proyecto: *https://vosk.davalan.fr/*

# ERRORES

Informe los errores en el rastreador de problemas del proyecto:
*https://github.com/RonanDavalan/vosk-cli-dictation/issues*

# AUTOR

Ronan Davalan, y los colaboradores mencionados en CONTRIBUTORS.md.
