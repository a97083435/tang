<?php
/*
 * 功能：
 *   - 访问 http://yourserver/youtube.php?token=xxxx 显示完整 M3U 清单
 *   - 访问 http://yourserver/youtube.php?token=xxxx&id=频道ID，播放指定频道的 M3U8 播放地址
 *   - 支持 ofiii 开头的点播频道，和 TS 切片代理
 */
header('Content-Type: text/plain; charset=utf-8', true, 200);
$SECRET_TOKEN = 'passwd'; // 替换为你的实际token

// 检查token是否有效
if (!isset($_GET['token'])) {
    http_response_code(403);
    echo "❌错误：访问被拒绝";
    exit;
}
if ($_GET['token'] !== $SECRET_TOKEN) {
    http_response_code(403);
    echo "❌错误：密码错误";
    exit;
}

// 频道映射表（完整）
$channels = [
    '4gtv-4gtv009' => ['中天新闻台', 'https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/CTI2.png', '新闻财经'],
    '4gtv-4gtv040' => ['中视', 'https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/CTV.png', '综合其他'],
    '4gtv-4gtv041' => ['华视', 'https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/CTS.png', '综合其他'],
    '4gtv-4gtv051' => ['台视新闻','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/TTV2.png','新闻财经'],
    '4gtv-4gtv052' => ['华视新闻','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/CTS1.png','新闻财经'],
    '4gtv-4gtv074' => ['中视新闻','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/CTV1.png','新闻财经'],
    '4gtv-4gtv076' => [ '亚洲旅游台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/Asiatravel.png','生活旅游'],
    '4gtv-4gtv084' => ['国会频道1台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/guohui1.png','综合其他'],
    '4gtv-4gtv085' => ['国会频道2台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/guohui2.png','综合其他'],
    '4gtv-4gtv102' =>  ['东森购物1台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/EBC11.png','综合其他'],
    '4gtv-4gtv103' =>  ['东森购物2台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/EBC11.png','综合其他'],
    '4gtv-4gtv104' => ['第1商业台','https://p-cdnstatic.svc.litv.tv/pics/logo_litv_4gtv-4gtv104_tv.png','新闻财经'],
    '4gtv-4gtv156' => ['寰宇新闻台湾台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/Global3.png', '新闻财经'],
    '4gtv-4gtv158' => ['寰宇财经台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/Global4.png','新闻财经'],
    'litv-xinchuang01' => ['龙华卡通台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/LTV9.png','儿童卡通'],
    'litv-xinchuang02' => ['龙华洋片台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/LTV2.png','电影戏剧'],
    'litv-xinchuang03' => ['龙华电影台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/LTV1.png','电影戏剧'],
    'litv-xinchuang11' => ['龙华日韩台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/LTV5.png','电影戏剧'],
    'litv-longturn14' => ['寰宇新闻台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/Global2.png','新闻财经'],
    'litv-xinchuang12' => ['龙华偶像台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/LTV6.png','电影戏剧'],
    'litv-xinchuang18' => ['龙华戏剧台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/LTV4.png','电影戏剧'],
    'litv-xinchuang19' => ['Smart知识台', 'https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/smarttv.png','生活旅游'],
    'litv-xinchuang20' => ['ELTV生活英语台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/ELTA7.png','儿童卡通'],
    'litv-xinchuang21' => ['龙华经典台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/LTV7.png','电影戏剧'],
    'litv-xinchuang18' => ['台湾戏剧台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/Taiwanxiju.png','电影戏剧'],
    'litv-ftv16' => ['好消息','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/GoodTV1.png','综合其他'],
    'litv-ftv17' => ['好消息2台','https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/GoodTV2.png','综合其他'],
    'iNEWS' => ['三立新闻iNEWS', 'https://cdn.jsdelivr.net/gh/wanglindl/TVlogo@main/img/SET3.png','新闻财经'],
    'nnews-zh' => ['倪珍播新闻', 'https://p-cdnstatic.svc.litv.tv/pics/logo_litv_nnews_tv.png','新闻财经'],
    'daystar' => ['DayStar','https://p-cdnstatic.svc.litv.tv/pics/Daystar_128x72.png','综合其他'],
];

$id = isset($_GET['id']) ? $_GET['id'] : null;

// 动态获取基础 URL
$protocol = "https";
$host = $_SERVER['HTTP_HOST'];
$base_url = "$protocol://$host";

// 完整 M3U 清单
if (!$id && !isset($_GET['ts_proxy'])) {
    header('Content-Type: text/plain; charset=utf-8');
    echo "#EXTM3U x-tvg-url=\"https://raw.githubusercontent.com/myhomebox/EPG/refs/heads/main/output/ofiii.xml\"\n";
    foreach ($channels as $key => $value) {
        $group = $value[2] ?? 'ofiii';
        echo '#EXTINF:-1 tvg-id="' . $value[0] . '" tvg-name="' . $value[0] . '" tvg-logo="' . $value[1] . '" group-title="' . $group . '",' . $value[0] . "\n";
        echo "$base_url/youtube.php?token=" . urlencode($SECRET_TOKEN) . "&id=" . urlencode($key) . "\n";
    }
    exit;
}

