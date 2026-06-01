def test_get_promoted_recommendations(client, dummy_db, monkeypatch):
    from app.routers import recommendations

    monkeypatch.setattr(
        recommendations,
        "get_user_taste_by_id",
        lambda db, user_id: {
            "user_id": user_id,
            "danceability": 0.8,
            "energy": 0.7,
            "acousticness": 0.1,
            "instrumentalness": 0.0,
            "valence": 0.9,
            "tempo": 120,
        },
    )
    monkeypatch.setattr(
        recommendations,
        "get_active_campaigns_audio_features",
        lambda db, user_id: [
            {
                "track_id": "track-1",
                "track_name": "Promoted Track",
                "artist_id": 10,
                "artist_name": "Promoted Artist",
                "genre": "Pop",
                "campaign_id": 101,
                "objective": "streams",
                "bid_weight": 0.8,
                "danceability": 0.8,
                "energy": 0.7,
                "acousticness": 0.1,
                "instrumentalness": 0.0,
                "valence": 0.9,
                "tempo": 120,
            }
        ],
    )
    monkeypatch.setattr(
        recommendations,
        "get_user_play_history_by_id",
        lambda user_id, db: {"top_genre_names": {"Rock"}, "top_artist_ids": {1}},
    )
    monkeypatch.setattr(recommendations, "insert_promotion_impressions", lambda db, user_id, rows: len(rows))

    response = client.get("/recommendations/promoted/user-1?limit=1")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["recommendations"][0]["rank_position"] == 1
    assert dummy_db.committed is True


def test_get_promoted_recommendations_missing_taste_profile(client, monkeypatch):
    from app.routers import recommendations

    monkeypatch.setattr(recommendations, "get_user_taste_by_id", lambda db, user_id: None)

    response = client.get("/recommendations/promoted/user-1")

    assert response.status_code == 404
    assert response.json()["detail"] == "User taste profile not found"


def test_get_promoted_recommendations_no_campaigns(client, monkeypatch):
    from app.routers import recommendations

    monkeypatch.setattr(recommendations, "get_user_taste_by_id", lambda db, user_id: {"user_id": user_id})
    monkeypatch.setattr(recommendations, "get_active_campaigns_audio_features", lambda db, user_id: [])

    response = client.get("/recommendations/promoted/user-1?limit=5")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "user-1",
        "limit": 5,
        "count": 0,
        "recommendations": [],
    }


def test_get_promoted_recommendations_rolls_back_when_logging_fails(client, dummy_db, monkeypatch):
    from app.routers import recommendations

    monkeypatch.setattr(recommendations, "get_user_taste_by_id", lambda db, user_id: {"user_id": user_id})
    monkeypatch.setattr(
        recommendations,
        "get_active_campaigns_audio_features",
        lambda db, user_id: [
            {
                "track_id": "track-1",
                "track_name": "Promoted Track",
                "artist_id": 10,
                "artist_name": "Promoted Artist",
                "genre": "Pop",
                "campaign_id": 101,
                "objective": "streams",
                "bid_weight": 0.8,
            }
        ],
    )
    monkeypatch.setattr(recommendations, "get_user_play_history_by_id", lambda user_id, db: {})

    def fail_insert(db, user_id, rows):
        raise RuntimeError("insert failed")

    monkeypatch.setattr(recommendations, "insert_promotion_impressions", fail_insert)

    response = client.get("/recommendations/promoted/user-1")

    assert response.status_code == 500
    assert dummy_db.rolled_back is True


def _patch_metrics_dependencies(monkeypatch, recommendations, ranked_rows, relevant_items):
    monkeypatch.setattr(recommendations, "get_user_taste_by_id", lambda db, user_id: {"user_id": user_id})
    monkeypatch.setattr(recommendations, "get_active_campaigns_audio_features", lambda db, user_id: [{"track_id": "raw"}])
    monkeypatch.setattr(recommendations, "get_user_play_history_by_id", lambda user_id, db: {})
    monkeypatch.setattr(
        recommendations,
        "generate_promoted_tracks",
        lambda user_taste_profile, active_campaigns_audio_features, user_play_context, limit: ranked_rows[:limit],
    )
    monkeypatch.setattr(
        recommendations,
        "get_relevant_items",
        lambda db, user_id, relevance_mode, threshold: relevant_items,
    )


