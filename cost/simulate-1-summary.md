# Tóm tắt mô phỏng simulate-1@20261128-024019

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| dung_it | 19 | 1 | 1107 | 443 | 2.0 | 1.7 |
| dung_vua | 11 | 3 | 2942 | 1112 | 6.0 | 3.3 |
| dung_nhieu | 9 | 5 | 5667 | 2190 | 10.0 | 8.0 |

Tỉ lệ đạt dùng để tính: 14/20 (70%) — lượt run-1@20261128-021701

- Tự chọn: lượt run-N mới nhất đã chấm xong, chạy bằng đúng model đang đo (run-1.csv). Muốn dùng lượt khác (vd lượt 2): thêm `--rate-from eval/run-2.csv`.

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (300 người) | Chi phí / tháng — cơ sở (700 người) | Chi phí / tháng — cao (1.000 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini-3.1-flash-lite (vào 0.25 · ra 1.5 $/1M) | $0.0022 | $0.0032 | $0.0013 | $8.37 | $19.53 | $27.90 | $0.0279 |
| gemini-4-hydrogen (vào 1.5 · ra 7.5 $/1M) | $0.0118 | $0.0168 | $0.0068 | $44.38 | $103.55 | $147.93 | $0.1479 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (2.5) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: claude-sonnet-4-5. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 11/50.
