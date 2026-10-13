#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 作者：Passwd Word
"""
哈TV 抓源 / 订阅服务（仅标准库）

把极致播放器专用的 hatv.js + tv.txt 转成 Python：
  - tv.txt 的 185 个频道内嵌为订阅数据
  - hatv.js 的 main(item) 逻辑逐行移植：拉 XML 取 <ad_url>，
    从 liveedge2/<channel>_ 提取频道名，拼出真实 m3u8 直链

用法（默认无参数即进服务模式，APTV 直接导入运行）：
  python3 hatv.py                      # 本机服务，默认 127.0.0.1:19914
  python3 hatv.py --bind 0.0.0.0       # 局域网共享
  python3 hatv.py --out hatv.m3u       # 一次性写出 m3u 订阅文件（需能连上 XML 服务器）
  python3 hatv.py --print-url 56       # 打印单个频道的真实直链（调试用）

订阅地址：http://127.0.0.1:19914/all.m3u
单频道：  http://127.0.0.1:19914/live/<id>.m3u8  （播放时实时解析并 302 跳转到真实地址）
"""
import argparse
import re
import socket
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# ================= 用户配置 =================
DEFAULT_SERVE = True        # 无参数时直接进服务模式（APTV 习惯），不写文件
DEFAULT_PORT = 19914
DEFAULT_BIND = "127.0.0.1"
XML_URL = ("http://58.99.33.12:8080/csr_mobile_client_web/"
           "Cloud_Account_ProcessAction.do?method=getVersionCode&ott_status="
           "&move_type=0&token_value=&source_service_type=&time=&id=&date=&name=")
XML_CACHE_TTL = 300         # XML 缓存秒数（所有频道共用同一份 XML）
HTTP_TIMEOUT = 15
# ===========================================

