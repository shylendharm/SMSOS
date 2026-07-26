"""
Reservation Service — Conflict Detection, Table Allocation, and Alternative Slot Finder.

This module contains the core logic for the Smart Conflict-Free Table Reservation system.
It prevents double-bookings by detecting time-window overlaps, automatically assigns
the lowest available table number, and suggests alternative open slots when the
requested time is fully booked.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models.reservation import Reservation
from app.db.models.business import BusinessSettings


async def get_business_settings(db: AsyncSession, business_id: uuid.UUID) -> Optional[BusinessSettings]:
    """Fetch business settings for a given business."""
    res = await db.execute(
        select(BusinessSettings).where(BusinessSettings.business_id == business_id)
    )
    return res.scalars().first()


async def get_overlapping_reservations(
    db: AsyncSession,
    business_id: uuid.UUID,
    target_start: datetime,
    duration_minutes: int,
) -> List[Reservation]:
    """
    Fetch all active (confirmed/seated) reservations for a business
    that overlap with the time window [target_start, target_start + duration].
    
    Overlap condition: existing.reserved_at < target_end AND existing_end > target_start
    """
    target_end = target_start + timedelta(minutes=duration_minutes)

    result = await db.execute(
        select(Reservation).where(
            Reservation.business_id == business_id,
            Reservation.status.in_(["confirmed", "seated"]),
            # Overlap: existing start < our end AND existing end > our start
            Reservation.reserved_at < target_end,
        )
    )
    all_active = result.scalars().all()

    # Filter in Python for the second overlap condition (existing_end > target_start)
    overlapping = []
    for r in all_active:
        existing_end = r.reserved_at + timedelta(minutes=r.duration_minutes)
        if existing_end > target_start:
            overlapping.append(r)

    return overlapping


async def check_table_availability(
    db: AsyncSession,
    business_id: uuid.UUID,
    target_datetime: datetime,
    duration_minutes: int = 90,
) -> Tuple[int, int, List[str], List[str]]:
    """
    Check table availability for a specific time window.
    
    Returns:
        (total_tables, occupied_count, occupied_table_names, available_table_names)
    """
    settings = await get_business_settings(db, business_id)
    total_tables = (settings.table_count if settings and settings.table_count else 10)
    slot_duration = (settings.reservation_slot_duration if settings else 90) or duration_minutes

    overlapping = await get_overlapping_reservations(db, business_id, target_datetime, slot_duration)

    # Collect occupied table names
    occupied_table_names = set()
    for r in overlapping:
        if r.table_or_slot:
            for t_part in r.table_or_slot.split(","):
                t_clean = t_part.strip()
                if t_clean:
                    occupied_table_names.add(t_clean)

    # Build full table name list
    all_table_names = [f"Table {i}" for i in range(1, total_tables + 1)]
    available_table_names = [t for t in all_table_names if t not in occupied_table_names]

    return (
        total_tables,
        len(occupied_table_names),
        sorted(occupied_table_names),
        available_table_names,
    )


async def allocate_table_number(
    db: AsyncSession,
    business_id: uuid.UUID,
    target_datetime: datetime,
    duration_minutes: int = 90,
    party_size: int = 2,
    seats_per_table: int = 4,
) -> Optional[str]:
    """
    Automatically allocate table(s) for a reservation based on party size.
    Each table seats `seats_per_table` people (default 4).
    A party of 10 needs ceil(10/4) = 3 tables.
    Returns a comma-separated table name string (e.g. "Table 1, Table 3") or None if not enough tables.
    """
    import math
    tables_needed = max(1, math.ceil(party_size / seats_per_table))

    _, _, _, available = await check_table_availability(
        db, business_id, target_datetime, duration_minutes
    )
    if len(available) >= tables_needed:
        return ", ".join(available[:tables_needed])
    return None


async def find_alternative_slots(
    db: AsyncSession,
    business_id: uuid.UUID,
    target_datetime: datetime,
    duration_minutes: int = 90,
    max_suggestions: int = 3,
) -> List[str]:
    """
    Find nearby available time slots on the same day when the requested slot is full.
    Searches in 30-minute increments both before and after the requested time.
    
    Returns list of available time strings (e.g., ["5:30 PM", "8:30 PM"]).
    """
    settings = await get_business_settings(db, business_id)
    slot_duration = (settings.reservation_slot_duration if settings else 90) or duration_minutes

    # Get opening/closing hours
    opening_str = (settings.opening_time if settings else "10:00") or "10:00"
    closing_str = (settings.closing_time if settings else "22:00") or "22:00"

    try:
        open_h, open_m = map(int, opening_str.split(":"))
        close_h, close_m = map(int, closing_str.split(":"))
    except (ValueError, AttributeError):
        open_h, open_m = 10, 0
        close_h, close_m = 22, 0

    target_date = target_datetime.date()
    tz = target_datetime.tzinfo or timezone.utc

    opening_dt = datetime(target_date.year, target_date.month, target_date.day, open_h, open_m, tzinfo=tz)
    closing_dt = datetime(target_date.year, target_date.month, target_date.day, close_h, close_m, tzinfo=tz)

    suggestions = []
    offsets = [-30, 30, -60, 60, -90, 90, -120, 120, -150, 150, -180, 180]

    for offset_min in offsets:
        candidate = target_datetime + timedelta(minutes=offset_min)

        # Skip if outside operating hours
        if candidate < opening_dt or candidate >= closing_dt:
            continue

        # Skip past times
        if candidate < datetime.now(tz):
            continue

        total, occupied, _, available = await check_table_availability(
            db, business_id, candidate, slot_duration
        )

        if available:
            try:
                time_str = candidate.strftime("%I:%M %p").lstrip("0")
            except Exception:
                time_str = candidate.strftime("%H:%M")
            suggestions.append(time_str)

        if len(suggestions) >= max_suggestions:
            break

    return suggestions


async def get_day_occupancy_matrix(
    db: AsyncSession,
    business_id: uuid.UUID,
    target_date: datetime,
    duration_minutes: int = 90,
) -> List[dict]:
    """
    Build an hourly occupancy matrix for a given date.
    Returns a list of dicts: [{hour: "10:00 AM", total: 10, occupied: 3, available: 7}, ...]
    """
    settings = await get_business_settings(db, business_id)
    total_tables = (settings.table_count if settings and settings.table_count else 10)
    slot_duration = (settings.reservation_slot_duration if settings else 90) or duration_minutes

    opening_str = (settings.opening_time if settings else "10:00") or "10:00"
    closing_str = (settings.closing_time if settings else "22:00") or "22:00"

    try:
        open_h, open_m = map(int, opening_str.split(":"))
        close_h, close_m = map(int, closing_str.split(":"))
    except (ValueError, AttributeError):
        open_h, open_m = 10, 0
        close_h, close_m = 22, 0

    d = target_date.date() if isinstance(target_date, datetime) else target_date
    tz = target_date.tzinfo or timezone.utc

    matrix = []
    current_h = open_h
    while current_h < close_h:
        slot_start = datetime(d.year, d.month, d.day, current_h, 0, tzinfo=tz)

        overlapping = await get_overlapping_reservations(db, business_id, slot_start, slot_duration)

        occupied_tables = set()
        table_details = []
        for r in overlapping:
            if r.table_or_slot:
                for t_part in r.table_or_slot.split(","):
                    t_clean = t_part.strip()
                    if t_clean:
                        occupied_tables.add(t_clean)
                        table_details.append({
                            "table": t_clean,
                            "customer": r.customer_name or "Guest",
                            "party_size": r.party_size,
                            "time": r.reserved_at.strftime("%I:%M %p").lstrip("0"),
                            "duration": r.duration_minutes,
                        })

        occupied_count = len(occupied_tables)

        try:
            hour_label = slot_start.strftime("%I:%M %p").lstrip("0")
        except Exception:
            hour_label = f"{current_h}:00"

        matrix.append({
            "hour": hour_label,
            "hour_24": f"{current_h:02d}:00",
            "total": total_tables,
            "occupied": occupied_count,
            "available": total_tables - occupied_count,
            "tables": table_details,
        })

        current_h += 1

    return matrix
