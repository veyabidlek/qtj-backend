import asyncio
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import AppException
from app.core.database import engine, Base, async_session
from app.models.telemetry import TelemetrySnapshot
from app.models.alert import Alert
from app.models.threshold import ThresholdConfig
from app.repositories import telemetry_repo, alert_repo, health_config_repo
from app.services.simulator import SimulatorState
from app.services.alerts import check_alerts, DEFAULT_THRESHOLDS
from app.services.broadcast import ConnectionManager
from app.api.websocket import router as ws_router, manager
from app.api.health import router as health_router
from app.api.alerts import router as alerts_router
from app.api.history import router as history_router
from app.api.recommendations import router as recommendations_router
from app.api.config import router as config_router
from app.api.system import router as system_router
from app.api.routes import router as routes_router

setup_logging()
logger = get_logger("locomotive")

THRESHOLD_SEED_DATA = [
    {"parameter": "speed", "min_value": 0, "max_value": 200, "warning_value": 160, "critical_value": 180},
    {"parameter": "temperature", "min_value": 0, "max_value": 120, "warning_value": 95, "critical_value": 105},
    {"parameter": "oil_temperature", "min_value": 0, "max_value": 150, "warning_value": 110, "critical_value": 130},
    {"parameter": "vibration", "min_value": 0, "max_value": 10, "warning_value": 5, "critical_value": 7},
    {"parameter": "voltage", "min_value": 20, "max_value": 30, "warning_value": 22, "critical_value": 21},
    {"parameter": "current", "min_value": 0, "max_value": 1000, "warning_value": 800, "critical_value": 900},
    {"parameter": "fuel_level", "min_value": 0, "max_value": 100, "warning_value": 25, "critical_value": 10},
    {"parameter": "fuel_consumption", "min_value": 0, "max_value": 500, "warning_value": 350, "critical_value": 420},
    {"parameter": "brake_pressure", "min_value": 0, "max_value": 1.0, "warning_value": 0.3, "critical_value": 0.15},
    {"parameter": "traction_effort", "min_value": 0, "max_value": 500, "warning_value": 400, "critical_value": 450},
    {"parameter": "efficiency", "min_value": 0, "max_value": 100, "warning_value": 60, "critical_value": 40},
]

# Shared state for latest snapshot (used by REST endpoints)
latest_snapshot = {"value": None}
latest_health = {"value": None}
latest_alerts: list = []
simulator_running = {"value": False}

# Thresholds loaded from DB, used by check_alerts
_db_thresholds: dict[str, dict[str, float]] | None = None

# Track previous health grade to log changes
_previous_grade: str | None = None


async def load_thresholds_from_db() -> dict[str, dict[str, float]]:
    """Load thresholds from DB and convert to dict format for check_alerts."""
    try:
        async with async_session() as session:
            rows = await health_config_repo.get_all_thresholds(session)
            return {
                row.parameter: {"warning": row.warning_value, "critical": row.critical_value}
                for row in rows
            }
    except Exception as e:
        logger.error("threshold_load_failed", error=str(e), fallback="defaults")
        return DEFAULT_THRESHOLDS


async def seed_threshold_config() -> None:
    async with async_session() as session:
        await health_config_repo.seed_thresholds(session, THRESHOLD_SEED_DATA)
        logger.info("threshold_seed_complete")


# Shared simulator state — accessible for scenario switching
simulator_state: dict[str, SimulatorState | None] = {"instance": None}


