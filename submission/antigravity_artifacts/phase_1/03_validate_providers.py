import json

data = json.load(open(r"d:\Infromal Economy\mock_data\providers.json", "r", encoding="utf-8"))

print(f"Total entries: {len(data)}")

sectors = set(p["sector"] for p in data)
print(f"Sectors ({len(sectors)}): {sorted(sectors)}")

names = [p["name"] for p in data]
dupes = set(n for n in names if names.count(n) > 1)
print(f"Duplicate names: {dupes if dupes else 'None'}")

print(f"All _synthetic=true: {all(p['_synthetic'] == True for p in data)}")

categories = {}
for p in data:
    categories[p["category"]] = categories.get(p["category"], 0) + 1
print(f"Categories: {categories}")
