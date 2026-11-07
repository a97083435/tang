"""台湾电视直播 —— FongMi / TVBox Python 爬虫（CatVodSpider 新写法）。

频道
----
- 内嵌 73 个频道，分组：台湾·新闻 16、台湾·无线 5、台湾·综合娱乐 33、台湾·文化 6、台湾·宗教 7、台湾·电影娱乐 6。
  （分组计数以生成时为准，见 README；频道名全局唯一，可直接当 vod_id。）
- 每个频道最多 3 条线：先 iptv-org 台湾源，再 ChinaIPTV 台湾源，
  再 lisb0910 社区列表的白名单直链。单线频道占多数——公开源就是这样，
  播不了先切线路，再切 taiwan.json 里的远程备用源。

来源（2026-11-07 拉取，见 grab_taiwan.py）
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

# 内嵌频道表：(分组, 频道名, (播放地址, ...))，由 grab_taiwan.py 从 2026-11-07 的
# iptv-org / ChinaIPTV / taiwan-iptv 三路公开源合并生成。
# ext 有频道表时会被覆盖，见 init。
CHANNELS = (
    ('台湾·新闻', '东森新闻台', ('http://4gtv.cnlive.club/channel/n5ca63a3a/index.m3u8', 'http://seb.sason.top/sc/dsxw_fhd.m3u8')),
    ('台湾·新闻', 'TVBS新闻台', ('http://seb.sason.top/sc/tvbsxw_fhd.m3u8',)),
    ('台湾·新闻', '三立新闻台', ('http://seb.sason.top/sc/sllive_fhd.m3u8',)),
    ('台湾·新闻', '中天新闻台', ('http://4gtv.cnlive.club/channel/3824d067/index.m3u8', 'http://74.91.26.218:82/live/ztxw.m3u8')),
    ('台湾·新闻', '民视新闻台', ('http://38.64.72.148/hls/modn/list/4012/playlist.m3u8', 'https://ythls.armelin.one/channel/UC2VmWn8dAqkzlQqvy02E1PA.m3u8', 'http://74.91.26.218:82/live/ftvnews.m3u8')),
    ('台湾·新闻', '台视新闻台', ('https://live.wcetv.com/hls/master-ttvnews.m3u8', 'https://ythls.armelin.one/channel/UC8ROUUjHzEQm-ndb69CX8Ww.m3u8', 'http://74.91.26.218:82/live/ttvnews.m3u8')),
    ('台湾·新闻', '华视新闻资讯台', ('http://4gtv.cnlive.club/channel/n692bc32c/index.m3u8', 'http://seb.sason.top/sc/hsxw_fhd.m3u8', 'http://74.91.26.218:82/live/ctsnews.m3u8?zbj')),
    ('台湾·新闻', '寰宇新闻台', ('http://4gtv.cnlive.club/channel/n4da4274/index.m3u8',)),
    ('台湾·新闻', '镜新闻台', ('http://4gtv.cnlive.club/channel/351c8485/index.m3u8', 'https://ythls.armelin.one/channel/UC4LjkybVKXCDlneVXlKAbmw.m3u8', 'https://cdn.19891230.eu.org/4gtv/4gtv-4gtv075/index.m3u8')),
    ('台湾·新闻', '三立iNEWS台', ('http://4gtv.cnlive.club/channel/4fa717ad/index.m3u8', 'https://ythls.armelin.one/channel/UCoNYj9OFHZn3ACmmeRCPwbA.m3u8')),
    ('台湾·新闻', '东森财经新闻台', ('http://4gtv.cnlive.club/channel/57ce2e74/index.m3u8', 'http://seb.sason.top/sc/dscjxw_fhd.m3u8')),
    ('台湾·新闻', '中视新闻台', ('http://74.91.26.218:82/live/ctvnews.m3u8?zbj', 'http://74.91.26.218:82/live/ctvnews.m3u8')),
    ('台湾·新闻', '年代新闻台', ('https://cdn.19891230.eu.org/api/Era-News/index.m3u8',)),
    ('台湾·新闻', '非凡新闻台', ('http://74.91.26.218:82/live/feifannews.m3u8', 'https://cdn.19891230.eu.org/4gtv/media-live010/index.m3u8')),
    ('台湾·新闻', '寰宇台湾台', ('http://4gtv.cnlive.club/channel/n37458587/index.m3u8',)),
    ('台湾·新闻', '台视财经台', ('http://74.91.26.218:82/live/ttvcj.m3u8', 'http://74.91.26.218:82/live/ttvcj.m3u8?zbj')),
    ('台湾·无线', '台视', ('http://162.19.247.76:22222/live/taishi/index.m3u8', 'http://74.91.26.218:82/live/ttvzh.m3u8', 'http://74.91.26.218:82/live/ttv.m3u8')),
    ('台湾·无线', '民视', ('http://seb.sason.top/ptv/ftv.php?id=ms', 'http://74.91.26.218:82/live/ftv.m3u8?zbj', 'http://74.91.26.218:82/live/ftv.m3u8')),
    ('台湾·无线', '中视', ('http://74.91.26.218:82/live/ctv.m3u8',)),
    ('台湾·无线', '公视', ('http://74.91.26.218:82/live/pts.m3u8?zbj',)),
    ('台湾·无线', '华视', ('https://cdn.19891230.eu.org/4gtv/4gtv-4gtv041/index.m3u8', 'http://74.91.26.218:82/live/cts.m3u8')),
    ('台湾·综合娱乐', 'TVBS Asia', ('http://38.64.72.148/hls/modn/list/4005/playlist.m3u8',)),
    ('台湾·综合娱乐', '三立台湾台', ('http://sanlihalive1-a.akamaihd.net/5ffd3a166f7241d9b489b7d7241db96f/ap-northeast-1/4338955585001/profile_0/chunklist.m3u8?hdnea=st=1664042391~exp=9007200918783382~acl=/5ffd3a166f7241d9b489b7d7241db96f/*/profile_0/chunklist.m3u8*~hmac=29538a1877a3c3728afe61bcd55b5a7b98f517bb3e2c75f8433b9338fda5b3e3',)),
    ('台湾·综合娱乐', '三立都会台', ('http://sanlihalive1-a.akamaihd.net/4c3bb0ccad574d0e9b507c2dcd2dfabc/ap-northeast-1/4338955585001/profile_0/chunklist.m3u8?hdnea=st=1664042191~exp=9007200918783182~acl=/4c3bb0ccad574d0e9b507c2dcd2dfabc/*/profile_0/chunklist.m3u8*~hmac=957e95920f87270a35afde9e5bd3d25c96af4c19596f0f2cc44ff968b89165c1',)),
    ('台湾·综合娱乐', '民视台湾台', ('http://seb.sason.top/ptv/ftv.php?id=tw', 'http://74.91.26.218:82/live/ftvtw.m3u8?zbj', 'http://74.91.26.218:82/live/ftvtw.m3u8')),
    ('台湾·综合娱乐', '民视第一台', ('http://4gtv.cnlive.club/channel/nc56ba28/index.m3u8', 'http://seb.sason.top/ptv/ftv.php?id=dy', 'http://74.91.26.218:82/live/ftvdy.m3u8')),
    ('台湾·综合娱乐', '中天综合台', ('http://23.237.10.66:16372', 'https://cdn.19891230.eu.org/api/Cti-K/index.m3u8')),
    ('台湾·综合娱乐', '东森洋片台', ('http://111.59.139.85:11888/tsfile/live/1217_1.m3u8?key=txiptv', 'https://cdn.19891230.eu.org/api/ET-Foreign-Movie-Channel/index.m3u8')),
    ('台湾·综合娱乐', '东森YOYO台', ('https://ythls.armelin.one/channel/UCiWRSesvSYmY7YOyz0tv_zQ.m3u8',)),
    ('台湾·综合娱乐', 'MOMO TV', ('http://nmk.ioapk.com:5050/4gtv-live107/index.m3u8',)),
    ('台湾·综合娱乐', '公视3台', ('http://111.59.139.85:11888/tsfile/live/1222_1.m3u8?key=txiptv',)),
    ('台湾·综合娱乐', 'SJTV', ('http://111.59.139.85:11888/tsfile/live/1220_1.m3u8?key=txiptv',)),
    ('台湾·综合娱乐', '三立综合台', ('http://4gtv.cnlive.club/channel/45c7d3e3/index.m3u8',)),
    ('台湾·综合娱乐', '三立戏剧台', ('http://61.221.215.25:8800/hls/41/index.m3u8',)),
    ('台湾·综合娱乐', '中天亚洲台', ('https://cdn.19891230.eu.org/api/Cti-I/index.m3u8',)),
    ('台湾·综合娱乐', '中天娱乐台', ('https://cdn.19891230.eu.org/api/Cti-E/index.m3u8',)),
    ('台湾·综合娱乐', 'TVBS HD', ('http://4gtv.cnlive.club/channel/58f128b2/index.m3u8', 'http://38.64.72.148/hls/modn/list/4005/chunklist1.m3u8', 'http://38.64.72.148:80/hls/modn/list/4005/chunklist1.m3u8')),
    ('台湾·综合娱乐', 'TVBS欢乐台', ('http://4gtv.cnlive.club/channel/498f035d/index.m3u8',)),
    ('台湾·综合娱乐', 'TVBS精采台', ('https://cdn.19891230.eu.org/4gtv/4gtv-4gtv067/index.m3u8',)),
    ('台湾·综合娱乐', 'TVBS台剧台', ('http://4gtv.cnlive.club/channel/49342c47/index.m3u8',)),
    ('台湾·综合娱乐', '东森综合台', ('https://cdn.19891230.eu.org/api/ET-Variety-Channel/index.m3u8',)),
    ('台湾·综合娱乐', '东森戏剧台', ('https://cdn.19891230.eu.org/api/ET-Drama-Channel/index.m3u8',)),
    ('台湾·综合娱乐', '东森超视台', ('http://38.64.72.148:80/hls/modn/list/2013/chunklist1.m3u8',)),
    ('台湾·综合娱乐', '民视综艺台', ('http://4gtv.cnlive.club/channel/nc46cff5/index.m3u8',)),
    ('台湾·综合娱乐', '民视影剧台', ('https://cdn.19891230.eu.org/4gtv/litv-ftv09/index.m3u8',)),
    ('台湾·综合娱乐', '纬来体育台', ('https://cdn.19891230.eu.org/api/VL-Sports/index.m3u8',)),
    ('台湾·综合娱乐', '纬来综合台', ('https://cdn.19891230.eu.org/api/VL-ONTV/index.m3u8',)),
    ('台湾·综合娱乐', '纬来戏剧台', ('https://cdn.19891230.eu.org/api/VL-Drama/index.m3u8',)),
    ('台湾·综合娱乐', '纬来日本台', ('https://cdn.19891230.eu.org/api/VL-Japan/index.m3u8',)),
    ('台湾·综合娱乐', '纬来育乐台', ('https://cdn.19891230.eu.org/api/VL-E/index.m3u8',)),
    ('台湾·综合娱乐', '八大戏剧台', ('http://61.221.215.25:8800/hls/39/index.m3u8',)),
    ('台湾·综合娱乐', '中视经典台', ('http://74.91.26.218:82/live/ctvjd.m3u8',)),
    ('台湾·综合娱乐', '中视菁采台', ('http://74.91.26.218:82/live/ctvjc.m3u8?zbj',)),
    ('台湾·综合娱乐', '公视2台', ('http://74.91.26.218:82/live/ptsse.m3u8',)),
    ('台湾·文化', 'Taiwan Plus', ('https://bcovlive-a.akamaihd.net/rce33d845cb9e42dfa302c7ac345f7858/ap-northeast-1/6282251407001/playlist.m3u8',)),
    ('台湾·文化', '客家电视台', ('https://h5cul1yar48um3t.wcetv.com/hls/hakkatv.m3u8',)),
    ('台湾·文化', '原住民族电视台', ('https://streamipcfapp.akamaized.net/live/_definst_/live_720/key_b1500.m3u8', 'http://streamipcf.akamaized.net/live/_definst_/smil:liveabr.smil/playlist.m3u8')),
    ('台湾·文化', '大爱1台', ('https://pulltv1.wanfudaluye.com/live/tv1.m3u8',)),
    ('台湾·文化', '大爱2台', ('http://nmk.ioapk.com:5050/4gtv-live106/index.m3u8', 'https://pulltv2.wanfudaluye.com/live/tv2.m3u8')),
    ('台湾·文化', '大立电视台', ('http://www.dalitv.com.tw:4568/live/dali/index.m3u8',)),
    ('台湾·宗教', 'GOOD TV综合台', ('https://live.streamingfast.net/osmflivech1.m3u8',)),
    ('台湾·宗教', 'GOOD TV真理台', ('https://live.streamingfast.net/osmflivech2.m3u8',)),
    ('台湾·宗教', 'Beautiful Life TV', ('https://5ddce30eb4b55.streamlock.net/bltvhd/bltv1/playlist.m3u8',)),
    ('台湾·宗教', 'CGNTV中文台', ('https://d3e05csss9c272.cloudfront.net/out/v1/f0bf71c57581470fb9379f603e8f5d83/CGNWebLiveCN.m3u8',)),
    ('台湾·宗教', '唯心电视台', ('https://mobile.ccdntech.com/transcoder/_definst_/vod164_Live/live/chunklist_w1177047531.m3u8',)),
    ('台湾·宗教', '无上师电视台', ('https://lbs-us1.suprememastertv.com/720p.m3u8',)),
    ('台湾·宗教', '新唐人电视台', ('https://live.ntdtv.com/aplive200/playlist.m3u8',)),
    ('台湾·电影娱乐', 'HBO亚洲台', ('http://125.227.210.55:1003/VideoInput/play.ts',)),
    ('台湾·电影娱乐', 'Cinemax亚洲台', ('http://125.227.210.55:1001/VideoInput/play.ts',)),
    ('台湾·电影娱乐', 'AXN亚洲台', ('http://125.227.210.55:4050/VideoInput/play.ts',)),
    ('台湾·电影娱乐', 'Animax亚洲台', ('http://125.227.210.55:3056/VideoInput/play.ts',)),
    ('台湾·电影娱乐', '探索频道亚洲台', ('http://125.227.210.55:1004/VideoInput/play.ts',)),
    ('台湾·电影娱乐', '东森电影台', ('https://cdn.19891230.eu.org/api/ET-Movie/index.m3u8',)),
)


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
            disp = re.sub(r"\s*\(\d+p\)", "", disp)
            disp = re.sub(r"\s*\[[^\]]*\]", "", disp).strip()
            disp = disp.translate(_TRAD2SIMP)
            name = _REMOTE_NAME.get(base) or disp
            if re.match(r"(?i)good\s*tv\s*ch(?!1\b|2\b)\d+", disp):
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
