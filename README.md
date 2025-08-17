# IoT Telemetry - gRPC Data Manager

This project implements a **gRPC service for managing IoT vehicle telemetry data** with a REST API Gateway. The system consists of a Python gRPC backend service and a .NET Core REST API gateway.

## 🏗️ System Architecture

```
┌─────────────────┐    HTTP/REST     ┌─────────────────┐    gRPC      ┌─────────────────┐
│   REST Client   │ ───────────────► │  .NET Gateway   │ ───────────► │ Python gRPC     │
│  (Browser/API)  │                  │  (Port 5000)    │              │ (Port 50051)    │
└─────────────────┘                  └─────────────────┘              └─────────────────┘
                                              │                                │
                                              │                                │
                                              ▼                                ▼
                                     ┌─────────────────┐              ┌─────────────────┐
                                     │   Swagger UI    │              │   PostgreSQL    │
                                     │  Documentation  │              │   Database      │
                                     └─────────────────┘              └─────────────────┘
```

### Components:

**🔵 .NET Gateway** - REST API frontend that:
- Exposes HTTP/REST endpoints on port `5000`
- Converts REST calls to gRPC calls
- Provides Swagger documentation
- Handles data validation and error responses

**🟡 gRPC Data Manager** - Python service that:
- Receives gRPC calls on port `50051`
- Stores data in PostgreSQL database
- Implements all CRUD operations
- Enables aggregations (MIN/MAX/AVG/SUM)

## 📋 API Documentation

### 🌐 REST API Endpoints (.NET Gateway)

| Method | Endpoint | Description | Query Parameters |
|--------|----------|-------------|------------------|
| `GET` | `/api/telemetry` | List telemetries with pagination | `driver`, `lap`, `page`, `pageSize` |
| `GET` | `/api/telemetry/{id}` | Get single telemetry by ID | - |
| `POST` | `/api/telemetry` | Create new telemetry | - |
| `PUT` | `/api/telemetry/{id}` | Update existing telemetry | - |
| `DELETE` | `/api/telemetry/{id}` | Delete telemetry | - |
| `GET` | `/api/telemetry/aggregate` | Aggregate calculations | `field`, `type`, `driver`, `lap`, `from`, `to` |

**📖 OpenAPI Documentation**: 
- Swagger UI available at `http://localhost:5000`
- OpenAPI 3.0 specification with detailed schemas
- Interactive API testing interface
- Request/response examples and validation rules

### 🔧 gRPC Services (Python)

**📋 Protobuf Definition**: [`telemetry.proto`](telemetry.proto)

| Method | Description | Input | Output |
|--------|-------------|-------|--------|
| `CreateTelemetry` | Creates new telemetry measurement | `CreateTelemetryRequest` | `CreateTelemetryResponse` |
| `GetTelemetry` | Reads measurement by ID | `GetTelemetryRequest` | `GetTelemetryResponse` |
| `UpdateTelemetry` | Updates existing measurement | `UpdateTelemetryRequest` | `UpdateTelemetryResponse` |
| `DeleteTelemetry` | Deletes measurement by ID | `DeleteTelemetryRequest` | `DeleteTelemetryResponse` |
| `ListTelemetry` | Lists measurements with pagination | `ListTelemetryRequest` | `ListTelemetryResponse` |
| `Aggregate` | Calculations (MIN/MAX/AVG/SUM) | `AggregateRequest` | `AggregateResponse` |

## 🚀 Docker Deployment

### Option A: Docker Compose (Recommended)

Start all services with a single command:

```bash
# Clone the repository
git clone https://github.com/yourusername/iot-telemetry-grpc.git
cd iot-telemetry-grpc

# Start complete system
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Services will be available at:**
- 🌐 **REST API + Swagger**: `http://localhost:5000`
- 🔧 **gRPC Service**: `localhost:50051`
- 🗄️ **PostgreSQL**: `localhost:5432`

### Option B: Individual Docker Containers

Start each service individually using Docker run commands:

#### 1. Create Docker Network

```bash
# Create shared bridge network
docker network create iot-network
```

#### 2. Start PostgreSQL Database

```bash
docker run -d \
  --name iot-postgres \
  --network iot-network \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=telemetry \
  -p 5432:5432 \
  -v iot-pgdata:/var/lib/postgresql/data \
  postgres:15
```

#### 3. Build and Start Python gRPC Service

```bash
# Build datamanager image
docker build -t iot-datamanager ./datamanager-py

# Run datamanager container
docker run -d \
  --name iot-datamanager \
  --network iot-network \
  -e POSTGRES_HOST=iot-postgres \
  -e POSTGRES_DB=telemetry \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e GRPC_HOST=0.0.0.0 \
  -e GRPC_PORT=50051 \
  -p 50051:50051 \
  iot-datamanager
```

#### 4. Build and Start .NET Gateway

```bash
# Build gateway image (from project root)
docker build -t iot-gateway -f ./gateway-dotnet/Dockerfile .

# Run gateway container
docker run -d \
  --name iot-gateway \
  --network iot-network \
  -e ASPNETCORE_URLS=http://0.0.0.0:8080 \
  -e ASPNETCORE_ENVIRONMENT=Development \
  -e Grpc__TelemetryServiceUrl=http://iot-datamanager:50051 \
  -p 5000:8080 \
  iot-gateway
```

#### 5. Manage Individual Containers

```bash
# View logs
docker logs iot-gateway
docker logs iot-datamanager
docker logs iot-postgres

# Stop services
docker stop iot-gateway iot-datamanager iot-postgres

# Remove containers
docker rm iot-gateway iot-datamanager iot-postgres

# Remove network and volume
docker network rm iot-network
docker volume rm iot-pgdata
```

## 📊 Data Models & Validation

### Telemetry Record Schema
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

### Input Validation Rules
- **Driver**: Required, max 100 characters
- **Speed**: 0-400 km/h
- **Throttle**: 0-100%
- **LapNumber**: 1-100
- **NGear**: -1 to 8 (including reverse)
- **RPM**: 0-20,000
- **TimestampUtc**: Required ISO 8601 format

### Aggregation Parameters
- **Fields**: `SPEED`, `RPM`, `THROTTLE`, `X`, `Y`
- **Types**: `MIN`, `MAX`, `AVG`, `SUM`
- **Filters**: Driver name, lap number, time range

## 🔍 API Testing Examples

### REST API Examples

```bash
# List telemetries with filtering
curl "http://localhost:5000/api/telemetry?driver=Hamilton&lap=15&page=1&pageSize=10"

# Get specific telemetry
curl "http://localhost:5000/api/telemetry/1"

# Create new telemetry
curl -X POST "http://localhost:5000/api/telemetry" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "Max Verstappen",
    "timestampUtc": "2024-08-17T14:30:00Z",
    "lapNumber": 1,
    "x": 0,
    "y": 0,
    "speed": 50,
    "throttle": 30,
    "brake": false,
    "nGear": 2,
    "rpm": 3000,
    "drs": false
  }'

# Update telemetry
curl -X PUT "http://localhost:5000/api/telemetry/1" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "Lewis Hamilton",
    "timestampUtc": "2024-08-17T14:31:00Z",
    "lapNumber": 1,
    "x": 100,
    "y": 50,
    "speed": 120,
    "throttle": 75,
    "brake": false,
    "nGear": 4,
    "rpm": 6000,
    "drs": true
  }'

# Delete telemetry
curl -X DELETE "http://localhost:5000/api/telemetry/1"

# Aggregate maximum speed for Hamilton
curl "http://localhost:5000/api/telemetry/aggregate?field=SPEED&type=MAX&driver=Lewis%20Hamilton"
```

### Direct gRPC Testing (Python)