# tv.txt 频道清单（分组行以 ,#genre# 结尾；条目：名称,http://?id=数字[$logo=...]）
CHANNELS_TXT = """🤪哈TV有线🤪,#genre#
公用頻道,http://?id=3
地方新聞,http://?id=4
民視,http://?id=5
CNN International,http://?id=6
台視,http://?id=7
人間衛視,http://?id=8
中視,http://?id=9
大愛電視,http://?id=10
華視,http://?id=11
動物星球,http://?id=12
公視,http://?id=13
公視台語台,http://?id=14
好消息頻道,http://?id=15
原住民族電視台,http://?id=16
客家電視台,http://?id=17
BBC Earth,http://?id=18
DISCOVERY,http://?id=19
中台灣生活網,http://?id=20
旅遊生活,http://?id=21
卡通頻道,http://?id=22
CARTOONITO,http://?id=23
MOMO親子台,http://?id=24
東森幼幼台,http://?id=25
緯來綜合台,http://?id=26
八大第一台,http://?id=27
八大綜合台,http://?id=28
三立台灣台,http://?id=29
三立都會台,http://?id=30
壹電視資訊綜合台,http://?id=31
東森綜合台,http://?id=32
東森超視,http://?id=33
東森購物2台,http://?id=34 
MOMO2台,http://?id=35
中天綜合台,http://?id=36
東風衛視,http://?id=37
年代MUCH,http://?id=38
地方采風,http://?id=39
東森戲劇台,http://?id=40
八大戲劇台,http://?id=41
TVBS歡樂台,http://?id=42
緯來戲劇台,http://?id=43
高點電視台,http://?id=44
JET綜合台,http://?id=45
東森購物3台,http://?id=46
東森購物1台,http://?id=47
MOMO1台,http://?id=48
壹電視新聞台,http://?id=49
年代新聞台,http://?id=50
東森新聞台,http://?id=51
華視新聞,http://?id=52
民視新聞台,http://?id=53
三立新聞台,http://?id=54
TVBS新聞,http://?id=55
TVBS,http://?id=56
東森財經新聞台,http://?id=57
非凡新聞台,http://?id=58
VIVA 1台,http://?id=59
東森購物5台,http://?id=60
CATCHPLAY電影台,http://?id=61
東森電影台,http://?id=62
緯來電影台,http://?id=63
冠軍電視台,http://?id=64
HBO,http://?id=65
東森洋片台,http://?id=66
中天娛樂台,http://?id=67
好萊塢電影台,http://?id=68
amc電影台,http://?id=69
美麗人生購物台,http://?id=70
CINEMAX,http://?id=71
緯來體育台,http://?id=72
DAZN 1,http://?id=73
DAZN 2,http://?id=74
MOMO綜合台,http://?id=75
博斯運動台 ,http://?id=76
海豚綜合台,http://?id=77
民俗才藝,http://?id=78
緯來日本台,http://?id=79
國興衛視,http://?id=80
冠軍夢想台,http://?id=81
信吉電視台,http://?id=82
生活資訊台,http://?id=83
AXN,http://?id=84
寰宇新聞台,http://?id=85
信大電視台,http://?id=86
緯來育樂台,http://?id=87
三立財經新聞台,http://?id=88
雙子衛視,http://?id=89
靖天購物一台,http://?id=90
台灣綜合台,http://?id=91
LS TIME電影台,http://?id=92
全球財經網頻道,http://?id=93
誠心電視台,http://?id=94
非凡商業台,http://?id=95
台灣藝術台,http://?id=96
運通財經,http://?id=97
Z頻道,http://?id=98
霹靂台灣台,http://?id=99
MTV綜合電視台,http://?id=100
BBC Lifestyle Channel,http://?id=101
十方法界電視台,http://?id=102
華藏衛星電視台,http://?id=103
Animax,http://?id=104
佛衛電視慈悲台,http://?id=105
八大娛樂台,http://?id=106
全大電視台,http://?id=107
華藝台灣台,http://?id=108
彰化生活台,http://?id=109
天良綜合台,http://?id=110
台灣蕃薯電視台,http://?id=111
富立電視台,http://?id=112
樂視台,http://?id=113
三聖電視台,http://?id=114
新天地民俗台,http://?id=115
紅豆2台,http://?id=116
威達超舜生活台,http://?id=117
天美麗電視台,http://?id=118
大立電視台,http://?id=119
大愛二台,http://?id=121
智林體育台,http://?id=122
國會頻道1台,http://?id=123
國會頻道2台,http://?id=124
幸福空間居家台,http://?id=125
高點育樂台,http://?id=126
華視教育體育文化台,http://?id=127
希望綜合台,http://?id=131
寶島文化台,http://?id=132
NHK WORLD PREMIUM,http://?id=135
唯心電視台,http://?id=140
Global Trekker,http://?id=145
ROCK Action,http://?id=146
TRACE Sport Starts,http://?id=147
美食星球,http://?id=148
寰宇新聞財經台,http://?id=149
Fun探索娛樂台,http://?id=150
民視第一台,http://?id=151
民視台灣台,http://?id=152
TBC台中生活台,http://?id=154
台視新聞台,http://?id=155
台視財經台,http://?id=156
台視綜合台,http://?id=157
小公視,http://?id=159
中視新聞台,http://?id=161
TaiwanPlus,http://?id=163
BBC NEWS,http://?id=164
CNA,http://?id=165
FRANCE 24(English),http://?id=166
A-One,http://?id=167
LOVE NATURE,http://?id=168
TV5MONDE,http://?id=170
Arirang TV,http://?id=171
亞洲旅遊台,http://?id=172$logo=https://tvlogo-282.pages.dev/logos/starhub/833_1920x1080_HTV.png
好消息二台,http://?id=203
Discovery Asia,http://?id=200
Discovery 科學頻道,http://?id=201
DMAX,http://?id=202
DREAMWORKS,http://?id=207
Cbeebies,http://?id=209
AFN亞洲美食頻道,http://?id=211
BBC Lifestyle Channel,http://?id=214
EVE,http://?id=215
HBO HD,http://?id=220
HBO Signature,http://?id=221
HBO Family,http://?id=222
HBO Hits,http://?id=223
TVN,http://?id=225
博斯高球台,http://?id=242
博斯網球台,http://?id=243
博斯運動二台,http://?id=244
博斯高球二台,http://?id=245
博斯無限台,http://?id=246
博斯無限二台,http://?id=247
博斯魅力網,http://?id=248

🤪哈TV18🤪,#genre#
玩家頻道,http://?id=401
Happy,http://?id=402
Hot,http://?id=403
松視4台,http://?id=404
松視1台,http://?id=405
松視2台,http://?id=406
松視3台,http://?id=407
彩虹頻道,http://?id=408
樂活頻道,http://?id=410
潘朵啦高畫質玩美台,http://?id=411
潘朵啦高畫質粉紅台,http://?id=412
驚豔成人電影台,http://?id=413
香蕉台,http://?id=414


"""

