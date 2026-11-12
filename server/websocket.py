"""WebSocket (RFC 6455) from scratch: handshake and frame encode/decode.

Only what a game needs: text frames, ping/pong, close, fragmentation, and
the 7/16/64-bit payload lengths. No extensions, no compression.
"""

import base64
import hashlib
import struct

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OP_CONT, OP_TEXT, OP_BINARY, OP_CLOSE, OP_PING, OP_PONG = 0x0, 0x1, 0x2, 0x8, 0x9, 0xA

MAX_MESSAGE = 1 << 16  # 64 KiB is far more than any client message should be


class ProtocolError(Exception):
    pass


def accept_key(client_key):
    """The Sec-WebSocket-Accept value for a given Sec-WebSocket-Key."""
    digest = hashlib.sha1((client_key + GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def handshake_response(client_key):
    return ("HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Accept: %s\r\n\r\n" % accept_key(client_key)).encode("ascii")


def encode_frame(opcode, payload=b"", mask_key=None):
    """Build one unfragmented frame. Servers send unmasked; tests pass a mask_key."""
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    first = 0x80 | opcode
    n = len(payload)
    mask_bit = 0x80 if mask_key is not None else 0x00
    if n < 126:
        head = struct.pack("!BB", first, mask_bit | n)
    elif n < (1 << 16):
        head = struct.pack("!BBH", first, mask_bit | 126, n)
    else:
        head = struct.pack("!BBQ", first, mask_bit | 127, n)
    if mask_key is not None:
        return head + mask_key + apply_mask(payload, mask_key)
    return head + payload


def apply_mask(data, key):
    """XOR data with the repeating 4-byte key (same operation masks and unmasks)."""
    if not data:
        return b""
    # Build the repeated key as one big int and XOR in bulk; far faster than a Python loop.
    n = len(data)
    rep = (key * (n // 4 + 1))[:n]
    return (int.from_bytes(data, "big") ^ int.from_bytes(rep, "big")).to_bytes(n, "big")


class FrameParser:
    """Feed it bytes as they arrive; it yields complete messages.

    Each message is (opcode, payload_bytes). Fragmented data messages are
    reassembled. Control frames (ping/pong/close) may arrive in the middle of
    a fragmented message and are yielded straight away.
    """

    def __init__(self, require_mask=True):
        self.buf = bytearray()
        self.require_mask = require_mask
        self._frag_op = None
        self._frag_data = bytearray()

    def feed(self, data):
        self.buf.extend(data)
        out = []
        while True:
            frame = self._take_frame()
            if frame is None:
                break
            fin, opcode, payload = frame
            if opcode >= 0x8:                       # control frame
                if not fin or len(payload) > 125:
                    raise ProtocolError("bad control frame")
                out.append((opcode, payload))
            elif opcode == OP_CONT:
                if self._frag_op is None:
                    raise ProtocolError("unexpected continuation")
                self._frag_data.extend(payload)
                if len(self._frag_data) > MAX_MESSAGE:
                    raise ProtocolError("message too large")
                if fin:
                    out.append((self._frag_op, bytes(self._frag_data)))
                    self._frag_op, self._frag_data = None, bytearray()
            else:                                   # text or binary
                if self._frag_op is not None:
                    raise ProtocolError("new message inside a fragmented one")
                if fin:
                    out.append((opcode, payload))
                else:
                    self._frag_op, self._frag_data = opcode, bytearray(payload)
        return out

    def _take_frame(self):
        b = self.buf
        if len(b) < 2:
            return None
        fin = bool(b[0] & 0x80)
        if b[0] & 0x70:
            raise ProtocolError("reserved bits set")
        opcode = b[0] & 0x0F
        masked = bool(b[1] & 0x80)
        length = b[1] & 0x7F
        pos = 2
        if length == 126:
            if len(b) < 4:
                return None
            length = struct.unpack("!H", bytes(b[2:4]))[0]
            pos = 4
        elif length == 127:
            if len(b) < 10:
                return None
            length = struct.unpack("!Q", bytes(b[2:10]))[0]
            pos = 10
        if length > MAX_MESSAGE:
            raise ProtocolError("frame too large")
        if self.require_mask and not masked:
            raise ProtocolError("client frames must be masked")
        key = b""
        if masked:
            if len(b) < pos + 4:
                return None
            key = bytes(b[pos:pos + 4])
            pos += 4
        if len(b) < pos + length:
            return None
        payload = bytes(b[pos:pos + length])
        del b[:pos + length]
        if masked:
            payload = apply_mask(payload, key)
        return fin, opcode, payload


def close_frame(code=1000):
    return encode_frame(OP_CLOSE, struct.pack("!H", code))
