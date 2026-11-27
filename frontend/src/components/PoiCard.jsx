import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function PoiCard({ poiId, lang }) {
  const [poi, setPoi] = useState(null)
  const [narration, setNarration] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setNarration(null)
    api.poi(poiId).then(setPoi).catch(() => setPoi(null))
  }, [poiId])

  async function listen() {
    setLoading(true)
    try {
      setNarration(await api.narrate(poiId, lang))
    } catch (e) {
      setNarration({ text: `⚠️ ${e.message}`, audio_url: null })
    } finally {
      setLoading(false)
    }
  }

  if (!poi) return null
  const notes = poi[`notes_${lang}`] || poi.notes_en || poi.notes_vi

  return (
    <div className="poi-card">
      <h3>{poi.name.vi}</h3>
      <p className="muted">
        {poi.name.en} · {poi.open}–{poi.close} · {poi.price_vnd.toLocaleString('vi-VN')} VND
        {poi.closed_days?.length > 0 && ` · nghỉ: ${poi.closed_days.join(', ')}`}
      </p>
      {notes && <p className="notes">📌 {notes}</p>}
      <button onClick={listen} disabled={loading}>
        {loading ? 'Đang tạo thuyết minh…' : '🔊 Nghe thuyết minh'}
      </button>
      {narration && (
        <div className="narration">
          <p>{narration.text}</p>
          {narration.audio_url
            ? <audio controls autoPlay src={narration.audio_url} />
            : <p className="muted">Chưa có audio (MOCK hoặc TTS lỗi).</p>}
        </div>
      )}
    </div>
  )
}
