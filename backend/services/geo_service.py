"""
Geo Service — centralized location resolution and distance computation.

This is the ONLY module that computes distances. Both Discovery and Ranking
agents import from here. Designed so Google Maps Distance Matrix can swap
in later behind the same interface.
"""

import math
from typing import Optional

# ── Haversine distance ───────────────────────────────────────────────────────

_EARTH_RADIUS_KM = 6371.0


def get_distance_km(
    point_a: tuple[float, float],
    point_b: tuple[float, float],
) -> float:
    """
    Compute the Haversine great-circle distance between two lat/lng points.

    Args:
        point_a: (latitude, longitude) in decimal degrees.
        point_b: (latitude, longitude) in decimal degrees.

    Returns:
        Distance in kilometers.
    """
    lat1, lng1 = math.radians(point_a[0]), math.radians(point_a[1])
    lat2, lng2 = math.radians(point_b[0]), math.radians(point_b[1])

    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return _EARTH_RADIUS_KM * c


# ── Known locations ──────────────────────────────────────────────────────────
# Base coordinates from generate_providers.py (neighborhood centroids).
# Keyed by BOTH full sector string and short neighborhood name for flexible
# matching from Intent Agent output.

KNOWN_LOCATIONS: dict[str, tuple[float, float]] = {
    # Islamabad
    "G-7, Islamabad":   (33.7100, 73.0480),
    "G-7":              (33.7100, 73.0480),
    "G-9, Islamabad":   (33.6930, 73.0390),
    "G-9":              (33.6930, 73.0390),
    "I-9, Islamabad":   (33.6680, 73.0460),
    "I-9":              (33.6680, 73.0460),
    "I-10, Islamabad":  (33.6420, 73.0200),
    "I-10":             (33.6420, 73.0200),
    # Rawalpindi
    "Tench Bhata, Rawalpindi": (33.5870, 73.0680),
    "Tench Bhata":             (33.5870, 73.0680),
    "Dhok Khabba, Rawalpindi": (33.5750, 73.0550),
    "Dhok Khabba":             (33.5750, 73.0550),
    "Raja Bazaar, Rawalpindi": (33.5980, 73.0470),
    "Raja Bazaar":             (33.5980, 73.0470),
    "Pirwadhai, Rawalpindi":   (33.6150, 73.0630),
    "Pirwadhai":               (33.6150, 73.0630),
    "Saddar, Rawalpindi":      (33.5960, 73.0510),
    "Saddar":                  (33.5960, 73.0510),
    # Lahore
    "Misri Shah, Lahore":   (31.5780, 74.3190),
    "Misri Shah":           (31.5780, 74.3190),
    "Shadbagh, Lahore":     (31.5850, 74.3250),
    "Shadbagh":             (31.5850, 74.3250),
    "Garhi Shahu, Lahore":  (31.5560, 74.3470),
    "Garhi Shahu":          (31.5560, 74.3470),
    "Daroghewala, Lahore":  (31.5950, 74.3100),
    "Daroghewala":          (31.5950, 74.3100),
    "Mochi Gate, Lahore":   (31.5830, 74.3220),
    "Mochi Gate":           (31.5830, 74.3220),
    "Lohari Gate, Lahore":  (31.5790, 74.3170),
    "Lohari Gate":          (31.5790, 74.3170),
    "Bhatti Gate, Lahore":  (31.5810, 74.3240),
    "Bhatti Gate":          (31.5810, 74.3240),
    # Faisalabad
    "Ghulam Mohammadabad, Faisalabad": (31.4180, 73.0790),
    "Ghulam Mohammadabad":             (31.4180, 73.0790),
    "Jhang Bazaar, Faisalabad":        (31.4160, 73.0730),
    "Jhang Bazaar":                    (31.4160, 73.0730),
    "Madina Town, Faisalabad":         (31.3950, 73.0840),
    "Madina Town":                     (31.3950, 73.0840),
    "D-Ground, Faisalabad":            (31.4250, 73.0900),
    "D-Ground":                        (31.4250, 73.0900),
    "Rail Bazaar, Faisalabad":         (31.4190, 73.0810),
    "Rail Bazaar":                     (31.4190, 73.0810),
    # Karachi
    "Lyari, Karachi":       (24.8520, 67.0120),
    "Lyari":                (24.8520, 67.0120),
    "Orangi, Karachi":      (24.9310, 66.9840),
    "Orangi":               (24.9310, 66.9840),
    "Korangi, Karachi":     (24.8380, 67.1310),
    "Korangi":              (24.8380, 67.1310),
    "Landhi, Karachi":      (24.8540, 67.1560),
    "Landhi":               (24.8540, 67.1560),
    "Baldia Town, Karachi": (24.9130, 66.9620),
    "Baldia Town":          (24.9130, 66.9620),
    # Quetta
    "Pashtunabad, Quetta":      (30.1970, 67.0050),
    "Pashtunabad":              (30.1970, 67.0050),
    "Hazara Town, Quetta":      (30.1620, 66.9810),
    "Hazara Town":              (30.1620, 66.9810),
    "Kandahari Bazaar, Quetta": (30.1880, 66.9960),
    "Kandahari Bazaar":         (30.1880, 66.9960),
    "Jinnah Road, Quetta":      (30.1910, 67.0010),
    "Jinnah Road":              (30.1910, 67.0010),
    # Peshawar
    "Hashtnagri, Peshawar": (34.0120, 71.5710),
    "Hashtnagri":           (34.0120, 71.5710),
    "Kohati Gate, Peshawar": (34.0050, 71.5680),
    "Kohati Gate":           (34.0050, 71.5680),
    "Qissa Khwani, Peshawar": (34.0100, 71.5750),
    "Qissa Khwani":           (34.0100, 71.5750),
    "Faqirabad, Peshawar":  (34.0200, 71.5640),
    "Faqirabad":            (34.0200, 71.5640),
    # Gilgit
    "Konodas, Gilgit":     (35.9210, 74.3080),
    "Konodas":             (35.9210, 74.3080),
    "Jutial, Gilgit":      (35.9250, 74.3200),
    "Jutial":              (35.9250, 74.3200),
    "Kashrote, Gilgit":    (35.9190, 74.3150),
    "Kashrote":            (35.9190, 74.3150),
    "Danyor, Gilgit":      (35.9130, 74.3740),
    "Danyor":              (35.9130, 74.3740),
    "Main Bazaar, Gilgit": (35.9200, 74.3120),
    "Main Bazaar":         (35.9200, 74.3120),
}


