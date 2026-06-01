def test_get_track(client, monkeypatch):
    from app.routers import tracks

    monkeypatch.setattr(
        tracks,
        "execute_query",
        lambda db, query, params=None: [
            {
                "track_name": "Street Life",
                "genre": "Soul",
                "release_year": 1979,
                "artist_name": "Randy Crawford",
            }
        ],
    )

    response = client.get("/tracks/TRACK123")

    assert response.status_code == 200
    assert response.json() == {
        "track_name": "Street Life",
        "genre": "Soul",
        "release_year": 1979,
        "artist_name": "Randy Crawford",
    }


def test_get_track_not_found(client, monkeypatch):
    from app.routers import tracks

    monkeypatch.setattr(tracks, "execute_query", lambda db, query, params=None: [])

    response = client.get("/tracks/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Track not found"
