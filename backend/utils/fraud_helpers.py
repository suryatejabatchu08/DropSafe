"""
DropSafe Fraud Detection Helpers
Mock GPS locations and platform activity for fraud testing
"""

import random
import math
from typing import Tuple


# Fixed seed per worker_id for testing consistency
# Each worker gets reproducible "random" location and activity
def _get_seed_for_worker(worker_id: str) -> int:
    """Generate deterministic seed from worker_id (for consistent mock data)."""
    return int(worker_id.replace("-", "")[:8], 16) % (2**31)


async def get_mock_worker_location(
    worker_id: str, zone_lat: float, zone_lon: float
) -> Tuple[float, float]:
    """
    Generate mock worker GPS location.

    Distribution:
    - 85% chance: Within zone (within 5km)
    - 15% chance: Outside zone (5-15km away in random direction)

    Used for GPS Zone Check in fraud detection.

    Args:
        worker_id: Worker UUID (used for seeded randomness)
        zone_lat: Zone center latitude
        zone_lon: Zone center longitude

    Returns:
        Tuple of (latitude, longitude)
    """
    try:
        rng = random.Random(_get_seed_for_worker(worker_id))

        # 85% in zone, 15% outside
        if rng.random() < 0.85:
            # In zone: random point within 5km
            # Use random bearing and distance
            bearing = rng.uniform(0, 360)
            distance_km = rng.uniform(0, 5.0)
        else:
            # Outside zone: 5-15km away
            bearing = rng.uniform(0, 360)
            distance_km = rng.uniform(5.0, 15.0)

        # Convert to lat/lon offset
        # Approximate: 1 degree ≈ 111km
        lat_offset = (distance_km / 111.0) * math.cos(math.radians(bearing))
        lon_offset = (
            (distance_km / 111.0)
            * math.sin(math.radians(bearing))
            / math.cos(math.radians(zone_lat))
        )

        worker_lat = zone_lat + lat_offset
        worker_lon = zone_lon + lon_offset

        return round(worker_lat, 6), round(worker_lon, 6)

    except Exception as e:
        print(f"[WARNING] Error generating mock location: {e}")
        # Return zone center as default
        return zone_lat, zone_lon


async def get_mock_platform_activity(worker_id: str) -> float:
    """
    Generate mock platform activity rate during disruption window.

    Distribution:
    - 90% activity rate simulated (how many orders worker delivered during disruption)
    - Returns 0.0-1.0 (0% = no activity, 1.0 = fully active)

    Used for Platform Activity Check and Order Volume Contradiction checks.

    Args:
        worker_id: Worker UUID (used for seeded randomness)

    Returns:
        Activity rate (0.0-1.0)
    """
    try:
        rng = random.Random(_get_seed_for_worker(worker_id))

        # 90% mean activity with some variance
        # Most workers have 85-95% activity, some 0% (off app)
        if rng.random() < 0.10:
            # 10% chance: completely off app
            activity = rng.uniform(0.0, 0.1)
        else:
            # 90% chance: normal activity (80-100%)
            activity = rng.uniform(0.80, 1.0)

        return round(activity, 2)

    except Exception as e:
        print(f"[WARNING] Error generating mock activity: {e}")
        return 0.9  # Default to normal activity


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.

    Args:
        lat1, lon1: First point (zone center)
        lat2, lon2: Second point (worker location)

    Returns:
        Distance in kilometers
    """
    try:
        # Earth radius in km
        R = 6371.0

        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        distance = R * c

        return round(distance, 2)

    except Exception as e:
        print(f"[WARNING] Error calculating haversine distance: {e}")
        return 0.0
