import os
import sys

# The suite validates the shipped configuration; a developer's local
# config_local.yaml overlay must not change what the tests see. Tests that
# exercise the overlay itself clear this in their own fixture.
os.environ.setdefault("VOSK_IGNORE_LOCAL_CONFIG", "1")

# Make the project root importable when pytest is run from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
