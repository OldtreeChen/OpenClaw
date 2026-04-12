from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from app.config import settings
from app.models import (
    BookingCancelRequest,
    BookingCancelResponse,
    BookingCreateRequest,
    BookingCreateResponse,
)


@dataclass
class BookingRecord:
    provider: str
    reservation_id: str
    restaurant_name: str
    reservation_time: str
    party_size: int
    contact_name: str
    contact_phone: str
    note: str | None
    created_at: str


BOOKINGS: dict[str, BookingRecord] = {}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _extract_reservation_id(response: dict) -> str | None:
    for key in ("reservation_id", "id", "booking_id", "reference"):
        value = response.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _provider_config(provider: str) -> tuple[str, str, str, str, float]:
    if provider == "inline":
        api_key = settings.inline_api_key
        base_url = settings.inline_base_url
        auth_header = settings.inline_auth_header
        auth_scheme = settings.inline_auth_scheme
        timeout = settings.inline_timeout_seconds
    elif provider == "eztable":
        api_key = settings.eztable_api_key
        base_url = settings.eztable_base_url
        auth_header = settings.eztable_auth_header
        auth_scheme = settings.eztable_auth_scheme
        timeout = settings.eztable_timeout_seconds
    else:
        raise ValueError(f"Unsupported provider config: {provider}")

    if not api_key:
        raise ValueError(f"{provider} API key is not configured. Set {provider.upper()}_API_KEY in .env.")
    if not base_url:
        raise ValueError(f"{provider} base URL is not configured. Set {provider.upper()}_BASE_URL in .env.")

    return api_key, base_url, auth_header, auth_scheme, timeout


def _provider_headers(provider: str) -> tuple[dict[str, str], float]:
    api_key, _, auth_header, auth_scheme, timeout = _provider_config(provider)
    token = api_key
    if auth_scheme:
        token = f"{auth_scheme} {token}".strip()

    return (
        {
            "Content-Type": "application/json",
            auth_header: token,
        },
        timeout,
    )


def _provider_request(provider: str, path: str, payload: dict) -> dict:
    _, base_url, _, _, _ = _provider_config(provider)
    normalized_path = path if path.startswith("/") else f"/{path}"
    url = f"{base_url}{normalized_path}"
    headers, timeout = _provider_headers(provider)
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
        raise ValueError(f"{provider} response is not a JSON object.")


def _inline_create(payload: BookingCreateRequest) -> BookingCreateResponse:
    request_body = payload.provider_payload or {
        "restaurant_name": payload.restaurant_name,
        "reservation_time": payload.reservation_time,
        "party_size": payload.party_size,
        "contact": {
            "name": payload.contact_name,
            "phone": payload.contact_phone,
        },
        "note": payload.note,
    }

    data = _provider_request("inline", settings.inline_create_path, request_body)
    reservation_id = _extract_reservation_id(data)
    if not reservation_id:
        reservation_id = f"inline_{uuid4().hex[:12]}"

    status = str(data.get("status", "confirmed")).lower()
    if status not in {"confirmed", "pending", "cancelled"}:
        status = "confirmed"

    return BookingCreateResponse(
        provider="inline",
        reservation_id=reservation_id,
        status=status,
        message="inline live booking request succeeded.",
    )


def _inline_cancel(payload: BookingCancelRequest) -> BookingCancelResponse:
    path = settings.inline_cancel_path.replace("{reservation_id}", payload.reservation_id)
    request_body = payload.provider_payload or {"reservation_id": payload.reservation_id}
    data = _provider_request("inline", path, request_body)

    status = str(data.get("status", "cancelled")).lower()
    if status not in {"cancelled", "pending"}:
        status = "cancelled"

    return BookingCancelResponse(
        provider="inline",
        reservation_id=payload.reservation_id,
        status=status,
        message="inline live cancellation request succeeded.",
    )


