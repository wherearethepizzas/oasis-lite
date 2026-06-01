def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_db_health(client, dummy_db):
    class Result:
        def scalar_one(self):
            return 1

    dummy_db.execute = lambda statement: Result()

    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
