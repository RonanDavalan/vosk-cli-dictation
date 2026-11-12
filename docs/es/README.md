# Vosk-CLI-Dictation

<p align="center">
  <a href="https://github.com/RonanDavalan/vosk-cli-dictation/blob/main/LICENSE"><img src="https://img.shields.io/badge/Licencia-MIT-blue.svg" alt="Licencia: MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/Version-v0.5.4--beta-yellow.svg" alt="Version: v0.5.4-beta"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+"></a>
  <a href="#"><img src="https://img.shields.io/badge/Linux-Debian_%C2%B7_Fedora_%C2%B7_openSUSE_%C2%B7_Arch-blue.svg" alt="Paquetes nativos para Debian, Fedora, openSUSE y Arch Linux"></a>
  <a href="#"><img src="https://img.shields.io/badge/Contribuciones-Bienvenidas-brightgreen.svg" alt="Contribuciones bienvenidas"></a>
</p>

[English](../../README.md) | [Français](../fr/README.md) | [Deutsch](../de/README.md) | **Español**

<p align="center">
  <a href="https://vosk.davalan.fr/"><strong>¡Visita la página de inicio oficial para un recorrido completo!</strong></a>
</p>

<p align="center">
  <a href="https://vosk.davalan.fr/"><strong>▶ Mira el vídeo de demostración en la página de inicio</strong></a>
</p>

Una herramienta de dictado por línea de comandos, potente y personalizable, para Linux, basada en el motor Vosk. Convierte tu voz en texto directamente en tu terminal y haz que aparezca en cualquier aplicación.

---

## ¿Por qué este proyecto?

Esta herramienta nació de la necesidad de un sistema de dictado robusto, ejecutado en local en GNU/Linux, que dé al usuario el control total de sus datos y del comportamiento del software. A diferencia de las soluciones en la nube, funciona **al 100 % sin conexión**, lo que garantiza tu privacidad.

## Características principales

*   **Integración en todo el sistema:** dicta en cualquier aplicación activa (terminal, navegador, editor de código, etc.).
*   **Compatibilidad con varios idiomas:** funciona desde la instalación con **inglés**, **francés**, **alemán** y **español**.
*   **Control universal:** una sesión en curso se maneja por un socket Unix privado; el mismo comando vinculado a un atajo del escritorio (`vosk-cli-dictation --toggle`, `--sleep`, `--status`) la controla en cualquier escritorio, Wayland nativo incluido. Los atajos globales de `pynput` siguen siendo una comodidad de mejor esfuerzo: bajo Wayland solo llegan a las ventanas de XWayland, no a las ventanas nativas de Wayland.
*   **Totalmente personalizable:** configura los colores de la interfaz, los atajos, las frases de activación por voz, la tipografía por idioma y los alias de reconocimiento en un sencillo archivo `config.yaml`.
*   **Puntuación completa:** dicta toda la gama de signos de puntuación con órdenes de voz naturales.
*   **Privado y sin conexión:** se ejecuta por completo en tu máquina. Tu voz nunca sale de tu ordenador.

> [!NOTE]
>
> **Compatibilidad con X11 y Wayland.** El texto se inyecta copiándolo al portapapeles y simulando un pegado. Bajo Wayland la herramienta usa `wtype` y `wl-clipboard`, con `ydotool` como alternativa (que necesita el demonio `ydotoold` y acceso a `/dev/uinput`, normalmente mediante el grupo `input` — `sudo usermod -aG input $USER`, y después cerrar sesión y volver a entrar). Bajo X11 usa `xdotool`. Debe instalarse al menos un motor para el tipo de sesión actual; `vosk-cli-dictation --diagnose` indica lo que está disponible.
>
> **Atajos globales.** `pynput` vigila el servidor X: bajo Wayland solo ve las teclas de las ventanas que pasan por XWayland (muchas aplicaciones Electron y antiguas), nunca las de una ventana nativa de Wayland que tenga el foco. Tampoco consume los eventos: la combinación de teclas llega también a la ventana con el foco, de modo que pulsarla al escribir en un terminal inserta una secuencia de escape (`^[s` para `Alt+S`). Para un control que funcione en todas partes, vincula en su lugar los ajustes de atajos de tu escritorio a los subcomandos de control (`vosk-cli-dictation --toggle`, `--finalize`, `--sleep-toggle`). Consulta *Controlar una sesión en curso* más abajo. En Debian, `ydotool` está empaquetado en `trixie-backports`, no en la versión estable.

