import os
import sys

# La suite valide la configuration livrée ; la surcharge locale
# config_local.yaml d'un développeur ne doit pas changer ce que voient les
# tests. Les tests qui exercent la surcharge elle-même la réactivent dans
# leur propre fixture.
os.environ.setdefault("VOSK_IGNORE_LOCAL_CONFIG", "1")

# Rend la racine du projet importable quand pytest tourne depuis n'importe où.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
