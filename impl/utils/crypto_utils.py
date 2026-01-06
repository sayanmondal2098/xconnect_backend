from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet


DEFAULT_LOCAL_KEY_FILE = ".xconnect_fernet_key"


def get_or_create_fernet_key() -> str:
    """Return a base64 Fernet key.

    Priority order:
      1) ENV: ENCRYPTION_KEY
      2) File: .xconnect_fernet_key (created if missing)

    This is intentionally "dev friendly": you get encryption at rest without
    the app exploding on first run. For production, set ENCRYPTION_KEY.
    """

    env_key = os.getenv("ENCRYPTION_KEY")
    if env_key:
        return env_key

    path = Path(DEFAULT_LOCAL_KEY_FILE)
    if path.exists():
        return path.read_text().strip()

    key = Fernet.generate_key().decode("utf-8")
    # best-effort: try to write with safe perms on *nix
    try:
        path.write_text(key)
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass
    except Exception:
        # if we can't persist it, still return an in-memory key
        return key

    return key
