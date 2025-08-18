import json
import os
import threading
from typing import Any, Dict
import paho.mqtt.client as mqtt
import logging

logger = logging.getLogger(__name__)


class MqttPublisher:
    def __init__(self):
        self.host = os.getenv("MQTT_HOST", "mqtt")
        self.port = int(os.getenv("MQTT_PORT", "1883"))
        self.topic = os.getenv("MQTT_TOPIC_RAW", "telemetry/raw")
        self.qos = int(os.getenv("MQTT_QOS", "1"))
        
        self._client = mqtt.Client(
            client_id=os.getenv("MQTT_CLIENT_ID", "datamanager-pub"), 
            clean_session=True
        )
        self._lock = threading.Lock()
        self._connected = False
        
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        
        try:
            self._client.connect_async(self.host, self.port, keepalive=30)
            self._client.loop_start()
            logger.info(f"MQTT client connecting to {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start MQTT client: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        self._connected = (rc == 0)
        if self._connected:
            logger.info(f"MQTT connected to {self.host}:{self.port}")
        else:
            logger.warning(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        logger.warning(f"MQTT disconnected with code {rc}")

    def publish(self, payload: Dict[str, Any]):
        try:
            data = json.dumps(payload, default=str)
            
            with self._lock:
                if not self._connected:
                    try:
                        self._client.reconnect()
                    except Exception as e:
                        logger.warning(f"MQTT reconnect failed: {e}")
                
                result = self._client.publish(self.topic, data, qos=self.qos, retain=False)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug(f"Published telemetry to {self.topic}: driver={payload.get('driver')}")
                else:
                    logger.warning(f"MQTT publish failed with code {result.rc}")
                    
        except Exception as e:
            logger.error(f"Failed to publish MQTT message: {e}")

    def disconnect(self):
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            logger.info("MQTT client disconnected")