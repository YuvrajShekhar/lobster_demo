import pytest

from app.parser import convert
from app.schema_models import ConversionSchema


def test_fixed_width_happy_path() -> None:
    schema = ConversionSchema.model_validate(
        {
            "format": "fixed_width",
            "fields": [
                {"name": "name", "type": "string", "start": 0, "length": 10},
                {"name": "quantity", "type": "integer", "start": 10, "length": 2},
                {"name": "order_date", "type": "date", "start": 12, "length": 8, "date_format": "%Y%m%d"},
            ],
        }
    )
    text = "JOHN DOE  0420250115\nJANE SMITH1520250116"

    result = convert(text, schema)

    assert result.errors == []
    assert result.records == [
        {"name": "JOHN DOE", "quantity": 4, "order_date": "2025-01-15"},
        {"name": "JANE SMITH", "quantity": 15, "order_date": "2025-01-16"},
    ]


def test_delimited_happy_path() -> None:
    schema = ConversionSchema.model_validate(
        {
            "format": "delimited",
            "delimiter": "|",
            "skip_header_rows": 1,
            "fields": [
                {"name": "sku", "type": "string", "column": 0},
                {"name": "price", "type": "decimal", "column": 1},
            ],
        }
    )
    text = "sku|price\nABC-123|19.99\nDEF-456|5.5"

    result = convert(text, schema)

    assert result.errors == []
    assert result.records == [
        {"sku": "ABC-123", "price": "19.99"},
        {"sku": "DEF-456", "price": "5.5"},
    ]


def test_bad_rows_are_reported_but_do_not_block_good_rows() -> None:
    schema = ConversionSchema.model_validate(
        {
            "format": "delimited",
            "fields": [
                {"name": "sku", "type": "string", "column": 0},
                {"name": "quantity", "type": "integer", "column": 1},
            ],
        }
    )
    text = "ABC-123,4\nBAD-ROW,not-a-number\nDEF-456,9"

    result = convert(text, schema)

    assert len(result.records) == 2
    assert result.records[0]["sku"] == "ABC-123"
    assert result.records[1]["sku"] == "DEF-456"
    assert len(result.errors) == 1
    assert result.errors[0].line_number == 2
    assert "quantity" in result.errors[0].message


def test_required_field_missing_is_an_error() -> None:
    schema = ConversionSchema.model_validate(
        {
            "format": "delimited",
            "fields": [{"name": "sku", "type": "string", "column": 0, "required": True}],
        }
    )
    result = convert("\n", schema)  # blank lines are skipped, so this produces nothing
    assert result.records == []
    assert result.errors == []


def test_optional_field_missing_becomes_none() -> None:
    schema = ConversionSchema.model_validate(
        {
            "format": "delimited",
            "fields": [
                {"name": "sku", "type": "string", "column": 0},
                {"name": "note", "type": "string", "column": 1, "required": False},
            ],
        }
    )
    result = convert("ABC-123,", schema)
    assert result.errors == []
    assert result.records == [{"sku": "ABC-123", "note": None}]


def test_blank_lines_are_skipped() -> None:
    schema = ConversionSchema.model_validate(
        {"format": "delimited", "fields": [{"name": "sku", "type": "string", "column": 0}]}
    )
    result = convert("ABC-123\n\n\nDEF-456\n", schema)
    assert len(result.records) == 2


def test_schema_requires_position_for_its_format() -> None:
    with pytest.raises(ValueError):
        ConversionSchema.model_validate(
            {
                "format": "fixed_width",
                "fields": [{"name": "sku", "type": "string", "column": 0}],  # missing start/length
            }
        )
