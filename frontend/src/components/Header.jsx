import Chip from "@mui/material/Chip";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Icon from "./Icon.jsx";
import IconButton from "@mui/material/IconButton";

function weatherLabel(weather, preview) {
  if (preview) return "26°C · Có thể mưa chiều (mẫu)";
  if (!weather) return "Chưa có dữ liệu thời tiết";
  if (weather.status === "unavailable") return "Chưa có dự báo thời tiết";
  const temperature = Number.isFinite(weather.temp_max)
    ? `${Math.round(weather.temp_max)}°C`
    : "Thiếu nhiệt độ";
  const rain =
    weather.is_rainy === true
      ? "Có thể có mưa"
      : weather.is_rainy === false
        ? "Xác suất mưa dưới 60%"
        : "Chưa rõ khả năng mưa";
  return `${temperature} · ${rain} · ${weather.mock ? "Mẫu" : weather.status === "partial" ? "Dữ liệu thiếu" : "Open-Meteo"}`;
}

export default function Header({
  langs,
  lang,
  onLangChange,
  weather,
  preview,
  onOpenSidebar,
  geo,
}) {
  const located = geo?.status === "ok" && geo.location;
  const locationLabel = located
    ? `Vị trí của bạn${geo.location.accuracy ? ` · ±${geo.location.accuracy} m` : ""}`
    : geo?.status === "pending"
      ? "Đang định vị…"
      : "Hà Nội";
  return (
    <header className="top-header">
      <div className="brand">
        {onOpenSidebar && (
          <IconButton
            onClick={onOpenSidebar}
            aria-label="Mở danh sách phiên chat"
          >
            <Icon name="panel" />
          </IconButton>
        )}
        <img className="brand-logo" src="/brand/emblem.png" alt="" width="38" height="38" />
        <strong>Hữu Duyên</strong>
        <Chip
          className={`location-pill ${located ? "located" : ""}`}
          icon={<Icon name="pin" size={14} />}
          label={locationLabel}
          title={
            located
              ? `Lịch trình xuất phát từ vị trí hiện tại (${geo.location.lat}, ${geo.location.lng})`
              : geo?.error || "Chưa có vị trí — lịch trình xuất phát từ Hồ Gươm. Bấm để thử lại."
          }
          onClick={!located && geo?.retry ? geo.retry : undefined}
          size="small"
        />
      </div>
      <div className="header-tools">
        <Chip
          className="weather-pill"
          icon={<Icon name="cloud" size={18} />}
          label={weatherLabel(weather, preview)}
          title={
            preview
              ? "Dữ liệu minh họa thiết kế"
              : weather?.error ||
                weather?.warning ||
                `${weather?.date || ""} · ${weather?.source || "Chưa có nguồn"}`
          }
          size="small"
          variant="outlined"
        />
        <ToggleButtonGroup
          className="language-switch"
          value={lang}
          exclusive
          size="small"
          aria-label="Ngôn ngữ thuyết minh"
          onChange={(_, value) => {
            if (value) onLangChange(value);
          }}
        >
          {langs.map((code) => (
            <ToggleButton
              key={code}
              value={code}
              aria-label={`Ngôn ngữ ${code.toUpperCase()}`}
            >
              {code.toUpperCase()}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </div>
    </header>
  );
}
