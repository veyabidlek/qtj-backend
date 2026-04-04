from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get(
    "/api/healthz",
    summary="Health check",
    description="Returns system health status.",
)
async def healthz():
    from app.main import simulator_running
    from app.api.websocket import manager

    db_status = "connected"
    try:
        from sqlalchemy import text
        from app.core.database import async_session
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok",
        "db": db_status,
        "simulator": "running" if simulator_running["value"] else "stopped",
        "clients": manager.client_count,
    }
