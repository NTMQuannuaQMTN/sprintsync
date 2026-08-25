"""Unit tests for GitHub webhook HMAC signature verification.

No DB/network required — exercises src.services.github.verify_webhook_signature
in isolation, per autopilot.md's rule that COMPLETED status needs run evidence,
not just a code read.
"""
import hashlib
import hmac

from src.services.github import verify_webhook_signature
from src.core.config import settings


def _sign(secret: str, payload: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_valid_signature_is_accepted(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", "test-secret")
    payload = b'{"ref": "refs/heads/main"}'
    signature = _sign("test-secret", payload)
    assert verify_webhook_signature(payload, signature) is True


def test_tampered_payload_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", "test-secret")
    payload = b'{"ref": "refs/heads/main"}'
    signature = _sign("test-secret", payload)
    tampered_payload = b'{"ref": "refs/heads/evil"}'
    assert verify_webhook_signature(tampered_payload, signature) is False


def test_wrong_secret_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", "test-secret")
    payload = b'{"ref": "refs/heads/main"}'
    signature = _sign("wrong-secret", payload)
    assert verify_webhook_signature(payload, signature) is False


def test_missing_signature_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", "test-secret")
    payload = b'{"ref": "refs/heads/main"}'
    assert verify_webhook_signature(payload, "") is False


def test_no_secret_configured_rejects_everything(monkeypatch):
    """V2 hardening: an unconfigured secret used to fail OPEN (accept every
    payload) — that's exactly how the real webhook endpoint ended up
    accepting forged requests in production, since the secret had simply
    never been set. Now it fails CLOSED: no secret means no request gets
    through, signed or not."""
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", "")
    payload = b'{"ref": "refs/heads/main"}'
    assert verify_webhook_signature(payload, "sha256=not-even-a-real-signature") is False
    assert verify_webhook_signature(payload, "") is False