def test_promoted_recommendation_metrics_track_mode(client, monkeypatch):
    from app.routers import recommendations

    ranked_rows = [
        {"track_id": "track-1", "genre": "Rock", "artist_id": 1},
        {"track_id": "track-2", "genre": "Pop", "artist_id": 2},
        {"track_id": "track-3", "genre": "Jazz", "artist_id": 3},
    ]
    _patch_metrics_dependencies(monkeypatch, recommendations, ranked_rows, {"track-1", "track-3"})

    def fail_if_called(*args, **kwargs):
        raise AssertionError("metrics endpoint should not insert promotion impressions")

    monkeypatch.setattr(recommendations, "insert_promotion_impressions", fail_if_called)

    response = client.get("/recommendations/promoted/user-1/metrics?k=3&relevance_mode=track&threshold=1")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "user-1",
        "k": 3,
        "relevance_mode": "track",
        "threshold": 1,
        "recommended_count": 3,
        "relevant_items_count": 2,
        "relevant_recommended_count": 2,
        "precision_at_k": 0.667,
        "recall_at_k": 1.0,
        "ndcg_at_k": 0.92,
        "map_at_k": 0.833,
    }


def test_promoted_recommendation_metrics_genre_mode(client, monkeypatch):
    from app.routers import recommendations

    ranked_rows = [
        {"track_id": "track-1", "genre": "Rock", "artist_id": 1},
        {"track_id": "track-2", "genre": "Pop", "artist_id": 2},
    ]
    _patch_metrics_dependencies(monkeypatch, recommendations, ranked_rows, {"Pop"})

    response = client.get("/recommendations/promoted/user-1/metrics?k=2&relevance_mode=genre&threshold=5")

    assert response.status_code == 200
    assert response.json()["relevance_mode"] == "genre"
    assert response.json()["threshold"] == 5
    assert response.json()["relevant_recommended_count"] == 1
    assert response.json()["precision_at_k"] == 0.5


def test_promoted_recommendation_metrics_artist_mode(client, monkeypatch):
    from app.routers import recommendations

    ranked_rows = [
        {"track_id": "track-1", "genre": "Rock", "artist_id": 1},
        {"track_id": "track-2", "genre": "Pop", "artist_id": 2},
    ]
    _patch_metrics_dependencies(monkeypatch, recommendations, ranked_rows, {1})

    response = client.get("/recommendations/promoted/user-1/metrics?k=2&relevance_mode=artist")

    assert response.status_code == 200
    assert response.json()["relevance_mode"] == "artist"
    assert response.json()["relevant_recommended_count"] == 1
    assert response.json()["map_at_k"] == 1.0


def test_promoted_recommendation_metrics_no_relevant_items(client, monkeypatch):
    from app.routers import recommendations

    ranked_rows = [{"track_id": "track-1", "genre": "Rock", "artist_id": 1}]
    _patch_metrics_dependencies(monkeypatch, recommendations, ranked_rows, set())

    response = client.get("/recommendations/promoted/user-1/metrics?k=2")

    assert response.status_code == 200
    assert response.json()["relevant_items_count"] == 0
    assert response.json()["relevant_recommended_count"] == 0
    assert response.json()["recall_at_k"] == 0.0
    assert response.json()["ndcg_at_k"] == 0.0
    assert response.json()["map_at_k"] == 0.0


def test_promoted_recommendation_metrics_missing_taste_profile(client, monkeypatch):
    from app.routers import recommendations

    monkeypatch.setattr(recommendations, "get_user_taste_by_id", lambda db, user_id: None)

    response = client.get("/recommendations/promoted/user-1/metrics")

    assert response.status_code == 404
    assert response.json()["detail"] == "User taste profile not found"


def test_promoted_recommendation_metrics_rejects_invalid_query_params(client):
    assert client.get("/recommendations/promoted/user-1/metrics?k=0").status_code == 422
    assert client.get("/recommendations/promoted/user-1/metrics?k=51").status_code == 422
    assert client.get("/recommendations/promoted/user-1/metrics?threshold=0").status_code == 422
    assert client.get("/recommendations/promoted/user-1/metrics?relevance_mode=album").status_code == 422
