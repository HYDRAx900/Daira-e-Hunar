"""
Generate mock_data/providers.json with 50 synthetic service providers.
Run from project root:
    .venv\Scripts\python.exe scratch/generate_providers.py
"""

import json
import random
from datetime import datetime, timedelta, timezone

random.seed(42)  # reproducible

PKT = timezone(timedelta(hours=5))
BASE_DATE = datetime(2026, 5, 16, tzinfo=PKT)  # tomorrow from "today" 2026-05-15

# ── Sector coordinates (OpenStreetMap centroids) ────────────────────────────
SECTORS = {
    "G-13":              (33.6350, 73.0290),
    "G-11":              (33.6655, 73.0185),
    "F-10":              (33.6940, 73.0125),
    "F-11":              (33.6855, 73.0295),
    "I-8":               (33.6640, 73.0530),
    "I-10":              (33.6430, 73.0220),
    "Blue Area":         (33.7100, 73.0480),
    "DHA Phase 2 Rawalpindi": (33.5560, 73.1120),
}

SLOT_HOURS = [9, 10, 11, 14, 15, 16, 17, 18]

def make_slots(count: int, skip_first_day: bool = False):
    """Generate `count` available slot datetimes over next 7 days."""
    pool = []
    for day_offset in range(0 if not skip_first_day else 1, 7):
        for hour in SLOT_HOURS:
            dt = BASE_DATE + timedelta(days=day_offset, hours=hour)
            pool.append(dt.isoformat())
    return sorted(random.sample(pool, min(count, len(pool))))


def jitter(lat, lng):
    """Add small random offset so providers in same sector aren't identical."""
    return (
        round(lat + random.uniform(-0.003, 0.003), 4),
        round(lng + random.uniform(-0.003, 0.003), 4),
    )


# ── Provider definitions ────────────────────────────────────────────────────
# (id, name, category, sector, rating, rating_count, price_min, price_max,
#  slot_count, verified, languages, notes)

