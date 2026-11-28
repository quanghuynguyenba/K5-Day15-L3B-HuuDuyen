"""Nối model — chỗ DUY NHẤT trong bản chạy thử gọi model AI.

Hợp đồng (giữ nguyên để khung đo được token):
    call_model(system: str, user: str) -> dict với 4 khoá
        "text":       str   chữ model trả về
        "model":      str   tên model đã gọi (để tra giá ở bảng giá model)
        "tokens_in":  int   số token vào, lấy từ trường usage trong phản hồi API — KHÔNG ước lượng
        "tokens_out": int   số token ra, gồm cả token suy luận / suy nghĩ nếu API tính riêng
"""
import json
import os
import urllib.error
import urllib.request

from tracing import model_call

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOW_RAW = False


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
MODEL_NAME = (os.environ.get("MODEL_NAME") or os.environ.get("LLM_MODEL") or "").strip()
API_KEY = (
    os.environ.get("API_KEY")
    or os.environ.get("AI_API_KEY")
    or os.environ.get("LLM_API_KEY")
    or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    or ""
).strip()
BASE_URL = (os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "").strip()
ANTHROPIC_BASE_URL = (os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").strip().rstrip("/")

URL_OPENAI = "https://api.openai.com/v1/chat/completions"
URL_GEMINI_OAI = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
URL_CLAUDE = ANTHROPIC_BASE_URL + "/v1/messages"
URL_OLLAMA = "http://localhost:11434/api/chat"


def post_json(url: str, headers: dict, body: dict, timeout: int = 60) -> dict:
    """Send a JSON POST request using stdlib urllib and return parsed JSON."""
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers=dict({"Content-Type": "application/json"}, **headers),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error calling {url}: {e.reason}") from e
    except TimeoutError as e:
        raise RuntimeError(f"Timeout calling {url} after {timeout}s") from e

    if SHOW_RAW:
        print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
    return data


def _chat_messages(system: str, user: str) -> list[dict]:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": user})
    return msgs


def _openai_endpoint() -> str:
    if BASE_URL:
        base = BASE_URL.rstrip("/")
        return base if base.endswith("/chat/completions") else f"{base}/chat/completions"
    if MODEL_PROVIDER == "gemini":
        return URL_GEMINI_OAI
    return URL_OPENAI


def call_openai(system: str, user: str, model_name: str | None = None) -> dict:
    """Call OpenAI-compatible chat completions endpoint and read usage tokens."""
    model = model_name or MODEL_NAME
    if not model:
        raise RuntimeError("MODEL_NAME is empty; set MODEL_NAME in .env")
    if not API_KEY:
        raise RuntimeError("API_KEY is empty; set API_KEY in .env")

    data = post_json(
        _openai_endpoint(),
        {"Authorization": f"Bearer {API_KEY}"},
        {"model": model, "messages": _chat_messages(system, user)},
    )
    usage = data.get("usage")
    if not isinstance(usage, dict) or "prompt_tokens" not in usage or "completion_tokens" not in usage:
        raise RuntimeError(f"API response missing usage token counts: {list(data.keys())}")
    text = data["choices"][0]["message"].get("content") or ""
    return {
        "text": text,
        "tokens_in": int(usage["prompt_tokens"]),
        "tokens_out": int(usage["completion_tokens"]),
    }


def call_claude(system: str, user: str, model_name: str | None = None) -> dict:
    """Call Anthropic Messages API and read usage tokens."""
    model = model_name or MODEL_NAME
    if not model:
        raise RuntimeError("MODEL_NAME is empty; set MODEL_NAME in .env")
    if not API_KEY:
        raise RuntimeError("API_KEY is empty; set API_KEY in .env")

    # Claude Code proxies usually take Bearer ANTHROPIC_AUTH_TOKEN; official API uses x-api-key.
    headers = {"anthropic-version": "2023-06-01"}
    if os.environ.get("ANTHROPIC_AUTH_TOKEN") or API_KEY.startswith("ak-"):
        headers["Authorization"] = "Bearer " + API_KEY
    else:
        headers["x-api-key"] = API_KEY

    data = post_json(
        URL_CLAUDE,
        headers,
        {
            "model": model,
            "max_tokens": 1024,
            "system": system or "",
            "messages": [{"role": "user", "content": user}],
        },
    )
    usage = data.get("usage")
    if not isinstance(usage, dict) or "input_tokens" not in usage or "output_tokens" not in usage:
        raise RuntimeError(f"Claude response missing usage token counts: {list(data.keys())}")
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return {
        "text": text,
        "tokens_in": int(usage["input_tokens"]),
        "tokens_out": int(usage["output_tokens"]),
    }


def call_ollama(system: str, user: str, model_name: str | None = None) -> dict:
    """Call local Ollama chat API and read eval token counts."""
    model = model_name or MODEL_NAME
    if not model:
        raise RuntimeError("MODEL_NAME is empty; set MODEL_NAME in .env")
    data = post_json(
        URL_OLLAMA,
        {},
        {"model": model, "messages": _chat_messages(system, user), "stream": False},
        timeout=300,
    )
    return {
        "text": data["message"].get("content") or "",
        "tokens_in": int(data.get("prompt_eval_count", 0)),
        "tokens_out": int(data.get("eval_count", 0)),
    }


@model_call
def call_model(system: str, user: str) -> dict:
    """Call the configured LLM provider (or fake fallback) and return text, model, tokens_in, tokens_out."""
    if MODEL_PROVIDER == "fake":
        last = (user.strip().splitlines() or [""])[-1]
        return {
            "text": "[câu trả lời giả — chưa nối model] " + last[:60],
            "model": "fake",
            "tokens_in": 0,
            "tokens_out": 0,
        }

    if MODEL_PROVIDER in ("openai", "gemini", "openai-compatible"):
        r = call_openai(system, user)
    elif MODEL_PROVIDER == "anthropic":
        r = call_claude(system, user)
    elif MODEL_PROVIDER == "ollama":
        r = call_ollama(system, user)
    else:
        raise RuntimeError(f"Unsupported MODEL_PROVIDER={MODEL_PROVIDER!r}")

    return {
        "text": r["text"],
        "model": MODEL_NAME,
        "tokens_in": int(r["tokens_in"]),
        "tokens_out": int(r["tokens_out"]),
    }


@model_call
def call_model_tools(messages: list[dict], tools: list[dict]) -> dict:
    """Call OpenAI-compatible chat completions with tool definitions and return usage + tool_calls."""
    if MODEL_PROVIDER == "fake":
        return {
            "text": "[fake tool-loop]",
            "model": "fake",
            "tokens_in": 0,
            "tokens_out": 0,
            "tool_calls": [],
            "assistant_message": {"role": "assistant", "content": ""},
        }
    if MODEL_PROVIDER not in ("openai", "gemini", "openai-compatible"):
        raise RuntimeError(f"Tool calling via OpenAI schema not supported for provider={MODEL_PROVIDER!r}")
    if not MODEL_NAME or not API_KEY:
        raise RuntimeError("MODEL_NAME and API_KEY must be set in .env for tool calling")

    data = post_json(
        _openai_endpoint(),
        {"Authorization": f"Bearer {API_KEY}"},
        {"model": MODEL_NAME, "messages": messages, "tools": tools},
    )
    usage = data.get("usage")
    if not isinstance(usage, dict) or "prompt_tokens" not in usage or "completion_tokens" not in usage:
        raise RuntimeError(f"API response missing usage token counts: {list(data.keys())}")
    msg = data["choices"][0]["message"]
    return {
        "text": msg.get("content") or "",
        "model": MODEL_NAME,
        "tokens_in": int(usage["prompt_tokens"]),
        "tokens_out": int(usage["completion_tokens"]),
        "tool_calls": msg.get("tool_calls") or [],
        "assistant_message": msg,
    }
