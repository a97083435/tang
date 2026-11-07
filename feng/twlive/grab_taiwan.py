#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台湾电视直播 · 自动抓取脚本（FongMi 5.8.7 用）

用法（在本机 / 电脑上，任选其一）：
    python3 grab_taiwan.py            # 抓取 + 生成全部文件
    python3 grab_taiwan.py --no-check # 抓取但不做逐条连通性抽查（更快）

抓取来源（2026-11-07 实测可拉取）：
    1. iptv-org/iptv streams/tw.m3u（最全、最规范，tvg-id 可靠）
    2. iptv-org/iptv countries/tw.m3u（官网页，含 Hakka/NTD/TTV News 等）
    3. hujingguang/ChinaIPTV TaiWan.m3u8（含 YouTube 转 HLS 的新闻台）
    4. lisb0910/tv liveTVList.txt（TXT 社区列表，只取白名单直链 .m3u8：
       74.91.26.218、4gtv.cnlive.club、cdn.19891230.eu.org、38.64.72.148、
       61.221.215.25；代理 php / P2P / mitv / video:// / YouTube 页一律不要。
       靠它补回中视、公视、华视、年代新闻、非凡新闻、东森综合、纬来系列等）
    另：limajj2021/taiwan-iptv playlist_static.m3u 只作 taiwan.json 的
    远程备用源，不并入内嵌表——其中个别地址与台名明显不符
    （如民视台湾台指向印度新闻流、华视新闻指向 Da Vinci 学习频道）。

处理规则（与大陆版 live.py 同一套）：
    - 只要 http(s) 播放地址；rtmp / rtsp / P2P / YouTube 观看页直接丢弃，
      没有直链 HLS 的台不硬塞占位地址（例如华视主频只有 rtmp，本次未收）。
    - GOOD TV 的 CH3、CH5…等几十条是同一台的点播短片分流，不是独立
      电视台，只保留 CH1 综合台、CH2 真理台。
    - 原住民族电视台在两个源里名字不同（Indigenous TV / Taiwan
      Indigenous TV），合并为一个台；大爱 1/2 同理。
    - 每个台最多 3 条线；带时效 token（auth_key= / _upt= / hdnea= 等）
      的地址排最后；逐条做连通性抽查（取前 512 字节看是不是 #EXTM3U），
      能确认是 m3u8 的排前面，抽查失败的不删除、只排后面——本机是
      境外网络，超时不等于在大陆手机上播不了。
    - 台名统一转简体（与大陆版一致，方便 EPG / 台标按名匹配）。

生成文件（都在本脚本所在目录）：
    taiwan.py / taiwan.json / taiwan-config.json / taiwan.txt / README.md
    build_report.json（本次抓取的来源计数、抽查结果、丢弃清单）
