# IoT Telemetry - gRPC Data Manager

This project implements a **gRPC service for managing IoT vehicle telemetry data**. The service enables creating, reading, updating, deleting, and aggregating telemetry measurements.

## 🏗️ gRPC Service Architecture

**gRPC Data Manager** is a Python service that:
- Receives gRPC calls on port `50051`
- Stores data in PostgreSQL database
- Implements all CRUD operations
- Enables aggregations (MIN/MAX/AVG/SUM)

## 📋 Implemented gRPC Services

### TelemetryService

| Method | Description | Input | Output |
|--------|-------------|-------|--------|
| `CreateTelemetry` | Creates new telemetry measurement | `CreateTelemetryRequest` | `CreateTelemetryResponse` |
| `GetTelemetry` | Reads measurement by ID | `GetTelemetryRequest` | `GetTelemetryResponse` |
| `UpdateTelemetry` | Updates existing measurement | `UpdateTelemetryRequest` | `UpdateTelemetryResponse` |
| `DeleteTelemetry` | Deletes measurement by ID | `DeleteTelemetryRequest` | `DeleteTelemetryResponse` |
| `ListTelemetry` | Lists measurements with pagination | `ListTelemetryRequest` | `ListTelemetryResponse` |
| `Aggregate` | Calculations (MIN/MAX/AVG/SUM) | `AggregateRequest` | `AggregateResponse` |

## 🚀 Getting Started

### Step 1: Start PostgreSQL Database

```bash
# From project root directory
docker-compose up postgres -d
```

### Step 2: Setup Python Environment

```bash
# From project root
cd datamanager-py
.\setup_venv.ps1
```

This script will:
- Create `.venv` virtual environment
- Install all dependencies
- Generate gRPC stubs from telemetry.proto

### Step 3: Environment Configuration

```bash
# Copy template configuration
copy .env.example .env
```

Edit `.env` file as needed:
```bash
POSTGRES_HOST=postgres
POSTGRES_DB=telemetry
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_PORT=5432
GRPC_HOST=0.0.0.0
GRPC_PORT=50051
DEBUG=true
```

### Step 4: Start gRPC Server

```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run server
python app.py
```

**Server will be available at `localhost:50051`** 🎉

## 🔧 Generating gRPC Stubs

To manually regenerate Python gRPC code:

```bash
cd datamanager-py
python generate_grpc.py
```

Generates files in `gen/` folder:
- `telemetry_pb2.py` - Python classes for messages
- `telemetry_pb2_grpc.py` - gRPC client/server stubs

## 📦 Dependencies

```
psycopg[binary]>=3.1,<4.0    # PostgreSQL driver
grpcio>=1.60.0,<2.0.0         # gRPC runtime
grpcio-tools>=1.60.0,<2.0.0   # Protocol Buffers compiler
protobuf>=4.25.0,<5.0.0       # Protocol Buffers library
python-dotenv>=1.0.0,<2.0.0   # Environment loader
```

## 🔍 Testing gRPC Service

```python
import grpc
from gen.telemetry_pb2_grpc import TelemetryServiceStub
from gen.telemetry_pb2 import CreateTelemetryRequest, Telemetry

# Connect to server
channel = grpc.insecure_channel('localhost:50051')
stub = TelemetryServiceStub(channel)

# Test telemetry creation
request = CreateTelemetryRequest(
    telemetry=Telemetry(
        driver="Lewis Hamilton",
        lap_number=1,
        speed=280.5,
        rpm=8500,
        throttle=95.2
    )
)

response = stub.CreateTelemetry(request)
print(f"Created telemetry ID: {response.telemetry.id}")
```

## 🐳 Docker Deployment

```bash
# Run complete system
docker-compose up -d

# gRPC server will be available at localhost:5001
```
