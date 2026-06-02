def test_dashboard_serves_static_shell(client):
    response = client.get("/dashboard/")

    assert response.status_code == 200
    assert "Oasis Lite Metrics" in response.text
    assert "/dashboard/styles.css" in response.text
    assert "/dashboard/app.js" in response.text


def test_dashboard_assets_are_available(client):
    css_response = client.get("/dashboard/styles.css")
    js_response = client.get("/dashboard/app.js")

    assert css_response.status_code == 200
    assert js_response.status_code == 200
    assert "kpi-grid" in css_response.text
    assert "refreshDashboard" in js_response.text
