from fastapi.testclient import TestClient

from alfred_flights.api import create_app


def test_trip_api_enforces_header_roles_and_version_conflicts() -> None:
    with TestClient(create_app()) as client:
        owner = client.post("/users", json={"display_name": "Анна"}).json()
        stranger = client.post("/users", json={"display_name": "Чужой"}).json()
        headers = {"X-User-ID": owner["id"]}
        trip = client.post(
            "/trips",
            headers=headers,
            json={
                "name": "Европа",
                "destinations": ["ROM", "PAR"],
                "start_date": "2026-12-10",
                "end_date": "2026-12-20",
                "timezone": "Europe/Rome",
            },
        ).json()

        denied = client.get(f"/trips/{trip['id']}", headers={"X-User-ID": stranger["id"]})
        first = client.post(
            f"/trips/{trip['id']}/itinerary",
            headers=headers,
            json={
                "expected_version": trip["version"],
                "item_type": "hotel",
                "title": "Hotel Roma",
                "start_at": "2026-12-10T14:00:00Z",
                "end_at": "2026-12-12T09:00:00Z",
                "timezone": "Europe/Rome",
            },
        )
        stale = client.post(
            f"/trips/{trip['id']}/itinerary",
            headers=headers,
            json={
                "expected_version": trip["version"],
                "item_type": "activity",
                "title": "Колизей",
                "start_at": "2026-12-11T10:00:00Z",
                "end_at": "2026-12-11T12:00:00Z",
                "timezone": "Europe/Rome",
            },
        )

    assert denied.status_code == 403
    assert first.status_code == 201
    assert stale.status_code == 409
    assert stale.json()["detail"]["current_version"] == 2
