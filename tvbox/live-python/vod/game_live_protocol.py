import struct
import uuid
from threading import Event, RLock, Thread
from xml.etree import ElementTree

DOUYU_COLORS = (0xffffff, 0xff2e2e, 0x00ccff, 0x66ff00, 0xff6600, 0xcc00ff, 0xf6447f)


def subscribe(net, room, emit):
    subscription = _Subscription(net, room, emit)
    subscription.start()
    return subscription.stop


class _Subscription:

    def __init__(self, net, room, emit):
        self.net, self.room, self.emit = net, room, emit
        self.platform = room["platform"]
        self.lock = RLock()
        self.socket = self.heartbeat = self.decode = None
        self.yy = None
        self.instance = str(uuid.uuid4()) if self.platform == "yy" else None
        self.stopped = self.ready = False

    def start(self):
        url = "wss://danmuproxy.douyu.com:8506/" if self.platform == "douyu" else "wss://cdnws.api.huya.com/"
        options = {"timeout": 10000, "idle": 90000, "reconnect": True}
        if self.platform == "yy":
            url = "wss://h5-sinchl.yy.com/websocket?appid=yymwebh5&version=3.2.14&uuid=" + self.instance
            options["headers"] = {"Origin": "https://www.yy.com"}
        socket = self.net.connect(url, options, self.receive)
        with self.lock:
            self.socket = socket
            if self.stopped:
                socket.cancel()

    def stop(self):
        with self.lock:
            if self.stopped:
                return
            self.stopped = True
            self._clear_heartbeat()
            self._clear_decoder()
            if self.socket is not None:
                self.socket.cancel()

    def _clear_heartbeat(self):
        if self.heartbeat is not None:
            self.heartbeat.set()
            self.heartbeat = None

    def _clear_decoder(self):
        if self.yy is not None:
            self.yy.clear()
            self.yy = None
        self.decode = None

    def _send(self, socket, data):
        if socket.send(data):
            return True
        self._clear_heartbeat()
        return False

    def _pulse(self, socket):
        if self.platform == "yy":
            return self.yy.pulse() if self.yy is not None else False
        packet = douyu_packet("type@=mrkl/") if self.platform == "douyu" else b"\x00\x14\x1d\x00\x0c"
        return self._send(socket, packet)

    def _beat(self, socket, heartbeat):
        while not heartbeat.wait(5 if self.platform == "yy" else 30):
            with self.lock:
                if self.stopped or heartbeat is not self.heartbeat:
                    return
                try:
                    if not self._pulse(socket):
                        return
                except Exception as error:
                    self._fail(error)
                    return

    def _open(self, socket):
        self._clear_heartbeat()
        self._clear_decoder()
        self.ready = False
        if self.platform == "douyu":
            self.decode = douyu_decoder(self._mark_ready)
            if not self._send(socket, douyu_packet(f"type@=loginreq/roomid@={self.room['id']}/")):
                return
            if not self._send(socket, douyu_packet(f"type@=joingroup/rid@={self.room['id']}/gid@=-9999/")):
                return
        elif self.platform == "yy":
            self.yy = YYSession(self.room, lambda data: self._send(socket, data), self._mark_ready, self.instance)
            self.decode = self.yy.decode
            if not self.yy.start():
                return
        else:
            self.decode = lambda data: huya_messages(data, self._mark_ready)
            if not self._send(socket, huya_login(self.room)):
                return
        if self._pulse(socket):
            self.heartbeat = Event()
            Thread(target=self._beat, args=(socket, self.heartbeat), daemon=True).start()

    def _mark_ready(self):
        if not self.ready:
            self.ready = True
            self.emit({"state": "ready"})

    def _fail(self, error):
        if not self.stopped:
            self.stop()
            self.emit({"state": "error", "msg": str(error or "彈幕連線已關閉")[:512]})

    def receive(self, socket, event):
        with self.lock:
            if self.stopped:
                return
            try:
                if event["type"] == "open":
                    self._open(socket)
                elif event["type"] == "message" and event["binary"]:
                    for item in self.decode(event["content"]):
                        if self.stopped:
                            return
                        self.emit(item)
                elif event["type"] == "retry":
                    self._clear_heartbeat()
                    self._clear_decoder()
                    self.ready = False
                    self.emit({"state": "retrying", "msg": "彈幕連線中斷，等待恢復"})
                elif event["type"] in ("error", "close"):
                    self._fail(event.get("error") or "彈幕連線已關閉")
            except Exception as error:
                self._fail(error)
                raise


def yy_packet(uri, body):
    return struct.pack("<IIH", len(body) + 10, uri, 200) + body


def _yy_u32(value):
    return struct.pack("<I", value & 0xffffffff)


def _yy_u64(value):
    return struct.pack("<Q", value)


