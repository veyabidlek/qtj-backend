from fastapi import APIRouter, Query, HTTPException

from app.core.logging import get_logger
from app.dependencies import ApiKey
from app.schemas.responses import RouteSchema, RouteStartResponse, RouteStatusResponse
from app.services.routes import ROUTES

logger = get_logger("locomotive.routes")

router = APIRouter(tags=["routes"])


@router.get(
    "/api/routes",
    response_model=list[RouteSchema],
    summary="List available routes",
    description="Returns all predefined routes with their stations.",
)
async def list_routes():
    return [
        RouteSchema(
            id=route_id,
            name=route["name"],
            stations=route["stations"],
            default=route.get("default", False),
        )
        for route_id, route in ROUTES.items()
    ]


@router.post(
    "/api/route/start",
    response_model=RouteStartResponse,
    summary="Start or restart a route",
    description="Resets the simulator position to the first station of the selected route.",
)
async def start_route(
    _api_key: ApiKey,
    route_id: str = Query(..., description="Route ID to start"),
):
    if route_id not in ROUTES:
        raise HTTPException(status_code=400, detail=f"Unknown route: {route_id}")

    from app.main import simulator_state

    state = simulator_state["instance"]
    if state is None:
        raise HTTPException(status_code=503, detail="Simulator not running")

    state.route_manager.start(route_id)
    state.route_completed = False
    state.reset_to_defaults()

    # Clear in-memory alerts
    from app.main import latest_alerts
    latest_alerts.clear()

    logger.info("route_started", route_id=route_id)
    return RouteStartResponse(message="Route started", route=route_id)


@router.get(
    "/api/route/status",
    response_model=RouteStatusResponse,
    summary="Current route status",
    description="Returns the current route progress, active station, and completion status.",
)
async def route_status():
    from app.main import simulator_state

    state = simulator_state["instance"]
    if state is None:
        raise HTTPException(status_code=503, detail="Simulator not running")

    status = state.route_manager.status()
    return RouteStatusResponse(**status)
