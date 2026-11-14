# Alfred Travel Platform — Complete Case Design

## Intent

Turn the current flight-search and disruption prototype into a coherent TravelTech service that helps an individual, family, or group plan a trip, keep every reservation in one timeline, react to disruptions, and receive explainable recommendations without exposing sensitive personal data.

This is an executable product prototype, not a licensed travel agency. Real purchases, ticket issuance, refunds, card processing, and production passport handling remain behind provider interfaces until commercial contracts, credentials, legal review, and secure infrastructure exist.

## User journey

1. A user creates a trip, adds dates, destinations, timezone, interests, budget, and participants.
2. Participants join by invitation and receive roles: owner, editor, or viewer.
3. The group searches flights, hotels, transfers, and activities. Results show price, baggage, visa/transit warnings, timing conflicts, and explicit advantages/disadvantages.
4. A selected offer becomes a pending itinerary item. External checkout or a provider token completes the booking; Alfred never treats a click as a paid booking.
5. All confirmed items appear in one chronological trip timeline, displayed in each location's timezone and also normalized to UTC internally.
6. A monitoring worker polls provider adapters and processes provider events. Stale observations never roll state backward.
7. Delay or cancellation creates a disruption incident. Alfred calculates missed connections and downstream conflicts, stores offline notifications, and automatically searches flight alternatives and nearby activities.
8. The user chooses an alternative. Alfred updates the shared plan, records an audit event, and notifies every affected participant. It never purchases or cancels without explicit confirmation.
9. After the trip, participants can leave feedback. The recommendation engine updates only non-sensitive preference scores.

## Functional scope

### Accounts and groups

- Local prototype accounts identified by UUID and display name; production authentication is an external identity-provider adapter.
- Trip roles: owner may delete or finalize, editor may change the plan, viewer may only read.
- Invitation tokens are random, expiring, and single-use.
- Participant changes and itinerary mutations create audit events.

### Unified itinerary

- A trip owns itinerary items of type flight, hotel, transfer, activity, or custom.
- Every item stores provider reference, lifecycle state, UTC timestamps, original timezone, price/currency, participants, and cancellation state.
- Conflict detection covers overlaps, impossible airport transfers, hotel check-in after checkout, and connection buffers.
- Version numbers support optimistic synchronization for offline clients; conflicting edits return the current version instead of silently overwriting.

### Search and booking adapters

- Flights: current global IATA resolution and provider abstraction remain. Without a Travelpayouts token, cards are demonstrative and purchase opens an Aviasales search page. With approved credentials, a real provider adapter may replace them.
- Hotels, transfers, and activities initially use deterministic demo adapters with provider URLs. Their interfaces match future Booking/Expedia, transfer, and activity integrations.
- A booking record contains only an external provider token/reference and status. Payment-card numbers are never stored; payment uses a payment-provider token.
- Real provider failures use timeouts, limited retries, a circuit breaker, and last-known results clearly marked with freshness.

### Monitoring and disruption orchestration

- Monitoring accepts polling results and webhook/email-normalized events through one observation interface.
- Each observation carries provider time, received time, and source. Older observations are ignored.
- A disruption incident links the affected flight, downstream itinerary items, alternatives, notification state, and resolution.
- Connection risk includes scheduled/estimated arrival, terminal or airport change, a configurable minimum connection time, baggage re-check, timezone conversion, and transit-country visa status.
- Alternatives include other flights plus airport-area activities or an overnight option when no safe same-day flight exists.
- Updating a shared trip requires explicit selection and preserves the displaced item as superseded for auditability.

### Notifications and offline behavior

- Notifications are durable outbox records, not fire-and-forget calls.
- Channels are in-app first, with adapter seams for push, Telegram, email, and SMS.
- An offline participant sees unread notifications and itinerary changes after reconnecting.
- Delivery is idempotent, retried with backoff, and records delivered/failed status per participant and channel.

### Recommendations and feedback

- Interests use explicit categories such as culture, food, family, nightlife, nature, and accessibility.
- Ranking combines declared interests, budget, distance from itinerary, opening hours, prior feedback, and schedule fit.
- Explanations state why an item was recommended. Sensitive attributes, passport details, payment data, and private data of other group members never enter ranking.
- Users can reset their preference history.