def _yy_bytes(value, wide=False):
    if isinstance(value, str):
        value = value.encode()
    return struct.pack("<I" if wide else "<H", len(value)) + value


class _YYReader:

    def __init__(self, data):
        self.data, self.offset = data, 0

    def read(self, size):
        if not 0 <= size <= len(self.data) - self.offset:
            raise ValueError("YY彈幕封包不完整")
        value = self.data[self.offset:self.offset + size]
        self.offset += size
        return value

    def number(self, size):
        return int.from_bytes(self.read(size), "little")

    def blob(self, wide=False):
        return self.read(self.number(4 if wide else 2))


class YYSession:

    def __init__(self, room, send, on_ready=None, instance=None):
        self.top, self.sub = int(room["top"]), int(room["sub"])
        if not 0 < self.top <= 0xffffffff or not 0 < self.sub <= 0xffffffff:
            raise ValueError("YY直播頻道無效")
        self.send, self.on_ready = send, on_ready
        self.instance = instance or str(uuid.uuid4())
        self.clear()

    def clear(self):
        self.pending, self.uid, self.state = b"", 0, "closed"

    def _send(self, uri, body):
        if self.state == "closed":
            return False
        if self.send(yy_packet(uri, body)):
            return True
        self.clear()
        return False

    def start(self):
        self.clear()
        self.state = "guest"
        payload = b"".join((_yy_bytes(""), _yy_u32(0), _yy_bytes("B8-97-5A-17-AD-4D"),
                            _yy_bytes("B8-97-5A-17-AD-4D"), _yy_u32(0), _yy_bytes("yymwebh5")))
        return self._send(778244, _yy_bytes("") + _yy_u32(19822) + _yy_bytes(payload, True))

    def pulse(self):
        return self._send(794116, _yy_u32(0)) if self.state in ("join", "subscribed") else self.state != "closed"

    def decode(self, chunk):
        if self.state == "closed":
            return []
        if not isinstance(chunk, bytes) or len(self.pending) + len(chunk) > 1048576:
            raise ValueError("YY彈幕封包過大或格式錯誤")
        data, offset, messages = self.pending + chunk, 0, []
        while offset + 10 <= len(data):
            size, uri, code = struct.unpack_from("<IIH", data, offset)
            if not 10 <= size <= 1048576:
                raise ValueError("YY彈幕封包長度錯誤")
            if offset + size > len(data):
                break
            item = self._dispatch(uri, _YYReader(data[offset + 10:offset + size]), code)
            if item is not None:
                messages.append(item)
            if self.state == "closed":
                return messages
            offset += size
        self.pending = data[offset:] if self.state != "closed" else b""
        return messages

    def _dispatch(self, uri, body, code):
        if uri == 795140:
            raise ValueError("YY彈幕連線被關閉")
        if uri == 778500 and self.state == "guest":
            self._guest(body, code)
        elif uri == 775940 and self.state == "ap":
            self._login(body, code)
        elif uri == 512011 and self.state == "join":
            self._joined(body, code)
        elif uri in (533080, 28760) and self.state == "subscribed":
            if code != 200:
                raise ValueError("YY彈幕聊天封包狀態錯誤")
            return self._message(body, uri)

    def _guest(self, body, code):
        body.blob()
        result, uri, payload = body.number(4), body.number(4), _YYReader(body.blob(True))
        payload.blob()
        status, legacy_uid = payload.number(4), payload.number(4)
        payload.number(4)
        account, password, cookie = payload.blob(), payload.blob(), payload.blob()
        payload.blob()
        payload.blob()
        payload.blob()
        self.uid = (payload.number(8) if payload.offset < len(payload.data) else 0) or legacy_uid
        if (code != 200 or result != 200 or uri != 20078 or status not in (0, 200)
                or not self.uid or not account or not password or not cookie):
            raise ValueError("YY彈幕遊客認證失敗")
        auth = b"".join((_yy_bytes(account), _yy_bytes(password), _yy_u32(2), _yy_u32(0) * 2,
                         _yy_bytes("yytianlaitv"), _yy_bytes("B8-97-5A-17-AD-4D"),
                         _yy_bytes("yymwebn_yymwebh5"), _yy_u32(0) * 4, _yy_bytes(self.instance)))
        request = b"".join((_yy_bytes(auth, True), _yy_u32(259), _yy_u64(self.uid), b"\0",
                            _yy_bytes(b""), _yy_bytes(cookie), _yy_bytes("259:0"), _yy_bytes("") * 3,
                            b"\0", _yy_u32(0) * 2, _yy_u32(-1), _yy_bytes(""), _yy_u32(1),
                            _yy_bytes("BCIFVer"), _yy_bytes("V2")))
        self.state = "ap"
        self._send(775684, request)

    def _login(self, body, code):
        body.number(4)
        result, context = body.number(4), body.blob()
        if code != 200 or result != 200 or context != b"259:0":
            raise ValueError("YY彈幕服務登入失敗")
        self.state = "join"
        if not self._send(538456, _yy_u64(self.uid) + _yy_u32(1) + _yy_u32(31)):
            return
        payload = b"".join((_yy_u32(self.uid), _yy_u32(self.top), _yy_u32(self.sub), _yy_u32(0), _yy_u64(self.uid)))
        self._send(513035, self._router(2048258, "channelAuther", payload))

    def _router(self, uri, service, payload):
        trace = "F" + str(self.uid) + "_yymwebh5_" + self.instance.replace("-", "")[:5] + "_1"
        props = _yy_u32(2) + _yy_u32(1) + _yy_bytes(_yy_u32(self.top)) + _yy_u32(103) + _yy_bytes(trace)
        route = b"".join((_yy_u32(0), struct.pack("<H", 0), _yy_u32(0), _yy_bytes(service), _yy_u32(0), _yy_bytes("")))
        headers = b"".join((_yy_u32(0x01000008), _yy_u32(uri), _yy_u32(0x02000010), _yy_u32(259),
                            _yy_u64(self.uid), _yy_u32(0x0400000c), _yy_u32(0) * 2,
                            _yy_u32(0x05000008), _yy_u32(0), _yy_u32(0x06000000 | (len(route) + 4)),
                            route, _yy_u32(0x07000000 | (len(props) + 4)), props,
                            _yy_u32(0x08000006), _yy_bytes(""), _yy_u32(0xff787878)))
        return _yy_bytes("") + _yy_u32(uri) + struct.pack("<H", 0) + _yy_bytes(payload, True) + _yy_bytes(headers, True)

    def _joined(self, body, code):
        body.blob()
        uri, result, payload = body.number(4), body.number(2), _YYReader(body.blob(True))
        if uri != 2048514:
            return
        top = payload.number(4)
        payload.number(4)
        sub = payload.number(4)
        payload.number(4)
        payload.number(4)
        status, message = payload.number(1), payload.blob().decode(errors="replace")
        if code != 200 or result != 200 or status != 4 or top != self.top or sub != self.sub:
            raise ValueError("YY彈幕頻道訂閱失敗" + ("：" + message[:256] if message else ""))
        groups = ((1, 0, top, 0), (2, 0, sub, 0), (1024, 259, sub, top),
                  (768, 259, 0, top), (256, 259, 0, top), (256, 259, sub, top))
        for values in (groups, groups[:2]):
            packet = _yy_u64(self.uid) + _yy_u32(len(values)) + b"".join(struct.pack("<IIII", *group) for group in values)
            if not self._send(537944, packet + _yy_bytes("")):
                return
        self.state = "subscribed"
        if self.on_ready:
            self.on_ready()

    def _message(self, body, uri):
        if uri == 533080:
            body.number(8)
            body.number(8)
            appid, data = body.number(4), body.blob(True)
        else:
            appid = body.number(2)
            body.number(4)
            data = body.blob()
        if appid != 31:
            return None
        chat = _YYReader(data)
        size, inner, code = chat.number(4), chat.number(4), chat.number(2)
        if size != len(data):
            raise ValueError("YY彈幕聊天封包長度錯誤")
        if inner != 3104600:
            return None
        if code != 200:
            raise ValueError("YY彈幕聊天封包狀態錯誤")
        chat.number(4)
        top, sub = chat.number(4), chat.number(4)
        if top != self.top or sub != self.sub:
            return None
        content = _YYReader(chat.blob())
        content.number(4)
        content.blob(True)
        color = content.number(4)
        content.number(4)
        text = _yy_text(content.blob(True).decode("utf-16le"))
        content.number(4)
        return {"text": text, "color": color if 0 < color <= 0xffffff else 0xffffff} if text.strip() else None


