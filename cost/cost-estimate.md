# Chi phí khi dùng thật

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Ôn lại: ngày 13, ngày 1, ngày 14 · lab ngày 13, lab ngày 14. Chấm ở rubric R6.
> Số **không điền tay**: điền `cost/personas.yaml` → `python run.py simulate` → chép bảng trong `cost/simulate-N-summary.md` vào đây.
> Lúc build dùng gói miễn phí vẫn tính theo **giá gói trả phí** — đây là chi phí cho lúc đưa vào dùng thật.

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): 3 kiểu — dung_it 60% · 1 phiên/tháng · 1 lượt; dung_vua 30% · 2 phiên · 2 lượt; dung_nhieu 10% · 4 phiên · 3 lượt. Nguồn: canvas (ít / vừa / nhiều) — số lần *(tự ước tính)*, chưa phỏng vấn, chưa khảo sát.
- **Số người dùng thật** 3 kịch bản: thấp 40 · cơ sở 120 · cao 400 người / tháng. Nguồn: *(tự ước tính)* — chưa có số khách tự túc một ngày ở Hà Nội; không dùng sĩ số lớp.
- **Giá** 3 model (từ `further-reading/model-prices.md`, BTC xem 25/11/2026): gpt-4o-mini 0,15 / 0,60 $/1M (https://developers.openai.com/api/docs/pricing) · gemini-3.1-flash-lite 0,25 / 1,50 · gemini-4-hydrogen 1,50 / 7,50 (https://ai.google.dev/gemini-api/docs/pricing)
- **Tỉ lệ đạt** dùng để tính: 19/20 (95%) — lượt `run-2@20261128-142129` (lượt 2, cùng model gpt-4o-mini)
- Đo token trên model **gpt-4o-mini** (model thật của bản chạy thử), tính giá gpt-4o-mini, gemini-3.1-flash-lite và gemini-4-hydrogen

## 2. Kết quả mô phỏng

Lượt mô phỏng: `cost/simulate-2.csv` · run ID `simulate-2@20261128-142245` · 50 phiên · seed 42 · 0 phiên lỗi

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| dung_it | 34 | 1 | 1634 | 450 | 3.0 | 2.1 |
| dung_vua | 14 | 2 | 2765 | 789 | 5.4 | 3.0 |
| dung_nhieu | 2 | 3 | 4487 | 1203 | 8.5 | 6.0 |

| Model | Chi phí / phiên | Chi phí / task thành công | / tháng — thấp (40) | / tháng — cơ sở (120) | / tháng — cao (400) | / người / tháng (cơ sở) |
|---|---|---|---|---|---|---|
| **gpt-4o-mini** (model thật) | $0.00065 | **$0.00069** | $0.056 | $0.168 | $0.56 | $0.0014 |
| gemini-3.1-flash-lite (rẻ) | $0.0014 | $0.0015 | $0.118 | $0.353 | $1.18 | $0.0029 |
| gemini-4-hydrogen (mạnh) | $0.0074 | $0.0078 | $0.633 | $1.90 | $6.33 | $0.0158 |

Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt (95%) — **không coi như đạt 100%**.

- Hai hàng Gemini chép từ `cost/simulate-2-summary.md` (do `python run.py simulate` sinh ra).
- Hàng gpt-4o-mini: `simulate-2` chạy khi `personas.yaml` chưa có giá gpt-4o-mini. Đã thêm giá (bảng trên) rồi tính lại bằng chính hàm `cost.simulate.summarize` trên `cost/simulate-2.csv` — không chạy lại phiên nào: `python cost/resummarize.py`. Hai hàng Gemini tính lại khớp đúng summary gốc.
- Token đo trên gpt-4o-mini; hàng Gemini là "đo trên gpt-4o-mini, tính giá Gemini" — bộ tách token khác nên số token thật có thể lệch.

## 3. So với impact

- Impact / người / tháng (`spec.md` §2): *(tự ước tính)* 90 phút tự gom bản đồ, blog và group cho một ngày.
- Chi phí / người / tháng (cơ sở, model gpt-4o-mini): $0.0014 (chỉ tiền model).
- Chưa tính: bản đồ TomTom (cache sẵn, gọi thêm khi có cặp điểm mới), máy chủ, giờ công người kiểm dữ liệu giờ / giá.
- **Kết luận một dòng — đáng làm không:** tiền model không phải rào cản (dưới $0.01 / người / tháng ở cả 3 model); điều chưa chắc là impact 90 phút và số người dùng — cả hai đều *(tự ước tính)*, cần phỏng vấn trước khi kết luận đáng làm.

## 4. *(Muốn sâu hơn, không bắt buộc)*

- Bảng độ nhạy: model rẻ hơn · cache · cắt ngữ cảnh · giới hạn bước — mỗi cần gạt đổi chi phí bao nhiêu
- Chi phí ngoài model: hosting, lưu trữ, giờ công người duyệt
- Quy mô nào thì bài toán còn đáng làm
