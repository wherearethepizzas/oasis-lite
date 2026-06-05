from typing import Annotated
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.metrics import promoted_tracks_served, recommendation_latency_seconds, recommendation_requests
from app.schemas import (
    PromotedRecommendationsResponse,
    RecommendationRelevanceMode
)
from app.services.recommendation_service import (
    attach_impression_ids,
    get_active_campaigns_audio_features,
    get_user_taste_by_id,
    insert_promotion_impressions,
    build_recommendation_metrics,
    reset_budget,
)
from app.services.scoring_service import (
    generate_promoted_tracks,
    get_user_play_history_by_id,
)


router = APIRouter()


@router.get("/promoted/{user_id}", response_model=PromotedRecommendationsResponse)
def get_promoted_recommendations(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    relevance_mode: Annotated[RecommendationRelevanceMode, Query()] = "track",
    threshold: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
):
    recommendation_requests.inc()
    started_at = perf_counter()
    served_count = 0
    try:
        user_taste_profile = get_user_taste_by_id(db, user_id)
        if user_taste_profile is None:
            raise HTTPException(status_code=404, detail="User taste profile not found")

        reset_budget(db)
        active_campaigns_audio_features = get_active_campaigns_audio_features(db, user_id)
        if not active_campaigns_audio_features:
            metrics = build_recommendation_metrics(
                db=db,
                user_id=user_id,
                recommendations=[],
                k=limit,
                relevance_mode=relevance_mode,
                threshold=threshold,
            )
            return {
                "user_id": user_id,
                "limit": limit,
                "count": 0,
                "recommendations": [],
                "metrics": metrics,
            }

        user_play_context = get_user_play_history_by_id(user_id, db)
        recommendations = generate_promoted_tracks(
            user_taste_profile=user_taste_profile,
            active_campaigns_audio_features=active_campaigns_audio_features,
            user_play_context=user_play_context,
            limit=limit,
        )
        metrics = build_recommendation_metrics(
            db=db,
            user_id=user_id,
            recommendations=recommendations,
            k=limit,
            relevance_mode=relevance_mode,
            threshold=threshold,
        )

        try:
            impression_ids = insert_promotion_impressions(db, user_id, recommendations)
            recommendations = attach_impression_ids(recommendations, impression_ids)
            db.commit()
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to log promotion impressions") from exc

        served_count = len(recommendations)
        return {
            "user_id": user_id,
            "limit": limit,
            "count": served_count,
            "recommendations": recommendations,
            "metrics": metrics,
        }
    finally:
        promoted_tracks_served.inc(served_count)
        recommendation_latency_seconds.observe(perf_counter() - started_at)
