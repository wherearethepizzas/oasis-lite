from decimal import Decimal


def test_get_promoted_recommendations(client, dummy_db, monkeypatch):
    from app.routers import recommendations
    from app.services import recommendation_service

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
                "daily_budget": Decimal("10.00"),
                "remaining_budget": Decimal("10.00"),
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
    monkeypatch.setattr(recommendations, "reset_budget", lambda db: None)
    monkeypatch.setattr(recommendation_service, "get_relevant_items", lambda db, user_id, relevance_mode, threshold: {"track-1"})
    monkeypatch.setattr(recommendations, "insert_promotion_impressions", lambda db, user_id, rows: [501])

    response = client.get("/recommendations/promoted/user-1?limit=1&relevance_mode=track&threshold=1")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["recommendations"][0]["rank_position"] == 1
    assert response.json()["recommendations"][0]["impression_id"] == 501
    assert response.json()["metrics"]["precision_at_k"] == 1.0
    assert response.json()["metrics"]["recall_at_k"] == 1.0
    assert dummy_db.committed is True


def test_get_promoted_recommendations_missing_taste_profile(client, monkeypatch):
    from app.routers import recommendations

    monkeypatch.setattr(recommendations, "get_user_taste_by_id", lambda db, user_id: None)

    response = client.get("/recommendations/promoted/user-1")

    assert response.status_code == 404
    assert response.json()["detail"] == "User taste profile not found"


def test_get_promoted_recommendations_no_campaigns(client, monkeypatch):
    from app.routers import recommendations
    from app.services import recommendation_service

    monkeypatch.setattr(recommendations, "get_user_taste_by_id", lambda db, user_id: {"user_id": user_id})
    monkeypatch.setattr(recommendations, "reset_budget", lambda db: None)
    monkeypatch.setattr(recommendations, "get_active_campaigns_audio_features", lambda db, user_id: [])
    monkeypatch.setattr(recommendation_service, "get_relevant_items", lambda db, user_id, relevance_mode, threshold: set())

    response = client.get("/recommendations/promoted/user-1?limit=5")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "user-1",
        "limit": 5,
        "count": 0,
        "recommendations": [],
        "metrics": {
            "user_id": "user-1",
            "k": 5,
            "relevance_mode": "track",
            "threshold": 1,
            "recommended_count": 0,
            "relevant_items_count": 0,
            "relevant_recommended_count": 0,
            "precision_at_k": 0.0,
            "recall_at_k": 0.0,
            "ndcg_at_k": 0.0,
            "map_at_k": 0.0,
        },
    }


def test_get_promoted_recommendations_rolls_back_when_logging_fails(client, dummy_db, monkeypatch):
    from app.routers import recommendations
    from app.services import recommendation_service

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
                "daily_budget": Decimal("10.00"),
                "remaining_budget": Decimal("10.00"),
            }
        ],
    )
    monkeypatch.setattr(recommendations, "get_user_play_history_by_id", lambda user_id, db: {})
    monkeypatch.setattr(recommendations, "reset_budget", lambda db: None)
    monkeypatch.setattr(recommendation_service, "get_relevant_items", lambda db, user_id, relevance_mode, threshold: set())

    def fail_insert(db, user_id, rows):
        raise RuntimeError("insert failed")

    monkeypatch.setattr(recommendations, "insert_promotion_impressions", fail_insert)

    response = client.get("/recommendations/promoted/user-1")

    assert response.status_code == 500
    assert dummy_db.rolled_back is True


def _patch_metrics_dependencies(monkeypatch, recommendations, ranked_rows, relevant_items):
    from app.services import recommendation_service

    monkeypatch.setattr(recommendations, "get_user_taste_by_id", lambda db, user_id: {"user_id": user_id})
    monkeypatch.setattr(recommendations, "reset_budget", lambda db: None)
    monkeypatch.setattr(recommendations, "get_active_campaigns_audio_features", lambda db, user_id: [{"track_id": "raw"}])
    monkeypatch.setattr(recommendations, "get_user_play_history_by_id", lambda user_id, db: {})
    monkeypatch.setattr(
        recommendations,
        "generate_promoted_tracks",
        lambda user_taste_profile, active_campaigns_audio_features, user_play_context, limit: ranked_rows[:limit],
    )
    monkeypatch.setattr(recommendation_service, "get_relevant_items", lambda db, user_id, relevance_mode, threshold: relevant_items)
    monkeypatch.setattr(
        recommendations,
        "insert_promotion_impressions",
        lambda db, user_id, rows: [1000 + index for index, _ in enumerate(rows)],
    )


