# Vosk-CLI-Dictation

<p align="center">
  <a href="https://github.com/RonanDavalan/vosk-cli-dictation/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/Version-v0.5.4--beta-yellow.svg" alt="Version: v0.5.4-beta"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+"></a>
  <a href="#"><img src="https://img.shields.io/badge/Linux-Debian_%C2%B7_Fedora_%C2%B7_openSUSE_%C2%B7_Arch-blue.svg" alt="Native packages for Debian, Fedora, openSUSE and Arch Linux"></a>
  <a href="#"><img src="https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg" alt="Contributions Welcome"></a>
</p>

**English** | [Français](docs/fr/README.md) | [Deutsch](docs/de/README.md) | [Español](docs/es/README.md)

<p align="center">
  <a href="https://vosk.davalan.fr/"><strong>Visit the Official Homepage for a full tour!</strong></a>
</p>

<p align="center">
  <a href="https://vosk.davalan.fr/"><strong>▶ Watch the demonstration video on the homepage</strong></a>
</p>

A powerful and customizable command-line dictation tool for Linux, powered by the Vosk engine. Turn your speech into text directly in your terminal and have it appear in any application.

---

## Why This Project?

This tool was born from the need for a robust, locally-run dictation system on GNU/Linux that gives the user full control over their data and the software's behavior. Unlike cloud-based solutions, it operates **100% offline**, guaranteeing your privacy.

## Key Features

*   **System-Wide Integration:** Dictate into any active application (terminal, browser, code editor, etc.).
*   **Multi-Language Support:** Works out-of-the-box with **English**, **French**, **German** and **Spanish**.
*   **Universal Control:** A running session is driven through a private Unix socket, so the same command bound to a desktop shortcut (`vosk-cli-dictation --toggle`, `--sleep`, `--status`) controls it on any desktop — native Wayland included. Global hotkeys via `pynput` remain as a best-effort convenience: under Wayland they reach only XWayland windows, not native-Wayland ones.
*   **Fully Customizable:** Configure UI colors, shortcuts, voice trigger phrases, per-language typography and recognition aliases in a simple `config.yaml` file.
*   **Full Punctuation:** Dictate a complete range of punctuation with natural voice commands.
*   **Private and Offline:** Runs entirely on your machine. Your voice data never leaves your computer.

> [!NOTE]
>
> **X11 and Wayland support.** Text is injected by copying it to the clipboard and simulating a paste. Under Wayland the tool uses `wtype` and `wl-clipboard`, falling back to `ydotool` (which needs the `ydotoold` daemon and access to `/dev/uinput`, typically via the `input` group — `sudo usermod -aG input $USER`, then log out and back in). Under X11 it uses `xdotool`. At least one backend for the current session type must be installed; `vosk-cli-dictation --diagnose` reports what is available.
>
> **Global shortcuts.** `pynput` watches the X server: under Wayland it only sees key events for windows running through XWayland (many Electron and legacy apps), never for a focused native-Wayland window. It also does not consume the events — the key combination reaches the focused window too, so pressing it while typing into a terminal inserts an escape sequence (`^[s` for `Alt+S`). For control that works everywhere, bind your desktop's own shortcut settings to the control subcommands (`vosk-cli-dictation --toggle`, `--finalize`, `--sleep-toggle`) instead. See *Controlling a running session* below. On Debian, `ydotool` is packaged in `trixie-backports`, not in stable.

## Getting Started

### Install the native package (recommended)