_ad_url_re = re.compile(r"<ad_url>(.*?)</ad_url>", re.S)
_channel_re = re.compile(r"liveedge2/(.*?)_")
_id_re = re.compile(r"\d+")


def parse_channels(txt):
    """解析内嵌频道文本 -> [(id, name, group, logo)]"""
    channels, group = [], "未分组"
    for raw in txt.splitlines():
        line = raw.strip().strip("\ufeff")
        if not line:
            continue
        if line.endswith(",#genre#"):
            group = line[:-len(",#genre#")].strip()
            continue
        if "," not in line:
            continue
        name, url = line.split(",", 1)
        name, url = name.strip(), url.strip()
        m = _id_re.search(url)
        if not m:
            continue
        logo = ""
        if "$logo=" in url:
            url, logo = url.split("$logo=", 1)
            logo = logo.strip()
        channels.append((int(m.group(0)), name, group, logo))
    return channels


CHANNELS = parse_channels(CHANNELS_TXT)
CHANNEL_BY_ID = {cid: (name, group, logo) for cid, name, group, logo in CHANNELS}

# 直连 opener：不读环境变量代理（源站地址必须直连，参考 pandalive 的 urllib 坑）
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_xml_cache = {"ts": 0.0, "xml": ""}
_xml_lock = threading.Lock()


def fetch_xml(force=False):
    """拉取 XML（带缓存），返回文本；失败返回 ''"""
    now = time.time()
    with _xml_lock:
        if not force and _xml_cache["xml"] and now - _xml_cache["ts"] < XML_CACHE_TTL:
            return _xml_cache["xml"]
    try:
        req = urllib.request.Request(XML_URL, headers={"User-Agent": "Mozilla/5.0"})
        with _opener.open(req, timeout=HTTP_TIMEOUT) as r:
            data = r.read().decode("utf-8", "replace")
    except Exception:
        data = ""
    with _xml_lock:
        if data:
            _xml_cache["ts"] = now
            _xml_cache["xml"] = data
        return _xml_cache["xml"] if data else _xml_cache["xml"]


def resolve_play_url(cid):
    """hatv.js main() 的 Python 移植：id -> 真实 m3u8 直链（失败返回 None）"""
    xml = fetch_xml()
    if not xml:
        return None
    m = _ad_url_re.search(xml)
    if not m:
        return None
    ch = _channel_re.search(m.group(1))
    if not ch:
        return None
    channel = ch.group(1)
    # 与 JS 一致：return { url: playUrl1 }（liveedge4 为主用）
    return (f"http://58.99.33.2:1935/liveedge4/{channel}_{cid}_1/chunklist_w.m3u8"
            "?checkCode=37050688asdfsdfsadf&aa=60999&as=abcdefg&mmmm=&dr=123&dt=&cust_type=NE")


