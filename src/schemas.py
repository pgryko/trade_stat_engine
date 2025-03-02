from typing import List

from pydantic import BaseModel, Field, field_validator


class BatchRequest(BaseModel):
    symbol: str
    values: List[float] = Field(..., min_items=1, max_items=10000)

    @field_validator("symbol")
    @classmethod
    def symbol_must_be_valid(cls, v: str) -> str:
        if not v or len(v) > 20:  # Arbitrary reasonable limit
            raise ValueError("Symbol must be non-empty and not exceed 20 characters")
        return v


class StatsResponse(BaseModel):
    min: float
    max: float
    last: float
    avg: float
    var: float
