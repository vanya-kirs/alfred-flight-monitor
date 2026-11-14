from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from alfred_flights.api import create_app


def test_home_page_serves_flight_dashboard() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="flight-form"' in response.text
    assert 'id="flights-list"' in response.text
    assert 'id="notifications-list"' in response.text
    assert 'id="ticket-search-form"' in response.text
    assert 'id="trip-workspace"' in response.text
    assert 'id="plan-builder"' in response.text
    assert 'id="selected-flight-summary"' in response.text
    assert 'id="selected-hotel-summary"' in response.text
    assert 'id="plan-variants"' in response.text
    assert 'Предварительный план поездки' in response.text
    assert 'async function loadHotelsForSelectedFlight' in response.text
    assert 'Выберите подходящий вариант' in response.text
    assert 'id="inventory-form"' in response.text
    assert 'id="trip-timeline"' in response.text
    assert 'id="ticket-sort"' in response.text
    assert 'id="ticket-offers-list"' in response.text
    assert 'id="more-ticket-offers"' in response.text
    assert 'id="location-suggestions"' in response.text
    assert 'id="ticket-hotels"' not in response.text
    assert 'id="hotel-search-form"' in response.text
    assert 'id="hotel-nights"' in response.text
    assert 'id="hotel-search-results"' in response.text
    assert 'id="more-hotel-offers"' in response.text
    assert 'hotel-metrics' in response.text
    assert 'hotel-amenities' in response.text
    assert 'Открыть отель' in response.text
    assert 'id="flight-number" name="flight_number" value="SU100"' in response.text
    assert 'id="monitor-origin" value="Москва"' in response.text
    assert 'id="monitor-destination" value="Стамбул"' in response.text
    assert "document.querySelector('#departure-at').value" in response.text
    assert 'id="ticket-error-summary"' in response.text
    assert 'id="bank-consent-gate"' not in response.text
    assert 'id="register-bank-consent"' in response.text
    assert 'Т‑Банк — самый лучший' in response.text
    assert 'data-section-target="tickets"' in response.text
    assert 'data-section-target="hotels"' in response.text
    assert 'data-section-target="plan"' in response.text
    assert 'data-section-target="monitoring"' in response.text
    assert 'function showSection' in response.text
    assert 'function renderPlanDays' in response.text
    assert 'data-edit-plan' in response.text
    assert 'data-add-activity-day' in response.text
    assert 'function addActivityToDay' in response.text
    assert 'data-add-activity="${escapeHtml(plan.strategy)}"' not in response.text
    assert 'data-remove-event' in response.text
    assert 'id="hotel-continuation"' in response.text
    assert 'id="continue-hotel-planning"' in response.text
    assert 'Продолжить планирование и подобрать отель' in response.text
    assert 'function prepareHotelContinuation' in response.text
    assert 'id="hotel-filters"' in response.text
    assert 'data-hotel-feature="daily_cleaning"' in response.text
    assert 'data-hotel-feature="private_beach"' in response.text
    assert 'id="hotel-meal-plan"' in response.text
    assert 'Ежедневная уборка' in response.text
    assert 'Собственный пляж' in response.text
    assert 'Трёхразовое питание' in response.text
    assert 'function selectedHotelFilters' in response.text
    assert 'target="_self"' in response.text
    assert 'data-section-target="bookings"' in response.text
    assert 'data-app-section="bookings"' in response.text
    assert 'id="bookings-content"' in response.text
    assert 'id="booking-passengers-value"' in response.text
    assert 'id="booking-nights-value"' in response.text
    assert 'id="booking-passengers"' not in response.text
    assert 'id="booking-nights"' not in response.text
    assert 'id="booking-cost-breakdown"' in response.text
    assert 'data-remove-booking' in response.text
    assert 'let bookingDraft' in response.text
    assert 'function saveBookingDraft' in response.text
    assert 'function renderBookings' in response.text
    assert 'function calculateBookingTotal' in response.text
    assert 'function recommendedBookingParameters' in response.text
    assert 'function applyBookingRecommendation' in response.text
    assert 'id="booking-recommendation"' in response.text
    assert 'id="apply-booking-recommendation"' in response.text
    assert 'function openBookingPlanEditor' in response.text
    assert 'data-edit-booking-plan' in response.text
    assert "clearSavedPlans(); bookingDraft.flight = null" in response.text
    assert "clearSavedPlans(); bookingDraft.hotel = null" in response.text
    assert "bookingDraft.plan_stale = false;" not in response.text.split('function saveEditedPlan', 1)[1].split('function clearSavedPlans', 1)[0]
    assert "const previous = dayEvents.at(-1);" in response.text
    assert 'Дата обратного рейса' in response.text
    assert 'необязательно' not in response.text
    assert 'Оставьте пустым, если летите в один конец' not in response.text
    assert 'id="ticket-return" type="text"' in response.text
    assert 'placeholder="ДД.ММ.ГГГГ" autocomplete="off" required' in response.text
    assert 'inputmode="numeric"' in response.text
    assert 'placeholder="ДД.ММ.ГГГГ"' in response.text
    assert 'function parseRussianDate' in response.text
    assert 'function formatRussianDateInput' in response.text
    assert 'novalidate' in response.text
    assert 'showFormError' in response.text
    assert 'field-invalid' in response.text
    assert 'id="ticket-strict-baggage"' not in response.text
    assert response.text.count('id="ticket-baggage"') == 1
    assert 'Безвизовый транзит' not in response.text
    assert 'id="ticket-visas"' not in response.text
    assert 'id="register-gate"' in response.text
    assert 'id="register-full-name"' in response.text
    assert 'id="register-password" type="password"' in response.text
    assert 'id="register-password-confirmation" type="password"' in response.text
    assert 'id="register-mode-switch"' in response.text
    assert 'id="register-submit"' in response.text
    assert 'id="registered-user"' in response.text
    assert 'id="account-button"' in response.text
    assert 'id="account-dialog"' in response.text
    assert 'id="account-logout"' in response.text
    assert 'Личный кабинет' in response.text
    assert 'function logoutAccount' in response.text
    assert "sessionStorage.setItem('alfred_profile_name'" in response.text
    assert "sessionStorage.setItem('alfred_account_id'" in response.text
    assert "'/auth/register'" in response.text
    assert "'/auth/login'" in response.text
    assert 'await fetch(' in response.text
    assert "localStorage.setItem('alfred_password'" not in response.text
    assert "sessionStorage.setItem('alfred_password'" not in response.text
    assert 'id="project-info-button"' in response.text
    assert 'id="project-dialog"' in response.text
    assert 'id="project-overview"' in response.text
    assert 'Какую задачу решает Альфред' in response.text
    assert 'Как устроен сервис' in response.text
    assert 'Ключевые проектные решения' in response.text
    assert 'Надёжность и приватность' in response.text
    assert 'Ограничения демоверсии' in response.text
    assert 'scrypt' in response.text
    assert 'SQLite' in response.text
    assert 'eventual consistency' in response.text
    assert 'href="https://github.com/vanya-kirs/alfred-flight-monitor"' in response.text
    assert 'GitHub — исходный код' in response.text
    assert 'GitHub — добавим позже' not in response.text
    assert 'id="hotel-next-step"' in response.text
    assert 'function showHotelContinuationPopup' in response.text
    assert 'id="plan-change-dialog"' in response.text
    assert 'id="plan-change-mode"' in response.text
    assert 'id="plan-change-target"' in response.text
    assert 'id="plan-change-date"' in response.text
    assert 'id="plan-change-time"' in response.text
    assert 'id="plan-change-duration"' in response.text
    assert 'function openPlanChangeEditor' in response.text
    assert 'function applyPlanChange' in response.text
    assert 'id="reset-hotel-filters"' in response.text
    assert 'function resetHotelFilters' in response.text


