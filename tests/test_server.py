import base64
import json
import os
import socket
import threading
import time
import unittest

from game.kite import Controls
from server import websocket as ws
from server.app import make_server, parse_input


class TestHandshake(unittest.TestCase):
    def test_rfc6455_example(self):
        # The worked example from RFC 6455 section 1.3.
        self.assertEqual(ws.accept_key("dGhlIHNhbXBsZSBub25jZQ=="), "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")

    def test_response_shape(self):
        r = ws.handshake_response("dGhlIHNhbXBsZSBub25jZQ==").decode()
        self.assertTrue(r.startswith("HTTP/1.1 101"))
        self.assertIn("Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=", r)
        self.assertTrue(r.endswith("\r\n\r\n"))


class TestFrames(unittest.TestCase):
    def test_rfc_masked_hello(self):
        # RFC 6455 section 5.7: a single-frame masked text message containing "Hello".
        raw = bytes([0x81, 0x85, 0x37, 0xfa, 0x21, 0x3d, 0x7f, 0x9f, 0x4d, 0x51, 0x58])
        self.assertEqual(ws.FrameParser().feed(raw), [(ws.OP_TEXT, b"Hello")])

    def test_rfc_unmasked_hello(self):
        raw = bytes([0x81, 0x05, 0x48, 0x65, 0x6c, 0x6c, 0x6f])
        self.assertEqual(ws.FrameParser(require_mask=False).feed(raw), [(ws.OP_TEXT, b"Hello")])
        self.assertEqual(ws.encode_frame(ws.OP_TEXT, "Hello"), raw)

    def test_roundtrip_all_length_classes(self):
        for n in (0, 1, 125, 126, 127, 65535, 65536 - 1):
            payload = os.urandom(n)
            frame = ws.encode_frame(ws.OP_BINARY, payload, mask_key=b"\x01\x02\x03\x04")
            self.assertEqual(ws.FrameParser().feed(frame), [(ws.OP_BINARY, payload)], n)

    def test_length_header_sizes(self):
        self.assertEqual(len(ws.encode_frame(ws.OP_TEXT, b"x" * 125)), 2 + 125)
        self.assertEqual(len(ws.encode_frame(ws.OP_TEXT, b"x" * 126)), 4 + 126)
        self.assertEqual(len(ws.encode_frame(ws.OP_TEXT, b"x" * 70000)), 10 + 70000)

    def test_bytes_arriving_one_at_a_time(self):
        frame = ws.encode_frame(ws.OP_TEXT, "hello world", mask_key=b"abcd")
        p, out = ws.FrameParser(), []
        for byte in frame:
            out += p.feed(bytes([byte]))
        self.assertEqual(out, [(ws.OP_TEXT, b"hello world")])

    def test_several_frames_in_one_read(self):
        data = b"".join(ws.encode_frame(ws.OP_TEXT, "m%d" % i, mask_key=b"wxyz") for i in range(3))
        self.assertEqual([m[1] for m in ws.FrameParser().feed(data)], [b"m0", b"m1", b"m2"])

    def test_fragmented_message_with_ping_in_the_middle(self):
        key = b"\x0a\x0b\x0c\x0d"
        f1 = bytearray(ws.encode_frame(ws.OP_TEXT, "Hel", mask_key=key)); f1[0] &= 0x7F   # FIN off
        ping = ws.encode_frame(ws.OP_PING, b"p", mask_key=key)
        f2 = ws.encode_frame(ws.OP_CONT, "lo", mask_key=key)
        out = ws.FrameParser().feed(bytes(f1) + ping + f2)
        self.assertEqual(out, [(ws.OP_PING, b"p"), (ws.OP_TEXT, b"Hello")])

    def test_unmasked_client_frame_rejected(self):
        with self.assertRaises(ws.ProtocolError):
            ws.FrameParser().feed(ws.encode_frame(ws.OP_TEXT, "hi"))

    def test_reserved_bits_rejected(self):
        with self.assertRaises(ws.ProtocolError):
            ws.FrameParser().feed(bytes([0xC1, 0x80, 0, 0, 0, 0]))

    def test_oversized_frame_rejected_before_buffering(self):
        header = bytes([0x81, 0xFF]) + (10 ** 9).to_bytes(8, "big")
        with self.assertRaises(ws.ProtocolError):
            ws.FrameParser().feed(header)

    def test_stray_continuation_rejected(self):
        with self.assertRaises(ws.ProtocolError):
            ws.FrameParser().feed(ws.encode_frame(ws.OP_CONT, "x", mask_key=b"1234"))

    def test_fragmented_control_frame_rejected(self):
        f = bytearray(ws.encode_frame(ws.OP_PING, b"", mask_key=b"1234")); f[0] &= 0x7F
        with self.assertRaises(ws.ProtocolError):
            ws.FrameParser().feed(bytes(f))

    def test_mask_is_its_own_inverse(self):
        data, key = os.urandom(1001), b"\xde\xad\xbe\xef"
        self.assertEqual(ws.apply_mask(ws.apply_mask(data, key), key), data)
        self.assertEqual(ws.apply_mask(b"", key), b"")


