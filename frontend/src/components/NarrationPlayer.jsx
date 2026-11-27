import { useEffect, useRef, useState } from "react";
import Button from "@mui/material/Button";
import Icon from "./Icon.jsx";

export default function NarrationPlayer({ narration, onClose, onRetry }) {
  const [audioError, setAudioError] = useState(false);
  const [autoplayBlocked, setAutoplayBlocked] = useState(false);
  const [buffering, setBuffering] = useState(false);
  const audioRef = useRef(null);
  useEffect(() => {
    setAudioError(false);
    setAutoplayBlocked(false);
    const audio = audioRef.current;
    if (!audio || !narration?.audio_url) return;
    setBuffering(true);
    audio.play()?.catch(() => setAutoplayBlocked(true));
    return () => {
      audio.pause();
    };
  }, [narration?.audio_url]);
  if (!narration) return null;
  return (
    <section className="narration-player" aria-label="Thuyết minh địa điểm">
      <div className="narration-heading">
        <Icon name="speaker" />
        <strong>{narration.title}</strong>
        <span>{narration.lang.toUpperCase()}</span>
        <Button onClick={onClose} aria-label="Đóng thuyết minh">
          <Icon name="close" size={18} />
        </Button>
      </div>
      {narration.loading ? (
        <p role="status">Đang tạo thuyết minh…</p>
      ) : narration.error ? (
        <div role="alert">
          <span>{narration.error}</span>
          <Button onClick={onRetry}>Thử lại</Button>
        </div>
      ) : (
        <>
          {narration.audio_url && !audioError ? (
            <audio
              key={narration.audio_url}
              controls
              ref={audioRef}
              preload="metadata"
              src={narration.audio_url}
              onCanPlay={() => setBuffering(false)}
              onWaiting={() => setBuffering(true)}
              onPlaying={() => {
                setBuffering(false);
                setAutoplayBlocked(false);
              }}
              onError={() => {
                setAudioError(true);
                setBuffering(false);
              }}
            />
          ) : (
            <p className="muted">
              {audioError
                ? "Không phát được audio. Bạn có thể đọc nội dung thuyết minh bên dưới."
                : "Chưa có audio; nội dung thuyết minh được hiển thị bên dưới."}
            </p>
          )}
          {narration.audio_url && buffering && !audioError && (
            <p role="status">Đang tải audio…</p>
          )}
          {autoplayBlocked && !audioError && (
            <p role="status">Nhấn nút Phát trên trình phát để bắt đầu nghe.</p>
          )}
          {audioError && <Button onClick={onRetry}>Tạo lại audio</Button>}
          {narration.text && (
            <details>
              <summary>Đọc nội dung thuyết minh</summary>
              <p>{narration.text}</p>
            </details>
          )}
        </>
      )}
    </section>
  );
}
