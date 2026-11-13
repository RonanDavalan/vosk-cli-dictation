% VOSK-CLI-DICTATION-TRAY(1) vosk-cli-dictation | Comandos de usuario
% Ronan Davalan
% 2026-11-12

# NOMBRE

vosk-cli-dictation-tray - icono de micrófono del área de notificación para vosk-cli-dictation

# SINOPSIS

**vosk-cli-dictation-tray** [**--socket** *RUTA*] [**--dictation-command** *COMANDO*]

**vosk-cli-dictation-tray** **--version**

# DESCRIPCIÓN

**vosk-cli-dictation-tray** muestra un micrófono en el área de notificación del escritorio (KDE Plasma de forma nativa; GNOME con la
extensión «AppIndicator and KStatusNotifierItem Support») y maneja una sesión **vosk-cli-dictation** en curso por su socket de control.
Es un programa aparte: el dictado nunca lo necesita, y él solo necesita el socket. Pregunta a la sesión por `info` cuatro veces por
segundo; un socket ausente significa que no hay ningún dictado en marcha. Las etiquetas del menú siguen el idioma del dictado en curso, o
el idioma de la sesión cuando no hay ninguno, desde los mismos catálogos gettext que el dictado.

Sin área de notificación, muestra una notificación de escritorio que explica cómo activar una y sigue funcionando: el icono aparece si el
área llega más tarde. Solo corre un icono por socket.

# OPCIONES

**--socket** *RUTA*
:   Socket de control que manejar. Por defecto: `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock`, el del dictado propio del usuario.

**--dictation-command** *COMANDO*
:   Comando que inicia el dictado, dividido como una línea de comandos de shell. Por defecto: la variable de entorno
    `VOSK_CLI_DICTATION_COMMAND`, luego **vosk-cli-dictation** del `PATH`, luego la copia de la rama Git.

**--version**
:   Muestra la versión y sale.

# ESTADOS DEL ICONO

El color y la forma dan el estado, de modo que el icono sigue siendo legible para una persona daltónica.

micrófono rojo rodeado de ondas
:   `DICTÉE`: el micrófono está abierto y la voz se escribe.

micrófono naranja
:   `ÉCOUTE`: el micrófono está abierto, el dictado está cortado, se espera la frase de activación.

micrófono azul bajo una luna creciente
:   `VEILLE`: el micrófono está liberado.

micrófono verde en contorno
:   No hay ningún dictado en marcha.

Un clic izquierdo inicia el dictado si no hay ninguno, y lo alterna en caso contrario. La información emergente repite la línea de
estado y dice «cargando el modelo…» mientras se carga un modelo.

# MENÚ

El menú del clic derecho, en este orden:

1.  una línea de estado: estado, idioma, motor;
2.  iniciar o detener el dictado; entrar en reposo profundo o salir de él; terminar y copiar el texto; cancelar la sesión;
3.  **Idioma**: seguir el sistema, o francés, inglés, alemán, español; un idioma sin modelo instalado dice «por descargar»;
4.  **Modelo**: ligero o completo; un modelo ausente muestra su tamaño, y elegirlo inicia su descarga, con una notificación al terminar;
5.  **Refinado**: *Ninguno* y los tamaños de Whisper, cada uno marcado `GPU` o `CPU`; en gris con su motivo cuando falta `faster-whisper`; el primer uso de un tamaño descarga sus pesos, con una notificación al principio y al final. **Corrección**: en gris con su motivo mientras el dictado en curso no anuncie opciones;
6.  volver a la configuración (olvidar la elección recordada);
7.  activar el dictado por voz o salir de él (iniciado separado de cualquier terminal); iniciar el icono al abrir la sesión; salir del icono.

Mientras se carga un modelo, las elecciones que lo cambian están en gris.

# ARCHIVOS

`~/.local/state/vosk-cli-dictation/instance.log`
:   Salida del dictado iniciado desde el icono, y de las descargas de modelo que arranca.

`~/.config/autostart/vosk-cli-dictation-tray.desktop`
:   La entrada XDG Autostart que escribe «Iniciar el icono al abrir la sesión» (`Hidden=true` con la casilla desmarcada).

`$XDG_RUNTIME_DIR/vosk-cli-dictation.sock`
:   El socket de control del dictado.

# VEA TAMBIÉN

**vosk-cli-dictation**(1)

# ERRORES

Informe de los errores en el sistema de seguimiento de incidencias del proyecto:
*https://github.com/RonanDavalan/vosk-cli-dictation/issues*

# AUTOR

Ronan Davalan y los colaboradores mencionados en CONTRIBUTORS.md.
