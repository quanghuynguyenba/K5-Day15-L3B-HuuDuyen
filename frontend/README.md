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
- **Về cuộc trò chuyện:** thoát xem trước và trở lại phiên đang chọn. **Cuộc trò chuyện mới** tạo phiên độc lập.
- Gửi tin nhắn trong chế độ xem mẫu sẽ chuyển sang phiên API mới. Nội dung mẫu không gửi vào backend.

Dữ liệu xem trước trong `src/preview.js` chỉ minh họa thiết kế, không phải dữ liệu du lịch đã kiểm chứng. Nút nghe ở chế độ mẫu hiển thị thông báo; không giả lập audio thật.

## Kết nối backend

Từ thư mục gốc repo, chạy ở terminal khác:

```powershell
python -m uvicorn server:app --reload --port 8000
```

`src/api.js` giữ các endpoint hiện có; Vite proxy `/api` và `/audio` sang cổng 8000. Chế độ API sử dụng dữ liệu backend và các API thuyết minh, thời tiết, tổng kết như trước.

Sidebar quản lý nhiều phiên trong bộ nhớ của trang. Mỗi phiên có `session_id`, tin nhắn, lịch trình, bản nháp, ngày đi, ngôn ngữ, trạng thái tải/lỗi và điểm đang chọn riêng. Chuyển phiên không xóa phiên cũ, phản hồi nền được cập nhật đúng phiên gửi. Reload/đóng trang sẽ mất danh sách phiên; không dùng localStorage hoặc lưu lịch sử lâu dài.

## Popup, audio và responsive

- Popup gọi `/api/pois/{id}`, có skeleton, thông báo lỗi, tải lại, mô tả, tag, giờ mở cửa, giá/người, thời gian tham quan, giờ đến và nguồn nếu có URL hợp lệ. Phần đầu dùng minh họa icon khi dữ liệu chưa có ảnh địa điểm.
- API có giới hạn chờ 60 giây để không bị loading vô hạn.
- Audio dùng `/api/narrate`: trình phát gốc hỗ trợ phát/tạm dừng, tua và thời lượng. Có báo đang tải, hướng dẫn khi bị chặn tự phát, thử lại khi lỗi và nội dung chữ dự phòng.
- Desktop trên 1100px: sidebar cố định có thể thu gọn, map và chat cạnh nhau.
- Tablet 801–1100px: sidebar drawer qua nút trên header; map/chat cạnh nhau.
- Mobile đến 800px: drawer, tab Trò chuyện/Bản đồ và bottom sheet địa điểm. Sheet có nút đóng/Escape; camera dịch vị trí marker lên trên sheet; ô nhập hỗ trợ safe area và font 16px.

## Trải nghiệm chat

- Bấm thẻ gợi ý để điền yêu cầu vào ô nhập và chỉnh sửa trước khi gửi.
- Enter gửi tin, Shift + Enter xuống dòng; ô nhập tự giãn đến 160px rồi cuộn bên trong.
- Trong lúc chờ, nút gửi bị khóa nhưng vẫn có thể soạn tin tiếp theo. Sau 12 giây có thông báo đang xử lý lâu hơn thường lệ.
- Lỗi hiển thị riêng với nút thử lại. Thử lại giữ nguyên ngày của yêu cầu và không thêm trùng tin người dùng trên giao diện. Backend hiện chưa có cơ chế chống lặp request, nên lỗi mạng sau khi máy chủ đã xử lý vẫn có thể dẫn đến xử lý lại khi thử lại.
- Tự cuộn khi đang ở gần cuối cuộc trò chuyện. Nếu đang đọc phía trên, giữ vị trí và hiện nút về tin mới nhất.
- Phản hồi đến sau khi chuyển phiên/xem mẫu không cập nhật nhầm màn hình mới.
- Nội dung đang soạn được giữ khi chuyển tab Chuyến đi / Sau chuyến đi; tạo phiên mới sẽ xóa bản nháp.
- Nút Sửa yêu cầu trong thông báo lỗi đưa lại nội dung cũ vào ô nhập và focus để chỉnh sửa.
- Phần chào, ô soạn tin và logic tự cuộn tách thành `ChatWelcome.jsx`, `ChatComposer.jsx`, `hooks/useChatScroll.js`.

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

## Timeline, bản đồ và thuyết minh

- `ItineraryTimeline.jsx` hiển thị số điểm, khung giờ, tổng tiền cho cả nhóm, và từng điểm theo đúng thứ tự `plan.stops`. Không dùng LLM để tính lại số liệu.
- Chọn card / Xem trên bản đồ: chọn marker cùng `poi_id`, mở popup và chuyển sang bản đồ trên mobile.
- Chọn marker: highlight card và cuộn tới card trên desktop. Nút Xem trong lịch trình đưa về chat trên mobile.
- Xem toàn tuyến ở đầu timeline hoặc góc bản đồ: bỏ lựa chọn, đóng popup và fit toàn bộ tuyến cùng các điểm có tọa độ. Thiếu tọa độ thì giữ đúng số thứ tự marker còn lại.
- Dùng `plan.polyline` từ công cụ. Thiếu geometry thì vẽ nét đứt nối các điểm kèm nhãn minh họa; không coi là chỉ dẫn đường.
- Nút nghe trên card hoặc thông tin POI gọi cùng API `/api/narrate`. Một trình phát chung dưới workspace ngăn audio phát chồng; có loading, thử lại khi lỗi API và nội dung chữ khi không có audio.
- Đổi ngôn ngữ/phiên sẽ đóng thuyết minh. Kết quả cũ về muộn không thay thế địa điểm đang nghe.
