# F1 Telemetry IoT Platform

Kompletna IoT platforma za analizu telemetrijskih podataka Formula 1 vozila implementirana kroz tri faze razvoja sa mikroservisnom arhitekturom.

Ovaj projekat predstavlja kompletnu IoT platformu koja obrađuje telemetrijske podatke Formula 1 vozila u realnom vremenu. Platforma je razvijena kroz tri projektna ciklusa, gde svaki dodaje nove funkcionalnosti:

- **Projekat 1**: Osnovna CRUD funkcionalnost sa REST i gRPC API-jima
- **Projekat 2**: MQTT messaging i event detection sistem
- **Projekat 3**: Machine Learning analiza i NATS messaging

---

## Projekat 1 - Osnovna IoT Platforma

### Opis

Implementacija osnovne IoT platforme sa CRUD operacijama nad telemetrijskim podacima F1 vozila. Dataset sadrži realnu telemetriju sa podatcima o brzini, RPM-u, poziciji, upotrebi kočnica, DRS-a i drugih parametara.

### Mikroservisi

#### Gateway Mikroservis (ASP.NET Core)

**Funkcionalnosti**:

- REST API endpoints za CRUD operacije
- Agregacione funkcije (MIN, MAX, AVG, SUM)
- OpenAPI specifikacija
- gRPC klijent komunikacija sa DataManager-om
- Swagger UI dokumentacija

#### DataManager Mikroservis (Python)

**Funkcionalnosti**:

- gRPC server sa Protocol Buffers definicijama
- PostgreSQL baza podataka integracija
- CRUD operacije nad telemetrijskim podacima
- Agregacione funkcije sa filtriranjem
- Connection pooling i health check

#### SensorGenerator (Python)

**Funkcionalnosti**:

- Čitanje F1 telemetrijskih podataka iz CSV fajla
- Simulacija real-time stream-a podataka
- Slanje podataka na Gateway REST API
- Konfigurisanje brzine slanja i batch veličine

---

## Projekat 2 - MQTT Messaging & Event Detection

### Opis

Proširenje platforme sa MQTT messaging sistemom i real-time event detection funkcionalnostima.

### Novi Mikroservisi

#### DataManager - MQTT Publisher (Python)

**Nove funkcionalnosti**:

- MQTT publikovanje na `telemetry/raw` topic
- AsyncAPI specifikacija za MQTT
- Dual-mode operacija (database + MQTT)

#### EventManager Mikroservis (Python)

**Funkcionalnosti**:

- MQTT subscriber na `telemetry/raw` topic
- Real-time event detection:
  - **SPEED_OVER_LIMIT**: Brzina > 310 km/h
  - **RPM_OVER_LIMIT**: RPM > 11,500
  - **HARD_BRAKE_AT_HIGH_SPEED**: Kočenje na brzini > 280 km/h
- Publikovanje events na `telemetry/events` topic
- AsyncAPI specifikacija za events

#### Web Client za MQTT Events (HTML/JavaScript)

**Funkcionalnosti**:

- WebSocket konekcija na MQTT broker
- Real-time prikaz događaja
- Statistike i filtriranje
- Responsive UI dizajn
- *Napomena: Ovaj osnovni web client je naknadno unapređen u Projektu 3*

---

## Projekat 3 - Machine Learning & Advanced Analytics

### Opis

Implementacija analitike sa machine learning modelima i NATS messaging sistemom.

### Novi Mikroservisi

#### Analytics Mikroservis (Python)

**Funkcionalnosti**:

- MQTT subscriber za telemetrijske podatke
- Agregacija podataka po krugovima (lap-based)
- Komunikacija sa MLaaS servisom
- NATS publisher za ML predikcije
- HTTP API za pristup predikcijama

#### MLaaS (Machine Learning as a Service)

**ML Model karakteristike**:

- **Algorithm**: Random Forest Regressor
- **Task**: Regression (predviđanje vremena kruga)

#### MqttNats Web Client (HTML/JavaScript)

**Funkcionalnosti**:

- Dual-stream monitoring (MQTT events + NATS predictions)
- Real-time ML predictions prikaz
- Advanced statistics dashboard
- HTTP polling fallback za NATS podatke

---

## Struktura Projekta

```
IOT/
├── docker-compose.yml                 # Glavna orchestracija
├── telemetry.proto                   # Protocol Buffers definicije
├── data/
│   └── f1_telemetry_wide.csv         # F1 telemetrijski dataset
├── gateway-dotnet/                   # ASP.NET Core Gateway
│   ├── Controllers/TelemetryController.cs
│   ├── Program.cs
│   ├── Dockerfile
│   └── gateway-dotnet.csproj
├── datamanager-py/                   # Python DataManager
│   ├── app.py                        # gRPC server
│   ├── mqtt_client.py               # MQTT publisher
│   ├── gen/                         # Generated gRPC files
│   ├── Dockerfile
│   └── requirements.txt
├── eventmanager-py/                  # Event Detection Service
│   ├── event_manager.py
│   ├── Dockerfile
│   └── requirements.txt
├── analytics-service/                # ML Analytics Service
│   ├── analytics.py
│   ├── Dockerfile
│   └── requirements.txt
├── mlaas-service/                    # Machine Learning Service
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── sensor-generator/                 # Data Simulator
│   ├── send_stream.py
│   ├── Dockerfile
│   └── requirements.txt
├── mqttnats-webclient/              # MqttNats Web Client (Enhanced)
│   ├── index.html
│   ├── styles.css
│   └── Dockerfile
├── mosquitto/                        # MQTT Broker Config
│   └── mosquitto.conf
└── Documentation/
    ├── openapi/
    │   └── swagger.json              # REST API spec
    └── asyncapi/
        ├── analytics-service.yaml    # NATS AsyncAPI
        ├── eventmanager.yaml        # MQTT Events AsyncAPI
        ├── mlaas-service.yaml
        └── telemetry-publish.yaml   # MQTT Telemetry AsyncAPI
```

