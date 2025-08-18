# 🚗 IoT Telemetry - Data Management System

Ovaj projekat implementira **IoT sistem za prikupljanje i upravljanje telemetrijskim podacima sa vozila**.  
Sistem se sastoji od više servisa koji komuniciraju putem **gRPC-a**, **REST API Gateway-a**, **MQTT-a** i baze podataka.

---

## 🏗️ Arhitektura

```
┌─────────────────┐    HTTP/REST     ┌─────────────────┐    gRPC      ┌─────────────────┐
│   REST Client   │ ───────────────► │  .NET Gateway   │ ───────────► │ Python gRPC     │
│  (Browser/API)  │                  │  (Port 8080)    │              │ (Port 50051)    │
└─────────────────┘                  └─────────────────┘              └─────────────────┘
                                              │                                │
                                              ▼                                ▼
                                     ┌─────────────────┐              ┌─────────────────┐
                                     │   Swagger UI    │              │   PostgreSQL    │
                                     │  Documentation  │              │   Database      │
                                     └─────────────────┘              └─────────────────┘
```

- **Telemetry Gateway API (REST, .NET)** → Exponira REST API i preusmerava pozive ka gRPC servisu.
- **Telemetry gRPC Service (Python)** → Čuva i obrađuje telemetrijske podatke u bazi.
- **MQTT Publisher** → Simulira IoT uređaje i objavljuje podatke na MQTT broker.
- **PostgreSQL** → Skladišti telemetriju.
- **Mosquitto (MQTT broker)** → Posreduje razmenu poruka između publisher-a i servisa.

---

## 📂 Struktura projekta

```
IOT/
 ├── docker-compose.yml         # Orkestracija svih servisa
 ├── telemetry.proto             # gRPC definicija (Protobuf) → generisanje koda
 ├── Documents/                  # Dokumentacija i dijagrami
 │    ├── eventmanager.yaml      # AsyncAPI definicija Event Manager servisa
 │    ├── telemetry-publish.yaml # AsyncAPI definicija Telemetry Publisher-a
 │    ├── openapi.yaml           # OpenAPI specifikacija za REST API (generisana iz .NET Gateway-a)
 │    ├── diagrams/              # Dijagrami sistema
 │    └── ...                    # Ostali dokumenti
 ├── IOT.sln                     # .NET solution
 ├── README.md                   # Ovaj fajl
 └── .env.example                # Primer konfiguracionih varijabli
```

👉 **Protobuf (`telemetry.proto`)** se koristi za definisanje gRPC servisa i generisanje stubova u C# i Python-u.  
👉 **OpenAPI (`Documents/openapi.yaml`)** dokument opisuje REST API (generisano iz Swagger-a u Gateway servisu).  
👉 **AsyncAPI (`Documents/eventmanager.yaml`, `Documents/telemetry-publish.yaml`)** dokumentuje mikroservise vezane za događaje i MQTT komunikaciju.

---

## 🚀 Pokretanje

### 1. Korišćenjem Docker Compose (preporučeno)

Pokreni sve servise odjednom:

```bash
docker-compose up --build
```

### 2. Pojedinačno (Docker run + bridge mreža)

Ako želiš da testiraš odvojeno, svaki servis možeš startovati pomoću `docker run` i povezati ih na istu mrežu:

```bash
docker network create iot-net

docker run --rm --network iot-net postgres
docker run --rm --network iot-net mosquitto
docker run --rm --network iot-net telemetry-grpc
docker run --rm --network iot-net telemetry-gateway
```

---

## 📖 Dokumentacija

- **Protobuf (telemetry.proto)** → Definicija gRPC servisa.
- **OpenAPI (Documents/openapi.yaml)** → REST API Gateway dokumentacija.
- **AsyncAPI (Documents/eventmanager.yaml, Documents/telemetry-publish.yaml)** → Mikroservisi i MQTT komunikacija.
- **Dijagrami sistema** → dostupni u `Documents/diagrams/`.
- **Swagger UI** → REST API dokumentacija dostupna na [http://localhost:8080](http://localhost:8080) nakon pokretanja Gateway servisa.

---

## 🛠️ Tehnologije

- **.NET 7 (C#)** – REST API Gateway
- **Python (gRPC)** – Data Manager servis
- **PostgreSQL** – baza podataka
- **Mosquitto** – MQTT broker
- **Docker & Docker Compose** – orkestracija servisa

---

## 📌 Napomena

- Koristi `.env.example` kao osnovu za konfigurisanje varijabli okruženja.
- Izvorni kod projekta kao i **OpenAPI i Protobuf dokumente** postaviti na GitHub, uz kratak opis implementiranih REST API i gRPC servisa.
- Izvorni kod projekta kao i **AsyncAPI dokumente** postaviti na GitHub, uz kratak opis implementiranih mikroservisa.
