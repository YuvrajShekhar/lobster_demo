"""Declarative description of a flat file's layout — the thing you'd hand to
a new trading partner ("here's how to send us your purchase orders") and the
thing this service uses to parse what they actually send.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"


class FieldSpec(BaseModel):
    name: str = Field(min_length=1, description="Key this field will have in the output JSON.")
    type: FieldType = FieldType.STRING
    required: bool = True
    trim: bool = True

    # Fixed-width layouts locate a field by character position.
    start: int | None = Field(default=None, ge=0, description="0-indexed start column (fixed-width only).")
    length: int | None = Field(default=None, gt=0, description="Field width in characters (fixed-width only).")

    # Delimited layouts locate a field by column index.
    column: int | None = Field(default=None, ge=0, description="0-indexed column number (delimited only).")

    # Only meaningful when type == DATE.
    date_format: str = "%Y-%m-%d"

    @model_validator(mode="after")
    def check_position_is_set(self) -> "FieldSpec":
        has_fixed_width_position = self.start is not None and self.length is not None
        has_delimited_position = self.column is not None
        if not has_fixed_width_position and not has_delimited_position:
            raise ValueError(f"field '{self.name}' needs either (start, length) or column")
        return self


class ConversionSchema(BaseModel):
    format: Literal["fixed_width", "delimited"]
    delimiter: str = ","
    skip_header_rows: int = 0
    fields: list[FieldSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def check_fields_match_format(self) -> "ConversionSchema":
        for field in self.fields:
            if self.format == "fixed_width" and field.start is None:
                raise ValueError(f"field '{field.name}': fixed_width schemas need (start, length)")
            if self.format == "delimited" and field.column is None:
                raise ValueError(f"field '{field.name}': delimited schemas need a column index")
        return self
