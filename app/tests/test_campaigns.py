from decimal import Decimal


def test_get_active_campaigns(client, monkeypatch):
    from app.routers import campaigns

    monkeypatch.setattr(
        campaigns,
        "execute_query",
        lambda db, query, params=None: [
            {
                "campaign_id": 101,
                "track_id": "track-1",
                "artist_id": 202,
                "objective": "streams",
                "bid_weight": Decimal("0.7500"),
                "daily_budget": Decimal("100.00"),
                "remaining_budget": Decimal("50.00"),
                "target_genre": "Rock",
                "max_impressions_per_user_per_day": 3,
            }
        ],
    )

    response = client.get("/campaigns/active")

    assert response.status_code == 200
    assert response.json()[0]["campaign_id"] == 101


def test_get_campaign_metrics(client, monkeypatch):
    from app.routers import campaigns

    monkeypatch.setattr(campaigns, "get_campaign_by_id", lambda campaign_id, db: {"campaign_id": campaign_id})
    monkeypatch.setattr(
        campaigns,
        "get_campaign_metrics_by_id",
        lambda campaign_id, db: {
            "campaign_id": campaign_id,
            "impressions": 1200,
            "clicks": 180,
            "streams": 95,
            "saves": 37,
            "skips": 410,
            "click_through_rate": 0.15,
            "stream_rate": 0.079,
            "save_rate": 0.031,
            "skip_rate": 0.342,
        },
    )

    response = client.get("/campaigns/101/metrics")

    assert response.status_code == 200
    assert response.json()["stream_rate"] == 0.079


def test_get_campaign_metrics_not_found(client, monkeypatch):
    from app.routers import campaigns

    monkeypatch.setattr(campaigns, "get_campaign_by_id", lambda campaign_id, db: None)

    response = client.get("/campaigns/999/metrics")

    assert response.status_code == 404
    assert response.json()["detail"] == "Campaign not found"


def test_campaign_leaderboard_sorts_by_metric(client, monkeypatch):
    from app.routers import campaigns

    monkeypatch.setattr(
        campaigns,
        "get_all_campaign_metrics",
        lambda db: [
            {
                "campaign_id": 1,
                "impressions": 10,
                "clicks": 1,
                "streams": 2,
                "saves": 0,
                "skips": 1,
                "click_through_rate": 0.1,
                "stream_rate": 0.2,
                "save_rate": 0.0,
                "skip_rate": 0.1,
            },
            {
                "campaign_id": 2,
                "impressions": 10,
                "clicks": 3,
                "streams": 5,
                "saves": 1,
                "skips": 0,
                "click_through_rate": 0.3,
                "stream_rate": 0.5,
                "save_rate": 0.1,
                "skip_rate": 0.0,
            },
        ],
    )

    response = client.get("/campaigns/leaderboard?metric=stream_rate")

    assert response.status_code == 200
    assert [campaign["campaign_id"] for campaign in response.json()] == [2, 1]


def test_campaign_leaderboard_rejects_invalid_metric(client):
    response = client.get("/campaigns/leaderboard?metric=made_up")

    assert response.status_code == 422
