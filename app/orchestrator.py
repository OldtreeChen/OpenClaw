from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.availability import probe_availability_batch
from app.models import (
    BookingIntent,
    AvailabilityProbeItem,
    AvailabilityProbeRequest,
    LineAction,
    LineWebhookRequest,
    LineWebhookResponse,
    SearchAndProbeItem,
    SearchAndProbeRequest,
    SearchAndProbeResponse,
    SearchRequest,
)
from app.reservation import get_reservation_link
from app.services import search_restaurants

TAIPEI_TZ = timezone(timedelta(hours=8))

CUISINE_KEYWORDS = [
    "\u706b\u934b",
    "\u71d2\u8089",
    "\u4e32\u71d2",
    "\u751f\u9b5a\u7247",
    "\u65e5\u5f0f",
    "\u97d3\u5f0f",
    "\u7fa9\u5f0f",
    "\u725b\u6392",
]
LOCATION_KEYWORDS = [
    "\u8606\u6d32\u5340",
    "\u8606\u6d32",
    "\u4e09\u91cd\u5340",
    "\u4e09\u91cd",
    "\u4fe1\u7fa9\u5340",
    "\u5927\u5b89\u5340",
    "\u4e2d\u5c71\u5340",
    "\u897f\u9580\u753a",
    "\u897f\u9580",
    "\u6771\u5340",
    "\u677f\u6a4b",
    "\u65b0\u5e97",
    "\u6c38\u548c",
    "\u4e2d\u548c",
    "\u53f0\u5317\u5e02",
    "\u53f0\u5317",
    "\u65b0\u5317\u5e02",
]
NEW_TAIPEI_DISTRICTS = {
    "\u677f\u6a4b\u5340",
    "\u65b0\u5e97\u5340",
    "\u6c38\u548c\u5340",
    "\u4e2d\u548c\u5340",
    "\u8606\u6d32\u5340",
    "\u4e09\u91cd\u5340",
}
TIME_KEYWORDS = {
    "\u4e2d\u5348": "12:00",
    "\u5348\u9910": "12:00",
    "\u4e0b\u5348": "14:00",
    "\u665a\u4e0a": "19:00",
    "\u665a\u9910": "19:00",
    "\u5bb5\u591c": "21:00",
}
STATUS_WEIGHT = {"available": 4, "unknown": 3, "fallback": 2, "unavailable": 1, "error": 0}
STATUS_TEXT = {
    "available": "\u53ef\u7528\u6642\u6bb5",
    "unknown": "\u67e5\u8a62\u4e2d\u7acb\u7d50\u679c",
    "fallback": "\u8acb\u9ede\u9023\u7d50\u78ba\u8a8d",
    "unavailable": "\u53ef\u80fd\u7121\u4f4d",
    "error": "\u67e5\u8a62\u5931\u6557",
}
PLATFORM_TEXT = {
    "inline": "inline",
    "eztable": "EZTABLE",
    "google_maps": "Google Maps",
    "website": "\u5b98\u7db2",
    "unknown": "\u8a02\u4f4d\u9023\u7d50",
    "none": "\u8a02\u4f4d\u9023\u7d50",
}
PEOPLE_PATTERN = re.compile(r"(\d+)\s*(?:\u4eba|\u4f4d)")
TIME_PATTERN = re.compile(
    r"(\u4e0a\u5348|\u4e0b\u5348|\u665a\u4e0a|\u4e2d\u5348|\u51cc\u6668)\s*(\d{1,2})(?:[:\uff1a\u9ede](\d{1,2}))?|(\d{1,2})(?:[:\uff1a\u9ede](\d{1,2}))"
)
DATE_PATTERN = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)")
COMPACT_TIME_PATTERN = re.compile(r"(?<!\d)([01]?\d|2[0-3])([0-5]\d)(?!\d)")
USER_CONTEXT: dict[str, "ParsedMessage"] = {}
FOLLOW_UP_HINTS = {
    "cuisine": "\u60f3\u5403\u4ec0\u9ebc\u985e\u578b\u7684\u9910\u5ef3\uff1f\u4f8b\u5982\u706b\u934b\u3001\u71d2\u8089\u3001\u4e32\u71d2\u3001\u751f\u9b5a\u7247\u3002",
    "location": "\u4f60\u60f3\u627e\u54ea\u500b\u5730\u5340\uff1f\u4f8b\u5982\u4fe1\u7fa9\u5340\u3001\u53f0\u5317\u5e02\u3001\u8606\u6d32\u5340\u3002",
    "time": "\u60f3\u7d04\u4ec0\u9ebc\u6642\u9593\uff1f\u4f8b\u5982\u4eca\u665a 7 \u9ede\u3001\u660e\u5929\u665a\u4e0a 6 \u9ede\u3002",
}
MUST_HAVE_KEYWORDS = [
    "\u8349\u8766",
    "\u548c\u725b",
    "\u5305\u5ec2",
    "\u5403\u5230\u98fd",
    "\u89aa\u5b50",
    "\u5bf5\u7269",
]
PREFERRED_KEYWORDS = [
    "\u5b89\u975c",
    "\u805a\u9910",
    "\u5c45\u9152\u5c4b",
    "\u666f\u89c0",
    "\u5ea7\u4f4d\u5bec\u655e",
]
AVOID_KEYWORDS = [
    "\u4e0d\u8981\u592a\u8cb4",
    "\u4e0d\u8981\u6392\u968a",
    "\u4e0d\u5403\u725b",
    "\u4e0d\u8981\u71d2\u8089",
    "\u4e0d\u8981\u5435",
]
LOW_BUDGET_HINTS = ["\u4e0d\u8981\u592a\u8cb4", "\u4fbf\u5b9c", "\u5e73\u50f9"]
HIGH_BUDGET_HINTS = ["\u9ad8\u7d1a", "\u7cbe\u7dfb", "\u6176\u751f", "\u7d04\u6703"]


