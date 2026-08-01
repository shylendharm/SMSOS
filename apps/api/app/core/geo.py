"""
OpenRouteService & OpenStreetMap Geocoding and Driving ETA Calculation Module.
Calculates dynamic food delivery ETAs based on actual driving distance and shop preparation time.
"""
import math
from typing import Optional, Tuple
import httpx
import structlog
from app.core.config import settings

logger = structlog.get_logger()

# Free OpenRouteService API endpoint
ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
ORS_GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate straight-line distance in kilometers using the Haversine formula."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


async def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Converts a text address into (latitude, longitude) fast with low timeouts.
    """
    if not address or not address.strip():
        return None

    import re
    # Fast regex clean Google Plus codes (e.g. 32P8+JRJ)
    clean_text = re.sub(r'^[A-Z0-9]{4,8}\+[A-Z0-9]{2,7}(,\s*)?', '', address.strip(), flags=re.IGNORECASE).strip()
    clean_text = clean_text.replace("/", ", ").replace("-", " ")
    
    if "india" not in clean_text.lower():
        query_text = f"{clean_text}, India"
    else:
        query_text = clean_text

    ors_key = getattr(settings, "ORS_API_KEY", None)

    # 1. OpenRouteService with tight 1.5s timeout
    if ors_key:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                resp = await client.get(
                    ORS_GEOCODE_URL,
                    params={
                        "api_key": ors_key,
                        "text": query_text,
                        "size": 1,
                        "boundary.country": "IND",
                    },
                )
                if resp.status_code == 200:
                    features = resp.json().get("features", [])
                    if features:
                        coords = features[0]["geometry"]["coordinates"]
                        lon, lat = float(coords[0]), float(coords[1])
                        # Reject generic center fallback (11.0, 78.3333)
                        if not (abs(lat - 11.0) < 0.1 and abs(lon - 78.3333) < 0.1):
                            logger.info("Geocoded address via ORS", address=address, lat=lat, lon=lon)
                            return (lat, lon)
        except Exception:
            pass

    # 2. Fallback to Nominatim with tight 1.5s timeout
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            headers = {"User-Agent": "SMSOS-DeliveryApp/1.0"}
            resp = await client.get(
                NOMINATIM_URL,
                params={"q": query_text, "format": "json", "limit": 1, "countrycodes": "in"},
                headers=headers,
            )
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    lat, lon = float(results[0]["lat"]), float(results[0]["lon"])
                    logger.info("Geocoded address via Nominatim", address=address, lat=lat, lon=lon)
                    return (lat, lon)
    except Exception:
        pass

    return None


async def get_driving_duration_and_distance(
    from_lat: float, from_lon: float, to_lat: float, to_lon: float
) -> Tuple[int, float]:
    """
    Calculates driving duration in minutes and distance in km between two GPS coordinates.
    Uses OpenRouteService Directions API if key configured, otherwise computes Haversine distance
    with an assumed average city driving speed of 25 km/h.
    """
    ors_key = getattr(settings, "ORS_API_KEY", None)

    if ors_key:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(
                    ORS_DIRECTIONS_URL,
                    params={
                        "api_key": ors_key,
                        "start": f"{from_lon},{from_lat}",
                        "end": f"{to_lon},{to_lat}",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    summary = data["features"][0]["properties"]["summary"]
                    duration_sec = summary.get("duration", 0)
                    distance_m = summary.get("distance", 0)

                    duration_mins = max(1, math.ceil(duration_sec / 60.0))
                    distance_km = round(distance_m / 1000.0, 2)
                    logger.info(
                        "Calculated driving route via ORS",
                        duration_mins=duration_mins,
                        distance_km=distance_km,
                    )
                    return (duration_mins, distance_km)
        except Exception as e:
            logger.warning("ORS Directions API call failed, falling back to Haversine calculation", error=str(e))

    # Fallback: Haversine distance + 25 km/h driving speed (+ 30% city traffic buffer)
    dist_km = haversine_distance_km(from_lat, from_lon, to_lat, to_lon)
    # 25 km/h = 0.416 km per min -> duration = dist / 0.416
    travel_mins = max(5, math.ceil((dist_km / 25.0) * 60.0 * 1.3))
    return (travel_mins, dist_km)


async def calculate_delivery_eta(
    shop_lat: Optional[float],
    shop_lon: Optional[float],
    delivery_address: Optional[str],
    default_prep_time: int = 15,
) -> Tuple[int, float]:
    """
    Full delivery ETA calculation pipeline:
    1. Geocodes customer delivery location.
    2. Calculates driving duration from shop to customer.
    3. Returns (total_eta_minutes, distance_km).
    """
    if not delivery_address or not delivery_address.strip():
        # Default fallback ETA if no address provided
        return (default_prep_time + 15, 0.0)

    # Default Chennai T. Nagar coordinates if shop lat/lon not set yet
    base_shop_lat = shop_lat if shop_lat is not None else 13.0405
    base_shop_lon = shop_lon if shop_lon is not None else 80.2337

    cust_coords = await geocode_address(delivery_address)
    if not cust_coords:
        # Fallback ETA if geocoding returns no result
        return (default_prep_time + 15, 5.0)

    cust_lat, cust_lon = cust_coords
    driving_mins, dist_km = await get_driving_duration_and_distance(
        base_shop_lat, base_shop_lon, cust_lat, cust_lon
    )

    total_eta = default_prep_time + driving_mins
    return (total_eta, dist_km)
