"""Icône de zone de notification et menu, branchés sur le client de la socket.

L'icône ne garde aucun état propre : tout vient de la dernière réponse d'`info`
(None : aucune dictée n'écoute). Les entrées du menu sont créées une fois et
seulement mises à jour, sauf les sous-menus de finition et de correction, que
la dictée annonce : refaire le menu toutes les 250 ms fermerait un menu ouvert.
"""

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from vosk_cli_dictation_tray import autostart, launcher, notifier
from vosk_cli_dictation_tray.icons import icon_name, load_icon
from vosk_cli_dictation_tray.sizes import ARCHIVE_BYTES, format_size

APP_TITLE = "vosk-cli-dictation"
LANGS = ("fr", "en", "de", "es")
SYSTEM = "system"


class DictationTray(QSystemTrayIcon):
    def __init__(self, client, translator, system_lang, dictation_command=None, notify=None):
        super().__init__()
        self._client = client
        self._t = translator
        self._system_lang = system_lang
        self._dictation_command = dictation_command
        self._notify = notify or self._default_notify
        self.info = None
        self.icon_name = None
        self._icons = {}
        self._download = None
        self._shown_error = None
        self._dynamic_options = {}

        self._build_menu()
        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)
        client.info_changed.connect(self.on_info)
        client.command_done.connect(self._on_command_done)
        self.on_info(None)

    # --- construction du menu -------------------------------------------- #

    def _action(self, menu, slot=None) -> QAction:
        action = menu.addAction("")
        if slot is not None:
            action.triggered.connect(slot)
        return action

    def _build_menu(self) -> None:
        self._menu = QMenu()
        self.a_status = self._action(self._menu)
        self.a_status.setEnabled(False)
        self._menu.addSeparator()
        self.a_dictation = self._action(self._menu, self._toggle_dictation)
        self.a_sleep = self._action(self._menu, self._toggle_sleep)
        self.a_finalize = self._action(self._menu, lambda: self._client.send("finalize"))
        self.a_cancel = self._action(self._menu, lambda: self._client.send("cancel"))
        self._menu.addSeparator()

        self.m_lang = self._menu.addMenu("")
        self._lang_group = QActionGroup(self)
        self.a_lang = {}
        for code in (SYSTEM, *LANGS):
            action = self._action(self.m_lang, lambda _=False, c=code: self._choose_lang(c))
            action.setCheckable(True)
            self._lang_group.addAction(action)
            self.a_lang[code] = action

        self.m_model = self._menu.addMenu("")
        self._model_group = QActionGroup(self)
        self.a_model = {}
        for size in ("small", "big"):
            action = self._action(self.m_model, lambda _=False, s=size: self._choose_model(s))
            action.setCheckable(True)
            self._model_group.addAction(action)
            self.a_model[size] = action

        self.m_refine = self._menu.addMenu("")
        self.m_correction = self._menu.addMenu("")
        self._menu.addSeparator()
        self.a_revert = self._action(self._menu, lambda: self._client.send("reset-selection"))
        self._menu.addSeparator()
        self.a_launch = self._action(self._menu, self._toggle_process)
        self.a_autostart = self._action(self._menu, self._set_autostart)
        self.a_autostart.setCheckable(True)
        self.a_quit = self._action(self._menu, self._quit)
        self._menu.aboutToShow.connect(self._sync_autostart)

    # --- libellés --------------------------------------------------------- #

    def _language_name(self, code: str) -> str:
        t = self._t
        return {"fr": t("French"), "en": t("English"),
                "de": t("German"), "es": t("Spanish")}.get(code, code)

    def _state_label(self, state) -> str:
        t = self._t
        return {"DICTÉE": t("Dictating"), "ÉCOUTE": t("Listening"),
                "VEILLE": t("Standby")}.get(state, state or "")

    def _engine_label(self, info: dict) -> str:
        t = self._t
        size = next((m.get("size") for m in info.get("models", [])
                     if m.get("folder") == info.get("model")), None)
        engine = t("Vosk full") if size == "big" else t("Vosk light")
        refine = info.get("refine") or "none"
        if refine.startswith("whisper:"):
            engine += " + Whisper " + refine.split(":", 1)[1]
        return engine

    def status_text(self) -> str:
        info = self.info
        if info is None:
            return self._t("Dictation not running")
        return " — ".join([self._state_label(info.get("state")),
                           self._language_name(info.get("lang") or self._system_lang),
                           self._engine_label(info)])

    def _missing_suffix(self, lang: str, size: str) -> str:
        n = ARCHIVE_BYTES.get((lang, size))
        return self._t("to download, {size}").format(size=format_size(n)) if n \
            else self._t("to download")

    def _refresh_texts(self) -> None:
        t, info = self._t, self.info
        installed = set(info.get("langs", [])) if info else set()
        lang = (info or {}).get("lang") or self._system_lang

        self.a_status.setText(self.status_text())
        self.m_lang.setTitle(t("Language"))
        self.a_lang[SYSTEM].setText(
            t("Follow the system ({language})").format(
                language=self._language_name(self._system_lang)))
        for code in LANGS:
            name = self._language_name(code)
            self.a_lang[code].setText(
                name if (code in installed or info is None)
                else "{} ({})".format(name, self._missing_suffix(code, "small")))

        self.m_model.setTitle(t("Model"))
        have = {m.get("size") for m in (info or {}).get("models", [])}
        for size, label in (("small", t("Light model")), ("big", t("Full model"))):
            self.a_model[size].setText(
                label if (size in have or info is None)
                else "{} ({})".format(label, self._missing_suffix(lang, size)))

        self.a_revert.setText(t("Revert to the configuration"))
        self.a_autostart.setText(t("Launch the icon at login"))
        self.a_quit.setText(t("Quit the icon"))

    # --- état ------------------------------------------------------------- #

    def on_info(self, info) -> None:
        self.info = info
        if info is not None and info.get("lang") and info["lang"] != self._t.lang:
            self._t.set_language(info["lang"])
        elif info is None and self._t.lang != self._system_lang:
            self._t.set_language(self._system_lang)
        self._refresh_icon()
        self._refresh_texts()
        self._refresh_actions()
        self._refresh_errors()

    def _refresh_icon(self) -> None:
        name = icon_name(self.info.get("state") if self.info else None)
        if name != self.icon_name:
            self.icon_name = name
            if name not in self._icons:
                self._icons[name] = load_icon(name)
            self.setIcon(self._icons[name])
        tip = self.status_text()
        if self.info and self.info.get("loading"):
            tip += " — " + self._t("Loading model…")
        self.setToolTip(tip)

    def _refresh_actions(self) -> None:
        t, info = self._t, self.info
        running = info is not None
        loading = running and bool(info.get("loading"))
        state = info.get("state") if running else None

        self.a_dictation.setText(t("Turn dictation off") if state == "DICTÉE"
                                 else t("Turn dictation on"))
        self.a_sleep.setText(t("Wake up") if state == "VEILLE" else t("Put to sleep"))
        self.a_finalize.setText(t("Finish and copy the text"))
        self.a_cancel.setText(t("Cancel the session"))
        self.a_dictation.setEnabled(running)
        self.a_sleep.setEnabled(running)
        self.a_finalize.setEnabled(state in ("DICTÉE", "ÉCOUTE"))
        self.a_cancel.setEnabled(state in ("DICTÉE", "ÉCOUTE"))

        self.m_lang.setEnabled(running and not loading)
        self.m_model.setEnabled(running and not loading)
        self.a_revert.setEnabled(running and not loading)
        if running:
            source = info.get("lang_source")
            checked = SYSTEM if source == "system" else info.get("lang")
            for code, action in self.a_lang.items():
                action.setChecked(code == checked)
            size = next((m.get("size") for m in info.get("models", [])
                         if m.get("folder") == info.get("model")), None)
            for key, action in self.a_model.items():
                action.setChecked(key == size)

        self._refresh_dynamic(self.m_refine, "refine", t("Refinement"),
                              (info or {}).get("refine_options"), (info or {}).get("refine"),
                              (info or {}).get("refine_reason"), running and not loading)
        self._refresh_dynamic(self.m_correction, "correction", t("Correction"),
                              (info or {}).get("correction_options"), (info or {}).get("correction"),
                              (info or {}).get("correction_reason"), running and not loading)

        self.a_launch.setText(t("Quit dictation") if running else t("Launch dictation"))

    def _option_label(self, value: str, device) -> str:
        t = self._t
        if value == "none":
            return t("None")
        kind, _sep, detail = value.partition(":")
        if kind == "whisper":
            label = "Whisper " + detail
            if device:
                label += " ({})".format({"cuda": "GPU", "gpu": "GPU", "cpu": "CPU"}
                                         .get(str(device).lower(), str(device)))
            return label
        if kind == "ollama":
            return "Ollama " + detail
        return value

    def _refresh_dynamic(self, menu, key, title, options, current, reason, usable) -> None:
        """Sous-menu annoncé par `info` (`<clé>_options`) : grisé, avec sa raison,
        tant que la dictée n'annonce aucune option."""
        announced = [o for o in (options or []) if isinstance(o, str)]
        offered = [o for o in announced if o != "none"]
        if not offered:
            why = reason if isinstance(reason, str) and reason else self._t("not available in this dictation")
            menu.setTitle("{} — {}".format(title, why))
            menu.setEnabled(False)
            menu.setToolTipsVisible(True)
            self._dynamic_options[key] = None
            return
        menu.setTitle(title)
        menu.setEnabled(usable)
        device = (self.info or {}).get("device")
        signature = (tuple(announced), device, self._t.lang)
        if self._dynamic_options.get(key) != signature:
            menu.clear()
            group = QActionGroup(menu)
            self._dynamic_options[key] = signature
            for value in announced:
                action = menu.addAction(self._option_label(value, device))
                action.setCheckable(True)
                action.setData(value)
                group.addAction(action)
                action.triggered.connect(
                    lambda _=False, v=value: self._client.send("set-{} {}".format(key, v)))
        for action in menu.actions():
            action.setChecked(action.data() == (current or "none"))

    def _refresh_errors(self) -> None:
        error = (self.info or {}).get("last_error")
        if error and error != self._shown_error:
            self._notify(self._t("Dictation error: {error}").format(error=error))
        self._shown_error = error

    # --- gestes ------------------------------------------------------------ #

    def _on_activated(self, reason) -> None:
        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            return
        if self.info is None:
            self.launch_dictation()
        else:
            self._client.send("toggle")

    def _toggle_dictation(self) -> None:
        on = (self.info or {}).get("state") == "DICTÉE"
        self._client.send("dictation-off" if on else "dictation-on")

    def _toggle_sleep(self) -> None:
        asleep = (self.info or {}).get("state") == "VEILLE"
        self._client.send("wake" if asleep else "sleep")

    def _toggle_process(self) -> None:
        if self.info is None:
            self.launch_dictation()
        else:
            self._client.send("quit")

    def _choose_lang(self, code: str) -> None:
        installed = set((self.info or {}).get("langs", []))
        if code == SYSTEM or code in installed:
            self._client.send("set-lang " + code)
        else:
            self.download_model(code, "small")

    def _choose_model(self, size: str) -> None:
        info = self.info or {}
        for model in info.get("models", []):
            if model.get("size") == size:
                self._client.send("set-model " + model["folder"])
                return
        self.download_model(info.get("lang") or self._system_lang, size)

    def _on_command_done(self, command: str, reply) -> None:
        t = self._t
        if reply is None:
            self._notify(t("The dictation does not answer."))
        elif reply.startswith("ERR"):
            reason = reply[3:].strip()
            text = {"busy": t("A model is loading, try again in a moment."),
                    "no-model": t("No model is installed for this choice.")}.get(
                reason, t("The dictation refused the request ({reason}).").format(reason=reason))
            self._notify(text)

    # --- processus ----------------------------------------------------------- #

    def launch_dictation(self) -> None:
        t = self._t
        command = launcher.dictation_command(self._dictation_command)
        if command is None:
            self._notify(t("The dictation program was not found."))
            return
        try:
            launcher.launch_detached(command)
        except OSError as error:
            self._notify(t("Could not launch the dictation: {error}").format(error=error))

    def download_model(self, lang: str, size: str) -> None:
        t = self._t
        if self._download is not None:
            self._notify(t("A model download is already running."))
            return
        command = launcher.dictation_command(self._dictation_command)
        if command is None:
            self._notify(t("The dictation program was not found."))
            return
        full = command.with_args(*launcher.download_arguments(lang, size))
        process = QProcess(self)
        process.setProgram(full.argv[0])
        process.setArguments(full.argv[1:])
        if full.cwd:
            process.setWorkingDirectory(full.cwd)
        log = launcher.log_path()
        log.parent.mkdir(parents=True, exist_ok=True)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.setStandardOutputFile(str(log), QProcess.OpenModeFlag.Append)
        process.finished.connect(lambda code, status: self._download_finished(lang, size, code, status))
        process.errorOccurred.connect(
            lambda _e: self._download_finished(lang, size, -1, QProcess.ExitStatus.CrashExit)
            if process.state() == QProcess.ProcessState.NotRunning else None)
        self._download = process
        process.start()
        self._notify(t("Downloading the {size} model for {language}…").format(
            size=t("full") if size == "big" else t("light"),
            language=self._language_name(lang)))

    def _download_finished(self, lang, size, code, status) -> None:
        t = self._t
        if self._download is None:
            return
        self._download.deleteLater()
        self._download = None
        if code == 0 and status == QProcess.ExitStatus.NormalExit:
            self._notify(t("Model download finished: {size} model, {language}.").format(
                size=t("full") if size == "big" else t("light"),
                language=self._language_name(lang)))
        else:
            self._notify(t("Model download failed (see {log}).").format(log=launcher.log_path()))

    def _sync_autostart(self) -> None:
        self.a_autostart.setChecked(autostart.is_enabled())

    def _set_autostart(self, checked: bool) -> None:
        if checked:
            autostart.enable()
        else:
            autostart.disable()

    def _quit(self) -> None:
        self._client.stop()
        QApplication.quit()

    def _default_notify(self, message: str) -> None:
        if self.isVisible() and QSystemTrayIcon.supportsMessages():
            self.showMessage(APP_TITLE, message, QSystemTrayIcon.MessageIcon.Warning)
        else:
            notifier.notify(APP_TITLE, message)