async def simulator_loop(mgr: ConnectionManager) -> None:
    global _db_thresholds, _previous_grade
    from app.services.health import compute_health

    state = SimulatorState(scenario=settings.simulator_scenario)
    simulator_state["instance"] = state
    db_buffer: list[dict] = []
    batch_size = settings.db_batch_interval_s
    simulator_running["value"] = True

    # Load thresholds from DB
    _db_thresholds = await load_thresholds_from_db()

    while True:
        try:
            # When route is completed, keep broadcasting last snapshot (frozen)
            if state.route_completed:
                if latest_snapshot["value"] is not None:
                    json_str = latest_snapshot["value"].model_dump_json(by_alias=True)
                    await mgr.broadcast(json_str)
                await asyncio.sleep(settings.simulator_interval_ms / 1000.0)
                continue

            snapshot = state.next_tick()
            latest_snapshot["value"] = snapshot

            health = compute_health(snapshot)
            latest_health["value"] = health

            # Log health grade changes
            if _previous_grade is not None and health.grade != _previous_grade:
                logger.info(
                    "health_grade_changed",
                    previous_grade=_previous_grade,
                    new_grade=health.grade,
                    score=health.score,
                )
            _previous_grade = health.grade

            alerts = check_alerts(snapshot, _db_thresholds)
            if alerts:
                latest_alerts.extend(alerts)
                # Keep only last 200 alerts in memory
                if len(latest_alerts) > 200:
                    del latest_alerts[:-200]

                logger.info("alerts_generated", count=len(alerts))

                # Store alerts in DB
                try:
                    async with async_session() as session:
                        for a in alerts:
                            await alert_repo.insert_alert(session, {
                                "timestamp": datetime.fromtimestamp(a.timestamp / 1000, tz=timezone.utc),
                                "severity": a.severity,
                                "message": a.message,
                                "parameter": a.parameter,
                                "value": a.value,
                                "threshold": a.threshold,
                                "error_code": a.error_code,
                            })
                        await session.commit()
                except Exception as e:
                    logger.error("alert_store_failed", error=str(e))

            json_str = snapshot.model_dump_json(by_alias=True)
            await mgr.broadcast(json_str)

            db_buffer.append({
                "timestamp": datetime.fromtimestamp(snapshot.timestamp / 1000, tz=timezone.utc),
                "speed": snapshot.speed,
                "temperature": snapshot.temperature,
                "oil_temperature": snapshot.oil_temperature,
                "vibration": snapshot.vibration,
                "voltage": snapshot.voltage,
                "current_amperage": snapshot.current,
                "fuel_level": snapshot.fuel_level,
                "fuel_consumption": snapshot.fuel_consumption,
                "brake_pressure": snapshot.brake_pressure,
                "traction_effort": snapshot.traction_effort,
                "efficiency": snapshot.efficiency,
                "lat": snapshot.position.lat,
                "lng": snapshot.position.lng,
            })

            if len(db_buffer) >= batch_size:
                try:
                    async with async_session() as session:
                        await telemetry_repo.insert_batch(session, db_buffer)
                except Exception as e:
                    logger.error("telemetry_batch_insert_failed", error=str(e))
                db_buffer.clear()

        except Exception as e:
            logger.error("simulator_tick_error", error=str(e))

        await asyncio.sleep(settings.simulator_interval_ms / 1000.0)


async def cleanup_old_data() -> None:
    while True:
        await asyncio.sleep(3600)  # every hour
        try:
            async with async_session() as session:
                await telemetry_repo.delete_old(session, settings.history_retention_hours)
            async with async_session() as session:
                await alert_repo.delete_old(session, settings.history_retention_hours)
            logger.info("data_cleanup_complete", retention_hours=settings.history_retention_hours)
        except Exception as e:
            logger.error("data_cleanup_error", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — retry DB connection (Docker DNS may not be ready immediately)
    for attempt in range(1, 11):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("database_tables_created")
            break
        except Exception as e:
            logger.warning("db_connection_attempt_failed", attempt=attempt, error=str(e))
            if attempt == 10:
                raise
            await asyncio.sleep(2)

    await seed_threshold_config()

    sim_task = asyncio.create_task(simulator_loop(manager))
    cleanup_task = asyncio.create_task(cleanup_old_data())
    logger.info("startup_complete", tasks=["simulator", "cleanup"])

    yield

    # Shutdown
    sim_task.cancel()
    cleanup_task.cancel()
    simulator_running["value"] = False
    logger.info("shutdown_complete")


# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

app = FastAPI(
    title="КТЖ — Цифровой Двойник Локомотива",
    description="API для мониторинга телеметрии локомотива в реальном времени",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = settings.cors_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "message": exc.message, "details": exc.details},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        path=str(request.url),
        method=request.method,
        traceback=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "message": "An unexpected error occurred", "details": {}},
    )


app.include_router(ws_router)
app.include_router(health_router)
app.include_router(alerts_router)
app.include_router(history_router)
app.include_router(recommendations_router)
app.include_router(config_router)
app.include_router(system_router)
app.include_router(routes_router)
