from datetime import datetime


def test_prometheus_metrics_are_exported(client, monkeypatch):
    from app.routers import campaigns, events, recommendations
    from app.services import recommendation_service

    monkeypatch.setattr(recommendations, "get_user_taste_by_id", lambda db, user_id: {"user_id": user_id})
    monkeypatch.setattr(recommendations, "get_active_campaigns_audio_features", lambda db, user_id: [{"track_id": "raw"}])
    monkeypatch.setattr(recommendations, "get_user_play_history_by_id", lambda user_id, db: {})
    monkeypatch.setattr(
        recommendations,
        "generate_promoted_tracks",
        lambda user_taste_profile, active_campaigns_audio_features, user_play_context, limit: [
            {
                "rank_position": 1,
                "track_id": "track-1",
                "track_name": "Track 1",
                "artist_id": 1,
                "artist_name": "Artist 1",
                "genre": "Rock",
                "campaign_id": 1,
                "objective": "streams",
                "relevance_score": 1.0,
                "campaign_score": 1.0,
                "diversity_bonus": 0.0,
                "fatigue_penalty": 0.0,
                "final_score": 1.0,
            }
        ],
    )
    monkeypatch.setattr(recommendation_service, "get_relevant_items", lambda db, user_id, relevance_mode, threshold: {"track-1"})
    monkeypatch.setattr(recommendations, "insert_promotion_impressions", lambda db, user_id, rows: len(rows))
    monkeypatch.setattr(events, "get_impression_by_id", lambda db, impression_id: {"impression_id": impression_id})
    monkeypatch.setattr(
        events,
        "insert_promotion_event",
        lambda db, impression_id, event_type: {
            "event_id": 1,
            "impression_id": impression_id,
            "event_type": event_type,
            "event_timestamp": datetime(2026, 6, 2, 12, 0, 0),
        },
    )
    monkeypatch.setattr(
        campaigns,
        "execute_query",
        lambda db, query, params=None: [
            {
                "campaign_id": 1,
                "track_id": "track-1",
                "artist_id": 1,
                "objective": "streams",
                "bid_weight": 1,
                "daily_budget": 10,
                "remaining_budget": 10,
                "target_genre": "Rock",
                "max_impressions_per_user_per_day": 3,
            }
        ],
    )

    assert client.get("/recommendations/promoted/user-1?limit=1").status_code == 200
    assert client.post("/promotion-events", json={"impression_id": 1, "event_type": "stream"}).status_code == 200
    assert client.get("/campaigns/active").status_code == 200

    body = client.get("/metrics").text
    for metric_name in [
        "recommendation_requests_total",
        "recommendation_latency_seconds",
        "promoted_tracks_served_total",
        "promotion_events_total",
        "active_campaigns_total",
    ]:
        assert metric_name in body
