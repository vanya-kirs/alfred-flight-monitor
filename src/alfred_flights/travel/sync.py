from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from alfred_flights.travel.domain import ItemType
from alfred_flights.travel.service import TravelService, VersionConflict


class SyncService:
    def __init__(self, travel: TravelService) -> None:
        self.travel = travel
        self.processed: dict[tuple[UUID, UUID, str], dict[str, Any]] = {}

    def synchronize(
        self,
        user_id: UUID,
        trip_id: UUID,
        *,
        after_version: int,
        operations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.travel.get_trip(user_id, trip_id)
        results: list[dict[str, Any]] = []
        for operation in operations:
            operation_id = str(operation.get("operation_id", "")).strip()
            if not operation_id:
                raise ValueError("operation_id is required")
            key = (trip_id, user_id, operation_id)
            if key in self.processed:
                result = dict(self.processed[key])
                result["status"] = "replayed"
                results.append(result)
                continue
            if operation.get("action") != "itinerary.add":
                result = {"operation_id": operation_id, "status": "rejected", "reason": "unsupported action"}
                results.append(result)
                continue
            payload = dict(operation.get("payload") or {})
            try:
                item = self.travel.add_itinerary_item(
                    user_id,
                    trip_id,
                    expected_version=int(operation["expected_version"]),
                    item_type=ItemType(payload["item_type"]),
                    title=str(payload["title"]),
                    start_at=_datetime(payload["start_at"]),
                    end_at=_datetime(payload["end_at"]),
                    timezone=str(payload["timezone"]),
                    participant_ids=tuple(UUID(value) for value in payload.get("participant_ids", [])),
                    provider_reference=payload.get("provider_reference"),
                    metadata=dict(payload.get("metadata") or {}),
                )
            except VersionConflict as exc:
                results.append(
                    {
                        "operation_id": operation_id,
                        "status": "conflict",
                        "current_version": exc.current_version,
                    }
                )
                continue
            result = {"operation_id": operation_id, "status": "applied", "entity_id": str(item.id)}
            self.processed[key] = result
            results.append(result)

        trip = self.travel.get_trip(user_id, trip_id)
        return {
            "results": results,
            "changes": self.travel.audit_events(user_id, trip_id, after_version),
            "current_version": trip.version,
        }


def _datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("sync datetime must be timezone-aware")
    return result

