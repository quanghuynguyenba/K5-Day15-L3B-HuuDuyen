"""Tùng — tóm tắt "Sau chuyến đi".

Tổng chi, tổng thời gian, danh sách điểm: tính bằng code từ plan. LLM chỉ viết lời tóm tắt + gợi ý lần sau.
"""
from agent.llm import call_llm
from rag.search import get_poi


def trip_facts(plan: dict) -> dict:
    names = []
    for s in plan.get("stops", []):
        p = get_poi(s["poi_id"])
        names.append(p["name"]["vi"] if p else s["poi_id"])
    return {
        "places": names,
        "n_places": len(names),
        "total_cost": sum(s["cost"] for s in plan.get("stops", [])),
        "total_minutes": plan.get("total_minutes", 0),
    }


def summarize_trip(plan: dict, lang: str) -> str:
    f = trip_facts(plan)
    facts = "Điểm đã đi: %s\nTổng chi: %d VND\nTổng thời gian: %d phút" % (
        ", ".join(f["places"]), f["total_cost"], f["total_minutes"])
    system = ("Bạn viết tóm tắt chuyến đi cho du khách, bằng ngôn ngữ mã '%s'. "
              "Chỉ dùng số liệu được cung cấp, không tự tính hay thêm số. "
              "Kết thúc bằng 2 gợi ý cho lần sau." % lang)
    return call_llm(system, facts, mock_reply="[MOCK] Tóm tắt chuyến đi\n" + facts)
