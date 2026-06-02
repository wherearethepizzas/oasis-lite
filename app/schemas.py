from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


PromotionEventType = Literal["click", "stream", "skip", "save"]
RecommendationRelevanceMode = Literal["track", "genre", "artist"]
CampaignMetricType = Literal[
    "impressions",
    "clicks",
    "streams",
    "saves",
    "skips",
    "click_through_rate",
    "stream_rate",
    "save_rate",
    "skip_rate",
]


class MessageResponse(BaseModel):
    message: str


class RootResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str


class DatabaseHealthResponse(BaseModel):
    status: str
    database: str


class TrackResponse(BaseModel):
    track_name: str
    genre: str | None = None
    release_year: int | None = None
    artist_name: str


class UserResponse(BaseModel):
    user_id: str
    created_at: datetime
    updated_at: datetime


class RecommendationReadyUserResponse(BaseModel):
    user_id: str


class ActiveCampaignResponse(BaseModel):
    campaign_id: int
    track_id: str
    artist_id: int
    objective: str
    bid_weight: Decimal
    daily_budget: Decimal
    remaining_budget: Decimal
    target_genre: str | None = None
    max_impressions_per_user_per_day: int


class CampaignMetricsResponse(BaseModel):
    campaign_id: int
    impressions: int
    clicks: int
    streams: int
    saves: int
    skips: int
    click_through_rate: float
    stream_rate: float
    save_rate: float
    skip_rate: float


class PromotionImpressionResponse(BaseModel):
    impression_id: int
    campaign_id: int
    user_id: str
    track_id: str
    rank_position: int
    relevance_score: Decimal | None = None
    campaign_score: Decimal | None = None
    diversity_bonus: Decimal | None = None
    fatigue_penalty: Decimal | None = None
    final_score: Decimal | None = None
    served_at: datetime


class PromotedTrackRecommendationResponse(BaseModel):
    impression_id: int
    rank_position: int
    track_id: str
    track_name: str
    artist_id: int
    artist_name: str
    genre: str | None = None
    campaign_id: int
    objective: str
    relevance_score: float
    campaign_score: float
    diversity_bonus: float
    fatigue_penalty: float
    final_score: float


class RecommendationEvaluationMetricsResponse(BaseModel):
    user_id: str
    k: int
    relevance_mode: RecommendationRelevanceMode
    threshold: int
    recommended_count: int
    relevant_items_count: int
    relevant_recommended_count: int
    precision_at_k: float
    recall_at_k: float
    ndcg_at_k: float
    map_at_k: float


class PromotedRecommendationsResponse(BaseModel):
    user_id: str
    limit: int
    count: int
    recommendations: list[PromotedTrackRecommendationResponse]
    metrics: RecommendationEvaluationMetricsResponse


class PromotionEventCreate(BaseModel):
    impression_id: int
    event_type: PromotionEventType


class PromotionEventResponse(BaseModel):
    event_id: int
    impression_id: int
    event_type: PromotionEventType
    event_timestamp: datetime
