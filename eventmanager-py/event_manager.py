import os
import json
import time
import logging
from typing import Dict, Any, List
import paho.mqtt.client as mqtt
from dateutil import parser as dateparser

logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger('EventManager')
logger.setLevel(logging.CRITICAL)

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
        
        if rpm > RPM_MAX:
            events.append({
                **base,
                "type": "RPM_OVER_LIMIT",
                "value": rpm,
                "limit": RPM_MAX
            })
        
        if brake and spd > BRAKE_ALERT_SPEED:
            events.append({
                **base,
                "type": "HARD_BRAKE_AT_HIGH_SPEED",
                "value": spd,
                "limit": BRAKE_ALERT_SPEED
            })
        
        events_detected += len(events)
        return events
        
    except Exception as e:
        return []


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(TOPIC_IN, qos=QOS)
    else:
        pass


def on_disconnect(client, userdata, rc):
    pass


def on_message(client, userdata, message):
    global messages_processed
    
    try:

        payload = json.loads(message.payload.decode("utf-8"))
        messages_processed += 1
        
        detected_events = detect_events(payload)
        
        for event in detected_events:
            try:
                event_json = json.dumps(event, default=str)
                result = client.publish(TOPIC_OUT, event_json, qos=QOS, retain=False)
                    
            except Exception as e:
                pass
        
    except json.JSONDecodeError as e:
        pass
    except Exception as e:
        pass


def main():
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    

    try:
        client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=30)
        
        client.loop_forever()
        
    except KeyboardInterrupt:
        client.disconnect()
    except Exception as e:
        client.disconnect()


if __name__ == "__main__":
    main()