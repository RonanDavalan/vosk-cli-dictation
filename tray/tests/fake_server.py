"""Faux serveur de contrôle : parle le protocole de la socket de la dictée
(jeton[ argument]\\n -> OK ... \\n) sans micro ni modèle. Sert aux tests de
l'icône et à sa recette sur un poste où une vraie dictée tourne.

Usage : python fake_server.py --socket CHEMIN [--journal FICHIER] [--state ÉCOUTE]
"""

import argparse
import json
import os
import socket
import threading
import time

LISTENING, DICTATING, SLEEPING = "ÉCOUTE", "DICTÉE", "VEILLE"


class FakeServer:
    def __init__(self, path, state=LISTENING, journal=None):
        self.path = str(path)
        self.journal = journal
        self.lock = threading.Lock()
        self.received = []
        self.state = state
        self.lang = "fr"
        self.lang_source = "config"
        self.langs = ["fr", "en", "de", "es"]
        self.models = [{"folder": "vosk-model-small-fr-0.22", "size": "small"},
                       {"folder": "vosk-model-fr-0.22", "size": "big"}]
        self.model = "vosk-model-small-fr-0.22"
        self.extra = {}
        self.stop_event = threading.Event()
        self._srv = None
        self._thread = None

    def info(self):
        data = {"state": self.state, "lang": self.lang, "lang_source": self.lang_source,
                "langs": self.langs, "model": self.model, "models": self.models,
                "refine": "none", "device": None, "correction": "none",
                "loading": False, "last_error": None}
        data.update(self.extra)
        return data

    def handle(self, raw):
        token, _sep, arg = raw.strip().partition(" ")
        with self.lock:
            self.received.append(raw.strip())
            if self.journal:
                with open(self.journal, "a", encoding="utf-8") as f:
                    f.write("{} {}\n".format(time.strftime("%H:%M:%S"), raw.strip()))
            if token == "info":
                return "OK " + json.dumps(self.info(), ensure_ascii=False, separators=(",", ":"))
            if token == "toggle":
                self.state = LISTENING if self.state == DICTATING else DICTATING
            elif token == "dictation-on":
                self.state = DICTATING
            elif token == "dictation-off":
                self.state = LISTENING
            elif token == "sleep":
                self.state = SLEEPING
            elif token == "wake":
                self.state = LISTENING
            elif token == "set-lang":
                if arg == "system":
                    self.lang_source = "system"
                elif arg in self.langs:
                    self.lang, self.lang_source = arg, "selection"
                else:
                    return "ERR no-model"
            elif token == "reset-selection":
                self.lang_source = "config"
            elif token == "quit":
                self.stop_event.set()
                return "OK stopping"
            elif token not in ("status", "finalize", "cancel", "sleep-toggle",
                               "set-model", "set-refine", "set-correction"):
                return "ERR unknown-command"
            return "OK " + self.state

    def start(self):
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass
        self._srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._srv.bind(self.path)
        os.chmod(self.path, 0o600)
        self._srv.listen(8)
        self._srv.settimeout(0.1)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self):
        while not self.stop_event.is_set():
            try:
                conn, _addr = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                conn.settimeout(2.0)
                data = b""
                try:
                    while b"\n" not in data:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                    conn.sendall((self.handle(data.decode("utf-8", "replace")) + "\n").encode())
                except OSError:
                    pass

    def stop(self):
        self.stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        try:
            self._srv.close()
        except OSError:
            pass
        try:
            os.unlink(self.path)
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    parser.add_argument("--journal")
    parser.add_argument("--state", default=LISTENING, choices=(LISTENING, DICTATING, SLEEPING))
    args = parser.parse_args()
    server = FakeServer(args.socket, args.state, args.journal).start()
    try:
        while not server.stop_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    server.stop()


if __name__ == "__main__":
    main()
