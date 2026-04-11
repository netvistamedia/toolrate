"""Tests for API key generation and security utilities."""

from app.core.security import generate_api_key, hash_api_key, make_fingerprint


class TestApiKeyGeneration:
    def test_key_format(self):
        key, key_hash, prefix = generate_api_key()
        assert key.startswith("nf_live_")
        assert len(key) == 40  # nf_live_ (8) + 32 hex chars

    def test_prefix_matches(self):
        key, _, prefix = generate_api_key()
        assert key.startswith(prefix)
        assert len(prefix) == 12

    def test_hash_is_deterministic(self):
        key, key_hash, _ = generate_api_key()
        assert hash_api_key(key) == key_hash

    def test_keys_are_unique(self):
        keys = [generate_api_key()[0] for _ in range(10)]
        assert len(set(keys)) == 10

    def test_hashes_are_unique(self):
        hashes = [generate_api_key()[1] for _ in range(10)]
        assert len(set(hashes)) == 10


class TestFingerprint:
    def test_deterministic(self):
        fp1 = make_fingerprint("hash123", "192.168.1.1")
        fp2 = make_fingerprint("hash123", "192.168.1.1")
        assert fp1 == fp2

    def test_different_inputs(self):
        fp1 = make_fingerprint("hash123", "192.168.1.1")
        fp2 = make_fingerprint("hash456", "192.168.1.1")
        fp3 = make_fingerprint("hash123", "10.0.0.1")
        assert fp1 != fp2
        assert fp1 != fp3
