"""Exercise the published Linux installer without downloading or running an uploader."""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

REFERENCE = (Path(__file__).resolve().parents[1]
             / "skills/workflows/itch-publish/references/butler-ci.md")


@unittest.skipUnless(shutil.which("bash") and shutil.which("sha256sum"),
                     "Bash and sha256sum required for the Linux install examples")
class ButlerInstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        markdown = REFERENCE.read_text(encoding="utf-8")
        cls.installers = [re.search(r"```bash\n(.*?)```", markdown, re.S)[1]]
        action = re.search(r"      - name: Install butler\n        run: \|\n(.*?)"
                           r"(?=      - name:)", markdown, re.S)[1]
        cls.installers.append(textwrap.dedent(action))

    def install(self, snippet, *, valid):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            commands = root / "bin"
            commands.mkdir()
            archive = root / "fixture.zip"
            archive.write_bytes(b"local fixture, never a real executable")
            expected = hashlib.sha256(archive.read_bytes()).hexdigest() if valid else "0" * 64
            # Replace only the reviewed digest so the published shell's verification runs unchanged.
            source = re.sub(r"(?m)^BUTLER_SHA256=[0-9a-f]{64}$",
                            "BUTLER_SHA256=" + expected, snippet)
            (commands / "curl").write_text(
                '#!/bin/sh\ncp "$FIXTURE_ARCHIVE" butler.zip\n', encoding="utf-8")
            (commands / "unzip").write_text(
                '#!/bin/sh\nprintf extracted > extracted\n'
                'printf \'#!/bin/sh\\nprintf executed > executed\\n\' > butler\n',
                encoding="utf-8")
            for command in commands.iterdir():
                command.chmod(0o755)
            env = dict(os.environ, PATH=str(commands) + os.pathsep + os.environ["PATH"],
                       FIXTURE_ARCHIVE=str(archive))
            env.pop("BUTLER_API_KEY", None)
            result = subprocess.run([shutil.which("bash"), "-c", source], cwd=root,
                                    env=env, capture_output=True, text=True, timeout=10)
            if valid:
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue((root / "extracted").exists())
                self.assertTrue((root / "butler").exists())
            else:
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((root / "extracted").exists())
                self.assertFalse((root / "executed").exists())
                self.assertFalse((root / "butler").exists())

    def test_checksum_mismatch_blocks_extraction_and_execution(self):
        for index, snippet in enumerate(self.installers):
            with self.subTest(example=index):
                self.install(snippet, valid=False)

    def test_verified_fixture_can_reach_the_install_steps(self):
        for index, snippet in enumerate(self.installers):
            with self.subTest(example=index):
                self.install(snippet, valid=True)


if __name__ == "__main__":
    unittest.main()
