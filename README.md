# IoT Telemetry – gRPC + REST + MQTT (Full Stack)

This repo contains **two complementary projects**:

1) **Data Manager (Project 1)** — Python **gRPC** service + **.NET REST Gateway** + **PostgreSQL** + optional **CSV sensor generator**.  
2) **Event Manager (Project 2)** — **MQTT** streaming pipeline with **Eclipse Mosquitto**, a **publisher** (Data Manager), and an **Event Manager** microservice that detects events and republishes them. Includes **AsyncAPI documents**.

---

## 🏗️ System Architecture

```
┌─────────────────┐   CSV Stream   ┌─────────────────┐   HTTP/REST   ┌─────────────────┐    gRPC     ┌─────────────────┐
│ Sensor Data     │──────────────► │ Sensor Gen      │──────────────►│ .NET Gateway    │───────────►│ Python gRPC     │
│ (F1 Telemetry)  │                │ (Python)        │               │ (Port 5000)     │           │ Data Manager     │
└─────────────────┘                └─────────────────┘               └─────────────────┘           └─────────────────┘
                                                                                 │
                                                                                 │ publishes MQTT
                                                                                 ▼
                                                                   ┌────────────────────────┐
                                                                   │   Eclipse Mosquitto   │
                                                                   │   (1883 / 9001 WS)    │
                                                                   └──────────┬────────────┘
                                                                              │ subscribes `telemetry/raw`
                                                                              ▼
                                                                  ┌─────────────────────────┐
                                                                  │   Event Manager (Py)   │
                                                                  │   detects & publishes  │
                                                                  │   to `telemetry/events`│
                                                                  └─────────────────────────┘

Data: PostgreSQL (telemetry). Docs: Swagger (REST), AsyncAPI (MQTT).
```

---

## 📦 Services (docker-compose)

