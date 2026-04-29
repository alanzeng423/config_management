from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cfgsync import core


class CoreTests(unittest.TestCase):
    def test_add_status_refresh_and_diff_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            source = root / "ghostty.conf"
            source.write_text("font-size = 14\n", encoding="utf-8")

            core.init(vault)
            item = core.add(vault, "ghostty", source)
            self.assertEqual(item.kind, "file")
            self.assertEqual(core.status(vault)[0].state, "clean")

            source.write_text("font-size = 16\n", encoding="utf-8")
            self.assertEqual(core.status(vault)[0].state, "changed")
            self.assertIn("+font-size = 16", core.diff(vault, "ghostty"))

            core.refresh(vault, "ghostty")
            self.assertEqual(core.status(vault)[0].state, "clean")

    def test_install_symlink_with_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            source = root / "claude.json"
            source.write_text('{"theme":"dark"}\n', encoding="utf-8")

            core.add(vault, "claude", source)
            source.write_text("local change\n", encoding="utf-8")
            actions = core.install(vault)

            self.assertIn("claude: link", actions[0])
            self.assertTrue(source.is_symlink())
            self.assertTrue((root / "claude.json.cfgsync.bak").exists())
            self.assertEqual(source.read_text(encoding="utf-8"), '{"theme":"dark"}\n')

    def test_directory_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            source = root / "hermes"
            source.mkdir()
            (source / "settings.json").write_text("{}\n", encoding="utf-8")

            core.add(vault, "hermes", source)
            self.assertEqual(core.status(vault)[0].state, "clean")
            (source / "settings.json").write_text('{"x":1}\n', encoding="utf-8")
            self.assertEqual(core.status(vault)[0].state, "changed")


if __name__ == "__main__":
    unittest.main()
