"""Check the Git file list and contributor-facing Markdown; no native tools required."""
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit
from audit_public_history import Audit

ROOT = Path(__file__).resolve().parents[1]


def main():
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    files = {os.fsdecode(p) for p in raw.split(b"\0") if p}
    if not files:
        sys.exit("No tracked files. Run this check in the prepared source repository.")
    audit = Audit()
    for name in sorted(files):
        path = PurePosixPath(name)
        audit.public_path(name)
        if (ROOT / name).is_symlink():
            audit.flag(name,"symlink requires publication review");continue
        if not (ROOT / name).is_file():
            audit.flag(name,"missing working file");continue
        audit.blob(name,(ROOT / name).read_bytes())
        contributor_doc = len(path.parts) == 1 or path.parent == PurePosixPath("docs") or path.is_relative_to("docs/guides")
        if path.suffix != ".md" or not contributor_doc:
            continue
        body = (ROOT / name).read_text(encoding="utf-8")
        for ref in re.findall(r"\]\(([^)\s]+)\)", body):
            url = urlsplit(ref)
            if url.scheme or url.netloc or not url.path:
                continue
            target = posixpath.normpath(posixpath.join(str(path.parent), unquote(url.path)))
            if target not in files and not any(f.startswith(target + "/") for f in files):
                audit.flag(name,"relative link missing from Git")
    if audit.result(): sys.exit(1)
    print(f"Public tree: {len(files)} tracked working files; contributor links, archives, "
          "embedded models and image metadata passed the privacy preflight.")


if __name__ == "__main__":
    main()
