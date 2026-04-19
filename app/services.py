from __future__ import annotations

from app.models import Restaurant, SearchRequest
from app.places_client import PlacesClient

CUISINE_TRANSLATIONS = {
    "\u706b\u934b": "hot pot",
    "\u5403\u5230\u98fd": "all you can eat",
    "\u5403\u5230\u98fd\u706b\u934b": "all you can eat hot pot",
    "\u71d2\u8089": "yakiniku",
    "\u4e32\u71d2": "yakitori",
    "\u751f\u9b5a\u7247": "sashimi",
    "\u65e5\u5f0f": "japanese restaurant",
    "\u97d3\u5f0f": "korean restaurant",
    "\u7fa9\u5f0f": "italian restaurant",
    "\u725b\u6392": "steakhouse",
}

LOCATION_TRANSLATIONS = {
    "\u65b0\u5317\u5e02\u8606\u6d32\u5340": "Luzhou District New Taipei City",
    "\u65b0\u5317\u5e02\u4e09\u91cd\u5340": "Sanchong District New Taipei City",
    "\u53f0\u5317\u5e02\u4fe1\u7fa9\u5340": "Xinyi District Taipei City",
    "\u53f0\u5317\u5e02\u5927\u5b89\u5340": "Da'an District Taipei City",
    "\u53f0\u5317\u5e02\u4e2d\u5c71\u5340": "Zhongshan District Taipei City",
    "\u53f0\u5317\u5e02": "Taipei City",
    "\u53f0\u5317": "Taipei",
    "\u8606\u6d32\u5340": "Luzhou District",
    "\u8606\u6d32": "Luzhou",
    "\u4e09\u91cd\u5340": "Sanchong District",
    "\u4e09\u91cd": "Sanchong",
    "\u4fe1\u7fa9\u5340": "Xinyi District",
    "\u5927\u5b89\u5340": "Da'an District",
    "\u4e2d\u5c71\u5340": "Zhongshan District",
}

CUISINE_KEYWORD_RULES = {
    "\u4e32\u71d2": {
        "include": ["\u4e32\u71d2", "\u71d2\u9ce5", "\u5c45\u9152\u5c4b", "yakitori", "skewer"],
        "exclude": ["\u71d2\u8089", "\u70e4\u8089", "yakiniku", "bbq", "barbecue"],
    },
    "\u71d2\u8089": {
        "include": ["\u71d2\u8089", "\u70e4\u8089", "yakiniku", "bbq", "barbecue"],
        "exclude": ["\u4e32\u71d2", "\u71d2\u9ce5", "\u5c45\u9152\u5c4b", "yakitori", "skewer"],
    },
    "\u706b\u934b": {
        "include": ["\u706b\u934b", "\u934b\u7269", "hot pot", "shabu", "nabe"],
        "exclude": ["\u71d2\u8089", "\u4e32\u71d2", "yakiniku", "yakitori"],
    },
    "\u751f\u9b5a\u7247": {
        "include": ["\u751f\u9b5a\u7247", "\u58fd\u53f8", "sashimi", "omakase"],
        "exclude": ["\u71d2\u8089", "\u4e32\u71d2", "\u706b\u934b"],
    },
}


def _translate_text(value: str) -> str:
    translated = value
    replacements = {**CUISINE_TRANSLATIONS, **LOCATION_TRANSLATIONS}
    for source in sorted(replacements, key=len, reverse=True):
        translated = translated.replace(source, replacements[source])
    return " ".join(translated.split())


