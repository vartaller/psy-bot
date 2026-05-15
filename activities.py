"""
Activity schemas — declarative descriptions of each activity's questionnaire.

Each activity is a list of `Field`s. The history engine, render functions,
and edit keyboards all walk these schemas instead of hardcoding field names.

To add a new activity:
1. Add its Field list below.
2. Register it in SCHEMAS.
3. Add its row to schema.sql.
4. Add a handler module that drives its FSM (questionnaire logic stays per-activity).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FieldType(str, Enum):
    SCALE  = "scale"   # integer 1..5, rendered as stars
    CHOICE = "choice"  # pick from options list OR enter custom text
    TEXT   = "text"    # free text


@dataclass(frozen=True)
class Field:
    name: str                                # key in `responses` JSON
    type: FieldType
    label_key: str                           # T(lang, label_key) → label shown in renders / edit buttons
    block_header_key: str | None = None      # if set, render this header above the field in the body
    options_key: str | None = None           # for CHOICE: T(lang, options_key) → list[str]


THINKING_PATTERN_SCHEMA: list[Field] = [
    Field("irritation", FieldType.SCALE,  "tp_label_irritation", block_header_key="tp_block1_header"),
    Field("excitement", FieldType.SCALE,  "tp_label_excitement"),
    Field("sensation",  FieldType.TEXT,   "tp_label_sensation"),
    Field("feeling",    FieldType.CHOICE, "tp_label_feeling", block_header_key="tp_block2_header", options_key="feelings"),
    Field("emotion",    FieldType.CHOICE, "tp_label_emotion", options_key="emotions"),
    Field("impression", FieldType.TEXT,   "tp_label_impression"),
    Field("meaning",    FieldType.TEXT,   "tp_label_meaning",  block_header_key="tp_block3_header"),
    Field("idea",       FieldType.TEXT,   "tp_label_idea"),
]


INDIVIDUALITY_CARDS_SCHEMA: list[Field] = [
    Field("q1", FieldType.CHOICE, "ic_label_q1", options_key="ic_q1_options"),
    Field("q2", FieldType.CHOICE, "ic_label_q2", options_key="ic_q2_options"),
    Field("q3", FieldType.CHOICE, "ic_label_q3", options_key="ic_q3_options"),
]


SCHEMAS: dict[str, list[Field]] = {
    "thinking_pattern":    THINKING_PATTERN_SCHEMA,
    "individuality_cards": INDIVIDUALITY_CARDS_SCHEMA,
}


def get_schema(slug: str) -> list[Field]:
    """Return the field schema for an activity slug, or empty list if unknown."""
    return SCHEMAS.get(slug, [])


def get_field(slug: str, name: str) -> Field | None:
    for f in get_schema(slug):
        if f.name == name:
            return f
    return None


def is_encrypted_type(t: FieldType) -> bool:
    """Text + choice answers contain user input → encrypt at rest. Scales are integers → store plainly."""
    return t in (FieldType.TEXT, FieldType.CHOICE)