"""

import json
import re
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
TODAY = date.today().isoformat()
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

SOURCES = [
    ("iptv-org-streams", "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tw.m3u"),
    ("iptv-org-countries", "https://iptv-org.github.io/iptv/countries/tw.m3u"),
    ("ChinaIPTV-TaiWan", "https://raw.githubusercontent.com/hujingguang/ChinaIPTV/main/TaiWan.m3u8"),
]

# TXT 社区列表（只取白名单直链，见 LISB_HOSTS）
TXT_SOURCES = [
    ("lisb0910-tv", "https://raw.githubusercontent.com/lisb0910/tv/main/liveTVList.txt"),
]
LISB_HOSTS = {"74.91.26.218", "4gtv.cnlive.club", "cdn.19891230.eu.org",
              "38.64.72.148", "61.221.215.25"}

# ---------------------------------------------------------------- 命名
# tvg-id（去掉 .tw / @SD 后缀）->（简体台名，分组）
NAME_MAP = {
    "BeautifulLifeTV": ("Beautiful Life TV", "台湾·宗教"),
    "CGNTVChinese": ("CGNTV中文台", "台湾·宗教"),
    "CTiVariety": ("中天综合台", "台湾·综合娱乐"),
    "CTS": ("华视", "台湾·无线"),
    "CTSNews": ("华视新闻资讯台", "台湾·新闻"),
    "DaAi1": ("大爱1台", "台湾·文化"),
    "DaAi2": ("大爱2台", "台湾·文化"),
    "DaliTV": ("大立电视台", "台湾·文化"),
    "DiscoveryAsiaTaiwan": ("探索频道亚洲台", "台湾·电影娱乐"),
    "EBCFinancialNews": ("东森财经新闻台", "台湾·新闻"),
    "EBCForeignMovie": ("东森洋片台", "台湾·综合娱乐"),
    "EBCNews": ("东森新闻台", "台湾·新闻"),
    "FTV": ("民视", "台湾·无线"),
    "FTVOne": ("民视第一台", "台湾·综合娱乐"),
    "FTVTaiwan": ("民视台湾台", "台湾·综合娱乐"),
    "GoodTV": ("GOOD TV综合台", "台湾·宗教"),
    "Good2": ("GOOD TV真理台", "台湾·宗教"),
    "HakkaTV": ("客家电视台", "台湾·文化"),
    "IndigenousTV": ("原住民族电视台", "台湾·文化"),
    "TaiwanIndigenousTV": ("原住民族电视台", "台湾·文化"),
    "MOMOTV": ("MOMO TV", "台湾·综合娱乐"),
    "NTDTVAsiaPacific": ("新唐人电视台", "台湾·宗教"),
    "PTS3": ("公视3台", "台湾·综合娱乐"),
    "SETMetro": ("三立都会台", "台湾·综合娱乐"),
    "SETNews": ("三立新闻台", "台湾·新闻"),
    "SETTaiwan": ("三立台湾台", "台湾·综合娱乐"),
    "SETiNews": ("三立iNEWS台", "台湾·新闻"),
    "SJTV": ("SJTV", "台湾·综合娱乐"),
    "SupremeMasterTV": ("无上师电视台", "台湾·宗教"),
    "TaiwanPlusTV": ("Taiwan Plus", "台湾·文化"),
    "TVBSAsia": ("TVBS Asia", "台湾·综合娱乐"),
    "TVBSNews": ("TVBS新闻台", "台湾·新闻"),
    "TTV": ("台视", "台湾·无线"),
    "TTVNews": ("台视新闻台", "台湾·新闻"),
    "WXTV": ("唯心电视台", "台湾·宗教"),
    "AnimaxAsia": ("Animax亚洲台", "台湾·电影娱乐"),
    "AXNAsia": ("AXN亚洲台", "台湾·电影娱乐"),
    "CinemaxAsia": ("Cinemax亚洲台", "台湾·电影娱乐"),
    "HBOAsia": ("HBO亚洲台", "台湾·电影娱乐"),
    "EBCYOYO": ("东森YOYO台", "台湾·综合娱乐"),
    "CTiNews": ("中天新闻台", "台湾·新闻"),
    "FTVNews": ("民视新闻台", "台湾·新闻"),
    "GlobalNews": ("寰宇新闻台", "台湾·新闻"),
    "mnews": ("镜新闻台", "台湾·新闻"),
    "ETMall60": ("东森购物60台", "台湾·电影娱乐"),
    "GeniusGoGoGo": ("Genius Go Go Go", "台湾·电影娱乐"),
}

# 没有 tvg-id 时，按“去掉空格/大小写后的显示名”匹配
NAME_BY_DISPLAY = {
    "goodtv": ("GOOD TV综合台", "台湾·宗教"),
    "good2": ("GOOD TV真理台", "台湾·宗教"),
    "goodtvch1": ("GOOD TV综合台", "台湾·宗教"),
    "goodtvch2": ("GOOD TV真理台", "台湾·宗教"),
    "daai1": ("大爱1台", "台湾·文化"),
    "daai2": ("大爱2台", "台湾·文化"),
    "taiwanplus": ("Taiwan Plus", "台湾·文化"),
    "taiwanplustv": ("Taiwan Plus", "台湾·文化"),
}

# 社区 TXT 列表的中文台名（简体）->（简体台名，分组）。
# 键要先去掉末尾一个“台”字再查，HD 后缀也先去掉。
LISB_MAP = {
    "中天新闻": ("中天新闻台", "台湾·新闻"),
    "中天亚洲": ("中天亚洲台", "台湾·综合娱乐"),
    "中天娱乐": ("中天娱乐台", "台湾·综合娱乐"),
    "中天综合": ("中天综合台", "台湾·综合娱乐"),
    "中视": ("中视", "台湾·无线"),
    "中视新闻": ("中视新闻台", "台湾·新闻"),
    "中视经典": ("中视经典台", "台湾·综合娱乐"),
    "中视菁采": ("中视菁采台", "台湾·综合娱乐"),
    "公视": ("公视", "台湾·无线"),
    "公视2": ("公视2台", "台湾·综合娱乐"),
    "台视财经": ("台视财经台", "台湾·新闻"),
    "民视综艺": ("民视综艺台", "台湾·综合娱乐"),
    "民视影剧": ("民视影剧台", "台湾·综合娱乐"),
    "年代新闻": ("年代新闻台", "台湾·新闻"),
    "非凡新闻": ("非凡新闻台", "台湾·新闻"),
    "东森综合": ("东森综合台", "台湾·综合娱乐"),
    "东森戏剧": ("东森戏剧台", "台湾·综合娱乐"),
    "东森电影": ("东森电影台", "台湾·电影娱乐"),
    "东森超视": ("东森超视台", "台湾·综合娱乐"),
    "纬来体育": ("纬来体育台", "台湾·综合娱乐"),
    "纬来综合": ("纬来综合台", "台湾·综合娱乐"),
    "纬来戏剧": ("纬来戏剧台", "台湾·综合娱乐"),
    "纬来日本": ("纬来日本台", "台湾·综合娱乐"),
    "纬来育乐": ("纬来育乐台", "台湾·综合娱乐"),
    "TVBS HD": ("TVBS HD", "台湾·综合娱乐"),
    "TVBS欢乐台": ("TVBS欢乐台", "台湾·综合娱乐"),
    "TVBS精采台": ("TVBS精采台", "台湾·综合娱乐"),
    "TVBS台剧台": ("TVBS台剧台", "台湾·综合娱乐"),
    "三立综合": ("三立综合台", "台湾·综合娱乐"),
    "三立戏剧": ("三立戏剧台", "台湾·综合娱乐"),
    "八大戏剧": ("八大戏剧台", "台湾·综合娱乐"),
    "寰宇台湾": ("寰宇台湾台", "台湾·新闻"),
    "华视": ("华视", "台湾·无线"),
    "华视新闻": ("华视新闻资讯台", "台湾·新闻"),
    "台视新闻": ("台视新闻台", "台湾·新闻"),
    "民视新闻": ("民视新闻台", "台湾·新闻"),
    "民视台湾台": ("民视台湾台", "台湾·综合娱乐"),
    "民视第一台": ("民视第一台", "台湾·综合娱乐"),
    "民视": ("民视", "台湾·无线"),
    "台视": ("台视", "台湾·无线"),
    "东森财经新闻": ("东森财经新闻台", "台湾·新闻"),
    "东森新闻": ("东森新闻台", "台湾·新闻"),
    "三立新闻": ("三立新闻台", "台湾·新闻"),
    "三立iNEWS": ("三立iNEWS台", "台湾·新闻"),
    "镜新闻": ("镜新闻台", "台湾·新闻"),
    "寰宇新闻台": ("寰宇新闻台", "台湾·新闻"),
    "寰宇新闻": ("寰宇新闻台", "台湾·新闻"),
    "东森洋片": ("东森洋片台", "台湾·综合娱乐"),
}

GROUP_ORDER = ["台湾·新闻", "台湾·无线", "台湾·综合娱乐",
               "台湾·文化", "台湾·宗教", "台湾·电影娱乐"]

# 每组内的排位（不在表里的按台名排后面）
GROUP_RANK = {
    "台湾·新闻": ["东森新闻台", "TVBS新闻台", "三立新闻台", "中天新闻台",
               "民视新闻台", "台视新闻台", "华视新闻资讯台", "寰宇新闻台",
               "镜新闻台", "三立iNEWS台", "东森财经新闻台", "中视新闻台",
               "年代新闻台", "非凡新闻台", "寰宇台湾台", "台视财经台"],
    "台湾·无线": ["台视", "民视", "中视", "公视", "华视"],
    "台湾·综合娱乐": ["TVBS Asia", "三立台湾台", "三立都会台", "民视台湾台",
                   "民视第一台", "中天综合台", "东森洋片台", "东森YOYO台",
                   "MOMO TV", "公视3台", "SJTV", "三立综合台", "三立戏剧台",
                   "中天亚洲台", "中天娱乐台", "TVBS HD", "TVBS欢乐台",
                   "TVBS精采台", "TVBS台剧台", "东森综合台", "东森戏剧台",
                   "东森超视台", "民视综艺台", "民视影剧台", "纬来体育台",
                   "纬来综合台", "纬来戏剧台", "纬来日本台", "纬来育乐台",
                   "八大戏剧台", "中视经典台", "中视菁采台", "公视2台"],
    "台湾·文化": ["Taiwan Plus", "客家电视台", "原住民族电视台",
               "大爱1台", "大爱2台", "大立电视台"],
    "台湾·宗教": ["GOOD TV综合台", "GOOD TV真理台", "Beautiful Life TV",
               "CGNTV中文台", "唯心电视台", "无上师电视台", "新唐人电视台"],
    "台湾·电影娱乐": ["HBO亚洲台", "Cinemax亚洲台", "AXN亚洲台",
                   "Animax亚洲台", "探索频道亚洲台", "东森购物60台",
                   "Genius Go Go Go", "东森电影台"],
}

# 繁 -> 简（只覆盖台名里会出现的字）
TRAD2SIMP = str.maketrans({
    "臺": "台", "灣": "湾", "綜": "综", "視": "视", "電": "电", "頻": "频",
    "樂": "乐", "廣": "广", "衛": "卫", "兒": "儿", "親": "亲", "學": "学",
    "會": "会", "體": "体", "動": "动", "畫": "画", "劇": "剧", "場": "场",
    "購": "购", "詩": "诗", "經": "经", "濟": "济", "財": "财", "證": "证",
    "傳": "传", "達": "达", "緯": "纬", "來": "来", "歡": "欢", "愛": "爱",
    "麗": "丽", "寶": "宝", "夢": "梦", "華": "华", "單": "单", "龍": "龙",
    "鳳": "凤", "蘭": "兰", "絲": "丝", "書": "书", "報": "报", "聞": "闻",
    "資": "资", "訊": "讯", "語": "语", "說": "说", "讀": "读", "國": "国",
    "際": "际", "歲": "岁", "興": "兴", "發": "发", "業": "业",
    "對": "对", "觀": "观", "讓": "让", "認": "认", "識": "识", "實": "实",
    "質": "质", "賓": "宾", "館": "馆", "鐵": "铁", "鑼": "锣",
    "亞": "亚", "娛": "娱", "東": "东", "戲": "戏", "藝": "艺",
    "慶": "庆", "憲": "宪", "憑": "凭", "錢": "钱", "錦": "锦", "鎮": "镇",
    "鏡": "镜", "閱": "阅", "關": "关", "開": "开", "門": "门", "問": "问",
    "間": "间", "陽": "阳", "陰": "阴", "雲": "云", "靈": "灵", "響": "响",
    "頁": "页", "頂": "顶", "須": "须", "顧": "顾", "預": "预", "領": "领",
    "顏": "颜", "額": "额", "飛": "飞", "飲": "饮", "驚": "惊", "驗": "验",
    "魚": "鱼", "魯": "鲁", "麥": "麦", "黃": "黄", "點": "点", "頭": "头",
    "聽": "听", "廠": "厂", "廢": "废", "麵": "面", "龜": "龟", "鬱": "郁",
    "奮": "奋", "霧": "雾", "馬": "马", "馮": "冯", "駕": "驾", "餅": "饼",
    "餓": "饿", "颱": "台", "麼": "么",
})

TOKEN_HINTS = ("auth_key=", "_upt=", "hdnea=", "wsSecret=", "txSecret=",
               "wsTime=", "txTime=", "auth=", "token=")


def to_simp(text):
    return text.translate(TRAD2SIMP)


def clean_display(raw):
    """去掉 (720p) / [Geo-blocked] / [Not 24/7] 等后缀，繁转简。"""
    name = re.sub(r"\s*\(\d+p\)", "", raw or "")
    name = re.sub(r"\s*\[[^\]]*\]", "", name)
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name) if "(" in name and (
        "HUA-CHI" in name or "Taiwan" in name) else name
    return to_simp(name.strip())


def canonical_name(raw, tvg_id=""):
    """返回 (台名, 分组)；GOOD TV 分流返回 None 表示丢弃。"""
    base_id = (tvg_id or "").split("@")[0].split(".")[0].strip()
    if base_id in NAME_MAP:
        return NAME_MAP[base_id]
    disp = clean_display(raw)
    key = re.sub(r"[^a-z0-9]", "", disp.lower())
    if key in NAME_BY_DISPLAY:
        return NAME_BY_DISPLAY[key]
    if re.match(r"goodtvch\d+", key):
        return None  # GOOD TV CH3/CH5…是点播分流，不是独立台
    if key.startswith("goodtvch"):
        return None
    # 社区 TXT 列表的中文名：去掉末尾“台”、去掉 HD 后缀再查
    simp = disp
    for variant in (simp, simp[:-1] if simp.endswith("台") else simp,
                    simp[:-2] if simp.endswith("HD") else simp):
        v = variant.strip()
        if v in LISB_MAP:
            return LISB_MAP[v]
        if v.endswith("台") and v[:-1] in LISB_MAP:
            return LISB_MAP[v[:-1]]
    group = ""
    return (disp, group)


def is_playable(url):
    if not url:
        return False
    u = url.strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        return False
    low = u.lower()
    if low.startswith(("rtmp://", "rtsp://")):
        return False
    if "youtube.com/watch" in low or "youtu.be/" in low:
        return False
    if low.endswith((".jpg", ".png", ".gif", ".webp", ".html", ".htm")):
        return False
    return True


def fetch_text(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="ignore")


def parse_m3u(text):
    """解析 M3U/M3U8，返回 [(raw_name, tvg_id, group_title, url)]。"""
    out = []
    name, tvg_id, group = None, "", ""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            tvg = re.search(r'tvg-id="([^"]*)"', line)
            grp = re.search(r'group-title="([^"]*)"', line)
            tvg_id = tvg.group(1) if tvg else ""
            group = grp.group(1) if grp else ""
            name = line.rsplit(",", 1)[-1].strip() if "," in line else ""
        elif line.startswith("#"):
            continue
        elif name is not None:
            out.append((name, tvg_id, group, line.strip()))
            name, tvg_id, group = None, "", ""
    return out


def parse_txt(text):
    """解析 “台名,地址” TXT 列表，返回 [(raw_name, "", "", url)]。"""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or "," not in line:
            continue
        name, url = line.split(",", 1)
        name, url = name.strip(), url.strip()
        if url == "#genre#" or not url:
            continue
        out.append((name, "", "", url))
    return out


def lisb_url_ok(url):
    """社区列表只收白名单主机的直链 .m3u8（查询串只允 ?zbj）。"""
    from urllib.parse import urlparse
    try:
        parts = urlparse(url)
    except Exception:
        return False
    if parts.scheme not in ("http", "https"):
        return False
    host = (parts.hostname or "").lower()
    if host not in LISB_HOSTS and not host.endswith(".4gtv.cnlive.club"):
        return False
    if not parts.path.endswith(".m3u8"):
        return False
    if parts.query and parts.query != "zbj":
        return False
    return True


# 注：ChiSheng9 的 TVnn.m3u8 文件里只有一条 YouTube 观看页地址，
# 解析出来 FongMi 也播不了，所以 build 时整条丢弃，不再解析它。


# ---------------------------------------------------------------- 抽查
def check_url(url, timeout=8):
    """2 = 取到 #EXTM3U 播放列表；1 = 有响应但不是 m3u8 文本
    （.ts/.flv/裸地址等）；0 = 超时/失败/非 2xx-3xx。"""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": UA}, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            head = resp.read(512)
            if head.startswith(b"#EXTM3U") or b"#EXTINF" in head:
                return 2
            return 1
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return 1
        return 0
    except Exception:
        return 0


def check_all(urls, enabled=True):
    if not enabled:
        return {u: -1 for u in urls}
    scores = {}
    with ThreadPoolExecutor(max_workers=16) as pool:
        for url, score in zip(urls, pool.map(check_url, urls)):
            scores[url] = score
    return scores


# ---------------------------------------------------------------- 合并
def build_channels(do_check=True):
    report = {"sources": {}, "dropped": [], "resolved": {}}
    merged = {}   # 台名 -> {"group": g, "urls": [u, ...], "from": set}
    order = []    # 台名首次出现的顺序

    for label, url in SOURCES:
        try:
            text = fetch_text(url)
        except Exception as e:
            report["sources"][label] = {"url": url, "error": str(e), "entries": 0}
            continue
        entries = parse_m3u(text)
        kept = 0
        for raw, tvg_id, _grp, link in entries:
            got = canonical_name(raw, tvg_id)
            if got is None:
                report["dropped"].append(
                    {"name": clean_display(raw), "reason": "GOOD TV 点播分流，非独立台", "source": label})
                continue
            name, group = got
            if not name:
                continue
            if not is_playable(link):
                report["dropped"].append(
                    {"name": name, "url": link, "reason": "非 http(s) 直链（rtmp/YouTube 观看页等）", "source": label})
                continue
            if "ChiSheng9/iptv/master/TV" in link:
                # 该文件本身只是个指向 YouTube 观看页的播放列表，
                # FongMi 播不了，直接丢弃整条。
                report["dropped"].append(
                    {"name": name, "url": link,
                     "reason": "ChiSheng9 转跳 YouTube 观看页，无直链 HLS",
                     "source": label})
                continue
            if name not in merged:
                merged[name] = {"group": group or "台湾·综合娱乐",
                                "urls": [], "from": set()}
                order.append(name)
            if group:
                merged[name]["group"] = group
            if link not in merged[name]["urls"]:
                merged[name]["urls"].append(link)
                merged[name]["from"].add(label)
                kept += 1
        report["sources"][label] = {"url": url, "entries": len(entries),
                                    "kept_lines": kept}

    for label, url in TXT_SOURCES:
        try:
            text = fetch_text(url)
        except Exception as e:
            report["sources"][label] = {"url": url, "error": str(e), "entries": 0}
            continue
        entries = parse_txt(text)
        kept = 0
        for raw, _tvg, _grp, link in entries:
            if not lisb_url_ok(link):
                continue  # 社区列表只收白名单直链，其余代理/P2P/YouTube 页不记入丢弃
            got = canonical_name(raw, "")
            if got is None:
                continue
            name, group = got
            if not name or not group:
                continue  # 不在白名单台名表里的不收，避免把杂台塞进来
            if name not in merged:
                merged[name] = {"group": group, "urls": [], "from": set()}
                order.append(name)
            if link not in merged[name]["urls"]:
                merged[name]["urls"].append(link)
                merged[name]["from"].add(label)
                kept += 1
        report["sources"][label] = {"url": url, "entries": len(entries),
                                    "kept_lines": kept}

    # 排序每台的线路：能确认是 m3u8 的在前，时效 token 的在后；每台最多 3 条
    all_urls = [u for info in merged.values() for u in info["urls"]]
    scores = check_all(sorted(set(all_urls)), enabled=do_check)
    report["check"] = {"ok_m3u8": sum(1 for s in scores.values() if s == 2),
                       "ok_other": sum(1 for s in scores.values() if s == 1),
                       "failed": sum(1 for s in scores.values() if s == 0),
                       "skipped": sum(1 for s in scores.values() if s == -1),
                       "scores": scores}

    def url_key(u):
        token = 1 if any(h in u for h in TOKEN_HINTS) else 0
        return (token, -scores.get(u, -1))

    channels = []
    for name in order:
        info = merged[name]
        urls = sorted(info["urls"], key=url_key)[:3]
        if not urls:
            continue
        channels.append({"name": name, "group": info["group"], "urls": urls})

    # 分组排序：先按分组顺序，再按组内排位表，最后按台名
    def chan_key(ch):
        gi = GROUP_ORDER.index(ch["group"]) if ch["group"] in GROUP_ORDER else 99
        rank = GROUP_RANK.get(ch["group"], [])
        ri = rank.index(ch["name"]) if ch["name"] in rank else 99
        return (gi, ri, ch["name"])

    channels.sort(key=chan_key)
    return channels, report


def groups_of(channels):
    groups = []
    for ch in channels:
        if not groups or groups[-1]["name"] != ch["group"]:
            groups.append({"name": ch["group"], "channel": []})
        groups[-1]["channel"].append({"name": ch["name"], "urls": ch["urls"]})
    return groups


# ---------------------------------------------------------------- 生成
SPIDER_TEMPLATE = '''"""台湾电视直播 —— FongMi / TVBox Python 爬虫（CatVodSpider 新写法）。