@dataclass
class ParsedMessage:
    query: str
    location: str
    party_size: int
    reservation_date: str
    preferred_time: str | None
    cuisine_tag: str | None = None
    must_have_terms: list[str] | None = None
    preferred_terms: list[str] | None = None
    avoid_terms: list[str] | None = None
    budget_level: int | None = None


def _extract_cuisine_tag(message: str) -> str | None:
    for keyword in CUISINE_KEYWORDS:
        if keyword in message:
            return keyword
    return None


def _extract_terms(message: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword in message]


def _extract_budget_level(message: str) -> int | None:
    if any(keyword in message for keyword in LOW_BUDGET_HINTS):
        return 1
    if any(keyword in message for keyword in HIGH_BUDGET_HINTS):
        return 4
    return None


def _now_taipei() -> datetime:
    return datetime.now(TAIPEI_TZ)


def _default_reservation_date() -> str:
    return _now_taipei().strftime("%Y-%m-%d")


def _infer_query(message: str, cuisine_type: str | None) -> str:
    if cuisine_type:
        return cuisine_type
    for keyword in CUISINE_KEYWORDS:
        if keyword in message:
            return keyword
    return message


def _clean_message_for_query(message: str) -> str:
    cleaned = message
    cleaned = DATE_PATTERN.sub(" ", cleaned)
    cleaned = PEOPLE_PATTERN.sub(" ", cleaned)
    cleaned = COMPACT_TIME_PATTERN.sub(" ", cleaned)
    cleaned = TIME_PATTERN.sub(" ", cleaned)

    for keyword in LOCATION_KEYWORDS:
        cleaned = cleaned.replace(keyword, " ")
    for keyword in ("\u6211\u60f3\u627e", "\u60f3\u627e", "\u6211\u8981\u627e", "\u5e6b\u6211\u627e", "\u5e6b\u4f60\u627e"):
        cleaned = cleaned.replace(keyword, " ")
    for keyword in TIME_KEYWORDS:
        cleaned = cleaned.replace(keyword, " ")
    for token in ("\u4eca\u5929", "\u4eca\u665a", "\u660e\u5929", "\u5f8c\u5929", "\u8acb\u554f", "\u60f3\u5403", "\u6709\u6c92\u6709"):
        cleaned = cleaned.replace(token, " ")
    cleaned = cleaned.replace("\u9ede", " ")

    cleaned = cleaned.replace(":", " ")
    cleaned = cleaned.replace("\uff1a", " ")
    cleaned = cleaned.replace("\uff0c", " ")
    cleaned = cleaned.replace(",", " ")
    cleaned = cleaned.replace("\u3002", " ")

    return " ".join(cleaned.split())


