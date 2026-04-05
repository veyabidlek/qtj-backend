# КТЖ — Цифровой Двойник Локомотива (Backend)

> Deployed at: http://165.22.216.205:8000 | Swagger: http://165.22.216.205:8000/docs

FastAPI backend for real-time locomotive telemetry streaming, health index calculation, and alert management.

## Quick Start (Docker)

```bash
# 1. Start PostgreSQL + Backend
docker-compose up --build

# 2. Verify it's running
curl http://localhost:8000/api/healthz
```

Backend starts at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

The telemetry simulator starts automatically and broadcasts data at 1 Hz via WebSocket.

## Connect Frontend

Add one line to `frontend/.env.local`:

```
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/telemetry
```

Then restart the frontend (`npm run dev`). The dashboard will switch from mock data to the real backend.

## Local Development (without Docker)

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start PostgreSQL (must be running on localhost:5432)
# Update .env:
#   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/locomotive

# 4. Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Test WebSocket

```bash
# Install wscat if needed: npm install -g wscat
wscat -c ws://localhost:8000/ws/telemetry
```

You'll see JSON telemetry snapshots at 1 Hz:

```json
{
  "timestamp": 1712345678000,
  "speed": 81.2,
  "temperature": 72.3,
  "oilTemperature": 85.1,
  "vibration": 2.1,
  "voltage": 25.0,
  "current": 420,
  "fuelLevel": 87.0,
  "fuelConsumption": 180,
  "brakePressure": 0.55,
  "tractionEffort": 220,
  "efficiency": 88.0,
  "position": { "lat": 43.238, "lng": 76.946 }
}
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/ws/telemetry` | Real-time telemetry stream (1 Hz) |
| GET | `/api/health` | Current health index (score, grade, breakdown) |
| GET | `/api/alerts?severity=&limit=50` | Filtered alerts list |
| GET | `/api/recommendations` | Active recommendations |
| GET | `/api/history?minutes=15` | Historical telemetry snapshots |
| GET | `/api/history/export?minutes=60` | CSV export download |
| GET | `/api/config/thresholds` | All threshold configs |
| PUT | `/api/config/thresholds` | Update a parameter's thresholds |
| GET | `/api/healthz` | System health check |

Full OpenAPI docs: `http://localhost:8000/docs`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@db:5432/locomotive` | PostgreSQL connection string |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `SIMULATOR_INTERVAL_MS` | `1000` | Telemetry tick interval (ms) |
| `DB_BATCH_INTERVAL_S` | `5` | Batch DB insert every N ticks |
| `HISTORY_RETENTION_HOURS` | `72` | Auto-delete data older than N hours |
| `LOG_LEVEL` | `INFO` | Logging level |

## Architecture

```
Simulator (1 Hz) → WebSocket Broadcast → Frontend
                 → Batch Insert → PostgreSQL
                 → Alert Check → Alert Storage
                 → Health Index Calculation
```

- **Simulator** runs as a background task in the FastAPI lifespan
- **WebSocket** broadcasts camelCase JSON matching the frontend's TypeScript interfaces
- **Health Index** uses weighted scoring across 4 subsystems (engine 30%, electrical 25%, brakes 25%, fuel 20%)
- **Alerts** check 5 parameters with inverted logic for voltage/fuel
- **DB** stores telemetry in batches (every 5s) and auto-cleans data older than 72h
