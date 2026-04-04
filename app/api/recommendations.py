from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["recommendations"])


@router.get(
    "/recommendations",
    summary="Get recommendations",
    description="Returns current recommendations based on latest snapshot and health.",
)
async def get_recommendations():
    from app.main import latest_snapshot, latest_health
    from app.services.recommendations import get_recommendations as compute_recs

    snapshot = latest_snapshot["value"]
    health = latest_health["value"]

    if snapshot is None or health is None:
        return {"data": []}

    recs = compute_recs(snapshot, health)
    return {"data": [r.model_dump() for r in recs]}
