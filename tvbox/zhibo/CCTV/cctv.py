import base64
import hashlib
import json
import re
import secrets
import time
from urllib.parse import quote, unquote, urljoin, urlparse

import requests
from lxml import html
from base.spider import Spider as BaseSpider


HOST = "https://tv.cctv.com"
CATALOG_URL = HOST + "/live/"
PLAY_URL = "https://vdnx.live.cntv.cn/api/v3/vdn/live"
PLAY_SECRET = "a4220a71b31746908fa3e7fdd7a6852a"
HLS_MIME = "application/x-mpegURL"
REQUEST_TIMEOUT = 8
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
MIN_CHANNELS = 18


class Spider(BaseSpider):

    def init(self, extend=""):
        self.snapshot_url = extend
        self.uid = base64.b64encode(secrets.token_bytes(18)).decode("ascii")

    def getName(self):
        return "央視網"

    def liveContent(self, url):
        channels = self._load_channels(url, self.snapshot_url)
        proxy = self.getProxyUrl() + "&siteKey=" + quote(str(self.siteKey), safe="")
        items = [
            self._item(channel, number, proxy)
            for number, channel in enumerate(channels, 1)
        ]
        return json.dumps([{"name": "央視頻道", "channel": items}], ensure_ascii=False)

    def localProxy(self, param):
        try:
            location = self._resolve(param.get("id", ""))
            return [302, "text/plain", "", {"Location": location}]
        except Exception as error:
            return [502, "text/plain", "央視網: " + str(error)]

    def destroy(self):
        self.uid = ""

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
        with requests.get(
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
            timeout=REQUEST_TIMEOUT,
        ) as response:
            response.raise_for_status()
            result = response.json()
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
        except (requests.RequestException, ValueError) as error:
            print("央視網 catalog fallback: {}".format(error))
            return self._load_snapshot(snapshot_url)

    @classmethod
    def _fetch_channels(cls, url):
        with requests.get(
            url,
            headers={"Referer": HOST + "/", "User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        ) as response:
            response.raise_for_status()
            document = html.fromstring(response.content)
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

    @staticmethod
    def _load_snapshot(url):
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            with requests.get(url, timeout=REQUEST_TIMEOUT) as response:
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
        channel_id = str(channel["id"])
        name = str(channel["name"])
        return {
            "name": name,
            "tvgName": name,
            "tvgId": channel_id,
            "number": str(number),
            "format": HLS_MIME,
            "ua": USER_AGENT,
            "urls": [proxy + "&id=" + quote(channel_id, safe="")],
        }
