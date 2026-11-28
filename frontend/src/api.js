// Mọi lời gọi backend nằm ở đây. Hợp đồng: xem server.py
// options.signal (tuỳ chọn): người dùng huỷ (vd đóng popup) → fetch dừng, backend thấy client ngắt kết nối,
// hàm ném lỗi có name = "AbortError" để nơi gọi bỏ qua im lặng.
async function request(path, { signal, ...options } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 60000);
  const cancel = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener("abort", cancel);
  try {
    let res;
    try {
      res = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options,
        signal: controller.signal,
      });
    } catch {
      if (signal?.aborted) {
        const aborted = new Error("Đã huỷ yêu cầu.");
        aborted.name = "AbortError";
        throw aborted;
      }
      if (controller.signal.aborted)
        throw new Error("Máy chủ phản hồi quá lâu. Vui lòng thử lại yêu cầu.");
      throw new Error(
        "Không kết nối được máy chủ. Hãy kiểm tra mạng hoặc backend rồi thử lại.",
      );
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = typeof err.detail === "string" ? err.detail : null;
      throw new Error(
        res.status >= 500
          ? "Máy chủ đang gặp sự cố. Vui lòng thử lại sau ít phút."
          : detail ||
              `Yêu cầu chưa được xử lý (HTTP ${res.status}). Vui lòng kiểm tra nội dung rồi thử lại.`,
      );
    }
    try {
      return await res.json();
    } catch {
      throw new Error("Phản hồi từ máy chủ chưa hợp lệ. Vui lòng thử lại.");
    }
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", cancel);
  }
}

const post = (path, body, options = {}) =>
  request(path, { method: "POST", body: JSON.stringify(body), ...options });

export const api = {
  config: () => request("/api/config"),
  // location: { lat, lng, accuracy } từ GPS trình duyệt, hoặc null nếu chưa có / bị từ chối
  chat: (sessionId, message, date, location = null) =>
    post("/api/chat", { session_id: sessionId, message, date, location }),
  reset: (sessionId) => post("/api/reset", { session_id: sessionId }),
  poi: (poiId) => request(`/api/pois/${poiId}`),
  pois: () => request("/api/pois"),
  weather: (date) => request(`/api/weather?date=${date}`),
  narrate: (poiId, lang, signal) =>
    post("/api/narrate", { poi_id: poiId, lang }, { signal }),
  summary: (sessionId, lang) =>
    post("/api/summary", { session_id: sessionId, lang }),
};

export function newSessionId() {
  return crypto.randomUUID();
}
