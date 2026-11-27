import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";

export default function useNarration({ lang, preview, stops, sessionId }) {
  const [narration, setNarration] = useState(null);
  const requestId = useRef(0);
  const close = useCallback(() => {
    requestId.current++;
    setNarration(null);
  }, []);
  useEffect(() => {
    close();
    return () => {
      requestId.current++;
    };
  }, [lang, preview, sessionId, close]);
  const listen = useCallback(
    async (poiId) => {
      const version = ++requestId.current;
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
          : await api.narrate(poiId, lang);
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
        if (version === requestId.current)
          setNarration({ ...context, error: error.message, loading: false });
      }
    },
    [stops, lang, preview],
  );
  return { narration, listen, close };
}
