from fastapi.testclient import TestClient

from alfred_flights.api import create_app


def test_preliminary_plans_require_flight_and_hotel() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/preliminary-plans", json={"flight": None, "hotel": None})
    assert response.status_code == 422


def test_preliminary_plans_return_four_ordered_explainable_variants() -> None:
    payload = {
        "flight": {
            "id": "flight-1", "destination_city": "Стамбул",
            "arrival_at": "2026-12-10T23:30:00+03:00", "price_eur": 140,
            "baggage_kg": 20,
        },
        "hotel": {
            "id": "hotel-1", "title": "Central Hotel",
            "destination_city": "Стамбул",
            "check_in_at": "2026-12-10T14:00:00+03:00",
            "check_out_at": "2026-12-13T11:00:00+03:00", "total_price_eur": 210,
        },
    }
    with TestClient(create_app()) as client:
        response = client.post("/preliminary-plans", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert {item["strategy"] for item in body["variants"]} == {"optimal", "comfortable", "intensive", "budget"}
    assert body["recommended_strategy"] == "optimal"
    for variant in body["variants"]:
        starts = [item["start_at"] for item in variant["timeline"]]
        assert starts == sorted(starts)
        assert variant["advantages"] and variant["tradeoffs"]
        activity_titles = [item["title"] for item in variant["timeline"] if item["kind"] == "activity"]
        assert len(activity_titles) == len(set(activity_titles))
    optimal = next(item for item in body["variants"] if item["strategy"] == "optimal")
    assert optimal["timeline"][0]["kind"] == "transfer"
    assert optimal["timeline"][1]["kind"] == "check_in"
    assert optimal["timeline"][2]["kind"] == "rest"
    assert optimal["timeline"][-1]["kind"] == "check_out"
    assert len({item["start_at"][:10] for item in optimal["timeline"] if item["kind"] == "activity"}) >= 2


def test_preliminary_plans_reject_hotel_in_another_city() -> None:
    payload = {
        "flight": {"destination_city": "Стамбул", "arrival_at": "2026-12-10T10:00:00+03:00", "price_eur": 100},
        "hotel": {"title": "Wrong city", "destination_city": "Сочи", "check_in_at": "2026-12-10T14:00:00+03:00", "check_out_at": "2026-12-12T11:00:00+03:00", "total_price_eur": 100},
    }
    with TestClient(create_app()) as client:
        response = client.post("/preliminary-plans", json=payload)
    assert response.status_code == 422
    assert "different cities" in response.json()["detail"]
