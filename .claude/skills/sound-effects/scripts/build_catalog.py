#!/usr/bin/env python3
"""Quét lại thư mục Drive công khai, đo từng file và sinh assets/catalog.json + references/catalog.md.
  python3 build_catalog.py [--folder <drive_folder_id>] [--reuse analysis.json] [--workers 12]
Mất ~10–15 phút cho ~1.300 file (tải từng file, đo, xoá ngay; cần ffmpeg + numpy).
"""
import argparse, concurrent.futures as cf, html, json, os, re, subprocess, sys, tempfile, urllib.request
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "1L4WOlQINxD45bRTikaUmV6QZ362P41rh"
AUDIO = {"wav", "mp3", "mp4", "webm", "aac", "m4a", "ogg", "flac", "aif", "aiff"}

def crawl(fid, path=()):
    h = urllib.request.urlopen(f"https://drive.google.com/embeddedfolderview?id={fid}", timeout=60).read().decode("utf-8", "replace")
    out = []
    for m in re.finditer(r'<div class="flip-entry" id="entry-([^"]+)".*?flip-entry-title">([^<]*)<', h, re.S):
        eid, title = m.group(1), html.unescape(m.group(2))
        if "/folders/" in h[m.start():m.start() + 600]:
            if title.startswith("_Mister Horse Previews"):
                continue  # chỉ là ảnh waveform PNG
            out += crawl(eid, path + (title,))
        elif title.rsplit(".", 1)[-1].lower() in AUDIO:
            out.append({"id": eid, "path": "/".join(path + (title,))})
    return out

def measure(x, tmp):
    import numpy as np
    r = dict(x)
    fn = os.path.join(tmp, x["id"])
    try:
        urllib.request.urlretrieve(f"https://drive.usercontent.google.com/download?id={x['id']}&export=download&confirm=t", fn)
        pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", fn],
                                       capture_output=True, text=True).stdout)
        r["dur"] = round(float(pr["format"]["duration"]), 3)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", fn, "-t", "120", "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                             capture_output=True).stdout
        y = np.frombuffer(raw, dtype=np.float32)
        n = len(y) // 160
        env = np.sqrt((y[:n * 160].reshape(n, 160) ** 2).mean(1) + 1e-12)
        i = int(env.argmax()); on = int(np.argmax(env > env.max() * 0.1))
        above = np.where(env > env.max() * 0.03)[0]
        r.update(peak_db=round(float(20 * np.log10(np.abs(y).max() + 1e-9)), 1),
                 rms_db=round(float(20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-9)), 1),
                 peak_t=round(i * 0.01, 2), onset_t=round(on * 0.01, 2), attack=round((i - on) * 0.01, 2),
                 tail_t=round(float(above[-1] + 1) * 0.01, 2) if len(above) else r["dur"])
    except Exception as e:
        r["err"] = str(e)[:200]
    finally:
        if os.path.exists(fn): os.remove(fn)
    return r

TAGWORDS = re.compile(r"[A-Za-zÀ-ỹ぀-ヿ一-鿿]+")
STOP = {"sound", "effect", "effects", "sfx", "hd", "the", "mp3", "wav", "sba", "es", "epidemic", "free", "audio", "y2mate", "com"}

def to_catalog(rows):
    cat = []
    for r in rows:
        if "dur" not in r: continue
        parts = r["path"].split("/")
        col, name = parts[0], parts[-1]
        category = "/".join(parts[1:-1])
        stem, ext = name.rsplit(".", 1)
        att = r.get("attack", 0)
        shape = "bed" if r["dur"] > 8 else "hit" if att < 0.06 else "swell" if att >= 0.3 else "short"
        tags = sorted({w.lower() for w in TAGWORDS.findall(stem + " " + category) if w.lower() not in STOP and len(w) > 1})
        cat.append(dict(id=r["id"], path=r["path"], collection=col, category=category, name=name, ext=ext.lower(),
                        dur=r["dur"], peak_t=r.get("peak_t", 0), onset_t=r.get("onset_t", 0), tail_t=r.get("tail_t", r["dur"]),
                        attack=att, peak_db=r.get("peak_db"), rms_db=r.get("rms_db"), shape=shape, tags=tags))
    cat.sort(key=lambda e: (e["collection"], e["category"], e["name"].lower()))
    return cat

def to_markdown(cat):
    groups = defaultdict(list)
    for e in cat: groups[(e["collection"], e["category"])].append(e)
    lines = ["# Catalog SFX — BASIC SFX QUẠ HD", "",
             f"{len(cat)} file. Cột: tên · thời lượng (s) · peak_t (s, điểm nhấn) · shape · rms dB · Drive ID.",
             "Tìm nhanh: `grep -n '^## ' catalog.md` để xem danh mục, rồi đọc đoạn cần thiết.",
             "Link nghe thử: https://drive.google.com/file/d/<ID>/view", "", "## Mục lục", ""]
    for (col, c), es in groups.items():
        lines.append(f"- {col} / {c or '(gốc)'} — {len(es)}")
    for (col, c), es in groups.items():
        lines += ["", f"## {col} / {c or '(gốc)'}", "", "| Tên | Dur | Peak | Shape | RMS | ID |", "|---|---|---|---|---|---|"]
        for e in es:
            nm = e["name"].replace("|", "/")
            lines.append(f"| {nm} | {e['dur']:.2f} | {e['peak_t']:.2f} | {e['shape']} | {e['rms_db']} | `{e['id']}` |")
    return "\n".join(lines) + "\n"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default=ROOT)
    ap.add_argument("--reuse", help="dùng kết quả đo có sẵn (bỏ qua tải/đo)")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    if a.reuse:
        rows = [r for r in json.load(open(a.reuse, encoding="utf-8"))
                if r["path"].rsplit(".", 1)[-1].lower() in AUDIO and "_Mister Horse Previews" not in r["path"]]
    else:
        files = crawl(a.folder); print(f"{len(files)} file âm thanh", file=sys.stderr)
        with tempfile.TemporaryDirectory() as tmp, cf.ThreadPoolExecutor(a.workers) as ex:
            rows = list(ex.map(lambda x: measure(x, tmp), files))
        bad = [r["path"] for r in rows if "err" in r]
        if bad: print(f"{len(bad)} lỗi: {bad[:10]}", file=sys.stderr)
    cat = to_catalog(rows)
    json.dump(cat, open(os.path.join(HERE, "..", "assets", "catalog.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    open(os.path.join(HERE, "..", "references", "catalog.md"), "w", encoding="utf-8").write(to_markdown(cat))
    print(f"catalog: {len(cat)} SFX")
