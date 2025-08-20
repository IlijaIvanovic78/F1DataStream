# 🚗 IoT Telemetry - Data Management System sa ML Predikcijama

Ovaj projekat implementira **IoT sistem za prikupljanje, upravljanje i analizu telemetrijskih podataka sa F1 vozila**.  
Sistem koristi mašinsko učenje za predikciju vremena kruga na osnovu telemetrijskih podataka.

---

## 🏗️ Arhitektura

```
┌─────────────────┐    HTTP/REST     ┌─────────────────┐    gRPC      ┌─────────────────┐
│ Sensor Generator│ ───────────────► │  .NET Gateway   │ ───────────► │   DataManager   │
│  (CSV Stream)   │                  │  (Port 5000)    │              │  (Port 50051)   │
└─────────────────┘                  └─────────────────┘              └─────────────────┘
                                                                               │
                                                                               ▼
┌─────────────────┐                  ┌─────────────────┐              ┌─────────────────┐
│   MqttNats      │ ◄─────────────── │      NATS       │ ◄─────────── │    Analytics    │
│   Web Client    │     WebSocket    │  (Port 9222)    │   Publish    │   Microservice  │
│  (Port 8082)    │                  └─────────────────┘              └─────────────────┘
└─────────────────┘                                                           │
        │                                                                     │
        ▼                                                                     ▼
┌─────────────────┐                  ┌─────────────────┐              ┌─────────────────┐
│  Event Manager  │ ◄─────────────── │      MQTT       │ ◄─────────── │      MLaaS      │
│   Dashboard     │     WebSocket    │  (Port 9001)    │  Subscribe   │  (Port 8000)    │
│  (Port 8081)    │                  └─────────────────┘              └─────────────────┘
└─────────────────┘
```

### Komponente sistema:

- **Sensor Generator** → Simulira F1 telemetriju čitanjem iz CSV fajla
- **Telemetry Gateway API (REST, .NET)** → Exponira REST API i preusmerava pozive ka gRPC servisu
- **DataManager (Python gRPC)** → Čuva telemetrijske podatke u bazi i publikuje na MQTT
- **Event Manager** → Prati MQTT telemetriju i generiše događaje (brzina, RPM, kočenje)
- **MLaaS (FastAPI)** → Machine Learning servis za predikciju vremena kruga
- **Analytics Service** → Prati MQTT podatke, poziva MLaaS i publikuje predikcije na NATS
- **PostgreSQL** → Skladišti telemetriju
- **Mosquitto (MQTT broker)** → Message broker za telemetrijske podatke
- **NATS** → Message broker za ML predikcije

---

## 📂 Struktura projekta

```
IOT/
 ├── docker-compose.yml           # Orkestracija svih servisa
 ├── telemetry.proto              # gRPC definicija (Protobuf)
 ├── data/                        # Podaci za treniranje ML modela
 │    └── f1_telemetry_wide.csv   # F1 telemetrijski podaci
 ├── gateway-dotnet/              # .NET REST API Gateway
 ├── datamanager-py/              # Python gRPC Data Manager
 ├── eventmanager-py/             # Python Event Manager (MQTT)
 ├── mlaas-service/               # FastAPI ML servis
 │    ├── app.py                  # Glavni ML servis
 │    └── requirements.txt        # Python dependencies
 ├── analytics-service/           # Analytics mikroservis
 │    ├── analytics.py            # MQTT→MLaaS→NATS pipeline
 │    └── requirements.txt        # Python dependencies
 ├── mqtt-webclient/              # Web UI za MQTT događaje
 ├── mqttnats-webclient/          # Web UI za MQTT+NATS
 ├── mosquitto/                   # MQTT broker konfiguracija
 ├── Documentation/               # Dokumentacija
 │    └── openapi/
 │         └── asyncapi/
 │              ├── eventmanager.yaml      # Event Manager AsyncAPI
 │              ├── telemetry-publish.yaml # Telemetry Publisher AsyncAPI
 │              ├── analytics-service.yaml # Analytics Service AsyncAPI
 │              └── mlaas-service.yaml     # MLaaS AsyncAPI
 ├── IOT.sln                      # .NET solution
 └── README.md                    # Ovaj fajl
```

### 📋 API Dokumentacija

- **Protobuf (`telemetry.proto`)** → Definicija gRPC servisa za telemetriju
- **AsyncAPI dokumenti** → Definišu asinhronu komunikaciju:
  - `eventmanager.yaml` → MQTT događaji (brzina, RPM, kočenje)
  - `analytics-service.yaml` → MQTT pretplata i NATS publikovanje
  - `mlaas-service.yaml` → REST API za ML predikcije

---

## 🚀 Pokretanje

