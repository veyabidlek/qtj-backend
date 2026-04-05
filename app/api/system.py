import logging

from fastapi import APIRouter, Depends, Query

from app.core.security import verify_api_key

logger = logging.getLogger("locomotive")

router = APIRouter(tags=["system"])

VALID_SCENARIOS = ["normal", "overheat", "brake_failure", "low_fuel", "highload", "demo"]


@router.get(
    "/api/healthz",
    summary="Health check",
    description="Returns system health status.",
)
async def healthz():
    from app.main import simulator_running, simulator_state
    from app.api.websocket import manager

    db_status = "connected"
    try:
        from sqlalchemy import text
        from app.core.database import async_session
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    state = simulator_state["instance"]

    return {
        "status": "ok",
        "db": db_status,
        "simulator": "running" if simulator_running["value"] else "stopped",
        "scenario": state.scenario if state else "unknown",
        "clients": manager.client_count,
    }


@router.post(
    "/api/scenario",
    summary="Switch simulator scenario",
    description=f"Switch the simulator scenario. Valid values: {', '.join(VALID_SCENARIOS)}",
)
async def set_scenario(
    scenario: str = Query(..., description="Scenario name"),
    _api_key: str = Depends(verify_api_key),
):
    from app.main import simulator_state

    if scenario not in VALID_SCENARIOS:
        return {"error": f"Invalid scenario. Must be one of: {VALID_SCENARIOS}"}

    state = simulator_state["instance"]
    if state is None:
        return {"error": "Simulator not running"}

    state.scenario = scenario
    state.tick_count = 0
    logger.info("Scenario switched to: %s", scenario)

    return {"scenario": scenario, "message": f"Switched to '{scenario}'"}


@router.get(
    "/api/scenarios",
    summary="List available scenarios",
    description="Returns all available simulator scenarios.",
)
async def list_scenarios():
    return {
        "scenarios": [
            {"id": "normal", "name": "Нормальный режим", "description": "Штатная работа, параметры в норме"},
            {"id": "overheat", "name": "Перегрев", "description": "Температура двигателя растёт, КПД падает"},
            {"id": "brake_failure", "name": "Отказ тормозов", "description": "Давление в тормозной магистрали падает"},
            {"id": "low_fuel", "name": "Низкое топливо", "description": "Топливо расходуется в 10x быстрее"},
            {"id": "highload", "name": "Высокая нагрузка", "description": "Все параметры под нагрузкой, скорость растёт"},
            {"id": "demo", "name": "Демо-режим", "description": "Циклическая смена фаз: норма → перегрев → тормоза → восстановление (2 мин цикл)"},
        ]
    }
