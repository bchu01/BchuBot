import os
import tempfile
import unittest
from pathlib import Path

from tools.memory import read_memory, write_memory


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "memory.sqlite"
        os.environ["BCHUBOT_MEMORY_DB"] = str(self.db_path)

    def tearDown(self):
        os.environ.pop("BCHUBOT_MEMORY_DB", None)
        self.temp_dir.cleanup()

    def test_write_requires_content(self):
        self.assertEqual(
            write_memory(""),
            {"ok": False, "error": "Memory content is required."},
        )

    def test_write_and_read_memory(self):
        written = write_memory("User prefers oat milk in coffee.")
        self.assertTrue(written["ok"])
        self.assertEqual(written["memory"]["category"], "memory")

        result = read_memory(query="coffee")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["memories"]), 1)
        self.assertIn("oat milk", result["memories"][0]["content"])

    def test_profile_key_is_required_and_updated(self):
        missing_key = write_memory("Brandon", category="profile")
        self.assertEqual(
            missing_key,
            {"ok": False, "error": "A profile key is required, such as 'name'."},
        )

        first = write_memory("Brandon", category="profile", key="name")
        second = write_memory("Brandon Chu", category="profile", key="name")
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(first["memory"]["id"], second["memory"]["id"])

        result = read_memory(query="name", category="profile")
        self.assertEqual(len(result["memories"]), 1)
        self.assertEqual(result["memories"][0]["content"], "Brandon Chu")

    def test_read_without_query_returns_only_a_small_subset(self):
        for index in range(12):
            write_memory(f"Note number {index}")

        result = read_memory()
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["memories"]), 8)

    def test_unrelated_query_returns_no_memories(self):
        write_memory("User likes morning runs.")
        result = read_memory(query="calendar timezone")
        self.assertTrue(result["ok"])
        self.assertEqual(result["memories"], [])


if __name__ == "__main__":
    unittest.main()
