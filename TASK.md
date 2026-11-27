# TASK.md — Hackathon #14: Hành trình du lịch cá nhân hoá

**Deadline:** 14:00 thứ 7, 28/11/2026
**Team:** Huy · Tùng · Hiếu · Cường — backend Python (FastAPI) + frontend ReactJS

> **Pitch:** Từ một câu chat, khách có ngay lịch trình tối ưu theo túi tiền & thời gian, xem trên bản đồ, nghe thuyết minh bằng tiếng mẹ đẻ.

---

## 1. Scope (đã chốt)

| # | Chức năng cốt lõi | Thách thức trong đề |
|---|---|---|
| 1 | Chatbot RAG hỏi đáp điểm đến (giờ mở cửa, giá, lưu ý) | Thông tin phân tán |
| 2 | Lập lịch trình tối ưu theo ngân sách + thời gian, hiển thị trên map | Tối ưu lộ trình & chi phí |
| 3 | Cá nhân hoá theo nhóm khách + sửa lịch trình bằng chat | Chưa có công cụ tự động, linh hoạt |
| 4 | Đa ngôn ngữ + thuyết minh audio tại từng điểm | Mong muốn: thuyết minh, đa ngôn ngữ |

**Phạm vi demo:** chỉ Hà Nội, ~50–100 POI.
**KHÔNG làm:** đặt vé, đặt phòng, thanh toán, đăng nhập, lưu lịch sử, nhiều thành phố, GraphRAG, fine-tune.
**Dịch vụ ngoài chỉ dùng:** API LLM, API map, API thời tiết (+ embedding API nếu chọn).

---

## 2. Kiến trúc & luồng xử lý

```
User chat
  └─► LLM (Huy) tách ràng buộc → JSON {budget, start, end, group_type, n_people, interests, lang}
        ├─► tool search_pois (Hiếu)   : lọc JSON + xếp hạng theo tag (MVP)
        ├─► tool plan_route  (Tùng)   : Distance Matrix + OR-Tools → lịch trình
        ├─► tool get_weather (Cường)  : Open-Meteo → mưa thì ưu tiên POI indoor
        └─► tool narrate     (Huy+Cường): RAG + LLM viết thuyết minh → TTS
  └─► FastAPI `server.py` ─► React (Cường): khung chat + map Leaflet (marker đánh số + polyline) + audio
```

Cấu trúc repo (khung đã dựng, mọi module có bản MOCK chạy được):

```
server.py              # FastAPI: /api/chat, /api/narrate, /api/summary… cho React (Cường)
frontend/              # React + Vite + react-leaflet (Cường)
  src/api.js           #   mọi lời gọi backend
  src/components/      #   Sidebar, Chat, MapView, PoiCard, AfterTrip
config.py              # đọc .env, cờ USE_MOCK, hằng số chung (cả nhóm)
agent/llm.py           # call_llm, chat(): prompt + vòng lặp tool calling, chế độ MOCK (Huy)
agent/tools.py         # TOOL_SCHEMAS, dispatch, narrate (Huy + Cường)
data/pois.json         # 50 POI; một số điểm mới chưa đủ giá/giờ cho bộ lập lịch (Hiếu)
data/build_db.py       # json → SQLite; MVP hiện đọc JSON trực tiếp (Hiếu)
rag/search.py          # search_pois, get_poi_context (Hiếu)
routing/maps.py        # TomTom: Matrix, Calculate Route, cache, fallback (Tùng)
routing/optimizer.py   # plan_route: OR-Tools → kiểm → greedy dự phòng (Tùng)
routing/ortools_solver.py # VRP 1 xe: time windows, ngân sách, disjunction (Tùng)
routing/validate.py    # validate_plan: kiểm lịch bằng code, dùng cho eval (Tùng)
routing/summary.py     # summarize_trip (Tùng)
routing/warm_cache.py  # tính sẵn ma trận TomTom cho mọi POI → data/cache/maps_cache.json (Tùng)
services/weather.py    # Open-Meteo (Cường)
services/tts.py        # edge-tts / gTTS (Cường)
audio/                 # mp3 thuyết minh pre-generate: <poi_id>_<lang>.mp3
data/cache/            # vector (không commit) + maps_cache.json (commit, để demo không cần mạng)
.env.example           # LLM_API_KEY, LLM_MODEL, LLM_BASE_URL, TOMTOM_API_KEY, (EMBED_API_KEY)
requirements.txt
```

