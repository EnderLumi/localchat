from unittest import TestCase

from localchat.client.parsing.join_target import parse_join_target


class TestJoinTarget(TestCase):
    def test_parse_host_port_ip(self):
        target = parse_join_target("192.168.1.42:51121")
        self.assertEqual(target.host, "192.168.1.42")
        self.assertEqual(target.port, 51121)
        self.assertIsNone(target.room)

    def test_parse_host_port_hostname(self):
        target = parse_join_target("localchat-server.local:51121")
        self.assertEqual(target.host, "localchat-server.local")
        self.assertEqual(target.port, 51121)
        self.assertIsNone(target.room)

    def test_parse_http_join_url(self):
        target = parse_join_target("http://192.168.1.42:8080/join/room1")
        self.assertEqual(target.host, "192.168.1.42")
        self.assertEqual(target.port, 8080)
        self.assertEqual(target.room, "room1")
        self.assertEqual(target.scheme, "http")

    def test_parse_http_without_explicit_port(self):
        target = parse_join_target("http://host.local/join/room1")
        self.assertEqual(target.host, "host.local")
        self.assertEqual(target.port, 80)
        self.assertEqual(target.room, "room1")

    def test_parse_invalid_target(self):
        with self.assertRaises(ValueError):
            parse_join_target("")
        with self.assertRaises(ValueError):
            parse_join_target("invalid-without-port")
