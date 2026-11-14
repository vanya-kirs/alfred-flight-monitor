from datetime import date, datetime, time, timedelta
from html import escape
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from alfred_flights.platform.service import InventoryService, PersonalizationService, SensitiveReferenceVault, booking_dict, offer_dict
from alfred_flights.travel.api import _raise_travel_error
from alfred_flights.travel.domain import ItemType
from alfred_flights.ticket_search.locations import RUSSIAN_CITY_NAMES, location_data, resolve_location

CurrentUser = Annotated[UUID, Header(alias="X-User-ID")]

HotelFeature = Literal[
    "daily_cleaning", "wifi", "city_center", "near_sea", "beachfront", "private_beach",
    "pool", "spa", "air_conditioning", "gym", "parking", "pets",
    "free_cancellation", "pay_at_property",
]
HotelMealPlan = Literal["none", "breakfast", "half_board", "full_board"]


class SearchRequest(BaseModel):
    kind: ItemType
    destination: str
    start_at: datetime
    end_at: datetime
    timezone: str


class BookingRequest(BaseModel):
    trip_id: UUID
    offer_id: str
    payment_token: str
    payment_data: dict[str, Any] = Field(default_factory=dict)


class ConfirmRequest(BaseModel):
    expected_version: int


class PreferenceRequest(BaseModel):
    interests: dict[str, float]


class FeedbackRequest(BaseModel):
    tag: str
    liked: bool


class VaultRequest(BaseModel):
    trip_id: UUID
    vault_token: str
    abandoned: bool = False
    raw_data: dict[str, Any] | None = None


class HotelSearchRequest(BaseModel):
    destination: str
    check_in: date
    nights: int = Field(default=1, ge=1, le=30)
    guests: int = Field(default=1, ge=1, le=10)
    sort_by: Literal["recommended", "price"] = "recommended"
    required_features: list[HotelFeature] = Field(default_factory=list)
    meal_plan: HotelMealPlan | None = None


