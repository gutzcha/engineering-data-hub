# ===
# File Summary
# Path: backend\apps\audit\middleware.py
# Type: python
# Purpose: Audit service for immutable audit log capture and retrieval APIs.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: AuditRequestMiddleware, __init__, __call__
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===
# 

import uuid

from apps.audit.services import sanitize_request_id


class AuditRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = sanitize_request_id(request.headers.get("X-Request-ID")) or uuid.uuid4().hex
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response