def test_health_endpoint() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_location_suggestions_endpoint_returns_city_choices() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/locations/suggest", params={"q": "стам", "limit": 5})

    assert response.status_code == 200
    assert response.json()[0]["code"] == "IST"
    assert response.json()[0]["city"] == "Стамбул"


def test_hotel_search_supports_russian_city_and_nights_total() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/hotel-search", json={
            "destination": "Сочи", "check_in": "2026-12-10", "nights": 5,
            "guests": 2, "sort_by": "price",
        })

    assert response.status_code == 200
    body = response.json()
    assert body["destination_code"] == "AER"
    assert body["nights"] == 5
    assert body["check_out"] == "2026-12-15"
    assert len(body["offers"]) >= 10
    assert all(item["total_price_eur"] == item["nightly_price_eur"] * 5 for item in body["offers"])
    assert [item["total_price_eur"] for item in body["offers"]] == sorted(item["total_price_eur"] for item in body["offers"])
    required_details = {
        "stars", "rating", "review_count", "room_type", "meal_plan", "amenities",
        "distance_to_center_km", "free_cancellation", "pay_at_property",
    }
    assert all(required_details <= item.keys() for item in body["offers"])
    assert all(item["amenities"] for item in body["offers"])
    assert all(item["checkout_url"].startswith("https://") for item in body["offers"])
    assert all("example.com" not in item["checkout_url"] for item in body["offers"])


