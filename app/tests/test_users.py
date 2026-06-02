from datetime import datetime
from decimal import Decimal


def test_get_user(client, monkeypatch):
    from app.routers import users

    monkeypatch.setattr(
        users,
        "execute_query",
        lambda db, query, params=None: [
            {
                "user_id": "user-1",
                "created_at": datetime(2026, 6, 1, 12, 0, 0),
                "updated_at": datetime(2026, 6, 1, 12, 30, 0),
            }
        ],
    )

    response = client.get("/users/user-1")

    assert response.status_code == 200
    assert response.json()["user_id"] == "user-1"


def test_get_recommendation_ready_users(client, monkeypatch):
    from app.routers import users

    captured = {}

    def fake_execute_query(db, query, params=None):
        captured["params"] = params
        return [{"user_id": "user-1"}, {"user_id": "user-2"}]

    monkeypatch.setattr(users, "execute_query", fake_execute_query)

    response = client.get("/users/recommendation-ready?limit=2")

    assert response.status_code == 200
    assert response.json() == [{"user_id": "user-1"}, {"user_id": "user-2"}]
    assert captured["params"] == {"limit": 2}


def test_get_recommendation_ready_users_empty(client, monkeypatch):
    from app.routers import users

    monkeypatch.setattr(users, "execute_query", lambda db, query, params=None: [])

    response = client.get("/users/recommendation-ready")

    assert response.status_code == 200
    assert response.json() == []


def test_get_recommendation_ready_users_rejects_invalid_limit(client):
    assert client.get("/users/recommendation-ready?limit=0").status_code == 422


def test_get_user_not_found(client, monkeypatch):
    from app.routers import users

    monkeypatch.setattr(users, "execute_query", lambda db, query, params=None: [])

    response = client.get("/users/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_get_user_promotion_history(client, monkeypatch):
    from app.routers import users

    monkeypatch.setattr(
        users,
        "execute_query",
        lambda db, query, params=None: [
            {
                "impression_id": 1,
                "campaign_id": 101,
                "user_id": "user-1",
                "track_id": "track-1",
                "rank_position": 1,
                "relevance_score": Decimal("0.800000"),
                "campaign_score": Decimal("0.900000"),
                "diversity_bonus": Decimal("1.000000"),
                "fatigue_penalty": Decimal("0.000000"),
                "final_score": Decimal("0.805000"),
                "served_at": datetime(2026, 6, 1, 13, 0, 0),
            }
        ],
    )

    response = client.get("/users/user-1/promotion-history")

    assert response.status_code == 200
    assert response.json()[0]["impression_id"] == 1


def test_get_user_promotion_history_empty(client, monkeypatch):
    from app.routers import users

    monkeypatch.setattr(users, "execute_query", lambda db, query, params=None: [])

    response = client.get("/users/user-1/promotion-history")

    assert response.status_code == 200
    assert response.json() == {"message": "User user-1 does not have a promotion history."}
