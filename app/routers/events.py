from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import PromotionEventCreate
from app.services.event_service import get_impression_by_id, insert_promotion_event

router = APIRouter()

@router.post("/promotion-events")
def log_event(event: PromotionEventCreate, db: Session = Depends(get_db)):
    if get_impression_by_id(db, event.impression_id) is None:
        raise HTTPException(status_code=404, detail="Promotion impression not found")

    try:
        promotion_event = insert_promotion_event(db, event.impression_id, event.event_type)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to log promotion event") from exc

    return promotion_event
