# TASK.md — Hackathon #14: Hành trình du lịch cá nhân hoá

**Deadline:** 14:00 thứ 7, 28/11/2026
**Team:** Huy · Tùng · Hiếu · Cường — tất cả dùng Python + Streamlit

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
        ├─► tool search_pois (Tùng)   : lọc SQLite + vector search
        ├─► tool plan_route  (Hiếu)   : Distance Matrix + OR-Tools → lịch trình
        ├─► tool get_weather (Cường)  : Open-Meteo → mưa thì ưu tiên POI indoor
        └─► tool narrate     (Huy+Cường): RAG + LLM viết thuyết minh → TTS
  └─► Streamlit (Cường): khung chat + map (marker đánh số + polyline) + audio
```

Cấu trúc repo:

```
app.py                 # Streamlit entry (Cường)
agent/llm.py           # client LLM, prompt, tool calling (Huy)
agent/tools.py         # đăng ký tool, gọi các module dưới (Huy)
data/pois.json         # dữ liệu POI (Tùng)
data/build_db.py       # json → SQLite + embedding (Tùng)
rag/search.py          # search_pois (Tùng)
routing/goong.py       # Distance Matrix, Directions, cache (Hiếu)
routing/optimizer.py   # OR-Tools / greedy (Hiếu)
services/weather.py    # Open-Meteo (Cường)
services/tts.py        # edge-tts / gTTS (Cường)
.env.example           # LLM_API_KEY, GOONG_API_KEY, (EMBED_API_KEY)
```

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
  "visit_minutes": 60,
  "suitable_for": ["family", "elderly", "couple", "friends", "solo"],
  "description_vi": "…",
  "description_en": "…",
  "source": "https://…"
}
```

Category gợi ý: `history`, `museum`, `food`, `cafe`, `nature`, `shopping`, `night`, `art`.

### 3.2 Chữ ký các tool

```python
search_pois(interests: list[str], group_type: str, max_price: int,
            indoor_only: bool = False, top_k: int = 15) -> list[dict]

plan_route(poi_ids: list[str], start_latlng: tuple, start_time: str,
           end_time: str, budget_vnd: int, n_people: int,
           vehicle: str = "car") -> dict
# trả về: {"stops":[{"poi_id","arrive","depart","cost"}],
#          "total_cost", "total_minutes", "polyline":[[lat,lng],...], "dropped":[poi_id]}

get_weather(date: str, lat: float, lng: float) -> dict
# {"rain_prob_by_hour": {...}, "is_rainy": bool, "temp_max": float}

narrate(poi_id: str, lang: str) -> {"text": str, "audio_path": str}
```

---

## 4. Phân công

### Tùng — Dữ liệu POI + RAG

**Nguồn dữ liệu:**

| Dữ liệu | Nguồn | Cách lấy |
|---|---|---|
| Danh sách POI + toạ độ | OpenStreetMap qua **Overpass API** (miễn phí, không key) | API |
| Bổ sung / kiểm tra toạ độ | **Goong Geocoding / Places** | API (dùng chung key với Hiếu) |
| Mô tả, lịch sử, nội dung thuyết minh | **Wikipedia / Wikivoyage** (có sẵn vi, en, ko, ja, zh…), thư viện `wikipedia-api` | API |
| Giá vé, giờ mở cửa, thời gian tham quan | Website chính thức, trang du lịch Hà Nội | **Tự gom**: LLM tạo bản nháp, người kiểm tra lại từng điểm |
| `suitable_for`, `indoor`, `tags` | Tự gán | **Tự gom** |

→ Overpass/Wikipedia cho số lượng; giá & giờ phải tự gom vì không có API đáng tin. Ưu tiên **50 POI sạch** hơn 200 POI bẩn. Ghi `source` cho từng điểm.

**Embedding — 2 phương án, chọn 1 trước 13h:**

