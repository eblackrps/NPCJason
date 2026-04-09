import unittest
from pathlib import Path

from npcjason_app.dialogue import DialogueLibrary, merge_pools, parse_dialogue_source, parse_dialogue_text, render_template
from tests.helpers import workspace_tempdir


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

    def test_dialogue_library_supports_json_packs_and_repeat_suppression(self):
        with workspace_tempdir() as temp_dir:
            packs_dir = Path(temp_dir)
            (packs_dir / "pack.json").write_text(
                """
                {
                  "key": "focus-pack",
                  "label": "Focus Pack",
                  "quotes": [
                    {"text": "Alpha", "categories": ["network"]},
                    {"text": "Beta", "categories": ["office"]}
                  ]
                }
                """,
                encoding="utf-8",
            )
            library = DialogueLibrary(
                sayings_path=packs_dir / "missing.txt",
                packs_dir=packs_dir,
                pack_states={"builtin-general": False, "builtin-moods": False},
            )

            choice = library.pick_ambient(
                "happy",
                context={"preferred_categories": ["network"], "skin_key": "network"},
                recent_templates=["Alpha"],
                rng=__import__("random").Random(7),
            )

            self.assertEqual("Beta", choice.template)
            self.assertEqual("focus-pack", choice.pack_key)

    def test_dialogue_library_can_disable_pack(self):
        with workspace_tempdir() as temp_dir:
            packs_dir = Path(temp_dir)
            (packs_dir / "pack.json").write_text(
                """
                {
                  "key": "jason-quotes",
                  "label": "Jason Quotes",
                  "quotes": ["not today little phish"]
                }
                """,
                encoding="utf-8",
            )
            library = DialogueLibrary(
                sayings_path=packs_dir / "missing.txt",
                packs_dir=packs_dir,
                pack_states={"jason-quotes": False},
            )

            packs = {pack["key"]: pack for pack in library.available_packs()}

            self.assertIn("jason-quotes", packs)
            self.assertFalse(packs["jason-quotes"]["enabled"])

    def test_dialogue_library_can_enable_default_disabled_pack(self):
        with workspace_tempdir() as temp_dir:
            packs_dir = Path(temp_dir)
            (packs_dir / "pack.json").write_text(
                """
                {
                  "key": "quiet-pack",
                  "label": "Quiet Pack",
                  "enabled": false,
                  "quotes": ["Calm line"]
                }
                """,
                encoding="utf-8",
            )
            library = DialogueLibrary(
                sayings_path=packs_dir / "missing.txt",
                packs_dir=packs_dir,
            )

            self.assertFalse(library.pack_enabled("quiet-pack"))
            self.assertTrue(library.set_pack_enabled("quiet-pack", True))
            self.assertTrue(library.pack_enabled("quiet-pack"))

    def test_dialogue_library_accepts_companion_and_dance_tokens(self):
        with workspace_tempdir() as temp_dir:
            packs_dir = Path(temp_dir)
            (packs_dir / "pack.json").write_text(
                """
                {
                  "key": "companion-pack",
                  "label": "Companion Pack",
                  "quotes": [
                    {"text": "{companion} approved the {dance_routine} routine."}
                  ]
                }
                """,
                encoding="utf-8",
            )
            library = DialogueLibrary(
                sayings_path=packs_dir / "missing.txt",
                packs_dir=packs_dir,
                pack_states={"builtin-general": False, "builtin-moods": False},
            )

            self.assertEqual([], library.warnings)

    def test_repo_dialogue_packs_include_title_and_cisco_humor(self):
        library = DialogueLibrary()
        pack_keys = {pack["key"] for pack in library.available_packs()}

        self.assertIn("app-title-humor", pack_keys)
        self.assertIn("cisco-jokes", pack_keys)


if __name__ == "__main__":
    unittest.main()
