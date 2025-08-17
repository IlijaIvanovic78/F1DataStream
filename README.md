# IoT Telemetry - gRPC Data Manager

This project implements a **gRPC service for managing IoT vehicle telemetry data** with a REST API Gateway and CSV data streaming capabilities. The system consists of a Python gRPC backend service, a .NET Core REST API gateway, and a Python sensor data generator.

## 🏗️ System Architecture

```
┌─────────────────┐    CSV Stream    ┌─────────────────┐    HTTP/REST     ┌─────────────────┐    gRPC      ┌─────────────────┐
│  Sensor Data    │ ───────────────► │  Sensor Gen     │ ───────────────► │  .NET Gateway   │ ───────────► │ Python gRPC     │
│   Generator     │                  │  (Python)       │                  │  (Port 5000)    │              │ (Port 50051)    │
└─────────────────┘                  └─────────────────┘                  └─────────────────┘              └─────────────────┘
                                              │                                      │                                │
                                              │                                      │                                │
                                              ▼                                      ▼                                ▼
                                     ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
                                     │   CSV Data      │              │   Swagger UI    │              │   PostgreSQL    │
                                     │ (F1 Telemetry)  │              │  Documentation  │              │   Database      │
                                     └─────────────────┘              └─────────────────┘              └─────────────────┘
```

### Components:

**🟢 Sensor Generator** - CSV data streamer that:
- Reads F1 telemetry data from CSV files
- Converts data to REST API format
- Streams data with configurable rate limiting
- Provides progress tracking and error handling

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

## 📊 Data Flow

1. **CSV Input**: F1 telemetry data with columns: `driver,timestamp,LapNumber,X,Y,Speed,Throttle,Brake,nGear,RPM,DRS`
2. **Sensor Generator**: Reads CSV → converts to JSON → sends HTTP POST to Gateway
3. **Gateway**: Validates REST request → converts to gRPC → calls DataManager
4. **DataManager**: Stores in PostgreSQL → returns created record with ID
5. **Response**: Success/error propagated back through the chain

## 🚀 Quick Start

### Option 1: Complete Docker Deployment (Recommended)

1. **Prepare your data**:
   ```bash
   # Place your CSV file in the data folder
   mkdir -p data
   # Copy your F1 telemetry CSV to: data/f1_telemetry_wide.csv
   ```

2. **Start the complete system**:
   ```bash
   docker-compose up -d --build
   ```

3. **Monitor the streaming**:
   ```bash
   # Watch sensor generator logs
   docker-compose logs -f sensorgen
   
   # Check all services
   docker-compose logs
   ```

4. **Access the services**:
   - 🌐 **REST API + Swagger**: `http://localhost:5000`
   - 📊 **View data**: Use Swagger UI to browse telemetry records
   - 📈 **Aggregations**: Test aggregate endpoints for analytics

### Option 2: Development Setup

```bash
# Start infrastructure
docker-compose up postgres datamanager gateway -d

# Run sensor generator locally (from project root)
cd sensor-generator
pip install -r requirements.txt
python send_stream.py --path ../data/f1_telemetry_wide.csv --base-url http://localhost:5000 --rate 100 --burst 5
```

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

## 📊 Sensor Generator Usage

### CSV Data Format

Your CSV file should have these columns:
```csv
driver,timestamp,LapNumber,X,Y,Speed,Throttle,Brake,nGear,RPM,DRS
Lewis Hamilton,2024-08-17T14:30:00Z,1,0.0,0.0,50.5,30.2,false,2,3000,false
Max Verstappen,2024-08-17T14:30:01Z,1,10.5,5.2,75.8,45.1,false,3,4500,true
```

### Streaming Options

```bash
# Basic streaming
python send_stream.py --path data/f1_telemetry_wide.csv

# Custom rate and burst
python send_stream.py --path data/f1_telemetry_wide.csv --rate 100 --burst 5

# Limited records for testing
python send_stream.py --path data/f1_telemetry_wide.csv --limit 1000

# Local development (gateway on localhost)
python send_stream.py --path data/f1_telemetry_wide.csv --base-url http://localhost:5000

# Verbose logging
python send_stream.py --path data/f1_telemetry_wide.csv --verbose
```

### Streaming Parameters

- **`--rate 50`**: Records per second (controls overall throughput)
- **`--burst 10`**: Records sent in each batch (improves efficiency)
- **`--limit -1`**: Max records to process (-1 = all)
- **`--base-url`**: Gateway API URL (docker: `http://gateway:8080`, local: `http://localhost:5000`)

### Example Output

