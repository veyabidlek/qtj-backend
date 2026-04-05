# КТЖ — Цифровой Двойник Локомотива (Backend)

> **Деплой:** http://165.22.216.205:8000 | **Swagger:** http://165.22.216.205:8000/docs | **WebSocket:** ws://165.22.216.205:8000/ws/telemetry

Full-stack бэкенд для дашборда цифрового двойника локомотива. Агрегирует поток телеметрии в реальном времени, рассчитывает индекс здоровья, генерирует алерты и рекомендации.

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                          │
│                                                                 │
│  ┌───────────┐    ┌──────────────┐    ┌───────────────────┐    │
│  │ Симулятор  │───▶│  Broadcast   │───▶│  WebSocket (WS)   │────────▶ Frontend
│  │  (1 Гц)   │    │  Manager     │    │  /ws/telemetry    │    │
│  └─────┬─────┘    └──────────────┘    └───────────────────┘    │
│        │                                                        │
│        ├──────────▶ Проверка алертов ──▶ In-Memory + PostgreSQL │
│        │                                                        │
│        ├──────────▶ Расчёт индекса здоровья (взвешенная формула)│
│        │                                                        │
│        └──────────▶ Batch Insert (каждые 5с) ──▶ PostgreSQL    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    REST API (/api/*)                      │   │
│  │  health │ alerts │ history │ export │ config │ scenarios  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │                                          │
         ▼                                          ▼
  ┌──────────────┐                        ┌──────────────────┐
  │ PostgreSQL 16│                        │  health_config   │
  │  (Docker)    │                        │    .yaml         │
  │              │                        │ (веса, пороги)   │
  │ - telemetry  │                        └──────────────────┘
  │ - alerts     │
  │ - thresholds │
  └──────────────┘
```

### Слоистая архитектура (Layered Architecture)

```
API (app/api/)          ← Тонкие обработчики, валидация, маршрутизация
    ↓
Services (app/services/) ← Бизнес-логика: симулятор, здоровье, алерты
    ↓
Repositories (app/repositories/) ← Запросы к БД, изоляция от ORM
    ↓
Database (app/core/database.py)  ← SQLAlchemy 2.0 async + asyncpg
```

### Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Фреймворк | FastAPI 0.115+ |
| Runtime | Python 3.11+, uvicorn |
| База данных | PostgreSQL 16 (Docker) |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| Миграции | Alembic |
| Валидация | Pydantic V2 |
| Логирование | structlog (JSON) |
| Rate Limiting | slowapi |
| Конфигурация | Pydantic Settings + .env |
| Контейнеризация | Docker, Docker Compose |
| CI/CD | GitHub Webhook → авто-деплой |

---

## Функциональные возможности

### 1. Телеметрия в реальном времени
- Симулятор генерирует 11 параметров локомотива с частотой 1 Гц
- Поток данных по WebSocket (`ws://host/ws/telemetry`)
- camelCase JSON, совместимый с фронтенд TypeScript интерфейсами
- Heartbeat: ping каждые 30с, отключение при отсутствии pong за 60с

### 2. Индекс здоровья
- Взвешенная формула по 4 подсистемам:
  - Двигатель (30%): температура, масло, вибрация
  - Электрика (25%): напряжение, ток, КПД
  - Тормоза (25%): давление тормозной системы
  - Топливо (20%): уровень топлива
- Оценка 0–100, грейд A–E
- Top-5 факторов с наибольшим влиянием
- Конфигурация через `health_config.yaml` без перекомпиляции

### 3. Система алертов
- Проверка всех 11 параметров по порогам из БД
- Severity: `critical`, `warning`, `info`
- Коды ошибок: E-101 (температура), E-201 (вибрация), E-301 (напряжение), E-401 (топливо), E-501 (тормоза), E-601 (скорость) и др.
- Хранение в PostgreSQL

### 4. Сценарии симуляции
| Сценарий | Описание |
|----------|----------|
| `normal` | Стабильный ход, малый шум |
| `overheat` | Температура двигателя постепенно растёт |
| `brake_failure` | Давление тормозов падает |
| `low_fuel` | Уровень топлива снижается |
| `highload` | 10x частота сообщений (100мс) |
| `demo` | Цикл: нормальный → перегрев → тормоза → восстановление |

### 5. Маршрут Астана → Алматы
- 17 реальных GPS-точек вдоль железнодорожной линии
- Локомотив движется по маршруту и разворачивается на конечных точках

### 6. Хранение и история
- Batch-вставка телеметрии каждые 5 секунд
- Автоочистка данных старше 72 часов
- REST API для исторических данных и экспорта CSV

---

## Быстрый старт (Docker)

```bash
# 1. Клонировать репозиторий
git clone https://github.com/veyabidlek/qtj-backend.git
cd qtj-backend

# 2. Создать .env файл
cp .env.example .env

# 3. Запустить PostgreSQL + Backend
docker-compose up --build

# 4. Проверить работоспособность
curl http://localhost:8000/api/healthz
```

Swagger документация: `http://localhost:8000/docs`

## Подключение фронтенда

Добавить в `frontend/.env.local`:

```
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/telemetry
```

Перезапустить фронтенд (`npm run dev`). Дашборд переключится с мок-данных на реальный бэкенд.

---

## API Endpoints

### WebSocket

| Протокол | Путь | Описание |
|----------|------|----------|
| WS | `/ws/telemetry` | Поток телеметрии в реальном времени (1 Гц) |

### REST API

| Метод | Путь | Описание | Авторизация |
|-------|------|----------|-------------|
| GET | `/api/health` | Текущий индекс здоровья (оценка, грейд, разбивка) | — |
| GET | `/api/health/config/reload` | Перезагрузка health_config.yaml | X-API-Key |
| GET | `/api/alerts?severity=&limit=50` | Список алертов с фильтрацией | — |
| GET | `/api/recommendations` | Активные рекомендации | — |
| GET | `/api/history?minutes=15` | Историческая телеметрия | — |
| GET | `/api/history/export?minutes=60` | Экспорт в CSV | — |
| GET | `/api/config/thresholds` | Конфигурация порогов | — |
| PUT | `/api/config/thresholds` | Обновление порогов | X-API-Key |
| GET | `/api/scenarios` | Список сценариев | — |
| POST | `/api/scenario?scenario=demo` | Переключение сценария | X-API-Key |
| GET | `/api/healthz` | Проверка состояния системы | — |

Полная OpenAPI документация: `/docs`

### Формат WebSocket сообщения

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
  "position": { "lat": 51.169, "lng": 71.449 }
}
```

---

## Схема базы данных

### telemetry_snapshots
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | BIGSERIAL PK | Автоинкремент |
| timestamp | TIMESTAMPTZ | Время снимка |
| speed | DOUBLE | Скорость (км/ч) |
| temperature | DOUBLE | Температура двигателя (°C) |
| oil_temperature | DOUBLE | Температура масла (°C) |
| vibration | DOUBLE | Вибрация |
| voltage | DOUBLE | Напряжение (В) |
| current_amperage | DOUBLE | Ток (А) |
| fuel_level | DOUBLE | Уровень топлива (%) |
| fuel_consumption | DOUBLE | Расход топлива |
| brake_pressure | DOUBLE | Давление тормозов |
| traction_effort | DOUBLE | Тяговое усилие |
| efficiency | DOUBLE | КПД (%) |
| lat, lng | DOUBLE | GPS координаты |
| updated_at | TIMESTAMPTZ | Время обновления |

Индекс: `idx_telemetry_timestamp` на `timestamp DESC`

### alerts
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | UUID PK | Уникальный идентификатор |
| timestamp | TIMESTAMPTZ | Время алерта |
| severity | VARCHAR(10) | critical / warning / info |
| message | TEXT | Описание |
| parameter | VARCHAR(50) | Параметр |
| value | DOUBLE | Текущее значение |
| threshold | DOUBLE | Пороговое значение |
| error_code | VARCHAR(10) | Код ошибки (E-101, E-201...) |

### threshold_config
| Колонка | Тип | Описание |
|---------|-----|----------|
| parameter | VARCHAR(50) PK | Имя параметра |
| min_value | DOUBLE | Минимум |
| max_value | DOUBLE | Максимум |
| warning_value | DOUBLE | Порог предупреждения |
| critical_value | DOUBLE | Критический порог |

---

## Формула индекса здоровья

```
Общий индекс = engine_score × 0.30 + electrical_score × 0.25 + brakes_score × 0.25 + fuel_score × 0.20

engine_score = avg(temperature_score, oil_temperature_score, vibration_score)
electrical_score = avg(voltage_score, current_score, efficiency_score)
brakes_score = brake_pressure_score
fuel_score = fuel_level_score

Каждый параметр оценивается 0–100 на основе расстояния от порогов warning/critical.

Грейд: A (≥80), B (≥60), C (≥40), D (≥20), E (<20)
```

Конфигурация весов и порогов в `health_config.yaml` — изменения без перекомпиляции.

---

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `DATABASE_URL` | `postgresql+asyncpg://...@db:5432/locomotive` | Строка подключения к PostgreSQL |
| `ENVIRONMENT` | `development` | Окружение (development / production) |
| `CORS_ORIGINS` | `http://localhost:3000` | Разрешённые origins (через запятую) |
| `SIMULATOR_INTERVAL_MS` | `1000` | Интервал тиков симулятора (мс) |
| `DB_BATCH_INTERVAL_S` | `5` | Интервал batch-записи в БД (с) |
| `HISTORY_RETENTION_HOURS` | `72` | Автоудаление данных старше N часов |
| `LOG_LEVEL` | `INFO` | Уровень логирования |
| `SIMULATOR_SCENARIO` | `normal` | Начальный сценарий симуляции |
| `API_KEY` | `dev-api-key` | Ключ для защищённых эндпоинтов |

---

## Безопасность

- **API Key** аутентификация через заголовок `X-API-Key` для админ-эндпоинтов
- **CORS** ограничен конкретными origin
- **Rate Limiting** — 100 запросов/минуту на IP
- **Валидация** — Pydantic V2 на входе, SQLAlchemy параметризованные запросы
- **Секреты** — через переменные окружения, не в коде

---

## Тестирование

```bash
# Запуск тестов
python -m pytest tests/ -v
```

25 тестов покрывают:
- Расчёт индекса здоровья (нормальные, критические, граничные значения)
- Генерация алертов (все 11 параметров, severity)
- Симулятор (начальное состояние, диапазоны, сценарии)

---

## CI/CD

GitHub Webhook → автоматический деплой при пуше в `main`:
1. GitHub отправляет webhook на сервер
2. Сервер выполняет `git pull`
3. Docker Compose пересобирает и перезапускает контейнеры
4. Бэкенд доступен через ~30 секунд

---

## Структура проекта

```
qtj-backend/
├── app/
│   ├── main.py                 # FastAPI app, lifespan, CORS
│   ├── config.py               # Pydantic Settings
│   ├── dependencies.py         # Shared Depends (DbSession, ApiKey)
│   ├── api/                    # Обработчики маршрутов
│   │   ├── websocket.py        # WebSocket /ws/telemetry
│   │   ├── health.py           # GET /api/health
│   │   ├── alerts.py           # GET /api/alerts
│   │   ├── history.py          # GET /api/history, export
│   │   ├── config.py           # GET/PUT /api/config/thresholds
│   │   ├── recommendations.py  # GET /api/recommendations
│   │   └── system.py           # GET /api/healthz, scenarios
│   ├── services/               # Бизнес-логика
│   │   ├── simulator.py        # Генератор телеметрии
│   │   ├── health.py           # Расчёт индекса здоровья
│   │   ├── alerts.py           # Проверка порогов
│   │   ├── broadcast.py        # WebSocket менеджер
│   │   └── recommendations.py  # Рекомендации
│   ├── repositories/           # Запросы к БД
│   │   ├── telemetry_repo.py
│   │   ├── alert_repo.py
│   │   └── health_config_repo.py
│   ├── models/                 # SQLAlchemy ORM модели
│   │   ├── telemetry.py
│   │   ├── alert.py
│   │   └── threshold.py
│   ├── schemas/                # Pydantic схемы
│   │   ├── telemetry.py
│   │   ├── health.py
│   │   └── responses.py
│   ├── core/                   # Инфраструктура
│   │   ├── database.py         # Async engine, session
│   │   ├── security.py         # API Key auth
│   │   ├── exceptions.py       # Кастомные исключения
│   │   └── logging.py          # structlog конфигурация
│   └── utils/
│       └── math.py             # clamp()
├── alembic/                    # Миграции БД
├── tests/                      # Тесты (pytest)
├── health_config.yaml          # Конфигурация индекса здоровья
├── Dockerfile                  # Multi-stage сборка
├── docker-compose.yml          # PostgreSQL + Backend
├── requirements.txt
└── .env.example
```
