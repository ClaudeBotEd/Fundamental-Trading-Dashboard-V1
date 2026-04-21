from enum import Enum
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Horizon(str, Enum):
    INTRADAY = "intraday"
    WEEKLY = "weekly"
    MACRO = "macro"


class BiasLabel(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class Factor(BaseModel):
    label: str
    weight: float = Field(ge=0.0, le=1.0)
    direction: Literal["bullish", "bearish", "neutral"]


class BiasResult(BaseModel):
    pair: str
    horizon: Horizon
    timestamp: datetime
    bias: BiasLabel
    conviction: int = Field(ge=0, le=100)
    factors: list[Factor]
    risks_to_thesis: list[str]
    reasoning: str
    model: str
    prompt_cache_hit: bool = False
    conflict_with: list[Horizon] = Field(default_factory=list)
    news_refs: list[str] = Field(default_factory=list)
    feedback: Optional[Literal["positive", "negative"]] = None
    feedback_note: Optional[str] = None


class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    published_at: datetime
    sentiment: Literal["bullish", "bearish", "neutral"]
    relevant_pairs: list[str]
    summary: str


class CalendarEvent(BaseModel):
    datetime_utc: datetime
    country: str
    name: str
    impact: Literal["high", "medium", "low"]
    previous: Optional[str] = None
    forecast: Optional[str] = None
    actual: Optional[str] = None


class RegimeScore(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    label: str
    vix_z: float
    audjpy_z: float
    hyg_lqd_z: float
    es_momentum_z: float
    computed_at: datetime
