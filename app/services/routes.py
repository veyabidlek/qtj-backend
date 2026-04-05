from dataclasses import dataclass


ROUTES = {
    "kulsary-astana": {
        "name": "Кульсары-Актау-Алматы-Астана",
        "stations": [
            {"name": "Кульсары", "lat": 46.9667, "lng": 54.0167},
            {"name": "Актау", "lat": 43.6500, "lng": 51.1500},
            {"name": "Алматы", "lat": 43.2380, "lng": 76.9460},
            {"name": "Астана", "lat": 51.1694, "lng": 71.4491},
        ],
        "ticks_per_segment": 60,
        "default": True,
    },
    "astana-almaty": {
        "name": "Астана-Алматы",
        "stations": [
            {"name": "Астана", "lat": 51.1694, "lng": 71.4491},
            {"name": "Юг Астаны", "lat": 50.9983, "lng": 71.3654},
            {"name": "Караганда-1", "lat": 50.5954, "lng": 71.1128},
            {"name": "Караганда-2", "lat": 50.2839, "lng": 70.9536},
            {"name": "Точка 5", "lat": 49.8028, "lng": 70.4567},
            {"name": "Точка 6", "lat": 49.2101, "lng": 69.9345},
            {"name": "Точка 7", "lat": 48.6733, "lng": 69.4012},
            {"name": "Точка 8", "lat": 48.0195, "lng": 68.8234},
            {"name": "Точка 9", "lat": 47.4536, "lng": 68.3456},
            {"name": "Точка 10", "lat": 46.8467, "lng": 67.7892},
            {"name": "Точка 11", "lat": 46.3012, "lng": 67.2345},
            {"name": "Точка 12", "lat": 45.7234, "lng": 66.8901},
            {"name": "Точка 13", "lat": 45.0123, "lng": 76.1234},
            {"name": "Точка 14", "lat": 44.5192, "lng": 76.5678},
            {"name": "Точка 15", "lat": 43.9012, "lng": 76.8234},
            {"name": "Точка 16", "lat": 43.4853, "lng": 76.8901},
            {"name": "Алматы", "lat": 43.2380, "lng": 76.9460},
        ],
        "ticks_per_segment": 20,
        "default": False,
    },
}


STATION_STOP_TICKS = 5  # seconds to stop at each station


@dataclass
class RouteTickResult:
    lat: float
    lng: float
    completed: bool
    current_station_index: int
    current_station_name: str
    next_station_name: str | None
    segment_progress: float  # 0.0-1.0 within current segment
    at_station: bool = False  # True when stopped at a station
    approaching_station: bool = False  # True 5s before arriving at next station


class RouteManager:
    def __init__(self) -> None:
        # Start with the default route
        default_id = next(
            (rid for rid, r in ROUTES.items() if r.get("default")),
            "kulsary-astana",
        )
        self._route_id: str = default_id
        self._route = ROUTES[default_id]
        self._segment_index: int = 0  # which segment (station pair) we're on
        self._tick_in_segment: int = 0
        self._completed: bool = False
        self._stop_ticks_remaining: int = STATION_STOP_TICKS  # start stopped at first station

    @property
    def route_id(self) -> str:
        return self._route_id

    @property
    def completed(self) -> bool:
        return self._completed

    def start(self, route_id: str) -> None:
        if route_id not in ROUTES:
            raise ValueError(f"Unknown route: {route_id}")
        self._route_id = route_id
        self._route = ROUTES[route_id]
        self._segment_index = 0
        self._tick_in_segment = 0
        self._completed = False
        self._stop_ticks_remaining = 0

    def tick(self) -> RouteTickResult:
        stations = self._route["stations"]
        ticks_per_seg = self._route["ticks_per_segment"]
        num_segments = len(stations) - 1

        if self._completed:
            last = stations[-1]
            return RouteTickResult(
                lat=last["lat"],
                lng=last["lng"],
                completed=True,
                current_station_index=len(stations) - 1,
                current_station_name=last["name"],
                next_station_name=None,
                segment_progress=1.0,
                at_station=True,
            )

        # If stopped at a station, count down
        if self._stop_ticks_remaining > 0:
            self._stop_ticks_remaining -= 1
            station = stations[self._segment_index]
            next_station = stations[self._segment_index + 1] if self._segment_index + 1 < len(stations) else None
            return RouteTickResult(
                lat=station["lat"],
                lng=station["lng"],
                completed=False,
                current_station_index=self._segment_index,
                current_station_name=station["name"],
                next_station_name=next_station["name"] if next_station else None,
                segment_progress=0.0,
                at_station=True,
            )

        # Interpolate within current segment
        frac = self._tick_in_segment / max(ticks_per_seg, 1)
        s1 = stations[self._segment_index]
        s2 = stations[self._segment_index + 1]
        lat = s1["lat"] + (s2["lat"] - s1["lat"]) * frac
        lng = s1["lng"] + (s2["lng"] - s1["lng"]) * frac

        current_station_name = s1["name"]
        next_station_name = s2["name"]

        # Check if approaching next station (within 5 ticks)
        ticks_remaining = ticks_per_seg - self._tick_in_segment
        approaching = ticks_remaining <= STATION_STOP_TICKS

        # Advance tick
        self._tick_in_segment += 1
        if self._tick_in_segment >= ticks_per_seg:
            self._tick_in_segment = 0
            self._segment_index += 1
            if self._segment_index >= num_segments:
                # Route finished
                self._completed = True
                self._segment_index = num_segments - 1
                self._tick_in_segment = ticks_per_seg
                last = stations[-1]
                return RouteTickResult(
                    lat=last["lat"],
                    lng=last["lng"],
                    completed=True,
                    current_station_index=len(stations) - 1,
                    current_station_name=last["name"],
                    next_station_name=None,
                    segment_progress=1.0,
                    at_station=True,
                )
            # Arrived at next station — stop for STATION_STOP_TICKS
            self._stop_ticks_remaining = STATION_STOP_TICKS

        return RouteTickResult(
            lat=lat,
            lng=lng,
            completed=False,
            current_station_index=self._segment_index,
            current_station_name=current_station_name,
            next_station_name=next_station_name,
            segment_progress=frac,
            approaching_station=approaching,
        )

    def status(self) -> dict:
        stations = self._route["stations"]
        if self._completed:
            return {
                "route_id": self._route_id,
                "current_station_index": len(stations) - 1,
                "current_station": stations[-1]["name"],
                "next_station": None,
                "progress": 1.0,
                "completed": True,
            }

        num_segments = len(stations) - 1
        ticks_per_seg = self._route["ticks_per_segment"]
        total_ticks = num_segments * ticks_per_seg
        current_tick = self._segment_index * ticks_per_seg + self._tick_in_segment
        overall_progress = current_tick / max(total_ticks, 1)

        next_station = (
            stations[self._segment_index + 1]["name"]
            if self._segment_index + 1 < len(stations)
            else None
        )

        return {
            "route_id": self._route_id,
            "current_station_index": self._segment_index,
            "current_station": stations[self._segment_index]["name"],
            "next_station": next_station,
            "progress": round(overall_progress, 4),
            "completed": False,
        }
