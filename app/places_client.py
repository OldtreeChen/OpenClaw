from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class PlacesClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.google_maps_api_key

    async def search_text(
        self,
        text_query: str,
        max_result_count: int = 5,
        language_code: str = "zh-TW",
    ) -> list[dict[str, Any]]:
        if not self.api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY is not configured.")

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.rating,places.userRatingCount,"
                "places.priceLevel,places.formattedAddress,places.googleMapsUri,"
                "places.websiteUri,places.nationalPhoneNumber,places.currentOpeningHours.openNow,"
                "places.reservable"
            ),
        }
        payload = {
            "textQuery": text_query,
            "includedType": "restaurant",
            "maxResultCount": max_result_count,
            "languageCode": language_code,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                settings.google_places_text_search_url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return data.get("places", [])
