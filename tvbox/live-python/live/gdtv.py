import base64
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode, urlsplit

from base.spider import Spider as BaseSpider


HOST = "https://android.itouchtv.cn"
API_URL = "https://api.itouchtv.cn/liveservice"
CATALOG_URL = API_URL + "/v7/tvCategoryList?pageSize=100&pageNumber=1"
PLAY_URL = API_URL + "/v2/tvChannelPlayUrl"
CATEGORY_IDS = {"3041", "3043", "3044"}
NODE_HOST = "https://tcdn-api.itouchtv.cn"
NODE_URL = NODE_HOST + "/getParam"
WS_URL = "wss://tcdn-ws.itouchtv.cn:3800/connect"
API_KEY = '04039368653554864194910691389924'
# App 公開的客戶端簽名密鑰；動態簽名、節點與播放 token 不寫入檔案。
API_SECRET = b'qmiHeB9bKgowHqxRv0prc2cPN2EwXL1HOYu3DPiYCcaYxyxdFIyT5mAfBmr0UKPO'
APP_VERSION = "7.0.0"
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"
)
REQUEST_TIMEOUT = 10
PLAY_CACHE_SECONDS = 30
PLAYER_HEADERS = {"User-Agent": USER_AGENT, "Referer": HOST + "/"}
# 已確認僅顯示「請在電視端觀看」提示，依使用者要求移除。
TV_ONLY_CHANNEL_IDS = {"1198"}


class _LoginRequired(ValueError):
    pass


class Spider(BaseSpider):

    def init(self, extend=""):
        self.login_required = set()

    def liveContent(self, url):
        result = self._get(url or CATALOG_URL)
        groups = result.get("categoryTvChannelResps") if isinstance(result, dict) else None
        if not isinstance(groups, list):
            raise ValueError("廣東廣電：直播清單格式錯誤")
        categories = {}
        for group in groups:
            if not isinstance(group, dict):
                raise ValueError("廣東廣電：頻道分類格式錯誤")
            category_id = str(group.get("categoryPk"))
            if category_id not in CATEGORY_IDS:
                continue
            if category_id in categories:
                raise ValueError("廣東廣電：頻道分類重複")
            categories[category_id] = group
        if set(categories) != CATEGORY_IDS:
            raise ValueError("廣東廣電：電視頻道分類清單不完整")
        result = []
        seen = {}
        number = 0
        for group in categories.values():
            group_name = str(group.get("categoryName") or "").strip()
            rows = group.get("tvChannelEntityList")
            if not group_name or not isinstance(rows, list) or not rows:
                raise ValueError("廣東廣電：頻道分類格式錯誤")
            channels = []
            for row in rows:
                if not isinstance(row, dict) or row.get("tvType") not in (1, 2):
                    raise ValueError("廣東廣電：頻道資料格式錯誤")
                if row["tvType"] == 2:
                    continue
                channel_id = self._channel_id(str(row.get("tvChannelPk") or ""))
                name = str(row.get("channelName") or "").strip()
                if not channel_id or not name:
                    raise ValueError("廣東廣電：頻道資料格式錯誤")
                if channel_id in seen:
                    if seen[channel_id] != name:
                        raise ValueError("廣東廣電：重複頻道對應錯誤")
                    continue
                seen[channel_id] = name
                if channel_id in self.login_required or channel_id in TV_ONLY_CHANNEL_IDS:
                    continue
                number += 1
                channels.append({
                    "name": name,
                    "tvgName": name,
                    "tvgId": channel_id,
                    "number": "{:02d}".format(number),
                    "logo": str(row.get("coverUrl") or ""),
                    "urls": [self.proxyUrl({"id": channel_id})],
                    "parse": 0,
                    "format": "application/x-mpegURL",
                    "ua": USER_AGENT,
                    "referer": HOST + "/",
                })
            if channels:
                result.append({"name": group_name, "channel": channels})
        if not result:
            raise ValueError("廣東廣電：直播清單為空")
        all_channels = [channel for group in result for channel in group["channel"]]
        return [{"name": "全部頻道", "channel": all_channels}] + result

    def proxy(self, params):
        channel_id = self._channel_id(params.get("id", ""))
        if not channel_id:
            return [400, "text/plain", "廣東廣電：頻道代碼錯誤"]
        if channel_id in TV_ONLY_CHANNEL_IDS:
            return [403, "text/plain", "廣東廣電：頻道僅提供電視端觀看，已略過"]
        try:
            if channel_id in self.login_required:
                raise _LoginRequired()
            return [302, "text/plain", "", {"Location": self._play_url(channel_id)}]
        except _LoginRequired:
            self.login_required.add(channel_id)
            return [403, "text/plain", "廣東廣電：頻道需要登入，已略過"]
        except (OSError, ValueError) as error:
            return [502, "text/plain", "廣東廣電：" + str(error)]

    @staticmethod
    def _channel_id(value):
        if isinstance(value, str) and value.isascii() and value.isdigit():
            return value.lstrip("0")
        return ""

    def _get(self, url):
        result = self.net.req(url, {
            "method": "GET", "headers": self._headers(url), "timeout": REQUEST_TIMEOUT * 1000,
        })
        if result.get("error"):
            raise ValueError("網路請求失敗：" + str(result["error"]))
        code = result.get("code") or 0
        try:
            data = json.loads(result.get("content"))
        except (TypeError, ValueError):
            if not 200 <= code < 300:
                raise ValueError("HTTP " + str(code)) from None
            raise ValueError("廣東廣電：回應不是有效 JSON") from None
        if isinstance(data, dict) and str(data.get("errorCode")) == "403001":
            raise _LoginRequired()
        if not 200 <= code < 300:
            raise ValueError("HTTP " + str(code))
        return data

    def _play_url(self, channel_id):
        return self.net.cached("play:" + channel_id, {"ttl": PLAY_CACHE_SECONDS * 1000, "stale": False},
                               lambda: self._resolve(channel_id))

    def _resolve(self, channel_id):
        result = self._get(NODE_URL)
        node = result.get("node") if isinstance(result, dict) else None
        if not isinstance(node, str) or not node:
            raise ValueError("直播參數格式錯誤")
        if node.endswith("-1"):
            node = self._ws_node(node)
        url = PLAY_URL + "?" + urlencode({"channelId": channel_id, "node": node})
        result = self._get(url)
        stream = result.get("videoUrl") if isinstance(result, dict) else None
        parsed = urlsplit(stream) if isinstance(stream, str) else None
        if parsed is None or parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("播放地址為空或格式錯誤")
        return stream

    def _ws_node(self, node):
        response = self.net.ws(WS_URL, {
            "headers": self._headers(NODE_HOST),
            "data": {"route": "getwsparam", "message": node},
            "timeout": REQUEST_TIMEOUT * 1000,
        })
        if response.get("error"):
            raise ValueError("網路請求失敗：" + str(response["error"]))
        if response.get("code") != 101:
            raise ValueError("HTTP " + str(response.get("code") or "無回應"))
        result = json.loads(response["content"])
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
            "X-ITOUCHTV-CLIENT": "NEWS_APP",
            "X-ITOUCHTV-APP-VERSION": APP_VERSION,
        }