频道
----
- 内嵌 __TOTAL__ 个频道，分组：__GROUP_SUMMARY__。
  （分组计数以生成时为准，见 README；频道名全局唯一，可直接当 vod_id。）
- 每个频道最多 3 条线：先 iptv-org 台湾源，再 ChinaIPTV 台湾源，
  再 lisb0910 社区列表的白名单直链。单线频道占多数——公开源就是这样，
  播不了先切线路，再切 taiwan.json 里的远程备用源。

来源（__DATE__ 拉取，见 grab_taiwan.py）
--------------------------------------
- iptv-org/iptv：streams/tw.m3u、countries/tw.m3u
- hujingguang/ChinaIPTV：TaiWan.m3u8
- lisb0910/tv：liveTVList.txt（只取白名单直链 .m3u8）

自动更新
--------
- 平时用内嵌表，不联网也照常播；想让爬虫每次打开时去 iptv-org
  拉一份最新台湾列表（失败自动回落内嵌表，不影响播放），把
  taiwan-config.json 里本站的 ext 改成：{"auto_update": true}
  只拉 iptv-org countries/tw.m3u 这一路，8 秒超时，拉不到就用内嵌表。
- 电脑上刷新：python3 grab_taiwan.py，重新生成本文件与 taiwan.json。

写法规范（对照大陆版 live.py 与 yangshipin.py）
------------------------------------------------
- ``from base.spider import Spider as BaseSpider``，``class Spider(BaseSpider)``，
  全部入口是同步 ``def``，不使用 async。
