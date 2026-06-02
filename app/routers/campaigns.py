from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Annotated

from app.database import get_db
from app.metrics import active_campaigns
from app.services.campaign_service import get_campaign_by_id, get_campaign_metrics_by_id, get_all_campaign_metrics
from app.services.utils import execute_query
from app.schemas import ActiveCampaignResponse, CampaignMetricType, CampaignMetricsResponse, MessageResponse

router = APIRouter()

@router.get("/active", response_model=list[ActiveCampaignResponse] | MessageResponse)
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

    active_campaigns.set(len(campaigns))
    if len(campaigns) == 0:
        return {"message": "There are no active campaigns"}
    else:
        return [dict(campaign) for campaign in campaigns]


@router.get("/{campaign_id}/metrics", response_model=CampaignMetricsResponse)
def get_campaign_metrics_endpoint(campaign_id: int, db: Session = Depends(get_db)):
    if get_campaign_by_id(campaign_id, db) is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return get_campaign_metrics_by_id(campaign_id, db)

@router.get("/leaderboard", response_model=list[CampaignMetricsResponse])
def get_campaigns_leaderboard(
    metric: Annotated[CampaignMetricType, Query()] = "stream_rate",
    db: Session = Depends(get_db)
):    
    results = get_all_campaign_metrics(db)
    return sorted(results, key=lambda campaign: campaign.get(metric), reverse=True)
