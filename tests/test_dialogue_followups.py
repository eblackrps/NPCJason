import json
from pathlib import Path
import unittest

from npcjason_app.dialogue import DialogueLibrary
from tests.helpers import workspace_tempdir


class DialogueFollowUpTests(unittest.TestCase):
    def test_json_packs_parse_follow_up_quotes(self):
        with workspace_tempdir() as temp_dir:
            packs_dir = Path(temp_dir)
            (packs_dir / "follow.json").write_text(
                json.dumps(
                    {
                        "key": "follow-up-pack",
                        "label": "Follow Up Pack",
                        "quotes": [
                            {
                                "text": "Primary line",
                                "follow_ups": [
                                    {
                                        "text": "Secondary line",
                                        "delay_ms": 1500,
                                        "chance": 0.5,
                                        "require_contexts": ["ticket"],
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            library = DialogueLibrary(
                sayings_path=packs_dir / "missing.txt",
                packs_dir=packs_dir,
                pack_states={"builtin-general": False, "builtin-moods": False},
            )

            choice = library.pick_ambient("happy")

            self.assertEqual("Primary line", choice.template)
            self.assertEqual(1, len(choice.follow_ups))
            self.assertEqual("Secondary line", choice.follow_ups[0].text)
            self.assertEqual(1500, choice.follow_ups[0].delay_ms)

    def test_repo_dialogue_packs_include_meltdown_pack(self):
        library = DialogueLibrary()
        pack_keys = {pack["key"] for pack in library.available_packs()}

        self.assertIn("networking-meltdown-helpdesk-chaos", pack_keys)


if __name__ == "__main__":
    unittest.main()