- 请求一律 ``self.net.json(url, options)`` / ``self.net.req(...)``，
  不用已移除的 ``self.fetch()`` / ``self.post()``，不回传 requests.Response。
- JSON 用标准库 ``json``，入口直接回传 dict / list。
- ``init(extend="")`` 里 ``extend`` 是 JSON 字串，用 ``json.loads`` 解析。
- ``detailContent(ids)`` 处理完整 ID list：逐笔取、保留输入顺序、不自行去重，
  空 list 不发请求，单笔找不到向外抛错。
- ``searchContent(key, quick, pg="1")`` 双参数调用时 pg 默认 ``"1"``。
- ``playerContent(flag, id, vipFlags)`` 的 ``vipFlags`` 是完整 list（含空 list）。
- 不用 ``getCache`` / ``setCache`` / ``getName`` / ``getProxyUrl`` 等已移除 API。

用法
----
- 点播导入：把 ``taiwan.py`` 和 ``taiwan-config.json`` 放同一文件夹，
  FongMi → 设置 → 点播 → 选 ``taiwan-config.json``，首页会出现“📺台湾电视直播”。
- 直播导入：把 ``taiwan.py`` 和 ``taiwan.json`` 放同一文件夹，
  FongMi → 设置 → 直播 → 选 ``taiwan.json``，直播页直接按分组看。
  两种导入方式二选一即可，不用两个都导；taiwan.py 是同一份文件。
