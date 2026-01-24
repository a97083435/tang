<?php
/**
 * m3u8/ts 代理（TS 流式转发 + failover + Range 透传 + 兼容 /xxx.ts 绝对路径）
 */

error_reporting(0);
date_default_timezone_set("Asia/Shanghai");

// CORS / OPTIONS
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: X-Requested-With, Content-Type, Range');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

// 参数
$name = $_GET['id'] ?? '';
$ts   = $_GET['ts'] ?? '';

if ($name === '') {
    http_response_code(400);
    echo "Missing id";
    exit;
}

// 简单安全过滤（避免奇怪路径注入）
$name = preg_replace('~[^a-zA-Z0-9_\-]~', '', $name);

// ts 允许 / . _ - 以及 query 常见字符 ? & = %
$ts = $ts ? preg_replace('~[^a-zA-Z0-9_\-\.\/\?\&\=\%]~', '', $ts) : '';

// 多服务器（域名/多域名都可以）
$serverHosts = [
    'smt.goiptv.us.ci',
];

// 选服务器（按频道名 hash，尽量稳定）
function selectServer($servers, $name = '') {
    if (!empty($name)) {
        $index = abs(crc32($name)) % count($servers);
        return $servers[$index];
    }
    return $servers[array_rand($servers)];
}

// 把服务器列表“旋转”一下：从选中的开始依次尝试
function rotatedServers($servers, $first) {
    $idx = array_search($first, $servers, true);
    if ($idx === false) return $servers;
    return array_merge(array_slice($servers, $idx), array_slice($servers, 0, $idx));
}

// ======== CURL：流式转发 TS（不进内存）========
function curl_stream_to_client($url, array $headers, $timeout = 10) {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_HEADER            => false,
        CURLOPT_FOLLOWLOCATION    => true,
        CURLOPT_CONNECTTIMEOUT    => 3,
        CURLOPT_TIMEOUT           => $timeout,
        CURLOPT_SSL_VERIFYPEER    => false,
        CURLOPT_SSL_VERIFYHOST    => false,
        CURLOPT_HTTPHEADER        => $headers,
        CURLOPT_RETURNTRANSFER    => false,  // 关键：不返回字符串
        CURLOPT_BUFFERSIZE        => 262144, // 256KB buffer
        CURLOPT_DNS_CACHE_TIMEOUT => 300,    // DNS 缓存 5 分钟（域名更稳）
        CURLOPT_WRITEFUNCTION     => function($ch, $data) {
            echo $data;
            @ob_flush();
            flush();
            return strlen($data);
        },
    ]);

    $ok = curl_exec($ch);
    $errno = curl_errno($ch);
    $code  = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($ok === false || $errno !== 0) return [false, 0];
    return [$code >= 200 && $code < 300, $code];
}

// ======== CURL：获取文本（m3u8 体积小，允许进内存）========
function curl_get_text($url, array $headers, $timeout = 8) {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_HEADER            => false,
        CURLOPT_FOLLOWLOCATION    => true,
        CURLOPT_CONNECTTIMEOUT    => 3,
        CURLOPT_TIMEOUT           => $timeout,
        CURLOPT_SSL_VERIFYPEER    => false,
        CURLOPT_SSL_VERIFYHOST    => false,
        CURLOPT_HTTPHEADER        => $headers,
        CURLOPT_RETURNTRANSFER    => true,
        CURLOPT_DNS_CACHE_TIMEOUT => 300,
    ]);

    $data  = curl_exec($ch);
    $errno = curl_errno($ch);
    $code  = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($errno !== 0 || $data === false || $code === 404) {
        return [null, $code ?: 0];
    }
    return [$data, $code];
}

// 构建透传请求头（Range 很重要）
$upHeaders = [];
if (!empty($_SERVER['HTTP_RANGE'])) {
    $upHeaders[] = 'Range: ' . $_SERVER['HTTP_RANGE'];
}

$selectedHost = selectServer($serverHosts, $name);
$serversTry   = rotatedServers($serverHosts, $selectedHost);

// 根据 ts 形态拼接上游 URL：
// - 以 "/" 开头：站内绝对路径 -> http://host{$ts}
// - 否则：兼容旧模式 -> http://host/{$name}/{$ts}
function build_ts_url($host, $name, $ts) {
    // 允许 ts 中包含 query（如 xxx.ts?token=...）
    if ($ts !== '' && $ts[0] === '/') {
        return "http://{$host}{$ts}";
    }
    return "http://{$host}/{$name}/{$ts}";
}

// ==============================
// TS 代理（流式）
// ==============================
if ($ts) {
    header('Content-Type: video/mp2t');
    header('Cache-Control: public, max-age=30');
    header('Expires: ' . gmdate('D, d M Y H:i:s', time() + 30) . ' GMT');
    header('Accept-Ranges: bytes');

    foreach ($serversTry as $host) {
        $url = build_ts_url($host, $name, $ts);
        [$ok, $code] = curl_stream_to_client($url, $upHeaders, 10);
        if ($ok) exit;
    }

    http_response_code(404);
    echo "Error: TS not found.";
    exit;
}

// ==============================
// M3U8 代理（文本）
// ==============================
header('Content-Type: application/vnd.apple.mpegurl');
header('Cache-Control: public, max-age=2');
header('Expires: ' . gmdate('D, d M Y H:i:s', time() + 2) . ' GMT');

$seed = "tvata nginx auth module";
$tid  = "mc42afe834703";

$playlistPath = "/{$name}/playlist.m3u8";

// ct/tsum
$t    = (string)intval(time() / 150);
$str  = $seed . $playlistPath . $tid . $t;
$tsum = md5($str);
$link = http_build_query(["ct" => $t, "tsum" => $tsum]);

$self = $_SERVER['PHP_SELF'];

// failover 获取 m3u8
$result = null;
foreach ($serversTry as $host) {
    // 修复：不要再多加一个 "/"
    $url = "http://{$host}{$playlistPath}?tid={$tid}&{$link}";
    [$data, $code] = curl_get_text($url, $upHeaders, 8);

    if (!empty($data) && $code >= 200 && $code < 300 && strpos($data, "EXTM3U") !== false) {
        $result = $data;
        break;
    }
}

if ($result === null) {
    header("Location: http://vjs.zencdn.net/v/oceans.mp4");
    exit;
}

// 重写 ts 行（只改真正的媒体行）
$lines = preg_split("/\r\n|\n|\r/", $result);
$out = [];

foreach ($lines as $line) {
    $line = trim($line);
    if ($line === '') continue;

    if ($line[0] === '#') {
        $out[] = $line;
        continue;
    }

    // 媒体 URL：相对/绝对/站内绝对都兼容
    if (stripos($line, '.ts') !== false) {
        $tsName = $line;

        // 如果上游给的是完整 URL，则取 path + query（保留以 / 开头的站内路径形态）
        if (stripos($tsName, 'http://') === 0 || stripos($tsName, 'https://') === 0) {
            $p = parse_url($tsName);
            $path = $p['path'] ?? '';
            // 保留站内绝对路径：/Thrill/xxx.ts
            $tsName = $path ?: '';
            if (!empty($p['query'])) $tsName .= '?' . $p['query'];
        }

        $out[] = $self . "?id=" . rawurlencode($name) . "&ts=" . rawurlencode($tsName);
    } else {
        $out[] = $line;
    }
}

echo implode("\n", $out) . "\n";
exit;
