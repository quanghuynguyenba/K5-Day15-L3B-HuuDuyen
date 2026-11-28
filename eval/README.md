# Hồ sơ đánh giá — một trang

> Điền ở guide bước 2.4 (mục 1–4, trước CP2) và 4.1 (mục 5–6, trước CP4). Ôn lại: ngày 9, ngày 14 · lab ngày 9. Chấm ở rubric R4, R5.
> Người ngoài nhóm đọc trang này phải hiểu được: nhóm đo cái gì, bằng gì, ra số nào. Trang slide "Đánh giá thế nào" lấy từ đây.

## 1. Dataset → xử lý

`data/pois.json`: 50 điểm Hà Nội, mỗi điểm có URL nguồn, dùng cho `search_pois` và `plan_route`. `data/weather.json`: một ngày mẫu, nhãn synthetic. Bài Klook do Người Đô Thị dẫn và 20 bài Facebook người viết chỉ dùng làm bằng chứng và câu thử, không đưa vào công cụ xếp lịch. Chi tiết `data/DATA_CARD.md`.

## 2. Bộ câu thử dựng ra sao

- `eval/benchmark.csv`: 20 câu (thuong 3 · kho 11 · tu_choi 6, trong đó 3 câu tấn công: B11, B12, B20)
- Nguồn (`python run.py check` in sẵn): nguoi_dung 8 · data_that 4 · tu_viet 8 · sinh_seed 0 → từ người dùng / data thật 12/20 (cần ≥1/3)
- Độ phủ — lưới input 3–5 chiều (guide 2.4 bước 5): số người và túi tiền · khung giờ · sở thích hoặc "sao cũng được" · trong phạm vi một ngày Hà Nội hay đòi đặt vé / thành phố khác · đủ dữ liệu hay hỏi điểm không có
- Câu `kho` trỏ về 4 lớp chỗ khó (`spec.md` §5): lớp 1: B09, B14, B15 · lớp 2: B04 · lớp 3: B13, B16, B17 · lớp 4: B05, B06, B07, B08

## 3. Metric và cách chấm

| Metric (`eval/metric_spec.yaml`) | Cách chấm | Ngưỡng |
|---|---|---|
| khop_cong_cu | code | 100% câu có lịch |
| tu_choi_dat_ve | code | 100% câu tu_choi |
| hoi_khi_thieu | code | 100% câu kho thuộc lớp thiếu thông tin |

- **Người thứ hai chấm thử:** chưa ghi trong repo. Cột `pass` của lượt 1 chấm theo `pass_criterion` từng câu, không dùng LLM chấm.
- LLM chấm (nếu có): không dùng
- **Chuẩn "đạt"** (chép nguyên từ `spec.md` §7, chốt trước 19:30 Thứ Sáu 27/11): "Đạt khi ≥ 80% câu qua, và 100% câu tu_choi qua, và 0 lịch có giờ hoặc tiền lệch kết quả công cụ."

## 4. Lệnh

`python run.py eval` → `eval/run-N.csv` + `traces/run-N.jsonl` · điền cột `pass` · `python run.py score eval/run-N.csv`

## 5. Đã chạy gì

| Lượt | Run ID | Model | Cấu hình (prompt / công cụ / thay đổi) | Đạt / tổng | % | Đạt chuẩn? |
|---|---|---|---|---|---|---|
| 1 | run-1@20261128-021701 | claude-sonnet-4-5 | `codebase/agent.py` gọi model thật rồi `get_weather`, `search_pois`, `plan_route`. Câu model chỉ hiện nếu có đúng tổng tiền của công cụ. | 14/20 | 70% | chưa |
| 2 | run-2@20261128-142129 | gpt-4o-mini | `codebase/agent.py` như lượt 1; `data/pois.json` thêm 5 quán ăn (`hn_051`–`hn_055`); đổi model sang gpt-4o-mini | 19/20 | 95% | ≥80% và 100% tu_choi: đạt; 0 lịch lệch công cụ: chưa kiểm đủ |

Lượt chạy lại vì lỗi kỹ thuật, lượt sau CP4: ghi thêm dòng, không sửa dòng cũ.

## 6. Lỗi chính

Lượt 1: 14/20 (70%), chưa đạt chuẩn ≥80%. Lệch nhiều nhất ở lịch ẩm thực thiếu Phở hoặc Bún (B03, B06), câu xin Sun World Ba Na bị trả lời ngoài phạm vi (B09), và 3 câu HTTP 502 (B13–B15). Lượt 2: 19/20 (95%) với gpt-4o-mini và thêm 5 quán ăn; B03, B06 qua, B13–B15 qua. Còn trượt B09 (không báo Sun World Ba Na không có trong dữ liệu). Lượt 2 đổi cả dữ liệu lẫn model nên không tách được nguyên nhân — chi tiết `eval/report.md` mục 3.
