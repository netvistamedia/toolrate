import hashlib
import secrets


def generate_api_key() -> tuple[str, str, str]:
    """Generate an API key. Returns (full_key, key_hash, key_prefix)."""
    raw = secrets.token_hex(16)
    full_key = f"nf_live_{raw}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    key_prefix = full_key[:12]
    return full_key, key_hash, key_prefix


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def make_fingerprint(key_hash: str, client_ip: str) -> str:
    return hashlib.sha256(f"{key_hash}:{client_ip}".encode()).hexdigest()


def context_hash(context: str) -> str:
    """Hash a context string for bucketed scoring. Empty/None returns '__global__'."""
    if not context:
        return "__global__"
    return hashlib.sha256(context.encode()).hexdigest()[:16]
