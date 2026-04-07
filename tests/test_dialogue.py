import unittest

from npcjason_app.dialogue import merge_pools, parse_dialogue_text


class DialogueTests(unittest.TestCase):
    def test_parse_dialogue_text_handles_sections_and_comments(self):
        payload = """
        ; comment
        [any]
        General line

        [happy]
        Happy line

        # another comment
        [tired]
        Tired line
        """

        parsed = parse_dialogue_text(payload)

        self.assertIn("General line", parsed["any"])
        self.assertIn("Happy line", parsed["happy"])
        self.assertIn("Tired line", parsed["tired"])

    def test_merge_pools_combines_entries(self):
        left = {"any": ["a"], "happy": [], "tired": [], "caffeinated": []}
        right = {"any": ["b"], "happy": ["c"], "tired": [], "caffeinated": []}

        merged = merge_pools(left, right)

        self.assertEqual(["a", "b"], merged["any"])
        self.assertEqual(["c"], merged["happy"])


if __name__ == "__main__":
    unittest.main()
