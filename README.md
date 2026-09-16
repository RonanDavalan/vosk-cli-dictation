# Vosk-CLI-Dictation

<p align="center">
  <a href="https://github.com/RonanDavalan/vosk-cli-dictation/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/Version-v0.5.2--beta-yellow.svg" alt="Version: v0.5.2-beta"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+"></a>
  <a href="#"><img src="https://img.shields.io/badge/OS-Debian_13-D70A53.svg" alt="Tested on Debian 13"></a>
  <a href="#"><img src="https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg" alt="Contributions Welcome"></a>
</p>

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
sudo apt install ./vosk-cli-dictation_0.5.2~beta_all.deb

# Fedora
sudo dnf install ./vosk-cli-dictation-0.5.2~beta-1.fc42.noarch.rpm

# openSUSE (Leap)
sudo zypper install ./vosk-cli-dictation-0.5.2~beta-1.leap156.noarch.rpm

# Arch Linux
sudo pacman -U ./vosk-cli-dictation-0.5.2_beta-1-any.pkg.tar.zst
```

The first time the package is configured it builds a private virtual environment and installs the Vosk engine into it (this step needs network access).

Then fetch a speech model and start dictating:

```bash
vosk-cli-dictation --download-model fr   # also: en, de, es
vosk-cli-dictation -l fr
```

If you start the tool with no model installed, it offers the download interactively. A missing model is reported, not fatal, as long as one language loads. Downloaded models are verified by SHA256 and stored under `~/.local/share/vosk-models/`.

The package pulls in `xdotool` (X11) or `ydotool` (Wayland fallback) for text injection. For native Wayland, also install the preferred backend:

```bash
sudo apt install wtype wl-clipboard
```

`ydotool` needs your user in the `input` group (`sudo usermod -aG input $USER`, then log out and back in); `xdotool` and `wtype` do not. Run `vosk-cli-dictation --diagnose` to see which backend, audio input and clipboard access are available.

> [!NOTE]
> If `apt` prints a sandbox / `_apt` permission warning, it is because the `.deb` sits under your home directory, which the `_apt` user cannot read. Copy it to `/tmp/` first and install from there. The installation succeeds either way.

### Install from source (for development)

This path runs the code directly from a git checkout.

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
2.  **Default in `config.yaml` (Fallback):** If no flag is used, the `default_model` from `config/config.yaml` is loaded.

### Voice Trigger Phrases

Each language has a two-word **wake phrase** and **stop phrase** (factory defaults: `start dictation` / `stop dictation` in English). Two words rather than one so an ordinary sentence never triggers them by accident. Say the wake phrase to start dictating, the stop phrase to finish and copy the result. Saying a phrase twice in a row (`stop dictation stop dictation`) types it literally instead of triggering. If the stop phrase is heard but recognition confidence is low, it is swallowed rather than typed into your document — repeat it, or use `--finalize`. The phrases are configurable per language under `language_settings.<lang>.voice_commands`.

### Trigger Modes

`interaction.mode` (default `toggle`, unchanged from earlier releases) picks how a session starts and stops: one gesture starts, a separate gesture stops. Two other modes: `maintenue` (push-to-talk — dictation lasts as long as `hotkeys.push_to_talk` is held down) and `silence` (a single press starts; the session stops and copies itself once `interaction.silence_timeout_ms` passes with no decoder output, as soon as a word has been captured). The spoken stop phrase and `--finalize`/`--cancel` keep working as a safety net in every mode. See [`docs/configuration.md`](docs/configuration.md#interaction) for the full reference.

### Controlling a Running Session

The session opens a private Unix socket at `$XDG_RUNTIME_DIR/vosk-cli-dictation.sock` (mode `0600`). Running the **same command** with a control flag connects to it, performs the action, prints the state and exits:

```bash
vosk-cli-dictation --status          # -> OK ÉCOUTE
vosk-cli-dictation --toggle          # start/stop dictation
vosk-cli-dictation --sleep-toggle    # enter/leave sleep mode (releases the microphone)
vosk-cli-dictation --finalize        # stop and copy the accumulated text
vosk-cli-dictation --stop            # shut the session down
```

Bind these to your desktop's keyboard-shortcut settings (KDE, GNOME, Sway, labwc…) to get global control that works everywhere, including the native-Wayland windows `pynput` cannot see. The `pynput` hotkeys in the `hotkeys` section also work as a best-effort convenience — under Wayland only over XWayland windows.

### Manual Commands

While the script is running in a terminal, you can also type these commands and press Enter:

*   `/cancel`: Stops the current recording session without outputting text.
*   `/delete-word`: Deletes the last typed word.
*   `/nl`: Inserts a new line (simulates pressing the Enter key).

### Customization

All settings can be modified in the `config/config.yaml` file: shortcuts, UI colors, voice trigger phrases, per-language typography, and recognition aliases. Corpus-specific alias examples live in `config/config.example.yaml`. See [`docs/configuration.md`](docs/configuration.md) for the full reference.

## Contributing

This project is open source and contributions are highly encouraged! Please check out our **[Contribution Guide](CONTRIBUTING.md)** and feel free to open an issue on the [issues page](https://github.com/RonanDavalan/vosk-cli-dictation/issues).

This project is built through an asymmetric human-LLM collaboration — see [CONTRIBUTORS.md](CONTRIBUTORS.md) for the roles involved.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.