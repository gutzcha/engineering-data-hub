# ===
# File Summary
# Path: backend\apps\records\codes.py
# Type: python
# Purpose: Records domain for core traceability records, validation, and coding constraints.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: render_code_pattern, replace_sequence, generate_record_code, validate_code_pattern
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

import re

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.records.models import CodeSequence


SEQ_TOKEN_RE = re.compile(r"\{seq:(0+)\}")


def render_code_pattern(pattern: str, sequence: int, now=None) -> str:
    validate_code_pattern(pattern)
    current_time = now or timezone.now()

    def replace_sequence(match):
        width = len(match.group(1))
        return f"{sequence:0{width}d}"

    rendered = SEQ_TOKEN_RE.sub(replace_sequence, pattern)
    return rendered.replace("{year}", str(current_time.year))


@transaction.atomic
def generate_record_code(object_type_key: str, code_pattern: str, now=None) -> str:
    validate_code_pattern(code_pattern)
    current_time = now or timezone.now()
    year_scope = current_time.year if "{year}" in code_pattern else None
    sequence, _created = CodeSequence.objects.select_for_update().get_or_create(
        object_type_key=object_type_key,
        code_pattern=code_pattern,
        year_scope=year_scope,
        defaults={"next_value": 1},
    )
    value = sequence.next_value
    sequence.next_value += 1
    sequence.save(update_fields=["next_value", "updated_at"])
    return render_code_pattern(code_pattern, value, now=current_time)


def validate_code_pattern(pattern: str) -> None:
    if not isinstance(pattern, str) or SEQ_TOKEN_RE.search(pattern) is None:
        raise serializers.ValidationError(
            {"code_pattern": ["Code pattern must include a sequence token."]}
        )

