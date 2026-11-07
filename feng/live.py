"""中国电视直播 —— FongMi / TVBox Python 爬虫（CatVodSpider 新写法）。

频道
----
- 内嵌 271 个频道，7 个分组：中央·央视 25、中央·风云/付费 15、
  省级卫视 38、省级地面 38、市级电视台 76、县级电视台 73、港澳台 6。
  （分组计数以生成时为准，见 README；频道名全局唯一，可直接当 vod_id。）
- 每个频道最多 3 条线：先 best-fan 每日更新源，再 YueChan 湖南运营商源，
  再 iptv-org 中国源。单线频道占多数——公开源就是这样，播不了先切线路，
  再切 live.json 里的远程备用源。

来源（2026-11-07 拉取）
-----------------------
- best-fan/iptv-sources：cn_cctv.m3u8、cn_province.m3u8（2026-11-07 05:25 生成）
- YueChan/Live：Hunan.txt（39.134 运营商 PLTV）
- iptv-org/iptv：streams/cn.m3u（市/县/港澳台主要靠它）
- hujingguang/ChinaIPTV：cnTV_AutoUpdate.m3u8（港澳台备用）

写法规范（对照随附的《Python 爬虫旧 API 迁移》与 yangshipin.py）
----------------------------------------------------------------
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
- 点播导入：把 ``live.py`` 和 ``config.json`` 放同一文件夹，
  FongMi → 设置 → 点播 → 选 ``config.json``，首页会出现“📺中国电视直播”。
- 直播导入：把 ``live.py`` 和 ``live.json`` 放同一文件夹，
  FongMi → 设置 → 直播 → 选 ``live.json``，直播页直接按分组看。
  两种导入方式二选一即可，不用两个都导；live.py 是同一份文件。
- ext 格式（JSON 字串，留空就用内嵌表）：
  ``{"channels": [{"name": "CCTV1", "group": "中央·央视",
  "urls": ["http://...m3u8"]}]}``，或 ``{"groups": [...]}``（与 live.json 的
  groups 同形），或直接传频道 JSON 的 http(s) 地址。

已知限制（实话）
--------------
- “所有县台”做不到字面全量：中国 2800 多个县（市、区），绝大多数县台
  没有公开互联网直播流，只有本地有线/IPTV 组播。本文件收的是能从公开源
  找到流的 71 个县台 + 71 个市台，剩下的县台请走 live.json 里
  “中国·iptv-org”“央视卫视·每日更新”等远程聚合源，或等当地台放出公开流。
- 直播源是第三方聚合的公开流，会过期、会换地址、部分限中国大陆 IP、
  部分 39.134 段运营商源在境外网络下会超时——在本机（非大陆 IP）抽查时
  39.134 段确实超时，59.39 段回 200，74.91 段回 302。手机在大陆网络下
  播放率会高很多，不能拿境外服务器的抽查结果判一个源死刑。
- CCTV卫生健康频道在 4 个公开源里都没找到流，这次没收录，别当它漏了。
- 没有在 FongMi 5.8.7 真机上逐台点播验证；格式按 FongMi 官方 CONFIG.md /
  SPIDER.md（lives.groups、liveContent 回 JSON groups）写，语法与模拟
  载入已在本机测过。

ext 之外想换源不用改代码：live.json 里 5 路远程源可直接在直播页切换。
"""

import json
from urllib.parse import quote

from base.spider import Spider as BaseSpider

