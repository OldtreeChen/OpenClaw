from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any

import httpx

from app.config import settings
from app.models import LineWebhookRequest
from app.orchestrator import run_line_query


def verify_line_signature(body: bytes, signature: str | None) -> bool:
    if not settings.line_channel_secret or not signature:
        return False

    digest = hmac.new(
        settings.line_channel_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def _extract_text_events(payload: dict[str, Any]) -> list[tuple[str, str, str]]:
    events = payload.get("events", [])
    extracted: list[tuple[str, str, str]] = []

    for event in events:
        if event.get("type") != "message":
            continue
        message = event.get("message") or {}
        source = event.get("source") or {}
        if message.get("type") != "text":
            continue

        reply_token = event.get("replyToken")
        user_id = source.get("userId")
        text = message.get("text")
        if reply_token and user_id and text:
            extracted.append((reply_token, user_id, text))

    return extracted


async def reply_line_message(reply_token: str, text: str) -> None:
    if not settings.line_channel_access_token:
        raise ValueError("LINE channel access token is not configured.")

    headers = {
        "Authorization": f"Bearer {settings.line_channel_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": text[:5000],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(settings.line_reply_api_url, headers=headers, json=payload)
        response.raise_for_status()


async def handle_line_webhook(payload: dict[str, Any]) -> int:
    handled = 0

    for reply_token, user_id, text in _extract_text_events(payload):
        response = await run_line_query(
            LineWebhookRequest(
                user_id=user_id,
                message=text,
            )
        )
        await reply_line_message(reply_token, response.reply_text)
        handled += 1

    return handled
