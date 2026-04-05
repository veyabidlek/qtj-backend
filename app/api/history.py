from datetime import datetime, timezone
from io import StringIO

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.dependencies import DbSession
from app.models.telemetry import TelemetrySnapshot
from app.repositories import telemetry_repo
from app.schemas.responses import HistoryResponse
from app.schemas.telemetry import TelemetrySnapshotSchema, TelemetryPosition

router = APIRouter(prefix="/api", tags=["telemetry"])


def row_to_schema(row: TelemetrySnapshot) -> dict:
    return TelemetrySnapshotSchema(
        timestamp=int(row.timestamp.replace(tzinfo=timezone.utc).timestamp() * 1000),
        speed=row.speed,
        temperature=row.temperature,
        oil_temperature=row.oil_temperature,
        vibration=row.vibration,
        voltage=row.voltage,
        current=row.current_amperage,
        fuel_level=row.fuel_level,
        fuel_consumption=row.fuel_consumption,
        brake_pressure=row.brake_pressure,
        traction_effort=row.traction_effort,
        efficiency=row.efficiency,
        position=TelemetryPosition(lat=row.lat, lng=row.lng),
    ).model_dump(by_alias=True)


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="Get telemetry history",
    description="Returns telemetry snapshots from the last N minutes.",
)
async def get_history(
    db: DbSession,
    minutes: int = Query(15, ge=1, le=1440, description="Number of minutes of history"),
):
    rows = await telemetry_repo.get_history(db, minutes)
    return {"data": [row_to_schema(r) for r in rows]}


@router.get(
    "/history/export",
    summary="Export telemetry as CSV",
    description="Returns CSV file as download.",
)
async def export_history(
    db: DbSession,
    minutes: int = Query(60, ge=1, le=4320, description="Number of minutes to export"),
):
    rows = await telemetry_repo.export_history(db, minutes)

    output = StringIO()
    output.write("timestamp,speed,temperature,oilTemperature,vibration,voltage,current,fuelLevel,fuelConsumption,brakePressure,tractionEffort,efficiency,lat,lng\n")

    for r in rows:
        ts = r.timestamp.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        output.write(
            f"{ts},"
            f"{r.speed:.1f},"
            f"{r.temperature:.1f},"
            f"{r.oil_temperature:.1f},"
            f"{r.vibration:.2f},"
            f"{r.voltage:.1f},"
            f"{r.current_amperage:.0f},"
            f"{r.fuel_level:.1f},"
            f"{r.fuel_consumption:.0f},"
            f"{r.brake_pressure:.3f},"
            f"{r.traction_effort:.0f},"
            f"{r.efficiency:.1f},"
            f"{r.lat:.5f},"
            f"{r.lng:.5f}\n"
        )

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    filename = f"telemetry-export-{now_str}.csv"

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
