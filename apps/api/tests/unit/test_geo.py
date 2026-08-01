"""
Unit tests for OpenRouteService & OpenStreetMap Geocoding and Driving ETA Calculation Module.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.core.geo import (
    haversine_distance_km,
    geocode_address,
    get_driving_duration_and_distance,
    calculate_delivery_eta,
)


def test_haversine_distance():
    # Distance between T. Nagar (13.0405, 80.2337) and Anna Nagar (13.0850, 80.2101)
    dist = haversine_distance_km(13.0405, 80.2337, 13.0850, 80.2101)
    assert 4.0 <= dist <= 7.0


@pytest.mark.asyncio
async def test_geocode_address_fallback_nominatim():
    coords = await geocode_address("T. Nagar, Chennai")
    assert coords is not None
    lat, lon = coords
    assert 12.5 <= lat <= 13.5
    assert 79.5 <= lon <= 80.5


@pytest.mark.asyncio
async def test_calculate_delivery_eta_pipeline():
    # Test ETA calculation from T. Nagar to Tinnanur
    eta_mins, dist_km = await calculate_delivery_eta(
        shop_lat=13.0405,
        shop_lon=80.2337,
        delivery_address="Tinnanur, Tamil Nadu",
        default_prep_time=15,
    )
    assert eta_mins > 15  # Prep time + driving duration > 15 mins
    assert dist_km >= 0.0


@pytest.mark.asyncio
async def test_calculate_delivery_eta_empty_address():
    eta_mins, dist_km = await calculate_delivery_eta(
        shop_lat=13.0405,
        shop_lon=80.2337,
        delivery_address="",
        default_prep_time=20,
    )
    assert eta_mins == 35  # 20 prep + 15 default fallback
    assert dist_km == 0.0
