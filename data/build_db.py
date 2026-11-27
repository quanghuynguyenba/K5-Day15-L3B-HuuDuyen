"""Hiếu — pois.json → SQLite (+ vector). Chạy: python data/build_db.py

Hiện mới dựng bảng SQLite. TODO (Hiếu):
  - chọn phương án embedding A (local) hoặc B (API) trước 13h
  - embed description_vi + description_en + tags của từng POI → lưu data/cache/poi_vectors.npy (+ thứ tự id)
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR  # noqa: E402

DB_PATH = os.path.join(DATA_DIR, "pois.db")


def build():
    with open(os.path.join(DATA_DIR, "pois.json"), encoding="utf-8") as f:
        pois = json.load(f)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE pois (
        id TEXT PRIMARY KEY, name_vi TEXT, name_en TEXT, lat REAL, lng REAL,
        category TEXT, indoor INTEGER, price_vnd INTEGER, open TEXT, close TEXT,
        visit_minutes INTEGER, json TEXT)""")
    for p in pois:
        con.execute("INSERT INTO pois VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            p["id"], p["name"]["vi"], p["name"]["en"], p["lat"], p["lng"], p["category"],
            int(p["indoor"]), p["price_vnd"], p["open"], p["close"], p["visit_minutes"],
            json.dumps(p, ensure_ascii=False)))
    con.commit()
    con.close()
    print("Đã ghi %d POI vào %s" % (len(pois), DB_PATH))
    # TODO (Hiếu): embedding


if __name__ == "__main__":
    build()
