from unittest import TestCase
from uuid import uuid4

from localchat.net.discovery import (
    DiscoveryRequest,
    DiscoveryResponse,
    DiscoveredServer,
    decode_discovery_request,
    decode_discovery_response,
    encode_discovery_request,
    encode_discovery_response,
)


class TestDiscoveryProtocol(TestCase):
    def test_request_roundtrip(self):
        req = DiscoveryRequest(nonce=uuid4(), reply_port=51122)
        payload = encode_discovery_request(req)
        decoded = decode_discovery_request(payload)
        self.assertEqual(decoded, req)

    def test_response_roundtrip(self):
        res = DiscoveryResponse(
            nonce=uuid4(),
            server=DiscoveredServer(
                server_id=uuid4(),
                server_name="my-server",
                host="127.0.0.1",
                port=51121,
                requires_password=True,
            ),
        )
        payload = encode_discovery_response(res)
        decoded = decode_discovery_response(payload)
        self.assertEqual(decoded, res)

    def test_request_validation(self):
        with self.assertRaises(IOError):
            decode_discovery_request(b"{}")
        with self.assertRaises(IOError):
            decode_discovery_request(
                b'{"v":1,"kind":"discover_request","nonce":"x","reply_port":51122}'
            )

    def test_response_validation(self):
        with self.assertRaises(IOError):
            decode_discovery_response(b"{}")
        with self.assertRaises(IOError):
            decode_discovery_response(
                b'{"v":1,"kind":"discover_response","nonce":"x","server_id":"x","server_name":"","host":"","port":0}'
            )
