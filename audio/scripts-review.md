# Duyệt kịch bản thuyết minh — `audio/demo-scripts.json`

Soạn tự động 28/11/2026 (13 điểm cập nhật giá/giờ — hn_022, 024, 025, 031, 032, 033, 038, 041, 042, 044, 045, 048, 049 — đã soạn lại theo dữ liệu mới) bằng prompt thuyết minh của app (`agent/tools.py` · `narrate_system`), nội dung chỉ lấy từ `data/pois.json`. **Trạng thái 28/11/2026: cả 275 bản đã được nhóm duyệt (`approved: true`) và đã tạo mp3** (`audio/hn_<id>_<lang>.mp3` + metadata `.json`, giọng edge-tts). Sửa lời một bản: chỉnh `text`, rồi chạy lại:

```powershell
python -m services.prepare_audio --scripts audio/demo-scripts.json
```

Chỉ bản `approved: true` được kiểm tra và tạo mp3 — nên duyệt các điểm demo trước, phần còn lại để sau (app vẫn tự tạo thuyết minh lúc chạy cho điểm chưa có bản duyệt).

**Code đã tự kiểm cả 275 bản:** đúng ngôn ngữ · độ dài ~60–90 giây · không lọt ghi chú nội bộ · mọi số tiền đều có trong dữ liệu. Tự kiểm KHÔNG thay việc đọc: vẫn cần xem phiên âm tên riêng, thông tin gán đúng chỗ, câu khuyên thêm không có nguồn.

## Kết quả tự kiểm

| | Số bản |
|---|---|
| Sạch | 192 |
| Chỉ không nhắc tên tiếng Việt gốc (chấp nhận được với audio tiếng nước ngoài) | 83 |
| **Lỗi cần sửa** | **0** |

## Gợi ý thứ tự duyệt

1. Điểm hay ra trong lịch demo: hn_001 Văn Miếu, hn_002 Hồ Hoàn Kiếm, hn_004 Hoàng thành, hn_005 Hỏa Lò (ko, vi).
2. Các điểm nội thành còn lại (vi, en).
3. ja / zh và ngoại thành.