# ── City centroids ───────────────────────────────────────────────────────────

CITY_CENTROIDS: dict[str, tuple[float, float]] = {
    "Islamabad":   (33.6844, 73.0479),
    "Rawalpindi":  (33.5651, 73.0169),
    "Lahore":      (31.5204, 74.3587),
    "Faisalabad":  (31.4187, 73.0791),
    "Karachi":     (24.8607, 67.0011),
    "Quetta":      (30.1798, 66.9750),
    "Peshawar":    (34.0151, 71.5249),
    "Gilgit":      (35.9208, 74.3144),
}


# ── Location resolver ────────────────────────────────────────────────────────

def resolve_user_location(
    location_sector: Optional[str],
    home_city: Optional[str] = None,
) -> Optional[tuple[float, float]]:
    """
    Best-effort resolution of a user's location to (lat, lng).

    Resolution cascade:
        1. Exact match in KNOWN_LOCATIONS (e.g. "Lyari, Karachi")
        2. Short-name match in KNOWN_LOCATIONS (e.g. "Lyari")
        3. City centroid match in CITY_CENTROIDS (e.g. "Lahore")
        4. Fall back to home_city centroid
        5. Return None if nothing resolves

    Args:
        location_sector: The location_sector string from IntentResult.
        home_city: The home_city or target city, if known.

    Returns:
        (lat, lng) tuple, or None if unresolvable.
    """
    if location_sector is not None:
        # 1. Exact match
        if location_sector in KNOWN_LOCATIONS:
            return KNOWN_LOCATIONS[location_sector]

        # 2. Short-name match (strip city suffix if present)
        short_name = location_sector.split(",")[0].strip()
        if short_name in KNOWN_LOCATIONS:
            return KNOWN_LOCATIONS[short_name]

        # 3. City centroid (handles "Lahore", "Karachi" as sector)
        if location_sector in CITY_CENTROIDS:
            return CITY_CENTROIDS[location_sector]

    # 4. Fall back to home_city centroid
    if home_city and home_city in CITY_CENTROIDS:
        return CITY_CENTROIDS[home_city]

    return None
