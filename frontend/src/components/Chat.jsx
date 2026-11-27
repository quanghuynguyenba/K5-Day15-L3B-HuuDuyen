import Button from "@mui/material/Button";
import InputBase from "@mui/material/InputBase";
import { useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";
const starters = [
  [
    "museum",
    "Di sản & ẩm thực",
    "2 người · 08:00–17:00 · 1 triệu",
    "2 người, 1 triệu, đi từ 08:00 đến 17:00 ở Hà Nội, thích lịch sử và ẩm thực",
  ],
  [
    "food",
    "Food tour phố cổ",
    "Phở, bún chả, cà phê trứng",
    "Lên lịch food tour phố cổ cho 2 người, ngân sách 1 triệu",
  ],
  [
    "cloud",
    "Lịch trình tránh mưa",
    "Bảo tàng & quán trong nhà",
    "Gợi ý lịch trình trong nhà ở Hà Nội cho 2 người, ngân sách 1 triệu",
  ],
  [
    "family",
    "Cuối tuần gia đình",
    "Nhịp độ nhẹ, ít đi bộ xa",
    "Gia đình 4 người khám phá Hà Nội, ngân sách 2 triệu, ưu tiên ít đi bộ",
  ],
];
const money = (n) => Number(n || 0).toLocaleString("vi-VN") + "đ";
export default function Chat({
  messages,
  loading,
  onSend,
  plan,
  preview,
  selectedPoi,
  onSelect,
  error,
  onRetry,
}) {
  const [text, setText] = useState("");
  const [awayFromBottom, setAwayFromBottom] = useState(false);
  const [hasNewReply, setHasNewReply] = useState(false);
  const [slow, setSlow] = useState(false);
  const listRef = useRef(null);
  const inputRef = useRef(null);
  const follow = useRef(!preview);
  const previousCount = useRef(messages.length);
  function scrollToLatest(behavior = "smooth") {
    const el = listRef.current;
    if (!el) return;
    el.scrollTo({
      top: el.scrollHeight,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : behavior,
    });
    follow.current = true;
    setAwayFromBottom(false);
    setHasNewReply(false);
  }
  function trackScroll() {
    const el = listRef.current;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 90;
    follow.current = nearBottom;
    setAwayFromBottom(!nearBottom);
    if (nearBottom) setHasNewReply(false);
  }
  useEffect(() => {
    const added = messages.length > previousCount.current;
    previousCount.current = messages.length;
    if (follow.current && !preview) scrollToLatest();
    else if (added) setHasNewReply(true);
  }, [messages, loading, plan, error, preview]);
  useEffect(() => {
    if (!loading) {
      setSlow(false);
      return;
    }
    const timer = setTimeout(() => setSlow(true), 12000);
    return () => clearTimeout(timer);
  }, [loading]);
  function fillPrompt(prompt) {
    setText(prompt);
    inputRef.current?.focus();
  }
  function submit(e) {
    e.preventDefault();
    if (text.trim() && !loading) {
      follow.current = true;
      setHasNewReply(false);
      onSend(text.trim());
      setText("");
      inputRef.current?.focus();
    }
  }
  return (
    <section className="chat" aria-label="Trợ lý hành trình">
      <div className="chat-header">
        <div className="bot-avatar">
          <Icon />
        </div>
        <div>
          <h2>Trợ lý hành trình</h2>
          <p>
            {preview
              ? "Hành trình mẫu · Dữ liệu minh họa"
              : "Sẵn sàng lên lịch trình Hà Nội cho bạn"}
          </p>
        </div>
        <span
          className={`ready-dot ${loading ? "busy" : ""}`}
          title={loading ? "Đang xử lý" : "Sẵn sàng"}
        />
      </div>
      <div
        ref={listRef}
        onScroll={trackScroll}
        className={`messages ${!messages.length ? "empty-messages" : ""}`}
        aria-label="Nội dung cuộc trò chuyện"
        aria-busy={loading}
      >
        {!messages.length ? (
          <div className="welcome">
            <div className="welcome-icon">
              <Icon name="museum" size={28} />
            </div>
            <span className="eyebrow">HÀ NỘI THEO CÁCH CỦA BẠN</span>
            <h1>Xin chào! Hôm nay bạn muốn khám phá Hà Nội thế nào?</h1>
            <p>
              Hãy cho mình biết số người, thời gian, ngân sách hoặc sở thích của
              bạn để mình gợi ý tuyến đường trên bản đồ.
            </p>
            <div className="starter-grid">
              {starters.map(([icon, title, sub, prompt]) => (
                <Button
                  type="button"
                  key={title}
                  onClick={() => fillPrompt(prompt)}
                  aria-label={`Điền gợi ý: ${title}`}
                >
                  <Icon name={icon} />
                  <strong>{title}</strong>
                  <span>{sub}</span>
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                {m.role === "assistant" && (
                  <span className="message-author">
                    <Icon size={16} /> Hanoi Travel AI
                  </span>
                )}
                {m.content}
              </div>
            ))}
            {plan && (
              <div className="itinerary">
                <div className="trip-overview">
                  <span className="eyebrow">HÀNH TRÌNH CỦA BẠN</span>
                  <h3>Một ngày khám phá Hà Nội</h3>
                  <div>
                    <span>
                      <Icon name="pin" size={15} />
                      {plan.stops.length} điểm
                    </span>
                    <span>
                      <Icon name="clock" size={15} />
                      {plan.total_minutes} phút
                    </span>
                    <strong>{money(plan.total_cost)}</strong>
                  </div>
                </div>
                <div className="timeline">
                  {plan.stops.map((s, i) => (
                    <article
                      key={s.poi_id}
                      className={`stop-card ${selectedPoi === s.poi_id ? "selected" : ""}`}
                    >
                      <span className="stop-number">{i + 1}</span>
                      <div className="stop-content">
                        <span className="stop-time">
                          {s.arrive} – {s.depart}
                        </span>
                        <h3>{s.name?.vi || s.poi_id}</h3>
                        <p>
                          {s.description_vi ||
                            "Khám phá điểm dừng trong hành trình của bạn."}
                        </p>
                        <div className="stop-footer">
                          <span>{money(s.cost)}</span>
                          <Button
                            type="button"
                            onClick={() => onSelect(s.poi_id)}
                          >
                            <Icon name="pin" size={15} />
                            Xem trên bản đồ
                          </Button>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
        {loading && (
          <div className="msg assistant typing" role="status">
            <span className="loading-dots" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            <div>
              <strong>Đang lên lịch trình cho bạn</strong>
              <p>
                {slow
                  ? "Yêu cầu đang mất nhiều thời gian hơn thường lệ. Bạn có thể tiếp tục soạn tin nhắn."
                  : "Mình đang xem xét yêu cầu và các điểm đến phù hợp…"}
              </p>
            </div>
          </div>
        )}
        {error && (
          <div className="chat-error" role="alert">
            <strong>Chưa nhận được phản hồi</strong>
            <p>{error.message}</p>
            <Button type="button" onClick={onRetry} disabled={loading}>
              Thử lại yêu cầu
            </Button>
            <span>Bạn cũng có thể sửa nội dung và gửi yêu cầu mới.</span>
          </div>
        )}
      </div>
      {awayFromBottom && (
        <div className="latest-reply">
          <Button type="button" onClick={() => scrollToLatest()}>
            {hasNewReply
              ? "Có phản hồi mới · Xem ngay"
              : "Về tin nhắn mới nhất"}
          </Button>
        </div>
      )}
      <div className="composer">
        {!!messages.length && (
          <div className="quick-actions">
            {["Giảm ngân sách", "Ưu tiên trong nhà", "Tôi đang trễ giờ"].map(
              (t) => (
                <Button type="button" key={t} onClick={() => fillPrompt(t)}>
                  {t}
                </Button>
              ),
            )}
          </div>
        )}
        <form onSubmit={submit}>
          <InputBase
            inputRef={inputRef}
            multiline
            minRows={1}
            maxRows={6}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Bạn muốn khám phá Hà Nội như thế nào?"
            slotProps={{
              input: {
                "aria-label": "Nhập yêu cầu du lịch",
                "aria-describedby": "composer-hint",
              },
            }}
            onKeyDown={(e) => {
              if (
                e.key === "Enter" &&
                !e.shiftKey &&
                !e.nativeEvent.isComposing
              )
                submit(e);
            }}
          />
          <Button
            type="submit"
            variant="contained"
            disabled={loading || !text.trim()}
            aria-label={loading ? "Đang chờ phản hồi" : "Gửi tin nhắn"}
            title={
              loading
                ? "Chờ phản hồi trước khi gửi tin tiếp theo"
                : "Gửi tin nhắn (Enter)"
            }
          >
            <Icon name="send" size={18} />
          </Button>
        </form>
        <div id="composer-hint" className="composer-hint">
          <span>
            {loading
              ? "Bạn có thể soạn trước tin nhắn tiếp theo"
              : "Enter để gửi · Shift + Enter để xuống dòng"}
          </span>
          <span>{text.trim().length ? `${text.length} ký tự` : ""}</span>
        </div>
        <p>
          {preview
            ? "Đang xem mẫu. Gửi tin nhắn sẽ bắt đầu cuộc trò chuyện qua API."
            : "Giá và giờ mở cửa cần được kiểm tra trước chuyến đi"}
        </p>
      </div>
    </section>
  );
}
