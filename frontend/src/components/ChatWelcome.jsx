import Button from "@mui/material/Button";
import Icon from "./Icon.jsx";

const STARTERS = [
  {
    icon: "museum",
    title: "Di sản & ẩm thực",
    subtitle: "2 người · 08:00–17:00 · 1 triệu",
    prompt:
      "2 người, 1 triệu, đi từ 08:00 đến 17:00 ở Hà Nội, thích lịch sử và ẩm thực",
  },
  {
    icon: "food",
    title: "Food tour phố cổ",
    subtitle: "Phở, bún chả, cà phê trứng",
    prompt: "Lên lịch food tour phố cổ cho 2 người, ngân sách 1 triệu",
  },
  {
    icon: "cloud",
    title: "Lịch trình tránh mưa",
    subtitle: "Bảo tàng & quán trong nhà",
    prompt:
      "Gợi ý lịch trình trong nhà ở Hà Nội cho 2 người, ngân sách 1 triệu",
  },
  {
    icon: "family",
    title: "Cuối tuần gia đình",
    subtitle: "Nhịp độ nhẹ, ít đi bộ xa",
    prompt:
      "Gia đình 4 người khám phá Hà Nội, ngân sách 2 triệu, ưu tiên ít đi bộ",
  },
];

export default function ChatWelcome({ onChoose, onBrowse, poiCount }) {
  return (
    <div className="welcome">
      <div className="welcome-icon">
        <Icon name="museum" size={28} />
      </div>
      <span className="eyebrow">HÀ NỘI THEO CÁCH CỦA BẠN</span>
      <h1>Xin chào! Hôm nay bạn muốn khám phá Hà Nội thế nào?</h1>
      <p>
        Hãy cho mình biết số người, thời gian, ngân sách hoặc sở thích của bạn
        để mình gợi ý tuyến đường trên bản đồ.
      </p>
      <div className="starter-grid">
        {STARTERS.map(({ icon, title, subtitle, prompt }) => (
          <Button
            type="button"
            key={title}
            onClick={() => onChoose(prompt)}
            aria-label={`Điền gợi ý: ${title}`}
          >
            <Icon name={icon} />
            <strong>{title}</strong>
            <span>{subtitle}</span>
          </Button>
        ))}
      </div>
      {onBrowse && (
        <Button
          className="browse-pois"
          onClick={onBrowse}
          startIcon={<Icon name="pin" size={17} />}
        >
          Khám phá {poiCount || ""} địa điểm từ dữ liệu nhóm
        </Button>
      )}
      <p className="starter-help">Chọn một gợi ý để chỉnh sửa trước khi gửi.</p>
    </div>
  );
}
