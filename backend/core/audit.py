from .models import AuditEvent


SENSITIVE_METADATA_KEY_PARTS = (
    "password",
    "token",
    "secret",
    "image",
    "frame",
    "template",
    "embedding",
    "notes",
    "cookie",
    "credential",
    "authorization",
)


def _safe_metadata_value(value):
    if isinstance(value, dict):
        safe = {}
        for key, item in value.items():
            normalized_key = str(key).strip().lower()
            if any(part in normalized_key for part in SENSITIVE_METADATA_KEY_PARTS):
                continue
            safe[normalized_key[:64]] = _safe_metadata_value(item)
        return safe
    if isinstance(value, (list, tuple)):
        return [_safe_metadata_value(item) for item in value[:100]]
    if isinstance(value, str):
        return value[:200]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:200]


def record_audit_event(
    *,
    actor,
    event_type,
    object_type,
    object_id="",
    summary,
    metadata=None,
):
    """Persist a minimal audit event without secrets or biometric payloads."""
    safe_metadata = _safe_metadata_value(metadata) if isinstance(metadata, dict) else {}
    authenticated = bool(getattr(actor, "is_authenticated", False))
    return AuditEvent.objects.create(
        actor=actor if authenticated else None,
        actor_username=actor.get_username() if authenticated else "",
        event_type=str(event_type)[:80],
        object_type=str(object_type)[:80],
        object_id=str(object_id)[:64],
        summary=str(summary)[:255],
        metadata=safe_metadata,
    )
