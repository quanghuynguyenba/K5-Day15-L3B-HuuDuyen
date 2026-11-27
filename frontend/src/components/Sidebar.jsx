import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Sidebar({ mock, langs, lang, onLang, date, onDate, onReset }) {
  const [weather, setWeather] = useState(null)

  useEffect(() => {
    api.weather(date).then(setWeather).catch(() => setWeather(null))
  }, [date])

  return (
    <aside className="sidebar">
      <h1>🗺️ Hanoi Trip</h1>
      {mock && <div className="badge-mock">Đang chạy MOCK — chưa nối LLM</div>}

      <label>
        Ngôn ngữ thuyết minh
        <select value={lang} onChange={(e) => onLang(e.target.value)}>
          {langs.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
      </label>

      <label>
        Ngày đi
        <input type="date" value={date} onChange={(e) => onDate(e.target.value)} />
      </label>

      {weather && (
        <div className="weather">
          <div className="temp">{Math.round(weather.temp_max)}°C</div>
          <div>{weather.is_rainy ? '🌧️ Có mưa' : '☀️ Không mưa'}</div>
        </div>
      )}

      <button className="secondary" onClick={onReset}>Bắt đầu lại</button>
    </aside>
  )
}
