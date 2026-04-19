import asyncio

import app.orchestrator as orchestrator
from app.models import (
    AssistedReservationOption,
    AvailabilityProbeResponse,
    AvailabilityProbeResult,
    LineWebhookRequest,
    Restaurant,
    SearchAndProbeItem,
    SearchAndProbeRequest,
    SearchAndProbeResponse,
)


def test_run_search_and_probe_sorts_by_status_and_rating(monkeypatch):
    async def fake_search_restaurants(payload):
        return [
            Restaurant(place_id="1", name="R1", rating=4.2, website_uri="https://inline.app/r1"),
            Restaurant(place_id="2", name="R2", rating=4.8, website_uri="https://eztable.com/r2"),
        ]

    async def fake_probe(payload):
        return AvailabilityProbeResponse(
            total=2,
            available_count=1,
            fallback_count=0,
            unknown_count=1,
            results=[
                AvailabilityProbeResult(
                    restaurant_name="R1",
                    platform="inline",
                    status="unknown",
                    available_times=[],
                ),
                AvailabilityProbeResult(
                    restaurant_name="R2",
                    platform="eztable",
                    status="available",
                    available_times=["19:00"],
                ),
            ],
        )

    monkeypatch.setattr(orchestrator, "search_restaurants", fake_search_restaurants)
    monkeypatch.setattr(orchestrator, "probe_availability_batch", fake_probe)

    result = asyncio.run(
        orchestrator.run_search_and_probe(
            SearchAndProbeRequest(message="燒肉", location="台北", party_size=2, reservation_date="2026-03-21")
        )
    )

    assert len(result.results) == 2
    assert result.results[0].name == "R2"
    assert result.results[0].availability_status == "available"
    assert result.results[0].reservation_platform == "eztable"


def test_run_search_and_probe_prefers_google_maps_when_reservable(monkeypatch):
    async def fake_search_restaurants(payload):
        return [
            Restaurant(
                place_id="1",
                name="\u53ef\u8a02\u4f4d\u706b\u934b",
                rating=4.5,
                website_uri="https://example.com/store",
                google_maps_uri="https://maps.google.com/?cid=123",
                reservable=True,
            )
        ]

    async def fake_probe(payload):
        return AvailabilityProbeResponse(
            total=1,
            available_count=0,
            fallback_count=1,
            unknown_count=0,
            results=[
                AvailabilityProbeResult(
                    restaurant_name="\u53ef\u8a02\u4f4d\u706b\u934b",
                    platform="google_maps",
                    status="fallback",
                    available_times=[],
                )
            ],
        )

    monkeypatch.setattr(orchestrator, "search_restaurants", fake_search_restaurants)
    monkeypatch.setattr(orchestrator, "probe_availability_batch", fake_probe)

    result = asyncio.run(
        orchestrator.run_search_and_probe(
            SearchAndProbeRequest(message="\u706b\u934b", location="\u53f0\u5317", party_size=2, reservation_date="2026-03-21")
        )
    )

    assert result.results[0].reservation_platform == "google_maps"
    assert result.results[0].reservation_url == "https://maps.google.com/?cid=123"


def test_run_line_query_builds_actions(monkeypatch):
    async def fake_run_search_and_probe(payload):
        return SearchAndProbeResponse(
            query="火鍋",
            location="台北",
            party_size=2,
            reservation_date="2026-03-21",
            preferred_time="19:00",
            results=[
                SearchAndProbeItem(
                    place_id="1",
                    name="Hotpot A",
                    rating=4.5,
                    platform="inline",
                    availability_status="available",
                    available_times=["18:30", "19:00"],
                    primary_option=AssistedReservationOption(
                        platform="inline",
                        url="https://inline.app/a",
                        label="前往 inline",
                    ),
                )
            ],
        )

    monkeypatch.setattr(orchestrator, "run_search_and_probe", fake_run_search_and_probe)

    response = asyncio.run(
        orchestrator.run_line_query(
            LineWebhookRequest(user_id="u1", message="火鍋", location="台北", party_size=2, preferred_time="19:00")
        )
    )

    assert "幫你找了" in response.reply_text
    assert "https://inline.app/a" in response.reply_text
    assert len(response.actions) == 1
    assert response.actions[0].url == "https://inline.app/a"
    assert len(response.booking_intents) == 1
    assert response.booking_intents[0].provider == "inline"
    assert response.booking_intents[0].booking_summary_text.startswith("餐廳：Hotpot A")


def test_run_line_query_asks_for_cuisine_when_missing():
    orchestrator.USER_CONTEXT.clear()

    response = asyncio.run(
        orchestrator.run_line_query(
            LineWebhookRequest(user_id="u-follow", message="今天晚上想吃點東西", location="台北市", party_size=2)
        )
    )

    assert "想吃什麼類型" in response.reply_text
    assert response.actions == []


def test_run_line_query_uses_previous_context_for_follow_up(monkeypatch):
    orchestrator.USER_CONTEXT.clear()

    async def fake_run_search_and_probe(payload):
        return SearchAndProbeResponse(
            query=payload.message,
            location=payload.location,
            party_size=payload.party_size,
            reservation_date=payload.reservation_date or "2026-03-21",
            preferred_time=payload.preferred_time,
            results=[],
        )

    monkeypatch.setattr(orchestrator, "run_search_and_probe", fake_run_search_and_probe)

    first = asyncio.run(
        orchestrator.run_line_query(
            LineWebhookRequest(user_id="u-memory", message="信義區 串燒", location="台北市", party_size=2)
        )
    )
    assert "想約什麼時間" in first.reply_text

    second = asyncio.run(
        orchestrator.run_line_query(
            LineWebhookRequest(user_id="u-memory", message="明天晚上7點", location="台北市", party_size=2)
        )
    )
    assert "找不到符合條件" in second.reply_text


