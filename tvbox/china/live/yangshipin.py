import datetime
import hashlib
import json
import os
import random
import re
import string
import struct
import tempfile
import threading
import time
from collections import OrderedDict
from urllib.parse import quote, unquote, urlparse

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from base.spider import Spider as BaseSpider


HOST = "https://www.yangshipin.cn"
NAVIGATION_URL = "https://capi.yangshipin.cn/api/oms/pc/navigation/home_top_nav"
PAGE_URL = "https://capi.yangshipin.cn/api/oms/pc/page/{}"
PLAYER_URL = "https://player-api.yangshipin.cn/v1/player/"
OPEN_TOKEN_URL = "https://h5access.yangshipin.cn/web/open/token"
KEYGEN_URL = "https://s.yangshipin.cn/CCTVVideo/cctvh5-openapicore/keygen_bg.wasm"
EPG_URL = "https://api.cntv.cn/epg/getEpgInfoByChannelNew"
HLS_MIME = "application/x-mpegURL"
CATALOG_TIMEOUT = 8
PLAYER_TIMEOUT = 15
PLAYER_BUDGET = 25
KEYGEN_CACHE_SECONDS = 24 * 60 * 60
EPG_CACHE_SECONDS = 60 * 60
TAIPEI = datetime.timezone(datetime.timedelta(hours=8))
LOGO_URL = "https://epg.112114.xyz/logo/{}.png"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)
GROUP_NAMES = {"yangshi": "央視頻道", "weishi": "衛視頻道"}
# Repeated regional-rights rejection, verified 2026-09-05.
# Recheck playback before restoring these channels.
EXCLUDED_PIDS = frozenset()
# EXCLUDED_PIDS = frozenset({
#     "600001818",  # CCTV5
#     "600001817",  # CCTV5+
#     "600098637",  # CCTV16-HD
#     "600099502",  # CCTV16 4K
# })
})
XMLTV_NAMES = {
    "CCTV1": "CCTV-1 综合",
    "CCTV2": "CCTV-2 财经",
    "CCTV3": "CCTV-3 综艺",
    "CCTV4": "CCTV-4 中文国际",
    "CCTV5": "CCTV-5 体育",
    "CCTV5+": "CCTV-5+ 体育赛事",
    "CCTV6": "CCTV-6 电影",
    "CCTV7": "CCTV-7 国防 军事",
    "CCTV8": "CCTV-8 电视剧",
    "CCTV9": "CCTV-9 记录",
    "CCTV10": "CCTV-10 科教",
    "CCTV11": "CCTV-11 戏曲",
    "CCTV12": "CCTV-12 社会与法",
    "CCTV13": "CCTV-13 新闻",
    "CCTV14": "CCTV-14 少儿",
    "CCTV15": "CCTV-15 音乐",
    "CCTV16-HD": "CCTV-16 奥林匹克",
    "CCTV16(4K）": "CCTV-16 奥林匹克",
    "CCTV17": "CCTV-17 农业 农村",
    "CCTV4K": "CCTV-4K",
    "CCTV8K": "CCTV8K",
    "CGTN": "CGTN英语",
    "CGTN法语频道": "CGTN法语",
    "CGTN俄语频道": "CGTN俄语",
    "CGTN阿拉伯语频道": "CGTN阿拉伯语",
    "CGTN西班牙语频道": "CGTN西班牙语",
    "CGTN外语纪录频道": "CGTN英文记录",
    "CCTV风云剧场频道": "CCTV-风云剧场",
    "CCTV第一剧场频道": "CCTV-第一剧场",
    "CCTV怀旧剧场频道": "CCTV-怀旧剧场",
    "CCTV世界地理频道": "CCTV-世界地理",
    "CCTV风云音乐频道": "CCTV-风云音乐",
    "CCTV兵器科技频道": "CCTV-兵器科技",
    "CCTV风云足球频道": "CCTV-央视足球",
    "CCTV高尔夫·网球频道": "CCTV-高尔夫网球",
    "CCTV女性时尚频道": "CCTV-女性时尚",
    "CCTV央视文化精品频道": "CCTV-央视文化精品",
    "CCTV央视台球频道": "CCTV-央视台球",
    "CCTV电视指南频道": "CCTV-电视指南",
    "CCTV卫生健康频道": "CCTV-卫生健康",
}
LOGO_NAMES = {
    "CCTV16-HD": "CCTV16",
    "CCTV16(4K）": "CCTV16-4K",
    "CGTN阿拉伯语频道": "CGTN阿拉伯语",
    "CGTN西班牙语频道": "CGTN西班牙语",
    "CGTN外语纪录频道": "CGTN纪录",
    "CCTV高尔夫·网球频道": "CCTV高尔夫网球",
}
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


