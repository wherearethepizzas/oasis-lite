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
