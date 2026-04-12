import pytest

import app.booking as booking
from app.booking import BOOKINGS, cancel_booking, create_booking
from app.models import BookingCancelRequest, BookingCreateRequest


def setup_function() -> None:
    BOOKINGS.clear()


def test_inline_create_and_cancel_dry_run() -> None:
    created = create_booking(
        BookingCreateRequest(
            provider="inline",
            restaurant_name="Test Inline Restaurant",
            reservation_time="2026-03-10T19:00:00+08:00",
            party_size=2,
            contact_name="Alex",
            contact_phone="0912345678",
            dry_run=True,
        )
    )

    assert created.status == "simulated"
    assert created.provider == "inline"
    assert created.reservation_id.startswith("inline_")

    cancelled = cancel_booking(
        BookingCancelRequest(
            provider="inline",
            reservation_id=created.reservation_id,
            dry_run=True,
        )
    )

    assert cancelled.status == "simulated"


def test_eztable_create_and_cancel_dry_run() -> None:
    created = create_booking(
        BookingCreateRequest(
            provider="eztable",
            restaurant_name="Test EZTABLE Restaurant",
            reservation_time="2026-03-10T20:00:00+08:00",
            party_size=4,
            contact_name="Jamie",
            contact_phone="0922333444",
            dry_run=True,
        )
    )

    assert created.status == "simulated"
    assert created.provider == "eztable"
    assert created.reservation_id.startswith("eztable_")

    cancelled = cancel_booking(
        BookingCancelRequest(
            provider="eztable",
            reservation_id=created.reservation_id,
            dry_run=True,
        )
    )

    assert cancelled.status == "simulated"


def test_inline_live_create_uses_provider_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(booking.settings, "inline_api_key", "token")
    monkeypatch.setattr(booking.settings, "inline_base_url", "https://api.inline.test")

    def fake_provider_request(provider: str, path: str, payload: dict) -> dict:
        assert provider == "inline"
        assert path == booking.settings.inline_create_path
        assert payload["restaurant_name"] == "Live Inline Restaurant"
        return {"reservation_id": "inl_123", "status": "confirmed"}

    monkeypatch.setattr(booking, "_provider_request", fake_provider_request)

    created = create_booking(
        BookingCreateRequest(
            provider="inline",
            restaurant_name="Live Inline Restaurant",
            reservation_time="2026-03-12T19:30:00+08:00",
            party_size=2,
            contact_name="Alex",
            contact_phone="0911111111",
            dry_run=False,
        )
    )

    assert created.status == "confirmed"
    assert created.reservation_id == "inl_123"


def test_inline_live_cancel_uses_provider_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(booking.settings, "inline_api_key", "token")
    monkeypatch.setattr(booking.settings, "inline_base_url", "https://api.inline.test")

    def fake_provider_request(provider: str, path: str, payload: dict) -> dict:
        assert provider == "inline"
        assert "abc123" in path
        assert payload["reservation_id"] == "abc123"
        return {"status": "cancelled"}

    monkeypatch.setattr(booking, "_provider_request", fake_provider_request)

    cancelled = cancel_booking(
        BookingCancelRequest(
            provider="inline",
            reservation_id="abc123",
            dry_run=False,
        )
    )

    assert cancelled.status == "cancelled"


def test_inline_live_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(booking.settings, "inline_api_key", "")
    monkeypatch.setattr(booking.settings, "inline_base_url", "https://api.inline.test")

    with pytest.raises(ValueError, match="inline API key"):
        create_booking(
            BookingCreateRequest(
                provider="inline",
                restaurant_name="Need Key",
                reservation_time="2026-03-12T19:30:00+08:00",
                party_size=2,
                contact_name="Alex",
                contact_phone="0911111111",
                dry_run=False,
            )
        )


def test_eztable_live_create_uses_provider_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(booking.settings, "eztable_api_key", "token")
    monkeypatch.setattr(booking.settings, "eztable_base_url", "https://api.eztable.test")

    def fake_provider_request(provider: str, path: str, payload: dict) -> dict:
        assert provider == "eztable"
        assert path == booking.settings.eztable_create_path
        assert payload["restaurant_name"] == "Live EZTABLE Restaurant"
        return {"id": "ezt_456", "status": "pending"}

    monkeypatch.setattr(booking, "_provider_request", fake_provider_request)

    created = create_booking(
        BookingCreateRequest(
            provider="eztable",
            restaurant_name="Live EZTABLE Restaurant",
            reservation_time="2026-03-12T19:30:00+08:00",
            party_size=2,
            contact_name="Alex",
            contact_phone="0911111111",
            dry_run=False,
        )
    )

    assert created.status == "pending"
    assert created.reservation_id == "ezt_456"


def test_eztable_live_cancel_uses_provider_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(booking.settings, "eztable_api_key", "token")
    monkeypatch.setattr(booking.settings, "eztable_base_url", "https://api.eztable.test")

    def fake_provider_request(provider: str, path: str, payload: dict) -> dict:
        assert provider == "eztable"
        assert "abc123" in path
        assert payload["reservation_id"] == "abc123"
        return {"status": "cancelled"}

    monkeypatch.setattr(booking, "_provider_request", fake_provider_request)

    cancelled = cancel_booking(
        BookingCancelRequest(
            provider="eztable",
            reservation_id="abc123",
            dry_run=False,
        )
    )

    assert cancelled.status == "cancelled"
