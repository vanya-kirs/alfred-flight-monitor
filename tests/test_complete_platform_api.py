from fastapi.testclient import TestClient

from alfred_flights.api import create_app


def test_end_to_end_trip_booking_sync_and_disruption_api() -> None:
    with TestClient(create_app()) as client:
        user = client.post("/users", json={"display_name": "Bruce"}).json()
        headers = {"X-User-ID": user["id"]}
        trip = client.post("/trips", headers=headers, json={
            "name": "Europe", "destinations": ["ROM", "PAR"],
            "start_date": "2026-12-10", "end_date": "2026-12-20", "timezone": "Europe/Rome",
        }).json()
        flight = client.post("/flights", json={
            "flight_number": "SU100", "departure_at": "2026-12-10T07:00:00Z",
            "origin": "MOW", "destination": "IST",
        }).json()
        item = client.post(f"/trips/{trip['id']}/itinerary", headers=headers, json={
            "expected_version": 1, "item_type": "flight", "title": "SU100",
            "start_at": "2026-12-10T07:00:00Z", "end_at": "2026-12-10T11:00:00Z",
            "timezone": "Europe/Moscow", "metadata": {"flight_id": flight["id"], "checked_baggage_required": True},
        })
        assert item.status_code == 201
        client.post(f"/demo/flights/{flight['id']}/observation", json={
            "state": "cancelled", "observed_at": "2026-12-09T08:00:00Z", "delay_minutes": 0,
        })
        assert client.post(f"/flights/{flight['id']}/check").status_code == 200
        incidents = client.get("/incidents", headers=headers, params={"trip_id": trip["id"]}).json()
        assert len(incidents) == 1 and len(incidents[0]["alternatives"]) >= 1
        assert len(client.get("/notifications/inbox", headers=headers).json()) == 1

        offers = client.post("/inventory/search", headers=headers, json={
            "kind": "hotel", "destination": "Rome", "start_at": "2026-12-10T14:00:00Z",
            "end_at": "2026-12-12T09:00:00Z", "timezone": "Europe/Rome",
        }).json()
        booking = client.post("/bookings", headers=headers, json={
            "trip_id": trip["id"], "offer_id": offers[0]["id"], "payment_token": "tok_demo",
        }).json()
        confirmed = client.post(f"/bookings/{booking['id']}/confirm", headers=headers, json={"expected_version": 2})
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "confirmed"

        reference = client.post("/privacy/passport-references", headers=headers, json={
            "trip_id": trip["id"], "vault_token": "vault_provider-token", "abandoned": True,
        })
        assert reference.status_code == 201
        sync = client.post("/sync", headers=headers, json={"trip_id": trip["id"], "after_version": 0, "operations": []})
        assert sync.status_code == 200
        assert sync.json()["current_version"] == 3
