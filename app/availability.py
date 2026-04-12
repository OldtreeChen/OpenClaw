from __future__ import annotations

import asyncio
import re
from collections.abc import Sequence

from app.models import (
    AssistedReservationOption,
    AvailabilityProbeItem,
    AvailabilityProbeRequest,
    AvailabilityProbeResponse,
    AvailabilityProbeResult,
)
from app.reservation import detect_platform

TIME_PATTERN = re.compile(r"\b([01]?\d|2[0-3]):[0-5]\d\b")
UNAVAILABLE_HINTS = [
    "no availability",
    "fully booked",
    "unavailable",
    "no table",
    "無可用",
    "已滿",
    "客滿",
    "無空位",
]


def _build_options(
    website_uri: str | None,
    google_maps_uri: str | None,
) -> tuple[str, AssistedReservationOption | None, list[AssistedReservationOption]]:
    options: list[AssistedReservationOption] = []

    if website_uri:
        platform = detect_platform(website_uri)
        label = "前往餐廳網站預約"
        if platform == "inline":
            label = "前往 inline 頁面"
        elif platform == "eztable":
            label = "前往 EZTABLE 頁面"
        options.append(AssistedReservationOption(platform=platform, url=website_uri, label=label))

    if google_maps_uri:
        options.append(
            AssistedReservationOption(
                platform="google_maps",
                url=google_maps_uri,
                label="前往 Google Maps 預約",
            )
        )

    platform = options[0].platform if options else "none"
    primary = options[0] if options else None
    fallback = options[1:] if len(options) > 1 else []
    return platform, primary, fallback


def _extract_times(texts: Sequence[str]) -> list[str]:
    times: set[str] = set()
    for text in texts:
        for match in TIME_PATTERN.finditer(text):
            times.add(match.group(0))
    return sorted(times)


async def _probe_with_playwright(url: str, timeout_sec: int) -> tuple[list[str], bool]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed.") from exc

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_sec * 1000)
            await page.wait_for_timeout(1500)
            nodes = await page.query_selector_all("button, [role='button'], a")
            texts: list[str] = []
            for node in nodes[:400]:
                try:
                    txt = (await node.inner_text()).strip()
                except Exception:
                    continue
                if txt:
                    texts.append(txt)

            page_text = (await page.content()).lower()
            unavailable = any(hint in page_text for hint in UNAVAILABLE_HINTS)
            return _extract_times(texts), unavailable
        finally:
            await browser.close()


async def _probe_item(item: AvailabilityProbeItem, timeout_sec: int) -> AvailabilityProbeResult:
    platform, primary, fallback = _build_options(item.website_uri, item.google_maps_uri)

    if not primary:
        return AvailabilityProbeResult(
            restaurant_name=item.restaurant_name,
            platform="none",
            status="fallback",
            available_times=[],
            reason="No website_uri/google_maps_uri provided.",
            primary_option=None,
            fallback_options=[],
        )

    if platform not in {"inline", "eztable"}:
        return AvailabilityProbeResult(
            restaurant_name=item.restaurant_name,
            platform=platform,
            status="fallback",
            available_times=[],
            reason="Platform not supported for auto probing. Using direct link fallback.",
            primary_option=primary,
            fallback_options=fallback,
        )

    try:
        times, unavailable = await _probe_with_playwright(primary.url, timeout_sec)
    except Exception as exc:
        return AvailabilityProbeResult(
            restaurant_name=item.restaurant_name,
            platform=platform,
            status="fallback",
            available_times=[],
            reason=f"Auto probe failed ({exc}). Use direct link.",
            primary_option=primary,
            fallback_options=fallback,
        )

    if times:
        return AvailabilityProbeResult(
            restaurant_name=item.restaurant_name,
            platform=platform,
            status="available",
            available_times=times,
            reason="Detected candidate time slots from page content.",
            primary_option=primary,
            fallback_options=fallback,
        )

    if unavailable:
        return AvailabilityProbeResult(
            restaurant_name=item.restaurant_name,
            platform=platform,
            status="unavailable",
            available_times=[],
            reason="Page indicates no availability for current condition.",
            primary_option=primary,
            fallback_options=fallback,
        )

    return AvailabilityProbeResult(
        restaurant_name=item.restaurant_name,
        platform=platform,
        status="unknown",
        available_times=[],
        reason="Probe completed but no clear slot signal found.",
        primary_option=primary,
        fallback_options=fallback,
    )


async def probe_availability_batch(payload: AvailabilityProbeRequest) -> AvailabilityProbeResponse:
    sem = asyncio.Semaphore(payload.max_parallel)

    async def _runner(item: AvailabilityProbeItem) -> AvailabilityProbeResult:
        async with sem:
            return await _probe_item(item, payload.probe_timeout_sec)

    results = await asyncio.gather(*[_runner(item) for item in payload.items])

    available_count = sum(1 for r in results if r.status == "available")
    fallback_count = sum(1 for r in results if r.status == "fallback")
    unknown_count = sum(1 for r in results if r.status in {"unknown", "error"})

    return AvailabilityProbeResponse(
        total=len(results),
        available_count=available_count,
        fallback_count=fallback_count,
        unknown_count=unknown_count,
        results=results,
    )
