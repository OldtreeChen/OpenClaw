from __future__ import annotations

import re

PLATFORM_PATTERNS = {
    "inline": re.compile(r"inline\.app", re.IGNORECASE),
    "eztable": re.compile(r"eztable\.com", re.IGNORECASE),
    "opentable": re.compile(r"opentable\.", re.IGNORECASE),
}


def detect_platform(url: str) -> str:
    for name, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(url):
            return name
    return "unknown"


def get_reservation_link(website_uri: str | None, google_maps_uri: str | None) -> tuple[str, str, str | None]:
    if website_uri:
        platform = detect_platform(website_uri)
        if platform != "unknown":
            return platform, website_uri, "Found direct reservation platform from restaurant website URI."
        if google_maps_uri:
            return "google_maps", google_maps_uri, "Google Maps listing is available for reservation confirmation."
        return "website", website_uri, "No known reservation platform detected; fallback to official website."

    if google_maps_uri:
        return "google_maps", google_maps_uri, "No website available; fallback to Google Maps listing."

    return "none", "", "No reservation URL found for this restaurant."
