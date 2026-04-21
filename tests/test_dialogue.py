from pathlib import Path
import unittest

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
        left = {"any": ["a"], "happy": [], "tired": [], "caffeinated": [], "skins": {"veeam": ["d"]}}
        right = {"any": ["b"], "happy": ["c"], "tired": [], "caffeinated": [], "skins": {"veeam": ["e"]}}

        merged = merge_pools(left, right)

        self.assertEqual(["a", "b"], merged["any"])
        self.assertEqual(["c"], merged["happy"])
        self.assertEqual(["d", "e"], merged["skins"]["veeam"])

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

    def test_parse_dialogue_source_handles_skin_sections(self):
        parsed, warnings = parse_dialogue_source(
            """
            [skin:veeam]
            Restore point standing by.
            """,
            source_name="veeam.txt",
        )

        self.assertEqual(["Restore point standing by."], parsed["skins"]["veeam"])
        self.assertEqual([], warnings)

    def test_ambient_pool_includes_only_matching_skin_lines(self):
        with workspace_tempdir() as temp_dir:
            packs_dir = Path(temp_dir)
            (packs_dir / "veeam-pack.txt").write_text(
                """
                [skin:veeam]
                Veeam line
                """,
                encoding="utf-8",
            )
            library = DialogueLibrary(
                sayings_path=packs_dir / "missing.txt",
                packs_dir=packs_dir,
                pack_states={"builtin-general": False, "builtin-moods": False},
            )

            veeam_pool = library.ambient_pool("happy", context={"skin_key": "veeam"})
            classic_pool = library.ambient_pool("happy", context={"skin_key": "jason"})

            self.assertIn("Veeam line", veeam_pool)
            self.assertNotIn("Veeam line", classic_pool)

    def test_veeam_dialogue_pack_parses_without_warnings(self):
        pack_path = Path(__file__).resolve().parents[1] / "dialogue-packs" / "veeam-jason.txt"
        parsed, warnings = parse_dialogue_source(
            pack_path.read_text(encoding="utf-8"),
            source_name=pack_path.name,
        )

        self.assertIn("veeam", parsed["skins"])
        self.assertGreaterEqual(len(parsed["skins"]["veeam"]), 10)
        self.assertEqual([], warnings)


if __name__ == "__main__":
    unittest.main()
