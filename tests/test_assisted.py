from app.assisted import prepare_assisted_reservation
from app.models import AssistedReservationRequest


def test_prepare_assisted_reservation_with_inline_and_maps() -> None:
    result = prepare_assisted_reservation(
        AssistedReservationRequest(
            restaurant_name="Foo Bar",
            reservation_time="2026-03-12T19:00:00+08:00",
            party_size=2,
            contact_name="Alex",
            contact_phone="0912345678",
            website_uri="https://inline.app/booking/demo",
            google_maps_uri="https://maps.google.com/?cid=123",
            note="靠窗",
        )
    )

    assert result.primary_option.platform == "inline"
    assert len(result.fallback_options) == 1
    assert result.fallback_options[0].platform == "google_maps"
    assert "餐廳：Foo Bar" in result.booking_summary_text
    assert "備註：靠窗" in result.booking_summary_text


def test_prepare_assisted_reservation_requires_at_least_one_link() -> None:
    try:
        prepare_assisted_reservation(
            AssistedReservationRequest(
                restaurant_name="Foo",
                reservation_time="2026-03-12T19:00:00+08:00",
                party_size=2,
                contact_name="Alex",
                contact_phone="0912345678",
            )
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "No reservation link available" in str(exc)
