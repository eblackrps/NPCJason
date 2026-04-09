from pathlib import Path
import unittest

from npcjason_app.store import JsonStore
from tests.helpers import FakeLogger, workspace_tempdir


def default_payload():
    return {"value": 1, "items": []}


class JsonStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = workspace_tempdir()
        self.store_path = Path(self.temp_dir.name) / "store.json"
        self.store = JsonStore(self.store_path, default_payload)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_update_writes_atomically_and_returns_mutator_result(self):
        def mutate(data):
            data["value"] = 2
            data["items"].append("ok")
            return "done"

        result = self.store.update(mutate)
        persisted = self.store.read()

        self.assertEqual("done", result)
        self.assertEqual(2, persisted["value"])
        self.assertEqual(["ok"], persisted["items"])

    def test_read_recovers_from_invalid_json(self):
        self.store_path.write_text("{not valid json", encoding="utf-8")

        payload = self.store.read()

        self.assertEqual(default_payload(), payload)

    def test_invalid_json_is_backed_up_when_logger_is_available(self):
        logger = FakeLogger()
        store = JsonStore(self.store_path, default_payload, logger=logger, store_name="settings")
        self.store_path.write_text("{broken", encoding="utf-8")

        payload = store.read()
        corrupt_files = list(Path(self.temp_dir.name).glob("store.corrupt-*.json"))

        self.assertEqual(default_payload(), payload)
        self.assertEqual(1, len(corrupt_files))
        self.assertTrue(any("backed up" in message for message in logger.messages["warning"]))


if __name__ == "__main__":
    unittest.main()