def create_platform_router(inventory: InventoryService, personalization: PersonalizationService, vault: SensitiveReferenceVault) -> APIRouter:
    router = APIRouter()
    hotel_details_by_id: dict[str, dict[str, Any]] = {}

    @router.post("/hotel-search")
    def hotel_search(payload: HotelSearchRequest) -> dict[str, Any]:
        code = resolve_location(payload.destination)
        if code is None:
            raise HTTPException(status_code=422, detail=f"Не удалось найти город: {payload.destination}")
        data = location_data(code)
        timezone = str(data.get("tz") or "UTC")
        city = RUSSIAN_CITY_NAMES.get(code, str(data.get("city") or payload.destination).strip())
        zone = ZoneInfo(timezone)
        start_at = datetime.combine(payload.check_in, time(14, 0), tzinfo=zone)
        check_out = payload.check_in + timedelta(days=payload.nights)
        end_at = datetime.combine(check_out, time(11, 0), tzinfo=zone)
        offers = inventory.search(ItemType.HOTEL, city, start_at, end_at, timezone)
        rows = [
            {
                **offer_dict(item),
                "detail_id": f"{item.id}-{uuid4().hex}",
                **_hotel_details(index),
                "nightly_price_eur": item.price_eur,
                "total_price_eur": round(item.price_eur * payload.nights, 2),
                "nights": payload.nights,
                "guests": payload.guests,
            }
            for index, item in enumerate(offers)
        ]
        required_features = set(payload.required_features)
        rows = [item for item in rows if required_features <= set(item["feature_codes"])]
        if payload.meal_plan is not None:
            rows = [item for item in rows if item["meal_code"] == payload.meal_plan]
        if payload.sort_by == "price":
            rows.sort(key=lambda item: (item["total_price_eur"], item["id"]))
        hotel_details_by_id.update({item["detail_id"]: item for item in rows})
        return {
            "destination_code": code,
            "destination_city": city,
            "check_in": payload.check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "nights": payload.nights,
            "guests": payload.guests,
            "offers": rows,
        }

    @router.get("/hotels/{offer_id}", response_class=HTMLResponse)
    def hotel_detail(offer_id: str) -> HTMLResponse:
        item = hotel_details_by_id.get(offer_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Отель не найден. Выполните поиск ещё раз.")
        amenities = "".join(f"<li>{escape(str(value))}</li>" for value in item["amenities"])
        html = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(str(item['title']))} — Альфред</title><style>body{{margin:0;background:#f5f5f6;color:#202022;font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}main{{width:min(760px,calc(100% - 32px));margin:40px auto}}.card{{padding:30px;border-radius:26px;background:#fff;box-shadow:0 18px 55px rgba(30,30,34,.1)}}.brand{{display:inline-grid;place-items:center;width:38px;height:38px;border-radius:12px;background:#ffdd2d;font-weight:900}}h1{{margin:20px 0 8px;font-size:36px}}.muted{{color:#74747c}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:22px 0}}.metric{{padding:14px;border-radius:14px;background:#f3f3f5}}.demo-note{{margin-top:18px;padding:14px;border-radius:14px;background:#fff8cf;color:#62540a}}ul{{line-height:1.8}}a{{display:inline-block;margin:8px 8px 0 0;padding:13px 17px;border-radius:13px;color:#202022;background:#ffdd2d;text-decoration:none;font-weight:750}}@media(max-width:600px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><main><div class="card"><span class="brand">A</span><h1>{escape(str(item['title']))}</h1><p class="muted">Точная карточка выбранного предложения</p><div class="grid"><div class="metric"><strong>Заезд</strong><br>{escape(str(item['start_at'])[:10])}</div><div class="metric"><strong>Выезд</strong><br>{escape(str(item['end_at'])[:10])}</div><div class="metric"><strong>Номер</strong><br>{escape(str(item['room_type']))}</div><div class="metric"><strong>Питание</strong><br>{escape(str(item['meal_plan']))}</div><div class="metric"><strong>Рейтинг</strong><br>{escape(str(item['rating']))} · {escape(str(item['review_count']))} отзывов</div><div class="metric"><strong>Стоимость</strong><br>€{float(item['total_price_eur']):.2f}</div></div><h2>Что входит</h2><ul>{amenities}</ul><p>{'Бесплатная отмена' if item['free_cancellation'] else 'Отмена платная'} · {'Оплата в отеле' if item['pay_at_property'] else 'Оплата онлайн'}</p><p class="demo-note"><strong>Демонстрационное предложение.</strong> У синтетического отеля нет достоверной страницы на Booking.com, поэтому Альфред не показывает общую ссылку как ссылку на конкретный объект.</p><a href="/">Вернуться в Альфред</a></div></main></body></html>"""
        return HTMLResponse(html)

    @router.post("/inventory/search")
    def search(payload: SearchRequest, user_id: CurrentUser) -> list[dict[str, Any]]:
        try:
            offers = inventory.search(payload.kind, payload.destination, payload.start_at, payload.end_at, payload.timezone)
            ranked = personalization.rank(user_id, offers)
            return [{**offer_dict(row["offer"]), "personal_score": row["score"], "recommendation_reason": row["reason"]} for row in ranked]
        except Exception as exc:
            _raise_travel_error(exc)

    @router.post("/bookings", status_code=201)
    def book(payload: BookingRequest, user_id: CurrentUser) -> dict[str, Any]:
        try:
            return booking_dict(inventory.create_booking(user_id, payload.trip_id, payload.offer_id, payload.payment_token, payload.payment_data))
        except Exception as exc:
            _raise_travel_error(exc)

    @router.post("/bookings/{booking_id}/confirm")
    def confirm(booking_id: UUID, payload: ConfirmRequest, user_id: CurrentUser) -> dict[str, Any]:
        try:
            return booking_dict(inventory.confirm(user_id, booking_id, payload.expected_version))
        except Exception as exc:
            _raise_travel_error(exc)

    @router.put("/preferences")
    def set_preferences(payload: PreferenceRequest, user_id: CurrentUser) -> dict[str, float]:
        return personalization.set_preferences(user_id, payload.interests)

    @router.post("/preferences/feedback")
    def feedback(payload: FeedbackRequest, user_id: CurrentUser) -> dict[str, float]:
        return personalization.feedback(user_id, payload.tag, payload.liked)

    @router.delete("/preferences", status_code=204)
    def reset_preferences(user_id: CurrentUser) -> None:
        personalization.reset(user_id)

    @router.post("/privacy/passport-references", status_code=201)
    def store_reference(payload: VaultRequest, user_id: CurrentUser) -> dict[str, Any]:
        try:
            item = vault.store(user_id, payload.trip_id, payload.vault_token, abandoned=payload.abandoned, raw_data=payload.raw_data)
            return {"id": str(item.id), "trip_id": str(item.trip_id), "expires_at": item.expires_at.isoformat()}
        except Exception as exc:
            _raise_travel_error(exc)

    @router.post("/privacy/purge")
    def purge() -> dict[str, int]:
        return {"deleted": vault.purge()}

    return router


def _hotel_details(index: int) -> dict[str, Any]:
    room_types = ("Стандарт", "Улучшенный номер", "Семейный номер", "Полулюкс")
    meal_codes = ("breakfast", "none", "half_board", "full_board")
    meal_labels = {
        "none": "Без питания", "breakfast": "Завтрак включён",
        "half_board": "Двухразовое питание", "full_board": "Трёхразовое питание",
    }
    base_features = {
        "daily_cleaning", "wifi", "air_conditioning", "free_cancellation",
        "city_center", "pool", "gym",
    }
    # Five profiles are intentionally coprime with the four meal plans. Across the
    # twenty deterministic offers every profile appears once with every meal plan.
    feature_sets = (
        {"city_center", "pool", "gym", "pay_at_property"},
        {"near_sea", "private_beach", "parking"},
        {"beachfront", "private_beach", "pool", "spa", "pay_at_property"},
        {"city_center", "spa", "gym", "parking", "pets"},
        {"near_sea", "beachfront", "pool", "parking", "pay_at_property"},
    )
    amenity_labels = {
        "daily_cleaning": "Ежедневная уборка", "wifi": "Wi‑Fi", "city_center": "Центр города",
        "near_sea": "Рядом с морем", "beachfront": "Первая береговая линия",
        "private_beach": "Собственный пляж", "pool": "Бассейн", "spa": "Спа",
        "air_conditioning": "Кондиционер", "gym": "Фитнес-зал", "parking": "Парковка",
        "pets": "Можно с животными", "free_cancellation": "Бесплатная отмена",
        "pay_at_property": "Оплата в отеле",
    }
    features = base_features | feature_sets[index % len(feature_sets)]
    meal_code = meal_codes[index % len(meal_codes)]
    return {
        "stars": 3 + index % 3,
        "rating": round(8.1 + (index % 8) * 0.2, 1),
        "review_count": 184 + index * 137,
        "room_type": room_types[index % len(room_types)],
        "meal_plan": meal_labels[meal_code],
        "meal_code": meal_code,
        "feature_codes": sorted(features),
        "amenities": [amenity_labels[code] for code in sorted(features) if code not in {"free_cancellation", "pay_at_property"}],
        "distance_to_center_km": round(0.4 + index * 0.55, 1),
        "cleaning": "Ежедневно" if "daily_cleaning" in features else "По запросу",
        "location_tags": [code for code in ("city_center", "near_sea", "beachfront") if code in features],
        "private_beach": "private_beach" in features,
        "free_cancellation": "free_cancellation" in features,
        "pay_at_property": "pay_at_property" in features,
    }
