"""Check the Git file list and contributor-facing Markdown; no native tools required."""
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
TOP_PRIVATE = {".publish", ".review", ".archify", ".local-tools", "bin", "build", "lib", "pcb", "share", "tmp"}
CACHES = {"node_modules", "__pycache__", ".work", ".venv", "vendor"}
TEXT = {".json", ".py", ".md", ".txt", ".mjs", ".js", ".ps1", ".html", ".svg", ".yml", ".toml"}
PRIVATE_TEXT = re.compile(rb"(?:[a-z]:[\\/]+Users[\\/]+[\w.-]+[\\/]|\bPXL_20\d{6}_\d{6}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)", re.I)


def main():
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    files = {os.fsdecode(p) for p in raw.split(b"\0") if p}
    if not files:
        sys.exit("No tracked files. Run this check in the prepared source repository.")
    errors = []
    for name in sorted(files):
        path = PurePosixPath(name)
        if (path.parts[0] in TOP_PRIVATE or CACHES.intersection(path.parts)
                or name.startswith("docs/mac-mini-m1-implementation/")
                or path.suffix.lower() in {".exe", ".dll", ".pyd", ".pyc"}
                or path.name == ".env" or path.name.startswith(".env.")):
            errors.append(f"local-only file: {name}")
        if path.suffix.lower() in TEXT and PRIVATE_TEXT.search((ROOT / name).read_bytes()):
            errors.append(f"private workstation path, camera filename or key in {name}")
        if not (path.suffix == ".md" and (len(path.parts) == 1 or path.parent == PurePosixPath("docs"))):
            continue
        body = (ROOT / name).read_text(encoding="utf-8")
        for ref in re.findall(r"\]\(([^)\s]+)\)", body):
            url = urlsplit(ref)
            if url.scheme or url.netloc or not url.path:
                continue
            target = posixpath.normpath(posixpath.join(str(path.parent), unquote(url.path)))
            if target not in files and not any(f.startswith(target + "/") for f in files):
                errors.append(f"{name}: link missing from Git: {ref}")
    if errors:
        sys.exit("\n".join(errors))
    print(f"Public tree: {len(files)} tracked files; contributor links and private-file checks passed.")


if __name__ == "__main__":
    main()
