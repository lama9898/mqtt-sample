# FastAPI + MQTT 채팅 샘플

2024년 부트캠프 프로젝트에서 채팅 기능을 구현하며 작성한 코드입니다.
처음에는 React에서 MQTT 브로커에 직접 메시지를 보내는 방식으로 구현했고,
이후 React에서 REST API를 호출하면 FastAPI 서버가 MQTT로 메시지를 발행하는 방식으로 변경했습니다.

## 구현 내용

- Mosquitto 브로커 설정
- React에서 MQTT 메시지 발행·구독
- FastAPI를 통한 메시지 전송 API 구현
- `lifespan`으로 서버 시작 시 MQTT 구독 및 종료 시 연결 해제 처리
- MQTT로 수신한 메시지를 수신자별로 조회하는 API 구현
- Python과 Oracle DB 연동 코드 작성

당시 구현 과정은 [채팅 구현 기록](docs/mqtt-learning-notes.md)에 정리했습니다.
현재 저장소는 별도 DB 설정 없이 실행할 수 있도록 메시지를 메모리에 저장합니다.

## 메시지 전송 구조

```text
초기: React → MQTT 브로커
변경: React → REST API(FastAPI) → MQTT 브로커
```

FastAPI 서버는 MQTT 토픽을 구독하고, 수신한 메시지를 저장합니다.
`GET /messages/{recipient}`로 수신자별 메시지를 조회할 수 있습니다.

## 실행

Python 3.12와 [Mosquitto](https://mosquitto.org/download/)를 사용합니다.
저장소 폴더에서 아래 명령을 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Mosquitto 실행:

```powershell
& 'C:\Program Files\mosquitto\mosquitto.exe' -c .\mosquitto.conf -v
```

다른 터미널에서 API 실행:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

API 문서: http://127.0.0.1:8000/docs

## API

| 메서드 | 경로 | 기능 |
|---|---|---|
| GET | `/health` | MQTT 연결 준비 상태 확인 |
| POST | `/send/` | 메시지 발행 |
| GET | `/messages/{recipient}` | 수신자별 메시지 조회 |

메시지 전송 예시:

```json
{
  "sender": "alice",
  "recipient": "bob",
  "content": "Hello MQTT"
}
```

## 테스트

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 실행 시 참고

- 로컬 실행용이며 사용자 인증과 채팅방 권한 검사는 포함하지 않습니다.
- 메시지는 전체 최근 1,000건까지 저장하며 서버를 종료하면 사라집니다. 단일 worker로 실행합니다.
- 메시지 수신은 비동기로 처리되므로 전송 직후 조회에는 아직 반영되지 않을 수 있습니다.
- 실제 Mosquitto 송수신 확인은 위 실행 절차로 진행합니다.
