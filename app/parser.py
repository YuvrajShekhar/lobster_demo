"""Parses flat files against a ConversionSchema.

Bad rows don't fail the whole file — a batch of 5,000 EDI lines with three
malformed ones should still hand back the other 4,997, with the bad ones
called out by line number. That's the difference between a parser you can
actually point at a real partner feed and one that only works on clean demo
data.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel

from app.schema_models import ConversionSchema, FieldSpec, FieldType


class RowError(BaseModel):
    line_number: int
    message: str


class ConversionResult(BaseModel):
    records: list[dict[str, Any]]
    errors: list[RowError]


def coerce_value(raw: str, field: FieldSpec) -> Any:
    value = raw.strip() if field.trim else raw

    if value == "":
        if field.required:
            raise ValueError(f"'{field.name}' is required but empty")
        return None

    if field.type == FieldType.STRING:
        return value
    if field.type == FieldType.INTEGER:
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"'{field.name}' is not a valid integer: '{value}'") from None
    if field.type == FieldType.DECIMAL:
        try:
            return str(Decimal(value))
        except InvalidOperation:
            raise ValueError(f"'{field.name}' is not a valid decimal: '{value}'") from None
    if field.type == FieldType.DATE:
        try:
            return datetime.strptime(value, field.date_format).date().isoformat()
        except ValueError:
            raise ValueError(
                f"'{field.name}' does not match date format {field.date_format}: '{value}'"
            ) from None

    raise ValueError(f"unsupported field type: {field.type}")  # pragma: no cover — exhaustive above


def _extract_fixed_width(line: str, field: FieldSpec) -> str:
    assert field.start is not None and field.length is not None
    return line[field.start : field.start + field.length]


def _extract_delimited(columns: list[str], field: FieldSpec) -> str:
    assert field.column is not None
    if field.column >= len(columns):
        return ""
    return columns[field.column]


def parse_line(line: str, schema: ConversionSchema) -> dict[str, Any]:
    columns = line.split(schema.delimiter) if schema.format == "delimited" else []
    record: dict[str, Any] = {}
    for field in schema.fields:
        raw = _extract_fixed_width(line, field) if schema.format == "fixed_width" else _extract_delimited(
            columns, field
        )
        record[field.name] = coerce_value(raw, field)
    return record


def convert(text: str, schema: ConversionSchema) -> ConversionResult:
    lines = text.splitlines()[schema.skip_header_rows :]

    records: list[dict[str, Any]] = []
    errors: list[RowError] = []

    for offset, line in enumerate(lines):
        line_number = offset + schema.skip_header_rows + 1
        if line.strip() == "":
            continue
        try:
            records.append(parse_line(line, schema))
        except ValueError as exc:
            errors.append(RowError(line_number=line_number, message=str(exc)))

    return ConversionResult(records=records, errors=errors)
