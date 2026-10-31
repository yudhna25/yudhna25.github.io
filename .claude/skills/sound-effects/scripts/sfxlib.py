"""Shared helpers for the sound-effects skill: catalog loading, search, download."""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "..", "assets", "catalog.json")
DEFAULT_CACHE = os.path.expanduser(os.environ.get("SFX_CACHE", "~/.cache/sfx-quaa"))
DL_URL = "https://drive.usercontent.google.com/download?id={id}&export=download&confirm=t"

# Vietnamese / casual words -> English tags present in the catalog.
SYNONYMS = {
    "chuyen canh": ["transition", "swoosh", "whoosh"],
    "chuyen": ["transition"],
    "luot": ["swoosh", "whoosh", "slide"],
    "vut": ["swoosh", "whoosh"],
    "truot": ["slide"],
    "no": ["boom", "blast", "explosion"],
    "va cham": ["boom", "impact", "hit"],
    "dap": ["impact", "hit", "boom"],
    "impact": ["boom", "impact", "hit"],
    "hit": ["boom", "impact", "hit"],
    "bass": ["bass", "drop"],
    "bat len": ["pop"],
    "xuat hien": ["pop", "appearance", "reveal"],
    "hien chu": ["pop", "title", "slide", "タイトル"],
    "tieu de": ["title", "タイトル"],
    "title": ["title", "タイトル"],
    "click": ["click", "決定", "button"],
    "bam": ["click", "button", "決定"],
    "nut": ["button", "click", "決定"],
    "go phim": ["keyboard", "click", "tap"],
    "go": ["tap", "knock"],
    "thong bao": ["beep", "notification", "ding", "check", "alert"],
    "ding": ["ding", "check", "chime", "bell"],
    "dung": ["check", "ding", "rewards"],
    "thuong": ["rewards"],
    "phan thuong": ["rewards"],
    "loi": ["error", "glitch", "erro"],
    "glitch": ["glitch"],
    "nhieu": ["glitch", "hiss", "crackle"],
    "cong nghe": ["glitch", "sci-fi", "hi-tech", "beep", "buzz"],
    "hud": ["glitch", "beep", "bleep", "sci-fi"],
    "hai": ["funny", "gag", "comical", "cartoon", "doink", "stupid"],
    "hai huoc": ["funny", "gag", "comical", "cartoon", "doink"],
    "nga": ["fall", "slip"],
    "nguong": ["awkward", "cricket"],
    "im lang": ["awkward", "cricket"],
    "soc": ["shock", "doom", "dun", "surprise"],
    "bat ngo": ["surprise", "bất ngờ", "sudden"],
    "that vong": ["disappointment", "sad", "fail", "depression"],
    "buon": ["sad", "depression", "violin"],
    "lap lanh": ["twinkle", "sparkle", "glitter", "shine", "shimmer"],
    "phep thuat": ["magic", "spell", "twinkle"],
    "de thuong": ["cute", "twinkle"],
    "hoi hop": ["suspense", "tension", "riser", "drone"],
    "cang thang": ["suspense", "tension", "drone", "heartbeat"],
    "kinh di": ["horror", "scary", "kinh di", "scream", "suspense"],
    "het": ["scream"],
    "bao dong": ["alert", "siren", "alarm"],
    "nhip tim": ["heartbeat", "heart beat"],
    "riser": ["approach", "riser", "rise", "buildup"],
    "build up": ["approach", "riser", "buildup", "tension"],
    "nen": ["ambience", "atmosphere", "drone", "rumble"],
    "khong khi": ["ambience", "atmosphere"],
    "am tram": ["rumble", "bass", "drone"],
    "xe": ["vroom"],
    "toc do": ["vroom", "swoosh", "flyby"],
    "kim loai": ["clang", "clink", "metal", "anvil"],
    "giay": ["crumple", "rustle"],
    "cua": ["creak"],
    "gio": ["blow", "puff"],
    "keo khoa": ["zip"],
    "meme": ["bruh", "wow", "triggered", "meme", "vine"],
    "chua": ["chuông chùa", "gõ mõ"],
    "chuong": ["bell", "chuông", "chime", "ding", "gong"],
    "slow motion": ["slow motion"],
}


