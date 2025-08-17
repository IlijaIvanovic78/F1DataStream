#!/usr/bin/env python3
"""
CSV to REST API Telemetry Data Streamer

Reads F1 telemetry data from CSV and streams it to the Gateway API.
Supports rate limiting, burst sending, and progress tracking.
"""

import argparse
import csv
import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

import requests
from dateutil import parser as date_parser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelemetryStreamer:
    """Streams telemetry data from CSV to REST API"""
    
    def __init__(self, base_url: str, rate: int = 50, burst: int = 1):
        self.base_url = base_url.rstrip('/')
        self.api_endpoint = f"{self.base_url}/api/telemetry"
        self.rate = rate
        self.burst = burst
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'TelemetryStreamer/1.0'
        })
        
        # Statistics
        self.total_sent = 0
        self.total_errors = 0
        self.start_time = None
    
    def parse_boolean(self, value: str) -> bool:
        """Parse various boolean representations"""
        if isinstance(value, bool):
            return value
        value_str = str(value).strip().lower()
        return value_str in ('true', '1', 'yes', 'on')
    
    def parse_timestamp(self, timestamp_str: str) -> str:
        """Parse timestamp to ISO 8601 UTC format"""
        try:
            # Parse the timestamp using dateutil (handles many formats)
            dt = date_parser.parse(timestamp_str)
            
            # Ensure UTC timezone
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            
            # Return ISO format
            return dt.isoformat().replace('+00:00', 'Z')
        except Exception as e:
            logger.error(f"Failed to parse timestamp '{timestamp_str}': {e}")
            raise
    
    def csv_row_to_dto(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Convert CSV row to CreateTelemetryDto format"""
        try:
            return {
                "driver": row["driver"].strip(),
                "timestampUtc": self.parse_timestamp(row["timestamp"]),
                "lapNumber": int(row["LapNumber"]),
                "x": float(row["X"]),
                "y": float(row["Y"]),
                "speed": float(row["Speed"]),
                "throttle": float(row["Throttle"]),
                "brake": self.parse_boolean(row["Brake"]),
                "nGear": int(float(row["nGear"])),  # Convert to float first, then to int
                "rpm": float(row["RPM"]),
                "drs": self.parse_boolean(row["DRS"])
            }
        except (ValueError, KeyError) as e:
            logger.error(f"Failed to convert row to DTO: {e}")
            logger.error(f"Row data: {row}")
            raise
    
    def send_telemetry_batch(self, telemetry_batch: List[Dict[str, Any]]) -> bool:
        """Send a batch of telemetry records"""
        success_count = 0
        
        for telemetry in telemetry_batch:
            if self.send_single_telemetry(telemetry):
                success_count += 1
        
        return success_count == len(telemetry_batch)
    
    def send_single_telemetry(self, telemetry: Dict[str, Any], max_retries: int = 3) -> bool:
        """Send single telemetry record with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    self.api_endpoint,
                    json=telemetry,
                    timeout=10
                )
                
                if response.status_code == 201:
                    self.total_sent += 1
                    return True
                elif response.status_code >= 500:
                    # Server error - retry with backoff
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Server error {response.status_code} on attempt {attempt + 1}/{max_retries}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    # Client error - don't retry
                    logger.error(
                        f"Client error {response.status_code}: {response.text[:200]}"
                    )
                    self.total_errors += 1
                    return False
                    
            except requests.exceptions.RequestException as e:
                wait_time = 2 ** attempt
                logger.warning(
                    f"Network error on attempt {attempt + 1}/{max_retries}: {e}. "
                    f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
        
        # All retries failed
        logger.error(f"Failed to send telemetry after {max_retries} attempts")
        self.total_errors += 1
        return False
    
    def stream_csv(self, csv_path: str, limit: int = -1):
        """Stream CSV data to API"""
        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        logger.info(f"Starting to stream data from {csv_path}")
        logger.info(f"Target: {self.api_endpoint}")
        logger.info(f"Rate: {self.rate} records/sec, Burst: {self.burst}")
        
        self.start_time = time.time()
        batch = []
        rows_processed = 0
        
        # Calculate sleep time between bursts
        sleep_time = self.burst / self.rate if self.rate > 0 else 0
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # Validate required columns
                required_cols = {'driver', 'timestamp', 'LapNumber', 'X', 'Y', 
                               'Speed', 'Throttle', 'Brake', 'nGear', 'RPM', 'DRS'}
                if not required_cols.issubset(reader.fieldnames or []):
                    missing = required_cols - set(reader.fieldnames or [])
                    raise ValueError(f"Missing required columns: {missing}")
                
                for row in reader:
                    if limit > 0 and rows_processed >= limit:
                        break
                    
                    try:
                        telemetry_dto = self.csv_row_to_dto(row)
                        batch.append(telemetry_dto)
                        rows_processed += 1
                        
                        # Send when batch is full
                        if len(batch) >= self.burst:
                            self.send_telemetry_batch(batch)
                            batch = []
                            
                            # Progress logging
                            if self.total_sent > 0 and self.total_sent % 100 == 0:
                                elapsed = time.time() - self.start_time
                                rate = self.total_sent / elapsed
                                logger.info(
                                    f"Progress: {self.total_sent} sent, {self.total_errors} errors, "
                                    f"{rate:.1f} records/sec"
                                )
                            
                            # Rate limiting
                            if sleep_time > 0:
                                time.sleep(sleep_time)
                    
                    except Exception as e:
                        logger.error(f"Failed to process row {rows_processed}: {e}")
                        self.total_errors += 1
                        continue
                
                # Send remaining batch
                if batch:
                    self.send_telemetry_batch(batch)
        
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            raise
        
        # Final statistics
        elapsed = time.time() - self.start_time
        logger.info("=" * 50)
        logger.info("STREAMING COMPLETED")
        logger.info(f"Total rows processed: {rows_processed}")
        logger.info(f"Successfully sent: {self.total_sent}")
        logger.info(f"Errors: {self.total_errors}")
        logger.info(f"Success rate: {(self.total_sent/max(rows_processed,1))*100:.1f}%")
        logger.info(f"Average rate: {self.total_sent/elapsed:.1f} records/sec")
        logger.info(f"Total time: {elapsed:.1f} seconds")


def main():
    parser = argparse.ArgumentParser(
        description="Stream F1 telemetry data from CSV to REST API"
    )
    parser.add_argument(
        "--path", 
        required=True, 
        help="Path to CSV file with telemetry data"
    )
    parser.add_argument(
        "--base-url", 
        default="http://gateway:8080",
        help="Base URL of the Gateway API (default: http://gateway:8080)"
    )
    parser.add_argument(
        "--rate", 
        type=int, 
        default=50,
        help="Records per second (default: 50)"
    )
    parser.add_argument(
        "--burst", 
        type=int, 
        default=1,
        help="Number of records to send in each burst (default: 1)"
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=-1,
        help="Maximum number of records to process (-1 for all, default: -1)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        streamer = TelemetryStreamer(
            base_url=args.base_url,
            rate=args.rate,
            burst=args.burst
        )
        
        streamer.stream_csv(
            csv_path=args.path,
            limit=args.limit
        )
        
    except KeyboardInterrupt:
        logger.info("Streaming interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Streaming failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()