from datetime import datetime

from fastapi import status


def test_valid_log_event(client, dummy_db, monkeypatch):
    from app.routers import events

    monkeypatch.setattr(events, "get_impression_by_id", lambda db, impression_id: {"impression_id": impression_id})
    monkeypatch.setattr(
        events,
        "insert_promotion_event",
        lambda db, impression_id, event_type: {
            "event_id": 7,
            "impression_id": impression_id,
            "event_type": event_type,
            "event_timestamp": datetime(2026, 6, 1, 12, 0, 0),
        },
    )

    response = client.post(
        "/promotion-events",
        json={
            "impression_id": 1,
            "event_type": "click",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["event_type"] == "click"
    assert dummy_db.committed is True


def test_invalid_log_event(client):
    response = client.post(
        "/promotion-events",
        json={
            "impression_id": 1,
            "event_type": "streams", # should be stream
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_non_existent_resource(client, monkeypatch):
    from app.routers import events

    monkeypatch.setattr(events, "get_impression_by_id", lambda db, impression_id: None)

    response = client.post(
        "/promotion-events",
        json={
            "impression_id": 2423,
            "event_type": "save",
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
