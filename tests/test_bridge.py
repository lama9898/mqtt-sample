import unittest
from types import SimpleNamespace
from fastapi import HTTPException
from src.main import Message, MessageBridge, TOPIC


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = MessageBridge()

    def receive(self, payload, topic=TOPIC):
        self.bridge.on_message(None, None, SimpleNamespace(topic=topic, payload=payload))

    def test_recipient_isolation(self):
        self.receive(b'{"sender":"alice","recipient":"bob","content":"hello"}')
        self.assertEqual(self.bridge.read('bob')[0]['content'], 'hello')
        self.assertEqual(self.bridge.read('alice'), [])

    def test_invalid_payload_does_not_interrupt_next_message(self):
        for payload in [b'broken', b'{}', b'\xff', b'x' * 17000]:
            self.receive(payload)
        self.receive(b'{"sender":"alice","recipient":"bob","content":"valid"}')
        self.assertEqual(len(self.bridge.read('bob')), 1)

    def test_wrong_topic_is_ignored(self):
        self.receive(b'{"sender":"a","recipient":"b","content":"x"}', 'other')
        self.assertEqual(self.bridge.read('b'), [])

    def test_broker_unavailable(self):
        with self.assertRaises(HTTPException) as ctx:
            self.bridge.publish(Message(sender='a', recipient='b', content='x'))
        self.assertEqual(ctx.exception.status_code, 503)

    def test_bounded_storage(self):
        for _ in range(1005):
            self.receive(b'{"sender":"a","recipient":"b","content":"x"}')
        self.assertEqual(len(self.bridge.read('b')), 1000)


if __name__ == '__main__':
    unittest.main()
