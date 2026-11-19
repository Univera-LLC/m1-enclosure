"""Build the organization Pages artifact with the active release and its archives."""
import argparse
import base64
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
from string import Template
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import quote, unquote, urljoin, urlsplit

from verify_release import ROOT, inside, load, require, verify

PAGES = "https://univera-llc.github.io/m1-enclosure/"
RAW = "https://raw.githubusercontent.com/Univera-LLC/m1-enclosure/main/"
REDLINE_ASSETS = ("index.html", "front.webp", "rear.webp", "exploded.webp")
# These archives are not part of the verified D2.6 receipt. Match links and legacy JS redirects.
OLDER = re.compile(r"""(?P<q>["'])\.\./(?P<route>(?:downloads/d2\.5|reference/d2\.5|d1|d2(?:\.[1-4])?|h1)/)""")
ARCHIVE_ASSETS = re.compile(r"""(?P<q>["'])(?:\./)?(?P<route>(?:downloads/d2\.6|reference/d2\.6|accessories|d2\.5)/|d26-connector-section\.svg|d26-rear-assembly\.jpg|d25-vs-d26-usb-audio-comparison\.svg)""")
ARCHIVE_OLDER = re.compile(r"""(?P<q>["'])(?:\./)?(?P<route>(?:d1|d2(?:\.[1-4])?|h1)/)""")
MARKDOWN_LINK = re.compile(r"(\]\()([^()\s]+)(\))")
COMPARE_NAV = re.compile(r'(<nav\b[^>]*\bid="tabs"[^>]*>.*?)(</nav>)', re.S)
COMPARE_TAB = ('<a class="compare-tab" href="compare/index.html"><svg aria-hidden="true" viewBox="0 0 24 24">'
               '<path d="M2.5 7h19v10h-19zM7 7v4m5-4v6m5-6v4"/></svg>Порівняння</a>')
COMPARE_TAB_STYLE = """<style>
#tabs:has(>.compare-tab){grid-template-columns:repeat(9,minmax(0,1fr))}
#tabs:has(>.compare-tab) a{text-align:center;line-height:1.16}
#tabs>.compare-tab{background:#dbeade;color:#25543f}
#tabs>.compare-tab:hover{background:#f2f8ef}
@media(max-width:980px){
  #tabs:has(>.compare-tab){grid-template-columns:repeat(3,minmax(0,1fr))}
  #tabs:has(>.compare-tab) a{grid-column:span 1}
}
</style>"""


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


def uk_number(value, places=2):
    return f"{value:.{places}f}".rstrip("0").rstrip(".").replace(".", ",")


