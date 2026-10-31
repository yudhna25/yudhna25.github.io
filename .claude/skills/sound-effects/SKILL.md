---
name: sound-effects
description: Chọn, tải và đặt sound effect (SFX) từ thư viện "BASIC SFX QUẠ HD" (~1.300 file — Mister Horse Free SFX, QUẠ BASIC meme, Anime SFX, SUSPEND ALERT, SFX Nhật Bản) cho video, motion graphics, TikTok/Reels, vlog, trailer, UI/web. Dùng skill này mỗi khi người dùng nhắc tới sound effect, SFX, âm thanh hiệu ứng, tiếng whoosh/swoosh/pop/click/boom/glitch/riser/ding, "thêm tiếng cho video", "chèn âm thanh chuyển cảnh", sound design, đồng bộ âm thanh với chuyển động, hoặc cần tiếng meme/hài/kinh dị/hồi hộp — kể cả khi họ không nói chữ "SFX". Có sẵn bảng thời lượng và điểm nhấn (peak) của từng file để căn khung hình chính xác, script tìm kiếm, tải về và tự mix lên video bằng ffmpeg.
---

# Sound Effects — thư viện BASIC SFX QUẠ HD

Skill này biến thư mục Drive "BASIC SFX QUẠ HD" thành một thư viện có thể tìm kiếm. File âm thanh
**không** nằm trong skill (quá nặng và nhiều file có bản quyền bên thứ ba); skill giữ một catalog có
Drive ID + số liệu phân tích, và script tải đúng file cần dùng khi cần.

Nguồn: https://drive.google.com/drive/folders/1L4WOlQINxD45bRTikaUmV6QZ362P41rh (công khai, ai có link đều xem được).

## Có gì trong skill

| File | Dùng khi |
|---|---|
| `references/categories.md` | Cần quyết định *loại* âm thanh cho một khoảnh khắc (bảng khoảnh khắc → danh mục, ghi chú bản quyền). Đọc trước khi chọn. |
| `references/catalog.md` | Cần xem danh sách file theo danh mục kèm thời lượng / peak. Lớn — dùng grep theo danh mục thay vì đọc hết. |
| `assets/catalog.json` | Dữ liệu máy đọc (script dùng). Trường: `id, path, collection, category, name, ext, dur, peak_t, onset_t, tail_t, attack, peak_db, rms_db, shape, tags`. |
| `scripts/find_sfx.py` | Tìm file theo từ khoá Việt/Anh, danh mục, thời lượng, shape. |
| `scripts/fetch_sfx.py` | Tải file về thư mục dự án (tuỳ chọn chuyển WAV 48k, cắt lặng, chỉnh gain). |
| `scripts/mix_sfx.py` | Đặt nhiều SFX lên video/stem theo cue sheet, căn peak đúng thời điểm, xuất kèm CSV cue. |

Script cần Python 3 và `ffmpeg`/`ffprobe`; tải file qua mạng từ `drive.usercontent.google.com`.
Đường dẫn script tính từ thư mục skill này (`<skill>/scripts/...`).

## Ý nghĩa các số liệu (vì sao quan trọng)

Một SFX hiếm khi "vang" ngay giây 0. Whoosh dâng lên rồi mới đập; boom có khoảng lặng nhỏ ở đầu.
Nếu đặt đầu file vào điểm cắt, tiếng sẽ bị trễ 3–15 frame và cảm giác "lệch". Vì vậy mỗi file đã
được đo sẵn:

- `peak_t` — giây có năng lượng lớn nhất = **điểm nhấn**. Căn điểm này vào frame cắt / va chạm / chữ chạm vị trí.
- `onset_t` — giây tiếng bắt đầu nghe được (bỏ qua lặng đầu file).
- `tail_t` — giây tiếng tắt hẳn (dưới ~-30 dB so với peak).
- `attack = peak_t - onset_t` — thời gian dâng.
- `shape` — `hit` (attack < 0.06s: nhấn tức thì), `swell` (attack ≥ 0.3s: dâng lên — whoosh, riser), `bed` (> 8s: làm nền/ambience/nhạc), `short` (còn lại).
- `rms_db` / `peak_db` — độ to trung bình / đỉnh. Dùng để cân mức giữa các file khác bộ (bộ meme thường to hơn Mister Horse nhiều).

Công thức đặt clip: `clip_start = thời_điểm_đích − peak_t` (theo giây; × fps để ra frame).

## Quy trình

1. **Hiểu khoảnh khắc.** Liệt kê các sự kiện cần tiếng: thời điểm (giây/frame), loại (chuyển cảnh,
   chữ bật, va chạm, reveal, UI, cảm xúc), sắc thái (sang trọng, công nghệ, hài, kinh dị). Hỏi
   người dùng nếu chưa rõ video dùng cho mục đích thương mại hay không — điều đó quyết định bộ nào được dùng.
