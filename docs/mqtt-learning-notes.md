# MQTT 채팅 구현 기록

2024년 8월, 부트캠프 프로젝트에서 채팅 기능을 구현하며 노션에 정리한 내용입니다.

## 1. React에서 MQTT로 직접 전송

처음에는 React에서 Mosquitto 브로커에 직접 연결해 메시지를 발행하고 구독하는 방식으로 구현했습니다.

```text
React → MQTT 브로커
```

브로커에 MQTT용 포트와 브라우저 연결을 위한 WebSocket용 포트를 설정했습니다.
아래는 로컬 실행용 설정입니다.

```conf
listener 1883 127.0.0.1
protocol mqtt

listener 1884 127.0.0.1
protocol websockets

allow_anonymous true
```

React에서는 MQTT.js로 연결한 뒤 토픽을 구독하고, 메시지가 도착하면 화면에 표시했습니다.

```javascript
const client = mqtt.connect('ws://127.0.0.1:1884');

client.on('connect', () => {
  client.subscribe('test/topic');
});

client.on('message', (topic, message) => {
  setMessage(message.toString());
});

// 전송 버튼 클릭 시
client.publish('test/topic', 'Hello MQTT!');
```

## 2. REST API를 거쳐 MQTT로 전송

이후 React에서 MQTT로 직접 요청하던 방식을 변경했습니다.
React가 REST API를 호출하면 FastAPI 서버에서 메시지를 MQTT로 발행하도록 구현했습니다.

```text
React → REST API(FastAPI) → MQTT 브로커
```

- `POST /send/`: 발신자, 수신자, 내용을 받아 MQTT 메시지로 발행
- MQTT 구독 콜백: 메시지를 받아 수신자별로 저장
- `GET /messages/{recipient}`: 해당 수신자의 메시지 조회

Python에서는 `paho-mqtt`를 사용했습니다.
당시 콜백 형식에 맞춰 2.0 미만 버전을 사용했으며, 현재 저장소는 1.6.1로 지정되어 있습니다.

## 3. 토픽 구독과 서버 시작·종료 처리

`chat/#`를 구독해 `chat` 아래의 토픽을 받도록 구성했습니다.
`+`는 한 단계, `#`는 여러 단계의 토픽을 구독할 때 사용하는 와일드카드입니다.

기존에는 `@app.on_event("startup")`과 `@app.on_event("shutdown")`으로
서버 시작 시 토픽을 구독하고, 종료 시 MQTT 루프를 멈추고 연결을 해제했습니다.

변경 전:

```python
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    mqtt_client.subscribe("chat/messages")

@app.on_event("shutdown")
async def shutdown_event():
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
```

이후 시작·종료 작업을 `start()`와 `shutdown()` 함수로 나누고,
`@asynccontextmanager`를 적용한 `lifespan()`에서 호출하도록 변경했습니다.
`yield` 앞에서는 시작 작업을, 뒤에서는 종료 작업을 처리합니다.
구독 토픽도 `chat/messages`에서 `chat/#`로 변경했습니다.

변경 후:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

def start():
    print("service is started.")
    mqtt_client.subscribe("chat/#")

def shutdown():
    print("service is stopped.")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

@asynccontextmanager
async def lifespan(app: FastAPI):
    start()
    yield
    shutdown()

app = FastAPI(lifespan=lifespan)
```

위 코드는 당시 MQTT 연결 코드 중 시작·종료 처리 부분입니다.

## 4. Oracle DB 설정 파일 경로 수정

Python에서 Oracle DB에 연결하기 위해 `database.ini`와 `model.py`를 사용했습니다.
설정 파일을 찾지 못하는 문제가 있어, 실행 위치 대신 Python 파일 위치를 기준으로 경로를 구성했습니다.

```python
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, 'database.ini')
config.read(config_path, encoding='utf8')
```

## 현재 저장소

현재 [실행 코드](../src/main.py)는 `sample/chat/messages` 토픽을 사용하고,
Oracle DB 대신 메모리에 메시지를 저장합니다. (테스트용)
React 연결 예제와 과거 구현 흐름은 이 문서에 정리했습니다.

## 참고 자료

- [MQTT.js](https://github.com/mqttjs/MQTT.js)
- [Paho Python](https://eclipse.dev/paho/clients/python/docs/)
- [Mosquitto](https://mosquitto.org/documentation/)
- [MQTT 와일드카드 참고](https://medium.com/@jspark141515/mqtt-실전-응용하기-wildcard-9643877262f2)
- [FastAPI lifespan 참고](https://limsw.tistory.com/142)