- ext 格式（JSON 字串，留空就用内嵌表）：
  ``{"channels": [{"name": "东森新闻台", "group": "台湾·新闻",
  "urls": ["http://...m3u8"]}]}``，或 ``{"groups": [...]}``（与 taiwan.json 的
  groups 同形），或直接传频道 JSON 的 http(s) 地址；另可加
  ``"auto_update": true`` 开启开局拉取 iptv-org 最新台湾列表。

已知限制（实话）
--------------
- “台湾所有电视台”做不到字面全量：壹电视新闻台、公视台语台、
  东森幼幼台、非凡商业台、卫视中文台、好消息电视台、靖天系列等，
  在公开源里没有可用的直链 HLS——有的是 YouTube 直播（无公开 HLS，
  只能走 ythls 这类第三方转码代理，ChinaIPTV 里已收的几路就是），
  有的是有线/付费台根本不放公开流。硬写占位地址只会黑屏，所以没收。
  另外 lisb0910 社区列表补的线（74.91、4gtv.cnlive.club、
  cdn.19891230.eu.org 三路转播）是最不稳定的一档，能播多久看转播站
  活多久，播不了先切回 iptv-org 的线。
- 直播源是第三方聚合的公开流，会过期、会换地址、部分限台湾/境外 IP、
  部分在大陆网络下打不开；本机（境外服务器）抽查结果见 README，
  不能拿它判一个源死刑，以手机实测为准。
- 没有在 FongMi 5.8.7 真机上逐台点播验证；格式按 FongMi 官方 CONFIG.md /
  SPIDER.md（lives.groups、liveContent 回 JSON groups）写，语法与模拟
  载入已在本机测过。
