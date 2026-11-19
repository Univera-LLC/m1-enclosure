"""Local privacy preflight for the exact Git tree, embedded design files and reachable history.

Print categories and paths only. This is a narrow project gate; run Gitleaks separately.
"""
import argparse
import base64
import binascii
from collections import Counter
import gzip
import html
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import sys
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
MAX_MEMBER = 128 * 1024 * 1024  # D2.6 has a ~90 MB native CAD cache.
MAX_NESTED = 256 * 1024 * 1024
PATH = re.compile(rb"(?:[A-Z]:[\\/]+(?:Users|Documents and Settings)[\\/]+[\w.-]+[\\/]|/(?:home|Users)/[\w.-]+/|\b(?:PXL|IMG)_20\d{6}_\d{6})", re.I)
TOKENS = re.compile(rb"(?:-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----|\b(?:gh[pousr]_[A-Za-z0-9]{32,}|github_pat_[A-Za-z0-9_]{40,}|(?:AKIA|ASIA)[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{15,}|AIza[\w-]{32,}|sk-(?:proj-|live-|test-)?[A-Za-z0-9_-]{24,}))")
AUTH_URL = re.compile(rb"https?://[^/@\s<>\x22\x27]{1,160}:[^/@\s<>\x22\x27]{1,160}@", re.I)
EMAIL = re.compile(rb"[A-Z0-9._%+-]{1,64}@(?:[A-Z0-9-]{1,63}\.){1,6}(?:[A-Z]{2}|com|org|net|info|biz|edu|gov|dev|app|cloud|online|tech|email|xyz)\b", re.I)
OWN_DOMAIN = {b"example.com", b"example.net", b"example.org", b"users.noreply.github.com"}
TEXT_EXT = {".json",".py",".md",".txt",".js",".mjs",".ps1",".html",".svg",".yml",".yaml",".toml",".css",".lock",".step",".stp",".xml",".ini"}
TOP_PRIVATE = {".publish",".review",".archify",".local-tools","bin","build","dist","lib","pcb","share","tmp"}
CACHES = {"node_modules","__pycache__",".work",".venv","vendor",".ssh",".aws"}
EMBEDDED = re.compile(rb'<script\b[^>]*?\bid="(model-bytes|glbs)"[^>]*>([^<]*)</script>', re.I)
MEDIA = re.compile(rb'data:(image/(?:webp|jpeg|png|svg\+xml));base64,([a-zA-Z0-9+/=]+)', re.I)
PRIVATE_NET = re.compile(rb"https?://(?:[^/\s]+\.(?:internal|local|corp)|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)(?=[:/\s'\x22]|$)", re.I)


def public_email(value):
    domain = value.rsplit(b"@", 1)[-1].lower()
    return domain in OWN_DOMAIN or domain.endswith((b".invalid", b".example"))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.PIPE)


