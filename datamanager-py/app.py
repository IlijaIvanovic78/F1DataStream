import os, sys, time, logging, pathlib
from pathlib import Path
from concurrent import futures
from datetime import datetime, timezone
from typing import Optional, List

import psycopg
from psycopg.rows import dict_row
import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).parent.joinpath("gen")))
import telemetry_pb2, telemetry_pb2_grpc

from mqtt_client import MqttPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

publisher = MqttPublisher()

def proto_to_dt(ts: Timestamp) -> datetime:
    return ts.ToDatetime().replace(tzinfo=timezone.utc)

def dt_to_proto(dt: datetime) -> Timestamp:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts

def row_to_proto(row) -> telemetry_pb2.Telemetry:
    t = telemetry_pb2.Telemetry()
    t.id = row["id"]
    t.driver = row["driver"]
    t.timestamp.CopyFrom(dt_to_proto(row["timestamp"]))
    t.lap_number = row["lap_number"]
    t.x = float(row["x"])
    t.y = float(row["y"])
    t.speed = float(row["speed"])
    t.throttle = float(row["throttle"])
    t.brake = bool(row["brake"])
    t.n_gear = row["n_gear"]
    t.rpm = float(row["rpm"])
    t.drs = bool(row["drs"])
    return t

class DatabaseManager:
    def __init__(self):
        self.conn: Optional[psycopg.Connection] = None
        self.host = os.getenv("POSTGRES_HOST", "postgres")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.user = os.getenv("POSTGRES_USER", "postgres")
        self.password = os.getenv("POSTGRES_PASSWORD", "postgres")
        self.db = os.getenv("POSTGRES_DB", "telemetry")

    def connect(self, retries: int = 10, delay: float = 2.0) -> bool:
        dsn = f"host={self.host} port={self.port} dbname={self.db} user={self.user} password={self.password}"
        for attempt in range(1, retries + 1):
            try:
                self.conn = psycopg.connect(dsn, row_factory=dict_row, autocommit=True)
                logger.info("Connected to PostgreSQL (%s:%s)", self.host, self.port)
                self.init_db()
                return True
            except Exception as e:
                logger.warning("PostgreSQL not ready (attempt %d/%d): %s", attempt, retries, e)
                time.sleep(delay)
        logger.error("Failed to connect to PostgreSQL after %d attempts.", retries)
        return False

    def disconnect(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("PostgreSQL connection closed.")

    def get_connection(self) -> psycopg.Connection:
        if not self.conn or self.conn.closed:
            raise RuntimeError("Database connection not available")
        return self.conn

    def init_db(self):
        sql = """
        CREATE TABLE IF NOT EXISTS telemetry (
            id BIGSERIAL PRIMARY KEY,
            driver TEXT NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            lap_number INT NOT NULL,
            x DOUBLE PRECISION NOT NULL,
            y DOUBLE PRECISION NOT NULL,
            speed DOUBLE PRECISION NOT NULL,
            throttle DOUBLE PRECISION NOT NULL,
            brake BOOLEAN NOT NULL,
            n_gear INT NOT NULL,
            rpm DOUBLE PRECISION NOT NULL,
            drs BOOLEAN NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_telemetry_driver ON telemetry(driver);
        CREATE INDEX IF NOT EXISTS idx_telemetry_lap ON telemetry(lap_number);
        CREATE INDEX IF NOT EXISTS idx_telemetry_ts ON telemetry(timestamp);
        """
        conn = self.get_connection()
        with conn.cursor() as cur:
            cur.execute(sql)
        logger.info("DB schema ensured.")

class TelemetryServiceImpl(telemetry_pb2_grpc.TelemetryServiceServicer):
    def __init__(self, db: DatabaseManager):
        self.db = db

    def CreateTelemetry(self, request, context):
        t = request.telemetry
        sql = """
            INSERT INTO telemetry (driver, timestamp, lap_number, x, y, speed, throttle, brake, n_gear, rpm, drs)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """
        vals = (
            t.driver,
            proto_to_dt(t.timestamp),
            t.lap_number,
            t.x, t.y,
            t.speed, t.throttle,
            t.brake,
            t.n_gear,
            t.rpm,
            t.drs
        )
        try:
            with self.db.get_connection().cursor() as cur:
                cur.execute(sql, vals)
                new_id = cur.fetchone()["id"]
            
            t_out = telemetry_pb2.Telemetry()
            t_out.CopyFrom(t)
            t_out.id = new_id
            
            publisher.publish({
                "id": t_out.id,
                "driver": t_out.driver,
                "timestampUtc": t_out.timestamp.ToDatetime().isoformat() + "Z",
                "lapNumber": t_out.lap_number,
                "x": t_out.x,
                "y": t_out.y,
                "speed": t_out.speed,
                "throttle": t_out.throttle,
                "brake": t_out.brake,
                "nGear": t_out.n_gear,
                "rpm": t_out.rpm,
                "drs": t_out.drs
            })
            
            return telemetry_pb2.CreateTelemetryResponse(telemetry=t_out, success=True, message="Created")
        except Exception as e:
            logger.exception("CreateTelemetry failed")
            return telemetry_pb2.CreateTelemetryResponse(success=False, message=str(e))

    def GetTelemetry(self, request, context):
        sql = "SELECT * FROM telemetry WHERE id=%s"
        with self.db.get_connection().cursor() as cur:
            cur.execute(sql, (request.id,))
            row = cur.fetchone()
        if not row:
            return telemetry_pb2.GetTelemetryResponse(found=False)
        return telemetry_pb2.GetTelemetryResponse(telemetry=row_to_proto(row), found=True)

    def UpdateTelemetry(self, request, context):
        t = request.telemetry
        if t.id == 0:
            return telemetry_pb2.UpdateTelemetryResponse(success=False, message="ID required")
        sql = """
            UPDATE telemetry
            SET driver=%s, timestamp=%s, lap_number=%s, x=%s, y=%s, speed=%s,
                throttle=%s, brake=%s, n_gear=%s, rpm=%s, drs=%s
            WHERE id=%s RETURNING *
        """
        vals = (
            t.driver, proto_to_dt(t.timestamp), t.lap_number, t.x, t.y, t.speed,
            t.throttle, t.brake, t.n_gear, t.rpm, t.drs, t.id
        )
        with self.db.get_connection().cursor() as cur:
            cur.execute(sql, vals)
            row = cur.fetchone()
        if not row:
            return telemetry_pb2.UpdateTelemetryResponse(success=False, message="Not found")
        return telemetry_pb2.UpdateTelemetryResponse(
            telemetry=row_to_proto(row),
            success=True,
            message="Updated"
        )

    def DeleteTelemetry(self, request, context):
        sql = "DELETE FROM telemetry WHERE id=%s RETURNING id"
        with self.db.get_connection().cursor() as cur:
            cur.execute(sql, (request.id,))
            row = cur.fetchone()
        if not row:
            return telemetry_pb2.DeleteTelemetryResponse(success=False, message="Not found")
        return telemetry_pb2.DeleteTelemetryResponse(success=True, message="Deleted")

    def ListTelemetry(self, request, context):
        page = max(1, request.page or 1)
        size = max(1, min(100, request.page_size or 10))
        where = []
        params: List = []
        if request.driver_filter:
            where.append("driver = %s")
            params.append(request.driver_filter)
        if request.lap_filter:
            where.append("lap_number = %s")
            params.append(request.lap_filter)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        count_sql = f"SELECT COUNT(*) AS c FROM telemetry {where_sql}"
        list_sql = f"""
            SELECT * FROM telemetry
            {where_sql}
            ORDER BY id
            LIMIT %s OFFSET %s
        """
        with self.db.get_connection().cursor() as cur:
            cur.execute(count_sql, params)
            total = cur.fetchone()["c"]
            cur.execute(list_sql, params + [size, (page - 1) * size])
            rows = cur.fetchall()
        telemetries = [row_to_proto(r) for r in rows]
        total_pages = (total + size - 1) // size if total else 0
        return telemetry_pb2.ListTelemetryResponse(
            telemetries=telemetries,
            total_count=total,
            page=page,
            page_size=size,
            total_pages=total_pages
        )

    def Aggregate(self, request, context):
        field_map = {
            telemetry_pb2.SPEED: "speed",
            telemetry_pb2.RPM: "rpm",
            telemetry_pb2.THROTTLE: "throttle",
            telemetry_pb2.X: "x",
            telemetry_pb2.Y: "y",
        }
        agg_map = {
            telemetry_pb2.MIN: "MIN",
            telemetry_pb2.MAX: "MAX",
            telemetry_pb2.AVG: "AVG",
            telemetry_pb2.SUM: "SUM",
        }
        field = field_map.get(request.field)
        func = agg_map.get(request.type)
        if not field or not func:
            return telemetry_pb2.AggregateResponse(success=False, message="Invalid field or type")
        where = []
        params: List = []
        if request.driver_filter:
            where.append("driver = %s")
            params.append(request.driver_filter)
        if request.lap_filter:
            where.append("lap_number = %s")
            params.append(request.lap_filter)
        if request.start_time.seconds or request.start_time.nanos:
            where.append("timestamp >= %s")
            params.append(proto_to_dt(request.start_time))
        if request.end_time.seconds or request.end_time.nanos:
            where.append("timestamp <= %s")
            params.append(proto_to_dt(request.end_time))
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        sql = f"SELECT {func}({field}) AS value, COUNT(*) AS cnt FROM telemetry {where_sql}"
        with self.db.get_connection().cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        if not row or row["cnt"] == 0 or row["value"] is None:
            return telemetry_pb2.AggregateResponse(success=False, message="No data", count=0, value=0.0)
        return telemetry_pb2.AggregateResponse(
            value=float(row["value"]),
            count=row["cnt"],
            success=True,
            message="OK"
        )

db_manager = DatabaseManager()

def init_database() -> bool:
    if db_manager.connect():
        return True
    logger.error("Failed to initialize database. Exiting.")
    return False

def serve():
    logger.info("Starting Telemetry gRPC Server...")
    if not init_database():
        return
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    telemetry_pb2_grpc.add_TelemetryServiceServicer_to_server(
        TelemetryServiceImpl(db_manager), server
    )
    listen_addr = f"{os.getenv('GRPC_HOST','0.0.0.0')}:{os.getenv('GRPC_PORT','50051')}"
    server.add_insecure_port(listen_addr)
    server.start()
    logger.info("gRPC listening on %s", listen_addr)
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.stop(5)
        db_manager.disconnect()

if __name__ == "__main__":
    serve()