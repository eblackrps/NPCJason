import unittest
import time

from npcjason_app.coordination import PetCoordinator
from tests.helpers import MemoryStore


class CoordinationTests(unittest.TestCase):
    def test_consume_commands_removes_executed_entries(self):
        created_at = time.time()
        store = MemoryStore(
            {
                "instances": {},
                "conversations": [],
                "commands": [
                    {"id": "1", "target": "main", "action": "quit", "created_at": created_at},
                    {"id": "2", "target": "other", "action": "quit", "created_at": created_at},
                ],
            }
        )
        coordinator = PetCoordinator(store, "main")

        actions = coordinator.consume_commands()

        self.assertEqual(["quit"], actions)
        self.assertEqual(["2"], [command["id"] for command in store.payload["commands"]])

    def test_pending_conversations_filters_seen_and_non_participants(self):
        store = MemoryStore(
            {
                "instances": {},
                "conversations": [
                    {"id": "seen", "created_at": 10, "participants": ["main"], "lines": {"main": "old"}},
                    {"id": "keep", "created_at": 10, "participants": ["main", "friend"], "lines": {"main": "hi"}},
                    {"id": "skip", "created_at": 10, "participants": ["friend"], "lines": {"friend": "yo"}},
                ],
                "commands": [],
            }
        )
        coordinator = PetCoordinator(store, "main")

        pending = coordinator.pending_conversations({"seen"}, now=15)

        self.assertEqual(["keep"], [conversation["id"] for conversation in pending])

    def test_invalid_shared_state_is_sanitized_on_read(self):
        store = MemoryStore({"instances": [], "conversations": "bad", "commands": None})
        coordinator = PetCoordinator(store, "main")

        pending = coordinator.pending_conversations(set(), now=15)

        self.assertEqual([], pending)
        self.assertEqual({}, store.payload["instances"])
        self.assertEqual([], store.payload["conversations"])
        self.assertEqual([], store.payload["commands"])


if __name__ == "__main__":
    unittest.main()