```
2024-08-17 14:30:00,123 - INFO - Starting to stream data from data/f1_telemetry_wide.csv
2024-08-17 14:30:00,124 - INFO - Target: http://gateway:8080/api/telemetry
2024-08-17 14:30:00,124 - INFO - Rate: 50 records/sec, Burst: 10
2024-08-17 14:30:02,456 - INFO - Progress: 100 sent, 0 errors, 49.5 records/sec
2024-08-17 14:30:04,789 - INFO - Progress: 200 sent, 0 errors, 50.1 records/sec
...
2024-08-17 14:30:30,123 - INFO - ==================================================
2024-08-17 14:30:30,123 - INFO - STREAMING COMPLETED
2024-08-17 14:30:30,123 - INFO - Total rows processed: 1500
2024-08-17 14:30:30,123 - INFO - Successfully sent: 1500
2024-08-17 14:30:30,123 - INFO - Errors: 0
2024-08-17 14:30:30,123 - INFO - Success rate: 100.0%
2024-08-17 14:30:30,123 - INFO - Average rate: 50.0 records/sec
2024-08-17 14:30:30,123 - INFO - Total time: 30.0 seconds
```

## 🐳 Docker Commands

### Start Services

```bash
# Complete system
docker-compose up -d --build

# Individual services
docker-compose up postgres -d
docker-compose up datamanager -d
docker-compose up gateway -d
docker-compose up sensorgen -d

# Without sensor generator (for manual testing)
docker-compose up postgres datamanager gateway -d
```

### Monitor and Control

```bash
# View logs
docker-compose logs -f sensorgen    # Streaming progress
docker-compose logs -f gateway      # API requests
docker-compose logs -f datamanager  # gRPC calls

# Restart sensor generator with different parameters
docker-compose stop sensorgen
docker-compose run --rm sensorgen python send_stream.py \
  --path /data/f1_telemetry_wide.csv \
  --base-url http://gateway:8080 \
  --rate 100 \
  --burst 20 \
  --limit 5000

# Stop services
docker-compose down
```

## 🔍 Testing and Verification

### 1. Check Data Streaming

```bash
# Monitor streaming progress
docker-compose logs -f sensorgen

# Should see:
# Progress: 100 sent, 0 errors, 50.0 records/sec
```

### 2. Verify Data in API

```bash
# List telemetries
curl "http://localhost:5000/api/telemetry?page=1&pageSize=10"

# Get aggregation
curl "http://localhost:5000/api/telemetry/aggregate?field=SPEED&type=MAX"
```

### 3. Use Swagger UI

Visit `http://localhost:5000` for interactive testing:
- Browse all API endpoints
- Test queries with different filters
- View response schemas and examples

### 4. Direct Database Access

```bash
# Connect to PostgreSQL
docker exec -it iot-postgres-1 psql -U postgres -d telemetry

# Query data
SELECT driver, COUNT(*) FROM telemetry GROUP BY driver;
SELECT MAX(speed), MIN(speed), AVG(speed) FROM telemetry;
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

## 📁 Repository Structure

```
iot-telemetry-grpc/
├── 📄 README.md                    # This documentation
├── 📄 telemetry.proto              # Protobuf service definition
├── 📄 docker-compose.yml           # Docker Compose configuration
├── 📄 .gitignore                   # Git ignore rules
├── 📄 .env.example                 # Environment template
│
├── 📂 data/                        # CSV data files
│   └── f1_telemetry_wide.csv       # F1 telemetry dataset
│
├── 📂 sensor-generator/            # CSV Data Streamer
│   ├── 📄 send_stream.py           # Main streaming script
│   ├── 📄 requirements.txt         # Python dependencies
│   └── 📄 Dockerfile               # Docker configuration
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

## 🎯 Production Considerations

- **Security**: Implement authentication and authorization
- **Monitoring**: Add health checks, metrics, and logging
- **Scaling**: Configure horizontal scaling for gateway instances  
- **Database**: Implement connection pooling and read replicas
- **API Versioning**: Establish versioning strategy for REST endpoints
- **Rate Limiting**: Add rate limiting for public endpoints
- **SSL/TLS**: Enable HTTPS for production deployments
- **Data Validation**: Enhanced CSV validation and error recovery
- **Batch Processing**: Consider bulk insert optimizations for large datasets

---

**🚀 Quick Start**: 
1. Create `data/f1_telemetry_wide.csv` with your F1 telemetry data
2. Run `docker-compose up -d --build` 
3. Monitor with `docker-compose logs -f sensorgen`
4. View results at `http://localhost:5000`
