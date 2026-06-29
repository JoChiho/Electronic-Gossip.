"""地点与经纬度预设（真太阳时换算用）。"""

from __future__ import annotations

from dataclasses import dataclass

from bagua.true_solar import default_longitude


# 北纬为正、南纬为负；东经为正、西经为负
@dataclass(frozen=True)
class CityCoord:
    latitude: float
    longitude: float


CITY_COORDS: dict[str, CityCoord] = {
    "北京": CityCoord(39.90, 116.41),
    "上海": CityCoord(31.23, 121.47),
    "广州": CityCoord(23.13, 113.26),
    "深圳": CityCoord(22.55, 114.06),
    "成都": CityCoord(30.57, 104.07),
    "武汉": CityCoord(30.59, 114.31),
    "西安": CityCoord(34.26, 108.94),
    "杭州": CityCoord(30.25, 120.16),
    "南京": CityCoord(32.06, 118.80),
    "重庆": CityCoord(29.56, 106.55),
    "天津": CityCoord(39.13, 117.20),
    "香港": CityCoord(22.32, 114.17),
    "台北": CityCoord(25.03, 121.56),
    "东京": CityCoord(35.68, 139.69),
    "首尔": CityCoord(37.57, 126.98),
    "新加坡": CityCoord(1.35, 103.85),
    "伦敦": CityCoord(51.51, -0.13),
    "巴黎": CityCoord(48.86, 2.35),
    "纽约": CityCoord(40.71, -74.01),
    "洛杉矶": CityCoord(34.05, -118.24),
}

TIMEZONE_DEFAULT_CITY: dict[str, str] = {
    "Asia/Shanghai": "上海",
    "Asia/Hong_Kong": "香港",
    "Asia/Taipei": "台北",
    "Asia/Tokyo": "东京",
    "Asia/Seoul": "首尔",
    "Asia/Singapore": "新加坡",
    "Europe/London": "伦敦",
    "Europe/Paris": "巴黎",
    "America/New_York": "纽约",
    "America/Los_Angeles": "洛杉矶",
    "UTC": "伦敦",
}

LOCATION_FOLLOW_TZ = "（跟随时区默认）"
LOCATION_CUSTOM = "自定义经度"

LOCATION_OPTIONS: list[str] = [LOCATION_FOLLOW_TZ, *CITY_COORDS.keys(), LOCATION_CUSTOM]


def parse_longitude(raw: str) -> float | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def coordinates_for_city(name: str) -> CityCoord | None:
    return CITY_COORDS.get(name)


def longitude_for_city(name: str) -> float | None:
    coord = coordinates_for_city(name)
    return coord.longitude if coord else None


def latitude_for_city(name: str) -> float | None:
    coord = coordinates_for_city(name)
    return coord.latitude if coord else None


def default_city_for_timezone(iana_name: str) -> str:
    return TIMEZONE_DEFAULT_CITY.get(iana_name, "北京")


def infer_location_label(longitude: float | None, iana_name: str) -> str:
    if longitude is None:
        return LOCATION_FOLLOW_TZ
    for name, coord in CITY_COORDS.items():
        if abs(coord.longitude - longitude) < 0.06:
            return name
    return LOCATION_CUSTOM


def resolve_longitude(
    location: str,
    manual_raw: str,
    tz_iana: str,
) -> float | None:
    """
    解析有效经度（真太阳时校正仅使用经度）。

    - 跟随时区默认 → None（由 default_longitude(tz) 推算）
    - 预设城市 → 城市经度
    - 自定义 → 手动输入
    """
    if not location or location == LOCATION_FOLLOW_TZ:
        return None
    preset = longitude_for_city(location)
    if preset is not None:
        return preset
    if location == LOCATION_CUSTOM:
        return parse_longitude(manual_raw)
    return parse_longitude(manual_raw)


def resolve_display_coord(
    location: str,
    manual_lon_raw: str,
    tz_iana: str,
) -> tuple[float, float | None]:
    """返回 (经度, 纬度或 None) 供界面展示。"""
    if not location or location == LOCATION_FOLLOW_TZ:
        lon = default_longitude(tz_iana)
        city = default_city_for_timezone(tz_iana)
        coord = coordinates_for_city(city)
        return lon, coord.latitude if coord else None
    preset = coordinates_for_city(location)
    if preset is not None:
        return preset.longitude, preset.latitude
    manual_lon = parse_longitude(manual_lon_raw)
    lon = manual_lon if manual_lon is not None else default_longitude(tz_iana)
    return lon, None


def format_latitude(lat: float | None) -> str:
    if lat is None:
        return "—"
    if lat >= 0:
        return f"北纬 {lat:.2f}°"
    return f"南纬 {abs(lat):.2f}°"


def format_longitude(lon: float) -> str:
    if lon >= 0:
        return f"东经 {lon:.2f}°"
    return f"西经 {abs(lon):.2f}°"


def display_coord_hint(longitude: float | None, tz_iana: str, latitude: float | None = None) -> str:
    lon = longitude if longitude is not None else default_longitude(tz_iana)
    parts = [format_longitude(lon)]
    if latitude is not None:
        parts.append(format_latitude(latitude))
    return " · ".join(parts)