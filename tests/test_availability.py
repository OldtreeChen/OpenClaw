import app.availability as availability
from app.models import AvailabilityProbeItem, AvailabilityProbeRequest


async def _fake_probe_available(url: str, timeout_sec: int):
    return ["18:00", "19:30"], False


async def _fake_probe_unavailable(url: str, timeout_sec: int):
    return [], True


def test_probe_batch_available(monkeypatch):
    monkeypatch.setattr(availability, "_probe_with_playwright", _fake_probe_available)
    payload = AvailabilityProbeRequest(
        items=[
            AvailabilityProbeItem(
                restaurant_name="A",
                party_size=2,
                reservation_date="2026-03-20",
                website_uri="https://inline.app/booking/a",
            )
        ]
    )

    result = availability.asyncio.run(availability.probe_availability_batch(payload))
    assert result.available_count == 1
    assert result.results[0].status == "available"
    assert result.results[0].available_times == ["18:00", "19:30"]


def test_probe_batch_fallback_for_unsupported_platform():
    payload = AvailabilityProbeRequest(
        items=[
            AvailabilityProbeItem(
                restaurant_name="B",
                party_size=2,
                reservation_date="2026-03-20",
                website_uri="https://example.com/booking",
                google_maps_uri="https://maps.google.com/?cid=1",
            )
        ]
    )

    result = availability.asyncio.run(availability.probe_availability_batch(payload))
    assert result.fallback_count == 1
    assert result.results[0].status == "fallback"


def test_probe_batch_unavailable(monkeypatch):
    monkeypatch.setattr(availability, "_probe_with_playwright", _fake_probe_unavailable)
    payload = AvailabilityProbeRequest(
        items=[
            AvailabilityProbeItem(
                restaurant_name="C",
                party_size=4,
                reservation_date="2026-03-21",
                website_uri="https://eztable.com/restaurant/c",
            )
        ]
    )

    result = availability.asyncio.run(availability.probe_availability_batch(payload))
    assert result.results[0].status == "unavailable"
