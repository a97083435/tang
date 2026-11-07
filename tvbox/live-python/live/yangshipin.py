import base64
import datetime
import hashlib
import json
import os
import random
import re
import secrets
import string
import struct
import tempfile
import threading
import time
import uuid
from collections import OrderedDict
from contextlib import contextmanager, suppress
from urllib.parse import quote, unquote, urljoin, urlparse

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
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
TV_APP_ID = "9f5c54c4ed0e50109b800f7e28fec205"
TV_VERSION = "1.4.1"
TV_BASE = "https://ytpaddr.cctv.cn/gsnw/"
TV_CLOUD = "https://ytpcloudws.cctv.cn/cloudps/wssapi/device/v2/"
TV_DEVICE_CODES = {
    TV_CLOUD + "get": ("0", "2", "601"),
    TV_CLOUD + "register": ("0", "2", "694"),
}
TV_REPORT = "https://ytpdata.cctv.cn/das/app/data/message/single"
TV_VDN = "https://ytpvdn.cctv.cn/cctvmobileinf/rest/cctv/videoliveUrl/getstream"
TV_PUBLIC_KEY = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAkKeLy4ywWLSnBkwRyqYgF3HMIj05V5uuh5Hj"
    "yEsZOWnu1NHu3jPQv3sr32wwQNYv5qapsNXmNgLUDHtgHZxqPQAYXltjSRc0qhcD286t62wOIHId8zXS"
    "3s1Jy4rgU4qjQWzI9rp/1sE0pMsmwTaJa4zuJ5iz8VwF8Av5oJ1k+HxY+/HLnjNlW1hmWLpuDYmkZYuA"
    "oTHa1VGeHQh9FEKI8ZcL3GTQphShUoC+Kg3P1hGUVTtCYapmzPS5lkAdwebuzwvTCfGiTErYZCnPBUSe"
    "V7BVlgjtLYIi29KvF0a8FHsJMfe/UdHcyW/RihsIYOtDQcRRpFGXyPXbVrzFJse24QIDAQAB"
)
TV_CHANNELS = {
    "600001859": "Live1717729995180256",  # CCTV-1 综合
    "600001800": "Live1718261577870260",  # CCTV-2 财经
    "600001801": "Live1718261955077261",  # CCTV-3 综艺
    "600001814": "Live1718276148119264",  # CCTV-4 中文国际
    "600001818": "Live1719474204987287",  # CCTV-5 体育
    "600001817": "Live1719473996025286",  # CCTV-5+ 体育赛事
    "600004092": "Live1718276412224269",  # CCTV-7 国防军事
    "600001803": "Live1718276458899270",  # CCTV-8 电视剧
    "600004078": "Live1718276503187272",  # CCTV-9 纪录
    "600001805": "Live1718276550002273",  # CCTV-10 科教
    "600001806": "Live1718276603690275",  # CCTV-11 戏曲
    "600001807": "Live1718276623932276",  # CCTV-12 社会与法
    "600001811": "Live1718276575708274",  # CCTV-13 新闻
    "600001809": "Live1718276498748271",  # CCTV-14 少儿
    "600001815": "Live1718276319614267",  # CCTV-15 音乐
    "600098637": "Live1718276256572265",  # CCTV-16 奥林匹克
    "600099502": "Live1704966749996185",  # CCTV-16 4K
    "600001810": "Live1718276138318263",  # CCTV-17 农业农村
    "600002264": "Live1767871224782105",  # CCTV-4K 超高清
    "600156816": "Live1688400593818102",  # CCTV-8K 超高清
    "600014550": "Live1719392219423280",  # CGTN
    "600084704": "Live1719392670442283",  # CGTN 法语
    "600084758": "Live1719392779653284",  # CGTN 俄语
    "600084782": "Live1719392885692285",  # CGTN 阿拉伯语
    "600084744": "Live1719392560433282",  # CGTN 西班牙语
    "600084781": "Live1719392360336281",  # CGTN 纪录
}
APP_LIVE_URL = "https://bkliveinfo.ysp.cctv.cn/"
APP_LIVE_PLATFORM = 4330403
APP_LIVE_VERSION = "V8.22.1035.3031"
PLAY_CACHE_SECONDS = 60
PLAY_SESSION_SECONDS = 7200
AUTO_SOURCE_SECONDS = 8
AUTO_CHOICE_SECONDS = 300
AUTO_FAILURE_SECONDS = 30
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


def _media_url(location, data):
    extension = data.get("extended_param")
    extension = "" if extension is None else extension
    if not isinstance(extension, str) or (extension and not extension.startswith("&")):
        raise _ProxyError(502, "播放地址: invalid media parameters")
    return location + (extension if "?" in location or not extension else "?" + extension[1:])


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


@contextmanager
def _timing(stage):
    started = time.perf_counter()
    success = False
    try:
        yield
        success = True
    finally:
        record = json.dumps({
            "stage": stage,
            "ms": round((time.perf_counter() - started) * 1000, 1),
            "ok": success,
        }, separators=(",", ":"))
        with suppress(OSError, ValueError):
            print("YSP timing " + record)


