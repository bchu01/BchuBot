import os
import tempfile
import unittest
from pathlib import Path

from tools.memory import forget_memory, memories_for_prompt, read_memory, update_memory, write_memory


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

    def test_update_memory_replaces_content(self):
        written = write_memory("User prefers oat milk.")
        memory_id = written["memory"]["id"]

        updated = update_memory(memory_id, "User prefers almond milk.")
        self.assertTrue(updated["ok"])
        self.assertEqual(updated["memory"]["id"], memory_id)
        self.assertEqual(updated["memory"]["content"], "User prefers almond milk.")

        result = read_memory(query="almond")
        self.assertEqual(len(result["memories"]), 1)

    def test_update_missing_memory(self):
        result = update_memory(999, "Nope")
        self.assertEqual(
            result,
            {"ok": False, "error": "Could not find memory 999."},
        )

    def test_forget_by_id_and_unique_query(self):
        first = write_memory("User prefers oat milk in coffee.")
        write_memory("User likes morning runs.")

        deleted = forget_memory(memory_id=str(first["memory"]["id"]))
        self.assertTrue(deleted["ok"])
        self.assertEqual(deleted["deleted"]["id"], first["memory"]["id"])
        self.assertEqual(read_memory(query="coffee")["memories"], [])

        forgotten = forget_memory(query="morning runs")
        self.assertTrue(forgotten["ok"])
        self.assertEqual(read_memory(query="runs")["memories"], [])

    def test_forget_does_not_guess_when_query_is_ambiguous(self):
        write_memory("User likes tea in the morning.")
        write_memory("User likes tea at night.")

        result = forget_memory(query="tea")
        self.assertFalse(result["ok"])
        self.assertIn("Multiple memories", result["error"])
        self.assertEqual(len(read_memory(query="tea")["memories"]), 2)

    def test_forget_requires_id_or_query(self):
        self.assertEqual(
            forget_memory(),
            {"ok": False, "error": "A memory_id or query is required."},
        )

    def test_prompt_retrieval_matches_keywords_and_includes_profile(self):
        write_memory("Brandon", category="profile", key="name")
        write_memory("User prefers oat milk in coffee.")
        write_memory("User likes morning runs.")

        coffee = memories_for_prompt("What should I put in my coffee?")
        self.assertIsNotNone(coffee)
        self.assertIn("oat milk", coffee)
        self.assertIn("profile name: Brandon", coffee)

        greeting = memories_for_prompt("hi")
        self.assertIsNotNone(greeting)
        self.assertIn("profile name: Brandon", greeting)
        self.assertIn("oat milk", greeting)

    def test_prompt_retrieval_includes_recent_notes_when_keywords_miss(self):
        write_memory("User prefers oat milk in coffee.")
        result = memories_for_prompt("What do I usually have in the morning?")
        self.assertIsNotNone(result)
        self.assertIn("oat milk", result)

    def test_prompt_retrieval_returns_none_when_store_is_empty(self):
        self.assertIsNone(memories_for_prompt("What should I put in my coffee?"))


if __name__ == "__main__":
    unittest.main()