def stage_comparison(dest, viewer, revision, routes):
    """Add a comparison using the released shell, without editing the frozen atlas."""
    source = viewer.parent / "compare"
    catalog = load(source / "catalog.json")
    photo = (source / "assets/zelensky-a4.jpg").read_bytes()
    next(item for item in catalog["objects"] if item["id"] == "portrait")["photo"] = (
        "data:image/jpeg;base64," + base64.b64encode(photo).decode("ascii"))
    report = f"downloads/{revision.lower()}/fit-validation.json"
    case_size = load(routes[report])["assembled_size_xyz_mm"]
    catalog["enclosure"] = {"id": "enclosure", "name": revision, "size": case_size,
                            "basis": "Габарит складання за CAD, з ніжками", "url": "../" + report}
    mac_size = catalog["mac"]["size"]
    case_area, mac_area = case_size[0] * case_size[1], mac_size[0] * mac_size[1]

    rows = []
    for axis, a, b in zip(("Ширина", "Глибина", "Висота"), case_size, mac_size):
        delta = ("−" if a < b else "+" if a > b else "") + uk_number(abs(a - b))
        rows.append(f'<tr><th scope="row">{axis}</th><td>{uk_number(a)}</td><td>{uk_number(b)}</td><td>{delta}</td></tr>')
    choices = ''.join(
        f'<button type="button" data-item="{escape(item["id"])}" aria-pressed="false">{escape(item["name"])}</button>'
        for item in catalog["objects"])
    sources = []
    for item in (catalog["enclosure"], catalog["mac"], *catalog["objects"]):
        title = escape(item["name"])
        name = f'<a href="{escape(item["url"])}">{title}</a>' if "url" in item else title
        size = ("≈ " if item.get("approx") else "") + ' × '.join(map(uk_number, item["size"]))
        sources.append(f'<li>{name} · {size} мм. {escape(item["basis"])}.</li>')
    bundle = json.loads(subprocess.check_output(["node", str(source / "build.mjs"), str(routes["index.html"])],
                                                cwd=ROOT, encoding="utf-8"))
    page = Template((source / "page.html").read_text(encoding="utf-8")).substitute(
        revision=revision, canonical=PAGES + "compare/", rows=''.join(rows), choices=choices,
        sources=''.join(sources), case_area=uk_number(case_area / 100), mac_area=uk_number(mac_area / 100),
        depth_delta=uk_number(mac_size[1] - case_size[1]), height_delta=uk_number(case_size[2] - mac_size[2]),
        area_delta=uk_number(100 * (1 - case_area / mac_area), places=1),
        shared_css=(viewer.parent / "d1/style.css").read_text(encoding="utf-8"),
        css=(source / "style.css").read_text(encoding="utf-8"),
        three_license=(ROOT / "LICENSES/three-js.txt").read_text(encoding="utf-8"),
        script=bundle["script"],
        data=json.dumps(catalog, ensure_ascii=False).replace("<", "\\u003c"))
    page = page.replace("__MODEL__", json.dumps(bundle["models"], separators=(",", ":")), 1)
    (dest / "compare").mkdir()
    (dest / "compare/index.html").write_text(page, encoding="utf-8", newline="\n")

    home_path = dest / "index.html"
    home = home_path.read_text(encoding="utf-8")
    home, slots = COMPARE_NAV.subn(lambda match: match[1] + COMPARE_TAB + match[2], home)
    require(slots == 1 and home.count("</head>") == 1, "missing comparison navigation slot")
    home_path.write_text(home.replace("</head>", COMPARE_TAB_STYLE + "</head>", 1),
                         encoding="utf-8", newline="\n")


