"""`arena dump --set` changes the dump and nothing else (2026-10-16).

It used to overwrite workspace.toml with the [workspace] section alone, which
dropped [coder] and made the next `arena coder prepare` refuse to run.
"""
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from pipeline import cli

FULL = '''[workspace]
dump = "/old/dump"

[coder]
url = "https://coder.example.invalid"
workspace = "pool-a"   # a comment survives
tasks_per_instance = 40
'''


class DumpSetKeepsSections(unittest.TestCase):
    def test_only_the_dump_line_changes(self):
        out = cli._with_dump(FULL, Path("/new/dump"))
        self.assertEqual(tomllib.loads(out)["workspace"]["dump"], "/new/dump")
        self.assertEqual(tomllib.loads(out)["coder"], tomllib.loads(FULL)["coder"])
        self.assertIn("# a comment survives", out)
        self.assertEqual(out.count("dump ="), 1)

    def test_missing_workspace_section_or_dump_line_is_added(self):
        coder_only = FULL.split("\n\n", 1)[1]
        out = cli._with_dump(coder_only, Path("/d"))
        self.assertEqual(tomllib.loads(out)["workspace"]["dump"], "/d")
        self.assertEqual(tomllib.loads(out)["coder"]["workspace"], "pool-a")
        no_line = FULL.replace('dump = "/old/dump"\n', "")
        self.assertEqual(tomllib.loads(cli._with_dump(no_line, Path("/d")))["workspace"]["dump"], "/d")
        self.assertEqual(tomllib.loads(cli._with_dump("", Path("/d"))), {"workspace": {"dump": "/d"}})

    def test_the_command_keeps_coder(self):
        with tempfile.TemporaryDirectory() as tmp:
            dump = Path(tmp) / "dump"
            (dump / "sessions" / "s1").mkdir(parents=True)
            workspace = Path(tmp) / "workspace.toml"
            workspace.write_text(FULL)
            with mock.patch.object(cli, "WORKSPACE", workspace), \
                    mock.patch("sys.stdout"):
                self.assertEqual(cli.cmd_dump(mock.Mock(set=str(dump))), 0)
            parsed = tomllib.loads(workspace.read_text())
            self.assertEqual(parsed["workspace"]["dump"], str(dump.resolve()))
            self.assertEqual(parsed["coder"]["workspace"], "pool-a")


if __name__ == "__main__":
    unittest.main()