def _yy_text(text):
    if not text.lstrip().startswith("<"):
        return text
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError("YY彈幕文字格式錯誤")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        raise ValueError("YY彈幕文字格式錯誤") from error
    pending = [(root, 1)]
    while pending:
        item, depth = pending.pop()
        if depth > 20:
            raise ValueError("YY彈幕文字層數過多")
        pending.extend((child, depth + 1) for child in item)
    return "".join(item.get("data", "") for item in root.iter("txt"))


def douyu_packet(text):
    body = (text + "\0").encode()
    return struct.pack("<III", len(body) + 8, len(body) + 8, 689) + body


def douyu_decoder(on_ready=None):
    pending = b""

    def decode(chunk):
        nonlocal pending
        if len(pending) + len(chunk) > 1048576:
            raise ValueError("斗魚彈幕封包過大")
        data = pending + chunk if pending else chunk
        messages, offset = [], 0
        while offset + 12 <= len(data):
            length, repeated = struct.unpack_from("<II", data, offset)
            if not 9 <= length <= 1048572 or length != repeated:
                raise ValueError("斗魚彈幕封包格式錯誤")
            end = offset + length + 4
            if end > len(data):
                break
            if data[end - 1] != 0:
                raise ValueError("斗魚彈幕封包缺少結尾")
            fields = {}
            for item in data[offset + 12:end - 1].decode(errors="replace").split("/"):
                key, separator, value = item.partition("@=")
                if separator:
                    fields[key] = value.replace("@S", "/").replace("@A", "@")
            if fields.get("type") in ("mrkl", "chatmsg") and on_ready:
                on_ready()
            if fields.get("type") == "chatmsg" and fields.get("txt", "").strip():
                messages.append({"text": fields["txt"], "color": _douyu_color(fields.get("col", ""))})
            offset = end
        pending = data[offset:]
        return messages

    return decode


