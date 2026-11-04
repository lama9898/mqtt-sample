"""Local FastAPI/MQTT learning sample; no external database required."""
import json
import logging
from collections import deque
from contextlib import asynccontextmanager
from threading import Event, Lock

import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError

TOPIC = "sample/chat/messages"
log = logging.getLogger(__name__)


class Message(BaseModel):
    sender: str = Field(min_length=1, max_length=80)
    recipient: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=2000)


class MessageBridge:
    def __init__(self):
        self.ready = Event()
        self.lock = Lock()
        self.messages = deque(maxlen=1000)
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_subscribe = self.on_subscribe
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        self.ready.clear()
        if rc == 0:
            client.subscribe(TOPIC, qos=1)

    def on_subscribe(self, client, userdata, mid, granted_qos):
        if granted_qos and all(qos in (0, 1, 2) for qos in granted_qos):
            self.ready.set()

    def on_disconnect(self, client, userdata, rc):
        self.ready.clear()

    def on_message(self, client, userdata, msg):
        if msg.topic != TOPIC or len(msg.payload) > 16384:
            return
        try:
            message = Message.model_validate_json(msg.payload)
        except (ValidationError, ValueError):
            log.warning("Ignored invalid MQTT payload")
            return
        with self.lock:
            self.messages.append(message.model_dump())

    def read(self, recipient):
        with self.lock:
            return [dict(item) for item in self.messages if item['recipient'] == recipient]

    def publish(self, message):
        if not self.ready.is_set():
            raise HTTPException(503, "MQTT broker is not ready")
        result = self.client.publish(TOPIC, message.model_dump_json(), qos=1)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise HTTPException(503, "MQTT publish failed")
        try:
            result.wait_for_publish(timeout=3)
            if not result.is_published():
                raise HTTPException(504, "MQTT acknowledgement timed out")
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(503, "MQTT publish failed") from exc


bridge = MessageBridge()


@asynccontextmanager
async def lifespan(app):
    # connect_async lets the API report 503 while the local broker is unavailable.
    bridge.client.connect_async("127.0.0.1", 1883, 60)
    bridge.client.loop_start()
    try:
        yield
    finally:
        bridge.client.disconnect()
        bridge.client.loop_stop()
        bridge.ready.clear()


app = FastAPI(title="FastAPI MQTT Learning Sample", lifespan=lifespan)


@app.get('/health')
def health():
    return {'mqtt_ready': bridge.ready.is_set()}


@app.post('/send/', status_code=202)
def send_message(message: Message):
    bridge.publish(message)
    return {'status': 'published', 'note': 'Subscriber storage is asynchronous'}


@app.get('/messages/{recipient}')
def get_messages(recipient: str):
    return {'messages': bridge.read(recipient)}
