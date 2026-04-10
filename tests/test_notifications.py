import unittest

from npcjason_app.notifications import pick_notification_reaction


class NotificationReactionTests(unittest.TestCase):
    def test_ticket_titles_bias_keyboard_reaction(self):
        reaction = pick_notification_reaction(
            {"contexts": ["title-observed", "title-ticket"], "reaction_key": "jira incident 123"},
            runtime_context={"personality_state": "busy", "active_desk_item": "", "active_companion_interaction": ""},
        )

        self.assertIsNotNone(reaction)
        self.assertEqual("ticket-triage", reaction.key)
        self.assertEqual("keyboard", reaction.desk_item_key)

    def test_unknown_contexts_return_none(self):
        reaction = pick_notification_reaction({"contexts": ["title-observed"]}, runtime_context={})

        self.assertIsNone(reaction)


if __name__ == "__main__":
    unittest.main()
