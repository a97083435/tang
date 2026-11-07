"""央视频 YangShiPin —— CatVodSpider Python 新写法。

来源
----
- 频道表：用户提供的 ``yangshipin_0_nhnt.json``（2026-10-31 生成，73 个频道），
  已内嵌为 ``CHANNELS``，ext 不传频道时也能直接用；ext 传了频道表则以 ext 为准，
  以后频道增减不用改代码。
- 播放接口：公开的 TvBox ysp.php 写法，
  ``POST https://player-api.yangshipin.cn/v1/player/get_live_info``，
  参数含 ``cnlid``、``cKey``（AES-128-CBC）、``signature``（MD5）。
- 写法规范：随附的《Python 爬虫旧 API 迁移》文档与 CatVodSpider
  ``examples/python/spider.py``（Kvymin/CatVodSpider，main 分支）。

新写法要点（对照迁移文档）
--------------------------
- ``from base.spider import Spider as BaseSpider``，``class Spider(BaseSpider)``，
  全部入口是同步 ``def``，不使用 async。
- 请求一律 ``self.net.json(url, options)`` / ``self.net.req(...)``，
  不用已移除的 ``self.fetch()`` / ``self.post()``，不回传 requests.Response。
- JSON 用标准库 ``json.loads`` / ``json.dumps``，入口直接回传 dict / list，
  不用 ``self.str2json()`` / ``self.json2str()``。
- ``init(extend="")`` 里 ``extend`` 是 JSON 字串，用 ``json.loads`` 解析；
  ``categoryContent`` 的 ``extend`` 已是 dict，不重复解析。
- ``detailContent(ids)`` 处理完整 ID list：逐笔 ``_detail``、保留输入顺序、
  不自行去重，空 list 不发请求，单笔找不到向外抛错，不捕捉后略过。
- ``searchContent(key, quick, pg="1")`` 双参数调用时 pg 默认 ``"1"``。
- ``playerContent(flag, id, vipFlags)`` 的 ``vipFlags`` 是完整 list（含空 list）。
- 不用 ``getCache`` / ``setCache`` / ``getName`` / ``getProxyUrl`` /
  ``localProxy`` / ``getDanmakuUrl`` / ``dialog.show`` / ``self.html`` /
  ``self.regStr`` 等已移除 API；不新增同名兼容层，不依赖 ``app.py`` /
  ``runtime`` 内部方法，不关闭共用 ``self.net``。
- ``timeout`` 单位毫秒，新默认 10000；这里播放请求明确传 15000。

AES 说明：Chaquopy 环境不保证装有 ``Crypto`` / ``cryptography``，
所以 ``cKey`` 的 AES-128-CBC 用纯标准库实现（S-box 由 GF(2^8) 求逆生成），
已用 FIPS-197 向量与 openssl 交叉验证通过，见文件末尾注释。

未验证 / 已知限制（2026-11-07 实测）
------------------------------------
- 本机（非中国大陆 IP）实测 ``get_live_info``：一次读超时，其余三次均回
  HTTP 401 空正文。401 发生在频道校验之前，所以**无法区分** JSON 里的
  ``cnlid``（如 CCTV1 的 2024078201）和 ysp.php 的旧 ``vid``
  （如 CCTV1 的 2000210103）哪个正确；本爬虫先试 JSON ``cnlid``，
  失败再试旧 ``vid``，两路都失败时回 ``{"msg": ...}``，不伪装成成功空列表。
- MyTV（lizongying/my-tv）的现行流程里 ``getLiveInfo`` 还要带
  ``Yspplayertoken`` 请求头，先向 token 服务取 token；ysp.php 的旧流程
  没有这个头，可能是 401 的原因之一。本爬虫支持 ext 传
  ``player_token``，有 token 时自动带上，没有也不强求。
- 央视频直播一般限中国大陆 IP，13 个 ``vip`` 频道（风云系列等）还可能要
  会员 / 登录；没有实机 App 播放验证，拿到 ``playurl`` 也不等于能播。
- ``liveContent`` / ``playerContent`` 的取流每次现算 ``cKey`` 与签名，
  不缓存播放地址，不写 Local / 持久缓存。

ext 格式（JSON 字串，二选一或留空）
------------------------------------
- 留空：用内嵌的 73 频道表。
- ``{"channels": [...]}``：与上传 JSON 同形，``channels`` 每项含
  ``name`` / ``pid`` / ``cnlid`` / ``logo`` / ``type``（yangshi/weishi）/
  ``vip``；也可以直接传频道数组，或传频道 JSON 的 http(s) 地址。
- 可选项：``defn``（默认 ``"fhd"``，可改 ``"hd"`` / ``"sd"`` / ``"auto"``）、
  ``player_token``（``Yspplayertoken``）、``guid``（默认 ``"0"``）、
  ``legacy_fallback``（默认 true）。
"""

