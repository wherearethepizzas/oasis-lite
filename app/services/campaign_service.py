from sqlalchemy.orm import Session
from typing import Any, List

from app.services.utils import execute_query


def get_campaign_by_id(campaign_id: int, db: Session):
    rows = execute_query(
        db,
        query="""
            SELECT campaign_id
            FROM promotion_campaigns
            WHERE campaign_id = :campaign_id
        """,
        params={"campaign_id": campaign_id},
    )
    return rows[0] if rows else None


def get_all_campaign_metrics(db: Session) -> List[dict[str, Any]]:
    rows = execute_query(
        db,
        query="""
            SELECT
                pc.campaign_id,
                COUNT(DISTINCT pi.impression_id) AS impressions,
                COALESCE(SUM(CASE WHEN pe.event_type = 'click' THEN 1 ELSE 0 END), 0) AS clicks,
                COALESCE(SUM(CASE WHEN pe.event_type = 'stream' THEN 1 ELSE 0 END), 0) AS streams,
                COALESCE(SUM(CASE WHEN pe.event_type = 'save' THEN 1 ELSE 0 END), 0) AS saves,
                COALESCE(SUM(CASE WHEN pe.event_type = 'skip' THEN 1 ELSE 0 END), 0) AS skips
            FROM promotion_campaigns pc
            LEFT JOIN promotion_impressions pi ON pi.campaign_id = pc.campaign_id
            LEFT JOIN promotion_events pe ON pe.impression_id = pi.impression_id
            GROUP BY pc.campaign_id
        """,
    )

    if not rows:
        return []

    def rate(count: int) -> float:
        return round(count / impressions, 3) if impressions else 0.0
    
    results = []
    
    for record in rows:
        campaign_id = int(record.get("campaign_id"))
        impressions = int(record.get("impressions") or 0)
        clicks = int(record.get("clicks") or 0)
        streams = int(record.get("streams") or 0)
        saves = int(record.get("saves") or 0)
        skips = int(record.get("skips") or 0)

        results.append(
            {
                "campaign_id": campaign_id,
                "impressions": impressions,
                "clicks": clicks,
                "streams": streams,
                "saves": saves,
                "skips": skips,
                "click_through_rate": rate(clicks),
                "stream_rate": rate(streams),
                "save_rate": rate(saves),
                "skip_rate": rate(skips),
            }
        )

    return results

def get_campaign_metrics_by_id(campaign_id: int, db: Session) -> dict:
    results = [campaign for campaign in get_all_campaign_metrics(db) if campaign.get("campaign_id") == campaign_id]
    return results[0] if results else None
    
