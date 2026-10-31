#!/usr/bin/env python3
"""Tìm SFX trong thư viện. Ví dụ:
  python3 find_sfx.py "chuyển cảnh" --max-dur 1.5
  python3 find_sfx.py boom --category "Boom/Strong" --commercial
  python3 find_sfx.py "" --category Pop --limit 50 --json
Cột: id  thời lượng  peak@(giây điểm nhấn)  shape  rms  path
shape: hit (nhấn ngay) | swell (dâng lên rồi nhấn) | bed (dài, làm nền) | short
"""
import argparse, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfxlib

ap = argparse.ArgumentParser()
ap.add_argument("query", nargs="?", default="", help="từ khoá Việt/Anh, vd 'whoosh', 'hài', 'kinh dị'")
ap.add_argument("--category", help="lọc theo thư mục, vd Transition, Glitch/Buzzing, Boom/Soft")
ap.add_argument("--collection", help="Mister Horse | QUẠ BASIC | Anime | SUSPEND | NHẬT BẢN")
ap.add_argument("--min-dur", type=float)
ap.add_argument("--max-dur", type=float)
ap.add_argument("--shape", choices=["hit", "swell", "bed", "short"])
ap.add_argument("--commercial", action="store_true", help="chỉ Mister Horse (an toàn bản quyền hơn)")
ap.add_argument("--limit", type=int, default=20)
ap.add_argument("--json", action="store_true")
ap.add_argument("--list-categories", action="store_true")
a = ap.parse_args()

if a.list_categories:
    from collections import Counter
    c = Counter((e["collection"], e["category"]) for e in sfxlib.load_catalog())
    for (col, cat), n in sorted(c.items()):
        print(f"{n:4d}  {col} / {cat or '-'}")
    sys.exit()

res = sfxlib.search(a.query, a.category, a.collection, a.min_dur, a.max_dur, a.shape, a.commercial, a.limit)
if a.json:
    print(json.dumps(res, ensure_ascii=False, indent=1))
else:
    if not res:
        print("Không có kết quả. Thử từ khoá tiếng Anh (whoosh, pop, boom, click, glitch...) hoặc --list-categories.")
    for e in res:
        print(sfxlib.fmt(e))