```python
import grpc
from gen.telemetry_pb2_grpc import TelemetryServiceStub
from gen.telemetry_pb2 import CreateTelemetryRequest, Telemetry
from google.protobuf.timestamp_pb2 import Timestamp
from datetime import datetime

# Connect to gRPC server
channel = grpc.insecure_channel('localhost:50051')
stub = TelemetryServiceStub(channel)

# Create timestamp
timestamp = Timestamp()
timestamp.FromDatetime(datetime.utcnow())

# Create telemetry
request = CreateTelemetryRequest(
    telemetry=Telemetry(
        driver="Lewis Hamilton",
        timestamp=timestamp,
        lap_number=1,
        x=0.0,
        y=0.0,
        speed=280.5,
        throttle=95.2,
        brake=False,
        n_gear=7,
        rpm=8500,
        drs=True
    )
)

response = stub.CreateTelemetry(request)
print(f"Created telemetry ID: {response.telemetry.id}")
```

## 📁 Repository Structure

```
iot-telemetry-grpc/
├── 📄 README.md                    # This documentation
├── 📄 telemetry.proto              # Protobuf service definition
├── 📄 docker-compose.yml           # Docker Compose configuration
├── 📄 .gitignore                   # Git ignore rules
├── 📄 .env.example                 # Environment template
│
├── 📂 datamanager-py/              # Python gRPC Service
│   ├── 📄 app.py                   # Main gRPC server
│   ├── 📄 requirements.txt         # Python dependencies
│   ├── 📄 Dockerfile               # Docker configuration
│   ├── 📄 .env                     # Environment variables
│   ├── 📄 generate_grpc.py         # gRPC stub generator
│   └── 📂 gen/                     # Generated Protobuf files
│       ├── telemetry_pb2.py
│       └── telemetry_pb2_grpc.py
│
└── 📂 gateway-dotnet/              # .NET REST API Gateway
    ├── 📄 Program.cs               # Main application entry
    ├── 📄 gateway-dotnet.csproj    # Project configuration
    ├── 📄 appsettings.json         # Application settings
    ├── 📄 Dockerfile               # Docker configuration
    └── 📂 Controllers/
        └── TelemetryController.cs  # REST API endpoints
```

## 🔧 Development Setup

### Prerequisites
- Docker & Docker Compose
- .NET 8.0 SDK (for local development)
- Python 3.12+ (for local development)
- Git

### Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/iot-telemetry-grpc.git
cd iot-telemetry-grpc

# Start database only
docker-compose up postgres -d

# Setup Python service
cd datamanager-py
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python generate_grpc.py
python app.py

# Setup .NET gateway (in new terminal)
cd gateway-dotnet
dotnet restore
dotnet run
```

## 📦 Dependencies

### Python gRPC Service
```txt
psycopg[binary]>=3.1,<4.0    # PostgreSQL driver
grpcio>=1.60.0,<2.0.0         # gRPC runtime  
grpcio-tools>=1.60.0,<2.0.0   # Protocol Buffers compiler
protobuf>=4.25.0,<5.0.0       # Protocol Buffers library
python-dotenv>=1.0.0,<2.0.0   # Environment loader
```

### .NET REST Gateway
```xml
<PackageReference Include="Grpc.Net.Client" Version="2.62.0" />
<PackageReference Include="Grpc.Net.ClientFactory" Version="2.62.0" />
<PackageReference Include="Google.Protobuf" Version="3.26.1" />
<PackageReference Include="Grpc.Tools" Version="2.62.0" />
<PackageReference Include="Swashbuckle.AspNetCore" Version="6.4.0" />
```

## 🎯 Production Considerations

- **Security**: Implement authentication and authorization
- **Monitoring**: Add health checks, metrics, and logging
- **Scaling**: Configure horizontal scaling for gateway instances  
- **Database**: Implement connection pooling and read replicas
- **API Versioning**: Establish versioning strategy for REST endpoints
- **Rate Limiting**: Add rate limiting for public endpoints
- **SSL/TLS**: Enable HTTPS for production deployments

---

**🚀 Quick Start**: `docker-compose up -d` → Open `http://localhost:5000` for Swagger UI