## Privacy and security

- Passport data is collected only for a specific booking step through a `SensitiveDocumentVault` interface.
- The prototype vault stores no real document number; it stores a synthetic encrypted payload for tests plus purpose, owner, booking ID, `expires_at`, and deletion audit.
- Production must use envelope encryption backed by KMS/HSM, strict service-level access, masked logs, and an isolated database. Application logs never contain raw passport fields.
- Default retention ends 24 hours after trip completion or immediately after provider confirmation when the provider no longer needs the data, whichever is earlier. Failed/abandoned booking payloads expire after 30 minutes. A deletion worker enforces expiry.
- Payment data is token-only. No PAN, CVV, or full cardholder data enters Alfred.
- Group participants cannot view one another's passport or payment data.
- Every sensitive-data read, write, and deletion is audited without recording the secret itself.

## Reliability and time

- Store instants in UTC and retain an IANA timezone for display and recurrence rules.
- Provider observations include freshness; stale data is visibly labeled.
- Provider calls have deadlines, bounded retry, circuit breaking, and cached fallback.
- Event processing and notifications are idempotent by event key.
- PostgreSQL is the target source of truth; Redis is the target cache/job queue. The current prototype may use in-memory repositories behind identical interfaces until infrastructure is introduced.

## API modules

- `/users`, `/trips`, `/trips/{id}/participants`, `/trips/{id}/invitations`
- `/trips/{id}/itinerary`, `/trips/{id}/conflicts`, `/trips/{id}/audit`
- `/ticket-search`, `/hotel-search`, `/transfer-search`, `/activity-search`
- `/bookings`, `/bookings/{id}/checkout-link`, `/bookings/{id}/status`
- `/flights`, `/flights/{id}/check`, `/flights/{id}/alternatives`
- `/incidents`, `/incidents/{id}/alternatives`, `/incidents/{id}/resolve`
- `/notifications`, `/notifications/{id}/read`, `/sync`
- `/preferences`, `/recommendations`, `/feedback`
- Internal-only `/sensitive-documents` operations guarded by booking purpose and role.

## Minimal frontend

Keep the framework-free FastAPI page. Add sections incrementally: trip switcher, participant list, unified timeline, conflicts, search tabs, incident banner, alternative comparison, notification inbox, and preferences. Functionality and clear states take priority over visual polish.

## Delivery phases

1. **Foundation already present:** global flight discovery, baggage/visa/timezone ranking, flight monitoring, notifications, alternative search, Aviasales handoff.
2. **Shared trip vertical slice:** users, trips, roles, invitations, unified itinerary, conflict detection, audit, optimistic sync, and a minimal timeline UI.
3. **Disruption vertical slice:** durable incidents, downstream impact calculation, automatic alternatives/activities, explicit resolution, group notifications, offline outbox.
4. **Travel inventory slice:** hotel, transfer, and activity adapters plus pending/confirmed booking state and provider checkout links.
5. **Personalization slice:** interests, explainable ranking, feedback, and preference reset.
6. **Sensitive-data and production infrastructure slice:** tokenized payment boundary, expiring vault abstraction, deletion worker, PostgreSQL, Redis, real provider credentials, observability, and security review.

Each phase must leave a runnable product with tests. Provider credentials are configuration, never committed code.

## Non-goals until external authority exists

- Issuing airline tickets or charging real payment cards.
- Storing real passport scans or numbers in the prototype.
- Claiming demo prices or availability are live.
- Automatically cancelling, purchasing, refunding, or changing paid bookings.

## Builder calls

- Python/FastAPI remains the backend and vanilla HTML/JavaScript remains the frontend for this prototype.
- Phase 2 is the next implementation target because every later feature needs a shared trip and timeline.
- Use in-memory repositories first but define repository protocols so PostgreSQL can replace them.
- Russian UI copy, English API field names, ISO 8601 timestamps, UUID identifiers.
- The current prototype user is supplied by the required `X-User-ID` header.
- A trip is multi-city and stores an ordered destination sequence.
- Editors may propose disruption alternatives; only the trip owner may apply one to the shared plan.
- Offline sync is bidirectional: clients read changes after a cursor and submit idempotent local operations with client operation IDs.
