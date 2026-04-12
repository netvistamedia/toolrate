import hashlib
import secrets


def effective_data_pool(stored: str | None) -> str | None:
    """Return the scoring/report data pool for a stored ApiKey.data_pool value.

    Free-tier signups overload the `data_pool` column to carry an email dedup
    tag (`"email:<hash>"`), but scoring and report ingestion filter reports by
    data_pool. Without this stripper, free users would be isolated in a pool
    of one — they'd never see the seeded/crowdsourced data and every assess
    would fall back to the Bayesian prior.

    Enterprise pools (`"ent:acme"`) and future explicit pools pass through.
    """
    if stored and stored.startswith("email:"):
        return None
    return stored


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
