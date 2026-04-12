import asyncio

import app.services as services
from app.models import SearchRequest


def test_search_restaurants_falls_back_to_english_query(monkeypatch):
    calls: list[tuple[str, str]] = []

    class FakePlacesClient:
        async def search_text(self, text_query: str, max_result_count: int = 5, language_code: str = "zh-TW"):
            calls.append((text_query, language_code))
            if language_code == "zh-TW":
                return [
                    {
                        "id": "place-1",
                        "displayName": {"text": "Test Hot Pot"},
                        "rating": 4.5,
                        "userRatingCount": 120,
                        "formattedAddress": "Taipei",
                    }
                ]
            return []

    monkeypatch.setattr(services, "PlacesClient", FakePlacesClient)

    result = asyncio.run(
        services.search_restaurants(
            SearchRequest(
                query="\u706b\u934b",
                location="\u53f0\u5317\u5e02",
                party_size=2,
                limit=5,
            )
        )
    )

    assert result
    assert result[0].name == "Test Hot Pot"
    assert calls[0][1] == "zh-TW"
    assert calls[-1][1] == "zh-TW"


def test_compose_query_variants_translates_common_keywords():
    variants = services._compose_query_variants(
        SearchRequest(
            query="\u71d2\u8089",
            location="\u53f0\u5317\u5e02\u4fe1\u7fa9\u5340",
            party_size=2,
        )
    )

    assert variants[0] == ("yakiniku restaurant in Xinyi District Taipei City", "zh-TW")
    assert ("\u71d2\u8089 \u53f0\u5317\u5e02\u4fe1\u7fa9\u5340", "zh-TW") in variants


def test_compose_query_variants_adds_buffet_and_luzhou_variants():
    variants = services._compose_query_variants(
        SearchRequest(
            query="\u5403\u5230\u98fd\u706b\u934b",
            location="\u65b0\u5317\u5e02\u8606\u6d32\u5340",
            party_size=2,
        )
    )

    assert ("all you can eat hot pot restaurant in Luzhou District New Taipei City", "zh-TW") in variants
    assert ("all you can eat hot pot buffet in Luzhou District New Taipei City", "zh-TW") in variants
    assert ("\u5403\u5230\u98fd\u706b\u934b \u5403\u5230\u98fd \u65b0\u5317\u5e02\u8606\u6d32\u5340", "zh-TW") in variants


def test_search_restaurants_filters_by_rating_and_review_count(monkeypatch):
    class FakePlacesClient:
        async def search_text(self, text_query: str, max_result_count: int = 5, language_code: str = "zh-TW"):
            return [
                {
                    "id": "place-1",
                    "displayName": {"text": "\u4f4e\u8a55\u50f9\u5e97"},
                    "rating": 3.9,
                    "userRatingCount": 500,
                },
                {
                    "id": "place-2",
                    "displayName": {"text": "\u4f4e\u8a55\u50f9\u6578\u5e97"},
                    "rating": 4.8,
                    "userRatingCount": 20,
                },
                {
                    "id": "place-3",
                    "displayName": {"text": "\u5408\u683c\u706b\u934b"},
                    "rating": 4.6,
                    "userRatingCount": 120,
                    "reservable": True,
                },
            ]

    monkeypatch.setattr(services, "PlacesClient", FakePlacesClient)

    result = asyncio.run(
        services.search_restaurants(
            SearchRequest(
                query="\u706b\u934b",
                location="\u53f0\u5317\u5e02",
                party_size=2,
                limit=5,
            )
        )
    )

    assert len(result) == 1
    assert result[0].name == "\u5408\u683c\u706b\u934b"
    assert result[0].reservable is True
