from __future__ import annotations

from abc import ABC, abstractmethod


class SecretStore(ABC):
    @abstractmethod
    def put(self, *, user_id: int, name: str, value: str) -> str:
        """Stores a secret and returns a reference string."""
        raise NotImplementedError

    @abstractmethod
    def get(self, *, user_id: int, ref: str) -> str:
        """Fetch secret value by ref."""
        raise NotImplementedError
