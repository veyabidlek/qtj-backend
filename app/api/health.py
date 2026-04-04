from fastapi import APIRouter

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