## Primeros pasos

### Instalar el paquete nativo (recomendado)

Instala el paquete construido para tu distribución desde la
[página de descargas](https://vosk.davalan.fr/) — sin configuración manual, sin
entorno virtual que crear:

```bash
# Debian 12+ y derivadas (Ubuntu 24.04+, Mint 22+...)
sudo apt install ./vosk-cli-dictation_0.5.4~beta_all.deb

# Fedora
sudo dnf install ./vosk-cli-dictation-0.5.4~beta-1.fc42.noarch.rpm

# openSUSE (Leap)
sudo zypper install ./vosk-cli-dictation-0.5.4~beta-1.leap156.noarch.rpm

# Arch Linux
sudo pacman -U ./vosk-cli-dictation-0.5.4_beta-1-any.pkg.tar.zst
```

La primera vez que se configura el paquete, construye un entorno virtual privado e instala en él el motor Vosk (este paso necesita acceso a la red).

Después descarga un modelo de voz y empieza a dictar:

```bash
vosk-cli-dictation --download-model fr   # también: en, de, es
vosk-cli-dictation -l fr
```

Añade `--model-size big` para el modelo completo (`vosk-cli-dictation --download-model fr --model-size big`): de 1,4 a 1,9 GB según el idioma, y unas tres veces ese tamaño de espacio libre en disco mientras se descomprime.

Si inicias la herramienta sin ningún modelo instalado, ofrece la descarga de forma interactiva. Un modelo ausente se señala sin ser fatal, mientras se cargue un idioma. Los modelos descargados se verifican con SHA256 y se guardan en `~/.local/share/vosk-models/`.

El paquete trae `xdotool` (X11) o `ydotool` (alternativa de Wayland) para la inyección del texto. Para Wayland nativo, instala además el motor preferido con el gestor de paquetes de tu distribución (ejemplo de Debian):

```bash
sudo apt install wtype wl-clipboard
```

`ydotool` exige que tu usuario esté en el grupo `input` (`sudo usermod -aG input $USER`, y después cerrar sesión y volver a entrar); `xdotool` y `wtype` no lo exigen. Ejecuta `vosk-cli-dictation --diagnose` para ver qué motor, qué entrada de audio y qué acceso al portapapeles están disponibles.

> [!NOTE]
> Si `apt` muestra una advertencia de sandbox o de permisos de `_apt`, es porque el `.deb` está dentro de tu directorio personal, que el usuario `_apt` no puede leer. Cópialo primero a `/tmp/` e instálalo desde allí. La instalación se completa en ambos casos.

### Instalar desde las fuentes (para el desarrollo)

Esta vía ejecuta el código directamente desde una copia de trabajo de git. Los paquetes del sistema de abajo son los de Debian; en Fedora, openSUSE o Arch, instala los equivalentes con tu gestor de paquetes.

```bash
sudo apt-get update && sudo apt-get install python3-pip python3-venv portaudio19-dev gettext xdotool pulseaudio-utils
# Wayland, opcional: sudo apt-get install wtype wl-clipboard ydotool

git clone https://github.com/RonanDavalan/vosk-cli-dictation.git
cd vosk-cli-dictation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Descarga un modelo y ejecuta el script:

```bash
python3 src/main.py --download-model fr   # también: en, de, es
python3 src/main.py -l fr                 # el idioma por defecto viene de config.yaml
python3 src/main.py --diagnose            # comprobar el entorno sin iniciar una sesión
```

Los modelos descargados así también quedan en `~/.local/share/vosk-models/`. Como alternativa, también se tiene en cuenta una carpeta de modelo (por ejemplo `vosk-model-small-fr-0.22`) colocada directamente en el directorio `vosk-model/` del proyecto.

Solo se ejecuta una sesión por usuario a la vez; un segundo arranque se rechaza y te remite a `--status`.

### Consejo: crear un comando de arranque rápido (opcional)

Para acceder con más facilidad, puedes añadir una función al archivo de configuración de tu intérprete de comandos (por ejemplo `~/.bashrc` o `~/.zshrc`).

1.  Abre tu archivo de configuración: `nano ~/.bashrc`
2.  Añade las líneas siguientes al final. **Recuerda sustituir `/path/to/your/vosk-cli-dictation` por la ruta absoluta real del directorio del proyecto.**

    ```bash
    # Define un comando 'vosk' para lanzar fácilmente el script de dictado.
    vosk() {
        # Comprueba que el directorio del proyecto existe
        if [ -d "/path/to/your/vosk-cli-dictation" ]; then
            cd "/path/to/your/vosk-cli-dictation" && \
            source venv/bin/activate && \
            python3 src/main.py "$@" && \
            deactivate
        else
            echo "Error: directorio del proyecto no encontrado: /path/to/your/vosk-cli-dictation"
        fi
    }
    ```

3.  Aplica los cambios con `source ~/.bashrc` o abriendo un terminal nuevo.
4.  Ya puedes lanzar la aplicación desde cualquier sitio escribiendo simplemente `vosk` o `vosk -l en`.

## Uso y configuración

### Selección del idioma

El modelo de idioma se elige según el orden de prioridad siguiente:

1.  **Opción de línea de comandos (prioridad más alta):** usa `-l en`, `-l fr`, `-l de` o `-l es` para imponer un idioma en la sesión.
2.  **Elección recordada:** un idioma o modelo elegido mientras una sesión está en marcha (`set-lang`, `set-model`, véase más abajo) se guarda en `~/.local/state/vosk-cli-dictation/selection.yaml` y se reutiliza en el siguiente arranque.
3.  **`default_model` de `config.yaml`:** un código de idioma, o `system` —el valor de fábrica, que también se usa si falta la clave—, que sigue el idioma de la sesión (`LC_ALL`, `LC_MESSAGES` y luego `LANG`) si hay un modelo instalado para él, y el inglés en caso contrario.

### Frases de activación por voz

Cada idioma tiene una **frase de activación** y una **frase de parada** de dos palabras (valores de fábrica: `start dictation` / `stop dictation` en inglés). Dos palabras en lugar de una, para que una frase corriente nunca las dispare por accidente. Di la frase de activación para empezar a dictar y la frase de parada para terminar y copiar el resultado. Decir una frase dos veces seguidas (`stop dictation stop dictation`) la escribe literalmente en lugar de dispararla. Si la frase de parada se oye con una confianza de reconocimiento baja, se descarta en lugar de escribirse en tu documento: repítela o usa `--finalize`. Las frases se configuran por idioma en `language_settings.<lang>.voice_commands`.

### Modos de activación

`interaction.mode` (por defecto `toggle`, sin cambios respecto a versiones anteriores) elige cómo empieza y termina una sesión: un gesto empieza y otro gesto termina. Otros dos modos: `maintenue` (pulsar para hablar — el dictado dura mientras `hotkeys.push_to_talk` siga pulsado) y `silence` (una sola pulsación empieza; la sesión termina y copia el texto por sí misma cuando pasa `interaction.silence_timeout_ms` sin salida del decodificador, en cuanto se ha captado una palabra). La frase de parada hablada y `--finalize`/`--cancel` siguen funcionando como red de seguridad en todos los modos. La referencia completa está en [`configuration.md`](configuration.md#interaction).

### Controlar una sesión en curso

La sesión abre un socket Unix privado en `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock` (modo `0600`). Ejecutar el **mismo comando** con una opción de control se conecta a él, realiza la acción, muestra el estado y termina:

```bash
vosk-cli-dictation --status          # -> OK ÉCOUTE
vosk-cli-dictation --info            # -> OK {"state":"ÉCOUTE","lang":"fr",…}  (estado completo, una línea JSON)
vosk-cli-dictation --toggle          # empezar/parar el dictado
vosk-cli-dictation --sleep-toggle    # entrar en el modo reposo o salir de él (libera el micrófono)
vosk-cli-dictation --finalize        # parar y copiar el texto acumulado
vosk-cli-dictation --stop            # cerrar la sesión
```

Vincula estos comandos a los ajustes de atajos de teclado de tu escritorio (KDE, GNOME, Sway, labwc…) para obtener un control global que funcione en todas partes, incluidas las ventanas nativas de Wayland que `pynput` no puede ver. Los atajos de `pynput` de la sección `hotkeys` también funcionan como comodidad de mejor esfuerzo — bajo Wayland, solo sobre ventanas de XWayland.

### Cambiar de idioma y de modelo sin reiniciar

Una sesión en curso cambia de idioma o de modelo sin reiniciar, y el texto ya escrito se conserva. Dos peticiones lo hacen: `set-lang fr|en|de|es|system` y `set-model <carpeta del modelo>` (un nombre de carpeta de la lista `models` que muestra `--info`). El modelo nuevo se carga en segundo plano mientras el actual sigue sirviendo, y lo reemplaza entre dos enunciados; si la carga falla, se mantiene el modelo actual y `last_error` en `--info` dice por qué. La elección se recuerda en `selection.yaml` (véase la selección del idioma). Las peticiones van directamente al socket; sirve cualquier herramienta que escriba una línea en un socket Unix, aquí `socat`:

```bash
printf 'set-lang en\n' | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/vosk-cli-dictation.sock   # -> OK ÉCOUTE
vosk-cli-dictation --info            # lang, model, models, loading, last_error…
```

Errores: `ERR bad-argument` (argumento desconocido), `ERR no-model` (no hay modelo instalado para la petición), `ERR busy` (hay una carga en curso).

### Comandos manuales

Mientras el script se ejecuta en un terminal, también puedes escribir estos comandos y pulsar Intro:

*   `/cancel`: detiene la sesión de grabación en curso sin producir texto.
*   `/delete-word`: borra la última palabra escrita.
*   `/nl`: inserta un salto de línea (simula pulsar la tecla Intro).

### Personalización

Todos los ajustes se pueden modificar en el archivo `config/config.yaml`: atajos, colores de la interfaz, frases de activación por voz, tipografía por idioma y alias de reconocimiento. Algunos ejemplos de alias propios de un corpus están en `config/config.example.yaml`. La referencia completa está en [`configuration.md`](configuration.md).

## Contribuir

Este proyecto es de código abierto y las contribuciones se fomentan mucho. Consulta nuestra **[Guía de contribución](../../CONTRIBUTING.md)** y abre una incidencia en la [página de incidencias](https://github.com/RonanDavalan/vosk-cli-dictation/issues).

Este proyecto se construye en una colaboración asimétrica entre humano y LLM — los roles implicados están en [CONTRIBUTORS.md](../../CONTRIBUTORS.md).

## Créditos

Este proyecto se construye en una colaboración entre humano y LLM, con los roles escritos tal como se desempeñaron realmente. La lista completa está en [CONTRIBUTORS.md](../../CONTRIBUTORS.md).

*   **Ronan Davalan** — Arquitecto y árbitro: visión, requisitos de seguridad, validación y pruebas.
*   **Claude Code (Anthropic)** — Ingeniero de sistemas y desarrollador principal: autor principal del código fuente desde la v0.5.0-alpha, del empaquetado Debian y de las herramientas.
*   **Gemini (Google)** — Sintetizador y asesor estratégico.
*   **Grok (xAI)** — Validador externo.
*   **GLM-5.3** — Auditor del núcleo de interacción (auditoría cruzada a ciegas).
*   **DeepSeek V4 Flash (vía OpenCode)** — Revisor de la documentación y del sitio, probador.

## Licencia

Este proyecto se distribuye bajo la **licencia MIT**. Consulta el archivo [LICENSE](../../LICENSE) para más detalles.
