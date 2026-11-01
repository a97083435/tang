"""斗魚／虎牙／YY 直播；斗魚官網簽名需安裝配套 QuickJS 模組。"""

import base64
import hashlib
import json
import math
import re
import time
import uuid
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit

from lxml import etree

from base.spider import Spider as BaseSpider

DOUYU = "https://www.douyu.com"
HUYA = "https://www.huya.com"
YY = "https://www.yy.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
NAMES = {"douyu": "斗魚", "huya": "虎牙", "yy": "YY"}
STYLE = {"type": "rect", "ratio": 1.78}
MAX_SAFE_INTEGER = 9007199254740991
HUYA_GROUPS = [
    {"id": "ol", "name": "網遊競技", "game": "100023"},
    {"id": "pc", "name": "單機熱遊", "game": "100002"},
    {"id": "yl", "name": "娛樂天地", "game": "100022"},
    {"id": "sy", "name": "手遊休閒", "game": "100004"},
]


def _now():
    return time.time_ns() // 1000000


def _headers(platform):
    return {"User-Agent": UA, "Referer": {"douyu": DOUYU, "huya": HUYA, "yy": YY}[platform] + "/"}


def _douyu_success(code):
    return not isinstance(code, bool) and code in (0, "0")


def _page_number(value):
    if isinstance(value, str):
        if not re.fullmatch(r"-?[0-9]+", value):
            raise ValueError("頁碼格式錯誤")
        digits = value.removeprefix("-").lstrip("0") or "0"
        if len(digits) > 16:
            raise ValueError("頁碼格式錯誤")
        value = int(digits) * (-1 if value.startswith("-") else 1)
    if type(value) not in (int, float) or not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER or value != int(value):
        raise ValueError("頁碼格式錯誤")
    return max(1, int(value))


def _room_id(value):
    match = re.fullmatch(r"(douyu|huya|yy):([A-Za-z0-9_-]{1,64})", str(value))
    if not match or match[1] == "yy" and not re.fullmatch(r"[0-9]+(?:_[0-9]+)?", match[2]):
        raise ValueError("直播房間編號格式錯誤")
    return {"platform": match[1], "id": match[2]}


def _image(value):
    if not isinstance(value, str):
        return ""
    return "https:" + value if value.startswith("//") else value


def _card(platform, id, name, pic, remark):
    if not id or not name:
        raise ValueError("直播列表缺少房間編號或名稱")
    return {
        "vod_id": f"{platform}:{id}", "vod_name": str(name), "vod_pic": _image(pic), "vod_remarks": remark or "",
        "style": dict(STYLE)
    }


def _md5(value):
    return hashlib.md5(value.encode()).hexdigest()


def _yy_card(item):
    sid = str(item.get("sid", ""))
    ssid = str(item["ssid"]) if item.get("ssid") is not None else None
    if not re.fullmatch(r"[0-9]+", sid) or ssid is not None and not re.fullmatch(r"[0-9]+", ssid):
        raise ValueError("YY 房間編號無效")
    remark = (item.get("name") or "") + (" · 未開播" if str(item.get("liveOn")) == "0" else "")
    return _card("yy", f"{sid}_{ssid}" if ssid is not None else sid, item.get("desc") or item.get("name"),
                 item.get("thumb2") or item.get("thumb") or item.get("headurl") or item.get("avatar"), remark)


def _yy_stream_url(result):
    code = result.get("result", 0)
    if type(code) not in (int, float) or code != 0:
        raise ValueError("YY 播放接口回應錯誤")
    streams = (result.get("channel_stream_info") or {}).get("streams")
    addresses = (result.get("avp_info_res") or {}).get("stream_line_addr") or {}
    if not isinstance(streams, list) or not isinstance(addresses, dict):
        raise ValueError("YY 缺少播放線路資料")
    for stream in streams:
        if stream.get("type") != 2:
            continue
        info = json.loads(stream["json"])
        cdn = info.get("is_cdn")
        if type(cdn) not in (int, float) or cdn != 1 or info.get("encoderType") != 100:
            continue
        line = addresses.get(f"{stream['appidstr']}_{stream['stream_name']}") or {}
        url = (line.get("cdn_info") or {}).get("url")
        if isinstance(url, str) and re.match(r"https?://", url):
            return url
    raise ValueError("YY 目前沒有可播放的直播線路")


