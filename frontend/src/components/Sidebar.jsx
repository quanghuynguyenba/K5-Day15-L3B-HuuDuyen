import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import ViewSidebarOutlined from "@mui/icons-material/ViewSidebarOutlined";
import Icon from "./Icon.jsx";

function dayGroup(createdAt) {
  const day = new Date(createdAt);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  return day.toDateString() === today.toDateString()
    ? "Hôm nay"
    : day.toDateString() === yesterday.toDateString()
      ? "Hôm qua"
      : "Trước đó";
}
function SessionRow({ title, active, onClick, hint }) {
  return (
    <Button
      className={`session ${active ? "active" : ""}`}
      onClick={onClick}
      title={hint || title}
      aria-current={active ? "page" : undefined}
    >
      <Icon name="chat" size={18} />
      <span className="sidebar-label session-title">{title}</span>
    </Button>
  );
}

export default function Sidebar({
  collapsed,
  onCollapse,
  onReset,
  preview,
  sessions = [],
  activeId,
  onSwitch,
  onClose,
}) {
  const visibleSessions = sessions;
  const groups = ["Hôm nay", "Hôm qua", "Trước đó"];
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
            <Icon name="plus" size={20} />
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
            {onClose ? (
              <Icon name="close" size={18} />
            ) : (
              <ViewSidebarOutlined sx={{ fontSize: 18 }} />
            )}
          </IconButton>
        </div>
        <nav className="session-list" aria-label="Danh sách phiên chat">
          {groups.map((group) => {
            const rows = visibleSessions.filter(
              (session) => dayGroup(session.createdAt) === group,
            );
            if (!rows.length) return null;
            return (
              <section className="session-group" key={group}>
                <p className="nav-label sidebar-label">{group}</p>
                {rows.map((session) => (
                  <SessionRow
                    key={session.id}
                    title={session.title}
                    active={!preview && session.id === activeId}
                    onClick={() => onSwitch(session.id)}
                    hint={`${session.title}${session.loading ? " · Đang trả lời…" : session.error ? " · Cần thử lại" : ""}`}
                  />
                ))}
              </section>
            );
          })}
        </nav>
      </div>
      <div className="sidebar-bottom">
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
