import { useState } from 'react'
import { api } from '../api.js'

export default function AfterTrip({ sessionId, plan, lang }) {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)

  if (!plan || plan.stops.length === 0) return <p className="hint pad">Chưa có lịch trình.</p>

  async function load() {
    setLoading(true)
    try {
      setSummary((await api.summary(sessionId, lang)).summary)
    } catch (e) {
      setSummary(`⚠️ ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="after pad">
      <div className="metrics">
        <div><span>Số điểm</span><b>{plan.stops.length}</b></div>
        <div><span>Tổng chi</span><b>{plan.total_cost.toLocaleString('vi-VN')} VND</b></div>
        <div><span>Thời gian</span><b>{plan.total_minutes} phút</b></div>
      </div>
      <ol>
        {plan.stops.map((s) => (
          <li key={s.poi_id}>{s.arrive}–{s.depart} {s.name?.vi} ({s.cost.toLocaleString('vi-VN')} VND)</li>
        ))}
      </ol>
      <button onClick={load} disabled={loading}>{loading ? 'Đang tóm tắt…' : 'Tóm tắt chuyến đi'}</button>
      {summary && <pre className="summary">{summary}</pre>}
    </div>
  )
}