**Chạy:**
```
python -m pip install -r requirements.txt
copy .env.example .env                       # để trống LLM_API_KEY = chạy MOCK
python -m uvicorn server:app --reload --port 8000    # terminal 1: API
cd frontend; npm install; npm run dev                # terminal 2: mở http://localhost:5173
```
Vite proxy `/api`, `/audio` sang cổng 8000, nên frontend không cần cấu hình CORS khi chạy dev.
Mỗi người thay phần MOCK trong file của mình (tìm chữ `TODO`), giữ nguyên chữ ký hàm ở mục 3.2.

---

## 3. Hợp đồng chung — CHỐT TRONG 30 PHÚT ĐẦU

Mọi người code song song theo hợp đồng này, test bằng dữ liệu giả cho đến khi phần thật xong.

### 3.1 Schema `pois.json`

```json
{
  "id": "hn_001",
  "name": {"vi": "Văn Miếu – Quốc Tử Giám", "en": "Temple of Literature"},
  "lat": 21.0294, "lng": 105.8355,
  "category": "history",
  "tags": ["culture", "architecture", "photo"],
  "indoor": false,
  "price_vnd": 70000,
  "open": "08:00", "close": "17:00",
  "closed_days": [],
  "visit_minutes": 60,
  "suitable_for": ["family", "elderly", "couple", "friends", "solo"],
  "description_vi": "…",
  "description_en": "…",
  "notes_vi": "…",
  "notes_en": "…",
  "source": "https://…"
}
```

- `closed_days`: các thứ đóng cửa, giá trị trong `mon`…`sun` (vd bảo tàng nghỉ thứ Hai → `["mon"]`). `search_pois` và `plan_route` phải loại điểm đóng cửa vào ngày đi.
- `notes_vi` / `notes_en`: lưu ý cho khách (trang phục, chỉ mở buổi sáng, cấm chụp ảnh…) — chatbot dùng để trả lời câu hỏi "lưu ý".

Category gợi ý: `history`, `museum`, `food`, `cafe`, `nature`, `shopping`, `night`, `art`.

### 3.2 Chữ ký các tool

```python
search_pois(interests: list[str], group_type: str, max_price: int,
            indoor_only: bool = False, top_k: int = 15,
            date: str | None = None) -> list[dict]      # date YYYY-MM-DD để lọc closed_days

plan_route(poi_ids: list[str], start_latlng: tuple, start_time: str,
           end_time: str, budget_vnd: int, n_people: int,
           vehicle: str = "car", date: str | None = None) -> dict
# trả về: {"stops":[{"poi_id","arrive","depart","cost"}],
#          "total_cost", "total_minutes", "polyline":[[lat,lng],...], "dropped":[poi_id]}

get_weather(date: str, lat: float, lng: float) -> dict
# {"rain_prob_by_hour": {...}, "is_rainy": bool, "temp_max": float}

narrate(poi_id: str, lang: str) -> {"text": str, "audio_path": str}

summarize_trip(plan: dict, lang: str) -> str   # plan = output của plan_route (Tùng)
```

---

## 4. Phân công

### Hiếu — Dữ liệu POI + RAG