### 1. Korišćenjem Docker Compose (preporučeno)

```bash
# Pokreni sve servise
docker-compose up --build

# Ili u pozadini
docker-compose up -d --build
```

### 2. Treniranje ML modela

Nakon što se servisi podignu, trebaš trenirati ML model:

```bash
# Sačekaj da MLaaS servis bude spreman
sleep 10

# Treniraj model
curl -X POST http://localhost:8000/train

# Proveri status modela
curl http://localhost:8000/model/info
```

### 3. Testiranje sistema

1. Otvori **MqttNats Dashboard** na [http://localhost:8082](http://localhost:8082)
2. Klikni "Connect" za oba protokola (MQTT i NATS)
3. Sensor Generator će automatski početi slanje podataka
4. Praćenje:
   - MQTT eventi (brzina, RPM, kočenje) se prikazuju odmah
   - ML predikcije se prikazuju nakon završetka svakog kruga (~10 sekundi)

### 4. Zaustavljanje sistema

```bash
docker-compose down

# Sa brisanjem volumena
docker-compose down -v
```

---

## 🤖 Machine Learning Funkcionalnosti

Sistem koristi **Random Forest Regressor** model za predikciju vremena kruga na osnovu:
- Prosečne brzine, throttle pozicije i RPM-a
- Korišćenja DRS-a i kočnica
- Pozicije vozila na stazi
- Istorijskih podataka vozača

### Kako funkcioniše ML pipeline:

1. **DataManager** publikuje telemetriju na MQTT topic `telemetry/raw`
2. **Analytics Service** agregira podatke po krugu
3. Kada se krug završi, poziva **MLaaS** za predikciju
4. Predikcija se publikuje na NATS topic `telemetry.predictions`
5. **MqttNats Web Client** prikazuje predikcije u realnom vremenu

---

## 📖 Dokumentacija i UI

### Web Interfejsi:
- **MqttNats Dashboard** → [http://localhost:8082](http://localhost:8082) - Prikazuje MQTT događaje i ML predikcije
- **Event Manager Dashboard** → [http://localhost:8081](http://localhost:8081) - Prikazuje samo MQTT događaje
- **MLaaS API** → [http://localhost:8000/docs](http://localhost:8000/docs) - FastAPI Swagger dokumentacija
- **Gateway API** → [http://localhost:5000/swagger](http://localhost:5000/swagger) - .NET API dokumentacija

### API Dokumentacija:
- **Protobuf** (`telemetry.proto`) → gRPC servis definicija
- **AsyncAPI dokumenti** → Asinhrona komunikacija:
  - `eventmanager.yaml` → MQTT event processing
  - `analytics-service.yaml` → MQTT→MLaaS→NATS pipeline
  - `mlaas-service.yaml` → ML REST API specifikacija

### Monitoring:
- **NATS Monitor** → [http://localhost:8222](http://localhost:8222) - NATS server statistike
- **PostgreSQL** → Port 5432 - Direktan pristup bazi

---

## 🛠️ Tehnologije

- **.NET 7 (C#)** – REST API Gateway
- **Python** – Mikroservisi:
  - **gRPC** – Data Manager servis
  - **FastAPI** – MLaaS (Machine Learning as a Service)
  - **Paho MQTT** – Event Manager i Analytics servisi
  - **scikit-learn** – ML model za predikciju vremena kruga
- **PostgreSQL** – Relaciona baza podataka
- **Mosquitto** – MQTT message broker
- **NATS** – High-performance message broker za ML predikcije
- **Docker & Docker Compose** – Kontejnerizacija i orkestracija
- **Nginx** – Web server za klijentske aplikacije

---

## 📌 Napomene

### Portovi sistema:
- **5000** - Gateway REST API (.NET)
- **8000** - MLaaS REST API (FastAPI)
- **8081** - MQTT Event Dashboard
- **8082** - MqttNats Dashboard (MQTT + NATS)
- **50051** - gRPC DataManager
- **5432** - PostgreSQL
- **1883** - MQTT TCP
- **9001** - MQTT WebSocket
- **4222** - NATS TCP
- **9222** - NATS WebSocket
- **8222** - NATS Monitoring

### Zahtevi:
- Docker i Docker Compose
- Minimum 4GB RAM za sve servise
- ~100MB prostora za F1 telemetrijske podatke

### GitHub dokumentacija:
- **OpenAPI i Protobuf dokumenti** → REST API i gRPC servis specifikacije
- **AsyncAPI dokumenti** → Specifikacije za:
  - Event Manager (MQTT događaji)
  - Analytics Service (MQTT→MLaaS→NATS pipeline)
  - MLaaS (REST API za ML predikcije)
- **Izvorni kod** → Svi mikroservisi sa README fajlovima
