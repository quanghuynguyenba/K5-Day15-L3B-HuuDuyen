// Dữ liệu xem thiết kế, không gửi vào session/API thật.
export const previewStops = [
  {
    poi_id: "hn_002",
    name: { vi: "Hồ Hoàn Kiếm – Đền Ngọc Sơn" },
    lat: 21.0307,
    lng: 105.8524,
    arrive: "08:00",
    depart: "09:00",
    cost: 100000,
    description_vi:
      "Bắt đầu ngày mới bên hồ, khám phá không gian văn hóa giữa lòng Hà Nội.",
    price_vnd: 50000,
  },
  {
    poi_id: "hn_001",
    name: { vi: "Văn Miếu – Quốc Tử Giám", en: "Temple of Literature" },
    lat: 21.0294,
    lng: 105.8355,
    arrive: "09:30",
    depart: "11:00",
    cost: 140000,
    description_vi:
      "Khám phá kiến trúc truyền thống, những khoảng sân xanh và câu chuyện về tinh thần hiếu học của Việt Nam.",
    price_vnd: 70000,
  },
  {
    poi_id: "hn_005",
    name: { vi: "Ăn trưa tại phố cổ" },
    lat: 21.0338,
    lng: 105.85,
    arrive: "11:30",
    depart: "12:30",
    cost: 200000,
    description_vi:
      "Dừng chân thưởng thức hương vị ẩm thực Hà Nội trong không gian phố cổ.",
    price_vnd: 100000,
  },
  {
    poi_id: "hn_004",
    name: { vi: "Hoàng thành Thăng Long" },
    lat: 21.0352,
    lng: 105.8403,
    arrive: "13:30",
    depart: "15:00",
    cost: 140000,
    description_vi: "Tìm hiểu lịch sử Thăng Long qua những không gian di sản.",
    price_vnd: 70000,
  },
  {
    poi_id: "preview_cafe",
    name: { vi: "Cà phê phố cổ" },
    lat: 21.034,
    lng: 105.852,
    arrive: "15:30",
    depart: "17:00",
    cost: 270000,
    description_vi:
      "Khép lại hành trình với một buổi chiều thư thả và tách cà phê.",
    price_vnd: 135000,
  },
].map((p) => ({ ...p, open: "08:00", close: "17:00", visit_minutes: 60 }));
export const previewPlan = {
  stops: previewStops,
  total_cost: 850000,
  total_minutes: 540,
  polyline: previewStops.map((p) => [p.lat, p.lng]),
  dropped: [],
};
export const previewMessages = [
  {
    role: "user",
    content:
      "Hai người, ngân sách 1 triệu, khám phá Hà Nội từ 8h đến 17h. Thích lịch sử và ẩm thực.",
  },
  {
    role: "assistant",
    content:
      "Mình đã gợi ý hành trình 5 điểm, kết hợp văn hóa và ẩm thực. Bạn có thể chọn từng điểm để xem trên bản đồ.",
  },
];
