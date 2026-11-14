from __future__ import annotations

import unicodedata
from functools import lru_cache
from typing import Any

import airportsdata


ALIASES = {
    "МОСКВА": "MOW",
    "MOSCOW": "MOW",
    "MOW": "MOW",
    "СТАМБУЛ": "IST",
    "ISTANBUL": "IST",
    "РИМ": "ROM",
    "ROME": "ROM",
    "ПАРИЖ": "PAR",
    "PARIS": "PAR",
    "ДУБАЙ": "DXB",
    "DUBAI": "DXB",
    "ТБИЛИСИ": "TBS",
    "TBILISI": "TBS",
    "НЬЮ-ЙОРК": "NYC",
    "NEW YORK": "NYC",
    "ЛОС-АНДЖЕЛЕС": "LAX",
    "LOS ANGELES": "LAX",
    "ЛОНДОН": "LON",
    "LONDON": "LON",
    "ТОКИО": "TYO",
    "TOKYO": "TYO",
    "БЕРЛИН": "BER",
    "BERLIN": "BER",
    "БАРСЕЛОНА": "BCN",
    "BARCELONA": "BCN",
    "МАДРИД": "MAD",
    "MADRID": "MAD",
    "АМСТЕРДАМ": "AMS",
    "AMSTERDAM": "AMS",
    "ВЕНА": "VIE",
    "VIENNA": "VIE",
    "ПРАГА": "PRG",
    "PRAGUE": "PRG",
    "ЕРЕВАН": "EVN",
    "YEREVAN": "EVN",
    "БАКУ": "GYD",
    "BAKU": "GYD",
    "АСТАНА": "NQZ",
    "ASTANA": "NQZ",
    "ПЕКИН": "PEK",
    "BEIJING": "PEK",
    "ШАНХАЙ": "PVG",
    "SHANGHAI": "PVG",
    "ДЕЛИ": "DEL",
    "DELHI": "DEL",
    "БАНГКОК": "BKK",
    "BANGKOK": "BKK",
    "САНКТ-ПЕТЕРБУРГ": "LED",
    "САНКТ ПЕТЕРБУРГ": "LED",
    "САНКТ ПИТЕРБУРГ": "LED",
    "САНКТ-ПИТЕРБУРГ": "LED",
    "ПИТЕР": "LED",
    "ЛЕНИНГРАД": "LED",
    "СОЧИ": "AER",
}

MULTI_AIRPORT_PREFERRED = {
    "MOW": "SVO",
    "ROM": "FCO",
    "PAR": "CDG",
    "NYC": "JFK",
    "LON": "LHR",
    "TYO": "HND",
}

RUSSIAN_CITY_NAMES = {
    "MOW": "Москва", "IST": "Стамбул", "ROM": "Рим", "PAR": "Париж",
    "DXB": "Дубай", "TBS": "Тбилиси", "NYC": "Нью-Йорк", "LAX": "Лос-Анджелес",
    "LON": "Лондон", "TYO": "Токио", "BER": "Берлин", "BCN": "Барселона",
    "MAD": "Мадрид", "AMS": "Амстердам", "VIE": "Вена", "PRG": "Прага",
    "EVN": "Ереван", "GYD": "Баку", "NQZ": "Астана", "PEK": "Пекин",
    "PVG": "Шанхай", "DEL": "Дели", "BKK": "Бангкок",
    "LED": "Санкт-Петербург", "AER": "Сочи",
}


@lru_cache(maxsize=1)
def iata_airports() -> dict[str, dict[str, Any]]:
    return airportsdata.load("IATA")


def resolve_location(value: str) -> str | None:
    normalized = _normalize(value)
    if not normalized:
        return None
    alias = ALIASES.get(normalized)
    if alias:
        return alias
    if normalized in MULTI_AIRPORT_PREFERRED or normalized in iata_airports():
        return normalized

    candidates = [
        (code, data)
        for code, data in iata_airports().items()
        if _normalize(str(data.get("city", ""))) == normalized
    ]
    if not candidates:
        candidates = [
            (code, data)
            for code, data in iata_airports().items()
            if normalized in _normalize(str(data.get("name", "")))
        ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            "international" not in str(item[1].get("name", "")).casefold(),
            item[0],
        )
    )
    return candidates[0][0]


def suggest_locations(query: str, limit: int = 8) -> list[dict[str, str]]:
    needle = _normalize(query)
    if not needle:
        return []
    capped_limit = max(1, min(limit, 20))
    ranked: list[tuple[int, str, dict[str, str]]] = []
    seen: set[str] = set()

    for code, city in RUSSIAN_CITY_NAMES.items():
        searchable = (_normalize(city), code, *(key for key, value in ALIASES.items() if value == code))
        if not any(needle in value for value in searchable):
            continue
        score = 0 if any(value.startswith(needle) for value in searchable) else 2
        item = {
            "code": code,
            "city": city,
            "airport": "Все аэропорты города" if code in MULTI_AIRPORT_PREFERRED else city,
            "label": f"{city} · {code}",
        }
        ranked.append((score, city, item))
        seen.add(code)

    for code, data in iata_airports().items():
        city = str(data.get("city") or "").strip()
        airport = str(data.get("name") or "").strip()
        values = (_normalize(city), _normalize(airport), code)
        if not any(needle in value for value in values):
            continue
        if code in seen:
            continue
        score = 1 if any(value.startswith(needle) for value in values) else 3
        display_city = RUSSIAN_CITY_NAMES.get(ALIASES.get(_normalize(city), ""), city or airport)
        item = {
            "code": code,
            "city": display_city,
            "airport": airport,
            "label": f"{display_city} · {airport} · {code}",
        }
        ranked.append((score, display_city, item))
        seen.add(code)

    ranked.sort(key=lambda value: (value[0], value[1], value[2]["code"]))
    return [item for _, _, item in ranked[:capped_limit]]


def location_data(code: str) -> dict[str, Any]:
    physical_code = MULTI_AIRPORT_PREFERRED.get(code, code)
    try:
        return iata_airports()[physical_code]
    except KeyError:
        raise ValueError(f"unknown airport: {code}") from None


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_marks.upper().split())