def test_hotel_search_requires_all_selected_features() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/hotel-search", json={
            "destination": "Сочи", "check_in": "2026-12-10", "nights": 3,
            "guests": 2, "required_features": ["wifi", "private_beach"],
        })

    assert response.status_code == 200
    offers = response.json()["offers"]
    assert offers
    assert all({"wifi", "private_beach"} <= set(item["feature_codes"]) for item in offers)


def test_hotel_search_filters_one_meal_plan() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/hotel-search", json={
            "destination": "Стамбул", "check_in": "2026-12-10", "nights": 2,
            "guests": 1, "meal_plan": "half_board",
        })

    assert response.status_code == 200
    offers = response.json()["offers"]
    assert offers
    assert all(item["meal_code"] == "half_board" for item in offers)


def test_hotel_search_common_multi_filters_have_options_for_each_meal_plan() -> None:
    with TestClient(create_app()) as client:
        for meal_plan in ("none", "breakfast", "half_board", "full_board"):
            response = client.post("/hotel-search", json={
                "destination": "Сочи", "check_in": "2026-12-10", "nights": 3,
                "guests": 2,
                "required_features": [
                    "daily_cleaning", "wifi", "air_conditioning", "free_cancellation",
                    "city_center", "pool", "gym",
                ],
                "meal_plan": meal_plan,
            })

            assert response.status_code == 200
            offers = response.json()["offers"]
            assert offers, meal_plan
            assert all(item["meal_code"] == meal_plan for item in offers)
            assert all(
                {
                    "daily_cleaning", "wifi", "air_conditioning", "free_cancellation",
                    "city_center", "pool", "gym",
                }
                <= set(item["feature_codes"])
                for item in offers
            )


def test_hotel_search_rejects_unknown_filter() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/hotel-search", json={
            "destination": "Сочи", "check_in": "2026-12-10", "nights": 2,
            "guests": 1, "required_features": ["free_champagne"],
        })

    assert response.status_code == 422


def test_hotel_search_rejects_unknown_meal_plan() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/hotel-search", json={
            "destination": "Сочи", "check_in": "2026-12-10", "nights": 2,
            "guests": 1, "meal_plan": "all_inclusive",
        })

    assert response.status_code == 422


def test_hotel_search_returns_empty_list_for_impossible_feature_combination() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/hotel-search", json={
            "destination": "Сочи", "check_in": "2026-12-10", "nights": 2,
            "guests": 1, "required_features": ["private_beach", "city_center", "pets"],
        })

    assert response.status_code == 200
    assert response.json()["offers"] == []


def test_hotel_detail_page_shows_the_exact_searched_offer() -> None:
    with TestClient(create_app()) as client:
        search = client.post("/hotel-search", json={
            "destination": "Сочи", "check_in": "2026-12-10", "nights": 4, "guests": 2,
        })
        offer = search.json()["offers"][0]
        detail = client.get(f"/hotels/{offer['detail_id']}")

    assert detail.status_code == 200
    assert detail.headers["content-type"].startswith("text/html")
    assert offer["title"] in detail.text
    assert "2026-12-10" in detail.text
    assert f"€{offer['total_price_eur']:.2f}" in detail.text
    assert offer["amenities"][0] in detail.text
    assert "Поиск у поставщика" not in detail.text
    assert "Демонстрационное предложение" in detail.text