class Handler(BaseHTTPRequestHandler):
    server_version = "hatv/1.0"

    def log_message(self, fmt, *args):  # 安静日志
        sys.stderr.write("[hatv] " + fmt % args + "\n")

    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _err(self, code, msg):  # message 必须 ASCII，否则 latin-1 炸连接
        self.send_error(code, msg)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/all.m3u":
            host = self.headers.get("Host", f"127.0.0.1:{DEFAULT_PORT}")
            base = f"http://{host}"
            out = ["#EXTM3U"]
            for cid, name, group, logo in CHANNELS:
                extinf = f'#EXTINF:-1 tvg-id="hatv-{cid}" group-title="{group}"'
                if logo:
                    extinf += f' tvg-logo="{logo}"'
                out.append(f"{extinf},{name}")
                out.append(f"{base}/live/{cid}.m3u8")
            self._send(200, "\n".join(out) + "\n",
                       "application/x-mpegurl; charset=utf-8")
            return

        m = re.match(r"^/live/(\d+)\.m3u8$", path)
        if m:
            cid = int(m.group(1))
            if cid not in CHANNEL_BY_ID:
                self._err(404, "channel not found")
                return
            url = resolve_play_url(cid)
            if not url:
                self._err(502, "upstream xml fetch failed")
                return
            self.send_response(302)
            self.send_header("Location", url)
            self.end_headers()
            return

        if path in ("/", "/index"):
            self._send(200, "hatv ok\n/all.m3u subscription\n/live/<id>.m3u8 channel\n")
            return

        self._err(404, "not found")

    do_HEAD = do_GET


def build_m3u_direct():
    """一次性解析全部直链并生成 m3u 文本（--out 用）"""
    xml = fetch_xml(force=True)
    if not xml:
        raise RuntimeError("XML 拉取失败：连不上 58.99.33.12:8080，请确认本机网络")
    out = ["#EXTM3U"]
    for cid, name, group, logo in CHANNELS:
        url = resolve_play_url(cid)
        if not url:
            sys.stderr.write(f"[hatv] 跳过 {cid} {name}：解析失败\n")
            continue
        extinf = f'#EXTINF:-1 tvg-id="hatv-{cid}" group-title="{group}"'
        if logo:
            extinf += f' tvg-logo="{logo}"'
        out.append(f"{extinf},{name}")
        out.append(url)
    return "\n".join(out) + "\n"


def serve(bind, port):
    server = ThreadingHTTPServer((bind, port), Handler)
    server.daemon_threads = True
    sys.stderr.write(f"[hatv] serving on http://{bind}:{port}  "
                     f"订阅: http://{bind}:{port}/all.m3u  ({len(CHANNELS)} 频道)\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:  # 协作式关闭：停服务 -> 关线程池 -> 释放端口
        server.shutdown()
        server.server_close()
        sys.stderr.write("[hatv] stopped\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="哈TV 订阅服务 / m3u 生成")
    ap.add_argument("--serve", action="store_true", help="启动 HTTP 服务")
    ap.add_argument("--bind", default=DEFAULT_BIND)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--out", metavar="FILE", help="一次性写出 m3u 订阅文件")
    ap.add_argument("--print-url", metavar="ID", type=int, help="打印单个频道的真实直链")
    args = ap.parse_args(argv)

    if args.print_url is not None:
        cid = args.print_url
        if cid not in CHANNEL_BY_ID:
            print(f"未知 id: {cid}", file=sys.stderr)
            return 2
        url = resolve_play_url(cid)
        if not url:
            print("解析失败：XML 拉不到或格式不符", file=sys.stderr)
            return 1
        print(url)
        return 0

    if args.out:
        try:
            m3u = build_m3u_direct()
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 1
        try:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(m3u)
        except OSError as e:
            print(f"写文件失败: {e}\n（iOS 请用服务模式订阅 /all.m3u）", file=sys.stderr)
            return 1
        print(f"已写入 {args.out}（{m3u.count('#EXTINF')} 个频道）")
        return 0

    if args.serve or DEFAULT_SERVE:
        serve(args.bind, args.port)
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
