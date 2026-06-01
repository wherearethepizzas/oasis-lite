from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    PromotedRecommendationsResponse,
    RecommendationEvaluationMetricsResponse,
    RecommendationRelevanceMode,
)
from app.services.recommendation_service import (
    get_active_campaigns_audio_features,
    get_relevant_items,
    get_user_taste_by_id,
    insert_promotion_impressions,
)
from app.services.scoring_service import (
    calculate_ranking_metrics,
    generate_promoted_tracks,
    get_user_play_history_by_id,
    mark_relevance,
)


router = APIRouter()


@router.get("/promoted/{user_id}", response_model=PromotedRecommendationsResponse)
def get_promoted_recommendations(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    user_taste_profile = get_user_taste_by_id(db, user_id)
    if user_taste_profile is None:
        raise HTTPException(status_code=404, detail="User taste profile not found")

    active_campaigns_audio_features = get_active_campaigns_audio_features(db, user_id)
    if not active_campaigns_audio_features:
        return {
            "user_id": user_id,
            "limit": limit,
            "count": 0,
            "recommendations": [],
        }

    user_play_context = get_user_play_history_by_id(user_id, db)
    recommendations = generate_promoted_tracks(
        user_taste_profile=user_taste_profile,
        active_campaigns_audio_features=active_campaigns_audio_features,
        user_play_context=user_play_context,
        limit=limit,
    )

    try:
        insert_promotion_impressions(db, user_id, recommendations)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to log promotion impressions") from exc

    return {
        "user_id": user_id,
        "limit": limit,
        "count": len(recommendations),
        "recommendations": recommendations,
    }

@router.get("/promoted/{user_id}/metrics", response_model=RecommendationEvaluationMetricsResponse)
def get_promoted_recommendations_eval(
    user_id: str,
    k: int = Query(default=10, ge=1, le=50),
    relevance_mode: Annotated[RecommendationRelevanceMode, Query()] = "track",
    threshold: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
):
    user_taste_profile = get_user_taste_by_id(db, user_id)
    if user_taste_profile is None:
        raise HTTPException(status_code=404, detail="User taste profile not found")

    active_campaigns_audio_features = get_active_campaigns_audio_features(db, user_id)
    user_play_context = get_user_play_history_by_id(user_id, db)
    recommendations = generate_promoted_tracks(
        user_taste_profile=user_taste_profile,
        active_campaigns_audio_features=active_campaigns_audio_features,
        user_play_context=user_play_context,
        limit=k,
    )
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
