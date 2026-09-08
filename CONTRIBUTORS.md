# Acknowledgments and Contributors

This project could not have come to life without the hard work of many people and the existence of fantastic open-source tools. I want to express my deep gratitude to everyone who contributed, directly or indirectly, to its creation.

## Core Projects and Libraries

This software relies entirely on the following open-source projects. A big thank you to their developers and communities for providing such powerful and accessible tools.

*   **[Vosk-API](https://alphacephei.com/vosk/)**: For providing the robust and high-performance offline speech recognition engine that is the heart of this application.
*   **[Python](https://www.python.org/)**: For a versatile programming language and an incredible community.
*   **[xdotool](https://github.com/jordansissel/xdotool)**: For the essential tool that allows simulating keyboard input and controlling windows under Linux (X11).
*   **[wtype](https://github.com/atx/wtype)**: For simulating the paste keystroke on Wayland by keysym, independent of the keyboard layout.
*   **[wl-clipboard](https://github.com/bugaevc/wl-clipboard)**: For reading and writing the Wayland clipboard, and detecting non-text content so it is never destroyed.
*   **[ydotool](https://github.com/ReimuNotMoe/ydotool)**: For keyboard input simulation on Wayland as a fallback, via the `/dev/uinput` interface.
*   **[pactl (PulseAudio)](https://www.freedesktop.org/wiki/Software/PulseAudio/)**: For the commands to manage the system's audio sources.
*   **[PyYAML](https://pyyaml.org/)**: For handling YAML configuration files.
*   **[Pynput](https://pynput.readthedocs.io/en/latest/)**: For managing keyboard and mouse events.
*   **[PyAudio](https://pypi.org/project/PyAudio/)**: For audio capture.

## Design and Development Support

This project was developed using an asymmetric human-LLM collaboration model. Roles are documented formally here to reflect the actual work performed, rather than listing "AI assistance" as a single vague category.

*   **Architect & Arbiter: Ronan Davalan.** Product vision, security requirements, project direction, validation and testing. All architectural decisions are validated by him.
*   **Systems Engineer & Lead Developer: Claude Code (Anthropic).** Principal author of the source code since v0.5.0-alpha — ReAct-style control loop, thread architecture, complex state management, configuration and per-language systems, session persistence and the control socket, the Debian packaging, Python and Bash tooling. Up to v0.0.4-alpha, an occasional outside contributor only.
*   **Synthesizer & Strategic Advisor: Gemini (Google).** Independent architectural analysis, logical conflict resolution, workflow optimisation, cross-validation of technical decisions.
*   **External Validator: Grok (xAI).** Challenges hypotheses and model coherence from an outside view.
*   **Auditor — interaction core: GLM-5.3.** Blind cross-audit of the hardening work; flagged the restricted-grammar recognizer for standby and the GIL check.
*   **Auditor — documentation: DeepSeek (via OpenCode).** Occasional review of documentation and web copy — never commits, never decides architecture.

## Code and Documentation Contributors

This section is dedicated to all the people who have contributed directly to the project by submitting relevant pull requests or issues.

*(This section is currently empty, but I hope to see your name here soon!)*

---
*If you wish to contribute, please see our [contribution guide](./CONTRIBUTING.md).*
