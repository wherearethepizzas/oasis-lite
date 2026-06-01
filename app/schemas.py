from typing import Literal

from pydantic import BaseModel


PromotionEventType = Literal["click", "stream", "skip", "save"]
CampaignMetricType = Literal["clicks", "streams", "saves", "skips", "click_through_rate", "stream_rate", "save_rate", "skip_rate"]


class PromotionEventCreate(BaseModel):
    impression_id: int
    event_type: PromotionEventType
