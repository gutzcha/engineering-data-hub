import copy
import json
import logging
import re
import uuid

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.forms.models import model_to_dict

from apps.audit.models import AuditEvent


logger = logging.getLogger(__name__)
REQUEST_ID_MAX_LENGTH = 120
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")


def record_audit_event(
    actor,
    action: str,
    target,
    before: dict | None,
    after: dict | None,
    request=None,
) -> None:
    """Append one audit event and never mutate existing audit rows."""
    if not target:
        return

    try:
        payload = {
            "actor": _actor_or_none(actor),
            "action": action,
            "object_type": _object_type_for(target),
            "object_id": str(getattr(target, "pk", target)),
            "before": _json_ready(before) if before is not None else None,
            "after": _json_ready(after) if after is not None else None,
            "request_id": _request_id(request),
            "ip_address": _ip_address(request),
            "user_agent": _user_agent(request),
        }
        _persist_audit_event(payload)
    except Exception:
        logger.exception("Failed to persist audit event.", extra={"action": action})


def _persist_audit_event(payload):
    connection = transaction.get_connection()
    if connection.in_atomic_block:
        with transaction.atomic():
            AuditEvent.objects.create(**payload)
        return
    AuditEvent.objects.create(**payload)


def sanitize_request_id(value) -> str:
    if value is None:
        return ""
    request_id = str(value).strip()
    if not request_id:
        return ""
    request_id = request_id[:REQUEST_ID_MAX_LENGTH]
    if not REQUEST_ID_RE.fullmatch(request_id):
        return ""
    return request_id


def snapshot_model(instance, fields: list[str] | None = None) -> dict:
    if instance is None:
        return {}
    if fields is None:
        data = model_to_dict(instance)
    else:
        data = {field: getattr(instance, field) for field in fields}
    return _json_ready(data)


def _actor_or_none(actor):
    if actor and getattr(actor, "is_authenticated", False):
        return actor
    return None


def _object_type_for(target) -> str:
    model = getattr(target, "_meta", None)
    if model:
        return model.model_name
    return target.__class__.__name__.lower()


def _request_id(request) -> str:
    if request is None:
        return ""
    meta = getattr(request, "META", {})
    return sanitize_request_id(getattr(request, "request_id", "")) or sanitize_request_id(
        meta.get("HTTP_X_REQUEST_ID", "")
    )


def _ip_address(request):
    if request is None:
        return None
    meta = getattr(request, "META", {})
    forwarded_for = meta.get("HTTP_X_FORWARDED_FOR")
    if getattr(settings, "AUDIT_TRUST_X_FORWARDED_FOR", False) and forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return meta.get("REMOTE_ADDR")


def _user_agent(request) -> str:
    if request is None:
        return ""
    meta = getattr(request, "META", None)
    if meta is None:
        return ""
    return meta.get("HTTP_USER_AGENT") or "unknown"


def _json_ready(value):
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, set):
        return [_json_ready(item) for item in sorted(value, key=str)]
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "pk"):
        return str(value.pk)
    copied = copy.deepcopy(value)
    return json.loads(json.dumps(copied, cls=DjangoJSONEncoder, default=str))
