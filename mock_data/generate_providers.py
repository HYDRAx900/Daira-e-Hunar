"""
Generator script for 100 synthetic providers across 8 Pakistani cities.
Phase 1.5 — Daira-e-Hunar realignment.

Run: python mock_data/generate_providers.py
Outputs: mock_data/providers.json
"""

import json
import random
from pathlib import Path

random.seed(42)

# ── Real neighborhood coordinates (centroids from OpenStreetMap knowledge) ────

NEIGHBORHOODS = {
    "Islamabad": [
        ("G-7, Islamabad", 33.7100, 73.0480),
        ("G-9, Islamabad", 33.6930, 73.0390),
        ("I-9, Islamabad", 33.6680, 73.0460),
        ("I-10, Islamabad", 33.6420, 73.0200),
    ],
    "Rawalpindi": [
        ("Tench Bhata, Rawalpindi", 33.5870, 73.0680),
        ("Dhok Khabba, Rawalpindi", 33.5750, 73.0550),
        ("Raja Bazaar, Rawalpindi", 33.5980, 73.0470),
        ("Pirwadhai, Rawalpindi", 33.6150, 73.0630),
        ("Saddar, Rawalpindi", 33.5960, 73.0510),
    ],
    "Lahore": [
        ("Misri Shah, Lahore", 31.5780, 74.3190),
        ("Shadbagh, Lahore", 31.5850, 74.3250),
        ("Garhi Shahu, Lahore", 31.5560, 74.3470),
        ("Daroghewala, Lahore", 31.5950, 74.3100),
        ("Mochi Gate, Lahore", 31.5830, 74.3220),
        ("Lohari Gate, Lahore", 31.5790, 74.3170),
        ("Bhatti Gate, Lahore", 31.5810, 74.3240),
    ],
    "Faisalabad": [
        ("Ghulam Mohammadabad, Faisalabad", 31.4180, 73.0790),
        ("Jhang Bazaar, Faisalabad", 31.4160, 73.0730),
        ("Madina Town, Faisalabad", 31.3950, 73.0840),
        ("D-Ground, Faisalabad", 31.4250, 73.0900),
        ("Rail Bazaar, Faisalabad", 31.4190, 73.0810),
    ],
    "Karachi": [
        ("Lyari, Karachi", 24.8520, 67.0120),
        ("Orangi, Karachi", 24.9310, 66.9840),
        ("Korangi, Karachi", 24.8380, 67.1310),
        ("Landhi, Karachi", 24.8540, 67.1560),
        ("Baldia Town, Karachi", 24.9130, 66.9620),
    ],
    "Quetta": [
        ("Pashtunabad, Quetta", 30.1970, 67.0050),
        ("Hazara Town, Quetta", 30.1620, 66.9810),
        ("Kandahari Bazaar, Quetta", 30.1880, 66.9960),
        ("Jinnah Road, Quetta", 30.1910, 67.0010),
    ],
    "Peshawar": [
        ("Hashtnagri, Peshawar", 34.0120, 71.5710),
        ("Kohati Gate, Peshawar", 34.0050, 71.5680),
        ("Qissa Khwani, Peshawar", 34.0100, 71.5750),
        ("Faqirabad, Peshawar", 34.0200, 71.5640),
    ],
    "Gilgit": [
        ("Konodas, Gilgit", 35.9210, 74.3080),
        ("Jutial, Gilgit", 35.9250, 74.3200),
        ("Kashrote, Gilgit", 35.9190, 74.3150),
        ("Danyor, Gilgit", 35.9130, 74.3740),
        ("Main Bazaar, Gilgit", 35.9200, 74.3120),
    ],
}

CATEGORIES = ["AC Technician", "Plumber", "Electrician", "Tutor", "Beautician"]

# ── Name pools ───────────────────────────────────────────────────────────────

MALE_FIRST = [
    "Muhammad Aslam", "Ali Raza", "Ghulam Farid", "Irfan", "Tariq",
    "Nadeem", "Shahbaz", "Rashid", "Imran", "Waqas",
    "Niaz Hussain", "Habib ur Rehman", "Fazal", "Liaqat", "Bahadur",
    "Zahoor", "Mumtaz", "Riaz", "Shabbir", "Akbar",
    "Gulzar", "Nazir", "Manzoor", "Qadir", "Hameed",
    "Bashir", "Amanullah", "Saifullah", "Noor Muhammad", "Iqbal",
    "Javed", "Ashraf", "Aziz", "Hanif", "Sharif",
    "Ramzan", "Yaqoob", "Dawood", "Ilyas", "Saleem",
    "Pervaiz", "Mushtaq", "Arshad", "Khalil", "Zulfiqar",
    "Gul Sher", "Dost Muhammad", "Fida Hussain", "Mehr Din", "Sultan",
]