Install the package built for your distribution from the
[downloads page](https://vosk.davalan.fr/) — no manual setup, no virtual
environment to create:

```bash
# Debian 12+ and derivatives (Ubuntu 24.04+, Mint 22+...)
sudo apt install ./vosk-cli-dictation_0.5.4~beta_all.deb

# Fedora
sudo dnf install ./vosk-cli-dictation-0.5.4~beta-1.fc42.noarch.rpm

# openSUSE (Leap)
sudo zypper install ./vosk-cli-dictation-0.5.4~beta-1.leap156.noarch.rpm

# Arch Linux
sudo pacman -U ./vosk-cli-dictation-0.5.4_beta-1-any.pkg.tar.zst
```

The first time the package is configured it builds a private virtual environment and installs the Vosk engine into it (this step needs network access).

Then fetch a speech model and start dictating:

```bash
vosk-cli-dictation --download-model fr   # also: en, de, es
vosk-cli-dictation -l fr
```

Add `--model-size big` for the full model (`vosk-cli-dictation --download-model fr --model-size big`): from 1.4 to 1.9 GB depending on the language, and about three times that in free disk space while it unpacks.

If you start the tool with no model installed, it offers the download interactively. A missing model is reported, not fatal, as long as one language loads. Downloaded models are verified by SHA256 and stored under `~/.local/share/vosk-models/`.

The package pulls in `xdotool` (X11) or `ydotool` (Wayland fallback) for text injection. For native Wayland, also install the preferred backend with your distribution's package manager (Debian example):

```bash
sudo apt install wtype wl-clipboard
```

`ydotool` needs your user in the `input` group (`sudo usermod -aG input $USER`, then log out and back in); `xdotool` and `wtype` do not. Run `vosk-cli-dictation --diagnose` to see which backend, audio input and clipboard access are available.

> [!NOTE]
> If `apt` prints a sandbox / `_apt` permission warning, it is because the `.deb` sits under your home directory, which the `_apt` user cannot read. Copy it to `/tmp/` first and install from there. The installation succeeds either way.

### Install from source (for development)

This path runs the code directly from a git checkout. The system packages below are Debian's; on Fedora, openSUSE or Arch, install the equivalents with your package manager.

```bash
sudo apt-get update && sudo apt-get install python3-pip python3-venv portaudio19-dev gettext xdotool pulseaudio-utils
# Wayland, optional: sudo apt-get install wtype wl-clipboard ydotool

git clone https://github.com/RonanDavalan/vosk-cli-dictation.git
cd vosk-cli-dictation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Fetch a model and run the script:

```bash
python3 src/main.py --download-model fr   # also: en, de, es
python3 src/main.py -l fr                 # default language comes from config.yaml
python3 src/main.py --diagnose            # check the environment without starting a session
```

Models downloaded this way also land in `~/.local/share/vosk-models/`. As a fallback, a model folder (e.g. `vosk-model-small-fr-0.22`) dropped directly inside the project's `vosk-model/` directory is picked up too.

Only one session runs per user at a time; a second launch is refused and points you at `--status`.

### Pro Tip: Create a Quick-Launch Command (Optional)

For easier access, you can add a function to your shell's configuration file (e.g., `~/.bashrc` or `~/.zshrc`).

1.  Open your configuration file: `nano ~/.bashrc`
2.  Add the following lines at the end. **Remember to replace `/path/to/your/vosk-cli-dictation` with the actual, absolute path to the project directory.**

    ```bash
    # Defines a 'vosk' command to launch the dictation script easily.
    vosk() {
        # Check if the project directory exists
        if [ -d "/path/to/your/vosk-cli-dictation" ]; then
            cd "/path/to/your/vosk-cli-dictation" && \
            source venv/bin/activate && \
            python3 src/main.py "$@" && \
            deactivate
        else
            echo "Error: Project directory not found at /path/to/your/vosk-cli-dictation"
        fi
    }
    ```

3.  Apply the changes by running `source ~/.bashrc` or by opening a new terminal.
4.  You can now launch the application from anywhere by simply typing `vosk` or `vosk -l en`.

## Usage & Configuration

### Language Selection

The language model is chosen based on the following priority:

1.  **Command-Line Flag (Highest Priority):** Use `-l en`, `-l fr`, `-l de` or `-l es` to force a specific language for the session.
2.  **Remembered choice:** a language or model chosen while a session runs (`set-lang`, `set-model`, see below) is stored in `~/.local/state/vosk-cli-dictation/selection.yaml` and reused at the next start.
3.  **`default_model` in `config.yaml`:** a language code, or `system` — the factory value, also used when the key is missing — which follows the session language (`LC_ALL`, `LC_MESSAGES`, then `LANG`) when a model for that language is installed, and English otherwise.

### Voice Trigger Phrases

Each language has a two-word **wake phrase** and **stop phrase** (factory defaults: `start dictation` / `stop dictation` in English). Two words rather than one so an ordinary sentence never triggers them by accident. Say the wake phrase to start dictating, the stop phrase to finish and copy the result. Saying a phrase twice in a row (`stop dictation stop dictation`) types it literally instead of triggering. If the stop phrase is heard but recognition confidence is low, it is swallowed rather than typed into your document — repeat it, or use `--finalize`. The phrases are configurable per language under `language_settings.<lang>.voice_commands`.

### Trigger Modes

`interaction.mode` (default `toggle`, unchanged from earlier releases) picks how a session starts and stops: one gesture starts, a separate gesture stops. Two other modes: `maintenue` (push-to-talk — dictation lasts as long as `hotkeys.push_to_talk` is held down) and `silence` (a single press starts; the session stops and copies itself once `interaction.silence_timeout_ms` passes with no decoder output, as soon as a word has been captured). The spoken stop phrase and `--finalize`/`--cancel` keep working as a safety net in every mode. See [`docs/configuration.md`](docs/configuration.md#interaction) for the full reference.

### Controlling a Running Session

The session opens a private Unix socket at `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock` (mode `0600`). Running the **same command** with a control flag connects to it, performs the action, prints the state and exits:

```bash
vosk-cli-dictation --status          # -> OK ÉCOUTE
vosk-cli-dictation --info            # -> OK {"state":"ÉCOUTE","lang":"fr",…}  (full state, one JSON line)
vosk-cli-dictation --toggle          # start/stop dictation
vosk-cli-dictation --sleep-toggle    # enter/leave sleep mode (releases the microphone)
vosk-cli-dictation --finalize        # stop and copy the accumulated text
vosk-cli-dictation --stop            # shut the session down
```

Bind these to your desktop's keyboard-shortcut settings (KDE, GNOME, Sway, labwc…) to get global control that works everywhere, including the native-Wayland windows `pynput` cannot see. The `pynput` hotkeys in the `hotkeys` section also work as a best-effort convenience — under Wayland only over XWayland windows.

### Changing Language and Model Without Restarting

A running session changes language or model without restarting, and the text already typed stays. Two requests do it: `set-lang fr|en|de|es|system` and `set-model <model folder>` (a folder name from the `models` list that `--info` prints). The new model loads in the background while the current one keeps serving, and replaces it between two utterances; if loading fails, the current model stays and `last_error` in `--info` says why. The choice is remembered in `selection.yaml` (see Language Selection). The requests go straight to the socket; any tool that writes one line to a Unix socket will do, here `socat`:

```bash
printf 'set-lang en\n' | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/vosk-cli-dictation.sock   # -> OK ÉCOUTE
vosk-cli-dictation --info            # lang, model, models, loading, last_error…
```

Errors: `ERR bad-argument` (unknown argument), `ERR no-model` (no model installed for the request), `ERR busy` (a model is still loading). A third request without argument, `reset-selection`, forgets the remembered choice and goes back to what `config.yaml` or the system language gives.

### Refining Each Utterance With Whisper (optional)

Vosk keeps cutting and showing the text as you speak. With the refinement on, each finished utterance is also sent, as audio, to `faster-whisper`, and its text, with capitals and punctuation, replaces Vosk's just before it is typed. A command phrase (stop, wake) is never refined; utterances are typed in the order they were said; and when Whisper takes longer than `refine.timeout_ms` (2000 ms) after the end of the utterance, or returns nothing usable, the text of Vosk is typed instead. `vosk-cli-dictation --status` (a second line), `--diagnose` and `--info` count those fallbacks. Nothing changes while `refine.engine` is `none`, the factory value.

**Prerequisite:** `faster-whisper` in the Python environment of the dictation: the optional package `vosk-cli-dictation-whisper` of the same version as the main one adds it (`sudo apt install ./vosk-cli-dictation-whisper_0.5.4~beta_all.deb`; the same file names with `-whisper` on Fedora, openSUSE and Arch), or `pip install faster-whisper` from a Git checkout. Without it the icon menu greys the entry with that reason and `--diagnose` says so. The weights download at first use under `~/.local/share/vosk-cli-dictation/whisper-models` (about 75 MB for `tiny`, 1.6 GB for `large-v3-turbo`); the icon announces the first download, and the text of Vosk is typed meanwhile.

```yaml
refine:
  engine: whisper      # none (factory value) | whisper
  model: auto          # auto | tiny | base | small | medium | large-v3-turbo
  device: auto         # auto | cpu | cuda
  compute_type: auto   # auto: float16 on cuda, int8 on cpu
  timeout_ms: 2000
```

*   **On a graphics card (NVIDIA):** CTranslate2 needs the CUDA 12 library `libcublas.so.12` (Debian and Ubuntu: `sudo apt install libcublas12 libcublaslt12`). `device: auto` uses the card when it is detected and the library loads; a card without the library falls back to the processor and the dictation prints that remedy; `device: cuda` is then refused with the same remedy. `--diagnose` shows the hardware chosen and the library's state. `model: auto` gives `large-v3-turbo`, the largest size whose 95th-percentile latency per utterance stays under 500 ms (about 310 ms on an RTX 3060).
*   **On a processor:** no size stays under 500 ms per utterance (`tiny` takes 3.4 s at the 95th percentile on a Raspberry Pi 4 and 1.3 s on an 8-core x86 machine), and `tiny` and `base` spoil the French text. `model: auto` therefore gives no refinement there; choose a size by hand in `config.yaml` or from the icon menu, and raise `timeout_ms` accordingly. One core is left to Vosk.
*   **What to expect:** on the project's synthetic-speech benchmark (it compares engines, it does not promise a real rate), French word errors fall from 15.4 % to 12.0 % with the light Vosk model and `large-v3-turbo`; with the full Vosk model the words are not better (10.1 % against 12.2 %) and the refinement mainly adds capitals and punctuation.

A running session changes the refinement without restarting, from the icon menu or on the socket: `set-refine whisper:small` or `set-refine none`. The size loads in the background while Vosk's text is typed; the choice is remembered in `selection.yaml` (key `refine`), and `reset-selection` goes back to the configuration. Errors: `ERR bad-argument` (unknown size), `ERR busy` (a load is running), `ERR unsupported` (`faster-whisper` is missing). `--info` gives `refine`, `refine_options`, `refine_reason`, `device`, `refine_download` and `refine_stats` (`done`, `timeout`, `error`, `rejected`, `skipped`, `mean_ms`).

### Manual Commands

While the script is running in a terminal, you can also type these commands and press Enter:

*   `/cancel`: Stops the current recording session without outputting text.
*   `/delete-word`: Deletes the last typed word.
*   `/nl`: Inserts a new line (simulates pressing the Enter key).

### Notification-Area Icon (optional)

`vosk-cli-dictation-tray` is a separate program (Python and PySide6) that shows a microphone in the notification area and drives the running session through its control socket. The dictation never needs it and runs the same without it. Colour and shape give the state, so the icon stays readable for colour-blind users:

*   **red microphone with sound waves**: `DICTÉE`, the voice is typed;
*   **orange microphone**: `ÉCOUTE`, the microphone is open, dictation is off, the wake phrase is awaited;
*   **blue microphone under a crescent moon**: `VEILLE`, the microphone is released;
*   **green outlined microphone**: no dictation is running; a click launches it.

A left click launches the dictation when it is off and toggles it otherwise. The right-click menu starts or stops dictation, sleeps or wakes it, finishes and copies the text, cancels the session, and chooses the language (follow the system or one of the four; a language without a model is marked "to download"), the model (light or full, with its size when it is missing; the download starts from the menu and a notification tells when it ends), the refinement by Whisper (offered when `faster-whisper` is installed, greyed with its reason otherwise; the first use of a size downloads its weights and a notification tells when it starts and ends) and the correction (greyed, with its reason, until the running dictation announces it), then "Revert to the configuration", launching or quitting the dictation, "Launch the icon at login" (an XDG Autostart entry) and quitting the icon. The dictation launched from the icon runs detached from any terminal; its output goes to `~/.local/state/vosk-cli-dictation/instance.log`. On a desktop with no notification area (GNOME without an extension), the icon says once, as a desktop notification, how to enable "AppIndicator and KStatusNotifierItem Support"; the control subcommands above keep working.

With the native packages, the icon is a second package of the same version as the main one:

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

Its graphics library, PySide6, is installed with `pip` into a private virtual environment on first configuration (network access needed at that point only); the package also adds a menu entry and a system login entry (uncheck "Launch the icon at login" in the menu to remove it for your account). From a Git checkout:

```bash
cd ~/git/vosk-cli-dictation/vosk-cli-dictation/tray
python3 -m venv venv && venv/bin/pip install -e .
venv/bin/vosk-cli-dictation-tray
```

Options: `--socket PATH` (drive another dictation's socket), `--dictation-command COMMAND` (how the icon launches the dictation), `--version`. See `man vosk-cli-dictation-tray` (`docs/vosk-cli-dictation-tray.1.md`).

### Customization

All settings can be modified in the `config/config.yaml` file: shortcuts, UI colors, voice trigger phrases, per-language typography, and recognition aliases. Corpus-specific alias examples live in `config/config.example.yaml`. See [`docs/configuration.md`](docs/configuration.md) for the full reference.

## Contributing

This project is open source and contributions are highly encouraged! Please check out our **[Contribution Guide](CONTRIBUTING.md)** and feel free to open an issue on the [issues page](https://github.com/RonanDavalan/vosk-cli-dictation/issues).

This project is built through an asymmetric human-LLM collaboration — see [CONTRIBUTORS.md](CONTRIBUTORS.md) for the roles involved.

## Credits

This project is built through a human-LLM collaboration, with the roles written down as they were actually played. The full list is in [CONTRIBUTORS.md](CONTRIBUTORS.md).

*   **Ronan Davalan** — Architect and arbiter: vision, security requirements, validation and testing.
*   **Claude Code (Anthropic)** — Systems engineer and lead developer: principal author of the source code since v0.5.0-alpha, the Debian packaging and the tooling.
*   **Gemini (Google)** — Synthesizer and strategic advisor.
*   **Grok (xAI)** — External validator.
*   **GLM-5.3** — Auditor of the interaction core (blind cross-audit).
*   **DeepSeek V4 Flash (via OpenCode)** — Documentation and website reviewer, tester.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.