---

## Pokretanje Sistema

### Docker Compose Metod

```bash

# Pokretanje celokupnog sistema
docker compose up --build

# Pokretanje u background-u
docker compose up --build -d

# Zaustavljanje sistema
docker compose down
```

**Dostupni servisi**:

- Gateway API: http://localhost:5000
- Swagger UI: http://localhost:5000/swagger
- DataManager gRPC: localhost:50051
- MQTT Broker: localhost:1883
- MQTT WebSocket: localhost:9001
- NATS Broker: localhost:4222
- Analytics API: http://localhost:8083
- MLaaS API: http://localhost:8000
- MqttNats Web Client: http://localhost:8082

### Pojedinačno Pokretanje sa Docker Run

#### 1. Kreiranje Bridge Network-a

```bash
docker network create iot-network
```

#### 2. PostgreSQL Baza

```bash
docker run -d \
  --name postgres-iot \
  --network iot-network \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=telemetry \
  -p 5432:5432 \
  postgres:15
```

#### 3. MQTT Broker

```bash
docker run -d \
  --name mosquitto-iot \
  --network iot-network \
  -p 1883:1883 \
  -p 9001:9001 \
  -v $(pwd)/mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro \
  eclipse-mosquitto:2
```

#### 4. NATS Broker

```bash
docker run -d \
  --name nats-iot \
  --network iot-network \
  -p 4222:4222 \
  -p 8222:8222 \
  nats:2.10-alpine \
  -js -m 8222 -DV --port 4222
```

#### 5. DataManager Service

```bash
docker build -t datamanager ./datamanager-py
docker run -d \
  --name datamanager-iot \
  --network iot-network \
  -p 50051:50051 \
  -e POSTGRES_HOST=postgres-iot \
  -e MQTT_HOST=mosquitto-iot \
  datamanager
```

#### 6. Gateway Service

```bash
docker build -t gateway ./gateway-dotnet
docker run -d \
  --name gateway-iot \
  --network iot-network \
  -p 5000:8080 \
  -e Grpc__TelemetryServiceUrl=http://datamanager-iot:50051 \
  gateway
```

#### 7. MLaaS Service

```bash
docker build -t mlaas ./mlaas-service
docker run -d \
  --name mlaas-iot \
  --network iot-network \
  -p 8000:8000 \
  mlaas
```

#### 8. Analytics Service

```bash
docker build -t analytics ./analytics-service
docker run -d \
  --name analytics-iot \
  --network iot-network \
  -p 8083:8080 \
  -e MQTT_HOST=mosquitto-iot \
  -e NATS_URL=nats://nats-iot:4222 \
  -e MLAAS_URL=http://mlaas-iot:8000 \
  analytics
```

#### 9. EventManager Service

```bash
docker build -t eventmanager ./eventmanager-py
docker run -d \
  --name eventmanager-iot \
  --network iot-network \
  -e MQTT_HOST=mosquitto-iot \
  eventmanager
```

#### 10. MqttNats Web Client

```bash
# MqttNats Web Client
docker build -t mqttnats-webclient ./mqttnats-webclient
docker run -d \
  --name mqttnats-web-iot \
  --network iot-network \
  -p 8082:80 \
  mqttnats-webclient
```

#### 11. Sensor Generator

```bash
docker build -t sensor-generator ./sensor-generator
docker run -d \
  --name sensorgen-iot \
  --network iot-network \
  -v $(pwd)/data:/data \
  sensor-generator \
  python send_stream.py --path /data/f1_telemetry_wide.csv --base-url http://gateway-iot:8080 --rate 50
```

---

## Monitoring & Observability

### Service Health Endpoints

- Gateway: `http://localhost:5000/health`
- Analytics: `http://localhost:8083/health`
- MLaaS: `http://localhost:8000/health`

### MQTT Broker Monitoring

- MQTT WebSocket: `ws://localhost:9001`

### NATS Monitoring

- NATS HTTP: `http://localhost:8222`

---

## 🛠️ Tehnologije

| Komponenta           | Tehnologije                                                 |
| -------------------- | ----------------------------------------------------------- |
| **Gateway**          | ASP.NET Core 8.0, gRPC Client, Swagger/OpenAPI              |
| **DataManager**      | Python 3.12, gRPC Server, PostgreSQL, SQLAlchemy, Paho-MQTT |
| **Analytics**        | Python 3.10, FastAPI, NATS-py, Paho-MQTT                    |
| **MLaaS**            | Python 3.10, FastAPI, scikit-learn, pandas, numpy           |
| **EventManager**     | Python 3.12, Paho-MQTT, AsyncAPI                            |
| **SensorGenerator**  | Python 3.12, Requests                                       |
| **Web Clients**      | HTML5, JavaScript, MQTT.js                                  |
| **Databases**        | PostgreSQL 15                                               |
| **Message Brokers**  | Eclipse Mosquitto, NATS                                     |
| **Containerization** | Docker, Docker Compose                                      |
| **Documentation**    | OpenAPI 3.0, AsyncAPI 2.6, Protocol Buffers                 |

---

## API Dokumentacija

- **OpenAPI Specification**: `/Documentation/openapi/swagger.json`
- **AsyncAPI Specifications**: `/Documentation/asyncapi/`
- **Protocol Buffers**: `/telemetry.proto`
- **Swagger UI**: `http://localhost:5000/swagger`
