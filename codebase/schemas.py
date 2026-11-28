"""Schemas and validators for intents, entities, itineraries, and agent responses."""
from dataclasses import dataclass, field
import json
import re
from typing import Any, Optional

VALID_INTENTS = (
    "PLAN_TRIP",
    "SEARCH_PLACE",
    "ESTIMATE_BUDGET",
    "MODIFY_TRIP",
    "TRAVEL_INFO",
    "RECOMMEND_PLACE",
    "OUT_OF_SCOPE",
    "REFUSE",
)

ALLOWED_INTERESTS = (
    "history",
    "food",
    "museum",
    "culture",
    "nature",
    "architecture",
    "photo",
    "shopping",
    "nightlife",
    "education",
)


@dataclass
class Entities:
    destination: str = "Hanoi"
    start_date: Optional[str] = "2026-11-28"
    window: Optional[tuple[str, str]] = None
    budget_vnd: Optional[int] = None
    interests: list[str] = field(default_factory=list)
    n_people: Optional[int] = None
    transportation: Optional[str] = None
    language: str = "vi"
    exclusions: list[str] = field(default_factory=list)
    rainy: Optional[bool] = None
    closed_day: str = ""
    requested_place: str = ""
    query: str = ""


@dataclass
class IntentResult:
    intent: str
    entities: Entities = field(default_factory=Entities)
    missing_field: Optional[str] = None
    reason: str = ""


@dataclass
class ItineraryStop:
    poi_id: str
    name: str
    arrive: str
    depart: str
    cost: int
    indoor: bool


@dataclass
class Itinerary:
    stops: list[ItineraryStop] = field(default_factory=list)
    total_cost: int = 0
    total_minutes: int = 0
    dropped: list[dict[str, Any]] = field(default_factory=list)
    transfer_minutes: int = 15
    feasible: bool = False


@dataclass
class AgentResponse:
    output: str


def _clean_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    try:
        num = int(value)
        return num if num > 0 else None
    except (TypeError, ValueError):
        return None


def _clean_window(value: Any) -> Optional[tuple[str, str]]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    start, end = str(value[0]).strip(), str(value[1]).strip()
    if re.match(r"^\d{2}:\d{2}$", start) and re.match(r"^\d{2}:\d{2}$", end):
        return (start, end)
    return None


def _clean_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip().lower() for item in value if str(item).strip()]


def validate_intent_payload(data: dict[str, Any]) -> IntentResult:
    """Validate and normalize a raw dict into an IntentResult."""
    if not isinstance(data, dict):
        raise ValueError("Intent payload must be a dict")
    intent = str(data.get("intent") or "").strip().upper()
    if intent not in VALID_INTENTS:
        raise ValueError(f"Unsupported intent: {intent!r}")

    raw_ent = data.get("entities") or {}
    if not isinstance(raw_ent, dict):
        raw_ent = {}

    rainy_val = raw_ent.get("rainy")
    rainy = bool(rainy_val) if isinstance(rainy_val, bool) else None

    entities = Entities(
        destination=str(raw_ent.get("destination") or "Hanoi").strip(),
        start_date=str(raw_ent.get("start_date")).strip() if raw_ent.get("start_date") else "2026-11-28",
        window=_clean_window(raw_ent.get("window")),
        budget_vnd=_clean_int(raw_ent.get("budget_vnd")),
        interests=_clean_str_list(raw_ent.get("interests")),
        n_people=_clean_int(raw_ent.get("n_people")),
        transportation=str(raw_ent.get("transportation")).strip() if raw_ent.get("transportation") else None,
        language=str(raw_ent.get("language") or "vi").strip().lower(),
        exclusions=_clean_str_list(raw_ent.get("exclusions")),
        rainy=rainy,
        closed_day=str(raw_ent.get("closed_day") or "").strip().lower(),
        requested_place=str(raw_ent.get("requested_place") or "").strip(),
        query=str(raw_ent.get("query") or "").strip(),
    )

    missing = data.get("missing_field")
    missing_field = str(missing).strip() if missing else None
    reason = str(data.get("reason") or "").strip()
    return IntentResult(intent=intent, entities=entities, missing_field=missing_field, reason=reason)


def parse_intent_json(raw_text: str) -> Optional[IntentResult]:
    """Parse JSON (with optional markdown code fences) into IntentResult, or return None."""
    if not raw_text or not isinstance(raw_text, str):
        return None
    cleaned = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if brace_match:
            cleaned = brace_match.group(0)
    try:
        payload = json.loads(cleaned)
        return validate_intent_payload(payload)
    except (json.JSONDecodeError, ValueError):
        return None
