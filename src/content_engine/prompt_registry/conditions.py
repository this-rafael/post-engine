"""Avaliacao declarativa e segura de condicoes de composicao."""
from __future__ import annotations

from typing import Any


ALLOWED_FIELDS = frozenset({
    "content_type", "is_visual_track", "platform", "operation_mode",
    "retry_attempt", "has_slidemark", "persona_key",
})
ALLOWED_OPERATORS = frozenset({
    "EQUALS", "NOT_EQUALS", "IN", "NOT_IN", "IS_TRUE", "IS_FALSE", "EXISTS", "NOT_EXISTS",
})


class InvalidPromptCondition(ValueError):
    pass


def validate_condition(condition: dict[str, Any] | None) -> None:
    if not condition:
        return
    field = condition.get("field")
    operator = condition.get("operator")
    if field not in ALLOWED_FIELDS:
        raise InvalidPromptCondition(f"Campo de condicao nao permitido: {field}")
    if operator not in ALLOWED_OPERATORS:
        raise InvalidPromptCondition(f"Operador de condicao nao permitido: {operator}")
    if operator in {"IN", "NOT_IN"} and not isinstance(condition.get("value"), list):
        raise InvalidPromptCondition(f"{operator} requer uma lista de valores")
    if operator not in {"IS_TRUE", "IS_FALSE", "EXISTS", "NOT_EXISTS"} and "value" not in condition:
        raise InvalidPromptCondition(f"{operator} requer valor de condicao")


def applies(condition: dict[str, Any] | None, context: dict[str, Any]) -> bool:
    if not condition or not condition.get("operator"):
        return True
    validate_condition(condition)
    field = str(condition["field"])
    operator = str(condition["operator"])
    actual = context.get(field)
    value = condition.get("value")
    if operator == "EQUALS":
        return actual == value
    if operator == "NOT_EQUALS":
        return actual != value
    if operator == "IN":
        return actual in value
    if operator == "NOT_IN":
        return actual not in value
    if operator == "IS_TRUE":
        return actual is True
    if operator == "IS_FALSE":
        return actual is False
    if operator == "EXISTS":
        return field in context and actual is not None
    if operator == "NOT_EXISTS":
        return field not in context or actual is None
    raise InvalidPromptCondition(f"Operador nao suportado: {operator}")


__all__ = ["ALLOWED_FIELDS", "ALLOWED_OPERATORS", "InvalidPromptCondition", "applies", "validate_condition"]
