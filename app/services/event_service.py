from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.utils import execute_query


def get_impression_by_id(db: Session, impression_id: int):
    rows = execute_query(
        db,
        query="""
            SELECT impression_id
            FROM promotion_impressions
            WHERE impression_id = :impression_id
        """,
        params={"impression_id": impression_id},
    )
    return rows[0] if rows else None


def insert_promotion_event(db: Session, impression_id: int, event_type: str) -> dict:
    result = db.execute(
        text(
            """
            INSERT INTO promotion_events (impression_id, event_type)
            VALUES (:impression_id, :event_type)
            """
        ),
        {"impression_id": impression_id, "event_type": event_type},
    )
    event_id = result.lastrowid
    rows = execute_query(
        db,
        query="""
            SELECT
                event_id,
                impression_id,
                event_type,
                event_timestamp
            FROM promotion_events
            WHERE event_id = :event_id
        """,
        params={"event_id": event_id},
    )
    if not rows:
        raise RuntimeError(f"Promotion event insert succeeded but event_id={event_id} could not be loaded.")
    return dict(rows[0])
