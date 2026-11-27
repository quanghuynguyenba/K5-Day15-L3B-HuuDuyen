import Chip from "@mui/material/Chip";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Icon from "./Icon.jsx";

function weatherLabel(weather, preview) {
  if (preview) return "26°C · Có thể mưa chiều (mẫu)";
  if (!weather) return "Chưa có dữ liệu thời tiết";
  return `${Math.round(weather.temp_max)}°C · ${weather.is_rainy ? "Có thể có mưa" : "Không mưa"}${weather.mock ? " (mẫu)" : ""}`;
}

export default function Header({
  langs,
  lang,
  onLangChange,
  weather,
  preview,
}) {
  return (
    <header className="top-header">
      <div className="brand">
        <span className="brand-icon">
          <Icon size={23} />
        </span>
        <strong>Hanoi Travel AI</strong>
        <Chip
          className="location-pill"
          icon={<Icon name="pin" size={14} />}
          label="Hà Nội"
          size="small"
        />
      </div>
      <div className="header-tools">
        <Chip
          className="weather-pill"
          icon={<Icon name="cloud" size={18} />}
          label={weatherLabel(weather, preview)}
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
