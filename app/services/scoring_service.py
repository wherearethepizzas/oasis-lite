from decimal import Decimal
from math import log2
from typing import Any

from sqlalchemy.orm import Session

from app.services.utils import execute_query


AUDIO_FEATURES = (
    "danceability",
    "energy",
    "acousticness",
    "instrumentalness",
    "valence",
)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _normalize_weighted_rows(rows: list[dict[str, Any]], id_key: str, name_key: str) -> list[dict[str, Any]]:
    total = sum(_to_float(row.get("weighted_play_count")) or 0.0 for row in rows)
    normalized: list[dict[str, Any]] = []
    for row in rows:
        weighted_count = _to_float(row.get("weighted_play_count")) or 0.0
        normalized.append(
            {
                id_key: row.get(id_key),
                name_key: row.get(name_key),
                "weighted_play_count": weighted_count,
                "weight": weighted_count / total if total else 0.0,
            }
        )
    return normalized


def get_user_play_history_by_id(user_id: str, db: Session) -> dict[str, Any]:
    genre_rows = execute_query(
        db,
        query="""
            SELECT
                t.genre,
                SUM(utp.play_count) AS weighted_play_count
            FROM user_track_plays utp
            JOIN tracks t ON t.track_id = utp.track_id
            WHERE utp.user_id = :user_id
              AND t.genre IS NOT NULL
              AND utp.play_count > 0
            GROUP BY t.genre
            ORDER BY weighted_play_count DESC, t.genre ASC
        """,
        params={"user_id": user_id},
    )
    artist_rows = execute_query(
        db,
        query="""
            SELECT
                a.artist_id,
                a.artist_name,
                SUM(utp.play_count) AS weighted_play_count
            FROM user_track_plays utp
            JOIN track_artists ta ON ta.track_id = utp.track_id
            JOIN artists a ON a.artist_id = ta.artist_id
            WHERE utp.user_id = :user_id
              AND utp.play_count > 0
            GROUP BY a.artist_id, a.artist_name
            ORDER BY weighted_play_count DESC, a.artist_name ASC
        """,
        params={"user_id": user_id},
    )

    top_genres = _normalize_weighted_rows([dict(row) for row in genre_rows], "genre", "genre")[:5]
    top_artists = _normalize_weighted_rows([dict(row) for row in artist_rows], "artist_id", "artist_name")[:5]
    return {
        "top_genres": top_genres,
        "top_artists": top_artists,
        "top_genre_names": {row["genre"] for row in top_genres if row.get("genre")},
        "top_artist_ids": {row["artist_id"] for row in top_artists if row.get("artist_id") is not None},
    }


def _calculate_relevance(user_taste_profile: dict[str, Any], candidate: dict[str, Any]) -> float:
    scores: list[float] = []
    for feature in AUDIO_FEATURES:
        user_value = _to_float(user_taste_profile.get(feature))
        candidate_value = _to_float(candidate.get(feature))
        if user_value is None or candidate_value is None:
            continue
        scores.append(1.0 - abs(user_value - candidate_value))

    user_tempo = _to_float(user_taste_profile.get("tempo"))
    candidate_tempo = _to_float(candidate.get("tempo"))
    if user_tempo is not None and candidate_tempo is not None:
        scores.append(1.0 - min(abs(user_tempo - candidate_tempo) / 100.0, 1.0))

    if not scores:
        return 0.0
    return _clamp(sum(scores) / len(scores))


def _calculate_diversity_and_fatigue(
    candidate: dict[str, Any],
    user_play_context: dict[str, Any] | None,
) -> tuple[float, float]:
    context = user_play_context or {}
    top_genres = context.get("top_genre_names", set())
    top_artists = context.get("top_artist_ids", set())

    genre = candidate.get("genre")
    artist_id = candidate.get("artist_id")
    genre_is_known = genre is not None
    artist_is_known = artist_id is not None
    genre_in_top = genre_is_known and genre in top_genres
    artist_in_top = artist_is_known and artist_id in top_artists

    if genre_in_top and artist_in_top:
        return 0.0, 1.0
    if genre_in_top or artist_in_top:
        return 0.5, 0.5
    return 1.0, 0.0


