import hashlib
import json
import os
import random
import string
import struct
import tempfile
import threading
import time
from collections import OrderedDict
from urllib.parse import quote, unquote, urlparse

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from base.spider import Spider as BaseSpider


HOST = "https://www.yangshipin.cn"
NAVIGATION_URL = "https://capi.yangshipin.cn/api/oms/pc/navigation/home_top_nav"
PAGE_URL = "https://capi.yangshipin.cn/api/oms/pc/page/{}"
PLAYER_URL = "https://player-api.yangshipin.cn/v1/player/"
OPEN_TOKEN_URL = "https://h5access.yangshipin.cn/web/open/token"
KEYGEN_URL = "https://s.yangshipin.cn/CCTVVideo/cctvh5-openapicore/keygen_bg.wasm"
HLS_MIME = "application/x-mpegURL"
CATALOG_TIMEOUT = 8
PLAYER_TIMEOUT = 15
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)
GROUP_NAMES = {"yangshi": "央視頻道", "weishi": "衛視頻道"}
MIN_CHANNELS = 50
YSP_APP_ID = "519748109"
APP_VERSION = "V1.0.0"
PLATFORM = "5910204"
AUTH_SALT = "n@7QKk%YeSjfw%22"
REQUEST_SALT = "0f$IVHi9Qno?G"
OPEN_VAPP_ID = "59306155"
OPEN_VSECRET = "b42702bf7309a179d102f3d51b1add2fda0bc7ada64cb801"
TICKET_KEYSTREAM = bytes.fromhex(
    "6a70e9ac007ccc384c28a88dfd2211decb66494bca83bd6178f85732b2eacc959"
    "4e4e5ab720ec3a43e87b3c72b86192ff0dfea8fa8f47794d8792668438c"
)
TICKET_SUFFIX = "bSCz8SqH8T"
PLAY_CACHE_SECONDS = 60
_KEYGEN_LOCK = threading.Lock()


def _md5(value):
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def _canonical_query(params):
    return "&".join("{}={}".format(key, params[key]) for key in sorted(params))


def _signature(params, salt):
    return _md5(_canonical_query(params) + salt)


def _random_text(length=10):
    alphabet = "ABCDEFGHIJKlMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.choice(alphabet) for _ in range(length))


def _ticket(pid, timestamp, guid):
    payload = "{}&{}&{}&{}&{}".format(
        pid,
        timestamp,
        guid,
        YSP_APP_ID,
        TICKET_SUFFIX,
    ).encode("utf-8")
    if len(payload) > len(TICKET_KEYSTREAM):
        raise ValueError("invalid ticket payload")
    return bytes(
        value ^ TICKET_KEYSTREAM[index] for index, value in enumerate(payload)
    ).hex()


def _download_keygen():
    path = os.path.join(tempfile.gettempdir(), "ysp-keygen-v1.wasm")
    minimum_size = 20000
    maximum_size = 100000

    def valid():
        try:
            size = os.path.getsize(path)
            if size < minimum_size or size > maximum_size:
                return False
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x00asm"
        except OSError:
            return False

    with _KEYGEN_LOCK:
        if valid():
            return path
        with requests.get(
            KEYGEN_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=PLAYER_TIMEOUT,
        ) as response:
            response.raise_for_status()
            payload = response.content
        if not (minimum_size <= len(payload) <= maximum_size) or payload[:4] != b"\x00asm":
            raise ValueError("invalid official wasm")
        temporary = path + ".download"
        with open(temporary, "wb") as stream:
            stream.write(payload)
        os.replace(temporary, path)
        return path


def _load_pywasm():
    import pywasm
    from pywasm import execution

    if not getattr(execution.hostfunc_call, "_ysp_fixed", False):
        def hostfunc_call(module, address, store, stack):
            function = store.funcs[address]
            values = [stack.pop() for _ in function.functype.args][::-1]
            context = execution.Ctx(store.mems)
            result = function.hostcode(context, *[value.n for value in values])
            if not function.functype.rets:
                return []
            return [execution.Value(function.functype.rets[0], result)]

        hostfunc_call._ysp_fixed = True
        execution.hostfunc_call = hostfunc_call
    return pywasm