def _extract_query(message: str, cuisine_type: str | None) -> str:
    inferred = _infer_query(message, cuisine_type)
    cleaned = _clean_message_for_query(message)
    if inferred and inferred in cleaned and cleaned != inferred:
        return cleaned
    if cleaned:
        return cleaned
    return inferred


def _normalize_location(location: str) -> str:
    if location in {"\u53f0\u5317", "\u53f0\u5317\u5e02"}:
        return "\u53f0\u5317\u5e02"
    if location in {"\u65b0\u5317", "\u65b0\u5317\u5e02"}:
        return "\u65b0\u5317\u5e02"
    if location in {"\u897f\u9580", "\u897f\u9580\u753a"}:
        return "\u53f0\u5317\u5e02\u842c\u83ef\u5340"
    if location == "\u6771\u5340":
        return "\u53f0\u5317\u5e02\u5927\u5b89\u5340"
    if location in {"\u8606\u6d32", "\u4e09\u91cd", "\u677f\u6a4b", "\u65b0\u5e97", "\u6c38\u548c", "\u4e2d\u548c"}:
        return _normalize_location(f"{location}\u5340")
    if location in NEW_TAIPEI_DISTRICTS:
        return f"\u65b0\u5317\u5e02{location}"
    if location.endswith("\u5340") and "\u5e02" not in location:
        return f"\u53f0\u5317\u5e02{location}"
    return location


def _extract_location(message: str, default_location: str) -> str:
    for keyword in LOCATION_KEYWORDS:
        if keyword in message:
            return _normalize_location(keyword)
    return default_location


def _extract_party_size(message: str, default_party_size: int) -> int:
    match = PEOPLE_PATTERN.search(message)
    if not match:
        return default_party_size
    return max(1, min(int(match.group(1)), 20))


def _extract_date(message: str, default_date: str | None) -> str:
    now = _now_taipei()
    explicit_date = DATE_PATTERN.search(message)
    if explicit_date:
        month = int(explicit_date.group(1))
        day = int(explicit_date.group(2))
        year = now.year
        candidate = datetime(year, month, day, tzinfo=TAIPEI_TZ)
        if candidate.date() < now.date():
            candidate = datetime(year + 1, month, day, tzinfo=TAIPEI_TZ)
        return candidate.strftime("%Y-%m-%d")
    if "\u4eca\u5929" in message or "\u4eca\u665a" in message:
        return now.strftime("%Y-%m-%d")
    if "\u660e\u5929" in message:
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    if "\u5f8c\u5929" in message:
        return (now + timedelta(days=2)).strftime("%Y-%m-%d")
    return default_date or _default_reservation_date()


def _extract_time(message: str, default_time: str | None) -> str | None:
    inferred_default = default_time
    for keyword, mapped_time in TIME_KEYWORDS.items():
        if keyword in message:
            inferred_default = mapped_time

    match = TIME_PATTERN.search(message)
    if not match:
        return inferred_default

    period, hour_text, minute_text, alt_hour_text, alt_minute_text = match.groups()
    hour = int(hour_text or alt_hour_text)
    minute = int(minute_text or alt_minute_text or 0)

    if period in {"\u4e0b\u5348", "\u665a\u4e0a"} and hour < 12:
        hour += 12
    if period == "\u4e2d\u5348" and hour < 11:
        hour += 12
    if period == "\u51cc\u6668" and hour == 12:
        hour = 0

    if hour > 23 or minute > 59:
        return inferred_default

    return f"{hour:02d}:{minute:02d}"


def _extract_compact_time(message: str, default_time: str | None) -> str | None:
    match = COMPACT_TIME_PATTERN.search(message)
    if not match:
        return default_time
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23 or minute > 59:
        return default_time
    return f"{hour:02d}:{minute:02d}"


