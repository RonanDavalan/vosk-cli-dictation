# Catalogue de src/model_download.py : huit archives, empreintes et option --model-size.

import hashlib
import re
import zipfile

import pytest

import src.model_download as md


def test_catalog_has_eight_entries_four_languages_two_sizes():
    assert len(md.CATALOG) == 8
    assert set(md.CATALOG) == {
        (l, s) for l in ("en", "fr", "de", "es") for s in ("small", "big")
    }


@pytest.mark.parametrize("key", sorted(md.CATALOG))
def test_each_entry_is_complete(key):
    info = md.CATALOG[key]
    assert re.fullmatch(r"[0-9a-f]{64}", info["sha256"])
    assert info["size"] > 10_000_000
    assert info["filename"] == info["folder"] + ".zip"
    if key[1] == "big":
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", info["checked"])
        assert info["size"] > 1_000_000_000


def test_models_view_keeps_the_four_small_ones():
    assert set(md.MODELS) == {"en", "fr", "de", "es"}
    assert md.MODELS["fr"]["folder"] == "vosk-model-small-fr-0.22"


def test_known_folders_maps_folder_to_language_and_size():
    assert md.known_folders()["vosk-model-fr-0.22"] == ("fr", "big")
    assert md.known_folders()["vosk-model-small-de-0.15"] == ("de", "small")


@pytest.fixture
def fake_archive(tmp_path, monkeypatch):
    """Une archive minuscule servie à la place du téléchargement, inscrite au
    catalogue sous une clé de test."""
    src_dir = tmp_path / "src" / "vosk-model-test-1.0"
    src_dir.mkdir(parents=True)
    (src_dir / "am.bin").write_bytes(b"x" * 100)
    archive = tmp_path / "vosk-model-test-1.0.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.write(src_dir / "am.bin", "vosk-model-test-1.0/am.bin")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    entry = {
        "filename": archive.name,
        "folder": "vosk-model-test-1.0",
        "sha256": digest,
        "size": archive.stat().st_size,
    }
    monkeypatch.setitem(md.CATALOG, ("fr", "big"), entry)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setattr(
        md.urllib.request,
        "urlretrieve",
        lambda url, dest: dest and open(dest, "wb").write(archive.read_bytes()),
    )
    return entry


def test_download_big_installs_and_verifies(fake_archive, tmp_path):
    assert md.download_model("fr", "big") is True
    assert (
        tmp_path / "data" / "vosk-models" / "vosk-model-test-1.0" / "am.bin"
    ).exists()


def test_download_with_wrong_digest_is_discarded(fake_archive, tmp_path):
    fake_archive["sha256"] = "0" * 64
    assert md.download_model("fr", "big") is False
    assert not (tmp_path / "data" / "vosk-models" / "vosk-model-test-1.0").exists()


def test_download_default_size_is_small(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    asked = []
    monkeypatch.setattr(
        md.urllib.request,
        "urlretrieve",
        lambda url, dest: asked.append(url) or (_ for _ in ()).throw(OSError("stop")),
    )
    md.download_model("fr")
    assert asked and "vosk-model-small-fr" in asked[0]


def test_unknown_language_or_size_is_refused(capsys):
    assert md.download_model("xx", "big") is False
