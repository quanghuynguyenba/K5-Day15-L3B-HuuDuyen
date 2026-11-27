import { useEffect, useState } from 'react'
import { api, newSessionId } from './api.js'
import Sidebar from './components/Sidebar.jsx'
import Chat from './components/Chat.jsx'
import MapView from './components/MapView.jsx'
import PoiCard from './components/PoiCard.jsx'
import AfterTrip from './components/AfterTrip.jsx'

const tomorrow = () => {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  return d.toISOString().slice(0, 10)
}

export default function App() {
  const [sessionId, setSessionId] = useState(newSessionId)
  const [config, setConfig] = useState({ mock: true, langs: ['vi'], center: [21.0285, 105.8542] })
  const [lang, setLang] = useState('vi')
  const [date, setDate] = useState(tomorrow)
  const [messages, setMessages] = useState([])
  const [plan, setPlan] = useState(null)
  const [selectedPoi, setSelectedPoi] = useState(null)
  const [tab, setTab] = useState('trip')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.config().then(setConfig).catch(() => {})
  }, [])

  async function send(text) {
    setMessages((m) => [...m, { role: 'user', content: text }])
    setLoading(true)
    try {
      const res = await api.chat(sessionId, text, date)
      setMessages((m) => [...m, { role: 'assistant', content: res.reply }])
      setPlan(res.plan)
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `⚠️ Lỗi: ${e.message}` }])
    } finally {
      setLoading(false)
    }
  }

  async function reset() {
    await api.reset(sessionId).catch(() => {})
    setSessionId(newSessionId())
    setMessages([])
    setPlan(null)
    setSelectedPoi(null)
  }

  return (
    <div className="layout">
      <Sidebar
        mock={config.mock}
        langs={config.langs}
        lang={lang}
        onLang={setLang}
        date={date}
        onDate={setDate}
        onReset={reset}
      />
      <main>
        <nav className="tabs">
          <button className={tab === 'trip' ? 'active' : ''} onClick={() => setTab('trip')}>Chuyến đi</button>
          <button className={tab === 'after' ? 'active' : ''} onClick={() => setTab('after')}>Sau chuyến đi</button>
        </nav>
        {tab === 'trip' ? (
          <div className="trip">
            <Chat messages={messages} loading={loading} onSend={send} />
            <section className="map-col">
              <MapView center={config.center} plan={plan} onSelect={setSelectedPoi} />
              {selectedPoi && <PoiCard poiId={selectedPoi} lang={lang} />}
            </section>
          </div>
        ) : (
          <AfterTrip sessionId={sessionId} plan={plan} lang={lang} />
        )}
      </main>
    </div>
  )
}
