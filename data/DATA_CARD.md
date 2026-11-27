# Data card — dữ liệu bản chạy thử dùng

> Điền ở guide bước 2.4 (bản đầu ở CP2, đủ ở CP3). Ôn lại: ngày 6 · lab ngày 6. Chấm ở rubric R4.
> Một trang. Mỗi dataset một mục. Dữ liệu chạy thử (bài mẫu, thông báo mẫu, đoạn transcript…) để trong thư mục `data/` này.
> Không commit nguyên tài liệu khoá, dữ liệu cá nhân thật hay nguyên file data BTC cấp — chỉ đoạn trích ngắn, bản viết lại, hoặc số đã tổng hợp.
> Bản đầu CP2, 27/11/2026. Data synthetic không phải bằng chứng pain.

## Dataset 1 · POI Hà Nội synthetic

| | |
|---|---|
| Dùng để làm gì | nguồn cho `search_pois` và `plan_route` |
| Từ đâu | nhóm tự viết, không copy review hay vé của người thật |
| Xử lý những bước gì | ghi giờ, giá, trong nhà, ngày đóng cửa ngay trong file. Chưa lọc từ API |
| Số dòng / số đoạn | 8 điểm |
| Phiên bản / ngày lấy | `data/pois.json` · 27/11/2026 · seed không dùng vì viết tay |
| Nhãn | `synthetic` |
| Giới hạn | giá và giờ là số giả để chạy lát cắt, chưa đối chiếu website điểm. Thời gian đi giữa hai điểm cố định 15 phút trong `plan_route`, chưa gọi bản đồ |

**Data `synthetic` (nhóm tự sinh):** 8 điểm viết tay trong `data/pois.json`, không dùng prompt sinh. Seed không dùng vì viết tay. Người kiểm là nhóm trước demo. Mỗi điểm có trường `source: synthetic`. Data tự dựng **không phải bằng chứng pain**.

## Dataset 2 · Thời tiết synthetic

| | |
|---|---|
| Dùng để làm gì | nguồn cho `get_weather` |
| Từ đâu | nhóm tự viết |
| Xử lý những bước gì | một ngày mẫu, mặc định không mưa. Câu người dùng có chữ mưa thì công cụ trả mưa |
| Số dòng / số đoạn | 1 ngày |
| Phiên bản / ngày lấy | `data/weather.json` · 27/11/2026 |
| Nhãn | `synthetic` |
| Giới hạn | chưa gọi Open-Meteo |

## Dataset 3 · Khảo sát Klook do báo dẫn

| | |
|---|---|
| Dùng để làm gì | bằng chứng pain, không đưa vào công cụ xếp lịch |
| Từ đâu | https://nguoidothi.net.vn/goc-khuat-cua-nguoi-len-ke-hoach-du-lich-53571.html · Người Đô Thị, 04/08/2026, dẫn khảo sát Klook 2.725 du khách tại 10 thị trường |
| Xử lý những bước gì | trích số và một câu, không tải microdata |
| Số dòng / số đoạn | một bài báo |
| Phiên bản / ngày lấy | xem 27/11/2026 |
| Nhãn | thật (nguồn công khai thứ cấp) |
| Giới hạn | bài không tách mọi số theo riêng Việt Nam. Khảo sát nói về người lên kế hoạch chuyến nhóm khoảng một tuần, không phải một ngày ở Hà Nội. Nhóm chưa tự đếm review và chưa phỏng vấn |

## Dataset 4 · Bài Facebook đã bỏ tên

| | |
|---|---|
| Dùng để làm gì | bằng chứng pain và câu thử `nguoi_dung`. Không đưa vào `search_pois`, `plan_route`, `get_weather` |
| Từ đâu | nhóm chép tay, bỏ tên, `docs/research-data.md` |
| Xử lý những bước gì | một dòng một bài. Bài 14 ghi nội dung do AI tạo, loại khỏi mẫu người |
| Số dòng / số đoạn | 21 dòng đã chép, 20 bài người viết |
| Phiên bản / ngày lấy | xem 27/11/2026 |
| Nhãn | thật (lời người dùng, mẫu có chủ đích) |
| Giới hạn | không phải mẫu ngẫu nhiên. 0/20 là một ngày ở Hà Nội. Không chép comment. Không dùng làm giờ, giá hay thời tiết cho bản chạy thử |