| | **A. Local** (sentence-transformers) | **B. API nhà cung cấp** |
|---|---|---|
| Model gợi ý | `BAAI/bge-m3` (chất lượng tốt nhất, ~2.2 GB) hoặc `intfloat/multilingual-e5-small` (~470 MB, nhanh) | Embedding API của OpenAI / Gemini / nhà cung cấp LLM đang dùng |
| Ưu điểm | Miễn phí, không phụ thuộc mạng/quota, dữ liệu không ra ngoài | Không tốn dung lượng, không cần GPU, cài đặt nhanh |
| Nhược điểm | **Tốn dung lượng lưu trữ** + RAM, tải model lâu, chạy CPU chậm hơn | **Có thể phải trả phí** (dù ~100 POI thì chi phí gần như không đáng kể), cần key, phụ thuộc mạng & rate limit |
| Rủi ro demo | Máy demo thiếu RAM / chưa tải model | Mất mạng hoặc hết quota lúc demo |

**Khuyến nghị:** dữ liệu nhỏ → embedding **một lần offline**, lưu vector ra file (`.npy` hoặc ChromaDB persist). Lúc demo chỉ cần embed câu hỏi. Dù chọn A hay B đều phải hỗ trợ đa ngôn ngữ (khách hỏi tiếng Hàn vẫn ra POI mô tả tiếng Việt/Anh).

**Lưu trữ:** SQLite cho dữ liệu cấu trúc (lọc giá, giờ, nhóm khách, indoor) + numpy cosine hoặc ChromaDB cho vector. 100 POI không cần vector DB nặng.

**Task:**
- [ ] Viết `pois.json` mẫu 5 POI theo schema → push **trước 12:00** để mọi người test
- [ ] Script Overpass + Wikipedia lấy dữ liệu thô
- [ ] Hoàn thiện ≥50 POI (giá, giờ, tag, indoor, suitable_for) → **trước 16:00**
- [ ] `build_db.py`: json → SQLite + vector
- [ ] `search_pois`: lọc cứng (giá, nhóm, indoor) rồi xếp hạng bằng vector similarity theo interests
- [ ] Hàm `get_poi_context(poi_id, lang)` trả đoạn nội dung cho thuyết minh

### Huy — Agent LLM + đa ngôn ngữ

**LLM:** chọn 1 model nhanh, rẻ, function calling tốt (dòng mini/flash của OpenAI hoặc Gemini). Gọi thẳng SDK, **không dùng LangChain** để dễ debug.

**Task:**
- [ ] Prompt tách ràng buộc → JSON (budget, start, end, group_type, n_people, interests, lang). Thiếu thông tin thì hỏi lại **tối đa 1 câu**, còn lại dùng giá trị mặc định
- [ ] Đăng ký 4 tool theo hợp đồng mục 3.2, vòng lặp tool calling
- [ ] Đa ngôn ngữ: tự nhận diện ngôn ngữ user, trả lời đúng ngôn ngữ đó, tên POI kèm tên tiếng Việt
- [ ] Sửa lịch trình qua chat ("bỏ bảo tàng", "bớt 200k", "trời mưa thì sao") → gọi lại tool với ràng buộc mới, giữ state lịch trình hiện tại
- [ ] Prompt thuyết minh: 60–90 giây, chỉ dùng nội dung RAG trả về, **không bịa số liệu**
- [ ] Guardrail: LLM **không tự tính** khoảng cách, giờ, tiền — luôn lấy từ `plan_route`
- [ ] Màn hình "Sau chuyến đi": LLM tóm tắt lịch trình, tổng chi, gợi ý lần sau

### Hiếu — Map API + tối ưu lộ trình

**Map API: Goong** (Việt Nam, định dạng giống Google Maps, hiển thị đúng Hoàng Sa – Trường Sa)
- Distance Matrix: thời gian/quãng đường giữa các POI
- Directions: lấy polyline để vẽ đường (decode bằng thư viện `polyline`)
- Free tier giới hạn request/phút → **cache Distance Matrix ra file** cho bộ POI cố định, tính sẵn trước demo
- Dự phòng: OSRM public demo server (`router.project-osrm.org`, chỉ để demo) → cuối cùng là Haversine × hệ số 1.4 / tốc độ trung bình nội thành

**Tối ưu: Google OR-Tools** (`pip install ortools`)
- Mô hình: TSP/VRP 1 xe, **time windows** (giờ mở/đóng cửa), **service time** (`visit_minutes`)
- **Disjunction có penalty** cho từng POI → solver được phép bỏ bớt điểm nếu không kịp giờ; POI phù hợp sở thích hơn thì penalty cao hơn
- Ngân sách: lọc trước + chọn tập POI theo điểm ưu tiên / giá (greedy kiểu knapsack) trước khi đưa vào solver; `total_cost = Σ price × n_people` (+ ước tính di chuyển nếu kịp)
- Giới hạn thời gian solver ~2 giây
- **Fallback:** greedy nearest-neighbor + kiểm tra giờ mở cửa → viết **trước**, OR-Tools làm sau

