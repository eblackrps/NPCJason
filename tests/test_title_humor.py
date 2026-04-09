import unittest

from npcjason_app.title_humor import classify_window_title


class TitleHumorTests(unittest.TestCase):
    def test_cisco_titles_bias_cisco_pack(self):
        result = classify_window_title("Cisco AnyConnect Secure Mobility Client")

        self.assertTrue(result["useful"])
        self.assertIn("title-cisco", result["contexts"])
        self.assertIn("network", result["categories"])
        self.assertIn("cisco-jokes", result["preferred_packs"])

    def test_boring_titles_are_ignored(self):
        result = classify_window_title("Settings")

        self.assertFalse(result["useful"])
        self.assertEqual([], result["contexts"])

    def test_generic_titles_need_structure_before_being_funny(self):
        plain = classify_window_title("Quarterly Report")
        structured = classify_window_title("Quarterly Report - VPN / Ticket #42")

        self.assertFalse(plain["interesting"])
        self.assertEqual(0.0, plain["chance"])
        self.assertTrue(structured["interesting"])
        self.assertGreater(structured["chance"], 0.0)


if __name__ == "__main__":
    unittest.main()