FEMALE_FIRST = [
    "Fatima Bibi", "Saima Bano", "Gul Bibi", "Nasreen", "Rukhsana",
    "Parveen", "Shahnaz", "Kausar", "Tahira", "Razia",
    "Zubaida", "Maryam", "Amina", "Bushra", "Sajida",
    "Nargis", "Shabnam", "Mumtaz", "Gulnaz", "Robina",
]

SURNAMES_COMMON = [
    "", "", "", "",  # many working-class Pakistanis go by single name
    "Khan", "Gujjar", "Mughal", "Butt", "Awan",
    "Rajput", "Jat", "Niazi", "Khattak", "Afridi",
    "Marri", "Bugti", "Mengal", "Lashari",
]

REGIONAL_SURNAMES = {
    "Pashtun": ["Achakzai", "Khattak", "Afridi", "Yousafzai", "Shinwari", "Khan"],
    "Baloch": ["Marri", "Bugti", "Mengal", "Lashari", "Rind"],
    "Hazara": ["Hazara", "Hussaini", "Changezi"],
    "Sindhi": ["Shaikh", "Laghari", "Bhutto", "Chandio"],
    "Punjabi": ["Butt", "Gujjar", "Jat", "Rajput", "Awan", "Mughal"],
    "Saraiki": ["Mazari", "Khosa", "Leghari", "Dreshak"],
    "Gilgiti": ["Baig", "Mir", "Shah", "Karim"],
    "Muhajir": ["Qureshi", "Ansari", "Siddiqui", "Rizvi"],
    "Sheedi": ["Sheedi", "Siddi", "Makrani"],
}

# ── Cultural background distributions by city ────────────────────────────────

CITY_CULTURES = {
    "Islamabad": [("Punjabi", 0.4), ("Pashtun", 0.3), (None, 0.3)],
    "Rawalpindi": [("Punjabi", 0.5), ("Pashtun", 0.2), (None, 0.3)],
    "Lahore": [("Punjabi", 0.4), (None, 0.6)],
    "Faisalabad": [("Punjabi", 0.3), ("Saraiki", 0.1), (None, 0.6)],
    "Karachi": [("Muhajir", 0.2), ("Sindhi", 0.1), ("Baloch", 0.05), ("Sheedi", 0.05), ("Pashtun", 0.1), (None, 0.5)],
    "Quetta": [("Pashtun", 0.3), ("Baloch", 0.2), ("Hazara", 0.2), (None, 0.3)],
    "Peshawar": [("Pashtun", 0.5), (None, 0.5)],
    "Gilgit": [("Gilgiti", 0.4), (None, 0.6)],
}

# ── Language distributions by city ───────────────────────────────────────────

CITY_LANGUAGES = {
    "Islamabad": [["Urdu", "Punjabi"], ["Urdu", "English"], ["Urdu"], ["Urdu", "Pashto"]],
    "Rawalpindi": [["Urdu", "Punjabi"], ["Urdu"], ["Urdu", "Punjabi", "English"], ["Urdu", "Pashto"]],
    "Lahore": [["Urdu", "Punjabi"], ["Punjabi", "Urdu"], ["Urdu"], ["Urdu", "Punjabi", "English"]],
    "Faisalabad": [["Urdu", "Punjabi"], ["Punjabi", "Urdu"], ["Urdu"], ["Urdu", "Saraiki"]],
    "Karachi": [["Urdu"], ["Urdu", "Sindhi"], ["Urdu", "Pashto"], ["Urdu", "Balochi"], ["Urdu", "English"]],
    "Quetta": [["Urdu", "Pashto"], ["Urdu", "Balochi"], ["Urdu", "Hazaragi"], ["Urdu", "Pashto", "Brahui"]],
    "Peshawar": [["Pashto", "Urdu"], ["Pashto", "Urdu", "English"], ["Pashto", "Urdu"]],
    "Gilgit": [["Urdu", "Shina"], ["Urdu", "Burushaski"], ["Urdu", "Shina", "English"], ["Urdu"]],
}

# ── Bio templates ────────────────────────────────────────────────────────────