// TS代理处理
if (isset($_GET['ts_proxy'])) {
    $ts_url = urldecode($_GET['ts_proxy']);
    $headers = [
        'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Referer: https://www.ofiii.com/',
        'Origin: https://www.ofiii.com',
        'Accept: video/mp2t, */*',
        'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8',
        'Connection: keep-alive',
        'Sec-Fetch-Dest: video',
        'Sec-Fetch-Mode: no-cors',
        'Sec-Fetch-Site: cross-site',
    ];
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $ts_url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_HEADER, false);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_BINARYTRANSFER, true);
    curl_setopt($ch, CURLOPT_BUFFERSIZE, 128000);
    $ts_content = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $contentType = curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
    curl_close($ch);
    if ($httpCode === 200 && !empty($ts_content)) {
        header('Content-Type: video/mp2t');
        header('Content-Length: ' . strlen($ts_content));
        header('Cache-Control: max-age=3600');
        echo $ts_content;
    } else {
        http_response_code(500);
        error_log("TS代理错误: HTTP $httpCode, Content-Type: $contentType, URL: $ts_url");
        echo "❌错误：无法获取TS片段 (HTTP $httpCode)";
    }
    exit;
}

// 检查频道 ID 是否有效
if (!isset($channels[$id])) {
    http_response_code(404);
    echo "❌错误：未找到频道。";
    exit;
}

function generateRandomDeviceId() {
    return sprintf('%04x%04x-%04x-%04x-%04x-%04x%04x%04x',
        mt_rand(0, 0xffff), mt_rand(0, 0xffff),
        mt_rand(0, 0xffff),
        mt_rand(0, 0x0fff) | 0x4000,
        mt_rand(0, 0x3fff) | 0x8000,
        mt_rand(0, 0xffff), mt_rand(0, 0xffff), mt_rand(0, 0xffff)
    );
}

// 处理 ofiii 点播频道
if (strpos($id, 'ofiii') === 0) {
    // 请求头
    $headers = [
        'accept: application/json, text/plain, */*',
        'accept-language: zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'cache-control: no-cache',
        'content-type: text/plain',
        'origin: https://www.ofiii.com',
        'pragma: no-cache',
        'priority: u=1, i',
        'referer: https://www.ofiii.com/',
        'sec-ch-ua: "Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile: ?0',
        'sec-ch-ua-platform: "macOS"',
        'sec-fetch-dest: empty',
        'sec-fetch-mode: cors',
        'sec-fetch-site: same-site',
        'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
    ];
    $build_id = getBuildId();
    $json_url = "https://www.ofiii.com/_next/data/{$build_id}/channel/watch/{$id}.json";
    $json_data = fetchUrl($json_url, $headers);
    if (!$json_data) {
        http_response_code(500);
        echo "❌错误：无法获取节目数据";
        exit;
    }
    $data = json_decode($json_data, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        http_response_code(500);
        echo "❌错误：解析节目数据失败";
        exit;
    }
    $programs = $data['pageProps']['channel']['vod_channel_schedule']['programs'] ?? [];
    if (empty($programs)) {
        http_response_code(404);
        echo "❌错误：目前无节目安排";
        exit;
    }
    $page_url = "https://www.ofiii.com/channel/watch/{$id}";
    $page_content = fetchUrl($page_url, $headers);
    if (!$page_content) {
        http_response_code(500);
        echo "❌错误：无法获取页面内容";
        exit;
    }
    preg_match('/<h2[^>]*subtitle_section[^>]*>(.*?)<\/h2>/i', $page_content, $matches);
    $current_program = $matches[1] ?? '';
    if (empty($current_program)) {
        http_response_code(404);
        echo "❌错误：无法定位节目信息";
        exit;
    }
    $ch_asset_id = matchProgram($current_program, $programs);
    $composite_id = $id . '%23' . $ch_asset_id;
    $device_id = generateRandomDeviceId();
    $vod_url = "https://cdi.ofiii.com/ofiii_cdi/video/urls?device_type=pc&device_id={$device_id}&media_type=vod-channel&asset_id={$composite_id}";
    $vod_data = fetchUrl($vod_url, $headers);
    if (!$vod_data) {
        http_response_code(500);
        echo "❌错误：无法获取播放地址";
        exit;
    }
    $vod_json = json_decode($vod_data, true);
    if (json_last_error() !== JSON_ERROR_NONE || !isset($vod_json['asset_urls'][0])) {
        http_response_code(500);
        echo "❌错误：解析播放地址失败";
        exit;
    }
    // 处理M3U8内容（已启用 TS 代理）
    $m3u8_content = processM3u8($vod_json['asset_urls'][0], $headers, true);
    if (!$m3u8_content) {
        http_response_code(500);
        echo "❌错误：处理M3U8内容失败";
        exit;
    }
    header('Content-Type: application/vnd.apple.mpegurl');
    echo $m3u8_content;
    exit;
}