def parse_line_message(payload: LineWebhookRequest) -> ParsedMessage:
    previous = USER_CONTEXT.get(payload.user_id)
    inferred_time = _extract_time(payload.message, payload.preferred_time)
    if inferred_time == payload.preferred_time:
        inferred_time = _extract_compact_time(payload.message, inferred_time)

    cuisine_tag = _extract_cuisine_tag(payload.message) or (previous.cuisine_tag if previous else None)
    parsed = ParsedMessage(
        query=_extract_query(payload.message, cuisine_tag),
        location=_extract_location(payload.message, previous.location if previous else payload.location),
        party_size=_extract_party_size(payload.message, payload.party_size),
        reservation_date=_extract_date(payload.message, previous.reservation_date if previous else payload.reservation_date),
        preferred_time=inferred_time or (previous.preferred_time if previous else None),
        cuisine_tag=cuisine_tag,
        must_have_terms=_extract_terms(payload.message, MUST_HAVE_KEYWORDS) or (previous.must_have_terms if previous else []),
        preferred_terms=_extract_terms(payload.message, PREFERRED_KEYWORDS) or (previous.preferred_terms if previous else []),
        avoid_terms=_extract_terms(payload.message, AVOID_KEYWORDS) or (previous.avoid_terms if previous else []),
        budget_level=_extract_budget_level(payload.message) or (previous.budget_level if previous else None),
    )
    return parsed


def _should_ask_follow_up(payload: LineWebhookRequest, parsed: ParsedMessage, has_previous: bool) -> tuple[str, str] | None:
    explicit_location = any(keyword in payload.message for keyword in LOCATION_KEYWORDS) or bool(payload.location)
    explicit_time = bool(_extract_time(payload.message, None) or _extract_compact_time(payload.message, None))
    if not parsed.cuisine_tag:
        return "cuisine", FOLLOW_UP_HINTS["cuisine"]
    if not explicit_location and not has_previous:
        return "location", FOLLOW_UP_HINTS["location"]
    if not explicit_time and not payload.preferred_time and not has_previous:
        return "time", FOLLOW_UP_HINTS["time"]
    return None


def _compose_search_payload(payload: SearchAndProbeRequest) -> SearchRequest:
    query = _infer_query(payload.message, payload.cuisine_type)
    dining_time = None
    if payload.reservation_date and payload.preferred_time:
        dining_time = f"{payload.reservation_date}T{payload.preferred_time}:00+08:00"

    return SearchRequest(
        query=query,
        location=payload.location,
        party_size=payload.party_size,
        dining_time=dining_time,
        cuisine_type=payload.cuisine_type,
        cuisine_tag=payload.cuisine_type,
        must_have_terms=payload.must_have_terms,
        preferred_terms=payload.preferred_terms,
        avoid_terms=payload.avoid_terms,
        budget_level=payload.budget_level,
        limit=payload.limit,
    )


def _reservation_entry(
    website_uri: str | None,
    google_maps_uri: str | None,
    reservable: bool | None,
) -> tuple[str | None, str | None]:
    if website_uri:
        platform, url, _ = get_reservation_link(website_uri, google_maps_uri)
        if url:
            return platform, url
    if reservable and google_maps_uri:
        return "google_maps", google_maps_uri
    platform, url, _ = get_reservation_link(website_uri, google_maps_uri)
    if not url:
        return None, None
    return platform, url


