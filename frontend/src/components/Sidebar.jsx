import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Icon from "./Icon.jsx";

export default function Sidebar({
  collapsed,
  onCollapse,
  onReset,
  onPreview,
  preview,
  date,
  onDate,
  onHelp,
  sessions = [],
  activeId,
  onSwitch,
  onClose,
}) {
  return (
    <aside
      className={`sidebar ${collapsed ? "collapsed" : ""}`}
      aria-label="Quản lý phiên chat"
    >
      <div className="sidebar-top">
        <div className="sidebar-actions">
          <Button
            variant="contained"
            className="new-chat"
            onClick={onReset}
            title="Cuộc trò chuyện mới"
          >
            <Icon name="plus" />
            <span className="sidebar-label">Cuộc trò chuyện mới</span>
          </Button>
          <IconButton
            className="icon-button collapse-button"
            onClick={onClose || onCollapse}
            aria-label={
              onClose
                ? "Đóng danh sách phiên chat"
                : collapsed
                  ? "Mở thanh bên"
                  : "Thu gọn thanh bên"
            }
          >
            <Icon name={onClose ? "close" : "panel"} />
          </IconButton>
        </div>
        <nav aria-label="Danh sách phiên chat">
          <p className="nav-label sidebar-label">
            PHIÊN HIỆN TẠI · {sessions.length}
          </p>
          <div className="session-list">
            {sessions.map((session) => (
              <Button
                key={session.id}
                className={`session ${!preview && activeId === session.id ? "active" : ""}`}
                onClick={() => onSwitch(session.id)}
                title={session.title}
                aria-current={
                  !preview && activeId === session.id ? "page" : undefined
                }
              >
                <Icon name="chat" />
                <span className="sidebar-label session-title">
                  {session.title}
                  <small>
                    {session.loading
                      ? "Đang trả lời…"
                      : session.error
                        ? "Cần thử lại"
                        : session.plan
                          ? `${session.plan.stops?.length || 0} điểm dừng`
                          : session.messages.length
                            ? `${session.messages.length} tin nhắn`
                            : "Bắt đầu hành trình mới"}
                  </small>
                </span>
              </Button>
            ))}
          </div>
        </nav>
        <div className="preview-session">
          <p className="nav-label sidebar-label">KHÁM PHÁ GIAO DIỆN</p>
          <Button
            className={`session ${preview ? "active" : ""}`}
            onClick={onPreview}
            title="Hành trình mẫu"
          >
            <Icon />
            <span className="sidebar-label">
              Một ngày khám phá Hà Nội<small>Dữ liệu minh họa</small>
            </span>
          </Button>
        </div>
        <label className="date-control sidebar-label">
          Ngày đi
          <input
            type="date"
            value={date}
            onChange={(event) => onDate(event.target.value)}
          />
        </label>
        <p className="sidebar-note sidebar-label">
          Các phiên chỉ được giữ trong lần mở trang này.
        </p>
      </div>
      <div className="sidebar-bottom">
        <Button className="session" onClick={onHelp} title="Trợ giúp">
          <Icon name="help" />
          <span className="sidebar-label">Trợ giúp</span>
        </Button>
        <div className="user-profile">
          <div className="avatar">K</div>
          <div className="sidebar-label">
            <strong>Khách khám phá</strong>
            <small>Du khách · Hà Nội</small>
          </div>
        </div>
      </div>
    </aside>
  );
}
