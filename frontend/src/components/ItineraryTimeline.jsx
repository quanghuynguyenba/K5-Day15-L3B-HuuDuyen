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
        <span>
          <Icon name="family" size={21} />
          {Number.isInteger(plan.n_people)
            ? `${plan.n_people} người`
            : "Cả nhóm"}
        </span>
        <span>
          <Icon name="clock" size={21} />
          {stops[0]?.arrive || "—"} – {stops.at(-1)?.depart || "—"}
        </span>
        <strong>
          <Icon name="money" size={21} />
          {formatMoney(plan.total_cost)}
        </strong>
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
                {stop.description_vi || "Chưa có mô tả địa điểm."} ·{" "}
                <span className="stop-cost">
                  {stop.cost === 0
                    ? "Miễn phí"
                    : `${formatMoney(stop.cost)}${Number.isInteger(plan.n_people) ? ` / ${plan.n_people} người` : ""}`}
                </span>
              </p>
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
                  className={`stop-audio ${narration?.poiId === stop.poi_id ? "active" : ""}`}
                  aria-label={`Nghe thuyết minh ${stop.name?.vi || stop.poi_id}`}
                  title="Nghe thuyết minh"
                >
                  <Icon
                    name={
                      narration?.poiId === stop.poi_id ? "waveform" : "speaker"
                    }
                    size={19}
                  />
                </Button>
              </div>
              {!hasCoordinates(stop) && (
                <small>Chưa có tọa độ để hiển thị trên bản đồ.</small>
              )}
            </div>
          </li>
        ))}
      </ol>
      <Button
        className="show-whole-route"
        variant="outlined"
        onClick={onShowRoute}
        startIcon={<Icon name="explore" size={19} />}
        disabled={!stops.some(hasCoordinates)}
      >
        Xem toàn bộ tuyến đường
      </Button>
      {!!plan.dropped?.length && (
        <p className="hint">
          {plan.dropped.length} điểm được bỏ khỏi lịch trình theo kết quả công
          cụ.
        </p>
      )}
    </section>
  );
}