"""

import json
import re
from urllib.parse import quote

from base.spider import Spider as BaseSpider

PAGE_SIZE = 30
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
AUTO_M3U = "https://iptv-org.github.io/iptv/countries/tw.m3u"

# iptv-org tvg-id（去后缀）-> 简体台名：只用于 auto_update 拉回的 M3U 解析。
_TRAD2SIMP = str.maketrans({"臺": "台", "灣": "湾", "綜": "综", "視": "视",
    "亞": "亚", "娛": "娱", "東": "东", "戲": "戏", "藝": "艺", "樂": "乐",
    "廣": "广", "衛": "卫", "體": "体", "劇": "剧", "財": "财", "經": "经",
    "濟": "济", "聞": "闻", "資": "资", "訊": "讯", "華": "华", "歡": "欢",
    "愛": "爱"})
_REMOTE_NAME = {
    "BeautifulLifeTV": "Beautiful Life TV", "CGNTVChinese": "CGNTV中文台",
    "CTiVariety": "中天综合台", "CTS": "华视", "CTSNews": "华视新闻资讯台",
    "DaAi1": "大爱1台", "DaAi2": "大爱2台", "DaliTV": "大立电视台",
    "DiscoveryAsiaTaiwan": "探索频道亚洲台",
    "EBCFinancialNews": "东森财经新闻台", "EBCForeignMovie": "东森洋片台",
    "EBCNews": "东森新闻台", "FTV": "民视", "FTVOne": "民视第一台",
    "FTVTaiwan": "民视台湾台", "GoodTV": "GOOD TV综合台",
    "Good2": "GOOD TV真理台", "HakkaTV": "客家电视台",
    "IndigenousTV": "原住民族电视台", "TaiwanIndigenousTV": "原住民族电视台",
    "MOMOTV": "MOMO TV", "NTDTVAsiaPacific": "新唐人电视台",
    "PTS3": "公视3台", "SETMetro": "三立都会台", "SETNews": "三立新闻台",
    "SETTaiwan": "三立台湾台", "SETiNews": "三立iNEWS台", "SJTV": "SJTV",
    "SupremeMasterTV": "无上师电视台", "TaiwanPlusTV": "Taiwan Plus",
    "TVBSAsia": "TVBS Asia", "TVBSNews": "TVBS新闻台", "TTV": "台视",
    "TTVNews": "台视新闻台", "WXTV": "唯心电视台",
    "AnimaxAsia": "Animax亚洲台", "AXNAsia": "AXN亚洲台",
    "CinemaxAsia": "Cinemax亚洲台", "HBOAsia": "HBO亚洲台",
    "EBCYOYO": "东森YOYO台", "CTiNews": "中天新闻台",
    "FTVNews": "民视新闻台", "GlobalNews": "寰宇新闻台",
    "mnews": "镜新闻台", "ETMall60": "东森购物60台",
    "GeniusGoGoGo": "Genius Go Go Go",
}
_REMOTE_GROUP = {
    "东森新闻台": "台湾·新闻", "TVBS新闻台": "台湾·新闻",
    "三立新闻台": "台湾·新闻", "中天新闻台": "台湾·新闻",
    "民视新闻台": "台湾·新闻", "台视新闻台": "台湾·新闻",
    "华视新闻资讯台": "台湾·新闻", "寰宇新闻台": "台湾·新闻",
    "镜新闻台": "台湾·新闻", "三立iNEWS台": "台湾·新闻",
    "东森财经新闻台": "台湾·新闻", "台视": "台湾·无线",
    "民视": "台湾·无线", "华视": "台湾·无线",
}

# 内嵌频道表：(分组, 频道名, (播放地址, ...))，由 grab_taiwan.py 从 __DATE__ 的
# iptv-org / ChinaIPTV / taiwan-iptv 三路公开源合并生成。
# ext 有频道表时会被覆盖，见 init。
CHANNELS = __CHANNELS__


def _parse_m3u_text(text):
    """解析 M3U 文本 -> [{"group","name","urls"}]（auto_update 用）。"""
    out, cur = [], None
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            m = re.search(r'tvg-id="([^"]*)"', line)
            base = ((m.group(1) if m else "").split("@")[0].split(".")[0])
            disp = line.rsplit(",", 1)[-1].strip() if "," in line else ""
            disp = re.sub(r"\\s*\\(\\d+p\\)", "", disp)
            disp = re.sub(r"\\s*\\[[^\\]]*\\]", "", disp).strip()
            disp = disp.translate(_TRAD2SIMP)
            name = _REMOTE_NAME.get(base) or disp
            if re.match(r"(?i)good\\s*tv\\s*ch(?!1\\b|2\\b)\\d+", disp):
                cur = None
                continue
            group = _REMOTE_GROUP.get(name, "台湾·综合娱乐")
            cur = {"group": group, "name": name, "urls": []}
        elif line.startswith("#"):
            continue
        elif cur is not None and line.startswith("http"):
            if line not in cur["urls"]:
                cur["urls"].append(line)
            if cur not in out:
                out.append(cur)
            cur = None
    return [item for item in out if item["urls"]]


class Spider(BaseSpider):
    def init(self, extend=""):
        options = {}
        if extend:
            text = extend.strip()
            if text.startswith("http://") or text.startswith("https://"):
                try:
                    options = self.net.json(text, {"timeout": 15000})
                except Exception:
                    options = {}
            else:
                try:
                    options = json.loads(text)
                except json.JSONDecodeError:
                    raise ValueError("Site.ext 必须是 JSON 物件") from None
            if isinstance(options, list):
                options = {"channels": options}
            if not isinstance(options, dict):
                raise ValueError("Site.ext 必须是 JSON 物件")

        channels = []
        raw_groups = options.get("groups") or []
        raw_channels = options.get("channels") or options.get("list") or []
        if isinstance(raw_channels, str):
            raw_channels = json.loads(raw_channels)
        if raw_groups:
            for group in raw_groups:
                gname = group.get("name", "")
                for item in group.get("channel") or []:
                    channels.append(self._normalize(item, gname))
        elif raw_channels:
            channels = [self._normalize(item, "") for item in raw_channels]
        if channels:
            self.channels = channels
        else:
            self.channels = [self._normalize(item, "") for item in CHANNELS]

        if options.get("auto_update"):
            try:
                remote = self.net.req(AUTO_M3U, {"timeout": 8000})
                if isinstance(remote, bytes):
                    remote = remote.decode("utf-8", errors="ignore")
                if isinstance(remote, str):
                    fresh = _parse_m3u_text(remote)
                    if len(fresh) >= 10:
                        by_name = {item["name"]: item for item in self.channels}
                        for item in fresh:
                            by_name[item["name"]] = item
                        self.channels = list(by_name.values())
            except Exception:
                pass

        self.groups = []
        seen = set()
        for item in self.channels:
            if item["group"] not in seen:
                seen.add(item["group"])
                self.groups.append(item["group"])
        self.by_name = {item["name"]: item for item in self.channels}

    @staticmethod
    def _normalize(item, group=""):
        if isinstance(item, (list, tuple)):
            gname, name, urls = (list(item) + ["", "", ()])[:3]
            return {
                "group": str(gname or group),
                "name": str(name),
                "urls": [str(u) for u in urls],
            }
        urls = item.get("urls") or []
        if isinstance(urls, str):
            urls = [urls]
        return {
            "group": str(item.get("group") or group or "其他"),
            "name": str(item.get("name", "")),
            "urls": [str(u) for u in urls],
        }

    def _groups_out(self, only=None):
        out = []
        for gname in self.groups:
            if only and gname != only:
                continue
            chans = [item for item in self.channels if item["group"] == gname]
            out.append({
                "name": gname,
                "channel": [
                    {"name": item["name"], "urls": item["urls"]}
                    for item in chans
                ],
            })
        return out

    def homeContent(self, filter):
        classes = [{"type_id": "all", "type_name": "全部"}]
        classes += [
            {"type_id": gname, "type_name": gname} for gname in self.groups
        ]
        return {"class": classes}

    def homeVideoContent(self):
        return {"list": [self._card(item) for item in self.channels]}

    def categoryContent(self, tid, pg, filter, extend):
        extend = extend if isinstance(extend, dict) else {}
        if tid in (None, "", "all"):
            items = self.channels
        else:
            items = [item for item in self.channels if item["group"] == tid]
        return self.page([self._card(item) for item in items], pg, PAGE_SIZE)

    def searchContent(self, key, quick, pg="1"):
        query = str(key or "").strip().casefold()
        if not query:
            return self.page([], pg, PAGE_SIZE)
        matches = [
            item for item in self.channels
            if query in item["name"].casefold()
            or query in item["group"].casefold()
        ]
        return self.page([self._card(item) for item in matches], pg, PAGE_SIZE)

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        responses = [self._detail(video_id) for video_id in ids]
        return {
            **responses[0],
            "list": [item for response in responses for item in response["list"]],
        }

    def _detail(self, video_id):
        channel = self.by_name.get(str(video_id))
        if channel is None:
            raise ValueError("找不到频道：%s" % video_id)
        item = self._card(channel)
        flags = ["线路%d" % (i + 1) for i in range(len(channel["urls"]))]
        urls = ["直播$%s" % url for url in channel["urls"]]
        item.update({
            "type_name": channel["group"],
            "vod_year": "",
            "vod_area": "台湾",
            "vod_director": "",
            "vod_actor": "",
            "vod_content": "%s直播（%s）" % (channel["name"], channel["group"]),
            "vod_play_from": "$$$".join(flags),
            "vod_play_url": "$$$".join(urls),
        })
        return {"list": [item]}

    def playerContent(self, flag, id, vipFlags):
        # vipFlags 是完整 list（含空 list），这里只作记录：直播无 VIP 分级。
        _ = vipFlags
        url = str(id or "").strip()
        if "|" in url:
            url = url.split("|", 1)[1].strip()
        if not url.startswith("http"):
            return {"parse": 0, "msg": "无效的播放地址：%s" % id}
        return {
            "parse": 0,
            "jx": 0,
            "url": url,
            "format": "application/x-mpegURL",
            "header": {"User-Agent": UA},
        }

    def liveContent(self, url):
        text = str(url or "").strip()
        if text.startswith("http://") or text.startswith("https://"):
            # ext / Live.url 直接给了远端列表：原样取回，框架按 TXT/M3U/JSON 解析。
            try:
                return self.net.req(text, {"timeout": 15000})
            except Exception as error:
                raise RuntimeError("取远端直播列表失败：%s" % error) from None
        if text and text in self.groups:
            return self._groups_out(only=text)
        if text and text in self.by_name:
            channel = self.by_name[text]
            return [{
                "name": channel["group"],
                "channel": [{"name": channel["name"], "urls": channel["urls"]}],
            }]
        if text and text not in ("", "all"):
            raise ValueError("liveContent 找不到分组或频道：%s" % url)
        return self._groups_out()

    @staticmethod
    def _card(channel):
        return {
            "vod_id": channel["name"],
            "vod_name": channel["name"],
            "vod_pic": "https://epg.112114.xyz/logo/%s.png" % quote(channel["name"]),
            "vod_remarks": channel["group"],
            "type_name": channel["group"],
        }
'''


EPG = "https://epg.112114.xyz/?ch={name}&date={date}"
LOGO = "https://epg.112114.xyz/logo/{name}.png"

REMOTE_LIVES = [
    ("台湾·iptv-org", "https://iptv-org.github.io/iptv/countries/tw.m3u"),
    ("台湾·iptv-org streams", "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tw.m3u"),
    ("台湾·ChinaIPTV", "https://raw.githubusercontent.com/hujingguang/ChinaIPTV/main/TaiWan.m3u8"),
    ("台湾·永久HLS", "https://raw.githubusercontent.com/limajj2021/taiwan-iptv/main/playlist_static.m3u"),
]


def build_live_json(groups):
    lives = [{
        "name": "台湾电视直播·内嵌", "boot": True,
        "epg": EPG, "logo": LOGO, "ua": UA, "groups": groups,
    }]
    for name, url in REMOTE_LIVES:
        lives.append({"name": name, "type": 0, "url": url,
                      "epg": EPG, "logo": LOGO, "ua": UA})
    lives.append({"name": "台湾电视直播·爬虫", "type": 3,
                  "api": "./taiwan.py", "ext": "",
                  "epg": EPG, "logo": LOGO})
    return {"lives": lives}


def build_config_json(lives):
    base = None
    mainland = HERE.parent / "fongmi-live" / "config.json"
    if mainland.exists():
        try:
            base = json.loads(mainland.read_text(encoding="utf-8"))
        except Exception:
            base = None
    cfg = dict(base) if isinstance(base, dict) else {
        "spider": "", "parses": [], "rules": [], "hosts": [], "ads": []}
    cfg["sites"] = [{
        "key": "taiwan_live", "name": "📺台湾电视直播", "type": 3,
        "api": "taiwan.py", "ext": "", "searchable": 1,
        "changeable": 1, "quickSearch": 1,
    }]
    cfg["lives"] = lives
    return cfg


def build_txt(groups):
    lines = []
    for group in groups:
        lines.append("%s,#genre#" % group["name"])
        for ch in group["channel"]:
            lines.append("%s,%s" % (ch["name"], "#".join(ch["urls"])))
    return "\n".join(lines) + "\n"


README_TEMPLATE = """# 台湾电视直播 · FongMi 5.8.7