def package(dest):
    require(not dest.exists(), f"destination already exists; choose a new directory: {dest}")
    manifest, routes = verify(ROOT)
    rev = manifest["revision"]
    require(rev in {"D2.6", "D2.7"}, "No viewer for the selected release")
    newer = rev == "D2.7"
    older, archived = verify(ROOT, "release/d2.6-manifest.json") if newer else (manifest, routes)
    viewer = ROOT / "cad/solidcraft-m1/viewer/d26"
    expected = download_routes(routes, rev)
    with TemporaryDirectory(prefix="enclosure-viewer-") as temp:
        built = Path(temp) / "viewer"
        subprocess.run(["node", str(viewer / "build.mjs"), "--output", str(built)], cwd=ROOT, check=True)
        if newer:
            require((built / "index.html").read_bytes() == routes["index.html"].read_bytes(),
                    "D2.7 viewer differs from the frozen release page")
        for route in expected:
            require(hashlib.sha256((built / route).read_bytes()).hexdigest() == manifest["files"][route]["sha256"],
                    f"rebuilt download differs from release: {route}")
        dest.mkdir(parents=True, exist_ok=False)
        for route, source in {**archived, **routes}.items():
            target = inside(dest, route)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(built / "index.html" if route == "index.html" else source, target)

    archive = dest / "d2.5/index.html"
    previous = older["target"].rstrip("/") + "/"
    archive.write_text(OLDER.sub(lambda m: m["q"] + previous + m["route"],
                                 archive.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    # The legacy README used site-relative links to the same older revision directories.
    readme = dest / "README.md"
    readme.write_text(re.sub(r"(\]\()((?:d1|d2(?:\.[1-4])?|h1)/)", lambda m: m[1] + previous + m[2],
                             readme.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    if newer:
        old_home = archived["index.html"].read_text(encoding="utf-8")
        old_home = ARCHIVE_ASSETS.sub(lambda m: m["q"] + "../" + m["route"], old_home)
        old_home = ARCHIVE_OLDER.sub(lambda m: m["q"] + previous + m["route"], old_home)
        old_home = old_home.replace('<body>', '<body><p class="wrap"><a href="../">Поточна ревізія D2.7 ↗</a></p>', 1)
        (dest / "d2.6").mkdir()
        (dest / "d2.6/index.html").write_text(old_home, encoding="utf-8", newline="\n")
        shutil.copyfile(readme, dest / "d2.6/README.md")
        readme.write_text(repo_links((ROOT / "README.md").read_text(encoding="utf-8")),
                          encoding="utf-8", newline="\n")

    shutil.copyfile(ROOT / "docs/assets/d26-enclosure.jpg", dest / "enclosure-lab.jpg")
    (dest / "llms.txt").write_text(repo_links((ROOT / "llms.txt").read_text(encoding="utf-8")),
                                  encoding="utf-8", newline="\n")
    notices = repo_links((ROOT / "THIRD_PARTY.md").read_text(encoding="utf-8"))
    download_dirs = (dest / "downloads/d2.6", dest / "downloads/d2.7") if newer else (dest / "downloads/d2.6",)
    for directory in (dest, *download_dirs):
        shutil.copyfile(ROOT / "LICENSE", directory / "LICENSE.txt")
        (directory / "THIRD_PARTY.md").write_text(notices, encoding="utf-8", newline="\n")
        (directory / "LICENSES").mkdir()
        shutil.copyfile(ROOT / "LICENSES/three-js.txt", directory / "LICENSES/three-js.txt")

    redline = dest / "redline"
    redline.mkdir()
    for name in REDLINE_ASSETS:
        shutil.copyfile(ROOT / "release/redline-r2-site" / name, redline / name)
    if not newer:
        home_path = dest / "index.html"
        home_source = home_path.read_text(encoding="utf-8")
        marker = "<!-- PAGES_EXPERIMENT -->"
        require(home_source.count(marker) == 1, "missing Redline navigation slot")
        home_path.write_text(home_source.replace(marker, '<p><a href="redline/">Експеримент Redline R2 ↗</a></p>'),
                             encoding="utf-8", newline="\n")
    else:
        stage_comparison(dest, viewer, rev, routes)
        check_html(dest, "compare/index.html")

    home = check_html(dest, "index.html")
    for route in ("d2.5/index.html", "accessories/index.html", "redline/index.html"):
        check_html(dest, route)
    require(len(expected) == 14 and home.downloads == expected, "organization viewer download set differs")
    for route in expected:
        actual = hashlib.sha256((dest / route).read_bytes()).hexdigest()
        require(actual == manifest["files"][route]["sha256"], f"download differs from release: {route}")
    if newer:
        archive_links = check_html(dest, "d2.6/index.html")
        expected_old = download_routes(archived, "D2.6")
        require(archive_links.downloads == {"../" + path for path in expected_old}, "D2.6 archive download set differs")
        for route in expected_old:
            require(hashlib.sha256((dest / route).read_bytes()).hexdigest() == older["files"][route]["sha256"],
                    f"archived D2.6 download differs: {route}")
    print(f"Organization Pages ready: {dest}; {rev} downloads, preserved D2.6/D2.5 and Redline routes checked.")


def download_routes(routes, revision):
    tag = revision.lower()
    return {r for r in routes if r.startswith(f"downloads/{tag}/") and
            Path(r).suffix in {".stl", ".step", ".sc", ".zip"}} | {f"reference/{tag}/mac-board-reference.glb"}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True, help="new directory for the static Pages site")
    try:
        package(cli.parse_args().output.resolve())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as err:
        sys.exit(f"Pages packaging failed: {err}")
