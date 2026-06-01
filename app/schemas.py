from typing import Literal

from pydantic import BaseModel


PromotionEventType = Literal["click", "stream", "skip", "save"]


class PromotionEventCreate(BaseModel):
    impression_id: int
    event_type: PromotionEventType