**Checklist dữ liệu (50 POI trong `data/pois.json`, 27/11):**
- [x] JSON đọc được; có 50 ID khác nhau và đủ tên trường theo schema.
- [x] POI thiếu giá/giờ được bỏ qua khi tìm và lập lịch; phần nội dung chi tiết hiển thị “chưa có dữ liệu”.
- [x] Kiểm tra trên bộ 50 POI: 32 điểm đủ giá/giờ để lập lịch, 18 điểm thiếu dữ liệu được bỏ qua an toàn.
- [x] `search_pois` lọc theo giá, nhóm khách, trong nhà và ngày đóng cửa; xếp hạng theo tag và bỏ điểm không khớp sở thích.
- [x] `get_poi_context` trả nội dung tiếng Việt/Anh và fallback cho ngôn ngữ khác.
- [x] Smoke test trước khi mở rộng (bộ 20 POI): truy vấn bảo tàng trong nhà trả 9 POI; bộ lập lịch chọn được 7 điểm.
- [x] Đối chiếu từng giá vé, giờ mở cửa, ngày nghỉ và tọa độ với nguồn tương ứng trước khi công bố là thông tin đã xác minh.

Phạm vi MVP dùng JSON và xếp hạng theo tag; SQLite/vector/embedding được hoãn. Trong 50 POI, 32 điểm đủ giá/giờ để lập lịch; 18 điểm còn lại chỉ dùng để xem thông tin.

**Nguồn dữ liệu:**

| Dữ liệu | Nguồn | Cách lấy |
|---|---|---|
| Danh sách POI + toạ độ | OpenStreetMap qua **Overpass API** (miễn phí, không key) | API |
| Bổ sung / kiểm tra toạ độ | **TomTom Search / Geocoding** | API (dùng chung key với Tùng) |
| Mô tả, lịch sử, nội dung thuyết minh | **Wikipedia / Wikivoyage** (có sẵn vi, en, ko, ja, zh…), thư viện `wikipedia-api` | API |
| Giá vé, giờ mở cửa, thời gian tham quan | Website chính thức, trang du lịch Hà Nội | **Tự gom**: LLM tạo bản nháp, người kiểm tra lại từng điểm |
| `suitable_for`, `indoor`, `tags` | Tự gán | **Tự gom** |

→ `data/pois.json` hiện có 50 POI với URL trong `source`. Dữ liệu đã được Hiếu đối chiếu; điểm thiếu giá/giờ không được đưa vào lịch trình.

**Embedding — phương án mở rộng, chưa cần cho MVP:**

| | **A. Local** (sentence-transformers) | **B. API nhà cung cấp** |
|---|---|---|
| Model gợi ý | `BAAI/bge-m3` (chất lượng tốt nhất, ~2.2 GB) hoặc `intfloat/multilingual-e5-small` (~470 MB, nhanh) | Embedding API của OpenAI / Gemini / nhà cung cấp LLM đang dùng |
| Ưu điểm | Miễn phí, không phụ thuộc mạng/quota, dữ liệu không ra ngoài | Không tốn dung lượng, không cần GPU, cài đặt nhanh |
| Nhược điểm | **Tốn dung lượng lưu trữ** + RAM, tải model lâu, chạy CPU chậm hơn | **Có thể phải trả phí** (dù ~100 POI thì chi phí gần như không đáng kể), cần key, phụ thuộc mạng & rate limit |
| Rủi ro demo | Máy demo thiếu RAM / chưa tải model | Mất mạng hoặc hết quota lúc demo |

**Khuyến nghị:** dữ liệu nhỏ → embedding **một lần offline**, lưu vector ra file (`.npy` hoặc ChromaDB persist). Lúc demo chỉ cần embed câu hỏi. Dù chọn A hay B đều phải hỗ trợ đa ngôn ngữ (khách hỏi tiếng Hàn vẫn ra POI mô tả tiếng Việt/Anh).

**Lưu trữ:** SQLite cho dữ liệu cấu trúc (lọc giá, giờ, nhóm khách, indoor) + numpy cosine hoặc ChromaDB cho vector. 100 POI không cần vector DB nặng.

