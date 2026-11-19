"""A corrupt STL must fail verification even with Python assertions disabled."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "tools/verify_release.py"


class FrozenRelease(unittest.TestCase):
    def test_released_kit_then_one_changed_byte(self):
        subprocess.run([sys.executable, VERIFY], check=True)
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            project = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
            manifest_path = project["published_manifest"]
            manifest = json.loads((ROOT / manifest_path).read_text(encoding="utf-8"))
            paths = [item["source"] for group in ("files", "companion_files")
                     for item in manifest.get(group, {}).values()]
            for name in ("project.json", manifest_path, *paths):
                (dest / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, dest / name)
            part = next(p for p in paths if p.endswith(".stl"))
            with (dest / part).open("r+b") as damaged:
                byte = damaged.read(1)[0]
                damaged.seek(0)
                damaged.write(bytes([byte ^ 1]))
            failed = subprocess.run([sys.executable, "-O", VERIFY, "--root", dest],
                                    text=True, capture_output=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn(part, failed.stderr)
            self.assertIn("published bytes differ", failed.stderr)


if __name__ == "__main__":
    unittest.main()
