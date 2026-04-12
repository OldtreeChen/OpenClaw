from app.reservation import detect_platform, get_reservation_link


def test_detect_platform_inline() -> None:
    assert detect_platform("https://inline.app/booking/-abc") == "inline"


def test_detect_platform_unknown() -> None:
    assert detect_platform("https://example.com") == "unknown"


def test_get_reservation_link_prefers_website() -> None:
    platform, url, _ = get_reservation_link("https://inline.app/booking/123", "https://maps.google.com/x")
    assert platform == "inline"
    assert url == "https://inline.app/booking/123"


def test_get_reservation_link_falls_back_to_maps() -> None:
    platform, url, _ = get_reservation_link(None, "https://maps.google.com/x")
    assert platform == "google_maps"
    assert url == "https://maps.google.com/x"