**Task MVP của Hiếu:**
- [x] Mở rộng `pois.json` lên 50 POI, ID không trùng; đối chiếu nguồn.
- [x] Xử lý giá/giờ `null` và kiểm tra tích hợp với bộ lập lịch trên 50 POI; không đoán giá/giờ còn thiếu.
- [x] `search_pois`: lọc giá, nhóm khách, trong nhà, ngày đóng cửa; xếp hạng theo tag và bỏ điểm không khớp sở thích.
- [x] `get_poi_context(poi_id, lang)` trả mô tả, lưu ý, giá và giờ cho thuyết minh.
- [ ] Kiểm thử hỏi đáp về POI với LLM thật sau khi Huy kết nối model: giá, giờ, lưu ý và trường hợp không có thông tin; sửa phần truy xuất nếu kết quả sai.

Script thu thập tự động, vector/embedding và tìm kiếm ngữ nghĩa là việc mở rộng, không thuộc phạm vi MVP đã chốt.

### Huy — Agent LLM + đa ngôn ngữ

**LLM:** chọn 1 model nhanh, rẻ, function calling tốt (dòng mini/flash của OpenAI hoặc Gemini). Gọi thẳng SDK, **không dùng LangChain** để dễ debug.

**Task:**
- [ ] Prompt tách ràng buộc → JSON (budget, start, end, group_type, n_people, interests, lang). Thiếu thông tin thì hỏi lại **tối đa 1 câu**, còn lại dùng giá trị mặc định
- [ ] Đăng ký 4 tool theo hợp đồng mục 3.2, vòng lặp tool calling
- [ ] Đa ngôn ngữ: tự nhận diện ngôn ngữ user, trả lời đúng ngôn ngữ đó, tên POI kèm tên tiếng Việt
- [ ] Sửa lịch trình qua chat ("bỏ bảo tàng", "bớt 200k", "trời mưa thì sao") → gọi lại tool với ràng buộc mới, giữ state lịch trình hiện tại
- [ ] Lập lại lịch giữa chuyến: khách báo vị trí / trễ giờ ("Tôi đang ở Hồ Gươm, trễ 1 tiếng rồi") → gọi lại `plan_route` cho phần còn lại của ngày với `start_latlng` = vị trí hiện tại, `start_time` = giờ hiện tại, bỏ các điểm đã đi (thêm 1 dòng hướng dẫn vào system prompt)
- [ ] Prompt thuyết minh: 60–90 giây, chỉ dùng nội dung RAG trả về, **không bịa số liệu**
- [ ] Guardrail: LLM **không tự tính** khoảng cách, giờ, tiền — luôn lấy từ `plan_route`

### Tùng — Map API + tối ưu lộ trình

**Map API: TomTom** (chọn thay Goong: có chế độ xe máy khi tìm đường, gói miễn phí theo ngày, không cần SDK)
- Matrix Routing v2 (`POST /routing/matrix/2`): thời gian giữa các POI
- Calculate Route (`GET /routing/1/calculateRoute/...`): **một lần gọi cho cả tuyến**, cache từng chặng → `polyline` bám đường
- **Cache theo từng cặp điểm** ra `data/cache/maps_cache.json`, tính sẵn bằng `python -m routing.warm_cache`
- `plan_route` gọi ma trận **một lần**, chỉ xin các cặp còn thiếu; điểm xuất phát mới chỉ tốn 1 × n ô (không xin chiều quay về điểm xuất phát)
- Matrix v2 có thể không nhận xe máy → xe máy tạm dùng thời gian ô tô trong ma trận (`MATRIX_MODE` trong `routing/maps.py`), đường vẽ vẫn dùng `motorcycle`
- Có `TOMTOM_API_KEY` là dùng TomTom (độc lập với LLM mock); `USE_TOMTOM=0` để tắt
- Hiển thị bản đồ nền là phần của frontend; backend chỉ trả `polyline` bám đường
- Dự phòng: TomTom lỗi → tạm ngừng gọi 60 giây, dùng Haversine × 1.4 / tốc độ trung bình nội thành (đường: nối thẳng)