2. **Chọn danh mục** bằng `references/categories.md`.
3. **Tìm file cụ thể:**
   ```bash
   python3 <skill>/scripts/find_sfx.py "whoosh" --max-dur 1.2 --shape swell
   python3 <skill>/scripts/find_sfx.py "" --category "Boom/Medium" --commercial
   python3 <skill>/scripts/find_sfx.py "hài" --collection Anime
   python3 <skill>/scripts/find_sfx.py --list-categories
   ```
   Chọn 1 phương án chính + 1–2 phương án dự phòng; với nhóm đánh số (`Swoosh 01 - 01…07`) các
   số là biến thể cùng họ — dùng luân phiên khi lặp lại cùng một hiệu ứng để tránh cảm giác máy móc.
4. **Giao kết quả** theo đúng nhu cầu:
   - Chỉ cần gợi ý → bảng: thời điểm · tên file · Drive ID · peak_t · vị trí đặt clip · gain gợi ý.
   - Cần file → `fetch_sfx.py <id...> --out ./sfx --wav` (thêm `--trim` nếu muốn clip gọn; khi trim, peak dịch sớm đi một đoạn bằng onset — script in ra số này).
   - Cần video hoàn chỉnh → viết `cues.json` rồi `mix_sfx.py cues.json --video in.mp4 --out out.mp4`.
     Script tự căn peak, giữ tiếng gốc, chống clip bằng limiter và xuất `out.mp4.cues.csv` để dựng lại trong NLE.
   - Web/UI → tải bản ngắn (`--trim`), chuyển sang MP3/OGG nhỏ nếu cần, gain khoảng −12 đến −18 dB, phát ở `onset` của tương tác.

## Nguyên tắc sound design (tóm tắt)

- **Căn peak, không căn đầu file.** Riêng riser/approach: căn `tail_t` (align `end`) vào khoảnh khắc reveal, rồi đặt một `hit`/`Bass` ngay tại đó.
- **Xếp lớp cho reveal:** riser (`Approach`) → hit (`Boom/Medium`) + sub (`Bass`) cùng frame → tail tự nhiên. 2–3 lớp là đủ; nhiều hơn thường bị đục.
- **Mức âm tham khảo** (so với thoại ở ~−12 dB đỉnh): UI/pop/click −18…−24 dB; whoosh chuyển cảnh −12…−18; impact −8…−12; ambience/drone −24…−30. File meme/QUẠ BASIC thường to hơn ~6–10 dB so với Mister Horse — dựa vào `rms_db` để cân.
- **Đừng lấp mọi chỗ.** Mỗi 1–2 giây một điểm nhấn là dày cho video thông tin; cho TikTok hài có thể dày hơn. Khoảng lặng trước một hit làm hit mạnh hơn.
- **Lặp lại = cùng họ, khác biến thể.** Dùng `Pop 01 - 01`, `- 02`, `- 03` cho ba chữ bật liên tiếp.
- **Hợp tông:** video sang trọng/BĐS → Mister Horse (Swoosh, Slide, Boom/Soft, Ambience); công nghệ/HUD → Glitch, Beep, Bleep; hài/reaction → Anime SFX, QUẠ BASIC; kinh dị/drama → SUSPEND ALERT, Drone, Rumble.
- **Frame:** 30 fps = 33 ms/frame, 25 fps = 40 ms, 24 fps = 41.7 ms. Lệch > 2 frame là tai người nhận ra.

## Bản quyền

Mister Horse Free SFX là bộ miễn phí dành cho creator (xem license của Mister Horse trước khi dùng
thương mại). Các bộ QUẠ BASIC / Anime SFX / SUSPEND ALERT chứa nhiều đoạn trích từ game, phim, meme,
Epidemic Sound và nhạc có bản quyền. Khi người dùng làm video thương mại, quảng cáo hoặc kênh kiếm
tiền, dùng `--commercial` và nói rõ lý do; vẫn có thể gợi ý file meme nhưng phải kèm cảnh báo.

## Khi có sự cố

- Tải về trang HTML / lỗi 403: chủ Drive có thể đã đổi quyền hoặc xoá file — chọn phương án dự phòng, báo người dùng.
- Không tìm thấy kết quả: thử từ khoá tiếng Anh theo tên thư mục (whoosh, pop, boom, click, glitch, slide, transition…) hoặc `--list-categories`.
- Thư viện trên Drive thay đổi: chạy lại `scripts/build_catalog.py` để quét và đo lại.
