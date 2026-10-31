#!/usr/bin/env python3
"""Tải SFX từ Google Drive về thư mục dự án.
  python3 fetch_sfx.py <id|đường dẫn|tên> [...] --out ./sfx [--wav] [--trim] [--gain -6]
--wav   : chuyển sang WAV 48 kHz 24-bit (chuẩn Premiere/AE/Resolve)
--trim  : cắt khoảng lặng đầu (onset) và đuôi (tail) theo phân tích sẵn
--gain  : tăng/giảm dB khi xuất
"""
import argparse, os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfxlib

ap = argparse.ArgumentParser()
ap.add_argument("refs", nargs="+")
ap.add_argument("--out", default="./sfx")
ap.add_argument("--wav", action="store_true")
ap.add_argument("--trim", action="store_true")
ap.add_argument("--gain", type=float, default=0.0)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
for ref in a.refs:
    e = sfxlib.find(ref)
    src = sfxlib.download(e)
    stem = f"{sfxlib.safe_name(e).rsplit('.', 1)[0]}"
    if not (a.wav or a.trim or a.gain):
        dst = os.path.join(a.out, stem + "." + e["ext"])
        shutil.copyfile(src, dst)
    else:
        dst = os.path.join(a.out, stem + (".wav" if a.wav or e["ext"] in ("mp4", "webm", "aac") else "." + e["ext"]))
        cmd = ["ffmpeg", "-y", "-v", "error"]
        if a.trim:
            st = max(0.0, e.get("onset_t", 0) - 0.01)
            cmd += ["-ss", f"{st:.3f}", "-to", f"{min(e['dur'], e.get('tail_t', e['dur']) + 0.05):.3f}"]
        cmd += ["-i", src, "-vn"]
        if a.gain:
            cmd += ["-af", f"volume={a.gain}dB"]
        if dst.endswith(".wav"):
            cmd += ["-ar", "48000", "-c:a", "pcm_s24le"]
        sfxlib.run(cmd + [dst])
    print(f"{dst}\t(peak@{e.get('peak_t', 0):.2f}s, dur {e['dur']:.2f}s)" + ("  [đã trim: peak dịch sớm hơn " + f"{max(0, e.get('onset_t',0)-0.01):.2f}s]" if a.trim else ""))
