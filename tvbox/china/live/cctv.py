import base64
import datetime
import hashlib
import json
import re
import secrets
import time
from urllib.parse import quote, unquote, urljoin, urlparse

from lxml import html
from base.spider import Spider as BaseSpider


HOST = "https://tv.cctv.com"
CATALOG_URL = HOST + "/live/"
EPG_URL = "https://api.cntv.cn/epg/getEpgInfoByChannelNew"
PLAY_URL = "https://vdnx.live.cntv.cn/api/v3/vdn/live"
PLAY_SECRET = "a4220a71b31746908fa3e7fdd7a6852a"
HLS_MIME = "application/x-mpegURL"
REQUEST_TIMEOUT = 8
EPG_CACHE_SECONDS = 60 * 60
TAIPEI = datetime.timezone(datetime.timedelta(hours=8))
LOGO_URL = "https://epg.112114.xyz/logo/{}.png"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)
CHANNEL_PATTERN = re.compile(
    r"^https?://tv\.cctv\.com/live/"
    r"(cctv(?:\d+|5plus|jilu|child|europe|america))/",
    re.IGNORECASE,
)
CHANNEL_ID_PATTERN = re.compile(
    r"^cctv(?:\d+|5plus|jilu|child|europe|america)$",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MIN_CHANNELS = 18
LOGO_NAMES = {
    "cctv5plus": "CCTV5+",
    "cctvjilu": "CCTV9",
    "cctvchild": "CCTV14",
    "cctveurope": "CCTV4欧洲",
    "cctvamerica": "CCTV4美洲",
}


class Spider(BaseSpider):

    def init(self, extend=""):
        self.snapshot_url = extend
        self.uid = base64.b64encode(secrets.token_bytes(18)).decode("ascii")

    def getName(self):
        return "央視網"

    def liveContent(self, url):
        channels = self._load_channels(url, self.snapshot_url)
        items = [
            self._item(channel, number)
            for number, channel in enumerate(channels, 1)
        ]
        return [{"name": "央視頻道", "channel": items}]

    def localProxy(self, param):
        try:
            if param.get("type") == "epg":
                content = self._epg(param.get("id", ""), param.get("date", ""))
                return [200, "application/json", content]
            location = self._resolve(param.get("id", ""))
            return [302, "text/plain", "", {"Location": location}]
        except Exception as error:
            return [502, "text/plain", "央視網: " + str(error)]

    def destroy(self):
        self.uid = ""

    def _epg(self, channel_id, date):
        if not isinstance(channel_id, str) or not CHANNEL_ID_PATTERN.fullmatch(
            channel_id
        ):
            raise ValueError("invalid channel id")
        if not isinstance(date, str) or not DATE_PATTERN.fullmatch(date):
            raise ValueError("invalid date")
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
            headers={"Referer": HOST + "/", "User-Agent": USER_AGENT},
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
                start = self._clock(row.get("startTime"))
                end = self._clock(row.get("endTime"))
            except (TypeError, ValueError, OverflowError):
                continue
            items.append({"title": title, "start": start, "end": end})
        content = json.dumps(
            {"date": date, "epg_data": items},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return content

    @staticmethod
    def _clock(value):
        return datetime.datetime.fromtimestamp(int(value), TAIPEI).strftime("%H:%M:%S")

    def _resolve(self, channel_id):
        if not isinstance(channel_id, str) or not CHANNEL_ID_PATTERN.fullmatch(
            channel_id
        ):
            raise ValueError("invalid channel id")
        timestamp = int(time.time() * 1000)
        nonce = secrets.randbelow(901) + 100
        digest = hashlib.md5(
            "{}{}{}{}".format(channel_id, timestamp, nonce, PLAY_SECRET).encode("utf-8")
        ).hexdigest()
        auth_key = "{}-{}-{}".format(timestamp, nonce, digest)
        result = self._get_json(
            PLAY_URL,
            params={
                "channel": channel_id,
                "vn": "1",
                "pdrm": "1",
                "uid": self.uid,
                "hbss": str(timestamp),
            },
            headers={
                "auth-key": auth_key,
                "Origin": HOST,
                "Referer": HOST + "/",
                "User-Agent": USER_AGENT,
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        if result.get("ack") != "yes":
            raise ValueError("play api rejected channel")
        manifest = result.get("manifest") or {}
        backup = result.get("backup") or {}
        location = manifest.get("hls_cdrm") or backup.get("hls_cdrm")
        if not isinstance(location, str) or not location.startswith(
            ("http://", "https://")
        ):
            raise ValueError("missing hls manifest")
        return location

    def _load_channels(self, url, snapshot_url):
        try:
            return self._fetch_channels(url or CATALOG_URL)
        except (OSError, ValueError) as error:
            print("央視網 catalog fallback: {}".format(error))
            return self._load_snapshot(snapshot_url)

    def _fetch_channels(self, url):
        headers = {"Referer": HOST + "/", "User-Agent": USER_AGENT}
        payload = self._request(url, headers=headers, buffer=3)
        document = html.fromstring(payload)
        channels = []
        seen = set()
        for anchor in document.xpath("//a[@href]"):
            match = CHANNEL_PATTERN.match(urljoin(url, anchor.get("href", "")))
            if not match:
                continue
            channel_id = match.group(1).lower()
            if channel_id in seen:
                continue
            name = " ".join(anchor.text_content().split())
            if not name:
                continue
            seen.add(channel_id)
            channels.append({"id": channel_id, "name": name})
        if len(channels) < MIN_CHANNELS:
            raise ValueError("incomplete channel list")
        return channels

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

    def _get_json(self, url, params=None, headers=None):
        options = {"headers": headers or {}, "timeout": REQUEST_TIMEOUT * 1000}
        if params:
            options["params"] = params
        try:
            return self.net.json(url, options)
        except Exception as error:
            raise ValueError(str(error)) from None

    def _request(self, url, params=None, headers=None, buffer=0):
        options = {
            "headers": headers or {},
            "timeout": REQUEST_TIMEOUT * 1000,
            "buffer": buffer,
        }
        if params:
            options["params"] = params
        result = self.net.req(url, options)
        if result.get("error"):
            raise OSError(str(result["error"]))
        if result["code"] >= 400:
            raise ValueError("HTTP " + str(result["code"]))
        return result["content"]

    def _item(self, channel, number):
        channel_id = str(channel["id"])
        name = str(channel["name"])
        logo_name = LOGO_NAMES.get(channel_id, channel_id.upper())
        return {
            "name": name,
            "tvgName": name,
            "tvgId": channel_id,
            "epg": self.getProxyUrl({"type": "epg", "id": channel_id}) + "&date={date}",
            "number": "{:02d}".format(number),
            "logo": LOGO_URL.format(quote(logo_name, safe="")),
            "format": HLS_MIME,
            "ua": USER_AGENT,
            "urls": [self.getProxyUrl({"id": channel_id})],
        }