def generate_promoted_tracks(
    user_taste_profile: dict[str, Any],
    active_campaigns_audio_features: list[dict[str, Any]] | None,
    user_play_context: dict[str, Any] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    candidates = active_campaigns_audio_features or []
    scored_candidates: list[dict[str, Any]] = []

    for candidate in candidates:
        candidate_dict = dict(candidate)
        relevance_score = _calculate_relevance(user_taste_profile, candidate_dict)
        campaign_score = _clamp(_to_float(candidate_dict.get("bid_weight")) or 0.0)
        diversity_bonus, fatigue_penalty = _calculate_diversity_and_fatigue(candidate_dict, user_play_context)
        final_score = (
            (0.60 * relevance_score)
            + (0.25 * campaign_score)
            + (0.10 * diversity_bonus)
            - (0.05 * fatigue_penalty)
        )

        scored_candidates.append(
            {
                "track_id": candidate_dict.get("track_id"),
                "track_name": candidate_dict.get("track_name"),
                "artist_id": candidate_dict.get("artist_id"),
                "artist_name": candidate_dict.get("artist_name"),
                "genre": candidate_dict.get("genre"),
                "campaign_id": candidate_dict.get("campaign_id"),
                "objective": candidate_dict.get("objective"),
                "relevance_score": round(_clamp(relevance_score), 6),
                "campaign_score": round(campaign_score, 6),
                "diversity_bonus": round(diversity_bonus, 6),
                "fatigue_penalty": round(fatigue_penalty, 6),
                "final_score": round(final_score, 6),
            }
        )

    scored_candidates.sort(
        key=lambda row: (
            -row["final_score"],
            -row["campaign_score"],
            str(row["track_id"] or ""),
        ),
    )

    ranked = scored_candidates[:limit]
    for index, row in enumerate(ranked, start=1):
        row["rank_position"] = index
    return ranked


def mark_relevance(
    recommendations: list[dict[str, Any]],
    relevant_items: set,
    relevance_mode: str,
) -> list[int]:
    flags: list[int] = []
    for recommendation in recommendations:
        if relevance_mode == "track":
            item = recommendation.get("track_id")
        elif relevance_mode == "genre":
            item = recommendation.get("genre")
        elif relevance_mode == "artist":
            item = recommendation.get("artist_id")
        else:
            raise ValueError(f"Unsupported relevance_mode: {relevance_mode}")
        flags.append(1 if item in relevant_items else 0)
    return flags


def calculate_ranking_metrics(relevance_flags: list[int], total_relevant: int, k: int) -> dict[str, float | int]:
    flags_at_k = relevance_flags[:k]
    relevant_recommended_count = sum(flags_at_k)
    precision_at_k = relevant_recommended_count / k
    recall_at_k = relevant_recommended_count / total_relevant if total_relevant else 0.0

    dcg = sum(flag / log2(rank + 1) for rank, flag in enumerate(flags_at_k, start=1))
    ideal_relevant_count = min(total_relevant, k)
    idcg = sum(1 / log2(rank + 1) for rank in range(1, ideal_relevant_count + 1))
    ndcg_at_k = dcg / idcg if idcg else 0.0

    precision_sum = 0.0
    hit_count = 0
    for rank, flag in enumerate(flags_at_k, start=1):
        if flag:
            hit_count += 1
            precision_sum += hit_count / rank
    map_denominator = min(total_relevant, k)
    map_at_k = precision_sum / map_denominator if map_denominator else 0.0

    return {
        "relevant_recommended_count": relevant_recommended_count,
        "precision_at_k": round(precision_at_k, 3),
        "recall_at_k": round(recall_at_k, 3),
        "ndcg_at_k": round(ndcg_at_k, 3),
        "map_at_k": round(map_at_k, 3),
    }