def test_parse_line_message_extracts_common_fields():
    parsed = orchestrator.parse_line_message(
        LineWebhookRequest(
            user_id="u1",
            message="\u660e\u5929\u665a\u4e0a7\u9ede \u4fe1\u7fa9\u5340 \u71d2\u8089 4\u4eba",
            location="\u53f0\u5317\u5e02",
            party_size=2,
        )
    )

    assert parsed.query == "\u71d2\u8089"
    assert parsed.location == "\u53f0\u5317\u5e02\u4fe1\u7fa9\u5340"
    assert parsed.party_size == 4
    assert parsed.preferred_time == "19:00"


def test_parse_line_message_extracts_luzhou_as_new_taipei():
    parsed = orchestrator.parse_line_message(
        LineWebhookRequest(
            user_id="u1",
            message="\u8606\u6d32\u6709\u5403\u5230\u98fd\u7684\u706b\u934b\u63a8\u85a6\u55ce",
            location="\u53f0\u5317\u5e02",
            party_size=2,
        )
    )

    assert parsed.location == "\u65b0\u5317\u5e02\u8606\u6d32\u5340"
    assert "\u5403\u5230\u98fd" in parsed.query
    assert "\u706b\u934b" in parsed.query


def test_parse_line_message_does_not_treat_party_size_as_time():
    parsed = orchestrator.parse_line_message(
        LineWebhookRequest(
            user_id="u1",
            message="\u4fe1\u7fa9\u5340 \u706b\u934b 2\u4eba",
            location="\u53f0\u5317\u5e02",
            party_size=2,
        )
    )

    assert parsed.party_size == 2
    assert parsed.preferred_time is None


def test_parse_line_message_extracts_slash_date_and_compact_time_and_query_constraints():
    parsed = orchestrator.parse_line_message(
        LineWebhookRequest(
            user_id="u1",
            message="\u6211\u60f3\u627e3/15\u665a\u4e0a1800\uff0c\u6709\u8349\u8766\u7684\u706b\u934b\u5403\u5230\u98fd",
            location="\u53f0\u5317\u5e02",
            party_size=2,
        )
    )

    assert parsed.reservation_date.endswith("-03-15")
    assert parsed.preferred_time == "18:00"
    assert parsed.query == "\u6709\u8349\u8766\u7684\u706b\u934b\u5403\u5230\u98fd"


def test_build_line_response_includes_summary_and_rating():
    result = SearchAndProbeResponse(
        query="\u706b\u934b",
        location="\u53f0\u5317\u5e02\u4fe1\u7fa9\u5340",
        party_size=2,
        reservation_date="2026-03-21",
        preferred_time="19:00",
        results=[
            SearchAndProbeItem(
                place_id="1",
                name="Hotpot A",
                rating=4.5,
                platform="inline",
                reservation_platform="inline",
                reservation_url="https://inline.app/a",
                availability_status="available",
                available_times=["18:30", "19:00"],
                primary_option=AssistedReservationOption(
                    platform="inline",
                    url="https://inline.app/a",
                    label="前往 inline",
                ),
            )
        ],
    )

    response = orchestrator.build_line_response(
        LineWebhookRequest(user_id="u1", message="\u706b\u934b", location="\u53f0\u5317\u5e02", party_size=2),
        result,
    )

    assert "\u53f0\u5317\u5e02\u4fe1\u7fa9\u5340" in response.reply_text
    assert "\u8a55\u5206 4.5" in response.reply_text
    assert "inline" in response.reply_text


def test_build_line_response_shows_requested_count():
    results = [
        SearchAndProbeItem(
            place_id=str(idx),
            name=f"R{idx}",
            rating=4.5,
            platform="google_maps",
            reservation_platform="google_maps",
            reservation_url=f"https://maps.google.com/?cid={idx}",
            availability_status="fallback",
            available_times=[],
        )
        for idx in range(1, 6)
    ]
    response = orchestrator.build_line_response(
        LineWebhookRequest(user_id="u1", message="\u706b\u934b", location="\u53f0\u5317\u5e02", party_size=2, limit=5),
        SearchAndProbeResponse(
            query="\u706b\u934b",
            location="\u53f0\u5317\u5e02",
            party_size=2,
            reservation_date="2026-03-21",
            preferred_time="18:00",
            results=results,
        ),
    )

    assert "\u5e6b\u4f60\u627e\u4e86 5 \u9593" in response.reply_text
    assert "5. R5" in response.reply_text
    assert len(response.actions) == 5
    assert len(response.booking_intents) == 5


def test_build_line_response_includes_recommendation_reason():
    response = orchestrator.build_line_response(
        LineWebhookRequest(user_id="u1", message="串燒", location="台北市", party_size=2, limit=1),
        SearchAndProbeResponse(
            query="串燒",
            location="台北市信義區",
            party_size=2,
            reservation_date="2026-03-21",
            preferred_time="19:00",
            results=[
                SearchAndProbeItem(
                    place_id="1",
                    name="串燒 A",
                    rating=4.8,
                    platform="google_maps",
                    reservation_platform="google_maps",
                    reservation_url="https://maps.google.com/?cid=1",
                    availability_status="available",
                    available_times=["19:00"],
                )
            ],
        ),
    )

    assert "推薦理由：" in response.reply_text
