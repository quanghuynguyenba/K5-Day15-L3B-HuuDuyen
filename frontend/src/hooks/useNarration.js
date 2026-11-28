import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";

// Mỗi lần nghe tạo một AbortController. Đóng popup / đổi ngôn ngữ / nghe điểm khác → abort request đang chạy:
// trình duyệt cắt kết nối, backend thấy client ngắt và dừng trước bước TTS (không ghi file audio).
export default function useNarration({ lang, preview, stops, sessionId }) {
  const [narration, setNarration] = useState(null);
  const requestId = useRef(0);
  const controller = useRef(null);
  const abort = useCallback(() => {
    controller.current?.abort();
    controller.current = null;
  }, []);
  const close = useCallback(() => {
    requestId.current++;
    abort();
    setNarration(null);
  }, [abort]);
  const invalidate = useCallback(() => {
    requestId.current++;
    abort();
  }, [abort]);
  useEffect(() => {
    close();
    return invalidate;
  }, [lang, preview, sessionId, close, invalidate]);
  const listen = useCallback(
    async (poiId) => {
      abort();
      const version = ++requestId.current;
      const ctrl = new AbortController();
      controller.current = ctrl;
      const stop = stops?.find((item) => item.poi_id === poiId);
      const context = { poiId, title: stop?.name?.vi || poiId, lang };
      setNarration({ ...context, loading: true });
      try {
        const result = preview
          ? {
              text: "Đây là hành trình minh họa. Bắt đầu phiên mới để nghe thuyết minh từ API.",
              audio_url: null,
              mock: true,
              source: "preview",
              tts_status: "disabled",
            }
          : await api.narrate(poiId, lang, ctrl.signal);
        if (
          !result ||
          ((typeof result.text !== "string" || !result.text.trim()) &&
            !result.audio_url)
        )
          throw new Error(
            "Máy chủ chưa trả về nội dung thuyết minh hợp lệ. Vui lòng thử lại.",
          );
        if (
          result.audio_url &&
          (typeof result.audio_url !== "string" ||
            !/^\/(?!\/)|^https?:\/\//i.test(result.audio_url))
        )
          throw new Error("Đường dẫn audio chưa hợp lệ. Vui lòng thử lại.");
        if (version === requestId.current)
          setNarration({ ...context, ...result, loading: false });
      } catch (error) {
        if (error.name === "AbortError") return; // người dùng đã huỷ — không báo lỗi
        if (version === requestId.current)
          setNarration({ ...context, error: error.message, loading: false });
      } finally {
        if (controller.current === ctrl) controller.current = null;
      }
    },
    [stops, lang, preview, abort],
  );
  return { narration, listen, close };
}
