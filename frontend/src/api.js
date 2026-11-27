// Mọi lời gọi backend nằm ở đây. Hợp đồng: xem server.py
async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

const post = (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) })

export const api = {
  config: () => request('/api/config'),
  chat: (sessionId, message, date) => post('/api/chat', { session_id: sessionId, message, date }),
  reset: (sessionId) => post('/api/reset', { session_id: sessionId }),
  poi: (poiId) => request(`/api/pois/${poiId}`),
  weather: (date) => request(`/api/weather?date=${date}`),
  narrate: (poiId, lang) => post('/api/narrate', { poi_id: poiId, lang }),
  summary: (sessionId, lang) => post('/api/summary', { session_id: sessionId, lang }),
}

export function newSessionId() {
  return crypto.randomUUID()
}