def _net_response(net, url, timeout, headers=None, params=None, buffer=0, data=None,
                  post_type="json", deadline=None, stage="網路請求", redirect=1, allowed_status=()):
    if deadline is not None:
        timeout = min(timeout, _remaining(deadline, stage))
    milliseconds = max(1, int(timeout * 1000))
    options = {
        "headers": headers or {},
        "timeout": milliseconds,
        "callTimeout": milliseconds,
        "buffer": buffer,
        "redirect": redirect,
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
    if result["code"] >= 400 and result["code"] not in allowed_status:
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


class _Keygen:

    def __init__(self, path):
        import pywasm

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
        for exported in self.runtime.machine.module.export_list:
            if exported.name == "memory":
                self.memory = self.runtime.machine.store.memory_list[exported.value]
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
        with _timing("keygen"):
            self._update_keygen(deadline)
        guid = "{}_{}".format(self._base36(int(time.time() * 1000)), _random_text(11))
        with self._session(guid) as session:
            with _timing("auth"):
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
            with _timing("play_info"):
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
                return _media_url(location, data)
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
        with _timing("token_random"):
            token_random = self.keygen.token_random(state)
        with _timing("open_token"):
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
        with _timing("signature"):
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


def _is_channel_id(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9]+", value) is not None


def _playback_url(value):
    if not isinstance(value, str) or re.search(r"[\s\x00-\x1f\x7f\\]", value):
        return False
    try:
        parsed = urlparse(value)
        host = parsed.hostname or ""
        if parsed.port == 0 or parsed.username is not None or parsed.password is not None:
            return False
        return parsed.scheme in ("http", "https") and any(
            host == suffix or host.endswith("." + suffix)
            for suffix in ("cctv.cn", "cctv.com", "cntv.cn", "cntv.com", "cctvpic.com", "citvc.com", "yangshipin.cn")
        )
    except ValueError:
        return False


class _AppPlayerApi:

    def __init__(self, owner):
        self.owner = owner
        self.net = owner.net

    @staticmethod
    def _checksum(data):
        value = 0
        for byte in data:
            value = (131 * value + byte) & 0x7FFFFFFF
        return value

    @staticmethod
    def _pack(value):
        data = value.encode("utf-8") if isinstance(value, str) else value
        return struct.pack(">H", len(data)) + data

    @staticmethod
    def _tea_block(block, key):
        left, right = struct.unpack(">2I", block)
        keys = struct.unpack(">4I", key)
        total = 0
        for _ in range(16):
            total = (total + 0x9E3779B9) & 0xFFFFFFFF
            left = (left + (((right << 4) + keys[0]) ^ (right + total) ^ ((right >> 5) + keys[1]))) & 0xFFFFFFFF
            right = (right + (((left << 4) + keys[2]) ^ (left + total) ^ ((left >> 5) + keys[3]))) & 0xFFFFFFFF
        return struct.pack(">2I", left, right)

    @classmethod
    def _tea_packet(cls, data, key):
        padding = (8 - (len(data) + 10) % 8) % 8
        plain = bytes([(secrets.token_bytes(1)[0] & 248) | padding]) + secrets.token_bytes(padding + 2) + data + bytes(7)
        previous_plain = previous_cipher = bytes(8)
        output = bytearray()
        for offset in range(0, len(plain), 8):
            mixed = bytes(a ^ b for a, b in zip(plain[offset:offset + 8], previous_cipher))
            encrypted = cls._tea_block(mixed, key)
            cipher = bytes(a ^ b for a, b in zip(encrypted, previous_plain))
            output.extend(cipher)
            previous_plain, previous_cipher = mixed, cipher
        return bytes(output)

    @classmethod
    def _ckey(cls, cnlid):
        timestamp = int(time.time())
        guid = secrets.token_bytes(16).hex()
        guard = cls._pack(struct.pack(">I", timestamp) + cls._pack(guid[-5:])
                          + cls._pack("") + cls._pack("") + cls._pack("-1"))
        encrypted = cls._tea_packet(guard, bytes.fromhex("110dbec10c23e7d2e56a1cad6914ef1b"))
        encrypted += struct.pack(">I", cls._checksum(guard))
        mask = bytes.fromhex("b3c953a06913ad4d")
        guard = bytes(value ^ mask[index % len(mask)] for index, value in enumerate(encrypted)).hex().upper()
        body = bytes.fromhex("0000004200000004000004d2") + struct.pack(">3I", APP_LIVE_PLATFORM, 0, timestamp)
        for value in ("dcgh", "_zj1A5Gh6QYcxWjIUGos2w==", APP_LIVE_VERSION, cnlid, guid):
            body += cls._pack(value)
        body += struct.pack(">2I", 1, 1)
        for value in (secrets.token_bytes(4).hex().upper(), "nil", "57eab0c4-2c58-44c6-8ae9-dd2757525dc5",
                      "nil", "v0.1.000", "com.cctv.yangshipin.app.iphone", str(APP_LIVE_PLATFORM),
                      "ex_json_bus", "ex_json_vs", guard):
            body += cls._pack(value)
        packet = bytearray(cls._pack(body))
        packet[18:22] = struct.pack(">I", cls._checksum(packet))
        encrypted = cls._tea_packet(bytes(packet), bytes.fromhex("59b2f7cf725ef43c34fdd7c123411ed3"))
        encrypted += struct.pack(">I", cls._checksum(packet))
        mask = bytes.fromhex("842eed08f066e6ea48b4caa991ed6ff3")
        encrypted = bytes(value ^ mask[index % len(mask)] for index, value in enumerate(encrypted))
        ckey = base64.b64encode(encrypted).decode().replace("+", "_").replace("/", "-").rstrip("=")
        return {"cKey": "--01" + ckey, "guid": guid, "fntick": str(timestamp),
                "flowid": uuid.uuid4().hex.upper() + "_" + str(APP_LIVE_PLATFORM)}

    def resolve(self, pid, cnlid, deadline, definition="fhd"):
        self.owner._assert_active()
        params = {
            "atime": "120", "livepid": pid, "cnlid": cnlid, "appVer": APP_LIVE_VERSION,
            "app_version": "300090", "caplv": "1", "cmd": "2", "defn": definition,
            "device": "iPhone", "encryptVer": "4.2", "getpreviewinfo": "0", "hevclv": "0",
            "lang": "zh-Hans_CN", "livequeue": "0", "logintype": "1", "nettype": "1", "newnettype": "1",
            "newplatform": str(APP_LIVE_PLATFORM), "platform": str(APP_LIVE_PLATFORM), "sdtfrom": "v3021",
            "spacode": "23", "spaudio": "1", "spdemuxer": "6", "spdrm": "2", "spdynamicrange": "1",
            "spflv": "1", "spflvaudio": "1", "sphdrfps": "60", "sphttps": "1",
            "spvcode": base64.b64encode(b"H(30:1080,60:1080|30:1080,60:1080)").decode(),
            "spvideo": "4", "stream": "1", "system": "1", "sysver": "ios18.2.1",
            "uhd_flag": "0", "playbacktime": "0", **self._ckey(cnlid),
        }
        result = _net_response(self.net, APP_LIVE_URL, PLAYER_TIMEOUT,
                               {"User-Agent": "qqlive", "Accept": "application/json"},
                               params=params, deadline=deadline, stage="App 直播取址")
        self.owner._assert_active()
        if not 200 <= result["code"] < 300:
            raise _ProxyError(502, "App 直播取址: HTTP " + str(result["code"]))
        try:
            value = json.loads(result["content"])
            if not isinstance(value, dict):
                raise ValueError("expected object")
        except (TypeError, ValueError) as error:
            raise _ProxyError(502, "App 直播取址: invalid JSON response") from error
        code = value.get("iretcode")
        if type(code) not in (int, str) or str(code) != "0":
            code = str(code) if str(code).lstrip("-").isdigit() else "invalid"
            raise _ProxyError(502, "App 直播取址: iretcode=" + code)
        candidates = [value.get("playurl")]
        backup = value.get("backurl_list") or value.get("backurlList") or value.get("backurl")
        if isinstance(backup, list):
            for item in backup:
                candidates.append(item.get("url") or item.get("playurl") if isinstance(item, dict) else item)
        elif isinstance(backup, str):
            candidates.extend(re.split(r"[;,]\s*(?=https?://)", backup))
        location = next((candidate for candidate in candidates if _playback_url(candidate)), None)
        if location is None:
            raise _ProxyError(502, "App 直播取址: no usable HLS URL")
        headers = value.get("http_header", {})
        if not isinstance(headers, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in headers.items()):
            raise _ProxyError(502, "App 直播取址: invalid playback headers")
        return {"url": _media_url(location, value), "headers": {"User-Agent": "qqlive", "Referer": "https://live.cctv.cn/", **headers}}


class _TvPlayerApi:

    def __init__(self, owner):
        self.owner = owner
        self.net = owner.net
        identity = owner.local.get("tv-device:v1")
        if not (isinstance(identity, dict)
                and isinstance(identity.get("android_id"), str)
                and isinstance(identity.get("mac"), str)
                and re.fullmatch(r"[0-9a-f]{16}", identity["android_id"])
                and re.fullmatch(r"[0-9a-f]{2}(?::[0-9a-f]{2}){5}", identity["mac"])):
            mac = bytearray(secrets.token_bytes(6))
            mac[0] = (mac[0] | 2) & 254
            identity = {"android_id": secrets.token_hex(8), "mac": ":".join("{:02x}".format(value) for value in mac)}
            owner.local.set("tv-device:v1", identity)
        self.profile = {
            **identity,
            "hardware": "mt5895", "board": "mt5895", "brand": "Sony",
            "device": "sony_xr_85z9k", "manufacturer": "Sony", "model": "XR-85Z9K",
            "product": "sony_xr_85z9k", "tags": "release-keys", "build_type": "user",
            "user": "build", "resolution": "7680*4320",
            "display": "XR-85Z9K-user 13 SONYTV.2022.XR_85Z9K 2024 release-keys",
            "version_id": "SONYTV.2022.XR_85Z9K", "host": "sony-tv-build",
            "fingerprint": "Sony/sony_xr_85z9k/sony_xr_85z9k:13/SONYTV.2022.XR_85Z9K/2024:user/release-keys",
        }
        source = "1698" + "".join(self.profile[key] for key in (
            "hardware", "board", "brand", "device", "manufacturer", "model", "product",
            "tags", "build_type", "user", "resolution", "mac",
        ))
        device_uuid = "{:016x}{:016x}".format(self._hashcode(source) & 0xFFFFFFFFFFFFFFFF,
                                            self._hashcode(self.profile["model"]) & 0xFFFFFFFFFFFFFFFF)
        self.uid = hashlib.sha1((identity["android_id"] + "|" + device_uuid).encode()).hexdigest().upper()
        self.fingerprint = ""
        self.session_key = ""
        self.guid = ""
        self.created_at = 0
        self.last_heartbeat = 0

    @staticmethod
    def _hashcode(value):
        result = 0
        for character in value:
            result = (result * 31 + ord(character)) & 0xFFFFFFFF
        return result - 0x100000000 if result & 0x80000000 else result

    def _common(self):
        p = self.profile
        fields = {
            "cctv_id": self.uid, "device_id": p["android_id"], "idfa": "", "idfv": "",
            "user_id": "", "app_key": "1178c84d-4818-44ff-b415-02106e87e144",
            "imei": "", "android_id": p["android_id"], "mac": p["mac"],
            "system_type": "Android", "device_type": "TV", "app_language": "CHINESE",
            "app_version": TV_VERSION, "sdk_version": "", "os_version": "13",
            "app_channel": "dangbei", "data_time": str(int(time.time() * 1000)),
            "device_builder_type": p["build_type"], "device_params": p["device"],
            "device_model": "XR85Z9K",
        }
        for key in ("hardware", "board", "brand", "display", "version_id", "host", "product",
                    "tags", "user", "fingerprint", "manufacturer", "resolution"):
            fields["device_" + key] = p[key]
        return fields

    def _request(self, url, body, deadline, stage, headers=None, form=False):
        self.owner._assert_active()
        request_headers = {
            "Accept": "application/json", "Accept-Language": "zh-CN,zh;q=0.8",
            "Referer": "api.cctv.cn", "User-Agent": "cctv_app_tv",
            "UID": self.profile["android_id"], "appChannel": "dangbei",
            "X-Uid": self.uid, "X-Fingerprint": self.fingerprint, "X-Version": TV_VERSION,
            "X-Timestamp": str(int(time.time() * 1000)), "X-Nonce": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded" if form else "application/json",
            **(headers or {}),
        }
        result = _net_response(self.net, url, PLAYER_TIMEOUT, request_headers, data=body,
                               post_type="form" if form else "json", deadline=deadline, stage=stage,
                               allowed_status=(400,) if url in TV_DEVICE_CODES else ())
        self.owner._assert_active()
        if result["code"] == 400:
            try:
                value = json.loads(result["content"])
            except (TypeError, ValueError) as error:
                raise _ProxyError(400, stage + ": HTTP 400") from error
            if isinstance(value, dict) and str(value.get("result", value.get("code"))) in TV_DEVICE_CODES[url]:
                return value
            raise _ProxyError(400, stage + ": HTTP 400")
        if not 200 <= result["code"] < 300:
            raise _ProxyError(502, stage + ": HTTP " + str(result["code"]))
        try:
            value = json.loads(result["content"])
            if not isinstance(value, dict):
                raise ValueError("expected object")
            return value
        except (TypeError, ValueError) as error:
            raise _ProxyError(502, stage + ": invalid JSON response") from error

    @staticmethod
    def _data(value, stage):
        code = value.get("result", value.get("code", value.get("ret")))
        if code is not None and str(code) != "0":
            raise _ProxyError(502, stage + ": code=" + str(code))
        if "data" not in value:
            raise _ProxyError(502, stage + ": missing data")
        return value["data"]

    @staticmethod
    def _decrypt(value, key):
        try:
            raw = base64.b64decode(value, validate=True)
            if len(raw) < 28:
                raise ValueError("short payload")
            cipher = AES.new(key.encode().ljust(32, b"\0")[:32], AES.MODE_GCM, nonce=raw[:12])
            return cipher.decrypt_and_verify(raw[12:-16], raw[-16:]).decode("utf-8")
        except (TypeError, ValueError) as error:
            raise _ProxyError(502, "電視端 AES-GCM 驗證失敗") from error

    def _encrypt(self, value):
        nonce = secrets.token_bytes(12)
        cipher = AES.new(self.session_key.encode().ljust(32, b"\0")[:32], AES.MODE_GCM, nonce=nonce)
        data, tag = cipher.encrypt_and_digest(value.encode())
        return base64.b64encode(nonce + data + tag).decode()

    def _bootstrap(self, deadline):
        timestamp = int(time.time() * 1000)
        day0 = ((timestamp // 1000 + 28800) // 86400) * 86400000 - 28800000
        digest = hashlib.sha256((TV_APP_ID + self.uid + str(timestamp) + str(day0)).encode()).hexdigest()
        self.fingerprint = hashlib.sha256(digest.encode()).hexdigest()
        start = self._request(TV_BASE + "api/app/start/v1/01", {"key": "app_start_d1", "value": self._common()},
                              deadline, "電視端初始化", {"UID": "", "X-Timestamp": str(timestamp)})
        data = self._data(start, "電視端初始化")
        encrypted = data.get("key") if isinstance(data, dict) else data
        self.session_key = self._decrypt(encrypted, self.fingerprint[:32])
        cipher = PKCS1_OAEP.new(RSA.import_key(base64.b64decode(TV_PUBLIC_KEY)), hashAlgo=SHA256)
        body = {"device_name": "央视频电视投屏助手",
                "device_id": base64.b64encode(cipher.encrypt(self.uid.encode())).decode()}
        cloud = self._request(TV_CLOUD + "get", body, deadline, "電視設備查詢")
        code = cloud.get("result", cloud.get("code"))
        if str(code) in ("601", "2"):
            cloud = self._request(TV_CLOUD + "register", body, deadline, "電視設備註冊")
            code = cloud.get("result", cloud.get("code"))
            if str(code) in ("0", "694", "2") and not (cloud.get("data") or {}).get("guid"):
                cloud = self._request(TV_CLOUD + "get", body, deadline, "電視設備查詢")
        data = self._data(cloud, "電視設備註冊")
        self.guid = data.get("guid") if isinstance(data, dict) else ""
        if not isinstance(self.guid, str) or not self.guid.strip():
            raise _ProxyError(502, "電視設備註冊: missing guid")
        self.created_at = time.monotonic()
        self.last_heartbeat = 0

    def heartbeat(self, deadline):
        if time.monotonic() - self.last_heartbeat < 30:
            return
        value = {**self._common(), "network_type": "WiFi", "guid": self.guid, "other": ""}
        result = self._request(TV_REPORT, {"key": "app_heartbeat", "value": value}, deadline, "電視設備心跳")
        code = result.get("result", result.get("code"))
        if code is not None and str(code) != "0":
            self.session_key = ""
            raise _ProxyError(502, "電視設備心跳: code=" + str(code))
        self.last_heartbeat = time.monotonic()

    def resolve(self, live_id, deadline):
        try:
            if not self.session_key or time.monotonic() - self.created_at >= PLAY_SESSION_SECONDS:
                self._bootstrap(deadline)
            self.heartbeat(deadline)
            body = {"screenParam": "7680-4320-280", "rate": "", "systemType": "ios",
                    "model": "XR-85Z9K", "id": live_id, "userId": "BAEBFF2B-C516-4F34-ABC0-A824A6461CBD",
                    "clientSign": "cctvVideo", "deviceId": {"serial": "", "imei": "", "android_id": ""}}
            result = self._request(TV_BASE + "api/live/v1/01", body, deadline, "電視端畫質列表")
            data = self._data(result, "電視端畫質列表")
            videos = (data.get("videoList") or data.get("videos")) if isinstance(data, dict) else None
            if not isinstance(videos, list):
                raise _ProxyError(502, "電視端畫質列表: missing videos")
            candidates = [item for item in videos if isinstance(item, dict) and isinstance(item.get("url"), str) and item["url"]]
            if not candidates:
                raise _ProxyError(502, "電視端畫質列表: no usable URL")

            video = next((item for item in candidates if item.get("rate") == "36p"), candidates[0])
            raw_url = video["url"]
            if not raw_url.startswith(("http://", "https://")):
                raw_url = self._decrypt(raw_url, self.session_key)
            result = self._request(TV_BASE + "api/live/v1/02", {"guid": self._encrypt("")}, deadline, "電視端播放授權")
            data = self._data(result, "電視端播放授權")
            secret = data.get("appSecret", data.get("app_secret")) if isinstance(data, dict) else data
            secret = self._decrypt(secret, self.session_key)
            random_value = "{}-0000-{}-0000-00000000{}".format(secrets.token_hex(4), secrets.token_hex(2), secrets.token_hex(2))
            sign = _md5(TV_APP_ID + secret + random_value)
            headers = {"APPID": TV_APP_ID, "APPSIGN": sign, "APPRANDOMSTR": random_value}
            body = {"appcommon": json.dumps({"adid": "", "av": TV_VERSION, "an": "央视频电视投屏助手", "ap": "cctv_app_tv"},
                                            ensure_ascii=False, sort_keys=True, separators=(",", ":")), "url": raw_url}
            result = self._request(TV_VDN, body, deadline, "電視端播放地址", headers, form=True)
            if str(result.get("succeed")) != "1" or not _playback_url(result.get("url")):
                raise _ProxyError(502, "電視端播放地址: no usable HLS URL")
            return {"url": result["url"], "headers": {**headers, "UID": self.profile["android_id"],
                    "Referer": "api.cctv.cn", "User-Agent": "cctv_app_tv"}, "rate": video.get("rate", "")}
        except Exception:
            self.session_key = ""
            raise


class Spider(BaseSpider):

    def init(self, extend=""):
        self.snapshot_url = extend
        self.player = None
        self._invalidate_tv_session()
        self.destroyed = False
        self.player_lock = threading.RLock()

    def liveContent(self, url):
        self._assert_active()
        channels = self._load_channels(url, self.snapshot_url)
        self._assert_active()
        groups = OrderedDict()
        for number, channel in enumerate(channels, 1):
            group = GROUP_NAMES.get(channel.get("type"), "其他頻道")
            groups.setdefault(group, []).append(self._item(channel, number))
        return [{"name": name, "channel": items} for name, items in groups.items()]

    def proxy(self, params):
        try:
            self._assert_active()
            if params.get("type") == "epg":
                content = self._epg(params.get("id", ""), params.get("date", ""))
                self._assert_active()
                return [200, "application/json", content]
            if params.get("type") == "auto":
                return self._proxy_auto(params)
            if params.get("type") in ("tv", "app", "web"):
                return self._proxy_live(params)
            refresh = "no-cache" in str(params.get("cache-control", "")).lower().replace(" ", "").split(",")
            location = self._resolve(params.get("pid", ""), params.get("cnlid", ""), refresh)
            self._assert_active()
            return [302, "text/plain", "", {"Location": location}]
        except _ProxyError as error:
            return [error.status, "text/plain; charset=utf-8", "央視頻: " + str(error)]
        except Exception as error:
            return [502, "text/plain; charset=utf-8", "央視頻: " + str(error)]

    def destroy(self):
        self.destroyed = True
        with self.player_lock:
            self.player = None
            self.tv_player = None

    def _assert_active(self):
        if self.destroyed:
            raise _ProxyError(503, "播放服務已關閉")

    def _invalidate_tv_session(self):
        self.tv_player = None
        self.tv_cache_prefix = "tvplay:" + secrets.token_hex(8) + ":"

    def _tv_entry(self, pid, cnlid, deadline, refresh=False):
        if pid not in TV_CHANNELS or not _is_channel_id(cnlid):
            raise _ProxyError(400, "invalid TV channel id")
        self._assert_active()
        key = self.tv_cache_prefix + pid
        if refresh:
            self.net.clearCache(key)
        entry = self.net.cached(key, {"ttl": PLAY_CACHE_SECONDS * 1000, "stale": False},
                                lambda: self._resolve_tv(pid, deadline))
        self._assert_active()
        return {**entry, "cache_key": key}

    def _resolve_tv(self, pid, deadline):
        if not self.player_lock.acquire(timeout=_remaining(deadline, "電視端播放取址")):
            raise _ProxyError(504, "電視端播放取址: 等待逾時")
        try:
            self._assert_active()
            if self.tv_player is None:
                self.tv_player = _TvPlayerApi(self)
            with _timing("tv_resolve"):
                entry = self.tv_player.resolve(TV_CHANNELS[pid], deadline)
            self._assert_active()
            return entry
        except Exception:
            self._invalidate_tv_session()
            raise
        finally:
            self.player_lock.release()

    def _app_entry(self, pid, cnlid, definition, deadline, refresh=False):
        if not _is_channel_id(pid) or not _is_channel_id(cnlid) or definition not in ("fhd", "shd"):
            raise _ProxyError(400, "invalid App channel id")
        self._assert_active()
        key = "appplay:" + pid + ":" + cnlid + ":" + definition
        if refresh:
            self.net.clearCache(key)

        def resolve():
            with _timing("app_resolve"):
                entry = _AppPlayerApi(self).resolve(pid, cnlid, deadline, definition)
            self._assert_active()
            return entry

        entry = self.net.cached(key, {"ttl": PLAY_CACHE_SECONDS * 1000, "stale": False}, resolve)
        self._assert_active()
        return {**entry, "cache_key": key}

    def _live_entry(self, source, params, deadline, refresh=False):
        pid, cnlid, definition = params["pid"], params["cnlid"], params.get("defn", "fhd")
        if source == "tv":
            entry = self._tv_entry(pid, cnlid, deadline, refresh)
        elif source == "app":
            entry = self._app_entry(pid, cnlid, definition, deadline, refresh)
        else:
            entry = {"url": self._resolve(pid, cnlid, refresh, deadline), "headers": _PlayerApi._headers(),
                     "cache_key": "play:" + pid + ":" + cnlid}
        generation = _md5(entry["url"] + "\n" + _canonical_query(entry["headers"]))
        return {**entry, "source": source, "pid": pid, "cnlid": cnlid, "defn": definition, "generation": generation}

    @staticmethod
    def _auto_key(params):
        return "auto:" + params["pid"] + ":" + params["cnlid"] + ":" + params.get("defn", "fhd")

    def _source_failure(self, params, source):
        return self.net.cached(self._auto_key(params) + ":" + source, {"ttl": AUTO_FAILURE_SECONDS * 1000, "stale": False}, lambda: "")

    def _entry_key(self, params):
        return self._auto_key(params) + ":entry:" + params["type"] + ":" + params["generation"]

    def _resource_entry(self, params, deadline):
        def resolve():
            entry = self._live_entry(params["type"], params, deadline)
            if entry["generation"] != params["generation"]:
                raise _ProxyError(410, "播放來源已更新，請重新播放")
            return entry

        return self.net.cached(self._entry_key(params), {"ttl": PLAY_SESSION_SECONDS * 1000, "stale": False}, resolve)

    def _fail_source(self, params, source, error, entry=None):
        self._assert_active()
        if isinstance(error, InterruptedError) or re.search(r"CancellationException|InterruptedException", str(error)):
            raise error
        if entry:
            if params.get("generation"):
                choice = self.net.cached(self._auto_key(params), {"ttl": AUTO_CHOICE_SECONDS * 1000, "stale": False},
                                         lambda: {"source": source, "generation": entry["generation"]})
                if choice != {"source": source, "generation": params["generation"]}:
                    return
            self.net.clearCache(entry["cache_key"])
        message = re.sub(r"https?://[^\s]+", "[網址]", str(error).split("\n", 1)[0])[:160] or type(error).__name__
        key = self._auto_key(params) + ":" + source
        self.net.clearCache(key)
        self.net.cached(key, {"ttl": AUTO_FAILURE_SECONDS * 1000, "stale": False}, lambda: message)
        print("央視頻 " + source + ": " + message)

    def _proxy_auto(self, params):
        self._assert_active()
        if (not _is_channel_id(params.get("pid")) or not _is_channel_id(params.get("cnlid"))
                or params.get("defn", "fhd") not in ("fhd", "shd") or params.get("url")
                or params.get("kind", "playlist") != "playlist" or params.get("generation")):
            raise _ProxyError(400, "invalid automatic playback request")
        deadline = time.monotonic() + PLAYER_BUDGET
        sources = (["tv"] if params["pid"] in TV_CHANNELS else []) + ["web", "app"]
        key = self._auto_key(params)
        choice = self.net.cached(key, {"ttl": AUTO_CHOICE_SECONDS * 1000, "stale": False},
                                 lambda: {"source": sources[0], "generation": ""})
        if choice["source"] in sources:
            sources.remove(choice["source"])
            sources.insert(0, choice["source"])
        refresh = "no-cache" in str(params.get("cache-control", "")).lower().replace(" ", "").split(",")
        errors = []
        for source in sources:
            self._assert_active()
            failure = self._source_failure(params, source)
            if failure:
                errors.append(source + ": " + failure)
                continue
            _remaining(deadline, "自動播放取址")
            attempt_deadline = min(deadline, time.monotonic() + AUTO_SOURCE_SECONDS)
            entry = None
            try:
                entry = self._live_entry(source, params, attempt_deadline, refresh)
                self._proxy_entry(entry, params, attempt_deadline, probe=True)
                self._assert_active()
                selected = {"source": source, "generation": entry["generation"]}
                if selected != choice:
                    self.net.clearCache(key)
                    self.net.cached(key, {"ttl": AUTO_CHOICE_SECONDS * 1000, "stale": False}, lambda: selected)
                target = {"type": source, "pid": entry["pid"], "cnlid": entry["cnlid"], "defn": entry["defn"], "generation": entry["generation"]}
                return [302, "text/plain", "", {"Location": self.proxyUrl(target), "Cache-Control": "no-store"}]
            except Exception as error:
                self._fail_source(params, source, error, entry)
                errors.append(source + ": " + self._source_failure(params, source))
        raise _ProxyError(502, "所有播放來源均失敗（" + "；".join(errors) + "）")

    def _proxy_live(self, params):
        pid, cnlid = params.get("pid", ""), params.get("cnlid", "")
        source = params.get("type")
        definition = params.get("defn", "fhd")
        kind = params.get("kind", "playlist")
        if source not in ("tv", "app", "web") or kind not in ("playlist", "segment"):
            raise _ProxyError(400, "invalid playback resource type")
        if params.get("url") and not _playback_url(params["url"]):
            raise _ProxyError(400, "invalid playback URL")
        deadline = time.monotonic() + PLAYER_BUDGET
        if not _is_channel_id(pid) or not _is_channel_id(cnlid) or definition not in ("fhd", "shd"):
            raise _ProxyError(400, "invalid playback channel id")
        entry = (self._resource_entry(params, deadline) if params.get("generation")
                 else self._live_entry(source, params, deadline))
        try:
            return self._proxy_entry(entry, params, deadline)
        except Exception as error:
            self._fail_source(params, source, error, entry)
            raise

    def _proxy_entry(self, entry, params, deadline, probe=False):
        source, pid, cnlid = entry["source"], entry["pid"], entry["cnlid"]
        kind = params.get("kind", "playlist")
        url = params.get("url") or entry["url"]
        if not _playback_url(url):
            raise _ProxyError(400, "invalid playback URL")
        headers = dict(entry["headers"])
        if kind == "segment":
            if params.get("range"):
                headers["Range"] = params["range"]
            milliseconds = max(1, int(_remaining(deadline, "直播切片") * 1000))
            result = self.net.stream(url, {"headers": headers, "timeout": min(PLAYER_TIMEOUT * 1000, milliseconds),
                                           "callTimeout": milliseconds})
            try:
                self._assert_active()
                if result["code"] >= 400:
                    self._fail_source(params, source, _ProxyError(result["code"], "直播切片: HTTP " + str(result["code"])), entry)
                return [result["code"], result["contentType"], result["stream"], result["headers"]]
            except Exception:
                result["stream"].close()
                raise
        if source == "tv":
            if not self.player_lock.acquire(timeout=_remaining(deadline, "電視設備心跳")):
                raise _ProxyError(504, "電視設備心跳: 等待逾時")
            try:
                if self.destroyed or self.tv_player is None:
                    raise _ProxyError(503, "播放服務已關閉")
                self.tv_player.heartbeat(deadline)
            except Exception:
                self._invalidate_tv_session()
                raise
            finally:
                self.player_lock.release()
        if "no-cache" in str(params.get("cache-control", "")).lower().replace(" ", "").split(","):
            headers["Cache-Control"] = "no-cache"
        playlist, base_url = self._fetch_playlist(url, headers, deadline)
        if probe:
            self._probe_playlist(playlist, base_url, headers, deadline)
        target = {"type": source, "pid": pid, "cnlid": cnlid, "defn": entry["defn"], "generation": entry["generation"]}
        self.net.cached(self._entry_key(target), {"ttl": PLAY_SESSION_SECONDS * 1000, "stale": False}, lambda: entry)
        content = self._rewrite_playlist(playlist, base_url, target)
        self._assert_active()
        return [200, HLS_MIME, content, {"Cache-Control": "no-store"}]

    def _probe_playlist(self, playlist, base_url, headers, deadline):
        for _ in range(3):
            variant = False
            for line in playlist.splitlines():
                line = line.strip()
                if line.startswith("#EXT-X-STREAM-INF:"):
                    variant = True
                elif line and not line.startswith("#"):
                    break
            else:
                raise _ProxyError(502, "直播 HLS: missing media URI")
            url = urljoin(base_url, line)
            if not _playback_url(url):
                raise _ProxyError(502, "直播 HLS: invalid media URL")
            if variant or urlparse(url).path.lower().endswith(".m3u8"):
                playlist, base_url = self._fetch_playlist(url, headers, deadline)
                continue
            for resource in re.findall(r'#EXT-X-(?:KEY|MAP):[^\r\n]*?URI="([^"]+)"', playlist):
                resource_url = urljoin(base_url, resource)
                if not _playback_url(resource_url):
                    raise _ProxyError(502, "直播 HLS: invalid media URL")
                self._probe_media(resource_url, headers, deadline)
            self._probe_media(url, headers, deadline)
            return
        raise _ProxyError(502, "直播 HLS: playlist nesting too deep")

    def _probe_media(self, url, headers, deadline):
        milliseconds = max(1, int(_remaining(deadline, "直播切片驗證") * 1000))
        reader = self.net.openStream(url, {"headers": headers, "timeout": milliseconds, "callTimeout": milliseconds})
        try:
            if reader.code not in (200, 206):
                raise _ProxyError(502, "直播切片驗證: HTTP " + str(reader.code))
            if str(reader.contentType).lower().startswith(("text/html", "application/json")):
                raise _ProxyError(502, "直播切片驗證: unexpected content type")
            if not reader.read(1):
                raise _ProxyError(502, "直播切片驗證: empty response")
            self._assert_active()
            _remaining(deadline, "直播切片驗證")
        finally:
            reader.close()

    def _fetch_playlist(self, url, headers, deadline):
        for _ in range(6):
            self._assert_active()
            if not _playback_url(url):
                raise _ProxyError(502, "直播 HLS: invalid redirect URL")
            result = _net_response(self.net, url, PLAYER_TIMEOUT, headers, deadline=deadline,
                                   stage="直播 HLS", redirect=0)
            self._assert_active()
            if result["code"] in (301, 302, 303, 307, 308):
                location = next((value for key, value in result.get("headers", {}).items()
                                 if key.lower() == "location"), "")
                if not location:
                    raise _ProxyError(502, "直播 HLS: missing redirect location")
                url = urljoin(url, location)
                continue
            text = result["content"]
            if result["code"] != 200 or not text.lstrip().startswith("#EXTM3U"):
                raise _ProxyError(502, "直播 HLS: invalid playlist")
            return text, url
        raise _ProxyError(502, "直播 HLS: too many redirects")

    def _rewrite_playlist(self, playlist, base_url, target):
        def proxy_url(value, kind):
            url = urljoin(base_url, value)
            if not _playback_url(url):
                raise _ProxyError(502, "直播 HLS: invalid resource URL")
            if target["type"] == "web" and kind == "segment":
                return url
            params = {**target, "kind": kind, "url": url}
            return self.proxyUrl(params)

        lines = []
        variant = False
        for line in playlist.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                kind = "playlist" if stripped.startswith(("#EXT-X-MEDIA:", "#EXT-X-I-FRAME-STREAM-INF:",
                                                           "#EXT-X-RENDITION-REPORT:")) else "segment"
                line = re.sub(r'URI="([^"]+)"', lambda match: 'URI="' + proxy_url(match.group(1), kind) + '"', line)
                if stripped.startswith("#EXT-X-STREAM-INF:"):
                    variant = True
            elif stripped:
                kind = "playlist" if variant or urlparse(stripped).path.lower().endswith(".m3u8") else "segment"
                line = proxy_url(stripped, kind)
                variant = False
            lines.append(line)
        return "\n".join(lines) + "\n"

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

    def _resolve(self, pid, cnlid, refresh=False, deadline=None):
        pid, cnlid = str(pid), str(cnlid)
        if not pid.isdigit() or not cnlid.isdigit():
            raise _ProxyError(400, "invalid channel id")
        if self.destroyed:
            raise _ProxyError(503, "播放服務已關閉")
        deadline = time.monotonic() + PLAYER_BUDGET if deadline is None else deadline
        key = "play:" + pid + ":" + cnlid
        if refresh:
            self.net.clearCache(key)
        with _timing("resolve"):
            return self.net.cached(key,
                                   {"ttl": PLAY_CACHE_SECONDS * 1000, "stale": False},
                                   lambda: self._resolve_player(pid, cnlid, deadline))

    def _resolve_player(self, pid, cnlid, deadline):
        acquired = False
        try:
            with _timing("lock_wait"):
                acquired = self.player_lock.acquire(timeout=_remaining(deadline, "播放取址"))
                if not acquired:
                    raise _ProxyError(504, "播放取址: 等待逾時")
            if self.destroyed:
                raise _ProxyError(503, "播放服務已關閉")
            if self.player is None:
                with _timing("initialize"):
                    self.player = _PlayerApi(self.net, deadline)
            location = self.player.resolve(pid, cnlid, deadline)
            self._assert_active()
            return location
        finally:
            if acquired:
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
            "referer": HOST + "/",
            "urls": [self.proxyUrl({"type": "auto", "pid": pid, "cnlid": cnlid,
                                    "defn": "shd" if channel.get("vip") else "fhd", "cmg": "1"})],
        }
        if epg_id:
            item["epg"] = self.proxyUrl({"type": "epg", "id": epg_id}) + "&date={date}"
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