def strip_accents(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm(s):
    return strip_accents(s).lower()


def load_catalog():
    with open(CATALOG, encoding="utf-8") as f:
        return json.load(f)


def expand_terms(query):
    q = norm(query)
    terms = set(t for t in re.split(r"[\s,;/]+", q) if t)
    groups = []
    for key, vals in SYNONYMS.items():
        if re.search(r"(^|\s)" + re.escape(key) + r"(\s|$)", q):
            groups.append([norm(v) for v in vals])
            for w in key.split():
                terms.discard(w)
    for t in terms:
        groups.append([t])
    return groups


def score(entry, groups):
    hay = norm(" ".join([entry["collection"], entry["category"], entry["name"], " ".join(entry.get("tags", []))]))
    s = 0
    for g in groups:
        hit = max((3 if re.search(r"\b" + re.escape(v) + r"\b", hay) else (1 if v in hay else 0)) for v in g)
        if hit == 0:
            return 0
        s += hit
    return s


def search(query="", category=None, collection=None, min_dur=None, max_dur=None,
           shape=None, commercial=False, limit=20):
    cat = load_catalog()
    groups = expand_terms(query) if query else []
    out = []
    for e in cat:
        if "dur" not in e:
            continue
        if commercial and e["collection"] != "Mister Horse Free SFX":
            continue
        if category and norm(category) not in norm(e["category"]):
            continue
        if collection and norm(collection) not in norm(e["collection"]):
            continue
        if min_dur is not None and e["dur"] < min_dur:
            continue
        if max_dur is not None and e["dur"] > max_dur:
            continue
        if shape and e.get("shape") != shape:
            continue
        sc = score(e, groups) if groups else 1
        if sc:
            out.append((sc, e))
    out.sort(key=lambda t: (-t[0], t[1]["collection"] != "Mister Horse Free SFX", t[1]["path"]))
    return [e for _, e in out[:limit]]


def find(ref):
    """Look up an entry by Drive id, exact path, or unique name substring."""
    cat = load_catalog()
    for e in cat:
        if ref in (e["id"], e["path"]):
            return e
    hits = [e for e in cat if norm(ref) in norm(e["path"])]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit(f"Không tìm thấy SFX: {ref}")
    sys.exit(f"'{ref}' khớp {len(hits)} file, hãy dùng id. Ví dụ: " + ", ".join(h["id"] + " " + h["path"] for h in hits[:5]))


def safe_name(e):
    base = re.sub(r"[^\w.\- ]+", "_", e["name"], flags=re.UNICODE).strip()
    return base


def download(e, cache=DEFAULT_CACHE):
    os.makedirs(cache, exist_ok=True)
    dst = os.path.join(cache, e["id"] + "." + e["ext"])
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return dst
    tmp = dst + ".part"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(DL_URL.format(id=e["id"]), timeout=120) as r, open(tmp, "wb") as f:
                ctype = r.headers.get("Content-Type", "")
                if "text/html" in ctype:
                    raise RuntimeError("Drive trả về trang HTML (file có thể đã bị đổi quyền/xoá)")
                shutil.copyfileobj(r, f)
            os.replace(tmp, dst)
            return dst
        except Exception as ex:  # network hiccups: back off and retry
            if attempt == 3:
                raise RuntimeError(f"Tải thất bại {e['path']}: {ex}")
            time.sleep(2 ** (attempt + 1))


def fmt(e):
    return (f"{e['id']}  {e['dur']:6.2f}s  peak@{e.get('peak_t', 0):5.2f}s  "
            f"{e.get('shape', '?'):6s} {e.get('rms_db', 0):6.1f}dB  {e['path']}")


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit("ffmpeg lỗi:\n" + p.stderr[-2000:])
    return p
