from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.campaign_service import get_campaign_by_id, get_campaign_metrics
from app.services.utils import execute_query

router = APIRouter()

@router.get("/active")
def get_active_campaigns(db: Session = Depends(get_db)):
    campaigns = execute_query(
        db,
        query="""
            SELECT 
                campaign_id,
                track_id,
                artist_id,
                objective,
                bid_weight,
                daily_budget,
                remaining_budget,
                target_genre,
                max_impressions_per_user_per_day
            FROM promotion_campaigns
            WHERE status = :status 
        """,
        params={"status":"active"},
    )

    if len(campaigns) == 0:
        return {"message": "There are no active campaigns"}
    else:
        return campaigns


@router.get("/{campaign_id}/metrics")
def get_campaign_metrics_endpoint(campaign_id: int, db: Session = Depends(get_db)):
    if get_campaign_by_id(db, campaign_id) is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return get_campaign_metrics(db, campaign_id)
