import os
import json
import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import requests
import paho.mqtt.client as mqtt
import nats
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MQTT_HOST = os.getenv('MQTT_HOST', 'mqtt')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'telemetry/raw')
MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'analytics-service')

NATS_URL = os.getenv('NATS_URL', 'nats://nats:4222')
NATS_TOPIC = os.getenv('NATS_TOPIC', 'telemetry.predictions')

MLAAS_URL = os.getenv('MLAAS_URL', 'http://mlaas:8000')

LAP_COMPLETION_THRESHOLD = int(os.getenv('LAP_COMPLETION_THRESHOLD', '10'))  # seconds without data

app = FastAPI(title="Analytics Service API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

recent_predictions = []
all_predictions = [] 
max_recent = 50 

@app.get("/predictions")
async def get_predictions():
    return {
        "status": "success",
        "predictions": all_predictions, 
        "total": len(all_predictions)
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "analytics"}


class TelemetryAggregator:
    def __init__(self):
        self.lap_data = defaultdict(lambda: defaultdict(list))
        self.last_update = defaultdict(float)
        self.completed_laps = []
        
    def add_telemetry(self, data: Dict):
        if 'driver' not in data or 'lap_number' not in data:
            return
            
        key = f"{data['driver']}_{data['lap_number']}"
        
        self.lap_data[key]['driver'] = data['driver']
        self.lap_data[key]['lap_number'] = data['lap_number']
        
        if 'speed' in data:
            self.lap_data[key]['speed'].append(data['speed'])
        if 'throttle' in data:
            self.lap_data[key]['throttle'].append(data['throttle'])
        if 'brake' in data:
            self.lap_data[key]['brake'].append(1 if data['brake'] else 0)
        if 'nGear' in data: 
            self.lap_data[key]['n_gear'].append(data['nGear'])
        if 'rpm' in data:
            self.lap_data[key]['rpm'].append(data['rpm'])
        if 'drs' in data:
            self.lap_data[key]['drs'].append(1 if data['drs'] else 0)
        if 'x' in data:
            self.lap_data[key]['x'].append(data['x'])
        if 'y' in data:
            self.lap_data[key]['y'].append(data['y'])
        
        self.last_update[key] = time.time()
        
    def check_completed_laps(self):
        current_time = time.time()
        completed = []
        
        for key, last_time in list(self.last_update.items()):
            if current_time - last_time > LAP_COMPLETION_THRESHOLD:
                if key in self.lap_data and len(self.lap_data[key]['speed']) > 10:
                    lap_summary = self._aggregate_lap_data(self.lap_data[key])
                    completed.append(lap_summary)
                    
                    del self.lap_data[key]
                    del self.last_update[key]
                    
        return completed
    
    def _aggregate_lap_data(self, lap_data: Dict) -> Dict:
        import numpy as np
        
        return {
            'driver': lap_data['driver'],
            'lap_number': lap_data['lap_number'],
            'speed': float(np.mean(lap_data['speed'])),
            'throttle': float(np.mean(lap_data['throttle'])),
            'brake': bool(np.sum(lap_data['brake']) > 0),
            'n_gear': int(np.mean(lap_data['n_gear'])),
            'rpm': float(np.mean(lap_data['rpm'])),
            'drs': bool(np.sum(lap_data['drs']) > 0),
            'x': float(np.mean(lap_data['x'])),
            'y': float(np.mean(lap_data['y'])),
            'timestamp': datetime.now().isoformat()
        }


class AnalyticsService:
    
    def __init__(self):
        self.mqtt_client = None
        self.nats_client = None
        self.aggregator = TelemetryAggregator()
        self.is_running = False
        self.mlaas_available = False
        
    async def start(self):
        logger.info("Starting Analytics Service")
        
        await self.check_mlaas_health()
        
        self.setup_mqtt()
        
        await self.setup_nats()
        
        self.is_running = True
        
        asyncio.create_task(self.process_completed_laps())
        asyncio.create_task(self.health_check_loop())
        
        try:
            while self.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down Analytics Service")
            await self.stop()
            
    async def stop(self):
        self.is_running = False
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            
        if self.nats_client and not self.nats_client.is_closed:
            await self.nats_client.close()
            
    def setup_mqtt(self):
        self.mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        try:
            self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            logger.info(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            raise
            
    async def setup_nats(self):
        try:
            self.nats_client = await nats.connect(NATS_URL)
            logger.info(f"Connected to NATS at {NATS_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise
            
    def on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Successfully connected to MQTT broker")
            client.subscribe(MQTT_TOPIC)
            logger.info(f"Subscribed to topic: {MQTT_TOPIC}")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
            
    def on_mqtt_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT broker, return code: {rc}")
        
    def on_mqtt_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            
            if 'lapNumber' in data:
                data['lap_number'] = data['lapNumber']
            
            if 'driver' not in data or 'lap_number' not in data:
                return
            
            self.aggregator.add_telemetry(data)

            if data.get('lap_number', 0) % 5 == 0:  
                logger.debug(f"Received telemetry: driver={data['driver']}, lap={data['lap_number']}")
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
            logger.error(f"Message payload: {msg.payload.decode()}")
            
    async def process_completed_laps(self):
        while self.is_running:
            try:
                completed_laps = self.aggregator.check_completed_laps()
                
                for lap_data in completed_laps:
                    prediction = await self.get_lap_prediction(lap_data)
                    
                    if prediction:
                        await self.publish_prediction(lap_data, prediction)
                        
            except Exception as e:
                logger.error(f"Error processing completed laps: {e}")
                
            await asyncio.sleep(5)  
            
    async def get_lap_prediction(self, lap_data: Dict) -> Optional[Dict]:
        if not self.mlaas_available:
            logger.warning("MLaaS not available, skipping prediction")
            return None
            
        try:
            request_data = {
                'driver': lap_data['driver'],
                'lap_number': lap_data['lap_number'],
                'speed': lap_data['speed'],
                'throttle': lap_data['throttle'] / 100.0,  
                'brake': lap_data['brake'],
                'n_gear': lap_data['n_gear'],
                'rpm': lap_data['rpm'],
                'drs': lap_data['drs'],
                'x': lap_data['x'],
                'y': lap_data['y']
            }
            
            response = requests.post(
                f"{MLAAS_URL}/predict",
                json=request_data,
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"MLaaS prediction failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling MLaaS: {e}")
            return None
            
    async def publish_prediction(self, lap_data: Dict, prediction: Dict):
        try:
            message = {
                'driver': lap_data['driver'],
                'lap_number': lap_data['lap_number'],
                'predicted_lap_time': prediction['predicted_lap_time'],
                'confidence_interval': prediction['confidence_interval'],
                'actual_telemetry': {
                    'avg_speed': lap_data['speed'],
                    'avg_throttle': lap_data['throttle'] / 100.0,  # Convert to 0-1 range for display
                    'avg_rpm': lap_data['rpm'],
                    'used_drs': lap_data['drs'],
                    'used_brake': lap_data['brake']
                },
                'timestamp': datetime.now().isoformat(),
                'model_version': prediction.get('model_version', 'unknown')
            }
            
            await self.nats_client.publish(
                NATS_TOPIC,
                json.dumps(message).encode()
            )
            
            global recent_predictions, all_predictions
            

            all_predictions.append(message)
            
            recent_predictions.append(message)
            if len(recent_predictions) > max_recent:
                recent_predictions = recent_predictions[-max_recent:]
            
            logger.info(
                f"Published prediction for {lap_data['driver']} lap {lap_data['lap_number']}: "
                f"{prediction['predicted_lap_time']:.2f}s"
            )
            
        except Exception as e:
            logger.error(f"Error publishing to NATS: {e}")
            
    async def check_mlaas_health(self):
        try:
            response = requests.get(f"{MLAAS_URL}/health", timeout=5)
            self.mlaas_available = response.status_code == 200
            
            if self.mlaas_available:
                logger.info("MLaaS service is available")
            else:
                logger.warning("MLaaS service is not responding")
                
        except Exception as e:
            logger.warning(f"Cannot reach MLaaS service: {e}")
            self.mlaas_available = False
            
    async def health_check_loop(self):
        while self.is_running:
            await self.check_mlaas_health()
            await asyncio.sleep(30) 


def start_api_server():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

async def main():
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    logger.info("Started FastAPI server on port 8080")
    
    service = AnalyticsService()
    await service.start()


if __name__ == "__main__":
    asyncio.run(main())