class TestParseInput(unittest.TestCase):
    def test_sets_only_booleans(self):
        c = Controls()
        parse_input({"type": "input", "left": True, "right": "yes", "up": 1, "down": False}, c)
        self.assertTrue(c.left)
        self.assertFalse(c.right)       # a string is not accepted
        self.assertFalse(c.up)          # neither is the integer 1
        self.assertFalse(c.down)

    def test_ignores_junk(self):
        c = Controls()
        for junk in (None, 5, "x", [], {"type": "nope"}, {}):
            self.assertIsNone(parse_input(junk, c))
        self.assertFalse(any((c.left, c.right, c.up, c.down)))

    def test_restart(self):
        self.assertEqual(parse_input({"type": "restart"}, Controls()), "restart")


class LiveServerCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = make_server("127.0.0.1", 0)
        cls.port = cls.srv.server_address[1]
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    # -- tiny client ------------------------------------------------------

    def http(self, path, headers=""):
        s = socket.create_connection(("127.0.0.1", self.port), timeout=3)
        s.sendall(("GET %s HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nConnection: close\r\n%s\r\n"
                   % (path, self.port, headers)).encode())
        data = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
        s.close()
        head, _, body = data.partition(b"\r\n\r\n")
        return int(head.split()[1]), head.decode("latin1"), body

    def connect(self, origin=True):
        s = socket.create_connection(("127.0.0.1", self.port), timeout=3)
        key = base64.b64encode(os.urandom(16)).decode()
        extra = "Origin: http://127.0.0.1:%d\r\n" % self.port if origin else ""
        s.sendall(("GET /ws HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                   "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n%s\r\n" % (self.port, key, extra)).encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += s.recv(4096)
        head, _, rest = buf.partition(b"\r\n\r\n")
        return s, key, head.decode(), ws.FrameParser(require_mask=False), rest

    def send(self, s, obj):
        s.sendall(ws.encode_frame(ws.OP_TEXT, json.dumps(obj), mask_key=os.urandom(4)))

    def messages(self, s, parser, first=b"", seconds=0.5, stop=None):
        out, deadline = [], time.time() + seconds
        for op, payload in parser.feed(first):
            out.append((op, payload))
        s.settimeout(0.1)
        while time.time() < deadline:
            try:
                data = s.recv(65536)
            except socket.timeout:
                continue
            if not data:
                break
            out.extend(parser.feed(data))
            if stop and stop(out):
                break
        return out

    @staticmethod
    def states(msgs):
        return [json.loads(p) for op, p in msgs if op == ws.OP_TEXT and json.loads(p).get("type") == "state"]


class TestHttp(LiveServerCase):
    def test_index_served(self):
        status, head, body = self.http("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", head)
        self.assertIn(b"<canvas", body)

    def test_js_served_with_right_type(self):
        status, head, body = self.http("/game.js")
        self.assertEqual(status, 200)
        self.assertIn("javascript", head)

    def test_missing_file_404(self):
        self.assertEqual(self.http("/nope.html")[0], 404)

    def test_path_traversal_blocked(self):
        for p in ("/../app.py", "/..%2fapp.py", "/%2e%2e/app.py", "/static/../../app.py", "//etc/passwd",
                  "/../../../../etc/passwd"):
            status, _, body = self.http(p)
            self.assertEqual(status, 404, p)
            self.assertNotIn(b"import", body)
            self.assertNotIn(b"root:", body)

    def test_ws_without_upgrade_is_400(self):
        self.assertEqual(self.http("/ws")[0], 400)

    def test_directory_is_not_served(self):
        for p in ("/.", "/tests", "/..", "/./"):
            self.assertEqual(self.http(p)[0], 404, p)   # a directory is never listed


class TestWebSocketSession(LiveServerCase):
    def test_handshake_and_init(self):
        s, key, head, parser, rest = self.connect()
        self.assertTrue(head.startswith("HTTP/1.1 101"))
        self.assertIn(ws.accept_key(key), head)           # exactly what a browser verifies
        msgs = self.messages(s, parser, rest, seconds=0.4)
        init = json.loads(msgs[0][1])
        self.assertEqual(init["type"], "init")
        self.assertEqual(init["tick_hz"], 60)
        s.close()

    def test_state_streams_at_about_30hz_and_time_advances(self):
        s, _, _, parser, rest = self.connect()
        msgs = self.messages(s, parser, rest, seconds=1.0)
        st = self.states(msgs)
        self.assertGreater(len(st), 20)
        self.assertLess(len(st), 45)
        self.assertGreater(st[-1]["t"], st[0]["t"] + 0.7)
        s.close()

    def test_input_changes_the_game(self):
        s, _, _, parser, rest = self.connect()
        self.messages(s, parser, rest, seconds=0.2)
        before = self.states(self.messages(s, parser, seconds=0.2))[-1]["kite"]["line"]
        self.send(s, {"type": "input", "right": True})
        after = self.states(self.messages(s, parser, seconds=1.0))[-1]["kite"]["line"]
        self.assertGreater(after, before + 1.0)
        s.close()

    def test_two_clients_have_independent_games(self):
        a = self.connect()
        b = self.connect()
        self.send(a[0], {"type": "input", "right": True})
        ma = self.states(self.messages(a[0], a[3], a[4], seconds=1.0))
        mb = self.states(self.messages(b[0], b[3], b[4], seconds=1.0))
        self.assertGreater(ma[-1]["kite"]["line"], mb[-1]["kite"]["line"] + 1.0)
        a[0].close(); b[0].close()

    def test_ping_gets_pong(self):
        s, _, _, parser, rest = self.connect()
        s.sendall(ws.encode_frame(ws.OP_PING, b"abc", mask_key=b"1234"))
        msgs = self.messages(s, parser, rest, seconds=0.6, stop=lambda m: any(o == ws.OP_PONG for o, _ in m))
        self.assertIn((ws.OP_PONG, b"abc"), msgs)
        s.close()

    def test_close_handshake(self):
        s, _, _, parser, rest = self.connect()
        s.sendall(ws.encode_frame(ws.OP_CLOSE, b"\x03\xe8", mask_key=b"1234"))
        msgs = self.messages(s, parser, rest, seconds=0.8, stop=lambda m: any(o == ws.OP_CLOSE for o, _ in m))
        self.assertTrue(any(o == ws.OP_CLOSE for o, _ in msgs))
        s.close()

    def test_garbage_does_not_crash_the_server(self):
        s, _, _, parser, rest = self.connect()
        for junk in (b"not json", b"{", b"\xff\xfe", b"[]", b"null", b'{"type":"input","left":"x"}', b"{" * 5000):
            s.sendall(ws.encode_frame(ws.OP_TEXT, junk, mask_key=b"1234"))
        msgs = self.messages(s, parser, rest, seconds=0.5)
        self.assertTrue(self.states(msgs))          # still streaming
        s.close()
        self.assertEqual(self.http("/")[0], 200)    # and the server still answers

    def test_protocol_violation_closes_with_1002(self):
        s, _, _, parser, rest = self.connect()
        s.sendall(ws.encode_frame(ws.OP_TEXT, "unmasked"))            # clients must mask
        msgs = self.messages(s, parser, rest, seconds=0.8, stop=lambda m: any(o == ws.OP_CLOSE for o, _ in m))
        closes = [p for o, p in msgs if o == ws.OP_CLOSE]
        self.assertTrue(closes)
        self.assertEqual(int.from_bytes(closes[0][:2], "big"), 1002)
        s.close()

    def test_cross_origin_refused(self):
        s = socket.create_connection(("127.0.0.1", self.port), timeout=3)
        s.sendall(("GET /ws HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                   "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n"
                   "Origin: http://evil.example\r\n\r\n" % self.port).encode())
        self.assertIn(b" 403 ", s.recv(4096).split(b"\r\n")[0] + b" ")
        s.close()

    def test_restart_only_works_after_game_over(self):
        s, _, _, parser, rest = self.connect()
        self.messages(s, parser, rest, seconds=0.3)
        self.send(s, {"type": "restart"})                 # mid-game: must be ignored
        st = self.states(self.messages(s, parser, seconds=0.4))
        self.assertTrue(all(x["lives"] == 3 and x["level"] == 1 for x in st))
        self.assertGreater(st[-1]["t"], 0.5)              # the clock was not reset
        s.close()

    def test_server_survives_abrupt_disconnects(self):
        for _ in range(10):
            s, _, _, _, _ = self.connect()
            s.close()
        time.sleep(0.2)
        s, _, _, parser, rest = self.connect()
        self.assertTrue(self.states(self.messages(s, parser, rest, seconds=0.5)))
        s.close()


if __name__ == "__main__":
    unittest.main()