class _Keygen:

    def __init__(self, path):
        pywasm = _load_pywasm()
        self.state = {}
        self.heap = {}
        self.next_handle = 132
        imports = {
            "wbg": {
                "__wbg_get_9c1840f7ecd81363": self._get,
                "__wbindgen_string_get": self._string_get,
                "__wbindgen_object_drop_ref": self._drop,
            }
        }
        self.runtime = pywasm.load(path, imports)
        self.memory = None
        for exported in self.runtime.module_instance.exports:
            if exported.name == "memory":
                self.memory = self.runtime.store.mems[exported.value.addr]
                break
        if self.memory is None:
            raise ValueError("missing keygen memory")

    def token_random(self, state):
        self.state = state
        return self._call("get_token_rnd")

    def signature(self, state):
        self.state = state
        return self._call("get_signature")

    def _get(self, context, pointer, length):
        path = self._text(pointer, length)
        prefix = "cctvh5openapi.state."
        if path.startswith(prefix):
            value = self.state.get(path[len(prefix):], "")
        elif path == "window.location.host":
            value = "www.yangshipin.cn"
        elif path == "window.location.protocol":
            value = "https:"
        else:
            value = ""
        handle = self.next_handle
        self.next_handle += 1
        self.heap[handle] = str(value)
        return handle

    def _string_get(self, context, output, handle):
        payload = self.heap.get(handle, "").encode("utf-8")
        pointer = self._exec("__wbindgen_malloc", len(payload), 1)
        self.memory.data[pointer:pointer + len(payload)] = payload
        struct.pack_into("<ii", self.memory.data, output, pointer, len(payload))

    def _drop(self, context, handle):
        self.heap.pop(handle, None)

    def _call(self, name):
        output = self._exec("__wbindgen_add_to_stack_pointer", -16)
        pointer = 0
        length = 0
        try:
            self._exec(name, output)
            pointer, length = struct.unpack_from("<ii", self.memory.data, output)
            return self._text(pointer, length)
        finally:
            if pointer:
                self._exec("__wbindgen_free", pointer, length, 1)
            self._exec("__wbindgen_add_to_stack_pointer", 16)

    def _text(self, pointer, length):
        return bytes(self.memory.data[pointer:pointer + length]).decode("utf-8")

    def _exec(self, name, *args):
        return self.runtime.exec(name, list(args))


