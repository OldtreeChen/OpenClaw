from __future__ import annotations

from app.models import (
    AssistedReservationOption,
    AssistedReservationRequest,
    AssistedReservationResponse,
)
from app.reservation import detect_platform


def _build_booking_summary(payload: AssistedReservationRequest) -> str:
    lines = [
        f"餐廳：{payload.restaurant_name}",
        f"時間：{payload.reservation_time}",
        f"人數：{payload.party_size}",
        f"訂位人：{payload.contact_name}",
        f"電話：{payload.contact_phone}",
    ]
    if payload.note:
        lines.append(f"備註：{payload.note}")
    return "\\n".join(lines)


def prepare_assisted_reservation(payload: AssistedReservationRequest) -> AssistedReservationResponse:
    options: list[AssistedReservationOption] = []

    if payload.website_uri:
        platform = detect_platform(payload.website_uri)
        label = "前往餐廳官網訂位"
        if platform == "inline":
            label = "前往 inline 訂位"
        elif platform == "eztable":
            label = "前往 EZTABLE 訂位"
        options.append(
            AssistedReservationOption(
                platform=platform,
                url=payload.website_uri,
                label=label,
            )
        )

    if payload.google_maps_uri:
        options.append(
            AssistedReservationOption(
                platform="google_maps",
                url=payload.google_maps_uri,
                label="前往 Google Maps 查看並訂位",
            )
        )

    if not options:
        raise ValueError("No reservation link available. Provide website_uri or google_maps_uri.")

    primary_option = options[0]
    fallback_options = options[1:]
    booking_summary_text = _build_booking_summary(payload)
    steps = [
        "先點開主連結進入訂位頁。",
        "貼上或填入 booking_summary_text 的資訊。",
        "若主連結無法訂位，改用 fallback_options。",
        "完成後把確認碼回傳給 agent 做紀錄。",
    ]

    return AssistedReservationResponse(
        primary_option=primary_option,
        fallback_options=fallback_options,
        booking_summary_text=booking_summary_text,
        steps=steps,
    )
