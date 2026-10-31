#!/usr/bin/env python3
"""Đặt SFX lên timeline theo cue sheet, căn điểm nhấn (peak) đúng thời điểm, rồi mix.

cues.json:
[
  {"at": 1.20, "sfx": "<id|tên>", "gain_db": -8},             # peak rơi đúng 1.20s
  {"at": 3.00, "sfx": "<id>", "align": "onset"},               # bắt đầu tiếng tại 3.00s
  {"at": 5.50, "sfx": "<id>", "align": "end", "gain_db": -14}, # riser kết thúc tại 5.50s
  {"at": 0.00, "sfx": "<id>", "duration": 10, "fade": 1.5}     # nền: cắt 10s, fade in/out 1.5s
]
align: peak (mặc định) | onset | end | start (đầu file thô)

  python3 mix_sfx.py cues.json --video in.mp4 --out out.mp4 [--sfx-level -3] [--duck 4]
  python3 mix_sfx.py cues.json --duration 30 --out sfx_stem.wav        # chỉ xuất stem SFX
Luôn xuất thêm <out>.cues.csv (thời điểm đặt clip) để dựng lại trong Premiere/Resolve.
"""
import argparse, csv, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfxlib

ap = argparse.ArgumentParser()
ap.add_argument("cues")
ap.add_argument("--video", help="video gốc; giữ tiếng gốc và trộn SFX lên")
ap.add_argument("--duration", type=float, help="độ dài stem khi không có video")
ap.add_argument("--out", required=True)
ap.add_argument("--sfx-level", type=float, default=0.0, help="dB cho cả bus SFX")
ap.add_argument("--duck", type=float, default=0.0, help="giảm tiếng gốc N dB khi trộn (0 = giữ nguyên)")
a = ap.parse_args()

cues = json.load(open(a.cues, encoding="utf-8"))
dur = a.duration
if a.video:
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                "default=nw=1:nk=1", a.video], capture_output=True, text=True).stdout.strip())
if not dur:
    sys.exit("Cần --video hoặc --duration")

inputs, filters, labels, rows = [], [], [], []
base = 1 if a.video else 0
for i, c in enumerate(cues):
    e = sfxlib.find(c["sfx"])
    src = sfxlib.download(e)
    align = c.get("align", "peak")
    anchor = {"peak": e.get("peak_t", 0), "onset": e.get("onset_t", 0),
              "end": e.get("tail_t", e["dur"]), "start": 0}[align]
    start = c["at"] - anchor          # thời điểm đặt đầu file trên timeline
    skip = max(0.0, -start)           # nếu âm: cắt bớt đầu file
    start = max(0.0, start)
    inputs += ["-i", src]
    n = base + i
    chain = f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo"
    if skip:
        chain += f",atrim=start={skip:.3f},asetpts=PTS-STARTPTS"
    if c.get("duration"):
        chain += f",atrim=duration={c['duration']:.3f}"
    if c.get("fade"):
        fd = c["fade"]; ln = c.get("duration") or (e["dur"] - skip)
        chain += f",afade=t=in:d={fd},afade=t=out:st={max(0, ln - fd):.3f}:d={fd}"
    chain += f",volume={c.get('gain_db', 0)}dB,adelay={int(start * 1000)}:all=1[s{i}]"
    filters.append(chain); labels.append(f"[s{i}]")
    rows.append([f"{start:.3f}", f"{c['at']:.3f}", align, e["path"], e["id"], c.get("gain_db", 0), f"{skip:.3f}"])

mix = "".join(labels) + f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,volume={a.sfx_level}dB"
if a.video:
    filters.append(mix + "[sfx]")
    filters.append(f"[0:a]volume={-a.duck}dB[orig]")
    filters.append("[orig][sfx]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[aout]")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.video] + inputs + ["-filter_complex", ";".join(filters),
           "-map", "0:v?", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-t", f"{dur:.3f}", a.out]
    has_audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                "-of", "csv=p=0", a.video], capture_output=True, text=True).stdout.strip()
    if not has_audio:  # video câm: dùng stem SFX làm tiếng
        filters = filters[:-3] + [mix + ",alimiter=limit=0.95[aout]"]
        cmd[cmd.index("-filter_complex") + 1] = ";".join(filters)
else:
    filters.append(mix + ",alimiter=limit=0.95,apad[aout]")
    cmd = ["ffmpeg", "-y", "-v", "error"] + inputs + ["-filter_complex", ";".join(filters), "-map", "[aout]",
           "-t", f"{dur:.3f}", "-ar", "48000", "-c:a", "pcm_s24le" if a.out.endswith(".wav") else "aac", a.out]
sfxlib.run(cmd)
with open(a.out + ".cues.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["clip_start_s", "anchor_at_s", "align", "path", "drive_id", "gain_db", "trimmed_head_s"])
    w.writerows(rows)
print(f"Đã xuất {a.out} ({len(cues)} SFX) + {a.out}.cues.csv")