RAW = [
    # ─── AC Technicians (12) ─────────────────────────────────────────────
    ("P0001", "Muhammad Irfan", "AC Technician", "G-13", 4.7, 132, 2000, 5000, 6, True, ["Urdu", "Punjabi"], None),
    ("P0002", "Ahmed Raza", "AC Technician", "G-11", 4.5, 89, 2500, 6000, 5, True, ["Urdu", "English"], None),
    ("P0003", "Bilal Hussain", "AC Technician", "F-10", 4.3, 64, 1800, 4500, 4, True, ["Urdu"], None),
    ("P0004", "Usman Ali", "AC Technician", "F-11", 4.8, 201, 3000, 7000, 7, True, ["Urdu", "English", "Punjabi"], None),
    ("P0005", "Farhan Saeed", "AC Technician", "I-8", 4.1, 45, 1500, 4000, 5, False, ["Urdu", "Punjabi"], None),
    ("P0006", "Kamran Shahid", "AC Technician", "I-10", 3.9, 33, 2000, 5000, 4, True, ["Urdu"], None),
    ("P0007", "Nadeem Akhtar", "AC Technician", "Blue Area", 4.6, 156, 3500, 8000, 8, True, ["Urdu", "English"], None),
    ("P0008", "Sajid Mehmood", "AC Technician", "G-13", 4.4, 78, 2000, 5500, 6, True, ["Urdu", "Punjabi"], "Also experienced in electrical wiring and switchboard repair"),
    ("P0009", "Tariq Mahmood", "AC Technician", "DHA Phase 2 Rawalpindi", 4.2, 52, 2500, 6000, 5, True, ["Urdu", "English"], None),
    ("P0010", "Waqar Hassan", "AC Technician", "G-11", 4.0, 28, 1500, 3500, 3, False, ["Urdu"], None),
    ("P0011", "Zubair Ahmad", "AC Technician", "F-10", 4.5, 91, 2000, 5000, 6, True, ["Urdu", "Punjabi"], None),
    ("P0012", "Faisal Raza Khan", "AC Technician", "I-8", 3.8, 19, 1800, 4000, 4, False, ["Urdu"], None),

    # ─── Plumbers (10) ───────────────────────────────────────────────────
    ("P0013", "Hassan Ali Shah", "Plumber", "G-11", 4.6, 110, 1000, 3000, 5, True, ["Urdu", "Punjabi"], None),
    ("P0014", "Imran Malik", "Plumber", "F-11", 4.3, 67, 800, 2500, 6, True, ["Urdu"], None),
    ("P0015", "Junaid Sheikh", "Plumber", "I-10", 4.5, 88, 1200, 3500, 7, True, ["Urdu", "English"], None),
    ("P0016", "Kashif Nawaz", "Plumber", "DHA Phase 2 Rawalpindi", 4.1, 41, 1000, 3000, 5, True, ["Urdu", "Punjabi"], None),
    ("P0017", "Liaqat Ali", "Plumber", "G-13", 2.1, 9, 500, 1500, 3, False, ["Urdu"], None),
    ("P0018", "Mansoor Ahmed", "Plumber", "G-11", 4.7, 145, 1500, 4000, 8, True, ["Urdu", "English", "Punjabi"], None),
    ("P0019", "Naeem Ullah", "Plumber", "F-10", 4.0, 36, 800, 2000, 4, False, ["Urdu"], None),
    ("P0020", "Omar Farooq", "Plumber", "Blue Area", 4.4, 73, 1200, 3500, 6, True, ["Urdu", "English"], None),
    ("P0021", "Qaiser Abbas", "Plumber", "I-8", 3.9, 25, 700, 2000, 4, True, ["Urdu", "Punjabi"], None),
    ("P0022", "Rizwan Chaudhry", "Plumber", "F-11", 4.2, 55, 1000, 3000, 5, True, ["Urdu"], None),

    # ─── Electricians (10) ───────────────────────────────────────────────
    ("P0023", "Sohail Aslam", "Electrician", "F-10", 4.5, 97, 1500, 4000, 6, True, ["Urdu", "English"], None),
    ("P0024", "Tahir Abbas", "Electrician", "F-11", 4.3, 62, 1200, 3500, 5, True, ["Urdu"], None),
    ("P0025", "Waseem Raja", "Electrician", "I-8", 4.6, 118, 1800, 4500, 7, True, ["Urdu", "Punjabi"], None),
    ("P0026", "Yasir Habib", "Electrician", "G-13", 4.1, 38, 1000, 3000, 4, True, ["Urdu"], None),
    ("P0027", "Amir Hamza", "Electrician", "Blue Area", 4.8, 189, 2500, 6000, 8, True, ["Urdu", "English", "Punjabi"], None),
    ("P0028", "Babar Khan", "Electrician", "G-11", 4.0, 29, 1000, 2500, 4, False, ["Urdu", "Punjabi"], None),
    ("P0029", "Danish Butt", "Electrician", "DHA Phase 2 Rawalpindi", 4.4, 71, 1500, 4000, 5, True, ["Urdu", "English"], "Also does plumbing work — previously trained as a plumber"),
    ("P0030", "Ehsan Elahi", "Electrician", "I-10", 3.7, 15, 800, 2000, 3, False, ["Urdu"], None),
    ("P0031", "Ghulam Mustafa", "Electrician", "F-10", 4.2, 54, 1200, 3000, 5, True, ["Urdu", "Punjabi"], None),
    ("P0032", "Hamid Raza", "Electrician", "G-13", 4.3, 66, 1400, 3500, 6, True, ["Urdu"], None),

    # ─── Tutors (10) ─────────────────────────────────────────────────────
    ("P0033", "Iftikhar Ahmed", "Tutor", "F-10", 4.5, 83, 3000, 8000, 0, True, ["Urdu", "English"], None),  # 0 slots = skip_first_day + empty
    ("P0034", "Javed Iqbal", "Tutor", "F-11", 4.7, 134, 2500, 7000, 6, True, ["Urdu", "English"], None),
    ("P0035", "Khalid Mehmood", "Tutor", "G-13", 4.4, 76, 2000, 5000, 5, True, ["Urdu", "English", "Punjabi"], None),
    ("P0036", "Asif Rafiq", "Tutor", "I-10", 4.2, 48, 1500, 4000, 4, True, ["Urdu"], None),
    ("P0037", "Mohsin Abbas", "Tutor", "G-11", 4.6, 105, 3000, 8000, 7, True, ["Urdu", "English"], None),
    ("P0038", "Noman Javed", "Tutor", "Blue Area", 4.8, 167, 5000, 12000, 8, True, ["Urdu", "English"], None),
    ("P0039", "Pervaiz Masih", "Tutor", "F-10", 4.1, 39, 2000, 5000, 4, False, ["Urdu", "English", "Punjabi"], None),
    ("P0040", "Raheel Sharif", "Tutor", "DHA Phase 2 Rawalpindi", 4.3, 59, 2500, 6000, 5, True, ["Urdu", "English"], None),
    ("P0041", "Shafiq Ahmad", "Tutor", "I-8", 4.0, 31, 1500, 4000, 4, True, ["Urdu"], None),
    ("P0042", "Taimoor Shah", "Tutor", "F-11", 4.4, 72, 2000, 5500, 6, True, ["Urdu", "English"], None),

    # ─── Beauticians (8) ─────────────────────────────────────────────────
    ("P0043", "Ayesha Bibi", "Beautician", "G-11", 4.6, 121, 2000, 8000, 6, True, ["Urdu", "Punjabi"], None),
    ("P0044", "Fatima Zahra", "Beautician", "DHA Phase 2 Rawalpindi", 4.8, 198, 3000, 12000, 7, True, ["Urdu", "English"], None),
    ("P0045", "Sana Malik", "Beautician", "F-10", 4.3, 65, 1500, 5000, 5, True, ["Urdu", "English", "Punjabi"], None),
    ("P0046", "Hina Rashid", "Beautician", "Blue Area", 4.5, 93, 2500, 10000, 6, True, ["Urdu", "English"], None),
    ("P0047", "Noor Electric", "Beautician", "G-13", 4.1, 42, 1800, 6000, 5, True, ["Urdu"], None),  # misleading name!
    ("P0048", "Rabia Aslam", "Beautician", "F-11", 4.4, 58, 2000, 7000, 4, True, ["Urdu", "Punjabi"], None),
    ("P0049", "Zainab Shah", "Beautician", "I-10", 4.2, 37, 1500, 5000, 4, False, ["Urdu"], None),
    ("P0050", "Uzma Shahid", "Beautician", "DHA Phase 2 Rawalpindi", 4.0, 22, 1200, 4000, 3, True, ["Urdu", "Punjabi"], None),
]

