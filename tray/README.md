# vosk-cli-dictation-tray

Notification-area microphone icon for vosk-cli-dictation. It is a separate program: it talks to a running
dictation only through its control socket, and the dictation never needs it.

Development:

    python3 -m venv venv && venv/bin/pip install -e '.[dev]'
    QT_QPA_PLATFORM=offscreen venv/bin/python -m pytest -q
    venv/bin/vosk-cli-dictation-tray --version
