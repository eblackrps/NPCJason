import unittest

from npcjason_app.dialogue import merge_pools, parse_dialogue_source, parse_dialogue_text, render_template


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

    def test_render_template_replaces_known_tokens_only(self):
        rendered = render_template(
            "Hi {pet_name}. Unknown stays {mystery}. Literal brace: {",
            {"pet_name": "Jason"},
        )

        self.assertEqual(
            "Hi Jason. Unknown stays {mystery}. Literal brace: {",
            rendered,
        )

    def test_parse_dialogue_source_reports_unknown_sections_and_tokens(self):
        parsed, warnings = parse_dialogue_source(
            """
            [boss]
            Beware {unknown_token}
            """,
            source_name="custom.txt",
        )

        self.assertIn("Beware {unknown_token}", parsed["any"])
        self.assertTrue(any("unknown section" in warning for warning in warnings))
        self.assertTrue(any("unknown template token" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
