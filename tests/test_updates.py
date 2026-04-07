import unittest

from npcjason_app.updates import is_newer_version, parse_version_tag


class UpdateTests(unittest.TestCase):
    def test_parse_version_tag_handles_v_prefix(self):
        self.assertEqual((1, 2, 0), parse_version_tag("v1.2"))

    def test_is_newer_version(self):
        self.assertTrue(is_newer_version("1.1.0", "v1.1.1"))
        self.assertFalse(is_newer_version("1.1.0", "v1.0.9"))


if __name__ == "__main__":
    unittest.main()
