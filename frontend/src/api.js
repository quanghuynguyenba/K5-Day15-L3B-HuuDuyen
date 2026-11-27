// Mọi lời gọi backend nằm ở đây. Hợp đồng: xem server.py
async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
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
}

const post = (path, body) =>
  request(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  config: () => request("/api/config"),
  chat: (sessionId, message, date) =>
    post("/api/chat", { session_id: sessionId, message, date }),
  reset: (sessionId) => post("/api/reset", { session_id: sessionId }),
  poi: (poiId) => request(`/api/pois/${poiId}`),
  weather: (date) => request(`/api/weather?date=${date}`),
  narrate: (poiId, lang) => post("/api/narrate", { poi_id: poiId, lang }),
  summary: (sessionId, lang) =>
    post("/api/summary", { session_id: sessionId, lang }),
};

export function newSessionId() {
  return crypto.randomUUID();
}
