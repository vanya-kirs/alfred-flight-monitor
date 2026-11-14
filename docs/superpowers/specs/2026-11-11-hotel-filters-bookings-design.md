# Hotel filters and trip bookings design

## Intent

Extend the Alfred demo so travelers can require concrete hotel features, add activities to an explicitly chosen day, and review the whole selected trip in one editable cost summary.

## Hotel filters

The hotel form exposes checkboxes for daily cleaning, Wi‑Fi, city center, near the sea, beachfront, private beach, pool, spa, air conditioning, gym, parking, pets, free cancellation, and pay at property. Meal plan is one exclusive selection: any, no meals, breakfast, two meals, or three meals.

`POST /hotel-search` accepts `required_features: list[str]` and `meal_plan: str | null`. Feature codes are `daily_cleaning`, `wifi`, `city_center`, `near_sea`, `beachfront`, `private_beach`, `pool`, `spa`, `air_conditioning`, `gym`, `parking`, `pets`, `free_cancellation`, and `pay_at_property`. Meal codes are `none`, `breakfast`, `half_board`, and `full_board`; “any” is sent as `null`. Every returned offer must satisfy every selected feature and the selected meal plan. Unknown filter values return HTTP 422. With no filters, existing behavior stays unchanged. Each response row exposes `feature_codes: list[str]`, `meal_code: str`, and the existing Russian display fields.

## Activities by day

Each rendered plan day has its own “Добавить активность” button. A new activity is inserted into that day, after its last event, and is immediately editable. The old card-level button and the implicit “second-to-last day” behavior are removed. Edited timelines continue to persist in local storage.

## My bookings

A fifth top-level section, “Мои бронирования”, displays the currently selected flight, hotel, applied plan, and plan activities. This is explicitly labeled as a preliminary booking draft, not a completed purchase.

The draft is stored in local storage and survives reloads. Users can change passenger count and hotel nights, edit plan activities through the existing plan editor, or remove the flight, hotel, or plan. Changing hotel nights updates only the stay dates and hotel cost; it never changes the selected flights. If hotel checkout no longer aligns with the return flight, the booking section shows a warning and marks the plan for rebuilding instead of silently changing flight dates. Prices recalculate immediately using transparent rules:

- flight: selected total divided by original passenger count, then multiplied by current passenger count;
- hotel: nightly price multiplied by current nights;
- activity: €20 per traveler for each activity event;
- transfer: €15 per transfer event;
- check-in, check-out, and rest events: €0.

The section shows line items and a grand total in euros. Removing or replacing an upstream item invalidates dependent data: removing or replacing the flight or hotel also removes the plan and its saved edits; removing the plan keeps flight and hotel.

## Hotel detail links

The current inventory uses synthetic demo hotel names, so a generic Booking.com search must not be presented as a direct property link. Every hotel card links to an Alfred detail route, `/hotels/{offer_id}`, which shows that exact offer, amenities, policies, dates, and pricing. A separate external provider button is shown only when the offer has a verified property-specific URL; generic provider search URLs are labeled as search and are not presented as the hotel page. Navigation uses the current tab to avoid popup blocking. State is retained in local storage so returning to Alfred restores the draft.

## Constraints

- Keep the existing FastAPI, in-memory inventory, and single-page vanilla JavaScript architecture.
- Do not introduce passport or payment-data storage.
- Preserve existing unfiltered hotel search and current ticket, monitoring, and plan behavior.
- UI copy remains Russian and the visual style remains consistent with the existing T‑Bank-inspired design.
