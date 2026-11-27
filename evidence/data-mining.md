# Đào data — cách đếm và kết quả

> Điền ở guide bước 1.2. Ôn lại: ngày 2, ngày 6 · lab ngày 2, lab ngày 6.
> Không đào data thì xoá file này. Script / công thức đếm để trong repo (vd `evidence/count.py` hoặc ghi công thức Sheets ngay dưới), người khác chạy lại phải ra cùng số.
> Repo chỉ chứa số đã tổng hợp và vài dòng ví dụ — không chép lại nguyên file data.

## 1. Cách đếm — viết TRƯỚC khi chạy

### Nguồn A · Bài báo

- Data dùng: bài Người Đô Thị, 04/08/2026, https://nguoidothi.net.vn/goc-khuat-cua-nguoi-len-ke-hoach-du-lich-53571.html — dẫn khảo sát Klook, 2.725 du khách, 10 thị trường. Xem 27/11/2026.
- Đếm gì: tỷ lệ bài viết sẵn (ngân sách, điều phối lịch) · trên tập nào: một bài báo · lọc gì: không tải file gốc của Klook
- **Mẫu số là gì:** 2.725 du khách do bài nêu. Bài không tách từng tỷ lệ theo riêng Việt Nam.
- Script / công thức: không có script. Lấy đúng chữ trong bài.

### Nguồn B · Facebook

- Data dùng: 21 dòng trong `docs/research-data.md`, đã bỏ tên, xem 27/11/2026. Bài 14 ghi nội dung do AI tạo, không tính là lời một người.
- Đếm gì: bài người viết đang tự lên lịch và hỏi nhóm; bài đã có lịch nháp vẫn hỏi nhóm trước khi chốt · trên tập nào: 20 bài người viết · lọc gì: mẫu có chủ đích, chỉ bài xin kinh nghiệm
- **Mẫu số là gì:** N = 20 bài người viết. Không tính bài 14. Không phải mẫu ngẫu nhiên của cả nhóm Facebook.
- Script / công thức: đếm tay trên bảng.
  - "Tự lên lịch và hỏi nhóm" = cột Đang kẹt hoặc câu xin giúp nói người viết đang tự xếp điểm, ngày, chi phí hoặc cung đường. Không tính câu hỏi chính là visa/thủ tục (bài 15, 20) hoặc chọn tour, land tour, hướng dẫn viên (bài 16, 17).
  - "Đã có lịch nháp" = cột Có lịch nháp ghi lịch từng ngày, ảnh lịch tự làm, km và giờ từng chặng, hoặc nói đã lên kế hoạch xong rồi phải sửa. "Có hướng", "thứ tự thành phố", "ý định ở mỗi nơi 2–3 ngày", "3 địa điểm" không tính.

## 2. Đọc trước, đếm sau

Đã đọc 1 bài báo và 21 dòng Facebook trước khi chốt nhãn trên mẫu 20 bài người viết. Các *kiểu* hành vi thấy được (trước khi định nghĩa thứ cần đếm):
- Người đang tự xếp lịch và đưa bài lên nhóm để xin người đã đi góp ý.
- Người đã có lịch nháp vẫn hỏi nhóm trước khi chốt.
- Người hỏi thời tiết hoặc mùa nhưng bài không kèm số dự báo; ảnh nếu có là lịch tự làm, không phải ảnh điểm.
- Một số bài không xin sửa lịch: hỏi ngày visa, hoặc hỏi nên book tour.

## 3. Kết quả

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| Facebook: đang tự lên lịch và hỏi nhóm | 16/20 | 80% | Bài 1–13, 18, 19, 21. Bỏ bài 14 (AI). Không tính 15, 16, 17, 20 |
| Facebook: đã có lịch nháp vẫn hỏi nhóm | 6/20 | 30% | Bài 1, 2, 4, 9, 19, 21. Ngày 18/05, 22/03, 04/09, 21/07, 19/09, 04/11/2026 |
| Facebook: hỏi visa hoặc tour, không tự xếp lịch ngày | 4/20 | 20% | Bài 15, 20 visa. Bài 16, 17 tour hoặc hướng dẫn viên |
| Facebook: có số thời tiết hoặc ảnh điểm thật | 0/20 | 0% | Bài 4, 15, 21 chỉ hỏi, không có số. Ảnh được nhắc là lịch tự làm |
| Facebook: đúng một ngày ở Hà Nội | 0/20 | 0% | Không suy ra pain của lát cắt từ mẫu này |
| Klook: cân đối ngân sách là thử thách lớn nhất | — /2725 | 60,4% | Bài chỉ ghi %, không ghi tử số. Không suy ra số người |
| Klook: áp lực điều phối lịch trình | — /2725 | 50,9% | Bài ghi %, không ghi tử số |

Ghi dạng "x/N (y%)". "Nhiều bạn…" không phải số.

## 4. ≥5 ví dụ cụ thể (mã dòng / mã đã ẩn danh, không đoán ai là ai)

1. "Cái này vượt quá ngân sách của tôi rồi" — Người Đô Thị 04/08/2026, bài ghi 52,8% người lên kế hoạch nghe câu này nhiều nhất.
2. "Mình đã tự tìm hiểu khá nhiều nhưng vẫn muốn xin thêm kinh nghiệm thực tế từ mọi người đã đi." — Facebook 04/09/2026.
3. "e gửi lên đây xin ý kiến mọi người nhiều kinh nghiệm xem hợp lý chưa để e còn sửa cho hợp lý ạ." — Facebook 22/03/2026.
4. "Rất mong nhận được mưa comment chia sẻ từ mọi người để nhà em chốt phòng sớm." — Facebook 18/05/2026.
5. "Lúc đó lên kế hoạch xong xuôi rồi nhưng cuối cùng lại đổi lịch, thế là lỡ mất một cuộc hẹn với biển." — Facebook 21/07/2026.
6. "Đi tháng 9 thời tiết KL/Malacca/Singapore thế nào, có nên mang ô/áo mưa không?" — Facebook 04/09/2026, bài 4. Bài không kèm số dự báo.
7. "tư vấn giúp xem lịch đi có ổn không ạ, và nếu có thêm thông tin ăn ngủ nghỉ ở các chặng thì cho mình xin luôn ạ." — Facebook 19/09/2026, bài 19. Đã có km và giờ từng chặng.
8. "nên tự bay sang rồi book land tour, hay đặt tour trọn gói từ Việt Nam luôn thì sẽ tối ưu và tiện hơn ạ?" — Facebook 25/11/2026, bài 16. Câu này không phải tự xếp lịch ngày.

## 5. Giới hạn của data

Data cho biết người ta **làm gì**, không cho biết **vì sao**. Thiếu gì, lệch về phía nào: Facebook là mẫu tự chọn; comment không được chép nên chưa đo giờ và giá lệch nhau đến mức nào; 0/20 bài người viết có ảnh điểm thật hoặc số thời tiết. Klook nói về chuyến nhóm khoảng một tuần, không phải một ngày ở Hà Nội. 0/20 bài là đúng một ngày ở Hà Nội. Nhược điểm của cách hỏi nhóm: các luồng thông tin khác nhau, không có hình ảnh điểm và không có thời tiết thật để đối chiếu. Không dùng các bài này làm giờ, giá hay thời tiết cho bản chạy thử.
→ Kiểm lại bằng phỏng vấn / khảo sát nào: phỏng vấn ≥3 người ngoài nhóm, chưa làm.
