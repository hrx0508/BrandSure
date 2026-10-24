from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import RuleType, Severity


class RuleIn(BaseModel):
    type: RuleType
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=4000)
    severity: Severity = "medium"
    valid_from: date | None = None
    valid_until: date | None = None
    params: dict[str, Any] = {}
    source: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _check_params(self):
        need = {"preferred_term": "preferred", "banned_term": "banned", "required_disclaimer": "phrase"}
        key = need.get(self.type)
        if key and not str(self.params.get(key, "")).strip():
            raise ValueError(f"{self.type} needs params.{key}")
        if self.type == "palette":
            cols = self.params.get("colors")
            import re
            if not isinstance(cols, list) or not cols or not all(isinstance(c, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", c) for c in cols):
                raise ValueError("palette needs params.colors as a list of #RRGGBB values")
        if self.type == "expiry" and not self.valid_until:
            raise ValueError("expiry rules need valid_until")
        return self


class ConfirmIn(BaseModel):
    rules: list[RuleIn] = Field(min_length=1, max_length=200)


class GoogleDocIn(BaseModel):
    url: str = Field(min_length=10, max_length=500)
    name: str | None = Field(default=None, max_length=200)
