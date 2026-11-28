# Tóm tắt mô phỏng simulate-2@20261128-142245

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| dung_it | 34 | 1 | 1634 | 450 | 3.0 | 2.1 |
| dung_vua | 14 | 2 | 2765 | 789 | 5.4 | 3.0 |
| dung_nhieu | 2 | 3 | 4487 | 1203 | 8.5 | 6.0 |

Tỉ lệ đạt dùng để tính: 19/20 (95%) — lượt run-2@20261128-142129

- Tự chọn: lượt run-N mới nhất đã chấm xong, chạy bằng đúng model đang đo (run-2.csv). Muốn dùng lượt khác (vd lượt 2): thêm `--rate-from eval/run-2.csv`.

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (40 người) | Chi phí / tháng — cơ sở (120 người) | Chi phí / tháng — cao (400 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini-3.1-flash-lite (vào 0.25 · ra 1.5 $/1M) | $0.0014 | $0.0015 | $0.0011 | $0.1178 | $0.3534 | $1.18 | $0.0029 |
| gemini-4-hydrogen (vào 1.5 · ra 7.5 $/1M) | $0.0074 | $0.0078 | $0.0057 | $0.6334 | $1.90 | $6.33 | $0.0158 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (1.4) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: gpt-4o-mini. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
