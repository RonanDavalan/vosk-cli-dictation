# src/refine/__init__.py
#
# Finition d'un énoncé par un second réseau de neurones. Vosk découpe et affiche
# au fil de la voix ; quand un énoncé est fini, son audio part à un moteur de
# finition dont le texte remplace celui de Vosk avant la frappe. Ce paquet ne
# dépend ni de la configuration ni de l'interface : le moteur reçoit de l'audio
# et rend du texte.

SAMPLE_RATE = 16000
NONE = "none"


class RefineUnavailable(Exception):
    """Le moteur ne peut pas servir ; `code` dit pourquoi (traduit plus haut),
    `detail` porte la valeur utile à la raison (taille, bibliothèque, remède)."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


class RefineEngine:
    """Interface d'un moteur de finition. `refine` reçoit l'audio d'un énoncé
    (PCM 16 bits mono, SAMPLE_RATE) et la langue de la session, et rend le texte
    final ; il est appelé par un seul fil à la fois."""

    spec = NONE

    def load(self) -> None:
        """Charge le moteur ; lève RefineUnavailable s'il ne le peut pas."""

    def refine(self, pcm: bytes, language: str) -> str:
        raise NotImplementedError

    def device(self):
        """`cuda`, `cpu` ou None quand le moteur n'a pas de matériel propre."""
        return None

    def close(self) -> None:
        pass
