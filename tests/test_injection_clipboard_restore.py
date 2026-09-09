# Correctif de collage (v0.5.1-alpha) — src/system_control.type_text :
#   - chemin par défaut : restauration APRÈS le collage, jamais avant, dans une
#     fenêtre bornée par clipboard.restore_delay_ms ;
#   - abandon anticipé : si le presse-papiers a déjà changé pendant l'attente,
#     aucune restauration n'est émise ;
#   - clipboard.defer_restore : aucune restauration en ligne ;
#     flush_deferred_clipboard() restaure le presse-papiers d'origine ;
#     enregistrement atexit posé une seule fois ;
#   - clipboard.restore=false : ni sauvegarde ni restauration ;
#   - collage non émis (_send_paste -> False) : restauration immédiate, sans
#     fenêtre d'attente.
# Spec : _CADRE/SPECIFICATIONS/CORRECTIF_INJECTION_COLLAGE.md

import time
import types

import pytest

import src.system_control as sc


@pytest.fixture
def clip(monkeypatch):
    """Presse-papiers bouchonné + traçage ordonné des set / collages."""
    state = {"value": "ORIGINAL"}
    trace = []          # ("set", v) | ("paste",), dans l'ordre
    paste_result = {"ok": True}
    get_script = {"values": None}  # si défini : file de valeurs rendues par get,
                                   # la dernière étant répétée une fois épuisée

    def fake_get():
        vals = get_script["values"]
        if vals is None:
            return state["value"]
        return vals.pop(0) if len(vals) > 1 else vals[0]

    def fake_set(v):
        state["value"] = v
        trace.append(("set", v))
        return True

    def fake_send_paste(_combo):
        trace.append(("paste",))
        return paste_result["ok"]

    monkeypatch.setattr(sc, "_detect_caps", lambda: {"key_backend": "wtype",
                                                     "session": "wayland"})
    monkeypatch.setattr(sc, "_clipboard_is_text", lambda: True)
    monkeypatch.setattr(sc, "_clipboard_get", fake_get)
    monkeypatch.setattr(sc, "_clipboard_set", fake_set)
    monkeypatch.setattr(sc, "_clipboard_confirm", lambda text, ms: True)
    monkeypatch.setattr(sc, "_send_paste", fake_send_paste)
    monkeypatch.setattr(sc, "_paste_combo_for_target", lambda: "ctrl+v")
    # état de module propre pour chaque test
    monkeypatch.setattr(sc, "_deferred_clip", {"pending": False, "value": None})
    monkeypatch.setattr(sc, "_deferred_atexit_registered", False)
    registered = []
    monkeypatch.setattr(sc, "atexit",
                        types.SimpleNamespace(register=registered.append))

    def set_cfg(**kw):
        base = {"restore": True, "defer_restore": False,
                "restore_delay_ms": 400, "confirm_timeout_ms": 500}
        base.update(kw)
        monkeypatch.setattr(sc, "_cfg",
                            lambda section, key, default: base.get(key, default)
                            if section == "clipboard" else default)

    return {"state": state, "trace": trace, "paste_result": paste_result,
            "get_script": get_script, "set_cfg": set_cfg, "registered": registered}


def test_default_restores_after_paste(clip):
    clip["set_cfg"](restore_delay_ms=60)

    assert sc.type_text("mot") is True

    assert clip["trace"] == [("set", "mot"), ("paste",), ("set", "ORIGINAL")]
    assert clip["state"]["value"] == "ORIGINAL"


def test_restore_wait_is_bounded(clip):
    clip["set_cfg"](restore_delay_ms=120)

    start = time.monotonic()
    sc.type_text("mot")
    elapsed = time.monotonic() - start

    # La fenêtre d'attente ne dépasse pas restore_delay_ms (large marge).
    assert elapsed < 1.0
    assert ("set", "ORIGINAL") in clip["trace"]


def test_early_abort_when_clipboard_hijacked(clip):
    clip["set_cfg"](restore_delay_ms=300)
    # 1er get (sauvegarde) -> "ORIGINAL" ; gets suivants (fenêtre d'attente) ->
    # "HIJACK" : un autre propriétaire a pris la main.
    clip["get_script"]["values"] = ["ORIGINAL", "HIJACK"]

    assert sc.type_text("mot") is True

    # Le collage a eu lieu, mais aucune restauration : un autre propriétaire
    # a pris la main.
    assert ("paste",) in clip["trace"]
    assert ("set", "ORIGINAL") not in clip["trace"]


def test_defer_restore_skips_inline_restore(clip):
    registered = clip["registered"]
    clip["set_cfg"](defer_restore=True)

    assert sc.type_text("mot1") is True
    assert sc.type_text("mot2") is True

    # Aucune restauration en ligne pendant la session.
    assert clip["trace"] == [("set", "mot1"), ("paste",),
                             ("set", "mot2"), ("paste",)]
    # atexit posé une seule fois malgré deux segments.
    assert registered == [sc.flush_deferred_clipboard]

    # Fin de session : le presse-papiers d'origine (celui d'avant "mot1") revient.
    sc.flush_deferred_clipboard()
    assert clip["trace"][-1] == ("set", "ORIGINAL")

    # Idempotence : un second flush ne réécrit rien.
    before = list(clip["trace"])
    sc.flush_deferred_clipboard()
    assert clip["trace"] == before


def test_restore_disabled_leaves_clipboard_alone(clip):
    clip["set_cfg"](restore=False)

    assert sc.type_text("mot") is True

    assert clip["trace"] == [("set", "mot"), ("paste",)]
    assert clip["state"]["value"] == "mot"


def test_failed_paste_restores_immediately(clip):
    clip["set_cfg"](restore_delay_ms=5000)
    clip["paste_result"]["ok"] = False

    start = time.monotonic()
    assert sc.type_text("mot") is False
    elapsed = time.monotonic() - start

    # Pas d'attente : rien n'a été collé.
    assert elapsed < 1.0
    assert clip["trace"] == [("set", "mot"), ("paste",), ("set", "ORIGINAL")]
