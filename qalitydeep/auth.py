"""User auth and API key management."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from pathlib import Path
from typing import Optional

from .config import get_settings


def _auth_path() -> Path:
    return get_settings().data_dir / "auth.json"


def _load_auth() -> dict:
    p = _auth_path()
    if not p.exists():
        return {"users": [], "api_keys": []}
    return json.loads(p.read_text())


def _save_auth(data: dict) -> None:
    _auth_path().parent.mkdir(parents=True, exist_ok=True)
    _auth_path().write_text(json.dumps(data, indent=2))


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def create_user_and_key(email: str) -> tuple[str, str]:
    """Create user + API key. Returns (user_id, api_key). Key shown once."""
    data = _load_auth()
    users = data.get("users", [])
    keys = data.get("api_keys", [])

    # Check existing email
    for u in users:
        if u.get("email", "").lower() == email.lower():
            # Return existing user, create new key
            user_id = u["id"]
            break
    else:
        user_id = f"u_{uuid.uuid4().hex[:8]}"
        users.append({"id": user_id, "email": email})
        data["users"] = users

    raw_key = f"qd_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)
    prefix = raw_key[:12] + "..."
    keys.append({"user_id": user_id, "key_hash": key_hash, "prefix": prefix})
    data["api_keys"] = keys
    _save_auth(data)
    return user_id, raw_key


def validate_api_key(key: Optional[str]) -> Optional[str]:
    """Validate key. Returns user_id if valid, else None."""
    if not key or not key.strip():
        return None
    key_hash = _hash_key(key.strip())
    data = _load_auth()
    for k in data.get("api_keys", []):
        if k.get("key_hash") == key_hash:
            return k.get("user_id")
    return None
