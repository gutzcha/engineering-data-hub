from datetime import UTC, datetime

import pytest
from rest_framework import serializers

from apps.records.codes import generate_record_code, render_code_pattern
from apps.records.models import CodeSequence


def test_render_code_pattern_supports_static_prefix_and_padded_sequence():
    rendered = render_code_pattern("PROD-{seq:000000}", 1)

    assert rendered == "PROD-000001"


def test_render_code_pattern_supports_year_and_sequence_width():
    now = datetime(2026, 6, 6, tzinfo=UTC)

    rendered = render_code_pattern("MAT-{year}-{seq:0000}", 1, now=now)

    assert rendered == "MAT-2026-0001"


@pytest.mark.django_db
def test_generate_record_code_increments_sequence_per_object_type_and_pattern():
    first = generate_record_code("product", "PROD-{seq:000000}")
    second = generate_record_code("product", "PROD-{seq:000000}")
    material = generate_record_code(
        "raw_material",
        "MAT-{year}-{seq:0000}",
        now=datetime(2026, 6, 6, tzinfo=UTC),
    )

    assert first == "PROD-000001"
    assert second == "PROD-000002"
    assert material == "MAT-2026-0001"
    assert CodeSequence.objects.get(object_type_key="product").next_value == 3


@pytest.mark.django_db
def test_generate_record_code_rejects_patterns_without_sequence_token():
    with pytest.raises(serializers.ValidationError) as error:
        generate_record_code("product", "STATIC")

    assert error.value.detail["code_pattern"][0] == "Code pattern must include a sequence token."
