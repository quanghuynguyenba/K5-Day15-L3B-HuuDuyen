# Hanoi Travel AI — giao diện

## Xem giao diện

```powershell
cd frontend
npm install
npm run dev
```

Mở địa chỉ Vite in ra (mặc định http://localhost:5173).

- **Phiên mới:** màn hình mặc định, có lời chào và gợi ý yêu cầu.
- **Hành trình mẫu:** nút trên thanh công cụ hoặc trong sidebar. Hiển thị 5 điểm, tổng chi minh họa 850.000đ, tuyến nối mẫu và thông tin Văn Miếu. Không cần backend hoặc API key. Bản đồ nền vẫn cần mạng.
- **Về phiên mới / Cuộc trò chuyện mới:** thoát xem trước và tạo phiên mới.
- Gửi tin nhắn trong chế độ xem mẫu sẽ chuyển sang phiên API mới. Nội dung mẫu không gửi vào backend.

Dữ liệu xem trước trong `src/preview.js` chỉ minh họa thiết kế, không phải dữ liệu du lịch đã kiểm chứng. Nút nghe ở chế độ mẫu hiển thị thông báo; không giả lập audio thật.

## Kết nối backend

Từ thư mục gốc repo, chạy ở terminal khác:

```powershell
python -m uvicorn server:app --reload --port 8000
```

`src/api.js` giữ các endpoint hiện có; Vite proxy `/api` và `/audio` sang cổng 8000. Chế độ API sử dụng dữ liệu backend và các API thuyết minh, thời tiết, tổng kết như trước.

Sidebar hiện cung cấp phiên mới và chế độ xem mẫu; quản lý nhiều phiên/lưu lịch sử chưa nằm trong bước dựng khung này.

## Trải nghiệm chat

- Bấm thẻ gợi ý để điền yêu cầu vào ô nhập và chỉnh sửa trước khi gửi.
- Enter gửi tin, Shift + Enter xuống dòng; ô nhập tự giãn đến 160px rồi cuộn bên trong.
- Trong lúc chờ, nút gửi bị khóa nhưng vẫn có thể soạn tin tiếp theo. Sau 12 giây có thông báo đang xử lý lâu hơn thường lệ.
- Lỗi hiển thị riêng với nút thử lại. Thử lại giữ nguyên ngày của yêu cầu và không thêm trùng tin người dùng trên giao diện. Backend hiện chưa có cơ chế chống lặp request, nên lỗi mạng sau khi máy chủ đã xử lý vẫn có thể dẫn đến xử lý lại khi thử lại.
- Tự cuộn khi đang ở gần cuối cuộc trò chuyện. Nếu đang đọc phía trên, giữ vị trí và hiện nút về tin mới nhất.
- Phản hồi đến sau khi chuyển phiên/xem mẫu không cập nhật nhầm màn hình mới.

## Kiểm tra build

```powershell
npm run build
```

Giao diện dựa trên hai file HTML desktop trong `stitch_hanoi_travel_ai_interface.zip`, dùng font Inter, xanh dương `#0369B2`, cyan nhạt `#E3F8FC`, nền `#FAFCFB` và Leaflet thay cho SVG bản đồ minh họa. Trên màn hình nhỏ, chuyển giữa Trò chuyện và Bản đồ bằng thanh tab.

## Theme và Material UI

- `src/theme.js`: bảng màu Stitch dùng chung cho Material UI và CSS; chỉnh token tại đây khi đổi thiết kế.
- `src/main.jsx`: `ThemeProvider`, `CssBaseline` và thứ tự style qua `StyledEngineProvider`.
- `src/components/Header.jsx`: header, thời tiết và chọn ngôn ngữ bằng Material UI Chip/ToggleButtonGroup.
- Các nút dùng Material UI Button; ô chat dùng InputBase multiline; icon dùng `@mui/icons-material`.
- `src/styles.css` quản lý bố cục responsive và thành phần Leaflet; màu tham chiếu biến CSS do theme cấp.
