import base64
import hashlib
import hmac

from fastapi.testclient import TestClient

import app.line_integration as line_integration
import app.main as main_module


def test_verify_line_signature(monkeypatch):
    monkeypatch.setattr(line_integration.settings, "line_channel_secret", "secret123")
    body = b'{"events":[]}'
    digest = hmac.new(b"secret123", body, hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode("utf-8")

    assert line_integration.verify_line_signature(body, signature) is True
    assert line_integration.verify_line_signature(body, "wrong") is False


def test_extract_text_events():
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "reply-1",
                "source": {"userId": "user-1"},
                "message": {"type": "text", "text": "燒肉"},
            },
            {
                "type": "follow",
                "replyToken": "reply-2",
            },
        ]
    }

    assert line_integration._extract_text_events(payload) == [("reply-1", "user-1", "燒肉")]


def test_line_webhook_endpoint(monkeypatch):
    async def fake_handle_line_webhook(payload):
        return 1

    monkeypatch.setattr(main_module, "handle_line_webhook", fake_handle_line_webhook)
    monkeypatch.setattr(main_module, "verify_line_signature", lambda body, signature: True)

    client = TestClient(main_module.app)
    response = client.post(
        "/line/webhook",
        headers={"x-line-signature": "ok"},
        json={
            "events": [
                {
                    "type": "message",
                    "replyToken": "reply-1",
                    "source": {"userId": "user-1"},
                    "message": {"type": "text", "text": "火鍋"},
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "handled": 1}
