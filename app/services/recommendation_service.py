from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.utils import execute_query
from app.services.scoring_service import (
    calculate_cost_per_impression,
    calculate_ranking_metrics,
    mark_relevance,
)
from app.schemas import RecommendationRelevanceMode


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


def insert_promotion_impressions(db: Session, user_id: str, recommendations: list[dict[str, Any]]) -> list[int]:
    if not recommendations:
        return []

    statement = text(
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
    )
    impression_ids = []
    for recommendation in recommendations:
        result = db.execute(
            statement,
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
            },
        )
        impression_id = getattr(result, "lastrowid", None)
        if impression_id is None:
            raise RuntimeError("Promotion impression insert did not return an inserted row ID.")
        impression_ids.append(int(impression_id))

    update_promotion_budget(db, recommendations)

    return impression_ids


def update_promotion_budget(db: Session, recommendations: list[dict[str, Any]]):
    costs_by_campaign: dict[Any, Decimal] = defaultdict(Decimal)
    for recommendation in recommendations:
        costs_by_campaign[recommendation["campaign_id"]] += calculate_cost_per_impression(recommendation)

    statement = text(
        """
        UPDATE promotion_campaigns
        SET remaining_budget = remaining_budget - :total_cost
        WHERE campaign_id = :campaign_id
          AND remaining_budget >= :total_cost
        """
    )
    for campaign_id, total_cost in costs_by_campaign.items():
        result = db.execute(
            statement,
            {
                "campaign_id": campaign_id,
                "total_cost": total_cost,
            },
        )
        if result.rowcount != 1:
            raise RuntimeError(f"Insufficient promotion budget for campaign {campaign_id}.")


def attach_impression_ids(recommendations: list[dict[str, Any]], impression_ids: list[int]) -> list[dict[str, Any]]:
    if len(recommendations) != len(impression_ids):
        raise RuntimeError("Recommendation count does not match inserted promotion impression count.")
    for recommendation, impression_id in zip(recommendations, impression_ids, strict=True):
        recommendation["impression_id"] = impression_id
    return recommendations


def build_recommendation_metrics(
    *,
    db: Session,
    user_id: str,
    recommendations: list[dict],
    k: int,
    relevance_mode: RecommendationRelevanceMode,
    threshold: int,
):
    relevant_items = get_relevant_items(db, user_id, relevance_mode, threshold)
    relevance_flags = mark_relevance(recommendations, relevant_items, relevance_mode)
    metrics = calculate_ranking_metrics(relevance_flags, total_relevant=len(relevant_items), k=k)
    return {
        "user_id": user_id,
        "k": k,
        "relevance_mode": relevance_mode,
        "threshold": threshold,
        "recommended_count": len(recommendations),
        "relevant_items_count": len(relevant_items),
        **metrics,
    }


def reset_budget(db: Session):
    execute_query(
        db,
        """
        UPDATE promotion_campaigns
        SET
            remaining_budget = CASE
                WHEN remaining_budget < 0 THEN GREATEST(0, daily_budget + remaining_budget)
                ELSE daily_budget
            END,
            budget_date = CURRENT_DATE,
            updated_at = CURRENT_TIMESTAMP
        WHERE status = 'active'
        AND start_date <= CURRENT_DATE
        AND end_date >= CURRENT_DATE
        AND (budget_date IS NULL OR budget_date < CURRENT_DATE);
        """
    )
