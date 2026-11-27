import ItineraryTimeline from "./ItineraryTimeline.jsx";
import Button from "@mui/material/Button";
import ChatWelcome from "./ChatWelcome.jsx";
import ChatComposer from "./ChatComposer.jsx";
import useChatScroll from "../hooks/useChatScroll.js";
import { useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";
const money = (n) => Number(n || 0).toLocaleString("vi-VN") + "đ";
export default function Chat({
  messages,
  loading,
  onSend,
  plan,
  preview,
  selectedPoi,
  onSelect,
  onNarrate,
  narration,
  selection,
  onShowRoute,
  error,
  onRetry,
  draft,
  onDraftChange,
}) {
  const [localText, setLocalText] = useState("");
  const text = draft ?? localText;
  const setText = onDraftChange ?? setLocalText;
  const [slow, setSlow] = useState(false);
  const inputRef = useRef(null);
  const {
    listRef,
    contentRef,
    trackScroll,
    scrollToLatest,
    awayFromBottom,
    hasNewReply,
  } = useChatScroll({ messages, loading, plan, error, preview, selection });
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
      scrollToLatest();
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
        <div
          ref={contentRef}
          className="chat-content"
          role="log"
          aria-live="polite"
          aria-relevant="additions text"
        >
          {!messages.length ? (
            <ChatWelcome onChoose={fillPrompt} />
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
              <ItineraryTimeline
                plan={plan}
                selectedPoi={selectedPoi}
                selection={selection}
                onSelect={onSelect}
                onNarrate={onNarrate}
                narration={narration}
                onShowRoute={onShowRoute}
              />
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
              <Button
                type="button"
                onClick={() => fillPrompt(error.text || "")}
                disabled={loading}
              >
                Sửa yêu cầu
              </Button>
              <span>Bạn cũng có thể sửa nội dung và gửi yêu cầu mới.</span>
            </div>
          )}
        </div>
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
      <ChatComposer
        inputRef={inputRef}
        text={text}
        onChange={setText}
        onSubmit={submit}
        onChoose={fillPrompt}
        loading={loading}
        preview={preview}
        hasMessages={!!messages.length}
      />
    </section>
  );
}
