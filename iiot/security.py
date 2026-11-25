import hashlib
import hmac
import json
import os
import random
import time

class SecurityError(Exception):
    """Базова помилка перевірки повідомлення."""


class InvalidSignature(SecurityError):
    """Повідомлення має некоректний формат або невірний підпис."""


class ExpiredError(SecurityError):
    """Часова мітка повідомлення виходить за допустимі межі."""


class ReplayError(SecurityError):
    """Ідентифікатор повідомлення (nonce) уже використовувався."""

def _signature(secret, topic, payload, ts, nonce):
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    message = f"{topic}\n{ts}\n{nonce}\n{canonical_payload}"
    return hmac.new(secret, message.encode("utf-8"), hashlib.sha256).hexdigest()


def sign(secret: bytes, topic, payload: dict, ts=None, nonce=None) -> bytes:
    if ts is None:
        ts = time.time()
    if nonce is None:
        nonce = os.urandom(8).hex()

    envelope = {
        "payload": payload,
        "ts": ts,
        "nonce": nonce,
        "sig": _signature(secret, topic, payload, ts, nonce),
    }
    return json.dumps(envelope, separators=(",", ":")).encode("utf-8")

class NonceCache:
    def __init__(self, ttl=60):
        self.ttl = ttl
        self.seen = {}

    def check_and_add(self, nonce, now):
        expired = [
            key for key, expires_at in self.seen.items()
            if expires_at <= now
        ]
        for key in expired:
            del self.seen[key]

        if nonce in self.seen:
            return False

        self.seen[nonce] = now + self.ttl
        return True

def verify(secret, topic, raw, max_age=30, cache=None, now=None):
    try:
        envelope = json.loads(raw)
        payload = envelope["payload"]
        ts = envelope["ts"]
        nonce = envelope["nonce"]
        sig = envelope["sig"]
    except (ValueError, KeyError, TypeError) as error:
        raise InvalidSignature("Некоректний формат повідомлення") from error

    if not isinstance(payload, dict) or not isinstance(nonce, str) or not nonce:
        raise InvalidSignature("Некоректні дані або nonce")
    if type(ts) not in (int, float) or not (-float("inf") < ts < float("inf")):
        raise InvalidSignature("Некоректна часова мітка")
    if not isinstance(sig, str) or not sig.isascii():
        raise InvalidSignature("Некоректний формат підпису")

    expected = _signature(secret, topic, payload, ts, nonce)
    if not hmac.compare_digest(expected, sig):
        raise InvalidSignature("Підпис не збігається")

    if now is None:
        now = time.time()
    if abs(now - ts) > max_age:
        raise ExpiredError("Часова мітка поза допустимим інтервалом")

    if cache is not None and not cache.check_and_add(nonce, now):
        raise ReplayError("Цей nonce вже використано")

    return payload

def backoff_delays(base=1.0, factor=2.0, cap=60.0, jitter=0.0, rng=None):
    if rng is None:
        rng = random

    delay = min(base, cap)
    while True:
        if jitter > 0:
            yield delay * (1 + rng.uniform(-jitter, jitter))
        else:
            yield delay

        delay = min(delay * factor, cap)

def generate_acl(devices, ingest_user="ingest", alert_user="alerts"):
    lines = []

    for device in devices:
        lines.extend([
            f"user {device}",
            f"topic write plant/+/+/{device}/#",
            "",
        ])

    lines.extend([
        f"user {ingest_user}",
        "topic read plant/#",
        "",
        f"user {alert_user}",
        "topic read plant/+/+/+/telemetry",
        "topic write plant/+/+/+/alerts",
    ])

    return "\n".join(lines) + "\n"