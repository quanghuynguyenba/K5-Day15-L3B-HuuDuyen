import { useMemo, useState } from "react";
import Drawer from "@mui/material/Drawer";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import MenuItem from "@mui/material/MenuItem";
import Icon from "./Icon.jsx";
import { formatMoney } from "../utils/itinerary.js";

const CATEGORIES = {
  history: "Lịch sử",
  museum: "Bảo tàng",
  food: "Ẩm thực",
  cafe: "Cà phê",
  nature: "Thiên nhiên",
  shopping: "Mua sắm",
  night: "Buổi tối",
  art: "Nghệ thuật",
};
const normalize = (text) =>
  String(text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/đ/g, "d");

export default function PoiExplorer({ open, onClose, catalogue, onSelect }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [indoor, setIndoor] = useState(false);
  const [readyOnly, setReadyOnly] = useState(false);
  const pois = useMemo(
    () =>
      catalogue.pois.filter(
        (poi) =>
          (!category || category === "all" || poi.category === category) &&
          (!indoor || poi.indoor === true) &&
          (!readyOnly || poi.schedulable === true) &&
          normalize(`${poi.name.vi} ${poi.name.en}`).includes(normalize(query)),
      ),
    [catalogue.pois, query, category, indoor, readyOnly],
  );
  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      slotProps={{ paper: { className: "poi-explorer" } }}
    >
      <div className="explorer-heading">
        <div>
          <span className="eyebrow">ĐỊA ĐIỂM TỪ API</span>
          <h2>Khám phá Hà Nội</h2>
        </div>
        <Button aria-label="Đóng danh sách địa điểm" onClick={onClose}>
          <Icon name="close" />
        </Button>
      </div>
      <p className="explorer-intro">
        {catalogue.pois.length} địa điểm ·{" "}
        {catalogue.pois.filter((poi) => poi.schedulable).length} điểm đủ giá/giờ
        để lập lịch. Dữ liệu có nguồn do nhóm tổng hợp; xem lưu ý tại từng điểm.
      </p>
      <div className="explorer-filters">
        <TextField
          size="small"
          label="Tìm tên địa điểm"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          fullWidth
        />
        <TextField
          select
          size="small"
          label="Loại địa điểm"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          fullWidth
        >
          <MenuItem value="all">Tất cả</MenuItem>
          {Object.entries(CATEGORIES).map(([value, label]) => (
            <MenuItem key={value} value={value}>
              {label}
            </MenuItem>
          ))}
        </TextField>
        <FormControlLabel
          control={
            <Checkbox
              checked={indoor}
              onChange={(event) => setIndoor(event.target.checked)}
            />
          }
          label="Chỉ điểm trong nhà"
        />
        <FormControlLabel
          control={
            <Checkbox
              checked={readyOnly}
              onChange={(event) => setReadyOnly(event.target.checked)}
            />
          }
          label="Đủ thông tin để lập lịch"
        />
      </div>
      {catalogue.loading ? (
        <p role="status" className="explorer-status">
          Đang tải địa điểm từ máy chủ…
        </p>
      ) : catalogue.error ? (
        <div role="alert" className="explorer-status">
          <p>{catalogue.error}</p>
          <Button onClick={catalogue.retry}>Thử tải lại</Button>
        </div>
      ) : (
        <>
          <p className="explorer-count">{pois.length} kết quả</p>
          <div className="explorer-results">
            {pois.length ? (
              pois.map((poi) => (
                <Button
                  key={poi.id}
                  className="explorer-poi"
                  onClick={() => onSelect(poi.id)}
                >
                  <span className="explorer-poi-icon">
                    <Icon name={poi.category === "food" ? "food" : "pin"} />
                  </span>
                  <span>
                    <strong>{poi.name.vi}</strong>
                    <small>
                      {CATEGORIES[poi.category] || poi.category} ·{" "}
                      {formatMoney(poi.price_vnd)}
                    </small>
                    <small>
                      {poi.schedulable
                        ? "Đủ thông tin lập lịch"
                        : "Chỉ xem thông tin · Thiếu giá hoặc giờ mở cửa"}
                    </small>
                  </span>
                </Button>
              ))
            ) : (
              <p className="hint">
                Không có điểm phù hợp. Thử bỏ bớt bộ lọc hoặc đổi từ khóa.
              </p>
            )}
          </div>
        </>
      )}
    </Drawer>
  );
}
