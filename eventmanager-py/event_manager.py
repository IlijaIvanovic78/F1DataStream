import os
import json
import time
import logging
from typing import Dict, Any, List
import paho.mqtt.client as mqtt
from dateutil import parser as dateparser


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EventManager')

MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC_IN = os.getenv("MQTT_TOPIC_RAW", "telemetry/raw")
TOPIC_OUT = os.getenv("MQTT_TOPIC_EVENTS", "telemetry/events")
QOS = int(os.getenv("MQTT_QOS", "1"))

SPEED_MAX = float(os.getenv("RULE_SPEED_MAX", "310"))
RPM_MAX = float(os.getenv("RULE_RPM_MAX", "11500"))
BRAKE_ALERT_SPEED = float(os.getenv("RULE_BRAKE_ALERT_SPEED", "280"))


events_detected = 0
messages_processed = 0

client = mqtt.Client(
    client_id=os.getenv("MQTT_CLIENT_ID", "eventmanager-sub"), 
    clean_session=True
)


def detect_events(msg: Dict[str, Any]) -> List[Dict[str, Any]]:
    global events_detected
    
    events = []
    
    try:
        spd = float(msg.get("speed", 0))
        rpm = float(msg.get("rpm", 0))
        brake = bool(msg.get("brake", False))
        ts = msg.get("timestampUtc")
        
        try:
            ts_iso = dateparser.parse(ts).isoformat()
        except Exception:
            ts_iso = ts 
        
        base = {
            "driver": msg.get("driver"),
            "lapNumber": msg.get("lapNumber"),
            "timestampUtc": ts_iso,
            "x": msg.get("x"),
            "y": msg.get("y")
        }
        
        if spd > SPEED_MAX:
            events.append({
                **base,
                "type": "SPEED_OVER_LIMIT",
                "value": spd,
                "limit": SPEED_MAX
            })
            logger.warning(f"SPEED_OVER_LIMIT: {msg.get('driver')} - {spd} km/h > {SPEED_MAX}")
        
        if rpm > RPM_MAX:
            events.append({
                **base,
                "type": "RPM_OVER_LIMIT",
                "value": rpm,
                "limit": RPM_MAX
            })
            logger.warning(f"RPM_OVER_LIMIT: {msg.get('driver')} - {rpm} RPM > {RPM_MAX}")
        
        if brake and spd > BRAKE_ALERT_SPEED:
            events.append({
                **base,
                "type": "HARD_BRAKE_AT_HIGH_SPEED",
                "value": spd,
                "limit": BRAKE_ALERT_SPEED
            })
            logger.warning(f"HARD_BRAKE_AT_HIGH_SPEED: {msg.get('driver')} - braking at {spd} km/h")
        
        events_detected += len(events)
        return events
        
    except Exception as e:
        logger.error(f"Error detecting events: {e}")
        return []


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"Connected to MQTT broker {MQTT_HOST}:{MQTT_PORT}")
        client.subscribe(TOPIC_IN, qos=QOS)
        logger.info(f"Subscribed to topic: {TOPIC_IN}")
        logger.info(f"Will publish events to: {TOPIC_OUT}")
        logger.info(f"Event detection rules:")
        logger.info(f"  - Speed limit: {SPEED_MAX} km/h")
        logger.info(f"  - RPM limit: {RPM_MAX}")
        logger.info(f"  - Brake alert speed: {BRAKE_ALERT_SPEED} km/h")
    else:
        logger.error(f"Failed to connect to MQTT broker: {rc}")


def on_disconnect(client, userdata, rc):
    logger.warning(f"Disconnected from MQTT broker: {rc}")


def on_message(client, userdata, message):
    global messages_processed
    
    try:

        payload = json.loads(message.payload.decode("utf-8"))
        messages_processed += 1
        

        if messages_processed % 100 == 0:
            logger.info(f"Processed {messages_processed} messages, detected {events_detected} events")
        

        detected_events = detect_events(payload)
        
        for event in detected_events:
            try:
                event_json = json.dumps(event, default=str)
                result = client.publish(TOPIC_OUT, event_json, qos=QOS, retain=False)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug(f"Published event: {event['type']} for driver {event['driver']}")
                else:
                    logger.error(f"Failed to publish event: {result.rc}")
                    
            except Exception as e:
                logger.error(f"Error publishing event: {e}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in telemetry message: {e}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")


def main():
    logger.info("Starting EventManager microservice...")
    

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    

    try:
        logger.info(f"Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
        client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=30)
        
        client.loop_forever()
        
    except KeyboardInterrupt:
        logger.info("EventManager stopped by user")
        client.disconnect()
    except Exception as e:
        logger.error(f"EventManager failed: {e}")
        client.disconnect()


if __name__ == "__main__":
    main()