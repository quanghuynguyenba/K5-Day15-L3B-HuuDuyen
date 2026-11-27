import Button from "@mui/material/Button";
import InputBase from "@mui/material/InputBase";
import Icon from "./Icon.jsx";

const QUICK_ACTIONS = [
  "Giảm ngân sách",
  "Ưu tiên trong nhà",
  "Bỏ một điểm",
  "Tôi đang trễ giờ",
];

export default function ChatComposer({
  inputRef,
  text,
  onChange,
  onSubmit,
  onChoose,
  loading,
  preview,
  hasMessages,
}) {
  return (
    <div className="composer">
      {hasMessages && (
        <div className="quick-actions">
          {QUICK_ACTIONS.map((label) => (
            <Button type="button" key={label} onClick={() => onChoose(label)}>
              {label}
            </Button>
          ))}
        </div>
      )}
      <form onSubmit={onSubmit} aria-label="Soạn tin nhắn">
        <InputBase
          inputRef={inputRef}
          multiline
          minRows={1}
          maxRows={6}
          value={text}
          onChange={(e) => onChange(e.target.value)}
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
              !e.nativeEvent.isComposing &&
              e.keyCode !== 229
            ) {
              e.preventDefault();
              if (!e.repeat) onSubmit(e);
            }
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
          <span>Gửi</span>
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
  );
}