class Audit:
    def __init__(self):
        self.findings = set()
        self.count = Counter()

    def flag(self, path, category):
        # A malicious filename may itself contain a secret. Never echo such a name.
        label = path.encode("utf-8", "replace")
        if EMAIL.search(label) or TOKENS.search(label) or AUTH_URL.search(label) or PATH.search(label):
            path = "<redacted path>"
        self.findings.add((path, category))

    def text(self, path, raw):
        if PATH.search(raw): self.flag(path, "personal workstation path or camera filename")
        if TOKENS.search(raw): self.flag(path, "credential-shaped value")
        if AUTH_URL.search(raw): self.flag(path, "URL with embedded credentials")
        if PRIVATE_NET.search(raw): self.flag(path, "private network URL")
        if b"@" in raw and any(not public_email(m[0]) for m in EMAIL.finditer(raw)):
            self.flag(path, "email address requiring review")

    def public_path(self, name):
        p=PurePosixPath(name)
        self.text("<Git path>",name.encode("utf-8","replace"))
        if (p.parts[0] in TOP_PRIVATE or CACHES.intersection(p.parts)
            or name.startswith("docs/mac-mini-m1-implementation/")
            or p.suffix.lower() in {".exe",".dll",".pyd",".pyc",".pfx",".p12",".key"}
            or p.name==".env" or p.name.startswith(".env.")):
            self.flag(name,"local-only file")

    def blob(self, path, raw, depth=0, budget=None):
        if budget is None: budget = [MAX_NESTED]
        budget[0] -= len(raw)
        if depth > 6 or len(raw) > MAX_MEMBER or budget[0] < 0:
            self.flag(path,"embedded file exceeds audit budget");return
        ext = PurePosixPath(path).suffix.lower()
        try:
            if ext in {".sc",".zip"}:
                with ZipFile(BytesIO(raw)) as z:
                    names = set()
                    for i, member in enumerate(z.infolist()):
                        if i >= 1000 or member.file_size > MAX_MEMBER or member.file_size > budget[0]:
                            raise ValueError("member limit")
                        if member.filename in names or member.flag_bits & 1:
                            raise ValueError("duplicate or encrypted member")
                        if (".." in PurePosixPath(member.filename).parts or member.filename.startswith(("/","\\"))
                            or "\\" in member.filename or ":" in member.filename or (member.external_attr>>16)&0o170000==0o120000):
                            raise ValueError("unsafe archive path or symlink")
                        names.add(member.filename)
                        if not member.is_dir():
                            self.count["archive members"] += 1
                            self.text(path + "!<member name>", member.filename.encode())
                            self.blob(path + "!" + member.filename, z.read(member), depth + 1, budget)
                return
            if ext == ".glb":
                if len(raw)<20 or raw[:4]!=b"glTF" or struct.unpack_from("<II",raw,4)!=(2,len(raw)):
                    raise ValueError("invalid GLB")
                at=12; document=None; binary=b""
                while at<len(raw):
                    size,kind=struct.unpack_from("<I4s",raw,at);at+=8
                    if at+size>len(raw):raise ValueError("invalid GLB chunk")
                    if kind==b"JSON":
                        metadata=raw[at:at+size];document=json.loads(metadata)
                        self.count["GLB JSON chunks"]+=1
                        self.blob(path+"!gltf.json",metadata,depth+1,budget)
                    elif kind==b"BIN\0":binary=raw[at:at+size]
                    at+=size
                if document is None:raise ValueError("missing GLB JSON")
                for i,im in enumerate(document.get("images",[])):
                    if "bufferView" in im:
                        view=document["bufferViews"][im["bufferView"]]
                        start=view.get("byteOffset",0);end=start+view["byteLength"]
                        suffix={"image/png":"png","image/jpeg":"jpg","image/webp":"webp"}.get(im.get("mimeType"))
                        if view["buffer"]!=0 or not suffix or not 0<=start<end<=len(binary):
                            raise ValueError("invalid GLB image")
                        self.blob(f"{path}!image-{i}.{suffix}",binary[start:end],depth+1,budget)
                    elif isinstance(im.get("uri"),str):
                        match=MEDIA.fullmatch(im["uri"].encode())
                        if not match: self.flag(path,"external or unsupported GLB image");continue
                        suffix=match[1].split(b"/")[1].split(b"+")[0].decode()
                        self.blob(f"{path}!image-{i}.{suffix}",base64.b64decode(match[2],validate=True),depth+1,budget)
                    else:raise ValueError("invalid GLB image")
                return
            if ext in {".jpg",".jpeg",".webp",".png"}:
                self.count["images"]+=1
                if any(t in raw for t in (b"Exif\0\0",b"EXIF",b"XMP ",b"http://ns.adobe.com/xap/",b"Photoshop 3.0\0",b"iTXt",b"tEXt",b"zTXt",b"eXIf")):
                    self.flag(path,"image EXIF/XMP, IPTC or text metadata requires review")
                return
            if ext in TEXT_EXT or not ext or PurePosixPath(path).name.startswith("."):
                if ext==".html":
                    for block in EMBEDDED.finditer(raw):
                        if block[2]==b"__MODEL__":continue  # Source HTML template.
                        vals=json.loads(block[2]).values() if block[1].lower()==b"glbs" else [block[2]]
                        for i,value in enumerate(vals):
                            if budget[0]<=0:raise ValueError("embedded data budget")
                            compressed=base64.b64decode(value,validate=True)
                            with gzip.GzipFile(fileobj=BytesIO(compressed)) as g: plain=g.read(min(budget[0],MAX_MEMBER)+1)
                            self.blob(f"{path}!model-{i}.glb",plain,depth+1,budget)
                    for i,m in enumerate(MEDIA.finditer(raw)):
                        kind=m[1].split(b"/")[1].split(b"+")[0].decode()
                        self.blob(f"{path}!inline-{i}.{kind}",base64.b64decode(m[2],validate=True),depth+1,budget)
                    # Long binary literals aren't prose or program text; their decoded contents were scanned above.
                    raw=MEDIA.sub(b"",EMBEDDED.sub(b"",raw))
                if ext in {".html",".json",".js",".svg"}:
                    raw=re.sub(rb"\\u([A-Fa-f0-9]{4})",lambda m:chr(int(m[1],16)).encode("utf-8","replace"),raw)
                    raw=html.unescape(raw.decode("utf-8","replace")).encode().replace(b"\\/",b"/")
                self.text(path,raw)
                if ext in {".step",".stp"}:
                    header=re.search(rb"FILE_NAME\s*\((.+?)\)\s*;",raw[:65536],re.S)
                    fields=re.findall(rb"'([^']*)'",header[1]) if header else []
                    if len(fields)!=7 or fields[2].strip() or fields[3].strip():
                        self.flag(path,"STEP author/organization metadata requires review")
                return
            # Numeric binary buffers aren't text. Check likely strings without running broad regexes over all vertices.
            if any(key in raw for key in (b"-----BEGIN ", b"ghp_", b"github_pat_", b"AKIA", b"ASIA",
                                          b"xoxb-", b"sk-proj-", b"Users\\", b"/Users/", b"/home/", b"PXL_20")):
                if PATH.search(raw) or TOKENS.search(raw):self.flag(path,"credential or private path in binary")
        except (BadZipFile, ValueError, KeyError, IndexError, TypeError, EOFError, OSError, struct.error, binascii.Error, UnicodeError):
            self.flag(path, "malformed or uninspectable embedded content")

    def result(self):
        for path,category in sorted(self.findings):
            print(f"{category}: {path}",file=sys.stderr)
        return int(bool(self.findings))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument("--tree",default="HEAD",help="exact Git commit/tree to scan (default: HEAD)")
    group.add_argument("--history",action="store_true",help="all commits, annotated tags and unique blobs reachable from local refs")
    args=parser.parse_args()
    audit=Audit(); blobs={}; commits=[]
    if args.history:
        commits=git("rev-list","--all").decode().splitlines()
        for commit in commits:
            data=git("cat-file","commit",commit)
            audit.text("commit "+commit[:12],data)
            for who in re.finditer(rb"^(?:author|committer) [^\n]*? <([^<>]+)>",data,re.M):
                if not public_email(who[1]):audit.flag("commit "+commit[:12],"non-placeholder/non-noreply Git actor email")
        for line in git("for-each-ref","--format=%(objecttype) %(objectname)","refs/tags").decode().splitlines():
            kind,oid=line.split()
            if kind=="tag":audit.text("tag "+oid[:12],git("cat-file","tag",oid))
    trees={git("rev-parse",rev+"^{tree}").decode().strip() for rev in (commits if args.history else [args.tree])}
    for tree in trees:
        for row in git("ls-tree","-rz",tree).split(b"\0"):
            if not row: continue
            meta,name=row.split(b"\t",1);mode,kind,oid=meta.split()
            path=name.decode("utf-8","replace")
            audit.public_path(path)
            if mode in (b"120000",b"160000"):audit.flag(path,"symlink or submodule requires publication review")
            if kind==b"blob":blobs[(oid,PurePosixPath(path).suffix.lower())]=path
    if not blobs:parser.error("No Git blobs to audit")
    # A single git process reads the exact stored blobs; ignored local files are never opened.
    with subprocess.Popen(["git","cat-file","--batch"],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE) as p:
        for (oid,ext),path in blobs.items():
            p.stdin.write(oid+b"\n");p.stdin.flush()
            _,kind,size=p.stdout.readline().split()
            if kind!=b"blob":raise ValueError("not a blob")
            size=int(size)
            if size>MAX_MEMBER:
                audit.flag(path,"Git blob exceeds audit budget")
                while size:
                    chunk=p.stdout.read(min(size,1024*1024))
                    if not chunk:raise ValueError("incomplete Git blob")
                    size-=len(chunk)
                p.stdout.read(1);continue
            raw=p.stdout.read(size);p.stdout.read(1)
            audit.blob(path,raw)
        p.stdin.close()
    print(f"Audited {len(trees)} Git tree(s), {len(blobs)} unique blob/type pairs, {len(commits)} history commits; "
          + ", ".join(f"{v} {k}" for k,v in sorted(audit.count.items())) + f"; {len(audit.findings)} findings.")
    return audit.result()


if __name__=="__main__":
    sys.exit(main())
