from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.utils import execute_query


def get_user_taste_by_id(db: Session, user_id: str):
    rows = execute_query(
        db,
        query="""
            SELECT
                utp.user_id,
                utp.danceability,
                utp.energy,
                utp.acousticness,
                utp.instrumentalness,
                utp.valence,
                utp.tempo
            FROM user_taste_profiles utp
            WHERE utp.user_id = :user_id
        """,
        params={"user_id": user_id},
    )

    return dict(rows[0]) if rows else None


def get_active_campaigns_audio_features(db: Session, user_id: str):
    rows = execute_query(
        db,
        query="""
            SELECT
                pc.campaign_id,
                pc.objective,
                pc.bid_weight,
                pc.daily_budget,
                pc.remaining_budget,
                pc.target_genre,
                pc.max_impressions_per_user_per_day,
                pc.track_id,
                pc.artist_id,
                t.track_name,
                t.genre,
                a.artist_name,
                taf.danceability,
                taf.energy,
                taf.acousticness,
                taf.instrumentalness,
                taf.valence,
                taf.tempo,
                COUNT(pi.impression_id) AS impressions_served_today
            FROM promotion_campaigns pc
            JOIN tracks t ON t.track_id = pc.track_id
            JOIN artists a ON a.artist_id = pc.artist_id
            JOIN track_audio_features taf ON taf.track_id = pc.track_id
            LEFT JOIN promotion_impressions pi
                ON pi.campaign_id = pc.campaign_id
               AND pi.user_id = :user_id
               AND DATE(pi.served_at) = CURDATE()
            WHERE pc.status = 'active'
              AND CURDATE() BETWEEN pc.start_date AND pc.end_date
              AND pc.remaining_budget > 0
            GROUP BY
                pc.campaign_id,
                pc.objective,
                pc.bid_weight,
                pc.daily_budget,
                pc.remaining_budget,
                pc.target_genre,
                pc.max_impressions_per_user_per_day,
                pc.track_id,
                pc.artist_id,
                t.track_name,
                t.genre,
                a.artist_name,
                taf.danceability,
                taf.energy,
                taf.acousticness,
                taf.instrumentalness,
                taf.valence,
                taf.tempo
            HAVING impressions_served_today < pc.max_impressions_per_user_per_day
            ORDER BY pc.bid_weight DESC, pc.campaign_id ASC
        """,
        params={"user_id": user_id},
    )

    return [dict(row) for row in rows]


def _get_relevant_track_ids(db: Session, user_id: str, threshold: int) -> set[str]:
    rows = execute_query(
        db,
        query="""
            SELECT track_id
            FROM user_track_plays
            WHERE user_id = :user_id
              AND play_count >= :threshold
        """,
        params={"user_id": user_id, "threshold": threshold},
    )
    return {row["track_id"] for row in rows}


def _get_relevant_genres(db: Session, user_id: str, threshold: int) -> set[str]:
    rows = execute_query(
        db,
        query="""
            SELECT t.genre
            FROM user_track_plays utp
            JOIN tracks t ON t.track_id = utp.track_id
            WHERE utp.user_id = :user_id
              AND t.genre IS NOT NULL
            GROUP BY t.genre
            HAVING SUM(utp.play_count) >= :threshold
        """,
        params={"user_id": user_id, "threshold": threshold},
    )
    return {row["genre"] for row in rows}


def _get_relevant_artist_ids(db: Session, user_id: str, threshold: int) -> set[int]:
    rows = execute_query(
        db,
        query="""
            SELECT ta.artist_id
            FROM user_track_plays utp
            JOIN track_artists ta ON ta.track_id = utp.track_id
            WHERE utp.user_id = :user_id
            GROUP BY ta.artist_id
            HAVING SUM(utp.play_count) >= :threshold
        """,
        params={"user_id": user_id, "threshold": threshold},
    )
    return {int(row["artist_id"]) for row in rows}


def get_relevant_items(db: Session, user_id: str, relevance_mode: str, threshold: int) -> set:
    if relevance_mode == "track":
        return _get_relevant_track_ids(db, user_id, threshold)
    if relevance_mode == "genre":
        return _get_relevant_genres(db, user_id, threshold)
    if relevance_mode == "artist":
        return _get_relevant_artist_ids(db, user_id, threshold)
    raise ValueError(f"Unsupported relevance_mode: {relevance_mode}")


def insert_promotion_impressions(db: Session, user_id: str, recommendations: list[dict[str, Any]]) -> int:
    if not recommendations:
        return 0

    rows = [
        {
            "campaign_id": recommendation["campaign_id"],
            "user_id": user_id,
            "track_id": recommendation["track_id"],
            "rank_position": recommendation["rank_position"],
            "relevance_score": recommendation["relevance_score"],
            "campaign_score": recommendation["campaign_score"],
            "diversity_bonus": recommendation["diversity_bonus"],
            "fatigue_penalty": recommendation["fatigue_penalty"],
            "final_score": recommendation["final_score"],
        }
        for recommendation in recommendations
    ]
    result = db.execute(
        text(
            """
            INSERT INTO promotion_impressions (
                campaign_id,
                user_id,
                track_id,
                rank_position,
                relevance_score,
                campaign_score,
                diversity_bonus,
                fatigue_penalty,
                final_score
            )
            VALUES (
                :campaign_id,
                :user_id,
                :track_id,
                :rank_position,
                :relevance_score,
                :campaign_score,
                :diversity_bonus,
                :fatigue_penalty,
                :final_score
            )
            """
        ),
        rows,
    )
    return int(result.rowcount or 0)
