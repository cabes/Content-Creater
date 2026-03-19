"""Calendar-based topic sources: celestial events, holidays, seasonal markers."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger()


# Major celestial/astrological events (simplified - in production, use kerykeion)
CELESTIAL_EVENTS = {
    # Mercury retrograde periods 2025-2026 (approximate)
    "mercury_retrograde": [
        {"start": "2025-03-15", "end": "2025-04-07", "sign": "Aries"},
        {"start": "2025-07-18", "end": "2025-08-11", "sign": "Leo"},
        {"start": "2025-11-09", "end": "2025-11-29", "sign": "Sagittarius"},
        {"start": "2026-03-02", "end": "2026-03-25", "sign": "Pisces"},
    ],
    # Eclipse seasons
    "eclipses": [
        {"date": "2025-03-29", "type": "partial_solar", "sign": "Aries"},
        {"date": "2025-09-21", "type": "total_lunar", "sign": "Pisces"},
        {"date": "2026-02-17", "type": "annular_solar", "sign": "Aquarius"},
    ],
    # Solstices and equinoxes
    "solar_terms": [
        {"date": "2025-03-20", "event": "vernal_equinox"},
        {"date": "2025-06-21", "event": "summer_solstice"},
        {"date": "2025-09-22", "event": "autumnal_equinox"},
        {"date": "2025-12-21", "event": "winter_solstice"},
        {"date": "2026-03-20", "event": "vernal_equinox"},
    ],
}

# Finance calendar events
FINANCE_EVENTS = [
    {"name": "FOMC Meeting", "dates": ["2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-17"]},
    {"name": "US CPI Release", "recurrence": "monthly_10th"},
    {"name": "Earnings Season", "periods": [{"start": "2025-01-15", "end": "2025-02-15"}, {"start": "2025-04-15", "end": "2025-05-15"}]},
]


def get_upcoming_events(
    domain: str,
    days_ahead: int = 7,
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    """Get calendar events relevant to a domain within the next N days."""
    ref = reference_date or date.today()
    end = ref + timedelta(days=days_ahead)
    events: list[dict[str, Any]] = []

    if domain in ("mystical", "knowledge"):
        # Check celestial events
        for event_type, event_list in CELESTIAL_EVENTS.items():
            for event in event_list:
                event_date = _parse_date(event.get("date") or event.get("start", ""))
                if event_date and ref <= event_date <= end:
                    events.append({
                        "type": event_type,
                        "date": str(event_date),
                        "domain": "mystical",
                        "details": event,
                        "topic_hint": _celestial_topic_hint(event_type, event),
                    })

    if domain in ("finance",):
        for cal_event in FINANCE_EVENTS:
            for d_str in cal_event.get("dates", []):
                event_date = _parse_date(d_str)
                if event_date and ref <= event_date <= end:
                    events.append({
                        "type": "finance_calendar",
                        "date": str(event_date),
                        "domain": "finance",
                        "details": {"name": cal_event["name"]},
                        "topic_hint": f"即将到来: {cal_event['name']}",
                    })

    return events


def _parse_date(s: str) -> date | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _celestial_topic_hint(event_type: str, event: dict[str, Any]) -> str:
    hints = {
        "mercury_retrograde": f"水星逆行 in {event.get('sign', '?')} — 影响沟通与决策",
        "eclipses": f"{event.get('type', '')} eclipse in {event.get('sign', '?')} — 重大转变能量",
        "solar_terms": f"节气转换: {event.get('event', '')} — 能量周期更替",
    }
    return hints.get(event_type, str(event))
