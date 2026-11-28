"""Nối model — chỗ DUY NHẤT trong bản chạy thử gọi model AI. NHÓM VIẾT phần gọi model thật.

Hợp đồng (giữ nguyên để khung đo được token):
    call_model(system: str, user: str) -> dict với 4 khoá
        "text":       str   chữ model trả về
        "model":      str   tên model đã gọi (để tra giá ở bảng giá model)
        "tokens_in":  int   số token vào, lấy từ trường usage trong phản hồi API — KHÔNG ước lượng
        "tokens_out": int   số token ra, gồm cả token suy luận / suy nghĩ nếu API tính riêng
    @model_call (từ tracing.py) tự ghi mỗi lần gọi vào trace; agent.py gọi call_model bao nhiêu lần
    cũng được, khung tự cộng token.
    Lỗi gọi model (hết lượt, sai key, mất mạng): cứ để exception bay ra — khung ghi lỗi vào cột error.

Chế độ giả (mặc định khi .env chưa có MODEL_PROVIDER, hoặc MODEL_PROVIDER=fake):
    trả một câu giả cố định, model "fake", token 0 — để luồng chạy hết từ trước CP2 (guide bước 3.2).
    Lượt `run.py eval` / `run.py simulate` chạy bằng model giả KHÔNG được tính.

Nối model thật: điền .env (chép từ .env.example), rồi viết nhánh gọi API ở dưới theo docs/connect-model.md
(có ví dụ OpenAI, Claude, model chạy trên máy, và cách nối nhà cung cấp khác). Không dán API key vào file này.
"""
import os

from tracing import model_call

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env(path=os.path.join(ROOT, ".env")):
    """Đọc file .env (KEY=VALUE mỗi dòng) vào biến môi trường, không ghi đè biến đã có. Khung — không cần sửa."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
MODEL_PROVIDER = (os.environ.get("MODEL_PROVIDER") or "fake").strip().lower()
MODEL_NAME = (os.environ.get("MODEL_NAME") or "").strip()
API_KEY = (os.environ.get("API_KEY") or "").strip()


@model_call
def call_model(system: str, user: str) -> dict:
    if MODEL_PROVIDER == "fake":
        last = (user.strip().splitlines() or [""])[-1]
        return {"text": "[câu trả lời giả — chưa nối model] " + last[:60], "model": "fake", "tokens_in": 0, "tokens_out": 0}

    if MODEL_PROVIDER not in OPENAI_COMPATIBLE:
        raise NotImplementedError(
            "MODEL_PROVIDER=%s chưa hỗ trợ trong codebase/ai.py (đang có: fake, %s) — xem docs/connect-model.md"
            % (MODEL_PROVIDER, ", ".join(OPENAI_COMPATIBLE)))
    if not API_KEY or not MODEL_NAME:
        raise RuntimeError("Thiếu API_KEY hoặc MODEL_NAME trong .env cho MODEL_PROVIDER=%s" % MODEL_PROVIDER)
    r = call_openai_compatible(OPENAI_COMPATIBLE[MODEL_PROVIDER], system, user)
    return {"text": r["text"], "model": r["model"], "tokens_in": int(r["tokens_in"]), "tokens_out": int(r["tokens_out"])}


# Nhà cung cấp có API dạng OpenAI Chat Completions (theo docs/connect-model.md mục 2.1 · 2.4)
OPENAI_COMPATIBLE = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
}


def call_openai_compatible(url, system, user):
    """Chỉ dùng thư viện chuẩn. Token lấy từ trường usage của API — không ước lượng."""
    import json
    import urllib.error
    import urllib.request
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    body = json.dumps({"model": MODEL_NAME, "messages": messages}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:  # để lỗi bay ra cho khung ghi vào cột error, không lộ key
        raise RuntimeError("HTTP %d từ %s: %s" % (e.code, MODEL_PROVIDER, e.read().decode("utf-8", "replace")[:300]))
    u = data.get("usage") or {}
    return {"text": data["choices"][0]["message"].get("content") or "",
            "model": data.get("model") or MODEL_NAME,
            "tokens_in": u.get("prompt_tokens", 0), "tokens_out": u.get("completion_tokens", 0)}
