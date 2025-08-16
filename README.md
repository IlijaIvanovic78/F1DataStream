# gRPC Code Generation

## Setup okruženja

### 1. Kreiranje virtualnog okruženja

Pokrenite PowerShell skriptu iz root direktorijuma:

```powershell
.\setup_venv.ps1
```

Ova skripta će:

- Kreirati `.venv` virtuelno okruženje
- Instalirati sve zavisnosti iz `requirements.txt`
- Generirati gRPC stubove u `gen/` folderu

### 2. Konfiguracija environment varijabli

Kopirajte `.env.example` u `.env`:

```powershell
# Windows
copy .env.example .env
```

```bash
# Linux/macOS
cp .env.example .env
```

Zatim uredite `.env` fajl sa vašim PostgreSQL kredencijalima:

```bash
POSTGRES_HOST=localhost      # ili IP adresa vašeg PostgreSQL servera
POSTGRES_DB=telemetry       # naziv baze podataka
POSTGRES_USER=postgres      # PostgreSQL korisnik
POSTGRES_PASSWORD=postgres  # PostgreSQL lozinka
POSTGRES_PORT=5432         # PostgreSQL port
```

### 3. Pokretanje servera

```bash
cd datamanager-py
python app.py
```

## Generisanje gRPC stubova

Za ručno generisanje Python gRPC stubova iz `telemetry.proto` fajla:

```bash
# Iz datamanager-py/ direktorijuma
python generate_grpc.py
```

## Što će biti generirano

Skripta će kreirati sledeće fajlove u `gen/` podfolderu:

- `telemetry_pb2.py` - Python klase za protobuf poruke
- `telemetry_pb2_grpc.py` - gRPC client i server stubovi
- `__init__.py` - Omogućava import stubova kao modul

## Korišćenje generiranih stubova

Nakon generisanja, možete importovati klase na sledeći način:

```python
# Import svih klasa
from gen import *

# Ili specifični import
from gen import (
    Telemetry,
    TelemetryServiceStub,
    TelemetryServiceServicer,
    CreateTelemetryRequest,
    AggregateType
)

# Kreiranje gRPC klijenta
import grpc
channel = grpc.insecure_channel('localhost:50051')
stub = TelemetryServiceStub(channel)

# Kreiranje telemetrije
telemetry = Telemetry(
    id=1,
    driver="Lewis Hamilton",
    lap_number=5,
    speed=320.5,
    # ...
)
```

## VS Code konfiguracija

Projekt je konfigurisan da koristi:

- Python interpreter iz `.venv/Scripts/python.exe`
- Environment varijable iz `.env` fajla
- Pylance može da pronađe generisane gRPC module

## Zavisnosti

Instalirane biblioteke (pinned versions u requirements.txt):

- `psycopg[binary]>=3.1,<4.0` - PostgreSQL driver
- `grpcio>=1.60.0,<2.0.0` - gRPC runtime
- `grpcio-tools>=1.60.0,<2.0.0` - Protocol Buffers compiler
- `protobuf>=4.25.0,<5.0.0` - Protocol Buffers library
- `python-dotenv>=1.0.0,<2.0.0` - Environment variables loader
