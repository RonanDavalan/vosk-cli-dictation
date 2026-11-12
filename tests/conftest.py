import os
import sys

# La suite valide la configuration livrée ; la surcharge locale
# config_local.yaml d'un développeur ne doit pas changer ce que voient les
# tests. Les tests qui exercent la surcharge elle-même la réactivent dans
# leur propre fixture.
os.environ.setdefault("VOSK_IGNORE_LOCAL_CONFIG", "1")

# Rend la racine du projet importable quand pytest tourne depuis n'importe où.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_real_clipboard():
    """Aucun test ne touche au presse-papiers du poste : la publication par wl-copy est neutralisée."""
    module = sys.modules.get("src.ui")
    original = getattr(module, "ensure_clipboard_text", None)
    if module is not None:
        module.ensure_clipboard_text = lambda text: True
    yield
    if module is not None and original is not None:
        module.ensure_clipboard_text = original
