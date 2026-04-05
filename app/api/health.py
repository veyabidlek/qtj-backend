from fastapi import APIRouter, Depends

from app.core.security import verify_api_key
from app.schemas.health import HealthIndex

router = APIRouter(prefix="/api", tags=["health"])


@router.get(
    "/health",
    response_model=HealthIndex,
    summary="Get current health index",
    description="Returns current health index computed from the latest telemetry snapshot.",
)
async def get_health():
    from app.main import latest_snapshot, latest_health
    from app.services.health import compute_health

    if latest_health["value"] is not None:
        return latest_health["value"]

    if latest_snapshot["value"] is not None:
        return compute_health(latest_snapshot["value"])

    return HealthIndex(
        score=100,
        grade="A",
        breakdown={"engine": 100, "electrical": 100, "brakes": 100, "fuel": 100},
        top_factors=[],
    )


@router.get(
    "/health/config/reload",
    summary="Reload health config",
    description="Reloads health_config.yaml without restart.",
)
async def reload_health_config(_api_key: str = Depends(verify_api_key)):
    from app.services.health import reload_config

    reload_config()
    return {"message": "Health config reloaded"}
