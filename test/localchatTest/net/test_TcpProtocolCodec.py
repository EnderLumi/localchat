from io import BytesIO
from unittest import TestCase
from uuid import uuid4

from localchat.config.limits import MAX_MESSAGE_LENGTH
from localchat.net import SerializableUserMessage, tcp_protocol
from localchat.net.SerializableUser import SerializableUser


class TestTcpProtocolCodec(TestCase):
    def test_encode_decode_join(self):
        user = SerializableUser(uuid4(), "Alice")
        payload = tcp_protocol.encode_join(user)
        packet_type, body = tcp_protocol.decode_client_packet(payload)
        self.assertEqual(packet_type, tcp_protocol.PT_C_JOIN)
        decoded = tcp_protocol.decode_join(body)
        self.assertEqual(decoded.get_id(), user.get_id())
        self.assertEqual(decoded.get_name(), "Alice")

    def test_encode_decode_public_message(self):
        payload = tcp_protocol.encode_public_message("hello")
        packet_type, body = tcp_protocol.decode_client_packet(payload)
        self.assertEqual(packet_type, tcp_protocol.PT_C_PUBLIC)
        self.assertEqual(tcp_protocol.decode_public_message(body), "hello")

    def test_encode_decode_private_message(self):
        recipient_id = uuid4()
        payload = tcp_protocol.encode_private_message(recipient_id, "secret")
        packet_type, body = tcp_protocol.decode_client_packet(payload)
        self.assertEqual(packet_type, tcp_protocol.PT_C_PRIVATE)
        decoded_recipient, decoded_message = tcp_protocol.decode_private_message(body)
        self.assertEqual(decoded_recipient.value, recipient_id)
        self.assertEqual(decoded_message, "secret")

    def test_decode_client_packet_rejects_empty_payload(self):
        with self.assertRaises(IOError):
            tcp_protocol.decode_client_packet(b"")

    def test_public_message_limit_enforced(self):
        too_long = "x" * (MAX_MESSAGE_LENGTH + 1)
        payload = tcp_protocol.encode_public_message(too_long)
        _, body = tcp_protocol.decode_client_packet(payload)
        with self.assertRaises(IOError):
            tcp_protocol.decode_public_message(body)

    def test_server_message_payloads_roundtrip(self):
        sender = SerializableUser(uuid4(), "Bob")
        msg = SerializableUserMessage(sender, "hi", 1.23)

        pub_payload = tcp_protocol.encode_server_public_message(msg)
        self.assertEqual(pub_payload[0], tcp_protocol.PT_S_PUBLIC)
        decoded_pub = SerializableUserMessage.deserialize(BytesIO(pub_payload[1:]))
        self.assertEqual(decoded_pub.message(), "hi")
        self.assertEqual(decoded_pub.sender().get_id(), sender.get_id())

        priv_payload = tcp_protocol.encode_server_private_message(msg)
        self.assertEqual(priv_payload[0], tcp_protocol.PT_S_PRIVATE)
        decoded_priv = SerializableUserMessage.deserialize(BytesIO(priv_payload[1:]))
        self.assertEqual(decoded_priv.message(), "hi")
        self.assertEqual(decoded_priv.sender().get_id(), sender.get_id())

    def test_join_ack_payload(self):
        payload = tcp_protocol.encode_server_join_ack()
        self.assertEqual(payload[0], tcp_protocol.PT_S_JOIN_ACK)
        self.assertEqual(len(payload), 1)

    def test_join_nack_payload_roundtrip(self):
        payload = tcp_protocol.encode_server_join_nack(
            tcp_protocol.ERR_JOIN_REJECTED,
            "server is locked",
        )
        self.assertEqual(payload[0], tcp_protocol.PT_S_JOIN_NACK)
        code, message = tcp_protocol.decode_server_join_nack(BytesIO(payload[1:]))
        self.assertEqual(code, tcp_protocol.ERR_JOIN_REJECTED)
        self.assertEqual(message, "server is locked")

    def test_server_error_payload_structured_roundtrip(self):
        payload = tcp_protocol.encode_server_error(
            tcp_protocol.ERR_UNKNOWN_RECIPIENT,
            "unknown recipient",
        )
        self.assertEqual(payload[0], tcp_protocol.PT_S_ERROR)
        code, message = tcp_protocol.decode_server_error(BytesIO(payload[1:]))
        self.assertEqual(code, tcp_protocol.ERR_UNKNOWN_RECIPIENT)
        self.assertEqual(message, "unknown recipient")

    def test_server_error_payload_legacy_decode(self):
        payload = tcp_protocol.encode_server_error("legacy message")
        code, message = tcp_protocol.decode_server_error(BytesIO(payload[1:]))
        self.assertEqual(code, tcp_protocol.ERR_GENERIC)
        self.assertEqual(message, "legacy message")

    def test_build_payload_type_bounds(self):
        with self.assertRaises(ValueError):
            tcp_protocol._build_payload(-1, b"a")
        with self.assertRaises(ValueError):
            tcp_protocol._build_payload(256, b"a")
