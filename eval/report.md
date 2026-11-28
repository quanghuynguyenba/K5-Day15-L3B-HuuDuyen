# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | run-1@20261128-021701 | 14/20 | 70% | 2/3 | 6/11 | 6/6 | chưa. Chuẩn: ≥80% câu qua, 100% câu tu_choi qua, và 0 lịch lệch công cụ. Model: claude-sonnet-4-5 |
| 2 | chưa chạy | | | | | | |

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

- Nhắm vào nhóm lỗi: chưa chọn — lượt 2 làm sau CP3, trước CP4
- Đã sửa gì (có thể vài thay đổi cùng nhắm nhóm lỗi đó): chưa
- Kết quả: nhóm lỗi đó __/__ → __/__ · tổng 70% → __%
- Câu nào **tệ đi** sau khi sửa: chưa chạy lượt 2

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào: B03 và B06 ra lịch ẩm thực không có Phở hoặc Bún, nên khách thích ăn không dùng được lịch. B09 không nói "không có trong dữ liệu" khi được xin Sun World Ba Na. B13–B15 không có output vì HTTP 502.
- Nếu có thêm 1 tuần: sửa lời từ chối khi điểm không có trong dữ liệu, rồi phỏng vấn ≥3 khách tự túc một ngày ở Hà Nội. Lượt 2 chưa chạy.