def _douyu_color(value):
    color = value.lstrip("0")
    return DOUYU_COLORS[int(color)] if len(color) == 1 and color in "123456" else 0xffffff


def _integer(tag, value):
    value = int(value)
    if value == 0:
        return bytes((tag << 4 | 12, ))
    size = 1 if -128 <= value <= 127 else 2 if -32768 <= value <= 32767 else 4 if -2147483648 <= value <= 2147483647 else 8
    kind = {1: 0, 2: 1, 4: 2, 8: 3}[size]
    return bytes((tag << 4 | kind, )) + value.to_bytes(size, "big", signed=True)


def huya_login(room):
    body = b"".join((_integer(0, room["uid"]), _integer(1, 1), b"\x26\0\x36\0", _integer(4, room["top"]),
                     _integer(5, room["sub"]), _integer(6, 0), _integer(7, 0)))
    return _integer(0, 1) + b"\x1d\0" + _integer(0, len(body)) + body


def huya_messages(data, on_ready=None):
    envelope = _tars(data)
    if envelope.get(0) == 2:
        if _tars(envelope[1]).get(0) != 0:
            raise ValueError("虎牙彈幕訂閱失敗")
        if on_ready:
            on_ready()
        return []
    if envelope.get(0) != 7:
        return []
    push = _tars(envelope[1])
    if push.get(1) != 1400:
        return []
    message = _tars(push[2])
    if not isinstance(message.get(3), str) or not message[3].strip():
        return []
    if on_ready:
        on_ready()
    format = message.get(6) or {}
    colors = [color for color in format.get(6, []) if _is_rgb(color)][:8] if isinstance(format.get(6), list) else []
    item = {"text": message[3], "color": colors[0] if colors else format[0] if _is_rgb(format.get(0)) else 0xffffff}
    if len(colors) > 1:
        item["colors"] = colors
    return [item]


def _is_rgb(value):
    return type(value) is int and 0 <= value <= 0xffffff


def _tars(data):
    if not isinstance(data, bytes) or len(data) > 1048576:
        raise ValueError("虎牙彈幕封包格式錯誤")
    offset = 0

    def read(size):
        nonlocal offset
        if type(size) is not int or not 0 <= size <= len(data) - offset:
            raise ValueError("虎牙彈幕封包不完整")
        value = data[offset:offset + size]
        offset += size
        return value

    def field(depth):
        if depth > 20:
            raise ValueError("虎牙彈幕巢狀層數過多")
        head = read(1)[0]
        kind = head & 15
        tag = read(1)[0] if head >> 4 == 15 else head >> 4
        if kind <= 3:
            value = int.from_bytes(read(1 << kind), "big", signed=True)
        elif kind in (4, 5):
            value = struct.unpack(">f" if kind == 4 else ">d", read(4 if kind == 4 else 8))[0]
        elif kind in (6, 7):
            size = read(1)[0] if kind == 6 else int.from_bytes(read(4), "big")
            value = read(size).decode(errors="replace")
        elif kind in (8, 9):
            count = field(depth + 1)[2]
            if type(count) is not int or not 0 <= count <= 4096:
                raise ValueError("虎牙彈幕集合長度錯誤")
            value = [[field(depth + 1)[2], field(depth + 1)[2]] if kind == 8 else field(depth + 1)[2]
                     for _ in range(count)]
        elif kind == 10:
            value = record(depth + 1)
        elif kind in (11, 12):
            value = 0
        elif kind == 13:
            if read(1)[0] != 0:
                raise ValueError("虎牙彈幕 byte 類型錯誤")
            value = read(field(depth + 1)[2])
        else:
            raise ValueError("虎牙彈幕包含未知類型")
        return tag, kind, value

    def record(depth):
        result = {}
        while offset < len(data):
            tag, kind, value = field(depth)
            if kind == 11:
                break
            result[tag] = value
        return result

    return record(0)