def _huya_url(stream):
    params = dict(parse_qsl(stream["sFlvAntiCode"], keep_blank_values=True))
    template = base64.b64decode(params.get("fm", "")).decode()
    if "$0_$1_$2_$3" not in template:
        raise ValueError("虎牙播放簽名格式已改變")
    stamp = _now()
    seqid = str(stamp)
    digest = _md5(f"{seqid}|{params.get('ctype')}|{params.get('t')}")
    secret = template.replace("$0", "0").replace("$1", stream["sStreamName"]).replace("$2", digest).replace(
        "$3", params.get("wsTime", ""))
    params.pop("fm", None)
    params.update(wsSecret=_md5(secret), u="0", seqid=seqid, ver="1", uuid=str(stamp % 4294967295), sdk_sid=str(stamp))
    return f"{stream['sFlvUrl']}/{stream['sStreamName']}.{stream['sFlvUrlSuffix']}?{urlencode(params)}"


class Spider(BaseSpider):

    def getDependence(self):
        return ["game_live_protocol", "game_live_stream", "game_live_yy"]

    def init(self, extend=""):
        self._stop_danmaku = None
        self.device_id = uuid.uuid4().hex
        self.protocol = self.loadModule("game_live_protocol")
        self.stream = self.loadModule("game_live_stream")
        self.yy_stream = self.loadModule("game_live_yy")

    def homeContent(self, filter):
        result = {"class": [{"type_id": id, "type_name": name, "land": 1, "ratio": 1.78} for id, name in NAMES.items()]}
        if filter:
            rows = self.net.map(list(NAMES), lambda id, index: (id, self._filters(id)))
            result["filters"] = dict(rows)
        return result

    def _filters(self, platform):
        items = self._groups(platform)
        return [
            {
                "key": "view", "name": "顯示", "init": "live",
                "value": [{"n": "直播", "v": "live"}, {"n": "分類", "v": "games"}]
            },
            {
                "key": "group", "name": "分區",
                "value": [{"n": "全部", "v": ""}] + [{"n": item["name"], "v": item["id"]} for item in items]
            },
        ]

    def _douyu(self, url, options=None):
        options = dict(options or {})
        options["headers"] = {**_headers("douyu"), **options.get("headers", {})}
        result = self.net.json(url, options)
        code = result.get("error") if result.get("error") is not None else result.get("code")
        if not _douyu_success(code):
            raise ValueError("斗魚：" + str(result.get("msg") or "接口回應錯誤"))
        if result.get("data") is None:
            raise ValueError("斗魚接口缺少資料")
        return result["data"]

    def _huya_room(self, id):

        def load():
            result = self.net.json(
                "https://mp.huya.com/cache.php",
                {"params": {"m": "Live", "do": "profileRoom", "roomid": id}, "headers": _headers("huya")})
            if result.get("status") != 200 or not isinstance((result.get("data") or {}).get("profileInfo"), dict):
                raise ValueError("虎牙：" + str(result.get("message") or "房間不存在"))
            return result["data"]

        return self.net.cached(f"room:huya:{id}", {"ttl": 5000, "stale": False}, load)

    def _groups(self, platform):
        if platform == "huya":
            return HUYA_GROUPS
        if platform == "yy":
            return self.net.cached("groups:yy", {"ttl": 86400000, "persist": True}, self._yy_groups)

        def load():
            items = self._douyu(DOUYU + "/japi/weblist/api/getC1List")
            if not isinstance(items, list) or not items:
                raise ValueError("斗魚主分類格式錯誤")
            return [{"id": str(item["cid1"]), "name": item["cname1"]} for item in items]

        return self.net.cached("groups:douyu", {"ttl": 86400000, "persist": True}, load)

    def _yy_groups(self):
        data = self.net.json(YY + "/yyweb/module/data/header", {"headers": _headers("yy")})
        if not isinstance(data.get("categoryTabs"), list) or any(
                not isinstance(group.get("navs"), list) for group in data["categoryTabs"]):
            raise ValueError("YY 分類格式錯誤")
        items = [item for group in data["categoryTabs"] for item in group["navs"]]
        if not items or any(type(item.get("id")) is not int or not item.get("title") or not isinstance(
                item.get("url"), str) or not re.match(r"https?://www\.yy\.com/", item["url"]) for item in items):
            raise ValueError("YY 直播分類資料無效")
        return [{"id": str(item["id"]), "game": str(item["id"]), "name": item["title"],
                 "url": item["url"].replace("http://", "https://", 1)} for item in items]

    def _yy_directory(self, game):
        if game == "0":
            return {"moduleId": -1, "biz": "index", "subBiz": "idx"}

        def load():
            item = next((item for item in self._groups("yy") if item["id"] == game), None)
            if item is None:
                raise ValueError("未知 YY 直播分類")
            response = self.net.req(item["url"], {"headers": _headers("yy")})
            if response.get("error") or response["code"] != 200:
                raise ValueError("YY 分類載入失敗：" + str(response.get("error") or response["code"]))
            match = re.search(r"\bpageBar\s*:\s*\{([^}]+)\}", response["content"])
            if not match:
                raise ValueError("YY 分類缺少分頁資料")
            source = match[1]
            module = re.search(r"\bmoduleId\s*:\s*([0-9]+)", source)
            count = re.search(r"\btotalCount\s*:\s*([0-9]+)", source)
            biz = re.search(r"\bbiz\s*:\s*['\"]([^'\"]+)['\"]", source)
            sub = re.search(r"\bsubBiz\s*:\s*['\"]([^'\"]+)['\"]", source)
            if not all((module, count, biz, sub)):
                raise ValueError("YY 分類分頁格式錯誤")
            if module[1] == "0" and count[1] == "0":
                return {"empty": True}
            if module[1] == "0" or biz[1] == "null" or sub[1] == "null":
                raise ValueError("YY 分類分頁資料無效")
            return {"moduleId": int(module[1]), "biz": biz[1], "subBiz": sub[1]}

        return self.net.cached(f"directory:yy:{game}", {"ttl": 20000, "stale": False}, load)

    def _yy_rooms(self, game, current):
        directory = self._yy_directory(game)
        if directory.get("empty"):
            return self.page([], current, 60)
        result = self.net.json(YY + "/more/page.action", {
            "params": {**directory, "page": current, "pageSize": 60}, "headers": _headers("yy")
        })
        data = result.get("data") or {}
        total = data.get("totalCount")
        if type(result.get("resultCode")) is not int or result["resultCode"] != 0 or type(total) is not int or total < 0:
            raise ValueError("YY 直播列表格式錯誤")
        pages = max(1, (total + 59) // 60)
        items = data.get("data")
        if items is None and (total == 0 or current > pages):
            items = []
        if not isinstance(items, list):
            raise ValueError("YY 直播列表缺少房間資料")
        return self.page([_yy_card(item) for item in items] if current <= pages else [], current, 60, total)

    def _yy_search(self, keyword, current):
        result = self.net.json(YY + "/apiSearch/doSearch.json", {
            "params": {"q": keyword, "t": 1, "n": current, "s": 15}, "headers": _headers("yy")
        })
        data = result.get("data") or {}
        found = (data.get("searchResult") or {}).get("response", {}).get("1") or {}
        pages, total = data.get("totalPage"), found.get("numFound")
        if result.get("success") is not True or type(result.get("status")) is not int or result["status"] != 0 or not (
                isinstance(found.get("docs"), list) and type(pages) is int and pages >= 0 and type(total) is int and total >= 0):
            raise ValueError("YY 搜尋回應格式錯誤")
        return {"list": [_yy_card(item) for item in found["docs"]] if current <= pages else [],
                "page": current, "pagecount": max(1, pages), "limit": 15, "total": total}

    def _yy_room(self, id):

        def load():
            parts = id.split("_")
            if len(parts) == 1:
                response = self.net.req(YY + "/" + id, {"headers": _headers("yy")})
                if response.get("error") or response["code"] != 200:
                    raise ValueError("YY 房間載入失敗：" + str(response.get("error") or response["code"]))
                info = re.search(r"\bvar\s+pageInfo\s*=\s*\{([\s\S]*?)\n\s*\};", response["content"])
                sid = re.search(r"\bsid\s*:\s*['\"]([0-9]+)['\"]", info[1]) if info else None
                ssid = re.search(r"\bssid\s*:\s*['\"]([0-9]+)['\"]", info[1]) if info else None
                if not sid or not ssid:
                    raise ValueError("YY 房間不存在或缺少頻道資料")
                parts = [sid[1], ssid[1]]
            result = self.net.json(YY + f"/api/liveInfoDetail/{parts[0]}/{parts[1]}/0", {"headers": _headers("yy")})
            if type(result.get("resultCode")) not in (int, float) or result["resultCode"] != 0:
                raise ValueError("YY 房間接口回應錯誤")
            data = result.get("data")
            if not isinstance(data, dict) or not data.get("sid") or not data.get("ssid") or not data.get("name"):
                raise ValueError("YY 目前未開播或房間不存在")
            _yy_card(data)
            return data

        return self.net.cached(f"room:yy:{id}", {"ttl": 5000, "stale": False}, load)

    def _games(self, platform, group=""):
        if platform == "yy":
            return [item for item in self._groups(platform) if not group or item["id"] == group]

        def load():
            if platform == "douyu":
                items = self._douyu(DOUYU + "/api/v1/getColumnDetail")
                if not isinstance(items, list):
                    raise ValueError("斗魚分類格式錯誤")
                return [{
                    "id": str(item["tag_id"]), "group": str(item["cate_id"]), "name": item["tag_name"],
                    "pic": item.get("pic_url") or item.get("pic_name")
                } for item in items if item.get("is_del") == "0" and item.get("is_hidden") == "0"]
            response = self.net.req(HUYA + ("/g_" + group if group else "/g"), {"headers": _headers(platform)})
            if response.get("error") or response["code"] != 200:
                raise ValueError("虎牙分類載入失敗：" + str(response.get("error") or response["code"]))
            items = etree.HTML(response["content"]).xpath(
                "//li[contains(concat(' ', normalize-space(@class), ' '), ' g-gameCard-item ')][@data-gid]")
            if not items:
                raise ValueError("虎牙分類頁沒有取得資料")
            result = []
            for item in items:
                images = item.xpath(".//img")
                pic = images[0].get("data-original") or images[0].get("src") if images else ""
                result.append({"id": item.get("data-gid"), "name": item.get("title", ""), "pic": pic})
            return result

        items = self.net.cached(f"catalog:{platform}:{group if platform == 'huya' else ''}",
                                {"ttl": 86400000, "persist": True}, load)
        return [item for item in items if item["group"] == group] if platform == "douyu" and group else items

    def categoryContent(self, tid, pg, filter, extend):
        path, separator, origin = str(tid).partition("?")
        parts = path.split("/")
        platform, kind, value = (parts + ["", ""])[:3]
        if platform not in NAMES:
            raise ValueError("未知直播平台")
        current = _page_number(pg)
        if kind == "s":
            return self._search_rooms(platform, unquote(value), current)
        extend = extend or {}
        context = {"view": extend.get("view") or "live", "group": extend.get("group") or ""}
        if separator:
            previous = dict(parse_qsl(origin, keep_blank_values=True, strict_parsing=True))
            if previous.keys() != context.keys():
                raise ValueError("分類條件格式錯誤")
            if previous != context:
                kind, value = "", ""
        group = "" if kind == "g" else extend.get("group") or (value if kind == "p" else "")
        parent = next((item for item in self._groups(platform) if item["id"] == group), None) if group else None
        if group and parent is None:
            raise ValueError("未知直播分區")
        if kind != "g" and (extend.get("view") == "games" or kind == "p" and not extend.get("view")):
            result = self.page(self._games(platform, group) if group else self._groups(platform), current, 60)
            query = urlencode(context)
            result["list"] = [{
                "vod_id": f"{platform}/{'g' if group or platform == 'yy' else 'p'}/{item['id']}?{query}", "vod_name": item["name"],
                "vod_pic": _image(item.get("pic")), "vod_tag": "folder",
                "style": dict(STYLE) if group else {"type": "list"}
            } for item in result["list"]]
            return result
        game = value if kind == "g" else (parent or {}).get("game", "0")
        if not re.fullmatch(r"[0-9]+", game):
            raise ValueError("分類編號格式錯誤")
        directory = game
        if platform == "douyu":
            directory = "2_" + game if kind == "g" else "1_" + group if group else "0_0"
        return self.net.cached(f"list:{platform}:{directory}:{current}", {"ttl": 20000, "stale": False},
                               lambda: self._rooms(platform, directory, current))

    def _rooms(self, platform, game, current):
        if platform == "yy":
            return self._yy_rooms(game, current)
        if platform == "douyu":
            data = self._douyu(f"{DOUYU}/gapi/rkc/directory/mixList/{game}/{current}")
            if not isinstance(data.get("rl"), list) or type(data.get("pgcnt")) is not int:
                raise ValueError("斗魚直播列表格式錯誤")
            return {
                "list": [
                    _card(platform, item["rid"], item["rn"],
                          item.get("rs16") or item.get("rs1"), item.get("nn")) for item in data["rl"]
                ],
                "page": current, "pagecount": max(1, data["pgcnt"]), "limit": 120
            }
        result = self.net.json(
            HUYA + "/cache.php", {
                "params": {"m": "LiveList", "do": "getLiveListByPage", "gameId": game, "tagAll": 0, "page": current},
                "headers": _headers("huya")
            })
        data = result.get("data") or {}
        if result.get("status") != 200 or not isinstance(data.get("datas"), list) or type(
                data.get("totalPage")) is not int:
            raise ValueError("虎牙直播列表格式錯誤")
        return {
            "list": [
                _card(platform, item["profileRoom"],
                      item.get("introduction") or item.get("roomName") or item["nick"], item.get("screenshot"),
                      item["nick"]) for item in data["datas"]
            ],
            "page": current, "pagecount": max(1, data["totalPage"]),
            "limit": data["pageSize"], "total": data["totalCount"]
        }

    def searchContent(self, key, quick, pg="1"):
        current = _page_number(pg)
        keyword = str(key).strip()
        return self.page([{
            "vod_id": f"{platform}/s/{quote(keyword, safe='')}", "vod_name": f"{name}：{keyword}",
            "vod_remarks": "搜尋主播或房間編號", "vod_tag": "folder", "style": {"type": "list"}
        } for platform, name in NAMES.items()], current, len(NAMES))

    def _search_rooms(self, platform, keyword, current):
        if re.fullmatch(r"[0-9]+", keyword):
            if current != 1:
                return {"list": [], "page": current, "pagecount": 1, "limit": 1}
            result = self.detailContent([f"{platform}:{keyword}"])
            return {
                "list": [{**item, "style": dict(STYLE)} for item in result["list"]], "page": current, "pagecount": 1,
                "limit": 1
            }
        if platform == "yy":
            return self._yy_search(keyword, current)
        if platform == "douyu":
            data = self._douyu(DOUYU + "/japi/search/api/searchShow",
                               {"params": {"kw": keyword, "page": current, "pageSize": 20}})
            if not isinstance(data.get("relateShow"), list) or type(data.get("total")) is not int:
                raise ValueError("斗魚搜尋回應格式錯誤")
            return self.page([
                _card(platform, item["rid"], item["roomName"], item.get("roomSrc"), item.get("nickName"))
                for item in data["relateShow"]
            ], current, 20, data["total"])
        result = self.net.json(
            "https://search.cdn.huya.com/", {
                "params": {
                    "m": "Search", "do": "getSearchContent", "q": keyword, "typ": -5, "rows": 20,
                    "start": (current - 1) * 20, "v": 4
                }, "headers": _headers("huya")
            })
        data = result.get("response", {}).get("1") or {}
        if result.get("responseHeader", {}).get("status") != 0 or not isinstance(data.get("docs"), list) or type(
                data.get("numFound")) is not int:
            raise ValueError("虎牙搜尋回應格式錯誤")
        return self.page([
            _card(platform, item["room_id"],
                  item.get("live_intro") or item["game_nick"], item.get("game_avatarUrl180"), item["game_nick"] +
                  ("" if item.get("gameLiveOn") else " · 未開播")) for item in data["docs"]
        ], current, 20, data["numFound"])

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        responses = [self._detail(video_id) for video_id in ids]
        return {**responses[0], "list": [item for response in responses for item in response["list"]]}

    def _detail(self, video_id):
        room = _room_id(video_id)
        platform, id = room["platform"], room["id"]
        if platform == "douyu":
            data = self._douyu("https://open.douyucdn.cn/api/RoomApi/room/" + id)
            vod = _card(platform, data["room_id"], data["room_name"], data.get("room_thumb"), data.get("owner_name"))
            content = [
                data.get("cate_name"),
                data.get("owner_name"), "直播中" if data.get("room_status") == "1" else "未開播"
            ]
        elif platform == "yy":
            data = self._yy_room(id)
            vod = _yy_card(data)
            content = [data.get("biz"), data["name"], "直播中"]
        else:
            data = self._huya_room(id)
            profile, live = data["profileInfo"], data.get("liveData") or {}
            vod = _card(platform, profile["profileRoom"],
                        live.get("introduction") or live.get("roomName") or profile["nick"],
                        live.get("screenshot") or profile.get("avatar180"), profile["nick"])
            content = [
                live.get("gameFullName"), profile["nick"], "直播中" if data.get("realLiveStatus") == "ON" else "未開播"
            ]
        vod.update(vod_content=" · ".join(item for item in content if item), vod_play_from=NAMES[platform],
                   vod_play_url="觀看直播$" + vod["vod_id"])
        return {"list": [vod]}

    def _douyu_stream(self, id):

        def load():
            scripts = self.net.cached(f"sign:douyu:{id}", {"ttl": 300000, "stale": False},
                                      lambda: self._douyu(DOUYU + "/swf_api/homeH5Enc", {"params": {"rids": id}}))
            source = scripts.get("room" + id)
            if not isinstance(source, str) or not source:
                raise ValueError("斗魚播放簽名資料無效")
            signed = self.js.eval("var CryptoJS = {MD5: md5X};\n" + source + "\nub98484234(rid, did, tt);", {
                "globals": {"rid": id, "did": self.device_id, "tt": str(int(time.time()))}
            })
            params = dict(parse_qsl(signed))
            return self._douyu(f"{DOUYU}/lapi/live/getH5Play/{id}",
                               {"method": "POST", "postType": "form", "data": {**params, "cdn": "", "rate": 0}})

        return self.net.cached(f"stream:douyu:{id}", {"ttl": 5000, "stale": False}, load)

    def _douyu_url(self, id):
        data = self._douyu_stream(id)
        if not data.get("rtmp_url") or not data.get("rtmp_live"):
            raise ValueError("斗魚目前沒有可播放的直播")
        return data["rtmp_url"].rstrip("/") + "/" + data["rtmp_live"].lstrip("/")

    def _douyu_live(self, id):
        url = self._douyu_url(id)
        format = "application/x-mpegURL" if urlsplit(url).path.endswith(".m3u8") else "video/x-flv"
        if format == "video/x-flv":
            url = self.proxyUrl({"live": "douyu:" + id})
        return {"parse": 0, "url": url, "header": _headers("douyu"), "format": format}

    def _replay_info(self, id):

        def load():
            result = self.net.json(DOUYU + "/wgapi/live/liveweb/roomapi/biz/getSwitch",
                                   {"params": {"rid": id}, "headers": _headers("douyu")})
            data = result.get("data") or {}
            code = result.get("code")
            if not _douyu_success(code) or not isinstance(data.get("playback"), dict) or not isinstance(
                    data.get("roomInfo"), dict):
                raise ValueError("斗魚回看資料無效")
            show = int(data["playback"].get("show") or 0)
            start = float(data["playback"].get("startTime") or 0) * 1000
            if show == 1 and (not math.isfinite(start) or not start.is_integer() or not 0 < start < _now()
                              or start > MAX_SAFE_INTEGER):
                raise ValueError("斗魚回看時間無效")
            window = (24 if int(data["roomInfo"].get("aiLiveSummary") or 0) == 1 else 2) * 3600000
            return {"show": show, "start": int(start), "window": window}

        return self.net.cached(f"replay:douyu:{id}", {"ttl": 60000, "stale": False}, load)

    def _timeshift(self, id):
        try:
            info = self._replay_info(id)
            if info["show"] == 1:
                url = self.proxyUrl({"replay": "douyu:" + id, "time": "{time}"})
                return {"url": url, "start": info["start"], "window": info["window"]}
        except Exception:
            self.log("斗魚回看資料暫時無法取得，保留直播播放")

    def _replay(self, id, value):
        if not re.fullmatch(r"[0-9]+", str(value)):
            raise ValueError("回看時間無效")
        stamp = int(value)
        if stamp == 0:
            return self._douyu_live(id)
        now = _now()
        if not 0 < stamp < now or stamp > MAX_SAFE_INTEGER:
            raise ValueError("回看時間無效")
        info = self._replay_info(id)
        if info["show"] != 1:
            raise ValueError("斗魚目前未提供回看")
        start = max(stamp, info["start"], now - info["window"])
        data = self._douyu(
            DOUYU + "/japi/universe/playback/getVodStream", {
                "params": {
                    "rid": id, "startTime": (start + 999) // 1000, "pt": 2, "rate": 0, "client_sys": "web",
                    "timeshiftReplay": 1, "isloopclick": 0
                }
            })
        if not isinstance(data.get("timeshiftUrl"), str) or not re.match(r"https?://", data["timeshiftUrl"]):
            raise ValueError("斗魚沒有回傳回看播放網址")
        return {"parse": 0, "url": data["timeshiftUrl"], "header": _headers("douyu"), "format": "application/x-mpegURL"}

    def _huya_lines(self, id):
        data = self._huya_room(id)
        if data.get("realLiveStatus") != "ON":
            raise ValueError("虎牙主播目前未開播")
        lines = (data.get("stream") or {}).get("baseSteamInfoList")
        if not isinstance(lines, list):
            raise ValueError("虎牙缺少播放線路")
        available = []
        for item in lines:
            rate = item.get("iWebPriorityRate")
            if type(rate) in (int, float) and math.isfinite(rate) and rate > 0:
                available.append(item)
        available.sort(key=lambda item: item["iWebPriorityRate"], reverse=True)
        if not available:
            raise ValueError("虎牙沒有可播放的線路")
        return available

    def _huya_stream_url(self, id, cdn):
        for item in self._huya_lines(id):
            if item["sCdnType"] == cdn:
                return _huya_url(item)
        raise ValueError("虎牙播放線路已失效")

    def _huya_live(self, id):
        values = [{"n": item["sCdnType"], "v": self.proxyUrl({"live": "huya:" + id, "cdn": item["sCdnType"]})}
                  for item in self._huya_lines(id)]
        return {
            "parse": 0, "url": {"values": values, "position": 0},
            "header": _headers("huya"), "format": "video/x-flv"
        }

    def _yy_source(self, id):

        def load():
            room = self._yy_room(id)
            sid, ssid = str(room["sid"]), str(room["ssid"])
            stamp = _now()
            version = "5.23.0-beta.2"
            result = self.net.json("https://stream-manager.yy.com/v3/channel/streams", {
                "method": "POST", "postType": "json",
                "headers": {**_headers("yy"), "Origin": YY, "Content-Type": "application/json; charset=utf-8"},
                "params": {"uid": 0, "cid": sid, "sid": ssid, "appid": 0, "sequence": stamp, "encode": "json"},
                "data": {
                    "head": {"seq": stamp, "appidstr": "0", "bidstr": "120", "cidstr": sid, "sidstr": ssid,
                             "uid64": 0, "client_type": 108, "client_ver": version, "stream_sys_ver": 1,
                             "app": "www.yy.com", "playersdk_ver": version, "thundersdk_ver": "0", "streamsdk_ver": version},
                    "client_attribute": {"client": "web", "model": "web0", "cpu": "", "graphics_card": "",
                                         "os": "chrome", "osversion": "148.0.0.0", "vsdk_version": "", "app_identify": "",
                                         "app_version": "", "business": "", "width": "1920", "height": "1080", "scale": "",
                                         "client_type": 8, "h265": 0},
                    "avp_parameter": {"version": 1, "client_type": 8, "service_type": 0, "imsi": 0,
                                      "send_time": stamp // 1000, "line_seq": -1, "gear": 4, "ssl": 1, "stream_format": 0}
                }
            })
            source = urlsplit(_yy_stream_url(result))
            query = urlencode({"playeruid": 0, "uuid": self.device_id})
            url = source._replace(query=source.query + ("&" if source.query else "") + query).geturl()
            return {"parse": 0, "url": url, "header": _headers("yy"), "format": "video/x-flv"}

        return self.net.cached(f"stream:yy:{id}", {"ttl": 5000, "stale": False}, load)

    def _yy_live(self, id):
        return {**self._yy_source(id), "url": self.proxyUrl({"live": "yy:" + id})}

    def playerContent(self, flag, id, vipFlags):
        room = _room_id(id)
        if room["platform"] == "douyu":
            result, timeshift = self.net.map([self._douyu_live, self._timeshift], lambda load, index: load(room["id"]), 2)
            if timeshift:
                result["timeshift"] = timeshift
        elif room["platform"] == "yy":
            result = self._yy_live(room["id"])
        else:
            result = self._huya_live(room["id"])
        result["position"] = 0
        result["danmaku"] = [{"name": "即時彈幕", "url": self.danmakuUrl(id)}]
        return result

    def proxy(self, params):
        if params.get("replay"):
            room = _room_id(params["replay"])
            if room["platform"] != "douyu":
                raise ValueError("此平台目前不提供回看")
            return [
                200, "application/json; charset=utf-8",
                json.dumps(self._replay(room["id"], params.get("time")), ensure_ascii=False),
                {"Cache-Control": "no-store"}
            ]
        room = _room_id(params.get("live"))
        platform, id = room["platform"], room["id"]

        def get_url():
            if platform == "yy":
                return self._yy_source(id)["url"]
            return self._douyu_url(id) if platform == "douyu" else self._huya_stream_url(id, params.get("cdn"))

        cache_key = f"room:huya:{id}" if platform == "huya" else f"stream:{platform}:{id}"
        get_url()

        def open_source():
            options = {"headers": _headers(platform), "timeout": 15000, "callTimeout": 0}
            reader = self.net.openStream(get_url(), options)
            if reader.code in (401, 403, 404):
                reader.close()
                self.net.clearCache(cache_key)
                reader = self.net.openStream(get_url(), options)
            if reader.code != 200:
                reader.close()
                raise ValueError("直播串流 HTTP " + str(reader.code))
            return reader

        min_duration = 10000 if platform in ("huya", "yy") else 0
        create_normalizer = self.yy_stream.Normalizer if platform == "yy" else None
        stream = self.stream.flv_stream(open_source, self.net.sleep, min_duration, create_normalizer)
        response = self.net.stream(stream)
        return [200, "video/x-flv", response["stream"], {"Cache-Control": "no-store", "Accept-Ranges": "none"}]

    def danmaku(self, id, emit):
        room = _room_id(id)
        if self._stop_danmaku is not None:
            self._stop_danmaku()
        if room["platform"] == "yy":
            data = self._yy_room(room["id"])
            room.update(top=str(data["sid"]), sub=str(data["ssid"]))
        elif room["platform"] == "huya":
            data = self._huya_room(room["id"])
            if data.get("realLiveStatus") != "ON":
                raise ValueError("虎牙主播目前未開播")
            lines = (data.get("stream") or {}).get("baseSteamInfoList") or []
            if not lines:
                raise ValueError("虎牙缺少彈幕房間資料")
            room.update(uid=lines[0]["lPresenterUid"], top=lines[0]["lChannelId"], sub=lines[0]["lSubChannelId"])
        stop = self.protocol.subscribe(self.net, room, emit)

        def close():
            stop()
            if self._stop_danmaku is close:
                self._stop_danmaku = None

        self._stop_danmaku = close
        return close

    def destroy(self):
        stop = getattr(self, "_stop_danmaku", None)
        if stop is not None:
            stop()
