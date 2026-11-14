from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any


class PreliminaryPlanService:
    STRATEGIES = {
        "optimal": ("Оптимальный", 60, "Главные места без перегрузки", "Баланс цены и свободного времени"),
        "comfortable": ("Комфортный", 45, "Больше отдыха и приватный трансфер", "Меньше активностей"),
        "intensive": ("Насыщенный", 45, "Максимум впечатлений", "Плотное расписание"),
        "budget": ("Экономный", 90, "Общественный транспорт и бесплатные места", "Дольше в дороге"),
    }

    def build(self, flight: dict[str, Any], hotel: dict[str, Any]) -> dict[str, Any]:
        arrival = _aware(flight["arrival_at"])
        hotel_in = _aware(hotel["check_in_at"])
        hotel_out = _aware(hotel["check_out_at"])
        if str(flight.get("destination_city", "")).casefold() != str(hotel.get("destination_city", "")).casefold():
            raise ValueError("flight and hotel are in different cities")
        if hotel_out <= arrival:
            raise ValueError("hotel checkout must be after flight arrival")
        variants = [self._variant(key, values, arrival, hotel_in, hotel_out, flight, hotel) for key, values in self.STRATEGIES.items()]
        return {"recommended_strategy": "optimal", "variants": variants}

    def _variant(self, strategy: str, config: tuple[str, int, str, str], arrival: datetime, hotel_in: datetime, hotel_out: datetime, flight: dict[str, Any], hotel: dict[str, Any]) -> dict[str, Any]:
        title, transfer_minutes, advantage, tradeoff = config
        transfer_end = arrival + timedelta(minutes=transfer_minutes)
        check_in_start = max(transfer_end, hotel_in)
        check_in_end = check_in_start + timedelta(minutes=30)
        timeline = [
            _event("transfer", "Трансфер до отеля", arrival, transfer_end, "С багажом и запасом времени"),
            _event("check_in", f"Заселение: {hotel['title']}", check_in_start, check_in_end, "Регистрация и размещение"),
        ]
        cursor = check_in_end
        is_night = arrival.hour >= 22 or arrival.hour < 6
        if is_night:
            rest_end = datetime.combine((arrival + timedelta(days=1)).date(), time(9), tzinfo=arrival.tzinfo)
            if rest_end <= cursor:
                rest_end = cursor + timedelta(hours=8)
            timeline.append(_event("rest", "Отдых после ночного прилёта", cursor, rest_end, "Без мероприятий сразу после рейса"))
            cursor = rest_end
        activity_count = {"comfortable": 1, "optimal": 2, "intensive": 3, "budget": 2}[strategy]
        names = {
            "comfortable": [
                "Неспешная прогулка по центру", "Отдых в городском парке", "Кофейни и локальные десерты",
                "Прогулка у воды", "Спа или бассейн в отеле", "Закат на смотровой площадке",
            ],
            "optimal": [
                "Главные достопримечательности", "Ужин с местной кухней", "Исторический квартал",
                "Музей по интересам", "Городская набережная", "Рынок и гастрономические лавки",
                "Панорамная площадка", "Современный район", "Прогулка по парку", "Свободный вечер",
            ],
            "intensive": [
                "Обзорная экскурсия", "Главный музей города", "Вечерний маршрут", "Архитектурная прогулка",
                "Гастрономический тур", "Панорамная площадка", "Галерея современного искусства",
                "Исторический квартал", "Прогулка у воды", "Местный рынок", "Шоу или концерт",
                "Авторская экскурсия",
            ],
            "budget": [
                "Бесплатная прогулка по центру", "Городской рынок", "Парк и смотровая площадка",
                "Самостоятельный архитектурный маршрут", "Набережная", "Бесплатная выставка",
                "Уличное искусство", "Пикник в парке", "Исторические улицы", "Закат у воды",
            ],
        }[strategy]
        day = cursor.date()
        activity_index = 0
        last_activity_day = (hotel_out - timedelta(days=1)).date()
        while day <= last_activity_day:
            day_cursor = max(cursor, datetime.combine(day, time(10), tzinfo=arrival.tzinfo))
            for index in range(activity_count):
                start = day_cursor + timedelta(minutes=60 if index == 0 else 45)
                end = min(start + timedelta(hours=2), hotel_out - timedelta(hours=2))
                if end > start and start.date() == day:
                    timeline.append(_event("activity", names[activity_index % len(names)], start, end, "Можно заменить под интересы"))
                    day_cursor = end
                    activity_index += 1
            day += timedelta(days=1)
        timeline.append(_event("check_out", f"Выселение: {hotel['title']}", hotel_out - timedelta(minutes=30), hotel_out, "Проверить багаж и трансфер"))
        timeline.sort(key=lambda item: item["start_at"])
        total = round(float(flight.get("price_eur", 0)) + float(hotel.get("total_price_eur", 0)) + {"optimal": 45, "comfortable": 75, "intensive": 60, "budget": 15}[strategy], 2)
        return {
            "strategy": strategy, "title": title, "recommended": strategy == "optimal",
            "estimated_total_eur": total, "advantages": [advantage], "tradeoffs": [tradeoff],
            "timeline": timeline,
        }


def _event(kind: str, title: str, start: datetime, end: datetime, note: str) -> dict[str, Any]:
    return {"kind": kind, "title": title, "start_at": start.isoformat(), "end_at": end.isoformat(), "note": note}


def _aware(value: Any) -> datetime:
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("plan times must be timezone-aware")
    return result
