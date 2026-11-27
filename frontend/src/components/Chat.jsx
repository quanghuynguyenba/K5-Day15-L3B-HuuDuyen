import { useEffect, useRef, useState } from 'react'

export default function Chat({ messages, loading, onSend }) {
  const [text, setText] = useState('')
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  function submit(e) {
    e.preventDefault()
    const t = text.trim()
    if (!t || loading) return
    onSend(t)
    setText('')
  }

  return (
    <section className="chat">
      <div className="messages">
        {messages.length === 0 && (
          <p className="hint">Vd: “2 người, 1 triệu, đi 1 ngày ở Hà Nội, thích lịch sử và ẩm thực”</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>{m.content}</div>
        ))}
        {loading && <div className="msg assistant typing">Đang lập lịch…</div>}
        <div ref={endRef} />
      </div>
      <form onSubmit={submit}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Nhập yêu cầu…" />
        <button disabled={loading || !text.trim()}>Gửi</button>
      </form>
    </section>
  )
}
