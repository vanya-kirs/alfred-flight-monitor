from datetime import date

from alfred_flights.ticket_search.domain import SearchQuery
from alfred_flights.ticket_search.providers.demo import DemoTicketProvider


def test_same_day_connection_is_not_marked_as_overnight() -> None:
    offers = DemoTicketProvider().search(
        SearchQuery(origin="MOW", destination="IST", departure_date=date(2026, 12, 10))
    )

    connection = next(item for item in offers if item.id.endswith("connection"))
    assert connection.overnight_layover is False


def test_provider_returns_many_options_with_real_search_purchase_url() -> None:
    offers = DemoTicketProvider().search(
        SearchQuery(
            origin="JFK",
            destination="LAX",
            departure_date=date(2026, 12, 10),
            return_date=date(2026, 12, 20),
            adults=2,
        )
    )

    assert len(offers) >= 10
    assert all(offer.purchase_url == "https://www.aviasales.com/search/JFK1012LAX20122" for offer in offers)
