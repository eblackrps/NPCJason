from importlib import util
from pathlib import Path
import sys
from unittest import TestCase, mock
import types


ROOT = Path(__file__).resolve().parents[1]
PATHS_FILE = ROOT / "npcjason_app" / "paths.py"


def load_paths_module(module_name, frozen=False, executable=None, meipass=None):
    package = types.ModuleType("npcjason_app")
    package.__path__ = [str(ROOT / "npcjason_app")]
    sys.modules.setdefault("npcjason_app", package)
    spec = util.spec_from_file_location(f"npcjason_app.{module_name}", PATHS_FILE)
    module = util.module_from_spec(spec)
    executable = executable or str(ROOT / "dist" / "NPCJason.exe")
    meipass = meipass or str(ROOT / "bundle")
    with mock.patch.object(sys, "frozen", frozen, create=True), mock.patch.object(
        sys,
        "executable",
        executable,
        create=True,
    ), mock.patch.object(sys, "_MEIPASS", meipass, create=True):
        module.__package__ = "npcjason_app"
        spec.loader.exec_module(module)
    return module


class PathsTests(TestCase):
    def test_source_mode_resource_dir_points_to_repo_root(self):
        paths = load_paths_module("npcjason_app_paths_source", frozen=False)

        self.assertEqual(ROOT, paths.RESOURCE_DIR)
        self.assertEqual(ROOT / "skins", paths.RESOURCE_SKINS_DIR)

    def test_frozen_mode_resource_dir_points_next_to_exe(self):
        exe_path = Path(r"C:\Program Files\NPCJason\NPCJason.exe")
        bundle_path = Path(r"C:\Users\embla\AppData\Local\Temp\_MEI12345")

        paths = load_paths_module(
            "npcjason_app_paths_frozen",
            frozen=True,
            executable=str(exe_path),
            meipass=str(bundle_path),
        )

        self.assertEqual(exe_path.parent, paths.RESOURCE_DIR)
        self.assertEqual(bundle_path / "skins", paths.BUNDLED_SKINS_DIR)
        self.assertEqual(exe_path.parent / "dialogue-packs", paths.RESOURCE_DIALOGUE_PACKS_DIR)


if __name__ == "__main__":
    import unittest

    unittest.main()
