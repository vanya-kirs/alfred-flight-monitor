# Guided travel UX design

## Intent

Make the next step obvious after a flight is selected, replace ambiguous manual draft editing with Alfred recommendations, and give travelers a small but coherent identity and trip-editing flow.

## Registration

Before the existing bank-consent step, show a compact demo registration card with full name and password. Full name is stored only in `sessionStorage` and shown in the top bar. The password is validated in memory (minimum 6 characters) and is never persisted, logged, or sent to an external service. This is explicitly labeled as demo registration for the current browser session.

## Flight-to-hotel continuation

After a flight is selected, show a fixed, high-contrast continuation popup above the page content with destination and dates, one primary action “Подобрать отель” and a secondary dismiss action. The existing inline continuation remains as contextual fallback. Opening the popup must not automatically select a hotel or navigate away.

## Plan editor

“Редактировать поездку” opens a dedicated editor dialog. The traveler chooses either an existing activity to modify or “Создать новую”, then sets title, date, start time, duration, and note. Saving modifies the selected activity or inserts a new activity into the chosen day, sorts the timeline chronologically, persists it, and preserves a dependency-stale plan state until the plan is rebuilt.

## Booking draft recommendations

The booking draft no longer exposes editable passenger/night inputs. It shows read-only values selected in search and an Alfred recommendation card. The recommendation uses the flight search passenger count and the number of calendar days between arrival and return departure, clamped to 1–30 nights. A button applies the recommendation; hotel changes never change flight dates and a mismatch remains visible.

## Project information

Add a top-right “О проекте” button. Its dialog describes flight search, hotel filtering, day planning, monitoring, demo-data limitations, and privacy. It contains a disabled “GitHub — добавим позже” control until a repository URL exists.

## Hotel links and filtering

Synthetic hotels keep their exact Alfred detail page. Do not display a generic Booking.com search as the hotel’s page; replace it with a clear demo-data note. Strict all-selected-feature semantics stay intact. Expand deterministic hotel metadata so common combinations of several filters still have results across meal plans. If the strict combination is genuinely impossible, the UI names the selected constraints and offers one-click “Сбросить фильтры”, rather than appearing broken.

## Constraints

- Keep FastAPI and the existing single-page vanilla JavaScript architecture.
- Do not add dependencies.
- Do not persist passwords, passport data, or payment data.
- Russian UI copy and the current T-Bank-inspired visual language remain.
- Existing ticket, hotel, monitoring, and booking APIs stay backward compatible.