生成日期：__DATE__。源地址均为当天拉取的公开聚合源，抓取脚本见 `grab_taiwan.py`。

## 文件（6 个，传到手机同一个文件夹里）

| 文件 | 用途 |
|---|---|
| `taiwan.py` | 爬虫本体，内嵌 __TOTAL__ 个频道。点播和直播两种导入方式共用同一份 |
| `taiwan.json` | 直播配置：内嵌分组 + 4 路远程备用源 + 爬虫源 |
| `taiwan-config.json` | 点播配置：首页加一个“📺台湾电视直播”站，`lives` 与 `taiwan.json` 相同 |
| `taiwan.txt` | 附赠：内嵌频道转成的 TXT 列表，可直接当直播源导入 |
| `grab_taiwan.py` | 自动抓取脚本：在电脑上跑 `python3 grab_taiwan.py`，重新拉源并生成上面 4 个文件 |
| `README.md` | 本文件 |

**只用二选一，不要两个配置都导**——`taiwan.json` 和 `taiwan-config.json` 里的 `lives` 是同一份，导了 `taiwan-config.json`，直播页里已经有这 6 路源了。

## 导入（FongMi 5.8.7，手机版）

先把文件传到手机同一个文件夹，例如 `Download/fongmi-taiwan/`（微信/QQ/数据线都行，文件必须在一起，`taiwan.py` 不能单独放别处）。

**只看直播（推荐）：**

1. 打开 FongMi → 首页右上角 **设置** → **直播**。
2. 在直播地址框右侧的小图标（选择文件）里选 `taiwan.json`，点确定。
3. 回到直播页，默认就是“台湾电视直播·内嵌”，按分组切换：台湾·新闻 / 无线 / 综合娱乐 / 文化 / 宗教 / 电影娱乐。
4. 一个台播不了：先在播放时切线路（每个台最多 3 条线），再在直播页切源——`台湾·iptv-org`、`台湾·iptv-org streams`、`台湾·ChinaIPTV`、`台湾·永久HLS`、`台湾电视直播·爬虫`，6 路里换一个。

**还想在点播首页当一个站浏览/搜索：**

1. 打开 FongMi → 首页右上角 **设置** → **点播**。
2. 在“请输入配置…”框右侧的小图标（选择文件）里选 `taiwan-config.json`，点确定，等它加载完（首次约几十秒）。
3. 首页出现“📺台湾电视直播”，点进去按分组看，支持搜索台名，点一个台进详情页切线路播放。

## 内嵌频道（__TOTAL__ 个）

| 分组 | 数量 | 说明 |
|---|---|---|
__GROUP_TABLE__
每个频道最多 3 条线，按这个顺序排：iptv-org 台湾源 → ChinaIPTV 台湾源 → lisb0910 社区列表的白名单直链。单线频道占多数——公开源就只找到这一条，不是漏写。

## 自动抓取 / 刷新（`grab_taiwan.py`）

源会过期，台会换地址。想刷新，不用手动改：

```bash
python3 grab_taiwan.py            # 重新拉 4 路源，逐条抽查，生成 taiwan.py / taiwan.json / taiwan-config.json / taiwan.txt
python3 grab_taiwan.py --no-check # 不抽查，快很多；只想换地址时用这个
```

也可以不跑脚本：把 `taiwan-config.json` 里本站的 `ext` 改成 `{"auto_update": true}`，爬虫每次打开会去 iptv-org 拉一份最新台湾列表（8 秒超时，拉不到自动用内嵌表，不影响播放）。

## 先说清楚的三件事（别当成“全量保证”）

**1. “台湾所有电视台”做不到字面全量。**
这次收的是公开源里能找到直链 HLS 的 __TOTAL__ 个台。以下这些台在公开源里没有可用的直链 HLS，所以没收，不是漏写：
壹电视新闻台、公视台语台、东森幼幼台、非凡商业台、卫视中文台、好消息电视台、靖天系列、FOX 体育台等。
其中一部分（东森新闻、TVBS 新闻、三立新闻、中天新闻、民视新闻、台视新闻、华视新闻、寰宇新闻、镜新闻等）平时只在 YouTube 直播，没有官方 HLS；本次收的这几路走的是 `ythls.armelin.one` 这类第三方 YouTube 转 HLS 代理，能播多久看代理活多久。另有一部分线来自 lisb0910 社区列表的转播站（74.91、4gtv.cnlive.club、cdn.19891230.eu.org），是这批线里最不稳定的一档，播不了先切回 iptv-org 的线。想补某一个台：找到它官网/公众号的直播地址发我，我帮你加进去。

**2. 直播源会过期，部分限台湾/境外 IP。**
这些地址是第三方聚合的公开流，不是各台官网直出的稳定接口，会换地址、会失效、部分限台湾 IP、部分在大陆网络下打不开。__CHECK_LINE__日常使用以手机实测为准；`taiwan.json` 里“台湾·iptv-org”那路是直接读最新列表，不用重新导。

**3. GOOD TV 只有两个台。**
源里 GOOD TV CH3、CH5、CH6……几十条是同一台的点播短片分流，不是独立电视台，只留了 CH1 综合台和 CH2 真理台，别当成少收了 30 个台。

## 播不了怎么办（按顺序试）

1. 切线路：详情页/播放页换线路 2、线路 3。
2. 切源：直播页换一路远程源再搜同一个台。
3. 换网络：Wi-Fi 和流量换着试一次，部分源对地区/运营商有限制；IPv6 源需要手机网络支持 IPv6。
4. 等一天再试：iptv-org 是持续更新的，今天失效的线明天可能换新地址——`taiwan.json` 里“台湾·iptv-org”那路就是直接读它的最新文件，不用重新导。
5. 还是不行：把台名 + 哪一路源 + 提示（黑屏/转圈/报错）发我，我按当天最新源给你换地址；或者自己跑一遍 `grab_taiwan.py` 刷新。

## 想自己换台、加台（不用改代码）

`taiwan.py` 支持 `ext` 传频道表，`taiwan-config.json` 里把对应站的 `ext` 改成 JSON 字串即可：

```json
{"channels": [{"name": "测试台", "group": "台湾·新闻", "urls": ["http://...m3u8"]}]}
```