**Tối ưu: Google OR-Tools** (`pip install ortools`)
- Mô hình: TSP/VRP 1 xe, **time windows** (giờ mở/đóng cửa), **service time** (`visit_minutes`)
- **Disjunction có penalty** cho từng POI → solver được phép bỏ bớt điểm. Phạt cơ bản > cả ngày di chuyển (ưu tiên đi được nhiều điểm nhất), cộng 10 phút cho mỗi bậc hạng sở thích (`PRIORITY_STEP`)
- Ngân sách: **chiều "Cost" ngay trong solver** (tổng giá vé × số người ≤ ngân sách), không cần lọc knapsack trước; `total_cost = Σ price × n_people`
- Giới hạn thời gian solver ~2 giây
- **Kiểm + fallback:** kết quả OR-Tools qua `validate_plan`; có vi phạm / lỗi / chưa cài ortools → greedy nearest-neighbor
- `plan_route` trả thêm `solver` (`ortools` | `greedy`) và `dropped_reasons` (`not_found`, `missing_data`, `closed`, `budget`, `time`, `low_priority`) để LLM giải thích đúng vì sao bỏ điểm
- Đo 27/11 trên 8 kịch bản (ma trận TomTom thật): OR-Tools 78 điểm vs greedy 64, cả hai 0 vi phạm; OR-Tools đi nhiều phút hơn vì nhiều điểm hơn; ~2 giây/lần

**Task:**
- [ ] Đăng ký TomTom key, điền `TOMTOM_API_KEY` vào `.env`, gọi thử matrix + calculateRoute cho 2 điểm ở Hà Nội
- [x] `routing/maps.py`: Matrix + Calculate Route + cache + fallback Haversine (khung đã viết, chờ test key thật)
- [ ] Kiểm: matrix v2 có nhận `travelMode` xe máy không; số ô tối đa mỗi lần gọi → chỉnh `MATRIX_MODE`, `MAX_CELLS`
- [ ] Chạy `python -m routing.warm_cache` trước demo, commit `data/cache/maps_cache.json`
- [x] Greedy fallback chạy được → **trước 18:00**
- [x] OR-Tools có time windows + disjunction + ngân sách
- [x] Trả đúng output `plan_route` (kèm `dropped` + `dropped_reasons`); loại POI có `closed_days` trùng ngày đi
- [x] `validate_plan` kiểm lịch bằng code → dùng làm metric "0 vi phạm" trong `eval/metric_spec.yaml`
- [ ] Hàm tóm tắt "Sau chuyến đi" `summarize_trip(plan, lang) -> str`: tổng chi và tổng thời gian **tính bằng code** từ `stops`, LLM chỉ viết lời tóm tắt + gợi ý lần sau (dùng lại client LLM của Huy)

### Cường — Giao diện + thuyết minh + thời tiết + demo

**Giao diện:** ReactJS (Vite) + `react-leaflet`, gọi API ở `server.py`
- Layout: sidebar + 2 cột, trái là chat, phải là map (`Chat.jsx`, `MapView.jsx`)
- Map: tile OpenStreetMap mặc định (miễn phí) hoặc tile TomTom (raster, dùng thẳng với Leaflet); marker đánh số theo thứ tự, polyline đường đi, popup giờ đến + giá
- Bắt sự kiện click marker → hiện thẻ POI + nút "Nghe thuyết minh"
- Chọn ngôn ngữ (vi / en / ko / ja / zh) ở sidebar
- State: lịch sử chat + lịch trình giữ ở server theo `session_id` (frontend sinh); React chỉ giữ state hiển thị

**Thuyết minh (TTS):**
- Chính: **`edge-tts`** — miễn phí, giọng tự nhiên, nhiều ngôn ngữ (ví dụ `vi-VN-HoaiMyNeural`, `en-US-AriaNeural`, `ko-KR-SunHiNeural`, `ja-JP-NanamiNeural`, `zh-CN-XiaoxiaoNeural`). Đây là thư viện không chính thức, cần mạng
- Dự phòng: **`gTTS`**
- **Pre-generate** audio cho các POI trong kịch bản demo, lưu file mp3 → server phục vụ ở `/audio/…`, phát bằng thẻ `<audio>`

