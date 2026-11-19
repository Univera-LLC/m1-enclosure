"""Build the organization Pages artifact from D2.6 and the separate Redline preview."""
import argparse
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import quote, unquote, urljoin, urlsplit

from verify_release import ROOT, inside, require, verify

PAGES = "https://univera-llc.github.io/m1-enclosure/"
RAW = "https://raw.githubusercontent.com/Univera-LLC/m1-enclosure/main/"
REDLINE_ASSETS = ("index.html", "front.webp", "rear.webp", "exploded.webp")
# These archives are not part of the verified D2.6 receipt. Match links and legacy JS redirects.
OLDER = re.compile(r"""(?P<q>["'])\.\./(?P<route>(?:downloads/d2\.5|reference/d2\.5|d1|d2(?:\.[1-4])?|h1)/)""")
MARKDOWN_LINK = re.compile(r"(\]\()([^()\s]+)(\))")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls, self.downloads = set(), set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("property") in {"og:image", "og:url"}:
            self.urls.add(a["content"])
        for key in ("href", "src", "poster"):
            if a.get(key) and not a[key].startswith(("data:", "#")):
                self.urls.add(a[key])
        if tag == "a" and "download" in a:
            self.downloads.add(a["href"])


def repo_links(text):
    """Keep text intact but resolve source-relative Markdown links for readers on Pages."""
    def mapped(match):
        ref = match[2]
        url = urlsplit(ref)
        if url.scheme or url.netloc or not url.path:
            return match[0]
        require(inside(ROOT, unquote(url.path)).is_file(), f"missing source document: {ref}")
        return match[1] + urljoin(RAW, quote(unquote(url.path), safe="/")) + (
            "#" + url.fragment if url.fragment else "") + match[3]
    return MARKDOWN_LINK.sub(mapped, text)


def check_html(dest, page):
    links = Links()
    links.feed((dest / page).read_text(encoding="utf-8"))
    org = urlsplit(PAGES)
    for url in links.urls:
        resolved = urlsplit(urljoin(PAGES + page, url))
        if resolved.netloc != org.netloc:
            continue
        require(resolved.path.startswith(org.path), f"{page} leaves organization site root: {url}")
        rel = unquote(resolved.path[len(org.path):])
        if not rel or rel.endswith("/"):
            rel += "index.html"
        require(inside(dest, rel).is_file(), f"{page}: missing static route {url}")
    return links


def package(dest):
    require(not dest.exists(), f"destination already exists; choose a new directory: {dest}")
    manifest, routes = verify(ROOT)
    require(manifest["revision"] == "D2.6", "Pages packaging expects the D2.6 viewer")
    viewer = ROOT / "cad/solidcraft-m1/viewer/d26"
    subprocess.run(["node", str(viewer / "build.mjs")], cwd=ROOT, check=True)
    built = ROOT / "build/d26-viewer"
    dest.mkdir(parents=True, exist_ok=False)
    for route, source in routes.items():
        target = inside(dest, route)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(built / "index.html" if route == "index.html" else source, target)

    archive = dest / "d2.5/index.html"
    previous = manifest["target"].rstrip("/") + "/"
    archive.write_text(OLDER.sub(lambda m: m["q"] + previous + m["route"],
                                 archive.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    # The legacy README used site-relative links to the same older revision directories.
    readme = dest / "README.md"
    readme.write_text(re.sub(r"(\]\()((?:d1|d2(?:\.[1-4])?|h1)/)", lambda m: m[1] + previous + m[2],
                             readme.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")

    shutil.copyfile(ROOT / "docs/assets/d26-enclosure.jpg", dest / "enclosure-lab.jpg")
    (dest / "llms.txt").write_text(repo_links((ROOT / "llms.txt").read_text(encoding="utf-8")),
                                  encoding="utf-8", newline="\n")
    notices = repo_links((ROOT / "THIRD_PARTY.md").read_text(encoding="utf-8"))
    for directory in (dest, dest / "downloads/d2.6"):
        shutil.copyfile(ROOT / "LICENSE", directory / "LICENSE.txt")
        (directory / "THIRD_PARTY.md").write_text(notices, encoding="utf-8", newline="\n")
        (directory / "LICENSES").mkdir()
        shutil.copyfile(ROOT / "LICENSES/three-js.txt", directory / "LICENSES/three-js.txt")

    redline = dest / "redline"
    redline.mkdir()
    for name in REDLINE_ASSETS:
        shutil.copyfile(ROOT / "release/redline-r2-site" / name, redline / name)
    home_path = dest / "index.html"
    home_source = home_path.read_text(encoding="utf-8")
    marker = "<!-- PAGES_EXPERIMENT -->"
    require(home_source.count(marker) == 1, "missing Redline navigation slot")
    home_path.write_text(home_source.replace(marker, '<p><a href="redline/">Експеримент Redline R2 ↗</a></p>'),
                         encoding="utf-8", newline="\n")

    home = check_html(dest, "index.html")
    for route in ("d2.5/index.html", "accessories/index.html", "redline/index.html"):
        check_html(dest, route)
    expected = {r for r in routes if r.startswith("downloads/d2.6/") and
                Path(r).suffix in {".stl", ".step", ".sc", ".zip"}} | {"reference/d2.6/mac-board-reference.glb"}
    require(len(expected) == 14 and home.downloads == expected, "organization viewer download set differs")
    for route in expected:
        for base in (built, dest):
            actual = hashlib.sha256((base / route).read_bytes()).hexdigest()
            require(actual == manifest["files"][route]["sha256"], f"download differs from release: {route}")
    print(f"Organization Pages ready: {dest}; Redline preview and D2.6 routes checked, all 14 downloads match D2.6.")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True, help="new directory for the static Pages site")
    try:
        package(cli.parse_args().output.resolve())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as err:
        sys.exit(f"Pages packaging failed: {err}")
