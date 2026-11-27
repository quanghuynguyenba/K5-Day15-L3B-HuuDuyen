import Header from "./components/Header.jsx";
import Button from "@mui/material/Button";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { api, newSessionId } from "./api.js";
import Sidebar from "./components/Sidebar.jsx";
import Chat from "./components/Chat.jsx";
import PoiCard from "./components/PoiCard.jsx";
import AfterTrip from "./components/AfterTrip.jsx";
import Icon from "./components/Icon.jsx";
import { previewMessages, previewPlan, previewStops } from "./preview.js";

const MapView = lazy(() => import("./components/MapView.jsx"));

const tomorrow = () => {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
export default function App() {
  const [sessionId, setSessionId] = useState(newSessionId);
  const [config, setConfig] = useState({
    mock: true,
    langs: ["vi", "en", "ko", "ja", "zh"],
    center: [21.0285, 105.8542],
  });
  const [lang, setLang] = useState("vi");
  const [date, setDate] = useState(tomorrow);
  const [messages, setMessages] = useState([]);
  const [plan, setPlan] = useState(null);
  const [selectedPoi, setSelectedPoi] = useState(null);
  const [tab, setTab] = useState("trip");
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [mobilePane, setMobilePane] = useState("chat");
  const [weather, setWeather] = useState(null);
  const [notice, setNotice] = useState("");
  const [chatError, setChatError] = useState(null);
  const sending = useRef(false);
  const generation = useRef(0);
  useEffect(() => {
    api
      .config()
      .then(setConfig)
      .catch(() =>
        setNotice("API chưa kết nối. Bạn vẫn có thể xem hành trình mẫu."),
      );
  }, []);
  useEffect(() => {
    let active = true;
    setWeather(null);
    api
      .weather(date)
      .then((w) => {
        if (active) setWeather(w);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [date]);
  const shownPlan = preview ? previewPlan : plan;
  function select(id) {
    setSelectedPoi(id);
    setMobilePane("map");
  }
  function showPreview() {
    generation.current++;
    sending.current = false;
    setChatError(null);
    setLoading(false);
    setPreview(true);
    setSelectedPoi("hn_001");
    setTab("trip");
  }
  async function send(text, retry = false) {
    if (sending.current) return false;
    sending.current = true;
    const current = ++generation.current;
    const requestDate = retry ? chatError.date : date;
    const targetSession = preview ? newSessionId() : sessionId;
    if (preview) setSessionId(targetSession);
    setPreview(false);
    setSelectedPoi(null);
    setLoading(true);
    setChatError(null);
    if (preview) {
      setPlan(null);
      setMessages([{ role: "user", content: text }]);
    } else if (!retry)
      setMessages((m) => [...m, { role: "user", content: text }]);
    try {
      const res = await api.chat(targetSession, text, requestDate);
      if (current !== generation.current) return;
      if (typeof res?.reply !== "string" || !res.reply.trim())
        throw new Error(
          "Máy chủ chưa trả về nội dung phản hồi. Vui lòng thử lại.",
        );
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
      setPlan(res.plan);
      if (res.weather) setWeather(res.weather);
    } catch (e) {
      if (current === generation.current)
        setChatError({ text, date: requestDate, message: e.message });
    } finally {
      if (current === generation.current) {
        sending.current = false;
        setLoading(false);
      }
    }
    return true;
  }
  function reset() {
    generation.current++;
    sending.current = false;
    setChatError(null);
    api.reset(sessionId).catch(() => {});
    setSessionId(newSessionId());
    setMessages([]);
    setPlan(null);
    setSelectedPoi(null);
    setPreview(false);
    setLoading(false);
    setTab("trip");
    setMobilePane("chat");
  }
  return (
    <div className="app-shell">
      <Header
        langs={config.langs}
        lang={lang}
        onLangChange={setLang}
        weather={weather}
        preview={preview}
      />
      <div className="workspace">
        <Sidebar
          collapsed={collapsed}
          onCollapse={() => setCollapsed(!collapsed)}
          onReset={reset}
          onPreview={showPreview}
          preview={preview}
          date={date}
          onDate={setDate}
          onHelp={() =>
            setNotice(
              "Nhập số người, ngân sách và sở thích để bắt đầu. Chọn “Hành trình mẫu” để xem trước thiết kế mà không cần backend.",
            )
          }
        />
        <main>
          <div className="workspace-toolbar">
            <div className="view-tabs">
              <Button
                type="button"
                className={tab === "trip" ? "active" : ""}
                onClick={() => setTab("trip")}
              >
                Khám phá Hà Nội
              </Button>
              <Button
                type="button"
                className={tab === "after" ? "active" : ""}
                onClick={() => setTab("after")}
              >
                Sau chuyến đi
              </Button>
            </div>
            <div className="preview-switch">
              <span>
                {preview
                  ? "Dữ liệu minh họa"
                  : config.mock
                    ? "API · Chế độ mock"
                    : "API · Trực tiếp"}
              </span>
              <Button type="button" onClick={preview ? reset : showPreview}>
                {preview ? "Về phiên mới" : "Hành trình mẫu"}
              </Button>
            </div>
          </div>
          {notice && (
            <div className="notice" role="status">
              {notice}
              <Button
                type="button"
                className="icon-button"
                onClick={() => setNotice("")}
                aria-label="Đóng thông báo"
              >
                <Icon name="close" size={15} />
              </Button>
            </div>
          )}
          {tab === "trip" ? (
            <>
              <div className="mobile-switch">
                <Button
                  type="button"
                  className={mobilePane === "chat" ? "active" : ""}
                  onClick={() => setMobilePane("chat")}
                >
                  Trò chuyện
                </Button>
                <Button
                  type="button"
                  className={mobilePane === "map" ? "active" : ""}
                  onClick={() => setMobilePane("map")}
                >
                  Bản đồ
                </Button>
              </div>
              <div className={`trip mobile-${mobilePane}`}>
                <section className="map-col" aria-label="Bản đồ Hà Nội">
                  <Suspense
                    fallback={
                      <div className="map-loading" role="status">
                        Đang tải bản đồ Hà Nội…
                      </div>
                    }
                  >
                    <MapView
                      center={config.center}
                      plan={shownPlan}
                      onSelect={select}
                      selectedPoi={selectedPoi}
                    />
                  </Suspense>
                  <div className="map-summary">
                    <Icon name={shownPlan ? "pin" : "explore"} size={19} />
                    <span>
                      {shownPlan ? (
                        <>
                          <strong>{shownPlan.stops.length} điểm dừng</strong>
                          <span className="summary-divider">·</span>
                          {shownPlan.total_minutes} phút
                          <span className="summary-divider">·</span>
                          <strong>
                            {Number(shownPlan.total_cost).toLocaleString(
                              "vi-VN",
                            )}
                            đ
                          </strong>
                        </>
                      ) : (
                        "Tuyến đường sẽ hiển thị sau khi bạn chọn lịch trình"
                      )}
                    </span>
                  </div>
                  {preview && (
                    <div className="map-sample-label">
                      Tuyến minh họa · Không phải chỉ dẫn đường
                    </div>
                  )}
                  {selectedPoi && (
                    <div className="poi-overlay">
                      <Button
                        type="button"
                        className="icon-button close-poi"
                        onClick={() => setSelectedPoi(null)}
                        aria-label="Đóng thông tin địa điểm"
                      >
                        <Icon name="close" size={16} />
                      </Button>
                      <PoiCard
                        key={`${preview}-${selectedPoi}-${lang}`}
                        poiId={selectedPoi}
                        lang={lang}
                        previewPoi={
                          preview
                            ? previewStops.find((p) => p.poi_id === selectedPoi)
                            : null
                        }
                      />
                    </div>
                  )}
                </section>
                <Chat
                  key={preview ? "preview" : sessionId}
                  messages={preview ? previewMessages : messages}
                  loading={loading}
                  onSend={send}
                  error={chatError}
                  onRetry={() => chatError && send(chatError.text, true)}
                  plan={shownPlan}
                  preview={preview}
                  selectedPoi={selectedPoi}
                  onSelect={select}
                />
              </div>
            </>
          ) : preview ? (
            <div className="after pad">
              <span className="eyebrow">TỔNG KẾT MINH HỌA</span>
              <h1>Một ngày, năm điểm dừng đáng nhớ.</h1>
              <div className="metrics">
                <div>
                  <span>Điểm khám phá</span>
                  <b>5</b>
                </div>
                <div>
                  <span>Tổng chi mẫu</span>
                  <b>850.000đ</b>
                </div>
                <div>
                  <span>Thời gian mẫu</span>
                  <b>540 phút</b>
                </div>
              </div>
              <p>
                Đây là dữ liệu xem trước giao diện. Bắt đầu phiên mới để nhận
                tổng kết qua API.
              </p>
            </div>
          ) : (
            <AfterTrip
              key={`${sessionId}-${lang}-${JSON.stringify(plan)}`}
              sessionId={sessionId}
              plan={plan}
              lang={lang}
            />
          )}
        </main>
      </div>
    </div>
  );
}
