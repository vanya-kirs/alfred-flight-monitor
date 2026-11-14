# Ticket Search and Alternative Ranking — Design

## Intent

Extend Alfred from a flight-status monitor into a useful flight discovery tool. A traveler can search by origin, destination, departure date, return date, and passenger count, compare options with transparent trade-offs, and reuse the same ranking logic when a monitored flight is disrupted.

## User experience

The main screen starts with a compact search form:

- origin city or IATA airport code;
- destination city or IATA airport code;
- departure date;
- optional return date;
- adults, from 1 through 9;
- checked baggage required or not;
- sorting: recommended, cheapest, fastest, or fewest stops.

Search results are cards. Each card shows airline, flight number, local departure and arrival time with timezone offsets, duration, stops, total price for every passenger, currency, cabin baggage, checked baggage, and transit countries. Every result contains automatically generated main advantages and disadvantages. The user can re-sort the already returned results without another provider call.

When `return_date` is present, one result is a round-trip offer: it contains separate outbound and inbound journeys plus one total price. Baggage and transit assessments cover both directions.

## Functional rules

- A provider adapter returns structured offers. The first adapter is a deterministic demo catalog and needs no external key.
- City names and IATA codes are normalized case-insensitively through a small built-in airport catalog.
- Price is the total for all passengers. Demo base fares are multiplied by passenger count.
- When checked baggage is required, offers without included checked baggage remain visible but receive a clear disadvantage and rank below otherwise comparable offers. A strict “baggage included only” filter is also available.
- Transit visa risk is derived from the user's optional visa-free country-code list. Unknown visa status is shown as a warning, never silently accepted.
- Connection feasibility uses a 90-minute minimum for the demo catalog. Offers below it are excluded.
- Overnight layovers, airport changes, checked-baggage absence, high price, long duration, and many stops create disadvantages.
- Low price, short duration, direct routing, included checked baggage, and visa-compatible transit create advantages.
- Recommended ranking is deterministic and combines normalized price, duration, stops, baggage fit, and visa risk. The response includes a numeric score and explanation fields; no opaque “AI” claim is made.
- Cheapest, fastest, and fewest-stops sorts use stable tie-breakers: recommendation score, then offer ID.
- Choosing an offer stores a lightweight in-memory trip plan containing the selected offer and selection time. It does not book or reserve anything.

## API

- `POST /ticket-search` accepts the search request and returns the normalized query plus ranked offers.
- `POST /ticket-search/sort` accepts an existing list of offers and a sort mode, returning only the reordered list. The frontend may sort locally but this endpoint keeps the rule reusable.
- `POST /trip-plan/selection` stores the selected offer from the latest search; `GET /trip-plan` returns it.
- Validation rejects identical origin/destination, dates in the wrong order, passenger counts outside 1–9, unknown airports, unsupported sort modes, and malformed country codes.

## Architecture

- `ticket_search/domain.py`: immutable search query, offer, baggage, segment, and assessment types.
- `ticket_search/service.py`: validation, provider invocation, filtering, assessment generation, scoring, and sorting.
- `ticket_search/providers/demo.py`: deterministic catalog of realistic offers for supported routes.
- `ticket_search/api.py`: Pydantic request/response schemas and route registration.
- Existing FastAPI app wires the ticket-search router and keeps monitoring unchanged.
- Existing static page gains the minimal search form, result cards, filters, and sorting controls.

The provider interface is the seam for a future Amadeus, Travelpayouts, or airline integration. Real booking, payment, live seat availability, fare guarantees, passport storage, and automatic rebooking remain out of scope.

## Supported demo data

The initial catalog supports Moscow (`MOW`, `SVO`, `DME`, `VKO`), Istanbul (`IST`), Rome (`ROM`, `FCO`), Paris (`PAR`, `CDG`), Dubai (`DXB`), and Tbilisi (`TBS`). It contains direct and connecting alternatives with different prices, baggage rules, durations, and transit risks so every ranking and explanation path can be exercised.

## Privacy and safety

Search needs no passport data. Optional visa-free country codes are request-only and are not persisted. Prices are demo estimates and must be labeled as such. Selecting an offer records no booking and never initiates a purchase.

## Builder calls

- Use Russian UI copy, English API field names, and ISO 8601 timestamps.
- Keep the frontend framework-free and served by FastAPI.
- Use EUR as the single demo currency to avoid misleading conversion logic.
- Preserve all current monitoring endpoints and tests.
