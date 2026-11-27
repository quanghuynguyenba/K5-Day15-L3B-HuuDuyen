import { useEffect, useState } from "react";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Skeleton from "@mui/material/Skeleton";
import { api } from "../api.js";
import { formatMoney } from "../utils/itinerary.js";
import Icon from "./Icon.jsx";
import NarrationPlayer from "./NarrationPlayer.jsx";
import { poiImages } from "../poiImages.js";

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
  stopNumber,
}) {
  const [poi, setPoi] = useState(previewPoi || null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [imageFailed, setImageFailed] = useState(false);
  useEffect(() => {
    let active = true;
    setError("");
    setImageFailed(false);
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
  const image =
    poiImages[poiId] ||
    (sourceUrl(poi.image_url || "")
      ? {
          src: poi.image_url,
          alt: poi.name?.vi || poiId,
          source: sourceUrl(poi.image_source || ""),
        }
      : null);
  const sources =
    typeof poi.source === "string"
      ? [...new Set(poi.source.split("|").map(sourceUrl).filter(Boolean))]
      : [];
  return (
    <article className="poi-card">
      {image && !imageFailed ? (
        <figure className="poi-photo">
          <img
            src={image.src}
            alt={image.alt}
            onError={() => setImageFailed(true)}
            decoding="async"
          />
          {stop?.arrive && (
            <span className="poi-photo-schedule">
              <Icon name="clock" size={14} />
              Lịch trình: {stop.arrive}
              {stop.depart ? ` – ${stop.depart}` : ""}
            </span>
          )}
        </figure>
      ) : (
        <div className="poi-cover">
          <Icon name={poi.category === "food" ? "food" : "museum"} size={22} />
          <span>
            HÀ NỘI · {previewPoi ? "ĐỊA ĐIỂM MẪU" : "KHÁM PHÁ ĐIỂM ĐẾN"}
          </span>
        </div>
      )}
      <h3>
        {stopNumber ? `${stopNumber}. ` : ""}
        {poi.name?.vi || poiId}
      </h3>
      <div className="poi-tags">
        <Chip
          label={CATEGORIES[poi.category] || "Văn hóa & khám phá"}
          size="small"
        />
        {poi.tags?.includes("culture") && <Chip label="Văn hóa" size="small" />}
        {typeof poi.indoor === "boolean" && (
          <Chip
            className={poi.indoor ? "poi-tag-indoor" : "poi-tag-outdoor"}
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
              : `${formatMoney(poi.price_vnd)} / người`}
          </dd>
        </div>
        {Number.isFinite(poi.visit_minutes) && (
          <div>
            <dt>Tham quan dự kiến</dt>
            <dd>{poi.visit_minutes} phút</dd>
          </div>
        )}
        <div className="poi-fact-sources">
          <dt>&nbsp;</dt>
          <dd>
            {sources.length ? (
              sources.map((source, index) => (
                <a
                  key={source}
                  href={source}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Nguồn thông tin{sources.length > 1 ? ` ${index + 1}` : ""} ↗
                </a>
              ))
            ) : (
              <span>Chưa có nguồn thông tin</span>
            )}
          </dd>
        </div>
      </dl>
      <Button
        variant="contained"
        onClick={() => onNarrate(poiId)}
        disabled={busy}
        startIcon={<Icon name="speaker" size={18} />}
      >
        {busy ? "Đang tạo thuyết minh…" : "Nghe thuyết minh"}
      </Button>
      {narration?.poiId === poiId && (
        <NarrationPlayer
          narration={narration}
          onRetry={() => onNarrate(poiId)}
        />
      )}
      {onShowInChat && (
        <Button
          variant="outlined"
          className="show-in-chat"
          onClick={onShowInChat}
        >
          Xem trong lịch trình
        </Button>
      )}
      <details className="poi-extra-details">
        <summary>Lưu ý và ghi công ảnh</summary>
        {notes && <p className="notes">{notes}</p>}
        {image?.source && !imageFailed && (
          <small className="poi-photo-credit">
            Ảnh:{" "}
            <a href={image.source} target="_blank" rel="noopener noreferrer">
              {image.author || "Nguồn ảnh"}
            </a>
            {image.license && (
              <>
                {" "}
                ·{" "}
                <a
                  href={image.licenseUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {image.license}
                </a>{" "}
                · Thu nhỏ/cắt khung hiển thị
              </>
            )}
          </small>
        )}
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
      </details>
      {poi.schedulable === false && (
        <p className="notes">
          Chưa đủ giá hoặc giờ mở cửa để đưa vào lịch trình. Bạn vẫn có thể xem
          thông tin địa điểm.
        </p>
      )}
    </article>
  );
}