# ── Build JSON ───────────────────────────────────────────────────────────────
providers = []

for row in RAW:
    pid, name, category, sector, rating, rating_count, pmin, pmax, slot_count, verified, langs, notes = row

    lat_base, lng_base = SECTORS[sector]
    lat, lng = jitter(lat_base, lng_base)

    # P0033 special case: no slots in next 24h (all slots start day-after-tomorrow)
    if pid == "P0033":
        slots = make_slots(5, skip_first_day=True)
    elif slot_count == 0:
        slots = []
    else:
        slots = make_slots(slot_count)

    entry = {
        "id": pid,
        "name": name,
        "category": category,
        "sector": sector,
        "lat": lat,
        "lng": lng,
        "rating": rating,
        "rating_count": rating_count,
        "price_range": {
            "min": pmin,
            "max": pmax,
            "currency": "PKR"
        },
        "available_slots": slots,
        "verified": verified,
        "languages_spoken": langs,
        "_synthetic": True,
    }
    if notes:
        entry["notes"] = notes

    providers.append(entry)

# ── Validate ─────────────────────────────────────────────────────────────────
assert len(providers) == 50, f"Expected 50, got {len(providers)}"
assert all(p["_synthetic"] is True for p in providers), "All must have _synthetic: true"

categories = {}
sectors_seen = set()
for p in providers:
    categories[p["category"]] = categories.get(p["category"], 0) + 1
    sectors_seen.add(p["sector"])

print("Category distribution:", categories)
print("Sectors covered:", sorted(sectors_seen))
print(f"Total providers: {len(providers)}")

# Check edge cases
p17 = next(p for p in providers if p["id"] == "P0017")
assert p17["rating"] == 2.1, "P0017 should have 2.1 rating"
assert p17["rating_count"] == 9, "P0017 should have 9 ratings"

p33 = next(p for p in providers if p["id"] == "P0033")
first_slot_date = p33["available_slots"][0][:10] if p33["available_slots"] else None
assert first_slot_date != "2026-05-16", "P0033 should have no slots on first day"
print(f"P0033 first slot: {first_slot_date} (should be 2026-05-17 or later)")

p08 = next(p for p in providers if p["id"] == "P0008")
assert "notes" in p08, "P0008 should have overlap notes"

p29 = next(p for p in providers if p["id"] == "P0029")
assert "notes" in p29, "P0029 should have overlap notes"

p47 = next(p for p in providers if p["id"] == "P0047")
assert p47["name"] == "Noor Electric" and p47["category"] == "Beautician", "P0047 misleading name"

# Check mean rating
ratings = [p["rating"] for p in providers]
mean_rating = sum(ratings) / len(ratings)
print(f"Mean rating: {mean_rating:.2f} (target ~4.2)")

# ── Write ────────────────────────────────────────────────────────────────────
import pathlib
out_path = pathlib.Path(r"d:\Infromal Economy\mock_data\providers.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(providers, f, indent=2, ensure_ascii=False)

print(f"\n✅ Written {len(providers)} providers to {out_path}")
