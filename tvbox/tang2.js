{

  "spider": "./tvkj.jar",

  "wallpaper": "https://深色壁纸.xxooo.cf/",

  "logo": "https://qixing.myhkw.com/tw.jpg",

  "warningText": "资源来自网络，无盈利纯技术分享！[所有内容仅供学习使用，请勿用于违法及商业用途，请勿付费购买]",

  "lives": [

    {

      "name": "天微livev1",

      "type": 0,

      "url": "https://7337.kstore.space/twkj/tvzb.txt",

      "ua": "okhttp/3.15",

      "playerType": 1,

      "epg": "http://diyp2.112114.xyz/?ch={name}&date={date}",

      "logo": "http://diyp2.112114.xyz/logo/{name}.png"

    },

        {

      "name": "天微livev2",

      "type": 0,

      "url": "https://tv.iill.top/m3u/Gather",

      "playerType": 2,

      "ua": "okhttp/5.0.0-alpha.14",

      "epg": "http://epg.51zmt.top:8000/api/diyp/?ch={name}&date={date}",

      "logo": "https://epg.112114.xyz/logo/{name}.png"

    },

        {

      "name": "天微livev3",

      "type": 0,

      "url": "https://cdn.jsdelivr.net/gh/Guovin/iptv-api@gd/output/result.m3u",

      "epg": "https://epg.112114.eu.org/?ch={name}&date={date}",

      "logo": "https://epg.112114.eu.org/logo/{name}.png"

    }

  ],

  "sites": [

    {

      "key": "豆瓣",

      "name": "公众号：天微科技 提示：自用测试禁止传播，免费资源切勿购买",

      "type": 3,

      "api": "csp_Douban",

      "searchable": 0,

      "changeable": 1

    },

    {

      "key": "配置中心",

      "name": "网盘配置┃中心",

      "type": 3,

      "api": "csp_Config",

      "searchable": 0,

      "changeable": 0,

      "indexs": 0,

      "style": {

        "type": "rect",

        "ratio": 1.43

      }

    },

    {

      "key": "好趣网",

      "name": "《好趣🔹直播》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "order_num": 87,

      "ext": "./lib/好趣网.js"

    },

    {

      "key": "alllive",

      "name": "《平台🔹直播》",

      "type": 3,

      "api": "csp_Alllive",

      "playerType": 2,

      "searchable": 0,

      "quickSearch": 0,

      "changeable": 0,

      "ext": {

        "danmu": true

      },

      "timeout": 10

    },

    {

      "key": "csp_JPYY",

      "name": "《金牌🔹秒播》",

      "type": 3,

      "searchable": 1,

      "changeable": 1,

      "api": "csp_Jpyy",

      "jar": "./lib/1020.jar",

      "playerType": 1,

      "filterable": 1,

      "ext": ""

    },

    {

      "key": "🌞腾腾4K解析_js",

      "name": "《免扫🔹腾4K》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "order_num": 0,

      "ext": "./lib/腾腾4K.js"

    },

    {

      "key": "果果4K解析_js",

      "name": "《免扫🔹果4K》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "order_num": 0,

      "ext": "./lib/果果4K.js"

    },

    {

      "key": "白嫖皮虾",

      "name": "《免扫🔹虾4K》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "order_num": 0,

      "ext": "./lib/皮皮虾4K.js"

    },

    {

      "key": "腾讯",

      "name": "《腾翼🔹翔天》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "ext": "./lib/腾讯VIP.js"

    },

    {

      "key": "芒果",

      "name": "《金辉🔹玉果》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "ext": "./lib/芒果.js"

    },

    {

      "key": "金牌影视",

      "name": "《天微🔹影院》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "ext": "./lib/金牌影视.js"

    },

    {

      "key": "优酷",

      "name": "《流光🔹酷影》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "ext": "./lib/优酷.js"

    },

    {

      "key": "csp_Xlys",

      "name": "《滴滴🔹影时》",

      "api": "csp_Xlys",

      "jar": "./lib/1020.jar",

      "type": 3,

      "playerType": 2

    },

    {

      "key": "天天弹幕版",

      "name": "《天天🔹弹幕》",

      "type": 3,

      "api": "csp_TianTian",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "ext": {

        "danmu": true

      },

      "timeout": 10

    },

    {

      "key": "嫖嫖嫖",

      "name": "《嫖嫖🔹秒播》",

      "type": 3,

      "api": "csp_XBPQ",

      "ext": {

        "主页url": "https://www.gs4x7nq4.com/",

        "播放请求头": "User-Agent$Mozilla/5.0(WindowsNT10.0;Win64;x64)AppleWebKit/537.36(KHTML,likeGecko)Chrome/128.0.0.0Safari/537.36",

        "简介": "⚠️天微科技特别提醒您⚠️请勿相信影片中的广告，以免上当受骗❗️+</label>&&</div>",

        "嗅探词": ".mp4#.m3u8#.flv#.m3u8?#.mp4?",

        "影片类型": "tags\">&&director\">",

        "影片状态": "bottom\">&&</div>",

        "二次截取": "videoList\":\\[&&\\]",

        "数组": "{&&}[不包含:伦理剧]",

        "图片": "https+://ywxohs.com+obs.gduamoe.com&&\",",

        "标题": "vodName\":\"&&\"",

        "副标题": "vodRemarks\":\"&&\"",

        "链接": "https://www.gs4x7nq4.com/detail/+vodId\":&&,",

        "导演": "导演:</div>&&主演",

        "主演": "主演:</div>&&别名",

        "线路标题": "天微科技",

        "播放数组": "listitem\">&&info\">",

        "播放列表": "<a&&</a>",

        "倒序": "否",

        "搜索url": "https://www.gs4x7nq4.com/vod/search/{wd}",

        "搜索副标题": "class=\"boottom\"*<div>&&</div",

        "分类": "电影$1#电视剧$2#综艺$3#动漫$4",

        "分类url": "https://www.gs4x7nq4.com/vod/show/id/{cateId}/class/{class}/year/{year}/area/{area}/page/{catePg}"

      }

    },

    {

      "key": "荐片",

      "name": "《荐片🔹官源》",

      "type": 3,

      "searchable": 1,

      "quickSearch": 1,

      "changeable": 1,

      "playerType": "1",

      "api": "./lib/drpy2.min.js",

      "ext": "./lib/jp.js"

    },

    {

      "key": "小苹果弹幕版",

      "name": "《苹果🔹秒播》",

      "type": 3,

      "api": "csp_Xpg",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "ext": {

        "danmu": true

      },

      "timeout": 10

    },

    {

      "key": "文才",

      "name": "《文采🔹秒播》",

      "type": 3,

      "api": "csp_Jpys",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "ext": {

        "danmu": true

      },

      "timeout": 10

    },

    {

      "key": "荐片弹幕版",

      "name": "《荐片🔹弹幕》",

      "type": 3,

      "api": "csp_Jianpian",

      "searchable": 1,

      "changeable": 0,

      "quickSearch": 1,

      "filterable": 1,

      "ext": {

        "danmu": true

      },

      "timeout": 10

    },

    {

      "key": "zhaixing",

      "name": "《星星🔹影院》",

      "type": 3,

      "api": "csp_AppZX",

      "jar": "./lib/1020.jar",

      "playerType": 2

    },

    {

      "key": "csp_XSX",

      "name": "《视讯🔹秒播》",

      "type": 3,

      "searchable": 1,

      "changeable": 1,

      "quickSearch": 1,

      "api": "csp_Xsx",

      "jar": "./lib/1020.jar",

      "playerType": 2,

      "filterable": 1,

      "ext": ""

    },

    {

      "key": "csp_zhufan",

      "name": "《追剧🔹秒播》",

      "searchable": 1,

      "quickSearch": 1,

      "type": 3,

      "api": "csp_MiTo",

      "jar": "./lib/1020.jar",

      "ext": {

        "url": "http://103.88.35.251:8989",

        "dataKey": "aassddwwxxllsx1x",

        "playKey": "bbssqdbbssll25sx",

        "version": "2.1.0"

      }

    },

    {

      "key": "宝片视频_js",

      "name": "《宝片🔹官源》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "order_num": 0,

      "ext": "./lib/宝片视频.js"

    },

    {

      "key": "瓜子",

      "name": "《瓜子🔹秒播》",

      "type": 3,

      "searchable": 1,

      "quickSearch": 1,

      "changeable": 1,

      "playerType": "1",

      "api": "./lib/drpy2.min.js",

      "ext": "./lib/瓜子.js"

    },

    {

      "key": "闪雷影视",

      "name": "《雷电🔹影视》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "ext": "./lib/闪雷影视.js"

    },

    {

      "key": "csp_UC",

      "name": "《小米🔹UC4K》",

      "type": 3,

      "api": "csp_MiUc",

      "jar": "./lib/1020.jar",

      "filterable": 1,

      "ext": {

        "site_urls": [

          "http://www.mucpan.cc",

          "http://ucmi.fun",

          "http://www.ucmi.fun"

        ],

        "url_key": "MiUc",

        "threadinfo": {

          "chunksize": 450,

          "threads": 10

        }

      }

    },

    {

      "key": "木偶网盘",

      "name": "《木偶🔹UC4K》",

      "type": 3,

      "api": "csp_Wobg",

      "searchable": 1,

      "filterable": 1,

      "changeable": 1,

      "ext": {

        "token": "http://127.0.0.1:9978/file/tvbox/tok.txt",

        "cookie": "http://127.0.0.1:9978/file/tvbox/quark.txt",

        "uc_cookie": "http://127.0.0.1:9978/file/tvbox/uc.txt",

        "site": "http://www.mogg.top/",

        "danmu": true

      },

      "timeout": 25

    },

    {

      "key": "csp_Wogg",

      "name": "《玩偶🔹哥4K》",

      "type": 3,

      "api": "csp_Wogg",

      "jar": "./lib/1020.jar",

      "changeable": 0,

      "filterable": 1,

      "ext": {

        "site_urls": [

          "http://woggpan.333232.xyz/",

          "http://wogg.xxooo.cf/",

          "http://woggapi.888484.xyz/",

          "http://www.wogg.net"

        ],

        "threadinfo": {

          "chunksize": 450,

          "threads": 12

        }

      }

    },

    {

      "key": "爱奇",

      "name": "《艺梦🔹流年》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "ext": "./lib/爱奇艺.js"

    },

    {

      "key": "搜狗",

      "name": "《搜罗🔹万象》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "ext": "./lib/搜狗.js"

    },

    {

      "key": "cjzy_360资源",

      "name": "《琉零🔹织散》",

      "type": 1,

      "api": "https://360zy.com/api.php/provide/vod",

      "playUrl": "",

      "categories": [

        "国产剧",

        "国产动漫",

        "香港剧",

        "台湾剧",

        "欧美剧",

        "日韩动漫",

        "NBA",

        "短片",

        "西部片",

        "综艺片",

        "动漫片",

        "动作片",

        "喜剧片",

        "爱情片",

        "科幻片",

        "恐怖片",

        "惊悚片",

        "悬疑片",

        "犯罪片",

        "剧情片",

        "战争片",

        "家庭篇",

        "记录片",

        "历史片",

        "动漫片",

        "大陆综艺",

        "港台综艺"

      ]

    },

    {

      "key": "csp_Wwys",

      "name": "《理想🔹秒播》",

      "type": 3,

      "playerType": 2,

      "changeable": 0,

      "api": "csp_Wwys",

      "jar": "./lib/1020.jar",

      "ext": "https://www.wwgz.cn/"

    },

    {

      "key": "csp_MiTuApp",

      "name": "《米兔🔹资源》",

      "type": 3,

      "api": "csp_MiTuApp",

      "jar": "./lib/1020.jar",

      "ext": "ewogICAgICAgICJ1cmwiOiAiaHR0cHM6Ly9reTEwODAudG9wIiwKICAgICAgICAiZGF0YUtleSI6ICJlNTlkNDRiMmVlZjAzYmEyIiwKICAgICAgICAiZGF0YUl2IjogImU1OWQ0NGIyZWVmMDNiYTIiLAogICAgICAgICJkZXZpY2VJZCI6ICIyMzgxM2IxNWJmN2JkMzU5Y2I4ZDMyZjlkMDI4NjI0NGMiCiAgfQ=="

    },

    {

      "key": "厂长资源_js",

      "name": "《工厂🔹资源》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "order_num": 0,

      "ext": "./lib/厂长资源.js"

    },

    {

      "key": "熊猫TV_js",

      "name": "《熊猫🔹秒播》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "order_num": 0,

      "ext": "./lib/熊猫TV.js"

    },

    {

      "key": "影视仓",

      "name": "《七星🔹影仓》",

      "type": 3,

      "api": "csp_AppMr",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "jar": "./lib/0819.jar;md5;380A08E7735A86D85AAA24E9A1C77AF3"

    },

    {

      "key": "✨YY影视✨",

      "name": "《天微🔹秒播》",

      "type": 3,

      "api": "csp_XBPQ",

      "ext": {

        "请求头": "User-Agent$MOBILE_UA",

        "编码": "UTF-8",

        "主页url": "https://uuys.cc",

        "二次截取": "module-page&&<div id=\"page\">",

        "数组": "<a&&</div></div>",

        "图片": "data-original=\"&&\"",

        "标题": "title=\"&&\"",

        "链接": "href=\"&&\"",

        "副标题": "天微专享✨+module-item-note&&</div>",

        "线路数组": "item tab-item&&</div>[排序:海湾资源>非凡播放>无尽资源]",

        "线路标题": "天微✨+<span>&&</span>+【共+<small>&&</small>+集】",

        "播放数组": "module-play-list\"&&</div>",

        "播放标题": "天微✨+>&&</",

        "简介": "【公众号：天微科技】提醒：请勿相信视频里的广告！+<p>&&</p >",

        "搜索url": "https://uuys.cc/vodsearch/{wd}----------{pg}---.html",

        "分类url": "https://uuys.cc/vodshow/{cateId}-{area}-{by}-{class}-{lang}-{letter}---{catePg}---{year}.html",

        "分类": "电影$2#电视剧$1#综艺$4#动漫$3"

      }

    },

    {

      "key": "360zy",

      "name": "《飞龙🔹秒播》",

      "type": 1,

      "api": "https://360zy.com/api.php/provide/vod?",

      "searchable": 1,

      "changeable": 1,

      "categories": [

        "动作片",

        "喜剧片",

        "爱情片",

        "科幻片",

        "恐怖片",

        "剧情片",

        "战争片",

        "古装片",

        "悬疑片",

        "犯罪片",

        "灾难片",

        "国产剧",

        "香港剧",

        "韩国剧",

        "欧美剧",

        "台湾剧",

        "日本剧",

        "海外剧",

        "泰国剧",

        "大陆综艺",

        "港台综艺",

        "日韩综艺",

        "欧美综艺",

        "国产动漫",

        "欧美动漫",

        "日韩动漫",

        "现代都市",

        "脑洞悬疑",

        "年代穿越",

        "古装仙侠",

        "女频恋爱",

        "成长逆袭",

        "反转爽剧"

      ]

    },

    {

      "key": "素白白[优]_js",

      "name": "《素白🔹秒播》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "order_num": 0,

      "ext": "./lib/素白白[优].js"

    },

    {

      "key": "csp_XYQBiu_骚火VIP",

      "name": "《骚火🔹秒播》",

      "type": 3,

      "api": "csp_XBPQ",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "ext": "./lib/shyyVIP.json"

    },

    {

      "key": "茶狐杯",

      "name": "《茶杯🔹狐源》",

      "type": 3,

      "api": "csp_XBPQ",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "ext": "./lib/茶狐杯.json"

    },

    {

      "key": "TVB云播_js",

      "name": "《云播🔹在线》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "order_num": 0,

      "ext": "./lib/TVB云播.js"

    },

    {

      "key": "子子影视",

      "name": "《高速🔹天微》",

      "type": 3,

      "api": "csp_XBPQ",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "ext": "./lib/子子.json"

    },

    {

      "key": "刺猬影视_js",

      "name": "《刺猬🔹秒播》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "order_num": 0,

      "ext": "./lib/刺猬影视.js"

    },

    {

      "key": "csp_xBPQ_奇优",

      "name": "《奇优🔹秒播》",

      "type": 3,

      "api": "csp_XBPQ",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "ext": "./lib/qiyou.json"

    },

    {

      "key": "七新电影网_js",

      "name": "《骑士🔹秒播》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "order_num": 0,

      "ext": "./lib/七新电影网.js"

    },

    {

      "key": "白嫖者联盟_js",

      "name": "《白嫖🔹联盟》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "order_num": 0,

      "ext": "./lib/白嫖者联盟.js"

    },

    {

      "key": "木耳",

      "name": "《木耳🔹采集》",

      "type": 1,

      "api": "https://json02.heimuer.xyz/api.php/provide/vod",

      "searchable": 1,

      "filterable": 1,

      "changeable": 1,

      "timeout": 20,

      "categories": [

        "剧情片",

        "动作片",

        "冒险片",

        "喜剧片",

        "奇幻片",

        "恐怖片",

        "悬疑片",

        "惊悚片",

        "灾难片",

        "爱情片",

        "犯罪片",

        "科幻片",

        "歌舞片",

        "战争片",

        "经典片",

        "动画电影",

        "网络电影",

        "其他片",

        "国产剧",

        "港剧",

        "韩剧",

        "日剧",

        "泰剧",

        "台剧",

        "欧美剧",

        "新马剧",

        "其他剧",

        "国产综艺",

        "港台综艺",

        "韩国综艺",

        "日本综艺",

        "欧美综艺",

        "新马泰综艺",

        "其他综艺",

        "古装短剧",

        "虐恋短剧",

        "逆袭短剧",

        "神豪短剧",

        "重生短剧",

        "复仇短剧",

        "穿越短剧",

        "甜宠短剧",

        "强者短剧",

        "欧美动漫",

        "日本动漫",

        "韩国动漫",

        "国产动漫",

        "港台动漫"

      ],

      "header": {

        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

      }

    },

    {

      "key": "csp_Mp4Mov",

      "name": "《磁力🔹在线》",

      "type": 3,

      "api": "csp_Mp4Mov",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1

    },

    {

      "key": "csp_New6v",

      "name": "《磁力🔹新六》",

      "type": 3,

      "api": "csp_New6v",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "ext": "https://www.xb6v.com"

    },

    {

      "key": "csp_SeedHub",

      "name": "《磁力🔹狐播》",

      "type": 3,

      "api": "csp_SeedHub",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1

    },

    {

      "key": "csp_KubaCL",

      "name": "《磁力🔹酷吧》",

      "type": 3,

      "api": "csp_KubaCL",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1

    },

    {

      "key": "csp_MeijuMi",

      "name": "《磁力🔹美剧》",

      "type": 3,

      "api": "csp_MeijuMi",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1

    },

    {

      "key": "csp_Xunlei8",

      "name": "《磁力🔹迅雷》",

      "type": 3,

      "api": "csp_Xunlei8",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1

    },

    {

      "key": "csp_星辰",

      "name": "《星辰🔹秒播》",

      "type": 3,

      "api": "csp_XBPQ",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "ext": "./lib/xcys.json"

    },

    {

      "key": "4K-AV_js",

      "name": "《爱看🔹4KHD》",

      "type": 3,

      "api": "./lib/drpy2.min.js",

      "searchable": 1,

      "quickSearch": 1,

      "filterable": 1,

      "order_num": 0,

      "ext": "./lib/4K-AV.js"

    },

    {

      "key": "至臻网盘",

      "name": "《至臻💿4KHD》",

      "type": 3,

      "api": "csp_Wobg",

      "searchable": 1,

      "filterable": 1,

      "changeable": 1,

      "ext": {

        "token": "http://127.0.0.1:9978/file/tvbox/tok.txt",

        "cookie": "http://127.0.0.1:9978/file/tvbox/quark.txt",

        "uc_cookie": "http://127.0.0.1:9978/file/tvbox/uc.txt",

        "site": "https://mihdr.top",

        "danmu": true

      },

      "timeout": 25

    },

    {

      "key": "立播网盘",

      "name": "《立播💿网盘》",

      "type": 3,

      "api": "csp_Libvio",

      "searchable": 1,

      "filterable": 1,

      "changeable": 1,

      "ext": {

        "token": "http://127.0.0.1:9978/file/tvbox/tok.txt",

        "cookie": "http://127.0.0.1:9978/file/tvbox/quark.txt",

        "uc_cookie": "http://127.0.0.1:9978/file/tvbox/uc.txt",

        "site": "https://libvio.link",

        "danmu": true

      },

      "timeout": 30

    },

    {

      "key": "土豆网盘",

      "name": "《土豆💿网盘》",

      "type": 3,

      "api": "csp_Wobg",

      "searchable": 1,

      "filterable": 1,

      "changeable": 1,

      "ext": {

        "token": "http://127.0.0.1:9978/file/tvbox/tok.txt",

        "cookie": "http://127.0.0.1:9978/file/tvbox/quark.txt",

        "uc_cookie": "http://127.0.0.1:9978/file/tvbox/uc.txt",

        "site": "https://yunpan.yunpay.cc/",

        "danmu": true

      },

      "timeout": 25

    },

    {

      "key": "纸条",

      "name": "《纸条💿搜索》",

      "type": 3,

      "api": "csp_XiaoZhiTiao",

      "searchable": 1,

      "filterable": 1,

      "changeable": 0,

      "ext": {

        "token": "http://127.0.0.1:9978/file/tvbox/tok.txt",

        "danmu": true

      },

      "timeout": 15

    },

    {

      "key": "js_星芽短剧",

      "name": "《天微🎦短剧》",

   