def _cntv_epg_id(name):
    special = {
        "CCTV5+": "cctv5plus",
        "CCTV16-HD": "cctv16",
        "CCTV16(4K）": "cctv16",
        "CCTV4K": "cctv4k",
        "CCTV8K": "cctv8k",
        "CCTV第一剧场频道": "diyijuchang",
        "CCTV世界地理频道": "shijiedili",
    }
    if name in special:
        return special[name]
    match = re.fullmatch(r"CCTV(\d{1,2})", name)
    if not match or not 1 <= int(match.group(1)) <= 17:
        return ""
    if match.group(1) == "9":
        return "cctvjilu"
    if match.group(1) == "14":
        return "cctvchild"
    return "cctv" + match.group(1)


def _logo(name, fallback):
    logo_name = LOGO_NAMES.get(name)
    if not logo_name:
        logo_name = name[:-2] if name.endswith("频道") else name
    return LOGO_URL.format(quote(logo_name, safe="")) if logo_name else fallback


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


class _ProxyError(ValueError):

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def _remaining(deadline, stage):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise _ProxyError(504, stage + ": 取址逾時")
    return remaining


def _net_response(net, url, timeout, headers=None, params=None, buffer=0, data=None,
                  post_type="json", deadline=None, stage="網路請求"):
    if deadline is not None:
        timeout = min(timeout, _remaining(deadline, stage))
    milliseconds = max(1, int(timeout * 1000))
    options = {
        "headers": headers or {},
        "timeout": milliseconds,
        "callTimeout": milliseconds,
        "buffer": buffer,
    }
    if params:
        options["params"] = params
    if data is not None:
        options.update({"method": "POST", "data": data, "postType": post_type})
    result = net.req(url, options)
    if result.get("error"):
        error = str(result["error"])
        status = 504 if "timeout" in error.lower() or "timed out" in error.lower() else 502
        raise _ProxyError(status, stage + ": " + error)
    if deadline is not None:
        _remaining(deadline, stage)
    if result["code"] >= 400:
        raise _ProxyError(result["code"], stage + ": HTTP " + str(result["code"]))
    return result


def _download_keygen(net, deadline):
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

    if not _KEYGEN_LOCK.acquire(timeout=_remaining(deadline, "簽名檔更新")):
        raise _ProxyError(504, "簽名檔更新: 等待逾時")
    try:
        cached = valid()
        try:
            with open(path + ".json", encoding="utf-8") as stream:
                metadata = json.load(stream)
        except (OSError, ValueError):
            metadata = {}
        if not isinstance(metadata, dict) or not cached:
            metadata = {}
        checked_at = metadata.get("checkedAt", 0)
        age = time.time() - checked_at if isinstance(checked_at, (int, float)) else KEYGEN_CACHE_SECONDS
        if cached and 0 <= age < KEYGEN_CACHE_SECONDS:
            return path
        headers = {"User-Agent": USER_AGENT}
        for key, header in (("etag", "If-None-Match"), ("modified", "If-Modified-Since")):
            if isinstance(metadata.get(key), str) and metadata[key]:
                headers[header] = metadata[key]
        conditional = "If-None-Match" in headers or "If-Modified-Since" in headers
        result = _net_response(net, KEYGEN_URL, PLAYER_TIMEOUT, headers, buffer=3,
                               deadline=deadline, stage="簽名檔更新")
        if result["code"] == 200:
            payload = result["content"]
            if not (minimum_size <= len(payload) <= maximum_size) or payload[:4] != b"\x00asm":
                raise _ProxyError(502, "簽名檔更新: invalid official wasm")
            _write_file(path, payload)
            metadata = {}
        elif result["code"] != 304 or not conditional:
            raise _ProxyError(502, "簽名檔更新: unexpected HTTP " + str(result["code"]))
        response_headers = {key.lower(): value for key, value in result.get("headers", {}).items()}
        for key, header in (("etag", "etag"), ("modified", "last-modified")):
            value = response_headers.get(header)
            if isinstance(value, str):
                metadata[key] = value
        metadata["checkedAt"] = time.time()
        _write_file(path + ".json", json.dumps(metadata).encode("utf-8"))
        return path
    finally:
        _KEYGEN_LOCK.release()


