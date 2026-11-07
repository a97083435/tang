# 台湾电视直播 · FongMi 5.8.7

生成日期：2026-11-07。源地址均为当天拉取的公开聚合源，抓取脚本见 `grab_taiwan.py`。

## 文件（6 个，传到手机同一个文件夹里）

| 文件 | 用途 |
|---|---|
| `taiwan.py` | 爬虫本体，内嵌 73 个频道。点播和直播两种导入方式共用同一份 |
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

## 内嵌频道（73 个）

| 分组 | 数量 | 说明 |
|---|---|---|
| 台湾·新闻 | 16 | 东森新闻、TVBS新闻、三立新闻、中天新闻、民视新闻、台视新闻、华视新闻资讯、寰宇新闻、镜新闻、三立iNEWS、东森财经新闻、中视新闻、年代新闻、非凡新闻、寰宇台湾台、台视财经台 |
| 台湾·无线 | 5 | 台视、民视、中视、公视、华视 |
| 台湾·综合娱乐 | 33 | TVBS Asia、三立台湾台/都会台/综合台/戏剧台、民视台湾台/第一台/综艺台/影剧台、中天综合台/亚洲台/娱乐台、东森洋片台/YOYO/综合台/戏剧台/超视台、纬来体育/综合/戏剧/日本/育乐台、TVBS HD/欢乐台/精采台/台剧台、八大戏剧台、MOMO TV、公视3台/2台、中视经典台/菁采台 |
| 台湾·文化 | 6 | Taiwan Plus、客家电视台、原住民族电视台、大爱1/2台、大立电视台 |
| 台湾·宗教 | 7 | GOOD TV综合/真理台、Beautiful Life TV、CGNTV中文台、唯心电视台、无上师电视台、新唐人电视台 |
| 台湾·电影娱乐 | 6 | HBO/Cinemax/AXN/Animax亚洲台（转播源，存活不稳定）、探索频道亚洲台、东森购物60台、东森电影台 |

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
这次收的是公开源里能找到直链 HLS 的 73 个台。以下这些台在公开源里没有可用的直链 HLS，所以没收，不是漏写：
壹电视新闻台、公视台语台、东森幼幼台、非凡商业台、卫视中文台、好消息电视台、靖天系列、FOX 体育台等。
其中一部分（东森新闻、TVBS 新闻、三立新闻、中天新闻、民视新闻、台视新闻、华视新闻、寰宇新闻、镜新闻等）平时只在 YouTube 直播，没有官方 HLS；本次收的这几路走的是 `ythls.armelin.one` 这类第三方 YouTube 转 HLS 代理，能播多久看代理活多久。另有一部分线来自 lisb0910 社区列表的转播站（74.91、4gtv.cnlive.club、cdn.19891230.eu.org），是这批线里最不稳定的一档，播不了先切回 iptv-org 的线。想补某一个台：找到它官网/公众号的直播地址发我，我帮你加进去。

**2. 直播源会过期，部分限台湾/境外 IP。**
这些地址是第三方聚合的公开流，不是各台官网直出的稳定接口，会换地址、会失效、部分限台湾 IP、部分在大陆网络下打不开。本次逐条抽查 105 条地址：确认是 m3u8 的 33 条、有响应但非 m3u8 文本的 7 条、超时或失败的 65 条。其中 111.59.139.85、cdn.19891230.eu.org、nmk.ioapk.com、sanlihalive1-a.akamaihd.net、seb.sason.top、ythls.armelin.one 本机抽查全部失败（疑似境外网络受限或源端拦截），只代表本机抽查结果，不等于在手机上播不了。日常使用以手机实测为准；`taiwan.json` 里“台湾·iptv-org”那路是直接读最新列表，不用重新导。

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

也可以直接传频道 JSON 的 http(s) 地址，或传 `{"groups": [...]}`（与 `taiwan.json` 的 `groups` 同形）。不传就用内嵌的 73 个台。

## 来源

- iptv-org-streams：`https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tw.m3u`（拉到 56 条，保留 28 条线）
- iptv-org-countries：`https://iptv-org.github.io/iptv/countries/tw.m3u`（拉到 34 条，保留 8 条线）
- ChinaIPTV-TaiWan：`https://raw.githubusercontent.com/hujingguang/ChinaIPTV/main/TaiWan.m3u8`（拉到 20 条，保留 7 条线）
- lisb0910-tv：`https://raw.githubusercontent.com/lisb0910/tv/main/liveTVList.txt`（拉到 1231 条，保留 62 条线）
- taiwan-iptv-static：`https://raw.githubusercontent.com/limajj2021/taiwan-iptv/main/playlist_static.m3u`（只作 taiwan.json 远程备用源，不并入内嵌表：其中个别地址与台名明显不符）

EPG 与台标用的是公开的 `epg.112114.xyz`（`?ch={name}&date={date}` / `logo/{name}.png`），台湾台的节目表/台标不一定全，缺的会显示空白，不影响播放。

## 验证情况（2026-11-07）

| 检查 | 结果 |
|---|---|
| `taiwan.json` / `taiwan-config.json` JSON 解析 | 通过 |
| `taiwan.py` Python 语法（`py_compile`） | 通过 |
| `taiwan.py` 模拟载入：空 ext 载入 73 频道、首页/分类分页、搜索、详情（顺序保留、空 list、未知 ID 抛错）、播放、ext 覆盖频道、`liveContent` 全量/按分组/按单台 | 全部通过 |
| 播放地址抽查（境外服务器，本次逐条抽查 105 条地址：确认是 m3u8 的 33 条、有响应但非 m3u8 文本的 7 条、超时或失败的 65 条。其中 111.59.139.85、cdn.19891230.eu.org、nmk.ioapk.com、sanlihalive1-a.akamaihd.net、seb.sason.top、ythls.armelin.one 本机抽查全部失败（疑似境外网络受限或源端拦截），只代表本机抽查结果，不等于在手机上播不了。） | 见上文第 2 条 |
| FongMi 5.8.7 真机逐台点播 | **未验证**——格式按 FongMi 官方 CONFIG.md / SPIDER.md（`lives.groups`、`liveContent` 回 JSON groups）写，需要你在手机上按上面步骤走一遍 |

格式依据：FongMi/TV `docs/CONFIG.md`（Live 配置、`lives`、`groups`、`channel.urls`）、`docs/SPIDER.md`（`liveContent` 回 TXT / M3U / JSON 三种格式）。`taiwan.py` 的写法与大陆版 `live.py`、你之前那份 `yangshipin.py` 同一套新 API（`from base.spider import Spider`，同步 `def`，`self.net.json` / `self.net.req`，不用已移除的 `fetch` / `post` / `str2json` / `getCache`）。
