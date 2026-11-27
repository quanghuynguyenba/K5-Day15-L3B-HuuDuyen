import Button from "@mui/material/Button";
import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function PoiCard({ poiId, lang, previewPoi }) {
  const [poi, setPoi] = useState(previewPoi || null);
  const [narration, setNarration] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    setNarration(null);
    if (previewPoi) {
      setPoi(previewPoi);
      return;
    }
    setPoi(null);
    api
      .poi(poiId)
      .then((p) => {
        if (active) setPoi(p);
      })
      .catch(() => {
        if (active) setPoi(null);
      });
    return () => {
      active = false;
    };
  }, [poiId, previewPoi]);

  async function listen() {
    setLoading(true);
    try {
      if (previewPoi) {
        setNarration({
          text: "Bản xem trước thiết kế. Audio thực tế sẽ được cung cấp qua API thuyết minh.",
          audio_url: null,
        });
        return;
      }
      setNarration(await api.narrate(poiId, lang));
    } catch (e) {
      setNarration({ text: `⚠️ ${e.message}`, audio_url: null });
    } finally {
      setLoading(false);
    }
  }

  if (!poi) return null;
  const notes = poi[`notes_${lang}`] || poi.notes_en || poi.notes_vi;

  return (
    <div className="poi-card">
      <h3>{poi.name.vi}</h3>
      <span className="poi-category">
        Văn hóa & khám phá {previewPoi ? "· Minh họa" : ""}
      </span>
      <p className="muted">
        {poi.name.en} · {poi.open}–{poi.close} ·{" "}
        {poi.price_vnd.toLocaleString("vi-VN")} VND
        {poi.closed_days?.length > 0 &&
          ` · nghỉ: ${poi.closed_days.join(", ")}`}
      </p>
      <p>
        {poi[`description_${lang}`] || poi.description_en || poi.description_vi}
      </p>
      {notes && <p className="notes">📌 {notes}</p>}
      <Button
        type="button"
        variant="contained"
        onClick={listen}
        disabled={loading}
      >
        {loading ? "Đang tạo thuyết minh…" : "🔊 Nghe thuyết minh"}
      </Button>
      {narration && (
        <div className="narration">
          <p>{narration.text}</p>
          {narration.audio_url ? (
            <audio controls autoPlay src={narration.audio_url} />
          ) : (
            <p className="muted">Chưa có audio (MOCK hoặc TTS lỗi).</p>
          )}
        </div>
      )}
    </div>
  );
}
