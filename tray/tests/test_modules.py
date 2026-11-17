# Modules sans interface : client, lanceur, démarrage de session, tailles.

import stat
import time

from vosk_cli_dictation_tray import autostart, launcher
from vosk_cli_dictation_tray.client import parse_info, request
from vosk_cli_dictation_tray.i18n import Translator, system_language
from vosk_cli_dictation_tray.icons import icon_dir, icon_files, icon_name
from vosk_cli_dictation_tray.sizes import (
    ARCHIVE_BYTES,
    MEMORY_MB,
    MEMORY_OVER_MB,
    format_size,
)


def test_parse_info():
    assert parse_info('OK {"state":"ÉCOUTE"}') == {"state": "ÉCOUTE"}
    assert parse_info("OK ÉCOUTE") is None
    assert parse_info("ERR unsupported") is None
    assert parse_info(None) is None


def test_request_without_a_socket_is_none(tmp_path):
    assert request(str(tmp_path / "absent.sock"), "info", 0.2) is None


def test_request_reads_a_long_info_reply(server):
    server.extra = {"padding": "x" * 5000}
    reply = request(server.path, "info", 0.5)
    assert reply.startswith("OK {") and len(reply) > 5000


def test_every_state_has_its_icon_files():
    assert icon_dir() is not None
    for state in ("DICTÉE", "ÉCOUTE", "VEILLE", None):
        files = [f.name for f in icon_files(icon_name(state))]
        assert "mic-{}.svg".format(icon_name(state)) in files
        assert "mic-{}-22.png".format(icon_name(state)) in files


def test_translator_falls_back_to_the_source_string():
    t = Translator("xx")
    assert t.lang == "en" and t("Language") == "Language"


def test_system_language(monkeypatch):
    monkeypatch.setenv("LC_ALL", "es_ES.UTF-8")
    assert system_language() == "es"
    monkeypatch.setenv("LC_ALL", "ja_JP.UTF-8")
    assert system_language() == "en"


def test_size_format():
    assert format_size(41205931) == "41 MB"
    assert format_size(1523026348) == "1.5 GB"
    assert format_size(41205931, "fr") == "41 Mo"
    assert format_size(1523026348, "fr") == "1,5 Go"
    assert format_size(1523026348, "de") == "1,5 GB"
    assert format_size(1484681703, "es") == "1,5 GB"
    assert format_size(1523026348, "en") == "1.5 GB"
    assert len(ARCHIVE_BYTES) == 8


def test_dictation_command_priority(monkeypatch):
    monkeypatch.setenv(launcher.ENV_COMMAND, "/bin/true --x")
    assert launcher.dictation_command().argv == ["/bin/true", "--x"]
    assert launcher.dictation_command("/bin/false").argv == ["/bin/false"]
    cmd = launcher.Command(["/bin/vosk"]).with_args(
        *launcher.download_arguments("fr", "big")
    )
    assert cmd.argv == ["/bin/vosk", "--download-model", "fr", "--model-size", "big"]


def test_launch_is_detached_and_logs(tmp_path):
    script = tmp_path / "dictation.sh"
    script.write_text(
        "#!/bin/sh\necho hello-from-dictation\nps -o sid= -p $$ > %s\n"
        % (tmp_path / "sid")
    )
    script.chmod(stat.S_IRWXU)
    pid = launcher.launch_detached(launcher.Command([str(script)]))
    for _ in range(100):
        if (tmp_path / "sid").exists() and (tmp_path / "sid").read_text().strip():
            break
        time.sleep(0.02)
    assert int((tmp_path / "sid").read_text()) == pid
    time.sleep(0.1)
    assert "hello-from-dictation" in launcher.log_path().read_text()
    assert launcher.log_path().name == "instance.log"
    assert launcher.log_path().parent.name == "vosk-cli-dictation"


def test_autostart_cycle(tmp_path, monkeypatch):
    monkeypatch.setattr(autostart, "SYSTEM_ENTRY", tmp_path / "absent.desktop")
    assert not autostart.is_enabled()
    autostart.enable()
    text = autostart.user_entry().read_text()
    assert "Exec=" in text and "vosk_cli_dictation_tray" in text
    assert autostart.is_enabled()
    autostart.disable()
    assert "Hidden=true" in autostart.user_entry().read_text()
    assert not autostart.is_enabled()


def test_autostart_with_a_system_entry(tmp_path, monkeypatch):
    system = tmp_path / "sys.desktop"
    system.write_text("[Desktop Entry]\nType=Application\n")
    monkeypatch.setattr(autostart, "SYSTEM_ENTRY", system)
    assert autostart.is_enabled()
    autostart.disable()
    assert not autostart.is_enabled()
    autostart.enable()
    assert not autostart.user_entry().exists() and autostart.is_enabled()


def test_exec_argument_quotes_reserved_characters():
    assert autostart._exec_argument("/opt/a b/python") == '"/opt/a b/python"'
    assert autostart._exec_argument("50%") == "50%%"


def test_every_model_has_a_memory_figure():
    assert set(MEMORY_MB) | set(MEMORY_OVER_MB) == set(ARCHIVE_BYTES)