PAGE_SIZE = 30
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# 内嵌频道表：(分组, 频道名, (播放地址, ...))，由 build 脚本从 2026-11-07 的
# best-fan / YueChan-Hunan / iptv-org / ChinaIPTV 四路公开源合并生成。
# ext 有频道表时会被覆盖，见 init。
CHANNELS = (
    ('中央·央视', 'CCTV1', ('http://222.223.41.27:8888/hls/1/index.m3u8', 'http://74.91.26.218:82/live/cctv1hd.m3u8', 'http://173.208.234.146/live/cctv1.m3u8',)),
    ('中央·央视', 'CCTV2', ('https://p2.bdstatic.com/rtmp.liveshow.lss-user.baidubce.com/live/stream_bduid_6488563992_8982723413/merged_1707497046297_88536_25144_41936.m3u8', 'http://116.128.243.121:85/tsfile/live/0002_1.m3u8?key=txiptv&playlive=0&authid=0', 'http://74.91.26.218:82/live/cctv2hd.m3u8',)),
    ('中央·央视', 'CCTV3', ('http://74.91.26.218:82/live/cctv3hd.m3u8', 'http://113.57.140.161:10081/newlive/live/hls/3/live.m3u8', 'http://119.129.172.127:9901/tsfile/live/0003_1.m3u8?key=txiptv&playlive=1&authid=0',)),
    ('中央·央视', 'CCTV4', ('http://58.56.162.102:4466/newlive/live/hls/4/live.m3u8', 'http://113.90.154.189:9901/tsfile/live/0004_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://45.192.97.170:8880/play/392.m3u8',)),
    ('中央·央视', 'CCTV5', ('http://183.129.255.66:8480/hls/5/index.m3u8', 'http://107.150.60.122/live/cctv5hd.m3u8', 'http://104.152.209.49:8181/720p/cctv5.m3u8',)),
    ('中央·央视', 'CCTV5+', ('http://120.238.94.82:9901/tsfile/live/1030_1.m3u8', 'http://219.147.245.238:25480/newlive/live/hls/6/live.m3u8', 'http://45.192.97.170:8880/play/260.m3u8',)),
    ('中央·央视', 'CCTV6', ('http://1.24.39.180:9003/hls/6/index.m3u8', 'http://222.223.41.27:8888/hls/6/index.m3u8', 'http://113.90.154.189:9901/tsfile/live/0006_1.m3u8?key=txiptv&playlive=1&authid=0',)),
    ('中央·央视', 'CCTV7', ('http://219.147.245.238:25480/newlive/live/hls/8/live.m3u8', 'http://63.141.230.178:82/gslb/zbdq5.m3u8?id=cctv7hd', 'http://45.192.97.170:8880/play/396.m3u8',)),
    ('中央·央视', 'CCTV8', ('http://183.223.157.33:9901/tsfile/live/0008_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://74.91.26.218:82/live/cctv8hd.m3u8', 'http://45.192.97.170:8880/play/448.m3u8',)),
    ('中央·央视', 'CCTV9', ('http://222.223.41.27:8888/hls/9/index.m3u8', 'http://113.90.154.189:9901/tsfile/live/0009_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://45.192.97.170:8880/play/398.m3u8',)),
    ('中央·央视', 'CCTV10', ('http://113.90.154.189:9901/tsfile/live/0010_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://45.192.97.170:8880/play/399.m3u8', 'http://74.91.26.218:82/live/cctv10hd.m3u8',)),
    ('中央·央视', 'CCTV11', ('http://222.223.41.27:8888/hls/11/index.m3u8', 'http://1.24.39.180:9003/hls/11/index.m3u8', 'http://183.129.255.66:8480/hls/12/index.m3u8',)),
    ('中央·央视', 'CCTV12', ('http://222.223.41.27:8888/hls/12/index.m3u8', 'http://183.129.255.66:8480/hls/13/index.m3u8', 'http://113.90.154.189:9901/tsfile/live/0012_1.m3u8?key=txiptv&playlive=1&authid=0',)),
    ('中央·央视', 'CCTV13', ('https://event.pull.hebtv.com/jishi/cp1.m3u8', 'http://116.128.243.121:85/tsfile/live/0013_1.m3u8?key=txiptv&playlive=0&authid=0', 'http://183.129.255.66:8480/hls/14/index.m3u8',)),
    ('中央·央视', 'CCTV14', ('https://event.pull.hebtv.com/jishi/cp2.m3u8', 'http://219.147.245.238:25480/newlive/live/hls/15/live.m3u8', 'http://183.129.255.66:8480/hls/15/index.m3u8',)),
    ('中央·央视', 'CCTV15', ('http://74.91.26.218:82/live/cctv15hd.m3u8', 'http://183.129.255.66:8480/hls/16/index.m3u8', 'http://1.24.39.180:9003/hls/15/index.m3u8',)),
    ('中央·央视', 'CCTV16', ('http://1.24.39.180:9003/hls/60/index.m3u8', 'http://112.27.5.218:9901/tsfile/live/faacts/1001_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://219.147.245.238:25480/newlive/live/hls/17/live.m3u8',)),
    ('中央·央视', 'CCTV17', ('http://74.91.26.218:82/live/cctv17hd.m3u8', 'http://183.129.255.66:8480/hls/18/index.m3u8', 'http://218.104.239.114:9901/tsfile/live/0019_2.m3u8?key=txiptv&playlive=1&authid=0',)),
    ('中央·央视', 'CCTV4K', ('http://198.204.240.250:82/live/cctv4k.m3u8', 'https://live-play-hls.cctvnews.cctv.com/CCTVChannel/channel_cctv4k_mbd.m3u8?auth_key=1794067200-1-b59134a2ead43d7f783f943c8f535e7bb80c5169575b2e8efcd5b3ddea21b41c-66db6c6636e7bfe8c8068212993b08df&yid=b59134a2ead43d7f783f943c8f535e7bb80c5169575b2e8efcd5b3ddea21b41c',)),
    ('中央·央视', 'CCTV8K', ('http://192.151.150.154/live/cctv8k.m3u8', 'http://198.204.240.250:82/live/cctv8k.m3u8',)),
    ('中央·央视', 'CGTN', ('http://39.134.240.3/PLTV/2/224/3221225950/index.m3u8', 'https://amg00405-rakutentv-cgtn-rakuten-i9tar.amagi.tv/master.m3u8', 'https://english-livebkali.cgtn.com/live/encgtn.m3u8',)),
    ('中央·央视', 'CGTN纪录', ('http://39.134.240.3/PLTV/2/224/3221225936/index.m3u8', 'https://amg00405-rakutentv-cgtndocumentary-rakuten-0ql8j.amagi.tv/master.m3u8', 'https://hlspackager.akamaized.net/live/DB/CGTN_DOCUMENTARY/HLS/CGTN_DOCUMENTARY.m3u8',)),
    ('中央·央视', 'CGTN西班牙语', ('http://45.165.82.19/test/index.m3u8', 'http://45.186.106.147:8880/play/a06f/index.m3u8',)),
    ('中央·央视', '中国教育电视台1频道', ('http://39.134.13.35:6610/180000001001/00000001000000000016000000007220/index.m3u8?', 'http://117.161.133.51:81/gitv_live/G_CETV-1/G_CETV-1.m3u8?p=GITV',)),
    ('中央·央视', '中国教育电视台2频道', ('http://117.161.133.51:81/gitv_live/G_CETV-2/G_CETV-2.m3u8?p=GITV',)),
    ('中央·风云/付费', 'CCTV风云剧场', ('http://39.134.242.92:80/180000001002/00000001000000000091000000244807/main.m3u8',)),
    ('中央·风云/付费', 'CCTV第一剧场', ('http://39.134.242.92:80/180000001002/00000001000000000091000000244808/main.m3u8',)),
    ('中央·风云/付费', 'CCTV怀旧剧场', ('http://39.134.242.92:80/180000001002/00000001000000000091000000244806/main.m3u8',)),
    ('中央·风云/付费', 'CCTV世界地理', ('http://39.134.242.92:80/180000001002/00000001000000000091000000244805/main.m3u8',)),
    ('中央·风云/付费', 'CCTV风云音乐', ('http://39.134.242.92:80/180000001002/00000001000000000091000000244809/main.m3u8',)),
    ('中央·风云/付费', 'CCTV兵器科技', ('http://39.134.242.92:80/180000001002/00000001000000000091000000244796/main.m3u8',)),
    ('中央·风云/付费', 'CCTV风云足球', ('http://39.134.242.92:80/180000001002/00000001000000000091000000244800/main.m3u8',)),
    ('中央·风云/付费', 'CCTV高尔夫·网球', ('http://39.134.242.92:80/180000001002/00000001000000000091000000244801/main.m3u8',)),
    ('中央·风云/付费', 'CCTV女性时尚', ('http://39.134.242.92:80/180000001002/00000001000000000091000000244811/main.m3u8',)),
    ('中央·风云/付费', 'CCTV央视文化精品', ('http://39.134.242.92:80/180000001002/00000001000000000091000000244810/main.m3u8',)),
    ('中央·风云/付费', 'CCTV央视台球', ('http://39.134.242.92:80/180000001002/00000001000000000091000000244803/main.m3u8',)),
    ('中央·风云/付费', 'CCTV电视指南', ('http://39.134.242.92:80/180000001002/00000001000000000091000000244797/main.m3u8',)),
    ('中央·风云/付费', 'CHC家庭影院', ('http://39.134.242.92:80/180000001002/00000001000000000050000000448840/main.m3u8',)),
    ('中央·风云/付费', 'CHC影迷电影', ('http://39.134.242.92:80/180000001002/00000001000000000050000000448841/main.m3u8',)),
    ('中央·风云/付费', 'CHC动作电影', ('http://39.134.242.92:80/180000001002/00000001000000000050000000448842/main.m3u8',)),
    ('省级卫视', '北京卫视', ('http://59.39.89.130:60901/tsfile/live/0125_7.m3u8?key=txiptv&playlive=1&authid=0', 'http://39.134.242.92:80/180000001002/00000001000000000008000000047443/main.m3u8', 'http://go.bkpcp.top/mg/bjws',)),
    ('省级卫视', '天津卫视', ('http://107.150.60.122/live/tjwshd.m3u8', 'http://198.204.228.26/live/tjwshd.m3u8', 'http://63.141.230.178:82/gslb/zbdq5.m3u8?id=tjwshd',)),
    ('省级卫视', '河北卫视', ('http://124.90.45.52:9901/tsfile/live/0117_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://event.pull.hebtv.com/jishi/weishi_tingyun.m3u8', 'http://39.134.242.92:80/180000001002/00000001000000000016000000007223/index.m3u8',)),
    ('省级卫视', '山西卫视', ('http://45.192.97.170:8880/play/312.m3u8', 'http://119.39.9.8:9901/tsfile/live/0118_1.m3u8', 'http://59.39.89.130:60901/tsfile/live/0125_20.m3u8?key=txiptv&playlive=1&authid=0',)),
    ('省级卫视', '内蒙古卫视', ('http://play1-qk.nmtv.cn/live/1769652018126032.m3u8', 'http://222.71.55.147:9901/tsfile/live/0109_1.m3u8?key=txiptv&playlive=0&authid=0', 'http://45.192.97.170:8880/play/310.m3u8',)),
    ('省级卫视', '辽宁卫视', ('http://59.39.89.130:60901/tsfile/live/0125_13.m3u8?key=txiptv&playlive=1&authid=0', 'http://153.0.171.163:9901/tsfile/live/0121_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://119.39.9.8:9901/tsfile/live/0121_1.m3u8?key=txiptv&playlive=0&authid=0',)),
    ('省级卫视', '吉林卫视', ('http://107.150.60.122/live/jlwshd.m3u8', 'http://124.90.45.52:9901/tsfile/live/0116_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://39.134.242.92:80/180000001002/00000001000000000057000000208223/main.m3u8',)),
    ('省级卫视', '黑龙江卫视', ('http://l.cztvcloud.com/channels/lantian/SXyuyao3/720p.m3u8', 'http://39.134.13.35:6610/180000001001/00000001000000000008000000047449/index.m3u8?', 'http://223.110.243.169/PLTV/3/224/3221227252/index.m3u8',)),
    ('省级卫视', '东方卫视', ('http://119.129.172.127:9901/tsfile/live/0107_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://bp-resource-dfl.bestv.cn/155/3/video.m3u8', 'http://bztv.tvbus.cc:8081/cdnlive/dfws.m3u8',)),
    ('省级卫视', '江苏卫视', ('http://119.129.172.127:9901/tsfile/live/0127_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://107.150.60.122/live/jswshd.m3u8', 'http://38.75.136.137:98/gslb/dsdqpub/jswshd.m3u8?auth=testpub',)),
    ('省级卫视', '浙江卫视', ('http://ali-xwl.cztv.com/live/channel011080Plxw.m3u8', 'http://fuxin.yunjifei.top:999/tsfile/live/0124_1.m3u8?key=txiptv', 'http://107.150.60.122/live/zjwshd.m3u8',)),
    ('省级卫视', '安徽卫视', ('http://59.39.89.130:60901/tsfile/live/0125_6.m3u8?key=txiptv&playlive=1&authid=0', 'http://219.147.245.238:25480/newlive/live/hls/40/live.m3u8', 'http://38.75.136.137:98/gslb/dsdqpub/ahwshd.m3u8?auth=testpub',)),
    ('省级卫视', '福建东南卫视', ('http://live.zohi.tv/video/s10001-fztv-3/index.m3u8', 'http://63.141.230.178:82/gslb/zbdq5.m3u8?id=dnwshd', 'http://124.90.45.52:9901/tsfile/live/0137_1.m3u8?key=txiptv&playlive=1&authid=0',)),
    ('省级卫视', '江西卫视', ('http://107.150.60.122/live/jxwshd.m3u8', 'http://198.204.228.26/live/jxwshd.m3u8', 'http://bztv.tvbus.cc:8081/cdnlive/jxws.m3u8',)),
    ('省级卫视', '山东卫视', ('http://38.75.136.137:98/gslb/dsdqpub/sdwshd.m3u8?auth=testpub', 'http://63.141.230.178:82/gslb/zbdq5.m3u8?id=sdwshd', 'http://l.cztvcloud.com/channels/lantian/SXshengzhou1/720p.m3u8',)),
    ('省级卫视', '河南卫视', ('http://tvcdn.stream3.hndt.com/tv/65c4a6d5017e1000b2b6ea2500000000_transios/playlist.m3u8?wsSecret=68d9106ce402a09294becb8dc2f01984&wsTime=1793995402', 'http://45.192.97.170:8880/play/298.m3u8', 'https://dxtx.hntv.tv/live/lypd.m3u8?txSecret=10c771842a0be59e8b575d765173ec96&txTime=7B923E0A&wsSecret=985ebb910dd1e9ad9603ffd7670bd155&wsTime=1791183481',)),
    ('省级卫视', '湖北卫视', ('http://119.129.172.127:9901/tsfile/live/0132_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://59.39.89.130:60901/tsfile/live/0125_12.m3u8?key=txiptv&playlive=1&authid=0', 'http://38.75.136.137:98/gslb/dsdqpub/hbwshd.m3u8?auth=testpub',)),
    ('省级卫视', '湖南卫视', ('http://59.39.89.130:60901/tsfile/live/0125_2.m3u8?key=txiptv&playlive=1&authid=0', 'http://118.193.115.2:9901/tsfile/live/0128_2.m3u8?key=txiptv', 'http://104.152.209.49:8181/720p/hnws.m3u8',)),
    ('省级卫视', '广东卫视', ('http://59.39.89.130:60901/tsfile/live/0125_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://113.90.154.189:9901/tsfile/live/1000_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://36.136.38.87:9901/tsfile/live/0125_1.m3u8?key=txiptv&playlive=1&authid=0',)),
    ('省级卫视', '广西卫视', ('https://hlscdn.liangtv.cn/live/de0f97348eb84f62aa6b7d8cf0430770/dd505d87880c478f901f38560ca4d4e6.m3u8', 'http://45.192.97.170:8880/play/292.m3u8', 'http://204.12.221.218:8181/3m1080p/gxws.m3u8',)),
    ('省级卫视', '海南卫视', ('http://39.134.242.92:80/180000001002/00000001000000000057000000208265/main.m3u8', 'https://livelyws.chinamcache.com/lyws/zb03.m3u8',)),
    ('省级卫视', '重庆卫视', ('http://59.39.89.130:60901/tsfile/live/0125_24.m3u8?key=txiptv&playlive=1&authid=0', 'http://198.204.228.26/live/cqwshd.m3u8', 'http://bztv.tvbus.cc:8081/cdnlive/cqws.m3u8',)),
    ('省级卫视', '四川卫视', ('http://59.39.89.130:60901/tsfile/live/0125_16.m3u8?key=txiptv&playlive=1&authid=0', 'http://fuxin.yunjifei.top:999/tsfile/live/0123_1.m3u8?key=txiptv', 'http://45.192.97.170:8880/play/532.m3u8',)),
    ('省级卫视', '贵州卫视', ('http://59.39.89.130:60901/tsfile/live/0125_15.m3u8?key=txiptv&playlive=1&authid=0', 'http://45.192.97.170:8880/play/518.m3u8', 'http://153.0.171.163:9901/tsfile/live/0120_1.m3u8?key=txiptv&playlive=1&authid=0',)),
    ('省级卫视', '云南卫视', ('http://59.39.89.130:60901/tsfile/live/0125_18.m3u8?key=txiptv&playlive=1&authid=0', 'https://hwapi.yntv.net/ew265l/z1z6s5.m3u8', 'http://192.151.150.154/live/ynwshd.m3u8',)),
    ('省级卫视', '西藏卫视', ('http://59.39.89.130:60901/tsfile/live/0125_3.m3u8?key=txiptv&playlive=1&authid=0', 'http://222.71.55.147:9901/tsfile/live/0111_1.m3u8?key=txiptv&playlive=0&authid=0', 'http://107.150.60.122/live/xzws.m3u8',)),
    ('省级卫视', '陕西卫视', ('http://63.141.230.178:82/gslb/zbdq5.m3u8?id=snwshd', 'http://38.75.136.137:98/gslb/dsdqpub/sxwshd.m3u8?auth=testpub', 'http://192.151.150.154/live/snwshd.m3u8',)),
    ('省级卫视', '甘肃卫视', ('http://63.141.230.178:82/gslb/zbdq5.m3u8?id=gswshd', 'http://120.238.84.45:9901/tsfile/live/1079_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://120.198.86.186:9901/tsfile/live/1091_1.m3u8?key=txiptv&playlive=1&authid=0',)),
    ('省级卫视', '青海卫视', ('http://38.75.136.137:98/gslb/dsdqpub/qhws.m3u8?auth=testpub', 'http://58.56.162.102:4466/newlive/live/hls/42/live.m3u8', 'http://107.150.60.122/live/qhws.m3u8',)),
    ('省级卫视', '宁夏卫视', ('http://222.71.55.147:9901/tsfile/live/0112_1.m3u8?key=txiptv&playlive=0&authid=0', 'http://120.198.86.186:9901/tsfile/live/1088_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://fuxin.yunjifei.top:999/tsfile/live/0112_1.m3u8?key=txiptv',)),
    ('省级卫视', '新疆卫视', ('http://120.198.86.186:9901/tsfile/live/1090_1.m3u8?key=txiptv&playlive=1&authid=0', 'http://fuxin.yunjifei.top:999/tsfile/live/0110_1.m3u8?key=txiptv', 'http://63.141.230.178:82/gslb/zbdq5.m3u8?id=xjws',)),
    ('省级卫视', '深圳卫视', ('http://74.91.26.218:82/live/szwshd.m3u8', 'http://120.238.94.82:9901/tsfile/live/1065_1.m3u8', 'http://63.141.230.178:82/gslb/zbdq5.m3u8?id=szwshd',)),
    ('省级卫视', '厦门卫视', ('http://223.110.245.159/ott.js.chinamobile.com/PLTV/3/224/3221226996/index.m3u8', 'http://112.25.48.68/live/program/live/xmws/1300000/mnf.m3u8',)),
    ('省级卫视', '海峡卫视', ('https://live1-fuyun.fjtv.net/haixiapd/hd/live.m3u8?_upt=777071ac1793598534',)),
    ('省级卫视', '康巴卫视', ('http://223.110.245.139/PLTV/4/224/3221227008/index.m3u8', 'http://scgctvshow.sctv.com/hdlive/kangba/1.m3u8',)),
    ('省级卫视', '三沙卫视', ('http://107.150.60.122/live/ssws.m3u8', 'http://63.141.230.178:82/gslb/zbdq5.m3u8?id=ssws', 'http://38.75.136.137:98/gslb/dsdqpub/ssws.m3u8?auth=testpub',)),
    ('省级卫视', '兵团卫视', ('http://222.71.55.147:9901/tsfile/live/0115_1.m3u8?key=txiptv&playlive=0&authid=0', 'http://59.39.89.130:60901/tsfile/live/0125_9.m3u8?key=txiptv&playlive=1&authid=0', 'http://120.238.84.45:9901/tsfile/live/1080_1.m3u8?key=txiptv&playlive=1&authid=0',)),
    ('省级卫视', '延边卫视', ('https://srs.iyb983.cn/video/CYS/index.m3u8', 'https://srs.iyb983.cn:443/video/CYS/index.m3u8', 'http://223.110.245.139/PLTV/4/224/3221227002/index.m3u8',)),
    ('省级地面', '湖南经视', ('http://39.134.240.3/PLTV/2/224/3221226036/index.m3u8',)),
    ('省级地面', '湖南都市频道', ('http://39.134.13.37:6610/180000001001/00000001000000000007000000001249/index.m3u8?',)),
    ('省级地面', '湖南娱乐频道', ('http://39.134.13.35:6610/180000001001/00000001000000000007000000001248/index.m3u8?',)),
    ('省级地面', '湖南电视剧', ('http://39.134.13.35:6610/180000001001/00000001000000001001000000000037/index.m3u8?',)),
    ('省级地面', '湖南电影频道', ('http://39.134.240.3/PLTV/2/224/3221226140/index.m3u8',)),
    ('省级地面', '湖南教育电视台', ('http://39.134.242.92:80/180000001002/00000001000000000023000000196697/index.m3u8',)),
    ('省级地面', '湖南国际频道', ('http://39.134.13.35:6610/180000001001/00000001000000001001000000000045/index.m3u8?',)),
    ('省级地面', '湖南爱晚频道', ('http://39.134.240.3/PLTV/2/224/3221226192/index.m3u8',)),
    ('省级地面', '金鹰卡通', ('http://39.134.13.35:6610/180000001001/00000001000000000007000000001247/index.m3u8?', 'http://223.110.245.145/ott.js.chinamobile.com/PLTV/3/224/3221226303/index.m3u8', 'http://223.110.241.149:6610/gitv/live1/G_JINYING/G_JINYING/1.m3u8',)),
    ('省级地面', '金鹰纪实', ('http://39.134.13.35:6610/180000001001/00000001000000000016000000007228/index.m3u8?',)),
    ('省级地面', '江苏城市', ('http://183.207.248.71/gitv/live1/G_JSCS/G_JSCS', 'http://223.110.245.143/ott.js.chinamobile.com/PLTV/3/224/3221225929/index.m3u8',)),
    ('省级地面', '江苏综艺', ('http://183.207.248.71/gitv/live1/G_JSZY/G_JSZY',)),
    ('省级地面', '江苏影视', ('http://223.110.243.134/PLTV/4/224/3221225937/index.m3u8', 'http://183.207.248.71/gitv/live1/G_JSYS/G_JSYS',)),
    ('省级地面', '江苏教育', ('http://223.110.245.151/ott.js.chinamobile.com/PLTV/3/224/3221225923/index.m3u8', 'http://183.207.248.71/gitv/live1/G_JSJY/G_JSJY',)),
    ('省级地面', '江苏体育', ('http://183.207.248.71/gitv/live1/G_JSTY/G_JSTY', 'http://183.207.249.12/PLTV/4/224/3221225935/index.m3u8', 'http://223.110.245.157/ott.js.chinamobile.com/PLTV/3/224/3221225935/index.m3u8',)),
    ('省级地面', '江苏公共', ('http://183.207.248.71/gitv/live1/G_JSGG/G_JSGG',)),
    ('省级地面', '浙江钱江', ('https://ali-m-l.cztv.com/channels/lantian/channel002/1080p.m3u8',)),
    ('省级地面', '浙江民生', ('https://ali-m-l.cztv.com/channels/lantian/channel006/1080p.m3u8',)),
    ('省级地面', '浙江经济', ('https://ali-m-l.cztv.com/channels/lantian/channel003/1080p.m3u8',)),
    ('省级地面', '浙江教科', ('https://ali-m-l.cztv.com/channels/lantian/channel004/1080p.m3u8',)),
    ('省级地面', '浙江公共', ('https://ct-m-l.cztv.com/channels/lantian/channel007/1080p.m3u8', 'https://qiniup-m-l.cztv.com/channels/lantian/channel007/1080p.m3u8',)),
    ('省级地面', '浙江新闻', ('https://ali-m-l.cztv.com/channels/lantian/channel007/1080p.m3u8',)),
    ('省级地面', '浙江国际', ('https://ali-m-l.cztv.com/channels/lantian/channel010/1080p.m3u8',)),
    ('省级地面', '山东齐鲁', ('http://livealone302.iqilu.com/iqilu/qlpd.m3u8',)),
    ('省级地面', '山东影视', ('http://livealone302.iqilu.com/iqilu/yspd.m3u8',)),
    ('省级地面', '山东综艺', ('http://livealone302.iqilu.com/iqilu/zypd.m3u8',)),
    ('省级地面', '山东生活', ('http://livealone302.iqilu.com/iqilu/shpd.m3u8',)),
    ('省级地面', '山东新闻', ('http://livealone302.iqilu.com/iqilu/ggpd.m3u8',)),
    ('省级地面', '山东农科', ('http://livealone302.iqilu.com/iqilu/nkpd.m3u8',)),
    ('省级地面', '山东体育', ('http://livealone302.iqilu.com/iqilu/typd.m3u8',)),
    ('省级地面', '山东少儿', ('http://livealone302.iqilu.com/iqilu/sepd.m3u8',)),
    ('省级地面', '北京纪实', ('http://39.134.115.163:8080/PLTV/88888910/224/3221225675/index.m3u8', 'http://39.134.115.163:8080/PLTV/88888910/224/3221225676/index.m3u8',)),
    ('省级地面', '北京财经', ('http://ivi.bupt.edu.cn/hls/btv5.m3u8',)),
    ('省级地面', '北京青年', ('http://ivi.bupt.edu.cn/hls/btv8.m3u8',)),
    ('省级地面', '五星体育', ('http://223.110.245.147/ott.js.chinamobile.com/PLTV/3/224/3221226799/index.m3u8',)),
    ('省级地面', '嘉佳卡通', ('http://223.110.245.139/PLTV/4/224/3221227009/index.m3u8', 'http://112.25.48.68/live/program/live/jjkt/1300000/mnf.m3u8',)),
    ('省级地面', '优漫卡通', ('http://183.207.249.15/PLTV/4/224/3221225933/index.m3u8', 'http://223.110.243.171/PLTV/3/224/3221226982/index.m3u8',)),
    ('省级地面', '卡酷动画', ('http://39.134.242.92:80/180000001002/00000001000000000090000000215608/main.m3u8',)),
    ('市级电视台', '长沙新闻综合', ('http://35848.hlsplay.aodianyun.com/guangdianyun_35848/tv_channel_346.m3u8',)),
    ('市级电视台', '长沙政法频道', ('http://35848.hlsplay.aodianyun.com/guangdianyun_35848/tv_channel_348.m3u8',)),
    ('市级电视台', '长沙经贸频道', ('http://35848.hlsplay.aodianyun.com/guangdianyun_35848/tv_channel_350.m3u8',)),
    ('市级电视台', '长沙女性频道', ('http://35848.hlsplay.aodianyun.com/guangdianyun_35848/tv_channel_349.m3u8',)),
    ('市级电视台', '长沙购物频道', ('http://35848.hlsplay.aodianyun.com/guangdianyun_35848/tv_channel_354.m3u8',)),
    ('市级电视台', '湘潭新闻综合', ('http://live.hnxttv.com:9601/live/xwzh/800K/tzwj_video.m3u8',)),
    ('市级电视台', '湘潭公共', ('http://live.hnxttv.com:9601/live/dspd/800K/tzwj_video.m3u8',)),
    ('市级电视台', '岳阳公共', ('http://live.hnxttv.com:9601/live/dspd/800K/tzwj_video.m3u8?BVUUID=C236454D-5355-2F5F-FA96-1887C72E55CE&auth=654837809071524@615@2E9A5FD0B225B012E3178551CF3754A8',)),
    ('市级电视台', '娄底综合', ('http://119.39.242.52:1935/live/zonghe/playlist.m3u8',)),
    ('市级电视台', '张家界综合1', ('http://stream.zjjrtv.com/zjjtv1/hd/live.m3u8',)),
    ('市级电视台', '张家界综合2', ('http://stream.zjjrtv.com/zjjtv2/hd/live.m3u8',)),
    ('市级电视台', '南京十八频道', ('http://183.207.248.71/gitv/live1/G_NJSB/G_NJSB',)),
    ('市级电视台', '南京少儿频道', ('https://live.nbs.cn/channels/njtv/sepd/m3u8:500k/live.m3u8',)),
    ('市级电视台', '南京教科', ('http://223.110.245.155/ott.js.chinamobile.com/PLTV/3/224/3221227194/index.m3u8', 'https://live.nbs.cn/channels/njtv/jkpd/m3u8:500k/live.m3u8',)),
    ('市级电视台', '西安新闻', ('http://stream2.xiancity.cn/xatv1/playlist.m3u8',)),
    ('市级电视台', '西安影视', ('http://stream2.xiancity.cn/xatv4/playlist.m3u8',)),
    ('市级电视台', '西安商务资讯', ('http://stream2.xiancity.cn/xatv3/playlist.m3u8',)),
    ('市级电视台', '福州新闻综合', ('http://live.zohi.tv/video/s10001-fztv-1/index.m3u8',)),
    ('市级电视台', '福州都市生活', ('http://live.zohi.tv/video/s10001-fztv-3/index.m3u8',)),
    ('市级电视台', '福州少儿频道', ('http://live.zohi.tv/video/s10001-fztv-4/index.m3u8',)),
    ('市级电视台', '广州综合', ('https://tencentplaybusiness.gztv.com/live/zonghes.m3u8',)),
    ('市级电视台', '哈尔滨新闻综合', ('https://stream.hrbtv.net/xwzh/playlist.m3u8?_upt=ef41dd531755913594',)),
    ('市级电视台', '哈尔滨影视频道', ('https://stream.hrbtv.net/yspd/playlist.m3u8',)),
    ('市级电视台', '长春新闻综合', ('https://stream2.jlntv.cn/jlcc/sd/live.m3u8',)),
    ('市级电视台', '徐州新闻综合', ('http://223.110.245.165/ott.js.chinamobile.com/PLTV/3/224/3221225945/index.m3u8',)),
    ('市级电视台', '徐州公共频道', ('http://183.207.248.11/PLTV/3/224/3221225951/index.m3u8',)),
    ('市级电视台', '徐州经济生活', ('http://223.110.245.167/ott.js.chinamobile.com/PLTV/3/224/3221225947/index.m3u8',)),
    ('市级电视台', '徐州新闻综合1', ('http://183.207.249.15/PLTV/3/224/3221225945/index.m3u8',)),
    ('市级电视台', '徐州综合3', ('http://183.207.249.7/PLTV/3/224/3221225949/index.m3u8', 'http://223.110.245.151/ott.js.chinamobile.com/PLTV/3/224/3221225949/index.m3u8',)),
    ('市级电视台', '徐州综合4', ('http://183.207.249.15/PLTV/3/224/3221225951/index.m3u8',)),
    ('市级电视台', '吴江新闻综合', ('http://30515.hlsplay.aodianyun.com/lms_30515/tv_channel_239.m3u8',)),
    ('市级电视台', '武进新闻', ('https://live.wjyanghu.com/live/CH1.m3u8',)),
    ('市级电视台', '武进生活', ('https://live.wjyanghu.com/live/CH2.m3u8',)),
    ('市级电视台', '萧山新闻综合', ('https://l.cztvcloud.com/channels/lantian/SXxiaoshan1/720p.m3u8',)),
    ('市级电视台', '萧山生活频道', ('https://l.cztvcloud.com/channels/lantian/SXxiaoshan2/720p.m3u8',)),
    ('市级电视台', '余姚新闻综合', ('https://l.cztvcloud.com/channels/lantian/SXyuyao1/720p.m3u8',)),
    ('市级电视台', '余姚姚江文化', ('https://l.cztvcloud.com/channels/lantian/SXyuyao3/720p.m3u8', 'https://l.cztvcloud.com/channels/lantian/SXyuyao2/720p.m3u8',)),
    ('市级电视台', '上虞新闻综合1', ('https://l.cztvcloud.com/channels/lantian/SXshangyu1/720p.m3u8',)),
    ('市级电视台', '上虞新商都', ('https://l.cztvcloud.com/channels/lantian/SXshangyu3/720p.m3u8',)),
    ('市级电视台', '上虞经济文化', ('https://l.cztvcloud.com/channels/lantian/SXshangyu2/720p.m3u8',)),
    ('市级电视台', '嵊州综合', ('https://l.cztvcloud.com/channels/lantian/SXshengzhou1/720p.m3u8',)),
    ('市级电视台', '新昌新闻综合', ('https://l.cztvcloud.com/channels/lantian/SXxinchang1/720p.m3u8',)),
    ('市级电视台', '乐清新闻', ('http://33809.hlsplay.aodianyun.com/guangdianyun_33809/tv_channel_170.m3u8',)),
    ('市级电视台', '乐清生活', ('http://33809.hlsplay.aodianyun.com/guangdianyun_33809/tv_channel_171.m3u8',)),
    ('市级电视台', '潮州公共', ('http://113.64.146.48:1688/hls/4/index.m3u8',)),
    ('市级电视台', '河源综合', ('https://tmpstream.hyrtv.cn/xwzh/sd/live.m3u8',)),
    ('市级电视台', '漳州新闻综合', ('https://31182.hlsplay.aodianyun.com/lms_31182/tv_channel_175.m3u8',)),
    ('市级电视台', '南阳新闻综合', ('http://30539.hlsplay.aodianyun.com/lms_30539/tv_channel_142.m3u8',)),
    ('市级电视台', '南阳公共频道', ('http://30539.hlsplay.aodianyun.com/lms_30539/tv_channel_295.m3u8',)),
    ('市级电视台', '南阳科教频道', ('http://30539.hlsplay.aodianyun.com/lms_30539/tv_channel_296.m3u8',)),
    ('市级电视台', '宿州新闻综合', ('http://live.ahsz.tv/video/s10001-szzh/index.m3u8',)),
    ('市级电视台', '宿州公共', ('http://live.ahsz.tv/video/s10001-ggpd/index.m3u8',)),
    ('市级电视台', '宿州科教', ('http://live.ahsz.tv/video/s10001-kxjy/index.m3u8',)),
    ('市级电视台', '滁州新闻综合', ('http://live.cztv.cc:85/live/xwpd.m3u8',)),
    ('市级电视台', '滁州公共频道', ('http://live.cztv.cc:85/live/ggpd.m3u8',)),
    ('市级电视台', '滁州科教频道', ('http://live.cztv.cc:85/live/sjpd.m3u8',)),
    ('市级电视台', '抚州公共', ('http://111.75.179.195:30767/video/live_vide2.m3u8',)),
    ('市级电视台', '抚州综合频道', ('http://111.75.179.195:30767/video/live_vide.m3u8',)),
    ('市级电视台', '萍乡新闻综合', ('http://www.pxitv.com:8099/hls-live/livepkgr/_definst_/pxitvevent/pxtv1stream.m3u8',)),
    ('市级电视台', '萍乡公共频道', ('http://www.pxitv.com:8099/hls-live/livepkgr/_definst_/pxitvevent/pxtv3stream.m3u8',)),
    ('市级电视台', '萍乡教育频道', ('http://www.pxitv.com:8099/hls-live/livepkgr/_definst_/pxitvevent/pxtv2stream.m3u8',)),
    ('市级电视台', '鹤壁新闻综合', ('http://pili-live-hls.hebitv.com/hebi/hebi.m3u8',)),
    ('市级电视台', '酒泉新闻综合', ('http://117.156.28.119/270000001111/1110000001/index.m3u8',)),
    ('市级电视台', '金昌综合频道', ('http://stream4.liveyun.hoge.cn/ch02/sd/live.m3u8',)),
    ('市级电视台', '东莞新闻综合', ('http://stream.sun0769.com/dgrtv1/mp4tv1_1500.flv', 'https://stream.sun0769.com/dgrtv1/mp4tv1_800/index.m3u8',)),
    ('市级电视台', '佛山新闻综合', ('http://dslive.grtn.cn/fszh/sd/live.m3u8',)),
    ('市级电视台', '文山综合', ('http://tvdrs.wsrtv.com.cn:8100/channellive/ch1.flv', 'http://m3u8.channel.wsrtv.com.cn/cms/videos/nmip-media/channellive/channel7/playlist.m3u8',)),
    ('市级电视台', '文山公共', ('http://tvdrs.wsrtv.com.cn:8100/channellive/ch2.flv',)),
    ('市级电视台', '韶关公共', ('https://www.sgmsw.cn/videos/tv/201805/1308/9P424TC5M000AFO13CXK6GN6BOA889D2/hls/live.m3u8',)),
    ('市级电视台', '韶关综合', ('https://www.sgmsw.cn/videos/tv/201805/1308/SB05RIYZOU8JR418AUQOF62CAJQ08D0E/hls/live.m3u8',)),
    ('市级电视台', '连云港公共', ('https://live.lyg1.com/ggpd/sd/live.m3u8',)),
    ('市级电视台', '连云港综合', ('https://live.lyg1.com/zhpd/sd/live.m3u8',)),
    ('市级电视台', '绍兴影视', ('http://live.shaoxing.com.cn/video/s10001-sxtv3/index.m3u8',)),
    ('市级电视台', '绍兴综合', ('http://live.shaoxing.com.cn/video/s10001-sxtv1/index.m3u8',)),
    ('市级电视台', '铜陵公共', ('http://dstpush1.retalltech.com/app/stream2.m3u8',)),
    ('市级电视台', '铜陵综合', ('http://dstpush1.retalltech.com/app/stream1.m3u8',)),
    ('县级电视台', '高台电视台', ('http://117.156.28.119/270000001111/1110000146/index.m3u8',)),
    ('县级电视台', '静宁综合', ('http://117.156.28.119/270000001111/1110000147/index.m3u8',)),
    ('县级电视台', '靖江新闻综合', ('http://visit.jjbctv.com:1935/live/xwzhmb/playlist.m3u8',)),
    ('县级电视台', '鹿泉一套', ('http://hblq.chinashadt.com:2036/live/stream:luquan1.stream/playlist.m3u8',)),
    ('县级电视台', '鹿泉二套', ('http://hblq.chinashadt.com:2036/live/stream:luquan2.stream/playlist.m3u8',)),
    ('县级电视台', '霸州公共频道', ('http://hbbz.chinashadt.com:2036/live/stream:bzgg.stream/playlist.m3u8',)),
    ('县级电视台', '霸州少儿频道', ('http://hbbz.chinashadt.com:2036/live/stream:bzse.stream/playlist.m3u8',)),
    ('县级电视台', '安顺新闻综合', ('https://hplayer1.juyun.tv/camera/154379194.m3u8',)),
    ('县级电视台', '赤峰新闻综合', ('http://play1-qk.nmtv.cn/live/1735546697341033.m3u8',)),
    ('县级电视台', '楚雄新闻综合', ('http://hwapi.yntv.net/ew265l/848y54.m3u8',)),
    ('县级电视台', '前郭综合', ('https://stream2.jlntv.cn/qg/sd/live.m3u8',)),
    ('县级电视台', '四平新闻综合', ('https://stream2.jlntv.cn/sptv/sd/live.m3u8',)),
    ('县级电视台', '松原新闻综合', ('https://stream2.jlntv.cn/sytv/sd/live.m3u8',)),
    ('县级电视台', '白城新闻综合', ('https://stream2.jlntv.cn/baicheng1/sd/live.m3u8',)),
    ('县级电视台', '白山新闻综合', ('https://stream2.jlntv.cn/baishan1/sd/live.m3u8',)),
    ('县级电视台', '辽源新闻综合', ('https://stream2.jlntv.cn/liaoyuan1/sd/live.m3u8',)),
    ('县级电视台', '通化新闻', ('https://stream2.jlntv.cn/tonghua1/sd/live.m3u8',)),
    ('县级电视台', '集安综合', ('https://stream2.jlntv.cn/ja/sd/live.m3u8',)),
    ('县级电视台', '农安新闻综合', ('https://stream2.jlntv.cn/naxw/sd/live.m3u8',)),
    ('县级电视台', '和政电视台', ('http://117.156.28.119/270000001111/1110000149/index.m3u8',)),
    ('县级电视台', '华亭电视台', ('http://117.156.28.119/270000001111/1110000148/index.m3u8',)),
    ('县级电视台', '岷县电视台', ('http://117.156.28.119/270000001111/1110000130/index.m3u8',)),
    ('县级电视台', '敦煌电视台', ('http://117.156.28.119/270000001111/1110000028/index.m3u8',)),
    ('县级电视台', '肃州电视台', ('http://117.156.28.119/270000001111/1110000123/index.m3u8',)),
    ('县级电视台', '积石山电视台', ('http://117.156.28.119/270000001111/1110000152/index.m3u8',)),
    ('县级电视台', '灵台新闻综合', ('http://117.156.28.119/270000001111/1110000145/index.m3u8',)),
    ('县级电视台', '罗山电视台', ('http://live.dxhmt.cn:9081/tv/11521-1.m3u8',)),
    ('县级电视台', '孟州电视台', ('http://live.dxhmt.cn:9081/tv/10883-1.m3u8',)),
    ('县级电视台', '新郑综合', ('http://live.dxhmt.cn:9081/tv/10184-1.m3u8',)),
    ('县级电视台', '建安电视台', ('http://live.dxhmt.cn:9081/tv/11003-1.m3u8',)),
    ('县级电视台', '景县电视一套', ('http://hbjx.chinashadt.com:1935/live/jx1.stream/playlist.m3u8', 'http://hbjx.chinashadt.com:1935/live/stream:jx1.stream_360p/playlist.m3u8',)),
    ('县级电视台', '辛集新闻频道', ('http://zsxj.chinashadt.com:1935/live/xjxw.stream_360p/playlist.m3u8',)),
    ('县级电视台', '辛集生活频道', ('http://zsxj.chinashadt.com:1935/live/xjsh.stream_360p/playlist.m3u8',)),
    ('县级电视台', '大冶一套', ('http://dayeyun.live.tempsource.cjyun.org/videotmp/s10102-TC1T.m3u8',)),
    ('县级电视台', '大冶二套', ('http://dayeyun.live.tempsource.cjyun.org/videotmp/s10102-TC2T.m3u8',)),
    ('县级电视台', '大悟综合', ('http://yunshangdawu.live.tempsource.cjyun.org/videotmp/s10129-dwzhpd.m3u8',)),
    ('县级电视台', '广水新闻综合', ('http://guangshui.live.tempsource.cjyun.org/videotmp/s10146-GSXW.m3u8',)),
    ('县级电视台', '利川新闻综合', ('http://uni6rtmp.tulix.tv:1935/vbstv/vbsabr.smil/chunklist_w439903609_b1228800.m3u8',)),
    ('县级电视台', '鹤峰综合', ('http://hefeng.live.tempsource.cjyun.org/videotmp/s10100-hftv.m3u8',)),
    ('县级电视台', '随州综合', ('http://34766.hlsplay.aodianyun.com/guangdianyun_34766/tv_channel_304.m3u8',)),
    ('县级电视台', '随州农村频道', ('http://34766.hlsplay.aodianyun.com/guangdianyun_34766/tv_channel_305.m3u8',)),
    ('县级电视台', '万州综合', ('http://123.146.162.24:8013/tslslive/noEX9SG/hls/live_sd.m3u8',)),
    ('县级电视台', '万州影视文艺', ('http://wanzhoulive.cbg.cn:8017/d4ceB1a/1000/live.m3u8', 'http://123.146.162.24:8017/d4ceB1a/1000/live.m3u8',)),
    ('县级电视台', '万州三峡移民', ('http://123.146.162.24:8013/tslslive/PU2vzMI/hls/live_sd.m3u8',)),
    ('县级电视台', '万州科教频道', ('http://123.146.162.24:8017/Cz7WPb8/800/live.m3u8', 'http://wanzhoulive.cbg.cn:8017/Cz7WPb8/800/live.m3u8',)),
    ('县级电视台', '北碚综合', ('http://222.178.181.121:12034/beibei01.m3u8',)),
    ('县级电视台', '江津新闻综合', ('http://222.179.155.21:1935/ch1.m3u8',)),
    ('县级电视台', '江津经济生活', ('http://222.179.155.21:1935/ch0.m3u8',)),
    ('县级电视台', '荣昌综合', ('http://183.64.181.25:40023/rongchang01.m3u8',)),
    ('县级电视台', '蓬安新闻综合', ('http://palive.patv123.com:8091/live/xwpd_800K.m3u8',)),
    ('县级电视台', '电白综合', ('http://gddb.chinashadt.com:1935/live/video1.stream/playlist.m3u8', 'http://gddb.chinashadt.com:1935/live/video1.stream_360p/playlist.m3u8',)),
    ('县级电视台', '莒县电视一套', ('http://61.162.225.122:8181/live/test1.m3u8',)),
    ('县级电视台', '莒县电视二套', ('http://61.162.225.122:8181/live/test2.m3u8',)),
    ('县级电视台', '新泰综合', ('http://111.17.214.4:1935/live/xtzh/playlist.m3u8', 'http://live.xtgdw.cn:1935/live/xtzh/playlist.m3u8',)),
    ('县级电视台', '新泰生活', ('http://111.17.214.4:1935/live/xtsh/playlist.m3u8', 'http://live.xtgdw.cn:1935/live/xtsh/playlist.m3u8',)),
    ('县级电视台', '福山生活', ('http://live.jiaodong.net:82/tvfushan/hls/tv_shenghuo.m3u8',)),
    ('县级电视台', '长乐综合', ('http://35908.hlsplay.aodianyun.com/guangdianyun_35908/tv_channel_327.m3u8',)),
    ('县级电视台', '涡阳新闻综合', ('http://220.180.110.101:8083/videos/live/36/57/hwEHU4UVQ1Iv5/hwEHU4UVQ1Iv5.m3u8',)),
    ('县级电视台', '亳州新闻频道', ('http://220.180.110.101:8083/videos/live/33/59/NC7XQdEveyncq/NC7XQdEveyncq.m3u8',)),
    ('县级电视台', '宿迁公共', ('http://223.110.245.153/ott.js.chinamobile.com/PLTV/3/224/3221226939/index.m3u8',)),
    ('县级电视台', '滨海新闻', ('http://60.30.52.41/live/bhtv1/playlist.m3u8',)),
    ('县级电视台', '滨海都市', ('http://60.30.52.41/live/bhtv2/playlist.m3u8',)),
    ('县级电视台', '邗江资讯', ('http://223.110.245.139/PLTV/4/224/3221227154/index.m3u8',)),
    ('县级电视台', '吉州新闻综合', ('http://218.204.153.158/10.m3u8',)),
    ('县级电视台', '海西州综合', ('http://stream.haixitv.cn/1/sd/live.m3u8',)),
    ('县级电视台', '交城电视台', ('http://sxjc.chinashadt.com:2036/live/stream:jctv.stream/playlist.m3u8',)),
    ('县级电视台', '晋中公共', ('http://jzlive.jztvnews.com:90/live/jzgg.m3u8',)),
    ('县级电视台', '石景山电视台', ('https://live.sjsrm.com/bjsjs/sd/live.m3u8',)),
    ('县级电视台', '兴隆综合', ('https://jwcdnqx.hebyun.com.cn/live/xlzh/1500k/tzwj_video.m3u8',)),
    ('县级电视台', '巴中综合', ('http://30814.hlsplay.aodianyun.com/lms_30814/tv_channel_246.flv',)),
    ('县级电视台', '达州公共', ('http://m3u8.channellive.dzxw.net/cms/videos/nmip-media/channellive/channel36/playlist.m3u8',)),
    ('县级电视台', '达州综合', ('http://m3u8.channellive.dzxw.net/cms/videos/nmip-media/channellive/channel35/playlist.m3u8',)),
    ('县级电视台', '郎溪综合', ('http://117.70.93.210:1935/live/xinwen/playlist.m3u8',)),
    ('港澳台', '凤凰卫视中文台', ('http://223.110.245.139/ott.js.chinamobile.com/PLTV/3/224/3221226922/index.m3u8', 'http://223.110.245.139/PLTV/3/224/3221226922/index.m3u8', 'http://223.110.245.167/ott.js.chinamobile.com/PLTV/3/224/3221226922/index.m3u8',)),
    ('港澳台', '凤凰卫视资讯台', ('http://223.110.245.167/ott.js.chinamobile.com/PLTV/3/224/3221226923/index.m3u8', 'http://125.210.152.18:9090/live/FHZX_1200.m3u8', 'http://api.mg.itv888.cn:8080/hls/11ef1dc70d8/index.m3u8',)),
    ('港澳台', '凤凰卫视香港台', ('http://223.110.245.136/PLTV/3/224/3221226975/index.m3u8',)),
    ('港澳台', '澳门卫视', ('http://61.244.22.4/ch1/ch1.live/playlist.m3u8',)),
    ('港澳台', 'TVB新闻', ('http://r.jdshipin.com/CkuBd',)),
    ('港澳台', '星空卫视', ('http://218.202.220.2:5000/nn_live.ts?id=STARTV',)),
)


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
            "vod_area": "中国",
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
            "header": {
                "Referer": "https://www.yangshipin.cn/",
                "User-Agent": UA,
            },
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
