# Weather and narration

## Thời tiết

`WEATHER_MODE=real` (mặc định) gọi Open-Meteo, độc lập với `USE_MOCK` của agent. `WEATHER_MODE=mock` trả dữ liệu minh họa và luôn gắn `mock: true`, `source: mock`.

- Theo giờ Hà Nội (UTC+7), xác suất mưa và nhiệt độ mỗi giờ; ngưỡng mưa 60%.
- `status`: `ok`, `partial`, `mock`, `unavailable`. Không có dự báo thì `is_rainy` và `temp_max` là `null`; không diễn giải thành không mưa/0°C.
- Phạm vi từ hôm nay đến 15 ngày tiếp theo; timeout 8 giây, cache kết quả 5 phút. Mất mạng hoặc ngày quá xa không tự chuyển sang mock.
- Nguồn/đơn vị: [Open-Meteo docs](https://open-meteo.com/en/docs). Dự báo có thể thay đổi; không phải cam kết về thời tiết.

## TTS năm ngôn ngữ

`vi`, `en`, `ko`, `ja`, `zh` dùng giọng tương ứng trong `tts.VOICES`. Thử edge-tts trước (timeout), sau đó gTTS. Không tự đổi ngôn ngữ không hợp lệ sang tiếng Anh. TTS đọc văn bản được cung cấp; dịch/viết lời thuyết minh thuộc LLM hoặc kịch bản đã duyệt.

- File được ghi tạm, kiểm tra MP3 rồi thay thế atomically. Cache kiểm tra hash nội dung/audio và ngôn ngữ; URL có version để tránh phát audio cũ khi đổi lời.
- Lỗi cả hai dịch vụ: trả nội dung chữ và warning, không trả URL file hỏng. API có metadata `source`, `mock`, `tts_status`, `tts_provider`.
- Chưa có LLM: không đọc nội dung tiếng Việt bằng giọng Hàn/Nhật. Audio đã duyệt từ trước vẫn phát được khi LLM hoặc mạng không sẵn sàng.
- Tài liệu thư viện: [edge-tts](https://github.com/rany2/edge-tts), [gTTS](https://gtts.readthedocs.io/en/stable/module.html).

## Chuẩn bị audio demo

Hiện `data/pois.json` có 5 POI mẫu, mô tả `MẪU/SAMPLE` và nguồn `TODO`. **Chưa tạo audio demo địa điểm từ các placeholder này.**

1. Sao chép `audio/demo-scripts.example.json` thành `audio/demo-scripts.json`.
2. Điền `text` đúng ngôn ngữ (mục tiêu 60–90 giây), `source` là URL căn cứ. Kiểm tra nội dung rồi đặt `approved: true`. Mỗi POI/ngôn ngữ một dòng; thêm dòng cho điểm khác.
3. Kiểm tra trước, chưa gọi TTS:

```powershell
python -m services.prepare_audio --scripts audio/demo-scripts.json --check
```

4. Tạo MP3 và metadata phục vụ cả khi agent mock:

```powershell
python -m services.prepare_audio --scripts audio/demo-scripts.json
```

API ưu tiên bộ audio đã duyệt trước khi gọi LLM. Không tự nhận file MP3 không có metadata khớp là nội dung đã duyệt. Nếu dữ liệu RAG đổi, hãy duyệt/chạy lại bộ script để cập nhật context hash.

Kiểm tra dữ liệu gốc: `python -m services.prepare_audio --check` (trả exit code 1 nếu còn thiếu).
