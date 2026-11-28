import useChatSessions from "./hooks/useChatSessions.js";
import useDesktopDensity from "./hooks/useDesktopDensity.js";
import Drawer from "@mui/material/Drawer";
import useMediaQuery from "@mui/material/useMediaQuery";
import Header from "./components/Header.jsx";
import Button from "@mui/material/Button";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import Sidebar from "./components/Sidebar.jsx";
import Chat from "./components/Chat.jsx";
import PoiCard from "./components/PoiCard.jsx";
import AfterTrip from "./components/AfterTrip.jsx";
import Icon from "./components/Icon.jsx";
import { previewMessages, previewPlan, previewStops } from "./preview.js";
import useNarration from "./hooks/useNarration.js";
import NarrationPlayer from "./components/NarrationPlayer.jsx";
import usePoiCatalogue from "./hooks/usePoiCatalogue.js";
import useGeolocation from "./hooks/useGeolocation.js";

const MapView = lazy(() => import("./components/MapView.jsx"));
const PoiExplorer = lazy(() => import("./components/PoiExplorer.jsx"));

export default function App() {
  const density = useDesktopDensity();
  const sessionStore = useChatSessions();
  const geo = useGeolocation(); // vị trí hiện tại → gửi kèm chat, hiện trên bản đồ
  const patchSession = sessionStore.patch;
  const catalogue = usePoiCatalogue();
  const [explorerOpen, setExplorerOpen] = useState(false);
  const [preview, setPreview] = useState(false);
  const [previewView, setPreviewView] = useState({
    selectedPoi: "hn_001",
    selection: null,
    tab: "trip",
    mobilePane: "chat",
    draft: "",
  });
  const {
    id: sessionId,
    lang,
    date,
    messages,
    plan,
    selectedPoi: sessionPoi,
    selection: sessionSelection,
    tab: sessionTab,
    mobilePane: sessionPane,
    weather,
    loading,
    error: chatError,
    draft: sessionDraft,
  } = sessionStore.active;
  const setLang = (value) => sessionStore.setField("lang", value);
  const setDate = (value) => sessionStore.setField("date", value);
  const selectedPoi = preview ? previewView.selectedPoi : sessionPoi;
  const selection = preview ? previewView.selection : sessionSelection;
  const tab = preview ? previewView.tab : sessionTab;
  const mobilePane = preview ? previewView.mobilePane : sessionPane;
  const chatDraft = preview ? previewView.draft : sessionDraft;
  const setViewField = (name, value) =>
    preview
      ? setPreviewView((current) => ({
          ...current,
          [name]: typeof value === "function" ? value(current[name]) : value,
        }))
      : sessionStore.setField(name, value);
  const setSelectedPoi = (value) => setViewField("selectedPoi", value);
  const setSelection = (value) => setViewField("selection", value);
  const setTab = (value) => setViewField("tab", value);
  const setMobilePane = (value) => setViewField("mobilePane", value);
  const setChatDraft = (value) => setViewField("draft", value);
  const compact = useMediaQuery("(max-width:1100px)");
  // Chỉ ≤800px mới tách tab Trò chuyện / Bản đồ; 801–1100px popup và chat hiện cùng lúc
  const phone = useMediaQuery("(max-width:800px)");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const poiPanelRef = useRef(null);
  useEffect(() => {
    if (compact && mobilePane === "map" && selectedPoi)
      poiPanelRef.current?.focus({ preventScroll: true });
  }, [compact, mobilePane, selectedPoi]);
  const [config, setConfig] = useState({
    mock: true,
    langs: ["vi", "en", "ko", "ja", "zh"],
    center: [21.0285, 105.8542],
  });
  const [routeViewKey, setRouteViewKey] = useState(0);
  const [collapsed, setCollapsed] = useState(false);
  const [notice, setNotice] = useState("");
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
    patchSession(sessionId, { weather: null });
    api
      .weather(date)
      .then((w) => {
        if (active) patchSession(sessionId, { weather: w });
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [date, sessionId, patchSession]);
  const shownPlan = preview ? previewPlan : plan;
  const {
    narration,
    listen,
    close: closeNarration,
  } = useNarration({ lang, preview, stops: shownPlan?.stops, sessionId });
  function select(id, source = "chat") {
    setSelectedPoi(id);
    setSelection((previous) => ({
      source,
      version: (previous?.version || 0) + 1,
    }));
    if (source === "chat") setMobilePane("map");
  }
  function showInChat(id) {
    select(id, "map");
    setMobilePane("chat");
  }
  function showRoute() {
    setSelectedPoi(null);
    setSelection(null);
    setRouteViewKey((value) => value + 1);
    setMobilePane("map");
  }
  function narrate(id) {
    setSelectedPoi(id);
    listen(id);
  }
  // Đóng popup địa điểm = dừng hẳn việc tạo thuyết minh đang chạy (huỷ request, backend bỏ bước TTS)
  // Đóng popup địa điểm = dừng hẳn thuyết minh: đang tạo thì huỷ request, đang phát thì dừng phát
  // (không chuyển xuống trình phát ở cuối màn hình để phát tiếp).
  function closePoi() {
    closeNarration();
    setSelectedPoi(null);
  }
  function showPreview() {
    closeNarration();
    setPreviewView({
      selectedPoi: "hn_001",
      selection: null,
      tab: "trip",
      mobilePane: "chat",
      draft: "",
    });
    setPreview(true);
    setDrawerOpen(false);
  }
  function send(text, retry = false) {
    closeNarration();
    const targetId = preview ? sessionStore.createSession() : sessionId;
    setPreview(false);
    return sessionStore.send(text, retry, targetId, geo.location);
  }
  function reset() {
    closeNarration();
    sessionStore.createSession();
    setPreview(false);
    setDrawerOpen(false);
  }
  function switchSession(id) {
    closeNarration();
    sessionStore.switchSession(id);
    setPreview(false);
    setDrawerOpen(false);
  }
  function chooseCataloguePoi(id) {
    setPreview(false);
    sessionStore.setField("selectedPoi", id);
    sessionStore.setField("selection", (previous) => ({
      source: "catalogue",
      version: (previous?.version || 0) + 1,
    }));
    sessionStore.setField("mobilePane", "map");
    sessionStore.setField("tab", "trip");
    setExplorerOpen(false);
  }
  const sidebar = (
    <Sidebar
      collapsed={!compact && collapsed}
      onCollapse={() => setCollapsed(!collapsed)}
      onReset={reset}
      preview={preview}
      sessions={sessionStore.sessions}
      activeId={sessionId}
      onSwitch={switchSession}
      onClose={compact ? () => setDrawerOpen(false) : undefined}
    />
  );
  return (
    <div className="app-shell" style={{ "--desktop-density": density }}>
      <Header
        onOpenSidebar={compact ? () => setDrawerOpen(true) : undefined}
        langs={config.langs}
        lang={lang}
        onLangChange={setLang}
        weather={weather}
        preview={preview}
        geo={geo}
      />
      <div className="workspace">
        {compact ? (
          <Drawer
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            slotProps={{ paper: { className: "session-drawer" } }}
          >
            {sidebar}
          </Drawer>
        ) : (
          sidebar
        )}
        <main>
          <details className="workspace-options">
            <summary>Tùy chọn</summary>
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
                      ? "POI từ API · Agent mô phỏng"
                      : "POI từ API · LLM thật"}
                </span>
                <Button
                  type="button"
                  onClick={preview ? () => setPreview(false) : showPreview}
                >
                  {preview ? "Về phiên mới" : "Hành trình mẫu"}
                </Button>
              </div>
            </div>
          </details>
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
                      onSelect={(id) => select(id, "map")}
                      selectedPoi={selectedPoi}
                      selection={selection}
                      routeViewKey={routeViewKey}
                      onShowRoute={showRoute}
                      userLocation={preview ? null : geo.location}
                      catalogue={preview ? [] : catalogue.pois}
                      onBrowse={
                        preview ? undefined : () => setExplorerOpen(true)
                      }
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
                      ) : preview ? (
                        "Tuyến đường sẽ hiển thị sau khi bạn chọn lịch trình"
                      ) : catalogue.loading ? (
                        "Đang tải địa điểm từ API…"
                      ) : catalogue.error ? (
                        "Chưa tải được địa điểm từ API"
                      ) : (
                        `${catalogue.pois.length} địa điểm có nguồn · ${catalogue.pois.filter((poi) => poi.schedulable).length} đủ thông tin lập lịch`
                      )}
                    </span>
                  </div>
                  {preview && (
                    <div className="map-sample-label">
                      Tuyến minh họa · Không phải chỉ dẫn đường
                    </div>
                  )}
                  {selectedPoi && (
                    <div
                      className="poi-overlay"
                      ref={poiPanelRef}
                      tabIndex={-1}
                      role="dialog"
                      aria-modal="false"
                      aria-label="Thông tin địa điểm"
                      onKeyDown={(event) => {
                        if (event.key === "Escape") closePoi();
                      }}
                    >
                      <span className="sheet-handle" aria-hidden="true" />
                      <Button
                        type="button"
                        className="icon-button close-poi"
                        onClick={closePoi}
                        aria-label="Đóng thông tin địa điểm"
                      >
                        <Icon name="close" size={16} />
                      </Button>
                      <PoiCard
                        key={`${preview}-${selectedPoi}-${lang}`}
                        poiId={selectedPoi}
                        lang={lang}
                        onNarrate={narrate}
                        narration={narration}
                        stopNumber={
                          shownPlan?.stops?.findIndex(
                            (item) => item.poi_id === selectedPoi,
                          ) >= 0
                            ? shownPlan.stops.findIndex(
                                (item) => item.poi_id === selectedPoi,
                              ) + 1
                            : undefined
                        }
                        stop={shownPlan?.stops?.find(
                          (item) => item.poi_id === selectedPoi,
                        )}
                        onShowInChat={
                          shownPlan?.stops?.some(
                            (item) => item.poi_id === selectedPoi,
                          )
                            ? () => showInChat(selectedPoi)
                            : undefined
                        }
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
                  date={date}
                  onDate={setDate}
                  onBrowse={preview ? undefined : () => setExplorerOpen(true)}
                  poiCount={catalogue.pois.length}
                  draft={chatDraft}
                  onDraftChange={setChatDraft}
                  error={chatError}
                  onRetry={() => chatError && send(chatError.text, true)}
                  plan={shownPlan}
                  preview={preview}
                  selectedPoi={selectedPoi}
                  onSelect={select}
                  selection={selection}
                  onShowRoute={showRoute}
                  onNarrate={narrate}
                  narration={narration}
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
          {/* Trình phát dưới cùng chỉ hiện khi popup KHÔNG đang hiện cùng thuyết minh đó —
              tránh 2 thẻ <audio> cùng phát (lỗi ở màn 801–1100px) */}
          {!(
            tab === "trip" &&
            selectedPoi &&
            narration?.poiId === selectedPoi &&
            (mobilePane === "map" || !phone)
          ) && (
            <NarrationPlayer
              key={`${narration?.poiId}-${narration?.lang}-${narration?.audio_url}`}
              narration={narration}
              onRetry={() => listen(narration.poiId)}
            />
          )}
        </main>
      </div>
      {explorerOpen && (
        <Suspense
          fallback={
            <div className="notice" role="status">
              Đang mở danh sách địa điểm…
            </div>
          }
        >
          <PoiExplorer
            open={explorerOpen}
            onClose={() => setExplorerOpen(false)}
            catalogue={catalogue}
            onSelect={chooseCataloguePoi}
          />
        </Suspense>
      )}
    </div>
  );
}
