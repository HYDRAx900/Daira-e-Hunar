"""
Geo Service unit tests — no LLM calls, no rate limit delays.

Tests Haversine distance accuracy and location resolution logic.
"""

import pytest

from backend.services.geo_service import (
    get_distance_km,
    resolve_user_location,
    KNOWN_LOCATIONS,
    CITY_CENTROIDS,
)


# ── Test 1: Haversine accuracy ──────────────────────────────────────────────

def test_haversine_islamabad_to_lahore():
    """Distance between Islamabad and Lahore centroids ~275 km (road ~375, air ~275)."""
    isb = CITY_CENTROIDS["Islamabad"]
    lhr = CITY_CENTROIDS["Lahore"]
    distance = get_distance_km(isb, lhr)

    # Great-circle distance Islamabad-Lahore is approximately 275 km
    assert 250 < distance < 310, f"Expected ~275 km, got {distance:.1f} km"


# ── Test 2: Neighborhood resolution ─────────────────────────────────────────

def test_resolve_neighborhood():
    """Full sector string resolves to known coordinates."""
    coords = resolve_user_location("Lyari, Karachi", "Karachi")
    assert coords is not None
    lat, lng = coords
    # Lyari is in Karachi — lat ~24.85, lng ~67.01
    assert 24.0 < lat < 26.0
    assert 66.0 < lng < 68.0


# ── Test 3: City-only resolution ────────────────────────────────────────────

def test_resolve_city_only():
    """City-only sector resolves to city centroid."""
    coords = resolve_user_location("Lahore", None)
    expected = CITY_CENTROIDS["Lahore"]
    assert coords == expected


# ── Test 4: None input ──────────────────────────────────────────────────────

def test_resolve_none():
    """Both None inputs resolve to None."""
    coords = resolve_user_location(None, None)
    assert coords is None


# ── Test 5: Short name resolution ───────────────────────────────────────────

def test_resolve_short_name():
    """Short neighborhood name resolves correctly."""
    coords = resolve_user_location("Misri Shah", None)
    assert coords is not None
    assert coords == KNOWN_LOCATIONS["Misri Shah"]


# ── Test 6: Fallback to home_city ───────────────────────────────────────────

def test_resolve_fallback_home_city():
    """Unknown sector falls back to home_city centroid."""
    coords = resolve_user_location("Unknown Place", "Quetta")
    expected = CITY_CENTROIDS["Quetta"]
    assert coords == expected