class _PlayerApi:

    def __init__(self):
        keygen_path = _download_keygen()
        self.keygen = _Keygen(keygen_path)

    def resolve(self, pid, cnlid):
        guid = "{}_{}".format(self._base36(int(time.time() * 1000)), _random_text(11))
        with self._session(guid) as session:
            auth = self._auth(session, pid, guid)
            timestamp = str(int(time.time() + 0.5))
            params = {
                "cnlid": cnlid,
                "livepid": pid,
                "stream": "2",
                "guid": guid,
                "cKey": self._ckey(cnlid, timestamp, guid),
                "adjust": 1,
                "sphttps": "1",
                "platform": PLATFORM,
                "cmd": "2",
                "encryptVer": "8.1",
                "dtype": "1",
                "devid": "devid",
                "otype": "ojson",
                "appVer": APP_VERSION,
                "app_version": APP_VERSION,
                "channel": "ysp_tx",
                "defn": "fhd",
            }
            headers = self._sdk_headers(session, guid, params)
            headers["yspPlayerToken"] = str(auth["token"])
            headers["yspticket"] = _ticket(pid, str(auth["ts"]), guid)
            params["rand_str"] = _random_text()
            params["signature"] = _signature(params, REQUEST_SALT)
            response = session.post(
                PLAYER_URL + "get_live_info",
                json=params,
                headers=headers,
                timeout=PLAYER_TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()
        if result.get("code") != 0:
            raise ValueError(result.get("msg") or "play api rejected channel")
        data = result.get("data") or {}
        if data.get("iretcode") not in (None, 0):
            raise ValueError(data.get("errinfo") or "channel is unavailable")
        candidates = data.get("backurl_list") or []
        locations = [item.get("url") for item in candidates if isinstance(item, dict)]
        locations.append(data.get("playurl"))
        for location in locations:
            if isinstance(location, str) and location.startswith("https://"):
                return location
        raise ValueError("missing hls manifest")

    def _auth(self, session, pid, guid):
        params = {
            "pid": pid,
            "guid": guid,
            "appid": "ysp_pc",
            "rand_str": _random_text(),
        }
        params["signature"] = _signature(params, AUTH_SALT)
        response = session.post(
            PLAYER_URL + "auth",
            data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
            timeout=PLAYER_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        data = result.get("data") or {}
        if result.get("code") != 0 or not data.get("token") or not data.get("ts"):
            raise ValueError(result.get("msg") or "player auth failed")
        return data

    def _sdk_headers(self, session, guid, params):
        sdk_input = _md5(_canonical_query(params))
        sequence = "1"
        request_id = "999999{}{}".format(_random_text(), int(time.time() * 1000))
        composite = "{}-{}-{}-{}".format(sdk_input, guid, sequence, request_id)
        state = {
            "guid": guid,
            "token": "",
            "yspappid": YSP_APP_ID,
            "input": "",
            "ts": str(int(time.time() * 1000)),
            "version": "v1",
            "query": "object",
        }
        token_random = self.keygen.token_random(state)
        response = session.get(
            OPEN_TOKEN_URL,
            params={
                "yspappid": YSP_APP_ID,
                "guid": guid,
                "vappid": OPEN_VAPP_ID,
                "vsecret": OPEN_VSECRET,
                "raw": 1,
                "version": "v1",
                "ts": state["ts"],
                "rnd": token_random,
            },
            timeout=PLAYER_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        data = result.get("data") or {}
        if not data.get("token"):
            raise ValueError(result.get("msg") or "open token failed")
        state["token"] = data["token"]
        state["input"] = composite
        sdk_signature = self.keygen.signature(state) + "-" + composite
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "yspsdkinput": sdk_input,
            "yspsdksign": sdk_signature,
            "seqId": sequence,
            "request-id": request_id,
            "yspappid": YSP_APP_ID,
        }

    @staticmethod
    def _ckey(cnlid, timestamp, guid):
        raw = (
            "|{}|{}|mg3c3b04ba|{}|{}|{}|https://www.yangshipin.c|"
            "mozilla/5.0 (windows nt ||Mozilla|Netscape|Win32|"
        ).format(cnlid, timestamp, APP_VERSION, guid, PLATFORM)
        value = 0
        for character in raw:
            value = ((value << 5) - value + ord(character)) & 0xFFFFFFFF
        if value >= 0x80000000:
            value -= 0x100000000
        source = ("|{}{}".format(value, raw)).encode("utf-8")
        cipher = AES.new(
            bytes.fromhex("48e5918a74ae21c972b90cce8af6c8be"),
            AES.MODE_CBC,
            bytes.fromhex("9a7e7d23610266b1d9fbf98581384d92"),
        )
        return "--01" + cipher.encrypt(pad(source, 16)).hex().upper()

    @staticmethod
    def _session(guid):
        session = requests.Session()
        session.headers.update({
            "Origin": HOST,
            "Referer": HOST + "/",
            "User-Agent": USER_AGENT,
            "sec-ch-ua": '"Chromium";v="148", "Not=A?Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "yspappid": YSP_APP_ID,
        })
        session.cookies.update({
            "guid": guid,
            "versionName": "99.99.99",
            "versionCode": "999999",
            "vplatform": "109",
            "platformVersion": "Chrome",
            "deviceModel": "148",
            "newLogin": "1",
            "nseqId": "1",
        })
        return session

    @staticmethod
    def _base36(value):
        alphabet = string.digits + string.ascii_lowercase
        result = ""
        while value:
            value, remainder = divmod(value, 36)
            result = alphabet[remainder] + result
        return result or "0"


class Spider(BaseSpider):

    def init(self, extend=""):
        self.snapshot_url = extend
        self.player = None
        self.play_cache = {}
        self.player_lock = threading.RLock()

    def getName(self):
        return "央視頻"

    def liveContent(self, url):
        channels = self._load_channels(url, self.snapshot_url)
        proxy = self.getProxyUrl() + "&siteKey=" + quote(str(self.siteKey), safe="")
        groups = OrderedDict()
        for number, channel in enumerate(channels, 1):
            group = GROUP_NAMES.get(channel.get("type"), "其他頻道")
            groups.setdefault(group, []).append(self._item(channel, number, proxy))
        return json.dumps(
            [{"name": name, "channel": items} for name, items in groups.items()],
            ensure_ascii=False,
        )

    def localProxy(self, param):
        try:
            location = self._resolve(param.get("pid", ""), param.get("cnlid", ""))
            return [302, "text/plain", "", {"Location": location}]
        except Exception as error:
            return [502, "text/plain", "央視頻: " + str(error)]

    def destroy(self):
        with self.player_lock:
            self.player = None
            self.play_cache.clear()

    def _resolve(self, pid, cnlid):
        pid = str(pid)
        cnlid = str(cnlid)
        if not pid.isdigit() or not cnlid.isdigit():
            raise ValueError("invalid channel id")
        cache_key = (pid, cnlid)
        with self.player_lock:
            cached = self.play_cache.get(cache_key)
            if cached and time.monotonic() < cached[0]:
                return cached[1]
            if self.player is None:
                self.player = _PlayerApi()
            location = self.player.resolve(pid, cnlid)
            self.play_cache[cache_key] = (
                time.monotonic() + PLAY_CACHE_SECONDS,
                location,
            )
            return location

    def _load_channels(self, url, snapshot_url):
        try:
            return self._fetch_channels(url or NAVIGATION_URL)
        except (requests.RequestException, ValueError) as error:
            print("央視頻 catalog fallback: {}".format(error))
            return self._load_snapshot(snapshot_url)

    def _fetch_channels(self, navigation_url):
        cache_key = str(int(time.time() / 5))
        with self._new_session() as session:
            navigation = session.get(
                navigation_url + "?" + cache_key,
                timeout=CATALOG_TIMEOUT,
            )
            navigation.raise_for_status()
            feed_id = self._decode_navigation(navigation.content)
            page = session.get(
                PAGE_URL.format(quote(feed_id, safe="")) + "?" + cache_key,
                timeout=CATALOG_TIMEOUT,
            )
            page.raise_for_status()
        channels = self._decode_page(page.content)
        if len(channels) < MIN_CHANNELS:
            raise ValueError("incomplete channel list")
        return channels

    @classmethod
    def _decode_navigation(cls, payload):
        code, data = cls._response(payload)
        if code != 200:
            raise ValueError("navigation response {}".format(code))
        for field, wire, value in cls._fields(data):
            if field != 2 or wire != 2:
                continue
            channel = cls._message(value)
            feed_id = cls._text(channel.get(4))
            name = cls._text(channel.get(1))
            tag = channel.get(10)
            if feed_id and (name in ("电视", "電視") or tag == 2):
                return feed_id
        raise ValueError("missing TV feed")

    @classmethod
    def _decode_page(cls, payload):
        code, data = cls._response(payload)
        if code != 200:
            raise ValueError("page response {}".format(code))
        channels = []
        seen = set()
        for field, wire, module_bytes in cls._fields(data):
            if field != 2 or wire != 2:
                continue
            module = cls._message(module_bytes, repeated={15})
            if cls._text(module.get(2)) != "tvChannel":
                continue
            for channel_bytes in module.get(15, []):
                channel = cls._message(channel_bytes)
                pid = cls._text(channel.get(4))
                name = cls._text(channel.get(2))
                if not pid or not name or pid in seen:
                    continue
                seen.add(pid)
                channels.append({
                    "name": name,
                    "pid": pid,
                    "cnlid": cls._text(channel.get(6)),
                    "logo": cls._text(channel.get(5)),
                    "type": cls._text(channel.get(11)),
                    "vip": bool(channel.get(7, 0)),
                })
        return channels

    @classmethod
    def _response(cls, payload):
        message = cls._message(payload)
        data = message.get(2)
        if not isinstance(data, bytes):
            raise ValueError("invalid protobuf response")
        return message.get(1, 0), data

    @classmethod
    def _message(cls, payload, repeated=None):
        repeated = repeated or set()
        result = {}
        for field, wire, value in cls._fields(payload):
            if field in repeated:
                result.setdefault(field, []).append(value)
            else:
                result[field] = value
        return result

    @classmethod
    def _fields(cls, payload):
        position = 0
        while position < len(payload):
            key, position = cls._varint(payload, position)
            field, wire = key >> 3, key & 7
            if field == 0:
                raise ValueError("invalid protobuf field")
            if wire == 0:
                value, position = cls._varint(payload, position)
            elif wire == 1:
                value = payload[position:position + 8]
                position += 8
            elif wire == 2:
                length, position = cls._varint(payload, position)
                value = payload[position:position + length]
                position += length
            elif wire == 5:
                value = payload[position:position + 4]
                position += 4
            else:
                raise ValueError("unsupported protobuf wire type")
            if position > len(payload):
                raise ValueError("truncated protobuf response")
            yield field, wire, value

    @staticmethod
    def _varint(payload, position):
        value = 0
        shift = 0
        while position < len(payload) and shift < 70:
            byte = payload[position]
            position += 1
            value |= (byte & 0x7F) << shift
            if byte < 0x80:
                return value, position
            shift += 7
        raise ValueError("invalid protobuf varint")

    @staticmethod
    def _text(value):
        if not isinstance(value, bytes):
            return ""
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return ""

    @staticmethod
    def _load_snapshot(url):
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            with requests.get(url, timeout=CATALOG_TIMEOUT) as response:
                response.raise_for_status()
                result = response.json()
        elif parsed.scheme in ("", "file"):
            path = unquote(parsed.path if parsed.scheme else url)
            if len(path) > 2 and path[0] == "/" and path[2] == ":":
                path = path[1:]
            with open(path, encoding="utf-8") as stream:
                result = json.load(stream)
        else:
            raise ValueError("invalid snapshot url")
        channels = result.get("channels") if isinstance(result, dict) else None
        if not isinstance(channels, list) or not channels:
            raise ValueError("invalid channel snapshot")
        return [channel for channel in channels if isinstance(channel, dict)]

    @staticmethod
    def _item(channel, number, proxy):
        pid = str(channel["pid"])
        cnlid = str(channel.get("cnlid") or "")
        name = str(channel["name"])
        return {
            "name": name,
            "tvgName": name,
            "tvgId": pid,
            "number": str(number),
            "logo": str(channel.get("logo") or ""),
            "format": HLS_MIME,
            "ua": USER_AGENT,
            "urls": [
                "{}&cmg=1&pid={}&cnlid={}".format(
                    proxy,
                    quote(pid, safe=""),
                    quote(cnlid, safe=""),
                )
            ],
        }

    @staticmethod
    def _new_session():
        session = requests.Session()
        session.headers.update({
            "Accept": "application/octet-stream",
            "Referer": HOST + "/",
            "User-Agent": USER_AGENT,
            "app-platform": "pc",
            "app-version": "1.0.0",
            "platform": "109",
            "yspappid": YSP_APP_ID,
        })
        return session
