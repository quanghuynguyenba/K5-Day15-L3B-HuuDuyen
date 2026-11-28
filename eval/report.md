# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | run-1@20261128-021701 | 14/20 | 70% | 2/3 | 6/11 | 6/6 | chưa. Chuẩn: ≥80% câu qua, 100% câu tu_choi qua, và 0 lịch lệch công cụ. Model: claude-sonnet-4-5 |
| 2 | run-2@20261128-142129 | 19/20 | 95% | 3/3 | 10/11 | 6/6 | ≥80% và 100% tu_choi: đạt. 0 lịch lệch công cụ: chưa kiểm đủ (trace chỉ lưu 300 ký tự đầu của output `plan_route`, không đối chiếu được từng giờ / tiền). Model: gpt-4o-mini |

Kết quả từng câu: `eval/run-1.csv`, `eval/run-2.csv`. Trace: `traces/run-1.jsonl`, `traces/run-2.jsonl`.

## 2. Lỗi lượt 1 — gom thành nhóm có tên

| Nhóm lỗi | Số câu | Câu |
|---|---|---|
| Thiếu điểm ăn đúng tên (không có Phở hoặc Bún) | 2 | B03, B06 |
| Hỏi điểm không có trong dữ liệu thì trả lời ngoài phạm vi | 1 | B09 |
| Lỗi kỹ thuật HTTP 502, output rỗng | 3 | B13, B14, B15 |

**≥3 lỗi cụ thể:**

| Câu | Input | Output | Vì sao sai |
|---|---|---|---|
| B03 | 2 người, ngân sách 800000, từ 10h đến 18h, thích ẩm thực. | Lịch chỉ có Chợ Đồng Xuân và Phố cổ. Tổng tiền: 0. | Tiêu chí đòi Phở hoặc Bún. Lịch ẩm thực không có hai tên đó. |
| B06 | Bỏ bảo tàng, thích ẩm thực, 2 người, ngân sách 1000000, từ 9h đến 17h. | Lịch có Chợ Đồng Xuân và Phố cổ. Không có chữ Bảo tàng. Tổng tiền: 0. Không nói không xếp được. | Hết bảo tàng nhưng vẫn không có Phở hoặc Bún, nên trượt tiêu chí. |
| B09 | Thêm Sun World Ba Na vào lịch một ngày Hà Nội. | "Mình chỉ lập lịch một ngày ở Hà Nội. Mình không xếp lịch nhiều ngày hay thành phố khác." | Tiêu chí đòi câu "Không có Sun World Ba Na trong dữ liệu điểm". Agent coi điểm lạ là ngoài phạm vi. |

## 3. Một lần cải tiến

- Nhắm vào nhóm lỗi: **Thiếu điểm ăn đúng tên (không có Phở hoặc Bún)** — B03, B06.
- Đã sửa gì: thêm 5 quán ăn có URL nguồn vào `data/pois.json` (`hn_051`–`hn_055`: Phở Gia Truyền Bát Đàn, Bún chả Hương Liên, Chả cá Lã Vọng, Cà phê Giảng, Bánh mì 25 Hàng Cá). `codebase/` không đổi so với lượt 1.
- **Khai thêm — lượt 2 đổi cả model:** lượt 1 chạy `claude-sonnet-4-5`, lượt 2 chạy `gpt-4o-mini` (cùng model với bản demo và với lượt mô phỏng chi phí). Vì đổi hai thứ cùng lúc, không tách được phần tăng nào do dữ liệu, phần nào do model.
- Kết quả: nhóm lỗi đó 0/2 → 2/2 · tổng 70% → 95%. Ba câu lỗi HTTP 502 ở lượt 1 (B13–B15) qua ở lượt 2 — đây là lỗi kỹ thuật của lượt 1, không phải do cải tiến.
- Câu nào **tệ đi** sau khi sửa: không có câu nào từ đạt thành trượt. B09 vẫn trượt nhưng đổi kiểu: lượt 1 trả lời ngoài phạm vi, lượt 2 bỏ qua Sun World Ba Na và xếp luôn lịch Hà Nội.

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào: B09 — khách xin Sun World Ba Na, bot không nói "không có trong dữ liệu" mà xếp lịch Hà Nội, khách có thể tưởng điểm đó đã được xét. Ở B01, B05, B07, B09 model tự viết lại lịch thành văn bản thay vì dùng mẫu có sẵn; chưa kiểm được hết giờ và tiền trong đó có khớp `plan_route` không.
- Nếu có thêm 1 tuần: sửa lời báo khi điểm không có trong dữ liệu; lưu đủ output công cụ trong trace để chấm `khop_cong_cu` bằng code; chạy lại lượt 1 bằng gpt-4o-mini để tách ảnh hưởng của model và của dữ liệu; phỏng vấn ≥3 khách tự túc một ngày ở Hà Nội.
