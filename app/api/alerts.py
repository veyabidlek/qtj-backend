from fastapi import APIRouter, Query

from app.schemas.responses import AlertListResponse

router = APIRouter(prefix="/api", tags=["alerts"])


@router.get(
    "/alerts",
    response_model=AlertListResponse,
    summary="Get alerts",
    description="Returns filtered alerts. Both query params optional.",
)
async def get_alerts(
    severity: str | None = Query(None, description="Filter by severity: critical, warning, info"),
    limit: int = Query(50, ge=1, le=500, description="Max number of alerts to return"),
):
    from app.main import latest_alerts

    filtered = latest_alerts
    if severity:
        filtered = [a for a in filtered if a.severity == severity]

    result = filtered[:limit]
    return {
        "data": [a.model_dump(by_alias=True) for a in result]
    }
