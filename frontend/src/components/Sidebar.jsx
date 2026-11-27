import Button from "@mui/material/Button";
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
}) {
  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-top">
        <div className="sidebar-actions">
          <Button
            type="button"
            variant="contained"
            className="new-chat"
            onClick={onReset}
            title="Cuộc trò chuyện mới"
          >
            <Icon name="plus" />
            <span className="sidebar-label">Cuộc trò chuyện mới</span>
          </Button>
          <Button
            type="button"
            className="icon-button collapse-button"
            onClick={onCollapse}
            aria-label={collapsed ? "Mở thanh bên" : "Thu gọn thanh bên"}
          >
            <Icon name="panel" />
          </Button>
        </div>
        <nav aria-label="Các màn hình xem trước">
          <p className="nav-label sidebar-label">HÔM NAY</p>
          <Button
            type="button"
            className={`session ${!preview ? "active" : ""}`}
            onClick={onReset}
            title="Phiên mới"
          >
            <Icon name="chat" />
            <span className="sidebar-label">Phiên mới</span>
          </Button>
          <Button
            type="button"
            className={`session ${preview ? "active" : ""}`}
            onClick={onPreview}
            title="Một ngày khám phá Hà Nội — mẫu"
          >
            <Icon />
            <span className="sidebar-label">
              Một ngày khám phá Hà Nội<small>Bản xem trước thiết kế</small>
            </span>
          </Button>
        </nav>
        <label className="date-control sidebar-label">
          Ngày khám phá
          <input
            type="date"
            value={date}
            onChange={(e) => onDate(e.target.value)}
          />
        </label>
        <div className="sidebar-note sidebar-label">
          Một hành trình, nhiều điều để khám phá.
        </div>
      </div>
      <div className="sidebar-bottom">
        <Button
          type="button"
          className="session"
          onClick={onHelp}
          title="Trợ giúp"
        >
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
