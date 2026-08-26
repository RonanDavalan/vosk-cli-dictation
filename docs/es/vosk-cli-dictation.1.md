% VOSK-CLI-DICTATION(1) vosk-cli-dictation | Comandos para el usuario
% Ronan Davalan
% 2026-08-26

# NOMBRE

vosk-cli-dictation: dictado de voz sin conexión, a nivel de sistema, para la línea de comandos.

# RESUMEN

**vosk-cli-dictation** [**-l** *LANG* | **--lang** *LANG*]

# DESCRIPCIÓN

**vosk-cli-dictation** es una herramienta de dictado de línea de comandos para Linux, impulsada por el motor de reconocimiento de voz offline Vosk. Escucha continuamente a través del micrófono y escribe el texto reconocido directamente en la aplicación que actualmente tiene el foco del teclado (terminal, navegador, editor o cualquier otra ventana), lo que permite que se utilice a nivel del sistema en lugar de dentro de un solo programa.

Todo el reconocimiento de voz se realiza localmente: ni el audio ni el texto transcrito se envían nunca a un servicio remoto.

La dictación se inicia y se detiene mediante la voz (una palabra de activación y una palabra de parada configurables) o mediante atajos de teclado globales, y también se puede poner en modo de suspensión para pausar completamente la captura de audio y el reconocimiento cuando no es necesaria, sin cerrar el programa.

La simulación de texto se realiza a través de **ydotool**, cuando esté disponible, o **xdotool** como alternativa. **ydotool** es compatible tanto con Wayland como con X11 a través de la interfaz `/dev/uinput`, mientras que **xdotool** solo es compatible con X11 (o Wayland a través de XWayland). Al menos uno de los dos debe estar instalado.

# OPCIONES

**-l** *LANG*, **--lang** *LANG*
:   Fuerza el idioma de la interfaz y el reconocimiento de voz para esta sesión
    (por ejemplo, `en` o `fr`), anulando el valor de `default_model`
    del archivo de configuración. *LANG* debe coincidir con el nombre de uno de
    los modelos declarados bajo `vosk_models` en el archivo de configuración.

# COMANDOS DE VOZ

La palabra de activación y la palabra de parada son configurables para cada idioma. Con la configuración predeterminada:

Inglés
:   Diga **"start"** para comenzar a dictar, **"oops"** para detener y copiar
    el resultado al portapapeles.

Francés
:   Diga **"démarre"** para comenzar a dictar, **"zut"** para detener y copiar
    el resultado al portapapeles.

La puntuación y el formato también se dictan mediante la voz; la lista completa, específica para cada idioma, se define en `language_settings.<lang>.punctuation` en el archivo de configuración, y se imprime por el propio programa al iniciarse.

# TECLAS DE ACCESO RÁPIDO

Las teclas de acceso global funcionan independientemente de la ventana que tenga el foco. La configuración predeterminada define:

**Alt+H**
:   Activa o desactiva el dictado. Solo alterna pausa/reanudación; **nunca** copia al
    portapapeles, a diferencia de **Alt+S** y de la palabra de parada más abajo. Mientras
    está en pausa, el micrófono permanece activo y la palabra de activación por voz sigue
    funcionando.

**Alt+S**
:   Detiene la dictación actual y copia el texto acumulado al portapapeles — equivalente a
    la palabra de parada.

**Alt+W**
:   Alterna el modo de suspensión, un tercer estado distinto de los dos anteriores. En modo de suspensión, la captura de audio y el reconocimiento de voz se suspenden completamente; el uso de la CPU disminuye casi a cero, pero la palabra de activación de voz no se puede escuchar hasta que se vuelve a desactivar el modo de suspensión. El atajo de teclado **Alt+W** sigue funcionando mientras está en modo de suspensión, ya que no depende del audio. Activar el modo de suspensión mientras se está realizando una dictado la detiene de forma limpia, evitando así la pérdida de audio en medio de una frase.

**Ctrl+C**
:   Salir del programa.

Las tres primeras combinaciones de teclas son configurables en la sección `hotkeys` del archivo de configuración. **Ctrl+C** no lo es: es la señal de interrupción estándar, siempre activa, nunca reasignable mediante configuración.

# COMANDOS MANUALES

Mientras el programa se está ejecutando, escribir uno de los siguientes comandos en su ventana de terminal y presionar Enter también le permite controlarlo:

**/cancel**
:   Detiene la sesión de grabación actual sin generar ninguna salida de texto.

**/delete-word**
: Elimina la última palabra que se escribió.

**/nl**
:   Insertar una nueva línea (simula presionar la tecla Enter).

# CONFIGURACIÓN

El comportamiento en tiempo de ejecución está controlado por un archivo de configuración YAML: modelos de voz disponibles, parámetros de audio, umbral de confianza de reconocimiento, comandos de voz y puntuación específicos para cada idioma, atajos de teclado, sonido de notificación y tema de color de la consola.

El archivo de configuración se encuentra mediante la primera regla que coincida; una vez que una regla coincide, las reglas restantes no se consultan.

1. La ruta especificada en la variable de entorno **VOSK_CONFIG**, si está definida. Se utiliza tal cual; nunca se crea automáticamente.
2. `config/config.yaml`, relativo al directorio del proyecto, cuando se ejecuta desde un repositorio Git (modo de desarrollo).
3. `$XDG_CONFIG_HOME/vosk-cli-dictation/config.yaml` (por defecto `~/.config/vosk-cli-dictation/config.yaml`). Se crea automáticamente en la primera ejecución, a partir de la plantilla predeterminada, cuando se instala desde el paquete Debian.
4. La plantilla predeterminada que se incluye en el paquete, de solo lectura.

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
:   Archivo de configuración que se utiliza al ejecutar desde un repositorio Git.

`vosk-model/`
:   Ubicación predeterminada donde se buscan los modelos acústicos de Vosk cuando se ejecuta desde un repositorio Git.

# ESTADO DE SALIDA

**0**
: El programa finalizó correctamente, incluso después de presionar **Ctrl+C**.

No nulo
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

Modelos y descargas de Vosk: *https://alphacephei.com/vosk/models*

Página de inicio del proyecto: *https://vosk.davalan.fr/*

# ERRORES

Reporte los errores en el rastreador de problemas del proyecto:
*https://github.com/RonanDavalan/vosk-cli-dictation/issues*

# AUTOR

Ronan Davalan, y los colaboradores listados en CONTRIBUTORS.md.