BIO_TEMPLATES = {
    "AC Technician": [
        "{years} years fixing ACs across {city}. Trained his son in the trade.",
        "Started as a helper at 14 in a shop near {neighborhood}. Now runs his own team.",
        "Specializes in split AC installation. Quiet man, fast hands.",
        "Learned the craft from his uncle. Gets most of his calls from repeat customers.",
        "Seasonal rush keeps him busy April through September. Winters, he does odd electrical work.",
        "Known in {neighborhood} for fixing ACs other technicians give up on.",
        "Former factory worker who switched to AC repair after the mill closed.",
        "Does commercial AC work for shops in {neighborhood}. Residential on weekends.",
        "Self-taught from YouTube videos and years of practice. Surprisingly good.",
        "Handles window ACs, splits, and inverters. Won't touch centralized systems.",
    ],
    "Plumber": [
        "Third-generation plumber. His grandfather laid pipes in old {city}.",
        "Moved from village to {city} fifteen years ago. Plumbing was the first job that stuck.",
        "Reliable for emergency calls. Has been known to show up at 2 AM.",
        "Quiet, does his work, doesn't overcharge. Hard to find that combination.",
        "Handles everything from leaky taps to full bathroom renovation.",
        "Learned plumbing in Saudi Arabia, came back and set up in {neighborhood}.",
        "Runs a small hardware shop on the side. Plumbing is the main income.",
        "Fixes water tanker connections and boring pumps. Specialized for {city}'s water issues.",
        "His wife handles the phone calls and scheduling. He just shows up and fixes things.",
        "Former sanitary worker who learned plumbing skills on the job. Very thorough.",
    ],
    "Electrician": [
        "Wiring specialist. Has done half the houses in {neighborhood}.",
        "DAE diploma but couldn't find factory work. Freelance electrical ever since.",
        "UPS and solar panel installations are his specialty. Good with inverters.",
        "Started rewinding motors in a shop. Now handles full house wiring.",
        "Night shift electrician at a factory, does private jobs during the day.",
        "Careful worker. Always tests everything twice before leaving.",
        "Known for fair pricing. Brings his own materials so you don't get overcharged.",
        "Handles high-tension connections that most electricians won't touch.",
        "Learned from his father who was a lineman at WAPDA. Practical knowledge, no degree.",
        "Moved to {city} from Mianwali. Built up his clientele through word of mouth.",
    ],
    "Tutor": [
        "Retired school teacher. Still sharp. Teaches math and science to matric students.",
        "BA in English Literature. Tutors O-level and A-level English from home.",
        "College student earning her way through fees by tutoring neighborhood kids.",
        "Former government school headmaster. Strict but effective.",
        "Quran teacher who also helps with Urdu and Islamiat homework.",
        "Engineering dropout. Teaches physics and math better than most degree holders.",
        "Runs a small tuition center from her house in {neighborhood}. 30 students.",
        "Teaches basic computer skills — MS Office, typing, internet basics.",
        "Hafiz who also tutors Arabic and basic English. Popular with madrassah families.",
        "MA in Urdu literature. Specializes in board exam preparation.",
    ],
    "Beautician": [
        "Home-based salon in {neighborhood}. Bridal makeup is her specialty.",
        "Trained at a beauty academy in {city}. Now works independently.",
        "Does mehndi for weddings across {city}. Gets booked months in advance.",
        "Basic beauty services — threading, facials, waxing. Affordable rates.",
        "Learned from her mother. Three generations of beauticians in the family.",
        "Specializes in bridal packages. Known for not overselling services.",
        "Does house calls for elderly women who can't come to a salon.",
        "Part-time beautician, part-time school teacher. Evenings and weekends only.",
        "Expert in hair treatments and styling. Uses mostly local products.",
        "Started during COVID when salons were closed. Never went back to office work.",
    ],
}

# ── Slot generator ───────────────────────────────────────────────────────────

def generate_slots(n=None):
    """Generate realistic available time slots."""
    if n is None:
        n = random.randint(2, 8)
    slots = []
    for day_offset in random.sample(range(1, 10), min(n, 9)):
        hour = random.choice([9, 10, 11, 14, 15, 16, 17, 18])
        slots.append(f"2026-05-{19 + day_offset:02d}T{hour:02d}:00:00+05:00")
    slots.sort()
    return slots


# ── Provider generator ───────────────────────────────────────────────────────

def pick_culture(city):
    """Pick a cultural_background based on city demographics."""
    options = CITY_CULTURES[city]
    cultures, weights = zip(*options)
    return random.choices(cultures, weights=weights, k=1)[0]


def pick_name(gender, culture):
    """Generate a realistic name."""
    if gender == "female":
        first = random.choice(FEMALE_FIRST)
    else:
        first = random.choice(MALE_FIRST)

    # Sometimes add a regional surname
    if culture and culture in REGIONAL_SURNAMES and random.random() < 0.5:
        surname = random.choice(REGIONAL_SURNAMES[culture])
        return f"{first} {surname}"
    elif random.random() < 0.3:
        surname = random.choice([s for s in SURNAMES_COMMON if s])
        return f"{first} {surname}"
    return first


def pick_bio(category, city, neighborhood, years):
    """Pick and customize a bio template."""
    template = random.choice(BIO_TEMPLATES[category])
    return template.format(
        years=years,
        city=city,
        neighborhood=neighborhood.split(",")[0],
    )


