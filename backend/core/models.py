from enum import Enum
from typing import Literal, Optional
from pydantic import AwareDatetime, BaseModel, Field, HttpUrl


class Horizon(str, Enum):
    INTRADAY = "intraday"
    WEEKLY = "weekly"
    MACRO = "macro"


class BiasLabel(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class SignalDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class RegimeLabel(str, Enum):
    STRONG_RISK_ON = "Strong Risk-On"
    MILD_RISK_ON = "Mild Risk-On"
    NEUTRAL = "Neutral"
    MILD_RISK_OFF = "Mild Risk-Off"
    STRONG_RISK_OFF = "Strong Risk-Off"


class Factor(BaseModel):
    label: str
    weight: float = Field(ge=0.0, le=1.0)
    direction: SignalDirection


class BiasResult(BaseModel):
    pair: str
    horizon: Horizon
    timestamp: AwareDatetime
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
    url: HttpUrl
    published_at: AwareDatetime
    sentiment: SignalDirection
    relevant_pairs: list[str]
    summary: str


class CalendarEvent(BaseModel):
    datetime_utc: AwareDatetime
    country: str
    name: str
    impact: Literal["high", "medium", "low"]
    previous: Optional[str] = None
    forecast: Optional[str] = None
    actual: Optional[str] = None


class RegimeScore(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    label: RegimeLabel
    vix_z: float
    audjpy_z: float
    hyg_lqd_z: float
    es_momentum_z: float
    computed_at: AwareDatetime
