"""Tính lại bảng chi phí từ cost/simulate-2.csv bằng đúng cost.simulate.summarize — không chạy lại phiên nào."""
import csv, json, sys
sys.path.insert(0, ".")
from cost import simulate as sim
cfg, _ = sim.load_config()
rows = []
for r in csv.DictReader(open("cost/simulate-2.csv", encoding="utf-8")):
    d = dict(r)
    for k in ("turns", "model_calls", "tool_calls", "tokens_in", "tokens_out"):
        d[k] = int(float(d[k] or 0))
    d["latency_s"] = float(d["latency_s"] or 0)
    try: d["by_model"] = json.loads(d.get("tokens_by_model") or "{}")
    except Exception: d["by_model"] = {}
    rows.append(d)
graded, other = sim.pick_rate(sim.measured_models(rows), "eval/run-2.csv")
print("\n".join(sim.summarize(cfg, rows, graded, other)))
