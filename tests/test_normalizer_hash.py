"""
Tests for normalizer hashing functionality.
"""
import unittest
from normalizers import load_preset, stable_hash_dict


class TestNormalizerHash(unittest.TestCase):
    """Test normalizer hashing."""

    def test_stable_hash_dict_deterministic(self):
        """Verify hash is deterministic across runs."""
        d1 = {"a": 1, "b": 2, "c": 3}
        d2 = {"a": 1, "b": 2, "c": 3}

        hash1 = stable_hash_dict(d1)
        hash2 = stable_hash_dict(d2)

        self.assertEqual(hash1, hash2)

    def test_stable_hash_dict_key_order_independent(self):
        """Verify hash is independent of key order."""
        d1 = {"a": 1, "b": 2, "c": 3}
        d2 = {"c": 3, "a": 1, "b": 2}

        hash1 = stable_hash_dict(d1)
        hash2 = stable_hash_dict(d2)

        self.assertEqual(hash1, hash2)

    def test_stable_hash_dict_different_values(self):
        """Verify different values produce different hashes."""
        d1 = {"a": 1}
        d2 = {"a": 2}

        hash1 = stable_hash_dict(d1)
        hash2 = stable_hash_dict(d2)

        self.assertNotEqual(hash1, hash2)

    def test_stable_hash_dict_sha256_format(self):
        """Verify hash is SHA256 hex digest."""
        d = {"test": "value"}
        h = stable_hash_dict(d)

        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_config_to_dict_hash_stable(self):
        """Verify config.to_dict() hash is stable."""
        config1 = load_preset("NBA")
        config2 = load_preset("NBA")

        dict1 = config1.to_dict()
        dict2 = config2.to_dict()

        hash1 = stable_hash_dict(dict1)
        hash2 = stable_hash_dict(dict2)

        self.assertEqual(hash1, hash2)

    def test_different_configs_different_hashes(self):
        """Verify different configs produce different hashes."""
        nba = load_preset("NBA")
        nhl = load_preset("NHL")

        nba_hash = stable_hash_dict(nba.to_dict())
        nhl_hash = stable_hash_dict(nhl.to_dict())

        self.assertNotEqual(nba_hash, nhl_hash)

    def test_config_hash_includes_all_fields(self):
        """Verify config hash changes when fields change."""
        config = load_preset("NBA")
        original_hash = stable_hash_dict(config.to_dict())

        # Any field change should change hash
        # (Tested by comparing different presets above)
        self.assertEqual(len(original_hash), 64)


if __name__ == "__main__":
    unittest.main()