def generate_providers():
    """Generate all 100 providers."""
    # City distribution: Isb:5, Rwp:15, Lhr:20, Fsd:20, Khi:10, Qta:10, Psh:10, Glt:10
    city_counts = {
        "Islamabad": 5,
        "Rawalpindi": 15,
        "Lahore": 20,
        "Faisalabad": 20,
        "Karachi": 10,
        "Quetta": 10,
        "Peshawar": 10,
        "Gilgit": 10,
    }

    providers = []
    pid = 1
    used_names = set()

    for city, count in city_counts.items():
        for i in range(count):
            neighborhood_data = random.choice(NEIGHBORHOODS[city])
            sector, base_lat, base_lng = neighborhood_data

            # Small coordinate jitter for realism
            lat = round(base_lat + random.uniform(-0.003, 0.003), 4)
            lng = round(base_lng + random.uniform(-0.003, 0.003), 4)

            category = random.choice(CATEGORIES)

            # Gender: beauticians are mostly female, others mostly male
            if category == "Beautician":
                gender = "female" if random.random() < 0.85 else "male"
            elif category == "Tutor":
                gender = "female" if random.random() < 0.3 else "male"
            else:
                gender = "female" if random.random() < 0.05 else "male"

            culture = pick_culture(city)

            # Generate unique name
            for _ in range(20):
                name = pick_name(gender, culture)
                if name not in used_names:
                    used_names.add(name)
                    break

            years_exp = max(1, min(40, int(random.gauss(12, 6))))
            languages = random.choice(CITY_LANGUAGES[city])
            rating = round(random.uniform(3.0, 4.9), 1)
            rating_count = random.randint(5, 220)
            verified = random.random() < 0.7
            price_min = random.choice([500, 800, 1000, 1200, 1500, 2000, 2500, 3000])
            price_max = price_min + random.choice([1500, 2000, 2500, 3000, 4000, 5000])

            bio = pick_bio(category, city, sector, years_exp)

            provider = {
                "id": f"P{pid:04d}",
                "name": name,
                "category": category,
                "sector": sector,
                "home_city": city,
                "lat": lat,
                "lng": lng,
                "rating": rating,
                "rating_count": rating_count,
                "price_range": {
                    "min": price_min,
                    "max": price_max,
                    "currency": "PKR",
                },
                "available_slots": generate_slots(),
                "verified": verified,
                "languages_spoken": languages,
                "bio": bio,
                "years_experience": years_exp,
                "cultural_background": culture,
                "_synthetic": True,
            }

            providers.append(provider)
            pid += 1

    # ── Edge cases ────────────────────────────────────────────────────────

    # Edge case 1: Low rating (preserving P0017 intent)
    providers[16]["rating"] = 2.1
    providers[16]["rating_count"] = 9
    providers[16]["verified"] = False
    providers[16]["bio"] = "Shows up late, but cheap. You get what you pay for."
    providers[16]["price_range"] = {"min": 500, "max": 1500, "currency": "PKR"}

    # Edge case 2: No slots (preserving P0033 intent)
    providers[32]["available_slots"] = []
    providers[32]["bio"] = "Fully booked for the season. Try again next month."
    providers[32]["rating"] = 4.5
    providers[32]["rating_count"] = 83

    # Edge case 3: Overlapping expertise (preserving P0008/P0029 intent)
    providers[7]["notes"] = "Also experienced in electrical wiring and switchboard repair"
    providers[7]["bio"] = "Started in AC work but picked up electrical along the way. Does both now."
    providers[28]["notes"] = "Also does plumbing work — previously trained as a plumber"
    providers[28]["bio"] = "Trained as a plumber first, then moved to electrical. Still takes plumbing jobs."

    # Edge case 4: Misleading name (preserving P0047 intent)
    providers[46]["name"] = "Noor Electric & Sons"
    providers[46]["category"] = "Beautician"
    providers[46]["bio"] = "The shop name is from her husband's electrical business. She runs beauty services from the same building."

    # Edge case 5: NEW — Bio implies different specialty than category
    providers[49]["category"] = "Tutor"
    providers[49]["bio"] = "Famous for stitching bridal lehengas for Lahori weddings. Also tutors Urdu literature to college girls in the evenings."
    providers[49]["name"] = "Nasreen Akhtar"

    return providers


if __name__ == "__main__":
    providers = generate_providers()
    out_path = Path(__file__).parent / "providers.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(providers, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(providers)} providers -> {out_path}")

    # Verify distribution
    from collections import Counter
    city_dist = Counter(p["home_city"] for p in providers)
    print(f"City distribution: {dict(city_dist)}")
    print(f"With cultural_background: {sum(1 for p in providers if p['cultural_background'])}")
    print(f"Categories: {dict(Counter(p['category'] for p in providers))}")
