import base64
import hashlib
import hmac
import json
import time
import uuid
from urllib.parse import urlsplit

from base.spider import Spider as BaseSpider


HOST = "https://www.gdtv.cn"
API_URL = "https://gdtv-api.gdtv.cn/api/tv/v2/tvChannel"
CATALOG_URL = API_URL + "?category=0"
NODE_URL = "https://tcdn-api.itouchtv.cn/getParam"
WS_URL = "wss://tcdn-ws.itouchtv.cn:3800/connect"
API_KEY = "89541943007407288657755311868534"
# 官網公開的客戶端簽名密鑰；每次請求重新簽名，動態簽名與播放 token 不寫入檔案。
API_SECRET = b"dfkcY1c3sfuw1Cii9DWj8UO3iQy2hqlDxyvDXd1oVMxwYVDSgeB6phO9eW1dfuwX"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 10
PLAY_CACHE_SECONDS = 30
PLAYER_HEADERS = {"User-Agent": USER_AGENT, "Referer": HOST + "/", "Origin": HOST}
PREFLIGHT_HEADERS = {
    **PLAYER_HEADERS,
    "Access-Control-Request-Method": "GET",
    "Access-Control-Request-Headers": (
        "x-itouchtv-ca-key,x-itouchtv-ca-signature,x-itouchtv-ca-timestamp,"
        "x-itouchtv-client,x-itouchtv-device-id"
    ),
}


class Spider(BaseSpider):

    def init(self, extend=""):
        self.device_id = "WEB_" + str(uuid.uuid4())

    def getName(self):
        return "廣東廣電"

    def liveContent(self, url):
        # 清單 API 的 playUrl 不可直接播放；選台時才取得動態地址。
        url = url or CATALOG_URL
        rows = self._get(url)
        if not isinstance(rows, list):
            raise ValueError("廣東廣電：直播清單格式錯誤")
        channels = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            channel_id = self._channel_id(str(row.get("pk") or ""))
            name = str(row.get("name") or "").strip()
            if not channel_id or not name or channel_id in seen:
                continue
            seen.add(channel_id)
            channels.append({
                "name": name,
                "tvgName": name,
                "tvgId": channel_id,
                "number": "{:02d}".format(len(channels) + 1),
                "logo": str(row.get("avatarUrl") or ""),
                "urls": [self.getProxyUrl({"id": channel_id})],
                "parse": 0,
                "format": "application/x-mpegURL",
                "ua": USER_AGENT,
                "referer": HOST + "/",
                "origin": HOST,
            })
        if not channels:
            raise ValueError("廣東廣電：直播清單為空")
        return [{"name": "廣東頻道", "channel": channels}]

    def localProxy(self, param):
        channel_id = self._channel_id(param.get("id", ""))
        if not channel_id:
            return [400, "text/plain", "廣東廣電：頻道代碼錯誤"]
        try:
            return [302, "text/plain", "", {"Location": self._play_url(channel_id)}]
        except (OSError, ValueError) as error:
            return [502, "text/plain", "廣東廣電：" + str(error)]

    @staticmethod
    def _channel_id(value):
        if isinstance(value, str) and value.isascii() and value.isdigit():
            return value.lstrip("0")
        return ""

    def _get(self, url):
        try:
            return self.net.json(url, {
                "method": "GET", "headers": self._headers(url), "timeout": REQUEST_TIMEOUT * 1000,
            })
        except Exception as error:
            raise ValueError("網路請求失敗：" + str(error)) from None

    def _request(self, url, headers, method="GET"):
        result = self.net.req(url, {
            "method": method, "headers": headers, "timeout": REQUEST_TIMEOUT * 1000,
        })
        return self._content(result, range(200, 300))

    @staticmethod
    def _content(result, codes):
        if result.get("error"):
            raise ValueError("網路請求失敗：" + str(result["error"]))
        if result.get("code") not in codes:
            raise ValueError("HTTP " + str(result.get("code") or "無回應"))
        return result["content"]

    def _play_url(self, channel_id):
        return self.net.cached("play:" + channel_id, {"ttl": PLAY_CACHE_SECONDS * 1000, "stale": False},
                               lambda: self._resolve(channel_id))

    def destroy(self):
        pass

    def _resolve(self, channel_id):
        # App 的 net 重用預檢與 GET 的連線，Cookie 預設不啟用。
        result = self._get(NODE_URL)
        node = result.get("node") if isinstance(result, dict) else None
        if not isinstance(node, str) or not node:
            raise ValueError("直播參數格式錯誤")
        if node.endswith("-1"):
            node = self._ws_node(node)
        encoded = base64.b64encode(node.encode("utf-8")).decode("ascii")
        # 官網使用原始 base64 查詢值；簽名與實際送出的網址必須一致。
        url = API_URL + "/" + channel_id + "?tvChannelPk=" + channel_id + "&node=" + encoded
        # 官網先送 CORS 預檢；直接 GET 雖回 200，卻會得到無效的播放 token。
        self._request(url, PREFLIGHT_HEADERS, "OPTIONS")
        result = self._get(url)
        play_url = result.get("playUrl") if isinstance(result, dict) else None
        if not isinstance(play_url, str):
            raise ValueError("播放資料格式錯誤")
        streams = json.loads(play_url)
        stream = streams.get("hd") if isinstance(streams, dict) else None
        parsed = urlsplit(stream) if isinstance(stream, str) else None
        if parsed is None or parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("播放地址為空或格式錯誤")
        return stream

    def _ws_node(self, node):
        response = self.net.ws(WS_URL, {
            "headers": PLAYER_HEADERS,
            "data": {"route": "getwsparam", "message": node},
            "timeout": REQUEST_TIMEOUT * 1000,
        })
        result = json.loads(self._content(response, (101,)))
        wsnode = result.get("wsnode") if isinstance(result, dict) else None
        if (not isinstance(result, dict) or result.get("status") != 201
                or not isinstance(wsnode, str) or not wsnode):
            raise ValueError("直播參數回應錯誤")
        return wsnode

    def _headers(self, url):
        timestamp = str(int(time.time() * 1000))
        message = "GET\n" + url + "\n" + timestamp + "\n"
        signature = base64.b64encode(
            hmac.new(API_SECRET, message.encode("utf-8"), hashlib.sha256).digest()
        ).decode("ascii")
        return {
            **PLAYER_HEADERS,
            "X-ITOUCHTV-Ca-Key": API_KEY,
            "X-ITOUCHTV-Ca-Signature": signature,
            "X-ITOUCHTV-Ca-Timestamp": timestamp,
            "X-ITOUCHTV-CLIENT": "WEB_PC",
            "X-ITOUCHTV-DEVICE-ID": self.device_id,
        }