**Task:**
- [ ] Đăng ký Goong key, test Distance Matrix + Directions
- [ ] `routing/goong.py` + cache
- [ ] Greedy fallback chạy được → **trước 18:00**
- [ ] OR-Tools có time windows + disjunction
- [ ] Trả đúng output `plan_route` (kèm `dropped` để LLM giải thích vì sao bỏ điểm)

### Cường — Giao diện + thuyết minh + thời tiết + demo

**Giao diện:** Streamlit + `streamlit-folium`
- Layout 2 cột: trái là chat (`st.chat_message`, `st.chat_input`), phải là map
- Map: tile OpenStreetMap mặc định (miễn phí) hoặc tile Goong; marker đánh số theo thứ tự, polyline đường đi, popup giờ đến + giá
- Bắt sự kiện click marker → hiện thẻ POI + nút "Nghe thuyết minh"
- Chọn ngôn ngữ (vi / en / ko / ja / zh) ở sidebar
- Giữ state bằng `st.session_state` (lịch sử chat, lịch trình hiện tại)

**Thuyết minh (TTS):**
- Chính: **`edge-tts`** — miễn phí, giọng tự nhiên, nhiều ngôn ngữ (ví dụ `vi-VN-HoaiMyNeural`, `en-US-AriaNeural`, `ko-KR-SunHiNeural`, `ja-JP-NanamiNeural`, `zh-CN-XiaoxiaoNeural`). Đây là thư viện không chính thức, cần mạng
- Dự phòng: **`gTTS`**
- **Pre-generate** audio cho các POI trong kịch bản demo, lưu file mp3 → phát bằng `st.audio`

**Thời tiết: Open-Meteo** (miễn phí, không cần key)
- Lấy `precipitation_probability` theo giờ + nhiệt độ cho Hà Nội
- `is_rainy = True` → báo Huy để agent ưu tiên POI `indoor`
- Hiện widget thời tiết nhỏ trên giao diện

**Task:**
- [ ] Khung Streamlit chạy với dữ liệu giả → **trước 14:00**
- [ ] Map marker + polyline + click marker
- [ ] `services/tts.py`, `services/weather.py`
- [ ] Màn hình "Sau chuyến đi" (gọi hàm tóm tắt của Huy)
- [ ] Kịch bản demo + slide + quay video dự phòng

---

## 5. Timeline

| Mốc | Việc | Ai |
|---|---|---|
| Hôm nay 11:30 | Chốt schema, tool contract, tạo repo + `.env.example` | Cả nhóm |
| 12:00 | 5 POI mẫu lên repo | Tùng |
| 14:00 | UI khung chạy dữ liệu giả; agent gọi được tool giả | Cường, Huy |
| 16:00 | ≥50 POI hoàn chỉnh + DB + vector | Tùng |
| 18:00 | Greedy route chạy với Goong thật | Hiếu |
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
5. Bấm marker Văn Miếu → nghe thuyết minh tiếng Hàn
6. Chuyển sang "Sau chuyến đi" → tóm tắt hành trình + chi tiêu

---

## 7. Rủi ro & dự phòng

| Rủi ro | Dự phòng |
|---|---|
| Hết quota / mất mạng Goong | Distance Matrix cache sẵn; fallback Haversine |
| LLM chậm / lỗi lúc demo | Câu chat demo đã chạy thử nhiều lần; video quay sẵn |
| TTS lỗi | Audio mp3 pre-generate cho POI trong kịch bản |
| Embedding local chạy chậm trên máy demo | Vector đã tính sẵn; chỉ embed câu hỏi |
| OR-Tools chưa xong | Dùng greedy fallback |
| Dữ liệu sai giá / giờ | Chỉ demo POI đã kiểm tra tay |

## 8. Quy ước

- Mỗi người 1 branch, merge vào `main` ở các mốc tích hợp
- Key để trong `.env`, **không commit**
- Hàm nào cũng có bản giả (mock) trả dữ liệu cứng để người khác test trước