async def run_search_and_probe(payload: SearchAndProbeRequest) -> SearchAndProbeResponse:
    search_payload = _compose_search_payload(payload)
    restaurants = await search_restaurants(search_payload)

    if not restaurants:
        return SearchAndProbeResponse(
            query=search_payload.query,
            location=payload.location,
            party_size=payload.party_size,
            reservation_date=payload.reservation_date or _default_reservation_date(),
            preferred_time=payload.preferred_time,
            results=[],
        )

    probe_payload = AvailabilityProbeRequest(
        items=[
            AvailabilityProbeItem(
                restaurant_name=restaurant.name,
                party_size=payload.party_size,
                reservation_date=payload.reservation_date or _default_reservation_date(),
                preferred_time=payload.preferred_time,
                website_uri=restaurant.website_uri,
                google_maps_uri=restaurant.google_maps_uri,
            )
            for restaurant in restaurants
        ],
        max_parallel=payload.max_parallel,
        probe_timeout_sec=payload.probe_timeout_sec,
    )

    availability = await probe_availability_batch(probe_payload)

    items: list[SearchAndProbeItem] = []
    for restaurant, probe_result in zip(restaurants, availability.results, strict=False):
        reservation_platform, reservation_url = _reservation_entry(
            restaurant.website_uri,
            restaurant.google_maps_uri,
            restaurant.reservable,
        )
        items.append(
            SearchAndProbeItem(
                place_id=restaurant.place_id,
                name=restaurant.name,
                rating=restaurant.rating,
                address=restaurant.formatted_address,
                website_uri=restaurant.website_uri,
                google_maps_uri=restaurant.google_maps_uri,
                platform=probe_result.platform,
                reservation_platform=reservation_platform,
                reservation_url=reservation_url,
                availability_status=probe_result.status,
                available_times=probe_result.available_times,
                primary_option=probe_result.primary_option,
                fallback_options=probe_result.fallback_options,
            )
        )

    items.sort(
        key=lambda item: (
            STATUS_WEIGHT.get(item.availability_status, 0),
            1 if item.reservation_platform in {"inline", "eztable", "google_maps"} else 0,
            item.rating or 0,
        ),
        reverse=True,
    )

    return SearchAndProbeResponse(
        query=search_payload.query,
        location=payload.location,
        party_size=payload.party_size,
        reservation_date=payload.reservation_date or _default_reservation_date(),
        preferred_time=payload.preferred_time,
        results=items,
    )


def _best_action_url(item: SearchAndProbeItem) -> str | None:
    if item.reservation_url:
        return item.reservation_url
    if item.primary_option:
        return item.primary_option.url
    if item.fallback_options:
        return item.fallback_options[0].url
    return item.google_maps_uri


def _best_platform(item: SearchAndProbeItem) -> str:
    if item.reservation_platform:
        return item.reservation_platform
    if item.primary_option:
        return item.primary_option.platform
    if item.fallback_options:
        return item.fallback_options[0].platform
    return item.platform


def _build_booking_summary(item: SearchAndProbeItem, result: SearchAndProbeResponse) -> str:
    lines = [
        f"\u9910\u5ef3\uff1a{item.name}",
        f"\u5730\u9ede\uff1a{result.location}",
        f"\u65e5\u671f\uff1a{result.reservation_date}",
        f"\u4eba\u6578\uff1a{result.party_size}",
    ]
    if result.preferred_time:
        lines.append(f"\u6642\u9593\uff1a{result.preferred_time}")
    if item.available_times:
        lines.append(f"\u5019\u9078\u6642\u6bb5\uff1a{', '.join(item.available_times[:3])}")
    return "\n".join(lines)