def _eztable_create(payload: BookingCreateRequest) -> BookingCreateResponse:
    request_body = payload.provider_payload or {
        "restaurant_name": payload.restaurant_name,
        "reservation_time": payload.reservation_time,
        "party_size": payload.party_size,
        "contact": {
            "name": payload.contact_name,
            "phone": payload.contact_phone,
        },
        "note": payload.note,
    }

    data = _provider_request("eztable", settings.eztable_create_path, request_body)
    reservation_id = _extract_reservation_id(data)
    if not reservation_id:
        reservation_id = f"eztable_{uuid4().hex[:12]}"

    status = str(data.get("status", "confirmed")).lower()
    if status not in {"confirmed", "pending", "cancelled"}:
        status = "confirmed"

    return BookingCreateResponse(
        provider="eztable",
        reservation_id=reservation_id,
        status=status,
        message="EZTABLE live booking request succeeded.",
    )


def _eztable_cancel(payload: BookingCancelRequest) -> BookingCancelResponse:
    path = settings.eztable_cancel_path.replace("{reservation_id}", payload.reservation_id)
    request_body = payload.provider_payload or {"reservation_id": payload.reservation_id}
    data = _provider_request("eztable", path, request_body)

    status = str(data.get("status", "cancelled")).lower()
    if status not in {"cancelled", "pending"}:
        status = "cancelled"

    return BookingCancelResponse(
        provider="eztable",
        reservation_id=payload.reservation_id,
        status=status,
        message="EZTABLE live cancellation request succeeded.",
    )


def _create_dry_run(payload: BookingCreateRequest) -> BookingCreateResponse:
    reservation_id = f"{payload.provider}_{uuid4().hex[:12]}"

    record = BookingRecord(
        provider=payload.provider,
        reservation_id=reservation_id,
        restaurant_name=payload.restaurant_name,
        reservation_time=payload.reservation_time,
        party_size=payload.party_size,
        contact_name=payload.contact_name,
        contact_phone=payload.contact_phone,
        note=payload.note,
        created_at=_now_iso(),
    )
    BOOKINGS[reservation_id] = record

    return BookingCreateResponse(
        provider=payload.provider,
        reservation_id=reservation_id,
        status="simulated",
        message="Dry-run booking succeeded.",
    )


def _cancel_dry_run(payload: BookingCancelRequest) -> BookingCancelResponse:
    record = BOOKINGS.get(payload.reservation_id)
    if not record or record.provider != payload.provider:
        return BookingCancelResponse(
            provider=payload.provider,
            reservation_id=payload.reservation_id,
            status="not_found",
            message="Reservation not found in current session.",
        )

    BOOKINGS.pop(payload.reservation_id, None)
    return BookingCancelResponse(
        provider=payload.provider,
        reservation_id=payload.reservation_id,
        status="simulated",
        message="Dry-run cancellation succeeded.",
    )


def create_booking(payload: BookingCreateRequest) -> BookingCreateResponse:
    if payload.dry_run:
        return _create_dry_run(payload)

    if payload.provider == "inline":
        try:
            return _inline_create(payload)
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"inline create failed: {exc.response.status_code} {exc.response.text}") from exc
        except httpx.HTTPError as exc:
            raise ValueError(f"inline create failed: {exc}") from exc

    if payload.provider == "eztable":
        try:
            return _eztable_create(payload)
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"eztable create failed: {exc.response.status_code} {exc.response.text}") from exc
        except httpx.HTTPError as exc:
            raise ValueError(f"eztable create failed: {exc}") from exc

    raise ValueError(f"Unsupported provider: {payload.provider}")


def cancel_booking(payload: BookingCancelRequest) -> BookingCancelResponse:
    if payload.dry_run:
        return _cancel_dry_run(payload)

    if payload.provider == "inline":
        try:
            return _inline_cancel(payload)
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"inline cancel failed: {exc.response.status_code} {exc.response.text}") from exc
        except httpx.HTTPError as exc:
            raise ValueError(f"inline cancel failed: {exc}") from exc

    if payload.provider == "eztable":
        try:
            return _eztable_cancel(payload)
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"eztable cancel failed: {exc.response.status_code} {exc.response.text}") from exc
        except httpx.HTTPError as exc:
            raise ValueError(f"eztable cancel failed: {exc}") from exc

    raise ValueError(f"Unsupported provider: {payload.provider}")