def _write_file(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".download"
    try:
        with open(temporary, "wb") as stream:
            stream.write(payload)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


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

    def __init__(self, net, deadline):
        self.net = net
        self.keygen = None
        self.keygen_hash = None
        self._update_keygen(deadline)

    def _update_keygen(self, deadline):
        path = _download_keygen(self.net, deadline)
        with open(path, "rb") as stream:
            digest = hashlib.sha256(stream.read()).digest()
        if digest != self.keygen_hash:
            self.keygen = _Keygen(path)
            self.keygen_hash = digest
        _remaining(deadline, "簽名初始化")

    def resolve(self, pid, cnlid, deadline):
        self._update_keygen(deadline)
        guid = "{}_{}".format(self._base36(int(time.time() * 1000)), _random_text(11))
        with self._session(guid) as session:
            auth = self._auth(session, pid, guid, deadline)
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
            headers = self._sdk_headers(session, guid, params, deadline)
            headers["yspPlayerToken"] = str(auth["token"])
            headers["yspticket"] = _ticket(pid, str(auth["ts"]), guid)
            params["rand_str"] = _random_text()
            params["signature"] = _signature(params, REQUEST_SALT)
            result = self._request_json(
                session, PLAYER_URL + "get_live_info", deadline, "取得播放資訊", data=params, headers=headers
            )
        if result.get("code") != 0:
            raise _ProxyError(502, "取得播放資訊: " + str(result.get("msg") or "play api rejected channel"))
        data = result.get("data") or {}
        if data.get("iretcode") not in (None, 0):
            raise _ProxyError(502, "取得播放資訊: " + str(data.get("errinfo") or "channel is unavailable"))
        candidates = data.get("backurl_list") or []
        locations = [item.get("url") for item in candidates if isinstance(item, dict)]
        locations.append(data.get("playurl"))
        for location in locations:
            if isinstance(location, str) and location.startswith("https://"):
                return location
        raise _ProxyError(502, "取得播放資訊: missing hls manifest")

    def _auth(self, session, pid, guid, deadline):
        params = {
            "pid": pid,
            "guid": guid,
            "appid": "ysp_pc",
            "rand_str": _random_text(),
        }
        params["signature"] = _signature(params, AUTH_SALT)
        result = self._request_json(
            session, PLAYER_URL + "auth", deadline, "播放授權", data=params, post_type="form",
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        )
        data = result.get("data") or {}
        if result.get("code") != 0 or not data.get("token") or not data.get("ts"):
            raise _ProxyError(502, "播放授權: " + str(result.get("msg") or "player auth failed"))
        return data

    def _sdk_headers(self, session, guid, params, deadline):
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
        result = self._request_json(
            session, OPEN_TOKEN_URL, deadline, "簽名授權",
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
        )
        data = result.get("data") or {}
        if not data.get("token"):
            raise _ProxyError(502, "簽名授權: " + str(result.get("msg") or "open token failed"))
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

    def _request_json(self, session, url, deadline, stage, params=None, headers=None, data=None, post_type="json"):
        result = _net_response(
            session, url, PLAYER_TIMEOUT, {**self._headers(), **(headers or {})},
            params=params, data=data, post_type=post_type, deadline=deadline, stage=stage,
        )
        try:
            data = json.loads(result["content"])
            if not isinstance(data, dict):
                raise ValueError("expected JSON object")
            return data
        except (TypeError, ValueError) as error:
            raise _ProxyError(502, stage + ": invalid JSON response") from error

    @staticmethod
    def _headers():
        return {
            "Origin": HOST,
            "Referer": HOST + "/",
            "User-Agent": USER_AGENT,
            "sec-ch-ua": '"Chromium";v="148", "Not=A?Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "yspappid": YSP_APP_ID,
        }

    def _session(self, guid):
        cookies = {
            "guid": guid,
            "versionName": "99.99.99",
            "versionCode": "999999",
            "vplatform": "109",
            "platformVersion": "Chrome",
            "deviceModel": "148",
            "newLogin": "1",
            "nseqId": "1",
        }
        session = self.net.session()
        try:
            # Player and open-token APIs use different Yangshipin subdomains.
            for name, value in cookies.items():
                if not session.setCookie(HOST, "{}={}; Domain=yangshipin.cn; Path=/".format(name, value)):
                    raise ValueError("invalid player cookie")
            return session
        except Exception:
            session.close()
            raise

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
        self.destroyed = False
        self.player_lock = threading.RLock()
        self.player_ready = threading.Event()
        threading.Thread(
            target=self._warm_player,
            name="yangshipin-player-warmup",
            daemon=True,
        ).start()

    def _warm_player(self):
        try:
            player = _PlayerApi(self.net, time.monotonic() + PLAYER_BUDGET)
            with self.player_lock:
                if not self.destroyed:
                    self.player = player
        except Exception as error:
            print("央視頻 player warmup: {}".format(error))
        finally:
            self.player_ready.set()

    def getName(self):
        return "央視頻"

    def liveContent(self, url):
        channels = [
            channel
            for channel in self._load_channels(url, self.snapshot_url)
            if not channel.get("vip")
            and str(channel.get("pid")) not in EXCLUDED_PIDS
        ]
        groups = OrderedDict()
        for number, channel in enumerate(channels, 1):
            group = GROUP_NAMES.get(channel.get("type"), "其他頻道")
            groups.setdefault(group, []).append(self._item(channel, number))
        return [{"name": name, "channel": items} for name, items in groups.items()]

    def localProxy(self, param):
        try:
            if param.get("type") == "epg":
                content = self._epg(param.get("id", ""), param.get("date", ""))
                return [200, "application/json", content]
            refresh = "no-cache" in str(param.get("cache-control", "")).lower().replace(" ", "").split(",")
            location = self._resolve(param.get("pid", ""), param.get("cnlid", ""), refresh)
            return [302, "text/plain", "", {"Location": location}]
        except _ProxyError as error:
            return [error.status, "text/plain; charset=utf-8", "央視頻: " + str(error)]
        except Exception as error:
            return [502, "text/plain; charset=utf-8", "央視頻: " + str(error)]

    def destroy(self):
        with self.player_lock:
            self.destroyed = True
            self.player = None

    def _epg(self, channel_id, date):
        if not isinstance(channel_id, str) or not re.fullmatch(r"[a-z0-9]+", channel_id):
            raise _ProxyError(400, "invalid epg channel id")
        try:
            datetime.date.fromisoformat(date)
        except (TypeError, ValueError):
            raise _ProxyError(400, "invalid date") from None
        return self.net.cached("epg:" + channel_id + ":" + date,
                               {"ttl": EPG_CACHE_SECONDS * 1000, "stale": False},
                               lambda: self._load_epg(channel_id, date))

    def _load_epg(self, channel_id, date):
        result = self._get_json(
            EPG_URL,
            params={
                "c": channel_id,
                "serviceId": "tvcctv",
                "d": date.replace("-", ""),
            },
            headers={"Referer": "https://tv.cctv.com/", "User-Agent": USER_AGENT},
        )
        data = result.get("data") if isinstance(result, dict) else None
        channel = data.get(channel_id) if isinstance(data, dict) else None
        rows = channel.get("list") if isinstance(channel, dict) else None
        if not isinstance(rows, list):
            raise ValueError("invalid epg response")
        items = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").strip()
            if not title:
                continue
            try:
                start = datetime.datetime.fromtimestamp(
                    int(row.get("startTime")), TAIPEI
                ).strftime("%H:%M:%S")
                end = datetime.datetime.fromtimestamp(
                    int(row.get("endTime")), TAIPEI
                ).strftime("%H:%M:%S")
            except (TypeError, ValueError, OverflowError):
                continue
            items.append({"title": title, "start": start, "end": end})
        content = json.dumps(
            {"date": date, "epg_data": items},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return content

    def _resolve(self, pid, cnlid, refresh=False):
        pid, cnlid = str(pid), str(cnlid)
        if not pid.isdigit() or not cnlid.isdigit():
            raise _ProxyError(400, "invalid channel id")
        if self.destroyed:
            raise _ProxyError(503, "播放服務已關閉")
        deadline = time.monotonic() + PLAYER_BUDGET
        key = "play:" + pid + ":" + cnlid
        if refresh:
            self.net.clearCache(key)
        return self.net.cached(key,
                               {"ttl": PLAY_CACHE_SECONDS * 1000, "stale": False},
                               lambda: self._resolve_player(pid, cnlid, deadline))

    def _resolve_player(self, pid, cnlid, deadline):
        if not self.player_ready.wait(_remaining(deadline, "簽名初始化")):
            raise _ProxyError(504, "簽名初始化: 等待逾時")
        if not self.player_lock.acquire(timeout=_remaining(deadline, "播放取址")):
            raise _ProxyError(504, "播放取址: 等待逾時")
        try:
            if self.destroyed:
                raise _ProxyError(503, "播放服務已關閉")
            if self.player is None:
                self.player = _PlayerApi(self.net, deadline)
            return self.player.resolve(pid, cnlid, deadline)
        finally:
            self.player_lock.release()

    def _load_channels(self, url, snapshot_url):
        try:
            return self._fetch_channels(url or NAVIGATION_URL)
        except (OSError, ValueError) as error:
            print("央視頻 catalog fallback: {}".format(error))
            return self._load_snapshot(snapshot_url)

    def _fetch_channels(self, navigation_url):
        cache_key = str(int(time.time() / 5))
        navigation = self._catalog_bytes(navigation_url + "?" + cache_key)
        feed_id = self._decode_navigation(navigation)
        page = self._catalog_bytes(PAGE_URL.format(quote(feed_id, safe="")) + "?" + cache_key)
        channels = self._decode_page(page)
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

    def _load_snapshot(self, url):
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            result = self._get_json(url)
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

    def _item(self, channel, number):
        pid = str(channel["pid"])
        cnlid = str(channel.get("cnlid") or "")
        name = str(channel["name"])
        epg_id = _cntv_epg_id(name)
        item = {
            "name": name,
            "tvgName": XMLTV_NAMES.get(name, name),
            "tvgId": pid,
            "number": "{:02d}".format(number),
            "logo": _logo(name, str(channel.get("logo") or "")),
            "format": HLS_MIME,
            "ua": USER_AGENT,
            "urls": [self.getProxyUrl({"cmg": "1", "pid": pid, "cnlid": cnlid})],
        }
        if epg_id:
            item["epg"] = self.getProxyUrl({"type": "epg", "id": epg_id}) + "&date={date}"
        return item

    def _get_json(self, url, params=None, headers=None):
        options = {"headers": headers or {}, "timeout": CATALOG_TIMEOUT * 1000}
        if params:
            options["params"] = params
        try:
            return self.net.json(url, options)
        except Exception as error:
            raise ValueError(str(error)) from None

    def _catalog_bytes(self, url):
        return _net_response(self.net, url, CATALOG_TIMEOUT, self._catalog_headers(), buffer=3,
                             stage="頻道清單")["content"]

    @staticmethod
    def _catalog_headers():
        return {
            "Accept": "application/octet-stream",
            "Referer": HOST + "/",
            "User-Agent": USER_AGENT,
            "app-platform": "pc",
            "app-version": "1.0.0",
            "platform": "109",
            "yspappid": YSP_APP_ID,
        }
