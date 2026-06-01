from sqlalchemy.orm import Session

from app.services.utils import execute_query


def get_campaign_by_id(db: Session, campaign_id: int):
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


def get_campaign_metrics(db: Session, campaign_id: int) -> dict:
    rows = execute_query(
        db,
        query="""
            SELECT
                COUNT(DISTINCT pi.impression_id) AS impressions,
                COALESCE(SUM(CASE WHEN pe.event_type = 'click' THEN 1 ELSE 0 END), 0) AS clicks,
                COALESCE(SUM(CASE WHEN pe.event_type = 'stream' THEN 1 ELSE 0 END), 0) AS streams,
                COALESCE(SUM(CASE WHEN pe.event_type = 'save' THEN 1 ELSE 0 END), 0) AS saves,
                COALESCE(SUM(CASE WHEN pe.event_type = 'skip' THEN 1 ELSE 0 END), 0) AS skips
            FROM promotion_impressions pi
            LEFT JOIN promotion_events pe ON pe.impression_id = pi.impression_id
            WHERE pi.campaign_id = :campaign_id
        """,
        params={"campaign_id": campaign_id},
    )
    row = dict(rows[0]) if rows else {}
    impressions = int(row.get("impressions") or 0)
    clicks = int(row.get("clicks") or 0)
    streams = int(row.get("streams") or 0)
    saves = int(row.get("saves") or 0)
    skips = int(row.get("skips") or 0)

    def rate(count: int) -> float:
        return round(count / impressions, 3) if impressions else 0.0

    return {
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
