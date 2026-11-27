import { useEffect, useState } from "react";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Skeleton from "@mui/material/Skeleton";
import { api } from "../api.js";
import { formatMoney } from "../utils/itinerary.js";
import Icon from "./Icon.jsx";

const CATEGORIES = {
  history: "Lịch sử",
  museum: "Bảo tàng",
  food: "Ẩm thực",
  cafe: "Cà phê",
  nature: "Thiên nhiên",
  shopping: "Mua sắm",
  art: "Nghệ thuật",
  night: "Khám phá buổi tối",
};
function sourceUrl(value) {
  try {
    const url = new URL(value.trim());
    return ["https:", "http:"].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

export default function PoiCard({
  poiId,
  lang,
  previewPoi,
  onNarrate,
  narration,
  onShowInChat,
  stop,
}) {
  const [poi, setPoi] = useState(previewPoi || null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setError("");
    if (previewPoi) {
      setPoi(previewPoi);
      return;
    }
    setPoi(null);
    api
      .poi(poiId)
      .then((result) => {
        if (!result || typeof result !== "object" || !result.name)
          throw new Error("Chưa có thông tin hợp lệ cho địa điểm này.");
        if (active) setPoi(result);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [poiId, previewPoi, retry]);
  if (error)
    return (
      <div className="poi-card poi-error" role="alert">
        <Icon name="pin" size={32} />
        <h3>Chưa tải được địa điểm</h3>
        <p>{error}</p>
        <Button
          variant="outlined"
          onClick={() => setRetry((value) => value + 1)}
        >
          Thử tải lại
        </Button>
      </div>
    );
  if (!poi)
    return (
      <div
        className="poi-card"
        role="status"
        aria-label="Đang tải thông tin địa điểm"
      >
        <Skeleton variant="rounded" height={40} />
        <Skeleton width="80%" height={36} />
        <Skeleton width="55%" />
        <Skeleton height={70} />
        <Skeleton variant="rounded" height={40} />
      </div>
    );
  const notes = poi[`notes_${lang}`] || poi.notes_vi || poi.notes_en;
  const description =
    poi[`description_${lang}`] || poi.description_vi || poi.description_en;
  const busy = narration?.loading && narration.poiId === poiId;
  const sources =
    typeof poi.source === "string"
      ? [...new Set(poi.source.split("|").map(sourceUrl).filter(Boolean))]
      : [];
  return (
    <article className="poi-card">
      <div className="poi-cover">
        <Icon name={poi.category === "food" ? "food" : "museum"} size={22} />
        <span>
          HÀ NỘI · {previewPoi ? "ĐỊA ĐIỂM MẪU" : "KHÁM PHÁ ĐIỂM ĐẾN"}
        </span>
      </div>
      <h3>{poi.name?.vi || poiId}</h3>
      {poi.name?.en && <p className="poi-english">{poi.name.en}</p>}
      <div className="poi-tags">
        <Chip
          label={CATEGORIES[poi.category] || "Văn hóa & khám phá"}
          size="small"
        />
        {typeof poi.indoor === "boolean" && (
          <Chip
            label={poi.indoor ? "Trong nhà" : "Ngoài trời"}
            size="small"
            variant="outlined"
          />
        )}
        {previewPoi && (
          <Chip label="Minh họa" size="small" variant="outlined" />
        )}
      </div>
      <p className="poi-description">
        {description || "Chưa có mô tả cho địa điểm này."}
      </p>
      <dl className="poi-facts">
        <div>
          <dt>
            <Icon name="clock" size={16} />
            Giờ mở cửa
          </dt>
          <dd>
            {poi.open && poi.close
              ? `${poi.open} – ${poi.close}`
              : "Chưa có giờ mở cửa"}
          </dd>
        </div>
        <div>
          <dt>Giá vé / người</dt>
          <dd>
            {poi.price_vnd == null
              ? "Chưa có giá vé"
              : formatMoney(poi.price_vnd)}
          </dd>
        </div>
        {Number.isFinite(poi.visit_minutes) && (
          <div>
            <dt>Tham quan dự kiến</dt>
            <dd>{poi.visit_minutes} phút</dd>
          </div>
        )}
        {stop && (
          <div>
            <dt>Giờ đến theo lịch</dt>
            <dd>{stop.arrive || "—"}</dd>
          </div>
        )}
      </dl>
      {notes && <p className="notes">{notes}</p>}
      {sources.length ? (
        sources.map((source, index) => (
          <a
            className="poi-source"
            key={source}
            href={source}
            target="_blank"
            rel="noopener noreferrer"
          >
            Nguồn thông tin {sources.length > 1 ? index + 1 : ""}
          </a>
        ))
      ) : (
        <small className="poi-source">
          {previewPoi
            ? "Thông tin minh họa cho thiết kế"
            : "Nguồn thông tin chưa được cung cấp"}
        </small>
      )}
      <Button
        variant="contained"
        onClick={() => onNarrate(poiId)}
        disabled={busy}
        startIcon={<Icon name="speaker" size={18} />}
      >
        {busy ? "Đang tạo thuyết minh…" : "Nghe thuyết minh"}
      </Button>
      <Button className="show-in-chat" onClick={onShowInChat}>
        Xem trong lịch trình
      </Button>
    </article>
  );
}