- **postgres**: PostgreSQL 15 (port **5432**).
- **datamanager**: Python gRPC service (port **50051**). Publishes raw telemetry to MQTT topic **`telemetry/raw`**.
- **gateway**: .NET 8 REST API Gateway (host port **5000** → container 8080). Docs at **`http://localhost:5000`**.
- **sensorgen**: Python CSV streamer (optional). Reads `data/f1_telemetry_wide.csv` and POST‑uje ka gateway‑u.
- **mqtt**: Eclipse Mosquitto broker (ports **1883** MQTT, **9001** WebSocket). Config at `mosquitto/mosquitto.conf`.
- **eventmanager**: Python MQTT worker that subscribes to **`telemetry/raw`**, detektuje evente i publish‑uje na **`telemetry/events`**.
- **mqttweb**: Minimal web MQTT klijent (served on **http://localhost:8081**) za test preko WebSocket‑a.

> 🔐 MQTT env (prekonfigurisano u compose): `MQTT_HOST=mqtt`, `MQTT_PORT=1883`, topic‑ovi: `telemetry/raw`, `telemetry/events`, QoS=1.

---

## 🚀 Quick Start

### A) Pokreni sve
```bash
docker-compose up -d --build
# Swagger (REST): http://localhost:5000
# MQTT broker: tcp://localhost:1883 , WS: ws://localhost:9001
# Web MQTT client: http://localhost:8081
```

### B) Praćenje logova
```bash
docker-compose logs -f gateway
docker-compose logs -f datamanager
docker-compose logs -f sensorgen
docker-compose logs -f mqtt
docker-compose logs -f eventmanager
```

### C) Samo jezgro (bez sensorgen)
```bash
docker-compose up -d postgres mqtt datamanager gateway eventmanager mqttweb
```

---

## 🌐 REST API (.NET Gateway)

| Method | Endpoint | Description | Query |
|---|---|---|---|
| GET | `/api/telemetry` | List with pagination | `driver`, `lap`, `page`, `pageSize` |
| GET | `/api/telemetry/{id}` | Get by id | - |
| POST | `/api/telemetry` | Create telemetry | body |
| PUT | `/api/telemetry/{id}` | Update telemetry | body |
| DELETE | `/api/telemetry/{id}` | Delete | - |
| GET | `/api/telemetry/aggregate` | MIN/MAX/AVG/SUM | `field`, `type`, `driver`, `lap`, `from`, `to` |

**OpenAPI/Swagger**: `http://localhost:5000`  
OpenAPI spec file: `openapi/swagger.json` (if present).

---

## 🔧 gRPC (Python Data Manager)

- Protobuf: [`telemetry.proto`](telemetry.proto)
- Port: **50051**

Glavne RPC metode:
- `CreateTelemetry`, `GetTelemetry`, `UpdateTelemetry`, `DeleteTelemetry`
- `ListTelemetry` (paginacija)
- `Aggregate` (MIN/MAX/AVG/SUM)

Publikovanje na MQTT: Data Manager nakon uspešnog čuvanja **publikuje sirovu telemetriju** na topic **`telemetry/raw`**.

---

## 📡 MQTT (Project 2 – Mosquitto + Event Manager)

### Topic‑ovi
- **`telemetry/raw`** — sirove poruke (kreira Data Manager posle REST/gRPC inserta).
- **`telemetry/events`** — događaji detektovani od strane Event Manager‑a (npr. `speeding`, `harshBraking`, `highRPM`, `drsActive`).

### Portovi
- MQTT TCP: **1883**
- MQTT WebSocket: **9001** (za web klijent na `http://localhost:8081`)

### Web test klijent
- `mqtt-webclient/index.html` (serviran preko **mqttweb** servisa) – povezuje se na `ws://localhost:9001`, subscribe‑uj na `telemetry/raw` i `telemetry/events` i gledaj poruke u realnom vremenu.

### Konfiguracija brokera
- `mosquitto/mosquitto.conf` (mount‑ovan u container).

### Event Manager mikroservis
- Kod: `eventmanager-py/event_manager.py`  
  - Subscribuje **`telemetry/raw`**  
  - Normalizuje timestamp, detektuje pragove (npr. **Speed > 300 km/h**, **RPM > 10000**, **Brake true + visoka brzina**…)  
  - Publikuje strukturisane događaje na **`telemetry/events`**

Primer izlazne poruke (skraćeno):
```json
{
  "type": "speeding",
  "driver": "Max Verstappen",
  "lapNumber": 5,
  "timestampUtc": "2025-08-17T14:30:15.123Z",
  "speed": 307.4,
  "details": { "threshold": 300.0 }
}
```

---

## 🧪 Testiranje

### 1) Stream CSV → REST → gRPC → DB → MQTT
```bash
docker-compose up -d postgres mqtt datamanager gateway
docker-compose run --rm sensorgen python send_stream.py   --path /data/f1_telemetry_wide.csv   --base-url http://gateway:8080   --rate 100 --burst 20 --limit 1000
```

Očekuj:
- `gateway` loguje REST zahteve
- `datamanager` pozive ka gRPC i publish na `telemetry/raw`
- `eventmanager` subscribuje i emituje na `telemetry/events`

### 2) Provera REST‑a (curl)
```bash
curl "http://localhost:5000/api/telemetry?page=1&pageSize=10"
curl "http://localhost:5000/api/telemetry/aggregate?field=SPEED&type=MAX"
```

### 3) Provera MQTT‑a (CLI)
```bash
# install mosquitto-clients locally if needed
mosquitto_sub -h localhost -p 1883 -t telemetry/raw -v
mosquitto_sub -h localhost -p 1883 -t telemetry/events -v
```

---

## 📊 Data Model & Validacija

```json
{
  "id": 1,
  "driver": "Lewis Hamilton",
  "timestampUtc": "2024-08-17T14:30:00Z",
  "lapNumber": 15,
  "x": 1250.5,
  "y": 800.2,
  "speed": 285.7,
  "throttle": 98.5,
  "brake": false,
  "nGear": 7,
  "rpm": 8500,
  "drs": true
}
```
**Rules:** Driver (<=100), Speed (0–400), Throttle (0–100), Lap (1–100), NGear (‑1..8), RPM (0–20000), ISO 8601 timestamp.

---

## 📁 Repo Structure (key parts)

```
IOT/
├─ docker-compose.yml
├─ telemetry.proto
├─ data/
│  └─ f1_telemetry_wide.csv
├─ asyncapi/
│  ├─ telemetry-publish.yaml    # Publisher spec (Data Manager → telemetry/raw)
│  └─ eventmanager.yaml         # Consumer+Producer spec (raw → events)
├─ mosquitto/
│  └─ mosquitto.conf
├─ mqtt-webclient/
│  └─ index.html                # Simple WS MQTT client (http://localhost:8081)
├─ datamanager-py/
│  ├─ app.py                    # gRPC server + DB + MQTT publish
│  ├─ mqtt_client.py            # MQTT helper (paho-mqtt)
│  ├─ requirements.txt
│  └─ Dockerfile
└─ eventmanager-py/
   ├─ event_manager.py          # Sub telemetry/raw → publish telemetry/events
   ├─ requirements.txt
   └─ Dockerfile
```

---

## 📚 Documentation

### OpenAPI (REST)
- **Location**: `openapi/swagger.json` (if included) or live at **`http://localhost:5000`**

### AsyncAPI (MQTT) ✅
- **Location in repo**: `asyncapi/telemetry-publish.yaml`, `asyncapi/eventmanager.yaml`
- **How to view**:
  - Drag‑and‑drop a YAML into **AsyncAPI Studio** (web UI), or
  - Use **@asyncapi/cli** locally to render docs / generate code:
    ```bash
    npm i -g @asyncapi/cli
    asyncapi validate asyncapi/telemetry-publish.yaml
    asyncapi validate asyncapi/eventmanager.yaml
    asyncapi render asyncapi/eventmanager.yaml -o ./docs/eventmanager.html
    ```

---

## 🎯 Production Notes
- **Auth** for REST and MQTT (username/password or JWT over WS).
- **Observability**: health checks, metrics, structured logs.
- **Scaling**: gateway horizontal scale; MQTT broker clustering; DB pooling.
- **Resilience**: retries/backoff for MQTT client; DLQ/parking topic (e.g., `telemetry/dlq`).
- **Data**: bulk inserts for large CSV, proper indexes for queries; retention policies for events.
- **Versioning**: REST v1/v2; topic versioning (`telemetry/raw/v1`).

---

**Quick demo path**: `docker-compose up -d --build` → open **Swagger** at `http://localhost:5000` → open **Web MQTT** at `http://localhost:8081` → watch `telemetry/events` while streaming CSV.


---

## 🧰 Alternative: Individual `docker run` (shared bridge network)

Ako želiš bez Compose‑a, pokreni svaki servis posebno na zajedničkoj mreži.

### 1) Kreiraj mrežu
```bash
docker network create iotnet
```

### 2) PostgreSQL
```bash
docker run -d \
  --name iot-postgres \
  --network iotnet \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=telemetry \
  -p 5432:5432 \
  -v iot-pgdata:/var/lib/postgresql/data \
  postgres:15
```

### 3) MQTT broker (Eclipse Mosquitto)
```bash
docker run -d \
  --name iot-mqtt \
  --network iotnet \
  -p 1883:1883 \
  -p 9001:9001 \
  -v "$PWD/mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro" \
  eclipse-mosquitto:2
```

### 4) Data Manager (Python gRPC)
```bash
# iz root foldera
docker build -t iot-datamanager ./datamanager-py

docker run -d \
  --name iot-datamanager \
  --network iotnet \
  -e POSTGRES_HOST=iot-postgres \
  -e POSTGRES_DB=telemetry \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e MQTT_HOST=iot-mqtt \
  -e MQTT_PORT=1883 \
  -e MQTT_TOPIC_RAW=telemetry/raw \
  -p 50051:50051 \
  iot-datamanager
```

### 5) .NET Gateway (REST)
```bash
docker build -t iot-gateway -f ./gateway-dotnet/Dockerfile .

docker run -d \
  --name iot-gateway \
  --network iotnet \
  -e ASPNETCORE_URLS=http://0.0.0.0:8080 \
  -e ASPNETCORE_ENVIRONMENT=Development \
  -e Grpc__TelemetryServiceUrl=http://iot-datamanager:50051 \
  -p 5000:8080 \
  iot-gateway
```

### 6) Event Manager (MQTT worker)
```bash
docker build -t iot-eventmanager ./eventmanager-py

docker run -d \
  --name iot-eventmanager \
  --network iotnet \
  -e MQTT_HOST=iot-mqtt \
  -e MQTT_PORT=1883 \
  -e MQTT_TOPIC_IN=telemetry/raw \
  -e MQTT_TOPIC_OUT=telemetry/events \
  iot-eventmanager
```

### 7) Web MQTT klijent (opciono)
```bash
docker build -t iot-mqttweb ./mqtt-webclient

docker run -d \
  --name iot-mqttweb \
  --network iotnet \
  -p 8081:80 \
  iot-mqttweb
```

### 8) Sensor Generator (opciono)
```bash
docker build -t iot-sensorgen ./sensor-generator

docker run --rm \
  --name iot-sensorgen \
  --network iotnet \
  -v "$PWD/data:/data" \
  iot-sensorgen \
  python send_stream.py \
    --path /data/f1_telemetry_wide.csv \
    --base-url http://iot-gateway:8080 \
    --rate 100 --burst 20
```

### 🧹 Gašenje i čišćenje
```bash
docker stop iot-mqttweb iot-eventmanager iot-gateway iot-datamanager iot-mqtt iot-postgres
docker rm   iot-mqttweb iot-eventmanager iot-gateway iot-datamanager iot-mqtt iot-postgres
docker volume rm iot-pgdata
docker network rm iotnet
```
