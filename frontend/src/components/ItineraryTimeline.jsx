import { useEffect, useRef } from "react";
import Button from "@mui/material/Button";
import Icon from "./Icon.jsx";
import { formatMoney, hasCoordinates } from "../utils/itinerary.js";

export default function ItineraryTimeline({
  plan,
  selectedPoi,
  selection,
  onSelect,
  onNarrate,
  narration,
  onShowRoute,
}) {
  const cards = useRef(new Map());
  useEffect(() => {
    if (selection?.source !== "map") return;
    const card = cards.current.get(selectedPoi);
    const list = card?.closest(".messages");
    if (!card || !list || !list.clientHeight) return;
    list.scrollTo({
      top:
        list.scrollTop +
        card.getBoundingClientRect().top -
        list.getBoundingClientRect().top -
        20,
      behavior: "instant",
    });
  }, [selection, selectedPoi]);
  if (!plan) return null;
  const stops = plan.stops || [];
  return (
    <section className="itinerary" aria-label="Lịch trình chuyến đi">
      <div className="trip-overview">
        <span className="eyebrow">HÀNH TRÌNH CỦA BẠN</span>
        <h3>Khám phá Hà Nội theo cách của bạn</h3>
        <div>
          <span>
            <Icon name="pin" size={15} />
            {stops.length} điểm
          </span>
          <span>
            <Icon name="clock" size={15} />
            {stops[0]?.arrive || "—"} – {stops.at(-1)?.depart || "—"}
          </span>
          <strong>{formatMoney(plan.total_cost)}</strong>
        </div>
        <p className="overview-caption">
          {Number.isFinite(plan.total_minutes)
            ? `${plan.total_minutes} phút · `
            : ""}
          Chi phí cho cả nhóm theo lịch trình
        </p>
        <Button
          onClick={onShowRoute}
          startIcon={<Icon name="explore" size={17} />}
          disabled={!stops.some(hasCoordinates)}
        >
          Xem toàn tuyến
        </Button>
      </div>
      {!stops.length && (
        <p className="hint">
          Chưa tìm được điểm phù hợp. Hãy thử nới ngân sách hoặc khung giờ.
        </p>
      )}
      <ol className="timeline">
        {stops.map((stop, index) => (
          <li
            key={stop.poi_id}
            ref={(el) => {
              if (el) cards.current.set(stop.poi_id, el);
              else cards.current.delete(stop.poi_id);
            }}
            className={`stop-card ${selectedPoi === stop.poi_id ? "selected" : ""}`}
            onClick={(event) => {
              if (!event.target.closest("button")) onSelect(stop.poi_id);
            }}
            aria-current={selectedPoi === stop.poi_id ? "step" : undefined}
          >
            <span className="stop-number">{index + 1}</span>
            <div className="stop-content">
              <span className="stop-time">
                <Icon name="clock" size={13} />
                {stop.arrive || "—"} – {stop.depart || "—"}
              </span>
              <h3>
                <button
                  className="stop-title"
                  onClick={() => onSelect(stop.poi_id)}
                  aria-label={`Chọn ${stop.name?.vi || stop.poi_id}`}
                >
                  {stop.name?.vi || stop.poi_id}
                </button>
              </h3>
              <p>
                {stop.description_vi ||
                  "Xem thông tin địa điểm trên bản đồ để tìm hiểu thêm."}
              </p>
              <div className="stop-footer">
                <span>{formatMoney(stop.cost)}</span>
                {selectedPoi === stop.poi_id && (
                  <span className="selected-label">Đang chọn</span>
                )}
              </div>
              <div className="stop-actions">
                <Button
                  onClick={() => onSelect(stop.poi_id)}
                  disabled={!hasCoordinates(stop)}
                  startIcon={<Icon name="pin" size={15} />}
                >
                  Xem trên bản đồ
                </Button>
                <Button
                  onClick={() => onNarrate(stop.poi_id)}
                  disabled={
                    narration?.loading && narration.poiId === stop.poi_id
                  }
                  startIcon={<Icon name="speaker" size={15} />}
                >
                  {narration?.loading && narration.poiId === stop.poi_id
                    ? "Đang tạo…"
                    : "Nghe thuyết minh"}
                </Button>
              </div>
              {!hasCoordinates(stop) && (
                <small>Chưa có tọa độ để hiển thị trên bản đồ.</small>
              )}
            </div>
          </li>
        ))}
      </ol>
      {!!plan.dropped?.length && (
        <p className="hint">
          {plan.dropped.length} điểm được bỏ khỏi lịch trình theo kết quả công
          cụ.
        </p>
      )}
    </section>
  );
}
