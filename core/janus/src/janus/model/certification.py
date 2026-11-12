"""The ``certified`` property on MDL models.

Certification is a convention on the free-form ``properties`` map: a model is
certified when its metadata sets ``certified: "true"`` (a YAML boolean ``true``
is accepted too, since the engine stores booleans as the same strings). The
engine enforces it only when ``require_certified`` is set; everywhere else it is
reported, not enforced.
"""

from __future__ import annotations

from typing import Any

CERTIFIED_PROPERTY = "certified"
CERTIFIED_VALUES = ("true", "false")


def is_certified(properties: Any) -> bool:
    """True when a model's ``properties`` mapping marks it certified."""
    if not isinstance(properties, dict):
        return False
    value = properties.get(CERTIFIED_PROPERTY)
    return value is True or value == "true"


def certified_value_error(properties: Any) -> str | None:
    """Describe an invalid ``certified`` value, or return ``None`` if it is fine."""
    if not isinstance(properties, dict) or CERTIFIED_PROPERTY not in properties:
        return None
    value = properties[CERTIFIED_PROPERTY]
    if isinstance(value, bool):
        return None
    if value in CERTIFIED_VALUES:
        return None
    return f'properties.certified must be "true" or "false", got {value!r}'
