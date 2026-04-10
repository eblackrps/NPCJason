import unittest

from npcjason_app.desk_items import DeskItemManager


class DeskItemManagerTests(unittest.TestCase):
    def test_available_items_include_expected_desk_bits(self):
        manager = DeskItemManager(root=None)

        items = manager.available_items()
        keys = {item["key"] for item in items}

        self.assertEqual({"coffee-mug", "keyboard", "tiny-network-rack"}, keys)
        self.assertTrue(all(item["cooldown_ms"] == 0 for item in items))
        self.assertEqual("", manager.active_item_key())


if __name__ == "__main__":
    unittest.main()