def build_line_response(payload: LineWebhookRequest, result: SearchAndProbeResponse) -> LineWebhookResponse:
    if not result.results:
        return LineWebhookResponse(
            reply_text="\u76ee\u524d\u627e\u4e0d\u5230\u7b26\u5408\u689d\u4ef6\u7684\u9910\u5ef3\uff0c\u6211\u5df2\u7d93\u5957\u7528\u300c\u8a55\u5206 4.0 \u4ee5\u4e0a\u3001\u8a55\u50f9 50 \u7b46\u4ee5\u4e0a\u300d\u7684\u689d\u4ef6\uff0c\u8acb\u63db\u500b\u5730\u5340\u6216\u653e\u5bec\u95dc\u9375\u5b57\u518d\u8a66\u4e00\u6b21\u3002",
            actions=[],
            search_and_probe=result,
        )

    shown = result.results[: min(payload.limit, len(result.results))]
    summary = f"{result.location}\uff5c{result.party_size}\u4eba\uff5c{result.reservation_date}"
    if result.preferred_time:
        summary = f"{summary} {result.preferred_time}"

    lines = [
        f"\u5e6b\u4f60\u627e\u4e86 {len(shown)} \u9593\uff0c\u689d\u4ef6\u662f {summary}\uff5c\u8a55\u5206 4.0 \u4ee5\u4e0a\uff5c50+ \u8a55\u50f9\uff1a",
    ]
    actions: list[LineAction] = []
    booking_intents: list[BookingIntent] = []

    for idx, item in enumerate(shown, start=1):
        status_text = STATUS_TEXT.get(item.availability_status, item.availability_status)
        time_hint = ", ".join(item.available_times[:3]) if item.available_times else "-"
        rating_hint = f"{item.rating:.1f}" if item.rating is not None else "-"
        platform_text = PLATFORM_TEXT.get(_best_platform(item), "\u8a02\u4f4d\u9023\u7d50")
        action_url = _best_action_url(item)
        reason = []
        if item.rating and item.rating >= 4.5:
            reason.append("\u9ad8\u8a55\u5206")
        if item.reservation_platform in {"inline", "eztable", "google_maps"}:
            reason.append("\u53ef\u76f4\u63a5\u8a02\u4f4d")
        if item.available_times:
            reason.append("\u6293\u5230\u5019\u9078\u6642\u6bb5")
        query_text = result.query
        for term in ("\u8349\u8766", "\u548c\u725b", "\u5305\u5ec2", "\u5403\u5230\u98fd", "\u5b89\u975c"):
            if term in query_text:
                reason.append(f"\u8cbc\u8fd1「{term}」\u9700\u6c42")
        reason_text = "\uff0c".join(reason) if reason else "\u689d\u4ef6\u76f8\u8fd1"

        lines.append(
            f"{idx}. {item.name}\uff5c\u8a55\u5206 {rating_hint}\uff5c{status_text}\uff5c\u8a02\u4f4d: {platform_text}\uff5c\u6642\u6bb5: {time_hint}"
        )
        lines.append(f"\u63a8\u85a6\u7406\u7531\uff1a{reason_text}")

        if action_url:
            actions.append(LineAction(label=f"{idx}. {item.name[:12]}", url=action_url))
            booking_intents.append(
                BookingIntent(
                    restaurant_name=item.name,
                    provider=_best_platform(item),
                    url=action_url,
                    party_size=result.party_size,
                    reservation_date=result.reservation_date,
                    preferred_time=result.preferred_time,
                    availability_status=item.availability_status,
                    available_times=item.available_times,
                    booking_summary_text=_build_booking_summary(item, result),
                )
            )
            lines.append(f"\u76f4\u63a5\u8a02\u4f4d\u9023\u7d50({platform_text}): {action_url}")

    lines.append(
        "\u8acb\u9ede\u9023\u7d50\u9032\u5165\u8a02\u4f4d\u9801\uff0c\u6211\u6703\u512a\u5148\u986f\u793a inline / EZTABLE / Google Maps \u80fd\u78ba\u8a8d\u7684\u8a02\u4f4d\u65b9\u5f0f\u3002\u5b8c\u6210\u5f8c\u628a\u78ba\u8a8d\u78bc\u56de\u50b3\u7d66\u6211\uff0c\u6211\u5e6b\u4f60\u7d00\u9304\u3002"
    )

    return LineWebhookResponse(
        reply_text="\n".join(lines),
        actions=actions,
        booking_intents=booking_intents,
        search_and_probe=result,
    )


async def run_line_query(payload: LineWebhookRequest) -> LineWebhookResponse:
    has_previous = payload.user_id in USER_CONTEXT
    parsed = parse_line_message(payload)
    follow_up = _should_ask_follow_up(payload, parsed, has_previous)
    if follow_up:
        USER_CONTEXT[payload.user_id] = parsed
        _, prompt = follow_up
        return LineWebhookResponse(reply_text=prompt, actions=[], booking_intents=[])
    USER_CONTEXT[payload.user_id] = parsed
    search_and_probe = await run_search_and_probe(
        SearchAndProbeRequest(
            message=parsed.query,
            location=parsed.location,
            party_size=parsed.party_size,
            reservation_date=parsed.reservation_date,
            preferred_time=parsed.preferred_time,
            cuisine_type=parsed.cuisine_tag,
            budget_level=parsed.budget_level,
            must_have_terms=parsed.must_have_terms,
            preferred_terms=parsed.preferred_terms,
            avoid_terms=parsed.avoid_terms,
            limit=payload.limit,
        )
    )
    return build_line_response(payload, search_and_probe)