def _ranked_recommendation(track_id: str, genre: str, artist_id: int, rank_position: int = 1):
    return {
        "rank_position": rank_position,
        "impression_id": 900 + rank_position,
        "track_id": track_id,
        "track_name": f"Track {track_id}",
        "artist_id": artist_id,
        "artist_name": f"Artist {artist_id}",
        "genre": genre,
        "campaign_id": 100 + rank_position,
        "objective": "streams",
        "relevance_score": 0.9,
        "campaign_score": 0.8,
        "diversity_bonus": 0.5,
        "fatigue_penalty": 0.0,
        "final_score": 0.86,
    }


def test_promoted_recommendations_include_track_metrics(client, monkeypatch):
    from app.routers import recommendations

    ranked_rows = [
        _ranked_recommendation("track-1", "Rock", 1, 1),
        _ranked_recommendation("track-2", "Pop", 2, 2),
        _ranked_recommendation("track-3", "Jazz", 3, 3),
    ]
    _patch_metrics_dependencies(monkeypatch, recommendations, ranked_rows, {"track-1", "track-3"})

    response = client.get("/recommendations/promoted/user-1?limit=3&relevance_mode=track&threshold=1")

    assert response.status_code == 200
    assert response.json()["count"] == 3
    assert response.json()["metrics"] == {
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


def test_promoted_recommendations_include_genre_metrics(client, monkeypatch):
    from app.routers import recommendations

    ranked_rows = [
        _ranked_recommendation("track-1", "Rock", 1, 1),
        _ranked_recommendation("track-2", "Pop", 2, 2),
    ]
    _patch_metrics_dependencies(monkeypatch, recommendations, ranked_rows, {"Pop"})

    response = client.get("/recommendations/promoted/user-1?limit=2&relevance_mode=genre&threshold=5")

    assert response.status_code == 200
    assert response.json()["metrics"]["relevance_mode"] == "genre"
    assert response.json()["metrics"]["threshold"] == 5
    assert response.json()["metrics"]["relevant_recommended_count"] == 1
    assert response.json()["metrics"]["precision_at_k"] == 0.5


def test_promoted_recommendations_genre_metrics_do_not_double_count_duplicate_genres(client, monkeypatch):
    from app.routers import recommendations

    ranked_rows = [
        _ranked_recommendation("track-1", "Rock", 1, 1),
        _ranked_recommendation("track-2", "Rock", 2, 2),
        _ranked_recommendation("track-3", "Rock", 3, 3),
        _ranked_recommendation("track-4", "Pop", 4, 4),
        _ranked_recommendation("track-5", "Pop", 5, 5),
    ]
    _patch_metrics_dependencies(monkeypatch, recommendations, ranked_rows, {"Rock", "Pop"})

    response = client.get("/recommendations/promoted/user-1?limit=5&relevance_mode=genre&threshold=1")

    assert response.status_code == 200
    assert response.json()["metrics"] == {
        "user_id": "user-1",
        "k": 5,
        "relevance_mode": "genre",
        "threshold": 1,
        "recommended_count": 5,
        "relevant_items_count": 2,
        "relevant_recommended_count": 2,
        "precision_at_k": 0.4,
        "recall_at_k": 1.0,
        "ndcg_at_k": 0.877,
        "map_at_k": 0.75,
    }


def test_promoted_recommendations_include_artist_metrics(client, monkeypatch):
    from app.routers import recommendations

    ranked_rows = [
        _ranked_recommendation("track-1", "Rock", 1, 1),
        _ranked_recommendation("track-2", "Pop", 2, 2),
    ]
    _patch_metrics_dependencies(monkeypatch, recommendations, ranked_rows, {1})

    response = client.get("/recommendations/promoted/user-1?limit=2&relevance_mode=artist")

    assert response.status_code == 200
    assert response.json()["metrics"]["relevance_mode"] == "artist"
    assert response.json()["metrics"]["relevant_recommended_count"] == 1
    assert response.json()["metrics"]["map_at_k"] == 1.0


def test_promoted_recommendations_metrics_no_relevant_items(client, monkeypatch):
    from app.routers import recommendations

    ranked_rows = [_ranked_recommendation("track-1", "Rock", 1, 1)]
    _patch_metrics_dependencies(monkeypatch, recommendations, ranked_rows, set())

    response = client.get("/recommendations/promoted/user-1?limit=2")

    assert response.status_code == 200
    assert response.json()["metrics"]["relevant_items_count"] == 0
    assert response.json()["metrics"]["relevant_recommended_count"] == 0
    assert response.json()["metrics"]["recall_at_k"] == 0.0
    assert response.json()["metrics"]["ndcg_at_k"] == 0.0
    assert response.json()["metrics"]["map_at_k"] == 0.0


def test_promoted_recommendations_metrics_missing_taste_profile(client, monkeypatch):
    from app.routers import recommendations

    monkeypatch.setattr(recommendations, "get_user_taste_by_id", lambda db, user_id: None)

    response = client.get("/recommendations/promoted/user-1")

    assert response.status_code == 404
    assert response.json()["detail"] == "User taste profile not found"


def test_promoted_recommendations_rejects_invalid_metric_query_params(client):
    assert client.get("/recommendations/promoted/user-1?limit=0").status_code == 422
    assert client.get("/recommendations/promoted/user-1?limit=51").status_code == 422
    assert client.get("/recommendations/promoted/user-1?threshold=0").status_code == 422
    assert client.get("/recommendations/promoted/user-1?relevance_mode=album").status_code == 422


def _campaign_candidate(
    *,
    track_id: str,
    campaign_id: int,
    bid_weight: Decimal,
    remaining_budget: Decimal,
    objective: str = "discovery",
):
    return {
        "track_id": track_id,
        "track_name": f"Track {track_id}",
        "artist_id": campaign_id,
        "artist_name": f"Artist {campaign_id}",
        "genre": "Pop",
        "campaign_id": campaign_id,
        "objective": objective,
        "bid_weight": bid_weight,
        "daily_budget": Decimal("10.00"),
        "remaining_budget": remaining_budget,
        "danceability": Decimal("0.80"),
        "energy": Decimal("0.70"),
        "acousticness": Decimal("0.10"),
        "instrumentalness": Decimal("0.00"),
        "valence": Decimal("0.90"),
        "tempo": Decimal("120.00"),
    }


def test_reset_budget_carries_negative_balance_into_next_daily_budget(monkeypatch):
    from app.services import recommendation_service

    captured = {}

    def capture_query(db, query, params=None):
        captured["query"] = query
        return []

    monkeypatch.setattr(recommendation_service, "execute_query", capture_query)

    assert recommendation_service.calculate_reset_remaining_budget(Decimal("10.00"), Decimal("-3.25")) == Decimal("6.75")
    assert recommendation_service.calculate_reset_remaining_budget(Decimal("10.00"), Decimal("-15.00")) == Decimal("0.00")
    assert recommendation_service.calculate_reset_remaining_budget(Decimal("10.00"), Decimal("2.50")) == Decimal("10.00")

    recommendation_service.reset_budget(db=object())

    assert "WHEN remaining_budget < 0 THEN GREATEST(0, daily_budget + remaining_budget)" in captured["query"]
    assert "ELSE daily_budget" in captured["query"]


def test_generate_promoted_tracks_backfills_unaffordable_campaigns():
    from app.services.scoring_service import generate_promoted_tracks

    recommendations = generate_promoted_tracks(
        user_taste_profile={
            "danceability": Decimal("0.80"),
            "energy": Decimal("0.70"),
            "acousticness": Decimal("0.10"),
            "instrumentalness": Decimal("0.00"),
            "valence": Decimal("0.90"),
            "tempo": Decimal("120.00"),
        },
        active_campaigns_audio_features=[
            _campaign_candidate(
                track_id="too-expensive",
                campaign_id=1,
                bid_weight=Decimal("1.00"),
                remaining_budget=Decimal("1.00"),
            ),
            _campaign_candidate(
                track_id="affordable-1",
                campaign_id=2,
                bid_weight=Decimal("0.80"),
                remaining_budget=Decimal("10.00"),
            ),
            _campaign_candidate(
                track_id="affordable-2",
                campaign_id=3,
                bid_weight=Decimal("0.60"),
                remaining_budget=Decimal("10.00"),
            ),
        ],
        user_play_context={},
        limit=2,
    )

    assert [row["track_id"] for row in recommendations] == ["affordable-1", "affordable-2"]
    assert [row["rank_position"] for row in recommendations] == [1, 2]


def test_generate_promoted_tracks_tracks_same_campaign_budget_across_list():
    from app.services.scoring_service import generate_promoted_tracks

    recommendations = generate_promoted_tracks(
        user_taste_profile={
            "danceability": Decimal("0.80"),
            "energy": Decimal("0.70"),
            "acousticness": Decimal("0.10"),
            "instrumentalness": Decimal("0.00"),
            "valence": Decimal("0.90"),
            "tempo": Decimal("120.00"),
        },
        active_campaigns_audio_features=[
            _campaign_candidate(
                track_id="same-campaign-1",
                campaign_id=10,
                bid_weight=Decimal("1.00"),
                remaining_budget=Decimal("3.00"),
                objective="streams",
            ),
            _campaign_candidate(
                track_id="same-campaign-2",
                campaign_id=10,
                bid_weight=Decimal("0.90"),
                remaining_budget=Decimal("3.00"),
                objective="streams",
            ),
            _campaign_candidate(
                track_id="other-campaign",
                campaign_id=20,
                bid_weight=Decimal("0.70"),
                remaining_budget=Decimal("10.00"),
                objective="streams",
            ),
        ],
        user_play_context={},
        limit=3,
    )

    assert [row["track_id"] for row in recommendations] == ["same-campaign-1", "other-campaign"]
    assert [row["rank_position"] for row in recommendations] == [1, 2]


class _BudgetUpdateResult:
    def __init__(self, rowcount):
        self.rowcount = rowcount


class _BudgetUpdateDb:
    def __init__(self, rowcounts):
        self.rowcounts = list(rowcounts)
        self.executions = []

    def execute(self, statement, params):
        self.executions.append({"statement": str(statement), "params": params})
        return _BudgetUpdateResult(self.rowcounts.pop(0))


def test_update_promotion_budget_aggregates_costs_by_campaign():
    from app.services.recommendation_service import update_promotion_budget

    db = _BudgetUpdateDb(rowcounts=[1])

    update_promotion_budget(
        db,
        [
            {"campaign_id": 101, "objective": "streams", "rank_position": 1},
            {"campaign_id": 101, "objective": "streams", "rank_position": 2},
        ],
    )

    assert len(db.executions) == 1
    assert db.executions[0]["params"] == {
        "campaign_id": 101,
        "total_cost": Decimal("3.24"),
    }
    assert "remaining_budget >= :total_cost" in db.executions[0]["statement"]


def test_update_promotion_budget_raises_when_atomic_budget_check_fails():
    from app.services.recommendation_service import update_promotion_budget

    db = _BudgetUpdateDb(rowcounts=[0])

    try:
        update_promotion_budget(
            db,
            [{"campaign_id": 101, "objective": "streams", "rank_position": 1}],
        )
    except RuntimeError as exc:
        assert "Insufficient promotion budget for campaign 101" in str(exc)
    else:
        raise AssertionError("Expected insufficient budget update to raise.")
