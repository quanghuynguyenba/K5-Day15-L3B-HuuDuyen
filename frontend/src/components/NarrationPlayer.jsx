import { useEffect, useRef, useState } from "react";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import PauseRounded from "@mui/icons-material/PauseRounded";
import PlayArrowRounded from "@mui/icons-material/PlayArrowRounded";

const timestamp = (value) => {
  const seconds = Number.isFinite(value) ? Math.floor(value) : 0;
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
};

export default function NarrationPlayer({ narration, onClose, onRetry }) {
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [failed, setFailed] = useState(false);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  useEffect(() => {
    setPlaying(false);
    setFailed(false);
    setPosition(0);
    setDuration(0);
    const audio = audioRef.current;
    if (!audio || !narration?.audio_url) return;
    audio.play()?.catch(() => setPlaying(false));
    return () => audio.pause();
  }, [narration?.audio_url]);
  if (!narration) return null;
  const unavailable = !narration.audio_url || failed || narration.error;
  const label = narration.loading
    ? "Đang tạo audio…"
    : unavailable
      ? "Chưa có audio"
      : playing
        ? "Đang phát thuyết minh"
        : "Nghe thuyết minh";
  function toggle() {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) audio.pause();
    else audio.play()?.catch(() => setFailed(true));
  }
  return (
    <section
      className="narration-player compact-audio"
      aria-label="Trình phát thuyết minh"
    >
      {narration.audio_url && (
        <audio
          ref={audioRef}
          src={narration.audio_url}
          preload="metadata"
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onEnded={() => setPlaying(false)}
          onError={() => {
            setFailed(true);
            setPlaying(false);
          }}
          onTimeUpdate={(event) => setPosition(event.currentTarget.currentTime)}
          onLoadedMetadata={(event) =>
            setDuration(event.currentTarget.duration)
          }
        />
      )}
      <IconButton
        className="audio-toggle"
        onClick={toggle}
        disabled={!!unavailable || narration.loading}
        aria-label={playing ? "Tạm dừng thuyết minh" : "Phát thuyết minh"}
      >
        {playing ? <PauseRounded /> : <PlayArrowRounded />}
      </IconButton>
      <div className="audio-main">
        <div className="audio-label-row">
          <span role="status" title={label}>
            {label}
          </span>
          <time>
            {timestamp(position)} / {timestamp(duration)}
          </time>
        </div>
        <input
          className="audio-progress"
          type="range"
          min="0"
          max={duration || 1}
          step="0.1"
          value={Math.min(position, duration || 1)}
          disabled={!!unavailable || !duration}
          aria-label="Tua thuyết minh"
          onChange={(event) => {
            const value = Number(event.target.value);
            if (audioRef.current) audioRef.current.currentTime = value;
            setPosition(value);
          }}
          style={{
            "--audio-progress": `${duration ? (position / duration) * 100 : 0}%`,
          }}
        />
      </div>
      <span className="audio-language">{narration.lang?.toUpperCase()}</span>
      {unavailable && !narration.loading && narration.source !== "preview" && (
        <Button className="audio-retry" onClick={onRetry}>
          Thử lại
        </Button>
      )}
    </section>
  );
}