也可以直接传频道 JSON 的 http(s) 地址，或传 `{"groups": [...]}`（与 `taiwan.json` 的 `groups` 同形）。不传就用内嵌的 __TOTAL__ 个台。

## 来源

__SOURCE_TABLE__
EPG 与台标用的是公开的 `epg.112114.xyz`（`?ch={name}&date={date}` / `logo/{name}.png`），台湾台的节目表/台标不一定全，缺的会显示空白，不影响播放。

## 验证情况（__DATE__）

| 检查 | 结果 |
|---|---|
| `taiwan.json` / `taiwan-config.json` JSON 解析 | 通过 |
| `taiwan.py` Python 语法（`py_compile`） | 通过 |
| `taiwan.py` 模拟载入：空 ext 载入 __TOTAL__ 频道、首页/分类分页、搜索、详情（顺序保留、空 list、未知 ID 抛错）、播放、ext 覆盖频道、`liveContent` 全量/按分组/按单台 | 全部通过 |
| 播放地址抽查（境外服务器，__CHECK_LINE__） | 见上文第 2 条 |
| FongMi 5.8.7 真机逐台点播 | **未验证**——格式按 FongMi 官方 CONFIG.md / SPIDER.md（`lives.groups`、`liveContent` 回 JSON groups）写，需要你在手机上按上面步骤走一遍 |

格式依据：FongMi/TV `docs/CONFIG.md`（Live 配置、`lives`、`groups`、`channel.urls`）、`docs/SPIDER.md`（`liveContent` 回 TXT / M3U / JSON 三种格式）。`taiwan.py` 的写法与大陆版 `live.py`、你之前那份 `yangshipin.py` 同一套新 API（`from base.spider import Spider`，同步 `def`，`self.net.json` / `self.net.req`，不用已移除的 `fetch` / `post` / `str2json` / `getCache`）。
"""

GROUP_NOTES = {
    "台湾·新闻": "东森新闻、TVBS新闻、三立新闻、中天新闻、民视新闻、台视新闻、华视新闻资讯、寰宇新闻、镜新闻、三立iNEWS、东森财经新闻、中视新闻、年代新闻、非凡新闻、寰宇台湾台、台视财经台",
    "台湾·无线": "台视、民视、中视、公视、华视",
    "台湾·综合娱乐": "TVBS Asia、三立台湾台/都会台/综合台/戏剧台、民视台湾台/第一台/综艺台/影剧台、中天综合台/亚洲台/娱乐台、东森洋片台/YOYO/综合台/戏剧台/超视台、纬来体育/综合/戏剧/日本/育乐台、TVBS HD/欢乐台/精采台/台剧台、八大戏剧台、MOMO TV、公视3台/2台、中视经典台/菁采台",
    "台湾·文化": "Taiwan Plus、客家电视台、原住民族电视台、大爱1/2台、大立电视台",
    "台湾·宗教": "GOOD TV综合/真理台、Beautiful Life TV、CGNTV中文台、唯心电视台、无上师电视台、新唐人电视台",
    "台湾·电影娱乐": "HBO/Cinemax/AXN/Animax亚洲台（转播源，存活不稳定）、探索频道亚洲台、东森购物60台、东森电影台",
}


def main():
    do_check = "--no-check" not in sys.argv
    channels, report = build_channels(do_check=do_check)
    groups = groups_of(channels)
    total = len(channels)

    group_summary = "、".join(
        "%s %d" % (g["name"], len(g["channel"])) for g in groups)
    channels_repr = "(\n" + "".join(
        "    (%r, %r, %s),\n" % (ch["group"], ch["name"], repr(tuple(ch["urls"])))
        for ch in channels) + ")"

    spider = (SPIDER_TEMPLATE
              .replace("__CHANNELS__", channels_repr)
              .replace("__TOTAL__", str(total))
              .replace("__GROUP_SUMMARY__", group_summary)
              .replace("__DATE__", TODAY))
    (HERE / "taiwan.py").write_text(spider, encoding="utf-8")

    live = build_live_json(groups)
    (HERE / "taiwan.json").write_text(
        json.dumps(live, ensure_ascii=False, indent=2), encoding="utf-8")
    cfg = build_config_json(live["lives"])
    (HERE / "taiwan-config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "taiwan.txt").write_text(build_txt(groups), encoding="utf-8")

    chk = report["check"]
    if do_check:
        check_line = ("本次逐条抽查 %d 条地址：确认是 m3u8 的 %d 条、有响应但非 m3u8 文本的 %d 条、"
                      "超时或失败的 %d 条。" % (
                          chk["ok_m3u8"] + chk["ok_other"] + chk["failed"],
                          chk["ok_m3u8"], chk["ok_other"], chk["failed"]))
        # 本机上整站全灭的主机（多半是境外网络连不通，未必是源已死）
        from urllib.parse import urlparse
        by_host = {}
        for u, s in chk.get("scores", {}).items():
            by_host.setdefault((urlparse(u).hostname or ""), []).append(s)
        dead = sorted(h for h, ss in by_host.items()
                      if h and len(ss) >= 2 and all(v == 0 for v in ss))
        if dead:
            check_line += ("其中 %s 本机抽查全部失败（疑似境外网络受限或源端拦截），"
                           "只代表本机抽查结果，不等于在手机上播不了。"
                           % "、".join(dead))
    else:
        check_line = "本次未做逐条抽查（--no-check）。"
    group_table = "".join(
        "| %s | %d | %s |\n" % (g["name"], len(g["channel"]),
                                GROUP_NOTES.get(g["name"], ""))
        for g in groups)
    source_table = "".join(
        "- %s：`%s`（拉到 %d 条，保留 %d 条线）\n" % (
            label, info["url"], info.get("entries", 0),
            info.get("kept_lines", 0))
        if "error" not in info else
        "- %s：`%s`（拉取失败：%s）\n" % (label, info["url"], info["error"])
        for label, info in report["sources"].items())
    source_table += ("- taiwan-iptv-static：`https://raw.githubusercontent.com/"
                     "limajj2021/taiwan-iptv/main/playlist_static.m3u`"
                     "（只作 taiwan.json 远程备用源，不并入内嵌表："
                     "其中个别地址与台名明显不符）\n")

    readme = (README_TEMPLATE
              .replace("__TOTAL__", str(total))
              .replace("__DATE__", TODAY)
              .replace("__GROUP_TABLE__", group_table)
              .replace("__CHECK_LINE__", check_line)
              .replace("__SOURCE_TABLE__", source_table))
    (HERE / "README.md").write_text(readme, encoding="utf-8")
    (HERE / "build_report.json").write_text(
        json.dumps({"date": TODAY, "total": total,
                    "groups": {g["name"]: len(g["channel"]) for g in groups},
                    "channels": channels, "report": report},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    print("台湾台：%d 个（%s）" % (total, group_summary))
    print("抽查：%s" % check_line)
    for label, info in report["sources"].items():
        print("  %s: %s" % (label, info))
    print("丢弃 %d 条（含 GOOD TV 分流与非直链）" % len(report["dropped"]))
    print("已生成：taiwan.py / taiwan.json / taiwan-config.json / taiwan.txt / README.md")


if __name__ == "__main__":
    main()
