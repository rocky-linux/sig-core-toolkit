
"""Backend for Kiwi"""
from .interface import BackendInterface


class KiwiBackend(BackendInterface):
    """Build an image using Kiwi"""

    def prepare(self):
        pass

    def build(self):
        pass

    def clean(self):
        pass