import hashlib
import json
import re
import time
from urllib.parse import urlencode

from base.spider import Spider as BaseSpider

API_URL = "https://player-api.yangshipin.cn/v1/player/get_live_info"
WEB_URL = "https://www.yangshipin.cn/tv/home?pid={pid}"
PAGE_SIZE = 30
REQUEST_TIMEOUT_MS = 15000

PLATFORM = "5910204"
APP_VER = "V1.0.0"
SALT = "0f$IVHi9Qno?G"
_AES_KEY = bytes.fromhex("48e5918a74ae21c972b90cce8af6c8be")
_AES_IV = bytes.fromhex("9a7e7d23610266b1d9fbf98581384d92")

# 内嵌频道表：由 yangshipin_0_nhnt.json（2026-10-31）生成，
# 每项 (name, pid, cnlid, type, vip, logo)。ext 有频道表时会被覆盖。
CHANNELS = (
    ('CCTV1', '600001859', '2024078201', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/d57905b93540bd15f0c48230dbbbff7ee0d645ff539e38866e2d15c8b9f7dfcd.png?imageMogr2/format/webp'),
    ('CCTV2', '600001800', '2024075401', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/20115388de0207131af17eac86c33049b95d69eaff064e55653a1b941810a006.png?imageMogr2/format/webp'),
    ('CCTV3', '600001801', '2024068501', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/7b7a65c712450da3deb6ca66fbacf4f9aee00d3f20bd80eafb5ada01ec63eb3a.png?imageMogr2/format/webp'),
    ('CCTV4', '600001814', '2029797101', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/f357e58fdbcc076a3d65e1f958c942b2e14f14342c60736ceed98b092d35356a.png?imageMogr2/format/webp'),
    ('CCTV5', '600001818', '2024078401', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/0a6a7138952675983a3d854df7688557b286d59aa06166edae51506f9204d655.png?imageMogr2/format/webp'),
    ('CCTV5+', '600001817', '2024078001', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/649ad76a90bfef55b05db9fe52e006487280f619089099d5dc971e387fc6eff0.png?imageMogr2/format/webp'),
    ('CCTV6', '600108442', '2013693901', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/741515efda91f03f455df8a7da4ee11fa9329139c276435cf0a9e2af398d5bf2.png?imageMogr2/format/webp'),
    ('CCTV7', '600004092', '2024072001', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/b29af94e295ebdf646cefb68122c429b9cd921f498ca20d2d8070252536f9ff9.png?imageMogr2/format/webp'),
    ('CCTV8', '600001803', '2029793001', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/ad51de94426a0ba039e6dd6a8534ea98ecc813a6176bde87b4f18cc34d6d7590.png?imageMogr2/format/webp'),
    ('CCTV9', '600004078', '2024078601', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/2ed1b4deeca179d5db806bb941790f82eb92a1b7299c1c38fe027f95a5caee5e.png?imageMogr2/format/webp'),
    ('CCTV10', '600001805', '2024078701', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/aa6157ec65188cd41826e5a2f088c3d6d153205f5f6428258d12c59999e221aa.png?imageMogr2/format/webp'),
    ('CCTV11', '600001806', '2027248701', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/ed12ed7c7a1034dae4350011fe039284c5d5a836506b28c9e32e3c75299625c0.png?imageMogr2/format/webp'),
    ('CCTV12', '600001807', '2027248801', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/484083cffaa40df7e659565e8cb4d1cc740158a185512114167aa21fa0c59240.png?imageMogr2/format/webp'),
    ('CCTV13', '600001811', '2029797201', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/266da7b43c03e2312186b4a999e0f060e8f15b10d2cc2c9aa32171819254cf1a.png?imageMogr2/format/webp'),
    ('CCTV14', '600001809', '2027248901', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/af6b603896938dc346fbb16abfc63c12cba54b0ec9d18770a15d347d115f12d5.png?imageMogr2/format/webp'),
    ('CCTV15', '600001815', '2027249001', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/2ceee92188ef684efe0d8b90839c4f3ad450d179dc64d59beff417059453af47.png?imageMogr2/format/webp'),
    ('CCTV16-HD', '600098637', '2027249101', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/53793fa7bacd3a93ff6dc5d2758418985e1f952a316c335d663b572d8bdcd74d.png?imageMogr2/format/webp'),
    ('CCTV16(4K）', '600099502', '2027249301', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/53793fa7bacd3a93ff6dc5d2758418985e1f952a316c335d663b572d8bdcd74d.png?imageMogr2/format/webp'),
    ('CCTV17', '600001810', '2027249401', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/ddef563072f8bad2bea5b9e52674cb7b4ed50efb20c26e61994dfbdf05c1e3c0.png?imageMogr2/format/webp'),
    ('CCTV4K', '600002264', '2029810301', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/3e9d06fd7244d950df5838750f1c6ac3456e172b51caca2c16d2282125b111e8.png?imageMogr2/format/webp'),
    ('CCTV8K', '600156816', '2026774101', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202503/df543dd2e337be8bf6aa06342d8d790992f7ae47b89403606253436e40409031.png?imageMogr2/format/webp'),
    ('CGTN', '600014550', '2024181701', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/a72dff758ca1c17cd0ecc8cedc11b893d208f409d5e6302faa0e9d298848abc3.png?imageMogr2/format/webp'),
    ('CGTN法语频道', '600084704', '2024181801', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/a8d0046a47433d952bf6ed17062deb8bd2184ba9aec0f7781df6bf9487a3ffcf.png?imageMogr2/format/webp'),
    ('CGTN俄语频道', '600084758', '2024181901', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/bf0a820893cbaf20dd0333e27042e1ef9c8806e5b602b6a8c95af399db0bc77a.png?imageMogr2/format/webp'),
    ('CGTN阿拉伯语频道', '600084782', '2024182001', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/2e44e2aa3e7a1cedf07fd0ae59fe69e86a60a2632660a006e3e9e7397b2d107e.png?imageMogr2/format/webp'),
    ('CGTN西班牙语频道', '600084744', '2024182101', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202309/7c337e3dbe64402ec7e4678a619a4a6d95144e42f35161181ff78e143b7cf67a.png?imageMogr2/format/webp'),
    ('CGTN外语纪录频道', '600084781', '2024182301', 'yangshi', False, 'https://resources.yangshipin.cn/assets/oms/image/202309/74d3ac436a7e374879578de1d87a941fbf566d39d5632b027c5097891ed32bd5.png?imageMogr2/format/webp'),
    ('CCTV风云剧场频道', '600099658', '2025637103', 'yangshi', True, 'https://resources.yangshipin.cn/assets/oms/image/202306/4d549e53e6d0f632d5a633d1945280797b153e588f919221a07faa869812cc89.png?imageMogr2/format/webp'),
    ('CCTV第一剧场频道', '600099655', '2026874203', 'yangshi', True, 'https://resources.yangshipin.cn/assets/oms/image/202306/a556bd7d93ce65e18f243a8892b5604f4faa994a4897315914216a710a706208.png?imageMogr2/format/webp'),
    ('CCTV怀旧剧场频道', '600099620', '2026874303', 'yangshi', True, 'https://resources.yangshipin.cn/assets/oms/image/202306/5661bd04fecdb6e899f801147a22ab5d3a475bf2b62e30aec2c0023190ebc9b1.png?imageMogr2/format/webp'),
    ('CCTV世界地理频道', '600099637', '2026874403', 'yangshi', True, 'https://resources.yangshipin.cn/assets/oms/image/202306/bb3c6c9e145d698137f5bb64a582021a01b51344b929003630eb769ea65832a9.png?imageMogr2/format/webp'),
    ('CCTV风云音乐频道', '600099660', '2026874503', 'yangshi', True, 'https://resources.yangshipin.cn/assets/oms/image/202306/bbf1d024c5228b8dd128b0e3cb1717d173fab4ee84c3a4c8a57b1a215362ca3b.png?imageMogr2/format/webp'),
    ('CCTV兵器科技频道', '600099649', '2026874603', 'yangshi', True, 'https://resources.yangshipin.cn/assets/oms/image/202306/4c6b6a6d3839889f34d33db3c2f80233b26b74d3489b393487635f8704e70796.png?imageMogr2/format/webp'),
    ('CCTV风云足球频道', '600099636', '2026966203', 'yangshi', True, 'https://resources.yangshipin.cn/assets/oms/image/202306/cd1e2bb52b06a991de168733e5ff0f1d85adc8042d40c8f393f723543e5dd08a.png?imageMogr2/format/webp'),
    ('CCTV高尔夫·网球频道', '600099659', '2026874703', 'yangshi', True, 'https://resources.yangshipin.cn/assets/oms/image/202306/cdd1b31ede7a5ad049ed53d9a072422f829e72dd062ed2c19e077fdd01699071.png?imageMogr2/format/webp'),
    ('CCTV女性时尚频道', '600099650', '2026874803', 'yangshi', True, 'https://resources.yangshipin.cn/assets/oms/image/202306/fa28955ce8b2539d728bf4c6a13a46ff57ad76eae46627f7bcfb1ed8a613d3fc.png?imageMogr2/format/webp'),
    ('CCTV央视文化精品频道', '600099653', '2026874903', 'yangshi', True, 'https://resources.yangshipin.cn/assets/oms/image/202306/14ac5ce40482cacd3d4b37435222bfe86af2b452a2f04ecbfc1d13d76edd7c57.png?imageMogr2/format/webp'),
    ('CCTV央视台球频道', '600099652', '2026875003', 'yangshi', True, 'https://resources.yangshipin.cn/assets/oms/image/202306/10e14a92478011aa6c3c8562e62127f3b1908e29fcd78e4b2b24b9e6d3ec2fbc.png?imageMogr2/format/webp'),
    ('CCTV电视指南频道', '600099656', '2026875103', 'yangshi', True, 'https://resources.yangshipin.cn/assets/oms/image/202306/244d72c0eb1615ed7d51c2f5db5a67f306aa3f58c05bc2d34de3aa7e956dc8c9.png?imageMogr2/format/webp'),
    ('CCTV卫生健康频道', '600099651', '2025637003', 'yangshi', True, 'https://resources.yangshipin.cn/assets/oms/image/202306/54a6863656fdfd8f803be193ddf22441c5000a108833889816fd2d8911715ce8.png?imageMogr2/format/webp'),
    ('北京卫视', '600002309', '2024052703', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/f4f23633c578beea49a3841d88d3490100f029ee349059fa532869db889872c5.png?imageMogr2/format/webp'),
    ('江苏卫视', '600002521', '2024171103', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/380ad685c0c1d5b2c902246b8d2df6d3f9b45e2837abcfe493075bbded597a31.png?imageMogr2/format/webp'),
    ('东方卫视', '600002483', '2024054503', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/9bd372ca292a82ce3aa08772b07efc4af1f85c21d1f268ea33440c49e9a0a488.png?imageMogr2/format/webp'),
    ('浙江卫视', '600002520', '2024054703', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/a66c836bd98ba3e41a2e9a570d4b9c50dedc6839e9de333e2e78212ad505f37e.png?imageMogr2/format/webp'),
    ('湖南卫视', '600002475', '2024054803', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/4120e89d3079d08aa17d382f69a2308ec70839b278367763c34a34666c75cb88.png?imageMogr2/format/webp'),
    ('湖北卫视', '600002508', '2024171203', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/7a6be5a2bb1dc53a945c016ff1f525dc4a84c51db371c15c89aa55404b0ba784.png?imageMogr2/format/webp'),
    ('广东卫视', '600002485', '2024060903', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/28886880a4dc0f06fb7e0a528a1def0591d61a65870e29176ede0cc92033bbfd.png?imageMogr2/format/webp'),
    ('广西卫视', '600002509', '2024060703', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/54b7e97cb816bb223fe05f3fc44da2c7820eb66e8550c19d23100f2c414ecc38.png?imageMogr2/format/webp'),
    ('黑龙江卫视', '600002498', '2029797003', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/d8273ae9be698ce2db21f5b886ecac95a73429593f93713c60ed8c12c38bf0d3.png?imageMogr2/format/webp'),
    ('海南卫视', '600002506', '2024055603', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/6e060391fde0469801fc3d84dbf204b4f8d650d251f17d7595a6964c0bb99e81.png?imageMogr2/format/webp'),
    ('重庆卫视', '600002531', '2024061103', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/657651f411de2673d1770d9a78b44c1265704f7468cc41d4be7f51d630768494.png?imageMogr2/format/webp'),
    ('深圳卫视', '600002481', '2024061303', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/d59fec04c902e3581c617136d02d4b9b8c4cbe64272781ddd3525e80c823edb7.png?imageMogr2/format/webp'),
    ('四川卫视', '600002516', '2024061403', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/3276a414ae0eaa0f116f2045cd913367967d0c7c1e978e8621ac3879436c6ed7.png?imageMogr2/format/webp'),
    ('河南卫视', '600002525', '2029797303', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/74925962148a6d31c85808b6cd4e444c2a54bab393d2c5fc85e960b50e22fa86.png?imageMogr2/format/webp'),
    ('福建东南卫视', '600002484', '2024061503', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/3208fe6564a293c21b711333fb3edb05bb5b406cff840573c9a8d839680a1579.png?imageMogr2/format/webp'),
    ('贵州卫视', '600002490', '2024061603', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/4eb45f4781d33d872af027dc01c941559aab55667dd99cc5c22bef7037807b13.png?imageMogr2/format/webp'),
    ('江西卫视', '600002503', '2024061703', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/3c760d0d00463855890e8a1864ea4a6b6dd66b90c29b4ac714a4b17c16519871.png?imageMogr2/format/webp'),
    ('辽宁卫视', '600002505', '2024171303', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/ac4ed6058a87c101ae7147ebc38905d0cae047fb73fd277ee5049b84f52bda36.png?imageMogr2/format/webp'),
    ('安徽卫视', '600002532', '2024171403', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/f35fa04b51b1ee4984b03578b65403570868ebca03c6c01e11b097f999a58d9b.png?imageMogr2/format/webp'),
    ('河北卫视', '600002493', '2024171503', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/d545becdc81c60197b08c7f47380705e4665ed3fe55efc8b855e486f6e655378.png?imageMogr2/format/webp'),
    ('山东卫视', '600002513', '2029787903', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202306/22d403f07a7cf5410b3ad3ddb65a11aa229a32475fac213f5344c9f0ec330ca1.png?imageMogr2/format/webp'),
    ('天津卫视', '600152137', '2019927003', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202411/2642bf96eaf49fdc6b08db2cf6a3d8a7c30824bbcc199985e70e8b8846c5d14d.png?imageMogr2/format/webp'),
    ('吉林卫视', '600190405', '2025561503', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202411/cfe6b0f01c7e381471b774f5a9f615e1bb70b946ad658da9ed6fcae28d752881.png?imageMogr2/format/webp'),
    ('陕西卫视', '600190400', '2029795103', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202411/b63ce6fd91a92076273ea2d4679bfbe367ece51a114b54b79a66bc8de5831fa0.png?imageMogr2/format/webp'),
    ('甘肃卫视', '600190408', '2025561703', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202411/ed4e35722f6d07f19274cac60eec0cc9e1205776c246a3717c2e9152025b3ddd.png?imageMogr2/format/webp'),
    ('宁夏卫视', '600190737', '2025608503', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202411/8392c1ee75dca2a13f6dc0efa37519be4284764fecd65415a1a9f55b11534c5b.png?imageMogr2/format/webp'),
    ('内蒙古卫视', '600190401', '2025561203', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202411/fe60396ae9ead3125d763146d8bc1e9b51ed8e19e8dc61600e28cc0b2f2d28c7.png?imageMogr2/format/webp'),
    ('云南卫视', '600190402', '2025561303', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202411/907600c544719ffdaa6b6fa177d91b530dc9ce38e3dfd43a14ea7c805a7df97d.png?imageMogr2/format/webp'),
    ('山西卫视', '600190407', '2025560803', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202411/d9fe4441f6adcfe9fd7ee2e45bf46d2a355b0fa48ff10dbba12978d2f8cf9780.png?imageMogr2/format/webp'),
    ('青海卫视', '600190406', '2025559103', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202411/182e779878c85642049514a6e033f6be41aa8bf5f489fadc6f63dfc50863c36d.png?imageMogr2/format/webp'),
    ('西藏卫视', '600190403', '2025558003', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202411/37f9668cded5cc19848cfe7dcaf717de4acc47667dde656ba2646aba372eebbe.png?imageMogr2/format/webp'),
    ('中国教育电视台1频道', '600171827', '2022823801', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202412/2b9301a4795c7f23b7ec7ed651d8c7df002ce8c608168970485999b03d29f783.png?imageMogr2/format/webp'),
    ('新疆卫视', '600152138', '2019927403', 'weishi', False, 'https://resources.yangshipin.cn/assets/oms/image/202412/005fd504f809ab28ec8cdd5d34d3886f0611ddefa20ebcc0f3f7dc176ad528c7.png?imageMogr2/format/webp'),
)

# 旧 vid 对照表（ysp.php 的 YSP_CHANNEL）：JSON cnlid 取流失败时的第二路尝试。
# 只收录名字能与 JSON 频道一一对应的条目，未收录的频道没有第二路。
LEGACY_CNLID = {
    "CCTV4K": "2000266303", "CCTV8K": "2020603401", "CCTV1": "2000210103",
    "CCTV2": "2000203603", "CCTV3": "2000203803", "CCTV4": "2000204803",
    "CCTV5": "2000205103", "CCTV5+": "2000204503", "CCTV6": "2000203303",
    "CCTV7": "2000510003", "CCTV8": "2000203903", "CCTV9": "2000499403",
    "CCTV10": "2000203503", "CCTV11": "2000204103", "CCTV12": "2000202603",
    "CCTV13": "2000204603", "CCTV14": "2000204403", "CCTV15": "2000205003",
    "CCTV16-HD": "2012375003", "CCTV16(4K）": "2012492303",
    "CCTV17": "2000204203",
    "CCTV风云剧场频道": "2012513603", "CCTV第一剧场频道": "2012514403",
    "CCTV怀旧剧场频道": "2012511203", "CCTV世界地理频道": "2012513303",
    "CCTV风云音乐频道": "2012514103", "CCTV兵器科技频道": "2012513403",
    "CCTV风云足球频道": "2012514203", "CCTV高尔夫·网球频道": "2012512503",
    "CCTV女性时尚频道": "2012513903", "CCTV央视文化精品频道": "2012513803",
    "CCTV央视台球频道": "2012513703", "CCTV电视指南频道": "2012514003",
    "CCTV卫生健康频道": "2012513503",
    "CGTN": "2001656803", "CGTN法语频道": "2010153503",
    "CGTN俄语频道": "2010152603", "CGTN阿拉伯语频道": "2010155203",
    "CGTN西班牙语频道": "2010152503", "CGTN外语纪录频道": "2010155403",
    "北京卫视": "2000272103", "江苏卫视": "2000295603",
    "东方卫视": "2000292403", "浙江卫视": "2000295503",
    "湖南卫视": "2000296203", "湖北卫视": "2000294503",
    "广东卫视": "2000292703", "广西卫视": "2000294203",
    "黑龙江卫视": "2000293903", "海南卫视": "2000291503",
    "重庆卫视": "2000297803", "深圳卫视": "2000292203",
    "四川卫视": "2000295003", "河南卫视": "2000296103",
    "福建东南卫视": "2000292503", "贵州卫视": "2000293303",
    "江西卫视": "2000294103", "辽宁卫视": "2000281303",
    "安徽卫视": "2000298003", "河北卫视": "2000293403",
    "山东卫视": "2000294803", "天津卫视": "2019927003",
    "新疆卫视": "2019927403",
}


# ---------------------------------------------------------------- AES-128
# 纯标准库实现，只用于加密，不解密。S-box 由 GF(2^8) 求逆 + 仿射变换生成。
def _gf_mul(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xFF
        if hi:
            a ^= 0x1B
        b >>= 1
    return p


def _gf_pow(a, e):
    r = 1
    while e:
        if e & 1:
            r = _gf_mul(r, a)
        a = _gf_mul(a, a)
        e >>= 1
    return r


def _rotl8(x, n):
    return ((x << n) | (x >> (8 - n))) & 0xFF


_SBOX = []
for _x in range(256):
    _inv = 0 if _x == 0 else _gf_pow(_x, 254)
    _SBOX.append(
        _inv ^ _rotl8(_inv, 1) ^ _rotl8(_inv, 2) ^ _rotl8(_inv, 3) ^ _rotl8(_inv, 4) ^ 0x63
    )
_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


def _expand_key(key):
    w = [list(key[i * 4:(i + 1) * 4]) for i in range(4)]
    for i in range(4, 44):
        t = list(w[i - 1])
        if i % 4 == 0:
            t = t[1:] + t[:1]
            t = [_SBOX[b] for b in t]
            t[0] ^= _RCON[i // 4 - 1]
        w.append([w[i - 4][j] ^ t[j] for j in range(4)])
    return w


def _encrypt_block(block, key):
    w = _expand_key(key)
    s = [[block[c * 4 + r] for c in range(4)] for r in range(4)]

    def add_round(rk):
        for r in range(4):
            for c in range(4):
                s[r][c] ^= w[rk * 4 + c][r]

    def sub_bytes():
        for r in range(4):
            for c in range(4):
                s[r][c] = _SBOX[s[r][c]]

    def shift_rows():
        for r in range(1, 4):
            s[r] = s[r][r:] + s[r][:r]

    def mix_columns():
        for c in range(4):
            a = [s[r][c] for r in range(4)]
            s[0][c] = _gf_mul(a[0], 2) ^ _gf_mul(a[1], 3) ^ a[2] ^ a[3]
            s[1][c] = a[0] ^ _gf_mul(a[1], 2) ^ _gf_mul(a[2], 3) ^ a[3]
            s[2][c] = a[0] ^ a[1] ^ _gf_mul(a[2], 2) ^ _gf_mul(a[3], 3)
            s[3][c] = _gf_mul(a[0], 3) ^ a[1] ^ a[2] ^ _gf_mul(a[3], 2)

    add_round(0)
    for rnd in range(1, 10):
        sub_bytes()
        shift_rows()
        mix_columns()
        add_round(rnd)
    sub_bytes()
    shift_rows()
    add_round(10)
    return bytes(s[r][c] for c in range(4) for r in range(4))


def _aes128_cbc_encrypt(plain, key, iv):
    pad = 16 - len(plain) % 16
    plain = plain + bytes([pad]) * pad
    out = b""
    prev = iv
    for i in range(0, len(plain), 16):
        block = bytes(a ^ b for a, b in zip(plain[i:i + 16], prev))
        prev = _encrypt_block(block, key)
        out += prev
    return out


# ---------------------------------------------------------------- 爬虫
class Spider(BaseSpider):
    def init(self, extend=""):
        options = {}
        if extend:
            text = extend.strip()
            if text.startswith("http://") or text.startswith("https://"):
                # ext 是频道 JSON 的地址：现取一次，取不到就用内嵌表，不让 init 炸掉。
                try:
                    options = self.net.json(text, {"timeout": REQUEST_TIMEOUT_MS})
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

        channels = options.get("channels") or options.get("list") or []
        if isinstance(channels, str):
            channels = json.loads(channels)
        if channels:
            self.channels = [self._normalize(item) for item in channels]
        else:
            self.channels = [self._normalize(item) for item in CHANNELS]
        self.by_pid = {item["pid"]: item for item in self.channels if item["pid"]}
        self.by_name = {item["name"]: item for item in self.channels}
        self.by_cnlid = {item["cnlid"]: item for item in self.channels if item["cnlid"]}
        self.defn = str(options.get("defn") or "fhd")
        self.player_token = str(
            options.get("player_token") or options.get("ysp_token") or ""
        ).strip()
        self.guid = str(options.get("guid") or "0")
        self.legacy_fallback = options.get("legacy_fallback", True) is not False

    @staticmethod
    def _normalize(item):
        if isinstance(item, (list, tuple)):
            name, pid, cnlid, kind, vip, logo = (list(item) + ["", "", "", "", False, ""])[:6]
        else:
            name = item.get("name", "")
            pid = item.get("pid", "")
            cnlid = item.get("cnlid", "")
            kind = item.get("type", "")
            vip = item.get("vip", False)
            logo = item.get("logo", "")
        return {
            "name": str(name),
            "pid": str(pid),
            "cnlid": str(cnlid),
            "type": "weishi" if str(kind) == "weishi" else "yangshi",
            "vip": bool(vip),
            "logo": str(logo),
        }

    def homeContent(self, filter):
        return {
            "class": [
                {"type_id": "yangshi", "type_name": "央视"},
                {"type_id": "weishi", "type_name": "卫视"},
            ]
        }

    def homeVideoContent(self):
        return {"list": [self._card(item) for item in self.channels]}

    def categoryContent(self, tid, pg, filter, extend):
        extend = extend if isinstance(extend, dict) else {}
        if tid == "all":
            items = self.channels
        elif tid in ("yangshi", "weishi"):
            items = [item for item in self.channels if item["type"] == tid]
        else:
            items = []
        return self.page([self._card(item) for item in items], pg, PAGE_SIZE)

    def searchContent(self, key, quick, pg="1"):
        query = str(key or "").strip().casefold()
        if not query:
            return self.page([], pg, PAGE_SIZE)
        matches = [
            item for item in self.channels
            if query in item["name"].casefold()
            or query in item["pid"]
            or query in item["cnlid"]
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
        channel = self._lookup(str(video_id))
        if channel is None:
            raise ValueError("找不到频道：%s" % video_id)
        item = self._card(channel)
        flags = ["央视频"]
        urls = ["直播$%s|%s" % (channel["pid"], channel["cnlid"])]
        legacy = LEGACY_CNLID.get(channel["name"], "")
        if legacy and legacy != channel["cnlid"]:
            flags.append("央视频·旧ID")
            urls.append("直播$%s|%s" % (channel["pid"], legacy))
        item.update({
            "type_name": "央视" if channel["type"] == "yangshi" else "卫视",
            "vod_year": "",
            "vod_area": "中国",
            "vod_director": "",
            "vod_actor": "",
            "vod_content": "%s直播%s" % (
                channel["name"],
                "（会员频道，可能需要登录/会员）" if channel["vip"] else "（央视频官方直播）",
            ),
            "vod_play_from": "$$$".join(flags),
            "vod_play_url": "$$$".join(urls),
        })
        return {"list": [item]}

    def playerContent(self, flag, id, vipFlags):
        # vipFlags 是完整 list（含空 list），这里只作记录，不改变取流逻辑：
        # VIP 与否以频道表为准，取流失败时由接口回的 msg 说明。
        _ = vipFlags
        channel, cnlid = self._parse_play_id(id)
        if channel is None:
            return {"parse": 0, "msg": "无效的播放 ID：%s" % id}
        playurl, error = self._get_playurl(channel, cnlid)
        if not playurl and self.legacy_fallback:
            legacy = LEGACY_CNLID.get(channel["name"], "")
            if legacy and legacy != cnlid:
                playurl, error = self._get_playurl(channel, legacy)
        if not playurl:
            return {
                "parse": 0,
                "msg": "央视频取流失败：%s（已试 cnlid=%s；可能需要 player_token、"
                       "中国大陆 IP，或该频道需会员/登录）" % (error or "接口未返回 playurl", cnlid),
            }
        return {
            "parse": 0,
            "jx": 0,
            "url": playurl,
            "header": {
                "Referer": "https://www.yangshipin.cn/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            },
            "list": [self._detail(channel["pid"])["list"][0]],
        }

    def liveContent(self, url):
        text = str(url or "").strip()
        if text.lower().split("?", 1)[0].endswith((".m3u8", ".mp4", ".flv")):
            return [{"name": "央视频", "channel": [{"name": "直播", "urls": [text + "$直播"]}]}]
        channel = self._lookup(text)
        if channel is None:
            raise ValueError("liveContent 找不到频道：%s" % url)
        playurl, error = self._get_playurl(channel, channel["cnlid"])
        if not playurl and self.legacy_fallback:
            legacy = LEGACY_CNLID.get(channel["name"], "")
            if legacy and legacy != channel["cnlid"]:
                playurl, error = self._get_playurl(channel, legacy)
        if not playurl:
            raise RuntimeError("央视频取流失败：%s" % (error or "接口未返回 playurl"))
        return [{
            "name": "央视频",
            "channel": [{"name": channel["name"], "urls": [playurl + "$直播"]}],
        }]

    # -- 取流 -------------------------------------------------------------
    def _parse_play_id(self, play_id):
        text = str(play_id or "").strip()
        # detail 给的格式：pid|cnlid；也兼容只传 pid / 频道名 / 网页地址。
        if "|" in text:
            pid, cnlid = text.split("|", 1)
            channel = self.by_pid.get(pid) or self.by_name.get(pid)
            return channel, cnlid.strip()
        channel = self._lookup(text)
        if channel is None:
            return None, ""
        return channel, channel["cnlid"]

    def _lookup(self, text):
        text = str(text or "").strip()
        if not text:
            return None
        if text in self.by_pid:
            return self.by_pid[text]
        if text in self.by_name:
            return self.by_name[text]
        if text in self.by_cnlid:
            return self.by_cnlid[text]
        match = re.search(r"[?&]pid=(\d+)", text)
        if match and match.group(1) in self.by_pid:
            return self.by_pid[match.group(1)]
        return None

    def _get_playurl(self, channel, cnlid):
        """调 get_live_info，成功回 (playurl, None)，失败回 (None, 原因)。"""
        try:
            payload = self._signed_payload(cnlid)
            data = self.net.json(API_URL, {
                "method": "POST",
                "postType": "json",
                "data": payload,
                "headers": self._api_headers(),
                "timeout": REQUEST_TIMEOUT_MS,
            })
        except Exception as error:
            return None, "%s：%s" % (type(error).__name__, error)
        if not isinstance(data, dict):
            return None, "接口回的不是 JSON 对象"
        if data.get("code") != 0:
            return None, "接口 code=%s msg=%s" % (data.get("code"), data.get("msg") or data.get("message") or "")
        playurl = (data.get("data") or {}).get("playurl") if isinstance(data.get("data"), dict) else None
        if not playurl:
            return None, "接口 code=0 但 data.playurl 为空"
        return str(playurl), None

    def _signed_payload(self, cnlid):
        now = int(time.time())
        payload = {
            "adjust": 1,
            "appVer": APP_VER,
            "app_version": APP_VER,
            "cKey": self._ckey(str(cnlid), now),
            "channel": "ysp_tx",
            "cmd": "2",
            "cnlid": str(cnlid),
            "defn": self.defn,
            "devid": "devid",
            "dtype": 1,
            "encryptVer": "8.1",
            "guid": self.guid,
            "otype": "ojson",
            "platform": PLATFORM,
            "rand_str": str(now),
            "sphttps": "1",
            "stream": "2",
        }
        # 与 PHP http_build_query 一致：按插入顺序 urlencode 后拼 salt 再 MD5。
        payload["signature"] = hashlib.md5(
            (urlencode(list(payload.items())) + SALT).encode("utf-8")
        ).hexdigest()
        return payload

    def _ckey(self, cnlid, now):
        # ysp.php 的 __getKey：先算 32 位 hash，再拼串做 AES-128-CBC。
        plain = "|%s|%s|mg3c3b04ba|V1.0.0|%s|%s|https://www.yangshipin.c|mozilla/5.0 (windows nt ||Mozilla|Netscape|Win32|" % (
            cnlid, now, self.guid, PLATFORM,
        )
        key = 0
        for ch in plain:
            key = ((key << 5) - key + ord(ch)) & 0xFFFFFFFF
        signed = key - 4294967296 if key > 2147483648 else key
        cipher = _aes128_cbc_encrypt(
            ("|" + str(signed) + plain).encode("utf-8"), _AES_KEY, _AES_IV
        )
        return "--01" + cipher.hex().upper()

    def _api_headers(self):
        headers = {
            "Content-Type": "application/json",
            "Referer": "https://www.yangshipin.cn/",
            "Cookie": "guid=0;vplatform=109",
            "Yspappid": "519748109",
        }
        if self.player_token:
            headers["Yspplayertoken"] = self.player_token
        return headers

    @staticmethod
    def _card(channel):
        return {
            "vod_id": channel["pid"],
            "vod_name": channel["name"],
            "vod_pic": channel["logo"],
            "vod_remarks": "VIP" if channel["vip"] else "直播",
            "type_name": "央视" if channel["type"] == "yangshi" else "卫视",
        }