def _compose_query_variants(payload: SearchRequest) -> list[tuple[str, str]]:
    query = (payload.cuisine_type or payload.query).strip()
    location = payload.location.strip()
    buffet_hint = "\u5403\u5230\u98fd" in query or "all you can eat" in query.lower()
    translated_query = _translate_text(query)
    translated_location = _translate_text(location)
    has_translation = translated_query != query or translated_location != location

    candidates: list[tuple[str, str]] = []
    if has_translation:
        candidates.extend(
            [
                (f"{translated_query} restaurant in {translated_location}", "zh-TW"),
                (f"{translated_query} restaurant {translated_location}", "zh-TW"),
                (f"{translated_query} {translated_location}", "zh-TW"),
            ]
        )
        if buffet_hint:
            candidates.extend(
                [
                    (f"{translated_query} buffet in {translated_location}", "zh-TW"),
                    (f"{translated_query} buffet {translated_location}", "en"),
                ]
            )

    candidates.extend(
        [
            (f"{query} {location}", "zh-TW"),
            (f"{query} \u9910\u5ef3 {location}", "zh-TW"),
        ]
    )
    if buffet_hint:
        candidates.extend(
            [
                (f"{query} \u5403\u5230\u98fd {location}", "zh-TW"),
                (f"{query} buffet {location}", "zh-TW"),
            ]
        )

    if has_translation:
        candidates.extend(
            [
                (f"{translated_query} restaurant in {translated_location}", "en"),
                (f"{translated_query} restaurant {translated_location}", "en"),
            ]
        )
        if buffet_hint:
            candidates.append((f"{translated_query} buffet in {translated_location}", "en"))

    seen: set[tuple[str, str]] = set()
    variants: list[tuple[str, str]] = []
    for candidate in candidates:
        normalized = (candidate[0].strip(), candidate[1])
        if normalized[0] and normalized not in seen:
            seen.add(normalized)
            variants.append(normalized)
    return variants


def _map_price_level(value: str | None) -> int | None:
    if not value:
        return None
    mapping = {
        "PRICE_LEVEL_INEXPENSIVE": 1,
        "PRICE_LEVEL_MODERATE": 2,
        "PRICE_LEVEL_EXPENSIVE": 3,
        "PRICE_LEVEL_VERY_EXPENSIVE": 4,
    }
    return mapping.get(value)


def _to_restaurant(place: dict) -> Restaurant:
    return Restaurant(
        place_id=place.get("id", ""),
        name=place.get("displayName", {}).get("text", ""),
        rating=place.get("rating"),
        user_rating_count=place.get("userRatingCount"),
        price_level=_map_price_level(place.get("priceLevel")),
        formatted_address=place.get("formattedAddress"),
        google_maps_uri=place.get("googleMapsUri"),
        website_uri=place.get("websiteUri"),
        phone_number=place.get("nationalPhoneNumber"),
        open_now=(place.get("currentOpeningHours") or {}).get("openNow"),
        reservable=place.get("reservable"),
    )


def _normalize_text_for_match(*parts: str | None) -> str:
    normalized = " ".join(part for part in parts if part)
    return normalized.casefold()


def _cuisine_match_score(restaurant: Restaurant, cuisine_tag: str | None) -> int:
    if not cuisine_tag:
        return 0

    rule = CUISINE_KEYWORD_RULES.get(cuisine_tag)
    if not rule:
        return 0

    haystack = _normalize_text_for_match(
        restaurant.name,
        restaurant.website_uri,
        restaurant.formatted_address,
    )
    score = 0
    for keyword in rule["include"]:
        if keyword.casefold() in haystack:
            score += 3
    for keyword in rule["exclude"]:
        if keyword.casefold() in haystack:
            score -= 4
    return score


def _rank_restaurants(restaurants: list[Restaurant], cuisine_tag: str | None) -> list[Restaurant]:
    ranked = sorted(
        restaurants,
        key=lambda restaurant: (
            _cuisine_match_score(restaurant, cuisine_tag),
            1 if restaurant.reservable else 0,
            restaurant.rating or 0,
            restaurant.user_rating_count or 0,
        ),
        reverse=True,
    )
    if cuisine_tag in CUISINE_KEYWORD_RULES:
        positively_matched = [restaurant for restaurant in ranked if _cuisine_match_score(restaurant, cuisine_tag) > 0]
        if positively_matched:
            return positively_matched
    return ranked


async def search_restaurants(payload: SearchRequest) -> list[Restaurant]:
    client = PlacesClient()

    for query, language_code in _compose_query_variants(payload):
        places = await client.search_text(
            query,
            max_result_count=payload.limit,
            language_code=language_code,
        )
        restaurants = [_to_restaurant(place) for place in places if place.get("id") and place.get("displayName")]
        qualified = [
            restaurant
            for restaurant in restaurants
            if (restaurant.rating or 0) >= 4.0 and (restaurant.user_rating_count or 0) >= 50
        ]
        if qualified:
            ranked = _rank_restaurants(qualified, payload.cuisine_tag or payload.cuisine_type)
            return ranked[: payload.limit]

    return []