// 直播频道处理
$baseUrl = 'https://cdi.ofiii.com/ofiii_cdi/video/urls';
$deviceId = generateRandomDeviceId();
$assetId = $id;
$timestamp = time();
$url = "$baseUrl?device_type=pc&device_id=$deviceId&media_type=channel&asset_id=$assetId&_t=$timestamp";
$headers = [
    'accept: application/json, text/plain, */*',
    'accept-language: zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'cache-control: no-cache',
    'content-type: text/plain',
    'origin: https://www.ofiii.com',
    'pragma: no-cache',
    'priority: u=1, i',
    'referer: https://www.ofiii.com/',
    'sec-ch-ua: "Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile: ?0',
    'sec-ch-ua-platform: "macOS"',
    'sec-fetch-dest: empty',
    'sec-fetch-mode: cors',
    'sec-fetch-site: same-site',
    'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
];
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_TIMEOUT, 5);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
$response = curl_exec($ch);
if (curl_errno($ch)) {
    http_response_code(500);
    echo "❌错误：获取频道信息失败 - " . curl_error($ch);
    curl_close($ch);
    exit;
}
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);
if ($httpCode !== 200) {
    http_response_code(502);
    echo "❌错误：上游服务异常 (HTTP $httpCode)";
    exit;
}
$data = json_decode($response, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    http_response_code(500);
    echo "❌错误：解析JSON响应失败";
    exit;
}
if (isset($data['asset_urls'][0]) && filter_var($data['asset_urls'][0], FILTER_VALIDATE_URL)) {
    // 直播的m3u8也做TS代理
    $m3u8_content = processM3u8($data['asset_urls'][0], $headers, false);
    if ($m3u8_content) {
        header('Content-Type: application/vnd.apple.mpegurl');
        echo $m3u8_content;
    } else {
        // fallback 直接跳转
        header('Location: ' . $data['asset_urls'][0]);
    }
    exit;
} else {
    http_response_code(503);
    echo "❌错误：无法获取有效的播放地址";
}

// ==== Helper Functions ====

function getBuildId() {
    $url = "https://www.ofiii.com/channel";
    $headers = [
        'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Referer: https://www.ofiii.com/',
        'Origin: https://www.ofiii.com'
    ];
    $content = fetchUrl($url, $headers);
    if (!$content) {
        return "VzNm04JKMTEeBeutVsAR4"; // 默认备用值
    }
    preg_match('/_next\/static\/([^\/]+)\/_buildManifest\.js/', $content, $matches);
    if (isset($matches[1])) {
        return $matches[1];
    }
    preg_match('/"buildId":"([^"]+)"/', $content, $matches);
    if (isset($matches[1])) {
        return $matches[1];
    }
    return "VzNm04JKMTEeBeutVsAR4"; // 默认备用值
}

function matchProgram($search_title, $programs) {
    $search_title = trim(strtolower($search_title));
    foreach ($programs as $program) {
        $combined = trim(strtolower($program['title'] . ' ' . ($program['subtitle'] ?? '')));
        if ($search_title === $combined) {
            return $program['asset_id'];
        }
    }
    foreach ($programs as $program) {
        $combined = trim(strtolower($program['title'] . ' ' . ($program['subtitle'] ?? '')));
        similar_text($search_title, $combined, $percent);
        if ($percent >= 85) {
            return $program['asset_id'];
        }
    }
    return $programs[0]['asset_id'];
}

function fetchUrl($url, $headers = []) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    return ($httpCode === 200) ? $response : false;
}

function processM3u8($m3u8_url, $headers, $is_vod = false) {
    $master_content = fetchUrl($m3u8_url, $headers);
    if (!$master_content) {
        return false;
    }
    preg_match_all('/#EXT-X-STREAM-INF:.*?BANDWIDTH=(\d+).*?\n(.+?\.m3u8)/s', $master_content, $matches, PREG_SET_ORDER);
    if (empty($matches)) {
        return false;
    }
    $selected = $matches[0];
    foreach ($matches as $match) {
        if (intval($match[1]) > intval($selected[1])) {
            $selected = $match;
        }
    }
    $playlist_url = $selected[2];
    if (strpos($playlist_url, 'http') !== 0) {
        $base = substr($m3u8_url, 0, strrpos($m3u8_url, '/') + 1);
        $playlist_url = $base . $playlist_url;
    }
    $playlist_content = fetchUrl($playlist_url, $headers);
    if (!$playlist_content) {
        return false;
    }
    // ---------这里已启用TS代理----------
    $protocol = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? "https" : "http";
    $host = $_SERVER['HTTP_HOST'];
    $base_url = "$protocol://$host";
    $modified_content = preg_replace_callback(
        '/([^\s]+\.ts[^\s]*)/',
        function($matches) use ($base_url) {
            $ts_url = $matches[1];
            return $base_url . '/youtube.php?token=' . urlencode($GLOBALS['SECRET_TOKEN']) . '&ts_proxy=' . urlencode($ts_url);
        },
        $playlist_content
    );
    return $modified_content;
}
?>