**Thời tiết: Open-Meteo** (miễn phí, không cần key)
- Lấy `precipitation_probability` theo giờ + nhiệt độ cho Hà Nội
- `is_rainy = True` → báo Huy để agent ưu tiên POI `indoor`
- Hiện widget thời tiết nhỏ trên giao diện

**Task:**
- [ ] Khung React + API chạy với dữ liệu giả → **trước 14:00**
- [ ] Map marker + polyline + click marker
- [ ] `services/tts.py`, `services/weather.py`
- [ ] Màn hình "Sau chuyến đi" (gọi `summarize_trip` của Tùng)
- [ ] Kịch bản demo + slide + quay video dự phòng

---

## 5. Timeline

| Mốc | Việc | Ai |
|---|---|---|
| Hôm nay 11:30 | Chốt schema, tool contract, tạo repo + `.env.example` | Cả nhóm |
| 12:00 | Bộ POI mẫu ban đầu; file hiện có 50 POI | Hiếu |
| 14:00 | UI khung chạy dữ liệu giả; agent gọi được tool giả | Cường, Huy |
| 16:00 | File đã tăng lên 50 POI đọc JSON; điểm thiếu giá/giờ được bỏ qua khi lập lịch | Hiếu |
| 18:00 | Greedy route chạy với TomTom thật | Tùng |
| 21:00 | **Tích hợp lần 1:** chat → lịch trình → map end-to-end | Cả nhóm |
| 22:00 | **Khoá tính năng.** Sau mốc này không thêm tính năng mới | Cả nhóm |
| 22:00–01:00 | OR-Tools, thuyết minh, thời tiết, sửa lịch trình qua chat | Theo phân công |
| Mai 08:00–11:00 | Fix bug, chạy kịch bản demo ≥5 lần, pre-generate audio, cache matrix | Cả nhóm |
| 11:00–13:00 | Slide + video dự phòng | Cường (+1 người hỗ trợ) |
| 13:30 | Nộp bài | — |

---

## 6. Kịch bản demo (luồng chính)

1. Khách Hàn Quốc chat bằng tiếng Hàn: *"2 người, 1 triệu, đi 1 ngày ở Hà Nội, thích lịch sử và ẩm thực"*
2. Bot trả lời tiếng Hàn + map hiện 5–6 điểm đánh số, đường đi, giờ, tổng chi phí
3. *"Chiều nay trời mưa thì sao?"* → lấy thời tiết → đổi điểm ngoài trời sang trong nhà
4. *"Bớt 200k"* → lịch trình tính lại
5. *"Tôi đang ở Hồ Gươm, trễ 1 tiếng rồi"* → lập lại phần còn lại của ngày từ vị trí + giờ hiện tại, bỏ điểm không kịp
6. Bấm marker Văn Miếu → nghe thuyết minh tiếng Hàn
7. Chuyển sang "Sau chuyến đi" → tóm tắt hành trình + chi tiêu

---

## 7. Rủi ro & dự phòng

| Rủi ro | Dự phòng |
|---|---|
| Hết quota / mất mạng TomTom | Ma trận + đường cache sẵn; tạm ngừng gọi 60 giây; fallback Haversine |
| LLM chậm / lỗi lúc demo | Câu chat demo đã chạy thử nhiều lần; video quay sẵn |
| TTS lỗi | Audio mp3 pre-generate cho POI trong kịch bản |
| Embedding local chạy chậm trên máy demo | Vector đã tính sẵn; chỉ embed câu hỏi |
| OR-Tools chưa xong | Dùng greedy fallback |
| Dữ liệu sai giá / giờ | Chỉ demo POI đã kiểm tra tay |

## 8. Quy ước

- Mỗi người 1 branch, merge vào `main` ở các mốc tích hợp
- Key để trong `.env`, **không commit**
- Hàm nào cũng có bản giả (mock) trả dữ liệu cứng để người khác test trước