def test_hotel_detail_url_keeps_its_search_snapshot_after_later_search() -> None:
    with TestClient(create_app()) as client:
        first = client.post("/hotel-search", json={
            "destination": "Сочи", "check_in": "2026-12-10", "nights": 4, "guests": 2,
        }).json()["offers"][0]
        first_url = f"/hotels/{first['detail_id']}"

        second = client.post("/hotel-search", json={
            "destination": "Сочи", "check_in": "2027-01-20", "nights": 2, "guests": 1,
        }).json()["offers"][0]
        first_detail = client.get(first_url)
        second_detail = client.get(f"/hotels/{second['detail_id']}")

    assert first["detail_id"] != second["detail_id"]
    assert "2026-12-10" in first_detail.text
    assert "2026-12-14" in first_detail.text
    assert "2027-01-20" not in first_detail.text
    assert "2027-01-20" in second_detail.text


def test_hotel_detail_page_returns_404_for_unknown_offer() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/hotels/hotel-does-not-exist")

    assert response.status_code == 404


def test_register_list_check_and_notifications_flow() -> None:
    app = create_app()
    with TestClient(app) as client:
        created = client.post(
            "/flights",
            json={"flight_number": " su 100 ", "departure_at": "2026-11-10T07:30:00Z"},
        )
        flight = created.json()
        flight_id = flight["id"]

        assert created.status_code == 201
        assert flight["flight_number"] == "SU100"
        assert client.get("/flights").json() == [flight]

        provider_update = client.post(
            f"/demo/flights/{flight_id}/observation",
            json={
                "state": "delayed",
                "observed_at": "2026-11-10T04:00:00Z",
                "delay_minutes": 75,
            },
        )
        assert provider_update.status_code == 204
        checked = client.post(f"/flights/{flight_id}/check")

        assert checked.status_code == 200
        assert checked.json()["flight"]["state"] == "delayed"
        assert checked.json()["notification"]["message"].endswith("75 minutes.")
        assert len(client.get("/notifications").json()) == 1


def test_unknown_flight_returns_404() -> None:
    with TestClient(create_app()) as client:
        response = client.get(f"/flights/{uuid4()}")

    assert response.status_code == 404


def test_naive_departure_time_returns_422() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/flights",
            json={"flight_number": "SU100", "departure_at": "2026-11-10T07:30:00"},
        )

    assert response.status_code == 422


def test_ticket_search_returns_ranked_offers_with_tradeoffs() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/ticket-search",
            json={
                "origin": "Москва",
                "destination": "Стамбул",
                "departure_date": "2026-12-10",
                "return_date": "2026-12-20",
                "adults": 2,
                "checked_baggage_required": True,
                "visa_free_countries": ["GE"],
                "sort_by": "recommended",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["query"]["origin"] == "MOW"
    assert body["query"]["destination"] == "IST"
    assert body["is_demo"] is True
    assert len(body["offers"]) >= 18
    assert all(item["advantages"] or item["disadvantages"] for item in body["offers"])
    assert all(float(item["total_price_eur"]) > float(item["price_per_adult_eur"]) for item in body["offers"])
    scores = [item["recommendation_score"] for item in body["offers"]]
    assert scores == sorted(scores, reverse=True)
    journey = body["offers"][0]["outbound"]
    first = journey["segments"][0]
    last = journey["segments"][-1]
    assert first["origin_city"] == "Москва"
    assert "airport" in first["origin_airport"].lower() or first["origin_airport"]
    assert last["destination_city"] == "Стамбул"
    assert last["destination_airport"]
    assert journey["departure_period"] in {"day", "night"}
    assert {"day", "night"} <= {item["outbound"]["departure_period"] for item in body["offers"]}
    assert all(item["inbound"] is not None for item in body["offers"])


def test_ticket_search_requires_return_date() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/ticket-search",
            json={"origin": "MOW", "destination": "IST", "departure_date": "2026-12-10"},
        )

    assert response.status_code == 422


def test_ticket_search_supports_round_trips_and_cheapest_sort() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/ticket-search",
            json={
                "origin": "MOW",
                "destination": "ROM",
                "departure_date": "2026-12-10",
                "return_date": "2026-12-20",
                "adults": 1,
                "sort_by": "cheapest",
            },
        )

    assert response.status_code == 200
    offers = response.json()["offers"]
    assert offers
    assert all(item["inbound"] is not None for item in offers)
    prices = [float(item["total_price_eur"]) for item in offers]
    assert prices == sorted(prices)


def test_ticket_search_rejects_unknown_airport() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/ticket-search",
            json={
                "origin": "XXX",
                "destination": "ROM",
                "departure_date": "2026-12-10",
                "return_date": "2026-12-20",
            },
        )

    assert response.status_code == 422
    assert "unknown origin" in response.json()["detail"]


def test_ticket_search_supports_global_city_names_and_buy_links() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/ticket-search",
            json={
                "origin": "New York",
                "destination": "Los Angeles",
                "departure_date": "2026-12-10",
                "return_date": "2026-12-20",
                "adults": 2,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "local-demo-catalog"
    assert body["purchase_destination"] == "Aviasales"
    assert len(body["offers"]) >= 18
    assert len(body["query"]["origin"]) == 3
    assert len(body["query"]["destination"]) == 3
    assert all(
        item["purchase_url"].startswith("https://www.aviasales.com/search/")
        for item in body["offers"]
    )


def test_selected_ticket_is_saved_to_trip_plan_without_booking() -> None:
    app = create_app()
    with TestClient(app) as client:
        search = client.post(
            "/ticket-search",
            json={
                "origin": "MOW",
                "destination": "IST",
                "departure_date": "2026-12-10",
                "return_date": "2026-12-20",
            },
        ).json()
        offer_id = search["offers"][0]["id"]
        search_id = search["search_id"]

        selected = client.post(
            "/trip-plan/selection",
            json={"search_id": search_id, "offer_id": offer_id},
        )
        plan = client.get("/trip-plan", params={"search_id": search_id})

    assert selected.status_code == 201
    assert selected.json()["selected_offer"]["id"] == offer_id
    assert selected.json()["booking_created"] is False
    assert plan.status_code == 200
    assert plan.json()["selected_offer"]["id"] == offer_id


def test_search_ids_keep_concurrent_searches_isolated() -> None:
    app = create_app()
    with TestClient(app) as client:
        first = client.post(
            "/ticket-search",
            json={"origin": "MOW", "destination": "IST", "departure_date": "2026-12-10", "return_date": "2026-12-20"},
        ).json()
        second = client.post(
            "/ticket-search",
            json={"origin": "MOW", "destination": "ROM", "departure_date": "2026-12-11", "return_date": "2026-12-21"},
        ).json()

        selection = client.post(
            "/trip-plan/selection",
            json={"search_id": first["search_id"], "offer_id": first["offers"][0]["id"]},
        )

    assert first["search_id"] != second["search_id"]
    assert selection.status_code == 201
    assert selection.json()["selected_offer"]["id"] == first["offers"][0]["id"]


def test_disrupted_monitored_flight_can_search_alternatives() -> None:
    app = create_app()
    with TestClient(app) as client:
        created = client.post(
            "/flights",
            json={
                "flight_number": "SU100",
                "departure_at": "2026-12-10T08:00:00+03:00",
                "origin": "MOW",
                "destination": "IST",
            },
        ).json()
        client.post(
            f"/demo/flights/{created['id']}/observation",
            json={"state": "cancelled", "observed_at": "2026-12-09T10:00:00Z"},
        )
        client.post(f"/flights/{created['id']}/check")

        alternatives = client.post(
            f"/flights/{created['id']}/alternatives",
            json={"adults": 2, "checked_baggage_required": True, "visa_free_countries": ["GE"]},
        )

    assert alternatives.status_code == 200
    assert alternatives.json()["offers"]
    assert alternatives.json()["query"]["origin"] == "MOW"
    assert alternatives.json()["query"]["destination"] == "IST"
