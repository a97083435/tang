export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // CORS / OPTIONS
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }
    if (request.method !== "GET") {
      return new Response("Method Not Allowed", { status: 405, headers: corsHeaders() });
    }

    // ====== 你的源站域名 ======
    const ORIGIN = "https://smt.tzh911.de5.net";

    // Params
    let id = url.searchParams.get("id") || "";
    let ts = url.searchParams.get("ts") || "";

    if (!id) return new Response("Missing id", { status: 400, headers: corsHeaders() });

    // sanitize
    id = id.replace(/[^a-zA-Z0-9_-]/g, "");
    if (ts) ts = ts.replace(/[^a-zA-Z0-9_\-./?&=%]/g, "");

    // Upstream headers (Range passthrough)
    const upstreamHeaders = new Headers();
    const range = request.headers.get("Range");
    if (range) upstreamHeaders.set("Range", range);

    // -------- TS proxy (streaming) --------
    if (ts) {
      const upstreamUrl = `${ORIGIN}/${encodeURIComponent(id)}/${ts}`;
      const resp = await safeFetch(upstreamUrl, { method: "GET", headers: upstreamHeaders }, 15000);

      if (!resp) {
        return new Response(`Upstream fetch failed (ts). url=${upstreamUrl}`, {
          status: 502,
          headers: corsHeaders(),
        });
      }

      if (!resp.ok) {
        return new Response(`Upstream error (ts): ${resp.status}`, {
          status: resp.status,
          headers: corsHeaders(),
        });
      }

      const headers = new Headers(corsHeaders());
      headers.set("Content-Type", resp.headers.get("Content-Type") || "video/mp2t");
      headers.set("Cache-Control", "public, max-age=30");
      headers.set("Accept-Ranges", "bytes");

      // propagate range response headers if present
      const cr = resp.headers.get("Content-Range");
      if (cr) headers.set("Content-Range", cr);
      const cl = resp.headers.get("Content-Length");
      if (cl) headers.set("Content-Length", cl);

      return new Response(resp.body, { status: resp.status, headers });
    }

    // -------- M3U8 proxy --------
    const seed = "tvata nginx auth module";
    const tid = "mc42afe834703";
    const playlistPath = `/${id}/playlist.m3u8`;

    const ct = String(Math.floor(Date.now() / 1000 / 150));
    const tsum = md5(seed + playlistPath + tid + ct);

    // 保持 query 顺序不敏感，一样即可
    const upstreamUrl = `${ORIGIN}${playlistPath}?ct=${encodeURIComponent(ct)}&tsum=${encodeURIComponent(tsum)}&tid=${encodeURIComponent(tid)}`;

    const resp = await safeFetch(upstreamUrl, { method: "GET", headers: upstreamHeaders }, 12000);

    if (!resp) {
      return new Response(`Upstream fetch failed (m3u8). url=${upstreamUrl}`, {
        status: 502,
        headers: corsHeaders(),
      });
    }

    if (!resp.ok) {
      return new Response(`Upstream error (m3u8): ${resp.status}`, {
        status: resp.status,
        headers: corsHeaders(),
      });
    }

    const text = await resp.text();
    if (!text || !text.includes("EXTM3U")) {
      return Response.redirect("http://vjs.zencdn.net/v/oceans.mp4", 302);
    }

    // rewrite ts lines -> worker url
    const selfBase = `${url.origin}${url.pathname}`;
    const lines = text.split(/\r\n|\n|\r/);
    const out = [];

    for (let line of lines) {
      line = line.trim();
      if (!line) continue;

      if (line.startsWith("#")) {
        out.push(line);
        continue;
      }

      // ts 行重写
      if (line.toLowerCase().includes(".ts")) {
        let tsName = line;

        // 若是绝对 URL，取 pathname + search
        if (/^https?:\/\//i.test(tsName)) {
          try {
            const u = new URL(tsName);
            tsName = u.pathname.replace(/^\/+/, "");
            if (u.search && u.search.length > 1) tsName += u.search;
          } catch {}
        }

        out.push(`${selfBase}?id=${encodeURIComponent(id)}&ts=${encodeURIComponent(tsName)}`);
      } else {
        out.push(line);
      }
    }

    const headers = new Headers(corsHeaders());
    headers.set("Content-Type", "application/vnd.apple.mpegurl");
    headers.set("Cache-Control", "public, max-age=2");

    return new Response(out.join("\n") + "\n", { status: 200, headers });
  },
};

// ---------------- helpers ----------------
function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "X-Requested-With, Content-Type, Range",
  };
}

async function safeFetch(url, init, timeoutMs) {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort("timeout"), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal, redirect: "follow" });
  } catch (e) {
    // 关键：吞掉异常，避免 1101
    return null;
  } finally {
    clearTimeout(t);
  }
}

// ---- MD5 (pure JS, Worker compatible) ----
function md5(input) {
  const x = toWordArray(new TextEncoder().encode(input));
  let A = 0x67452301, B = 0xefcdab89, C = 0x98badcfe, D = 0x10325476;

  for (let i = 0; i < x.length; i += 16) {
    const AA = A, BB = B, CC = C, DD = D;

    A = ff(A, B, C, D, x[i+0], 7, 0xd76aa478);
    D = ff(D, A, B, C, x[i+1], 12, 0xe8c7b756);
    C = ff(C, D, A, B, x[i+2], 17, 0x242070db);
    B = ff(B, C, D, A, x[i+3], 22, 0xc1bdceee);
    A = ff(A, B, C, D, x[i+4], 7, 0xf57c0faf);
    D = ff(D, A, B, C, x[i+5], 12, 0x4787c62a);
    C = ff(C, D, A, B, x[i+6], 17, 0xa8304613);
    B = ff(B, C, D, A, x[i+7], 22, 0xfd469501);
    A = ff(A, B, C, D, x[i+8], 7, 0x698098d8);
    D = ff(D, A, B, C, x[i+9], 12, 0x8b44f7af);
    C = ff(C, D, A, B, x[i+10], 17, 0xffff5bb1);
    B = ff(B, C, D, A, x[i+11], 22, 0x895cd7be);
    A = ff(A, B, C, D, x[i+12], 7, 0x6b901122);
    D = ff(D, A, B, C, x[i+13], 12, 0xfd987193);
    C = ff(C, D, A, B, x[i+14], 17, 0xa679438e);
    B = ff(B, C, D, A, x[i+15], 22, 0x49b40821);

    A = gg(A, B, C, D, x[i+1], 5, 0xf61e2562);
    D = gg(D, A, B, C, x[i+6], 9, 0xc040b340);
    C = gg(C, D, A, B, x[i+11], 14, 0x265e5a51);
    B = gg(B, C, D, A, x[i+0], 20, 0xe9b6c7aa);
    A = gg(A, B, C, D, x[i+5], 5, 0xd62f105d);
    D = gg(D, A, B, C, x[i+10], 9, 0x02441453);
    C = gg(C, D, A, B, x[i+15], 14, 0xd8a1e681);
    B = gg(B, C, D, A, x[i+4], 20, 0xe7d3fbc8);
    A = gg(A, B, C, D, x[i+9], 5, 0x21e1cde6);
    D = gg(D, A, B, C, x[i+14], 9, 0xc33707d6);
    C = gg(C, D, A, B, x[i+3], 14, 0xf4d50d87);
    B = gg(B, C, D, A, x[i+8], 20, 0x455a14ed);
    A = gg(A, B, C, D, x[i+13], 5, 0xa9e3e905);
    D = gg(D, A, B, C, x[i+2], 9, 0xfcefa3f8);
    C = gg(C, D, A, B, x[i+7], 14, 0x676f02d9);
    B = gg(B, C, D, A, x[i+12], 20, 0x8d2a4c8a);

    A = hh(A, B, C, D, x[i+5], 4, 0xfffa3942);
    D = hh(D, A, B, C, x[i+8], 11, 0x8771f681);
    C = hh(C, D, A, B, x[i+11], 16, 0x6d9d6122);
    B = hh(B, C, D, A, x[i+14], 23, 0xfde5380c);
    A = hh(A, B, C, D, x[i+1], 4, 0xa4beea44);
    D = hh(D, A, B, C, x[i+4], 11, 0x4bdecfa9);
    C = hh(C, D, A, B, x[i+7], 16, 0xf6bb4b60);
    B = hh(B, C, D, A, x[i+10], 23, 0xbebfbc70);
    A = hh(A, B, C, D, x[i+13], 4, 0x289b7ec6);
    D = hh(D, A, B, C, x[i+0], 11, 0xeaa127fa);
    C = hh(C, D, A, B, x[i+3], 16, 0xd4ef3085);
    B = hh(B, C, D, A, x[i+6], 23, 0x04881d05);
    A = hh(A, B, C, D, x[i+9], 4, 0xd9d4d039);
    D = hh(D, A, B, C, x[i+12], 11, 0xe6db99e5);
    C = hh(C, D, A, B, x[i+15], 16, 0x1fa27cf8);
    B = hh(B, C, D, A, x[i+2], 23, 0xc4ac5665);

    A = ii(A, B, C, D, x[i+0], 6, 0xf4292244);
    D = ii(D, A, B, C, x[i+7], 10, 0x432aff97);
    C = ii(C, D, A, B, x[i+14], 15, 0xab9423a7);
    B = ii(B, C, D, A, x[i+5], 21, 0xfc93a039);
    A = ii(A, B, C, D, x[i+12], 6, 0x655b59c3);
    D = ii(D, A, B, C, x[i+3], 10, 0x8f0ccc92);
    C = ii(C, D, A, B, x[i+10], 15, 0xffeff47d);
    B = ii(B, C, D, A, x[i+1], 21, 0x85845dd1);
    A = ii(A, B, C, D, x[i+8], 6, 0x6fa87e4f);
    D = ii(D, A, B, C, x[i+15], 10, 0xfe2ce6e0);
    C = ii(C, D, A, B, x[i+6], 15, 0xa3014314);
    B = ii(B, C, D, A, x[i+13], 21, 0x4e0811a1);
    A = ii(A, B, C, D, x[i+4], 6, 0xf7537e82);
    D = ii(D, A, B, C, x[i+11], 10, 0xbd3af235);
    C = ii(C, D, A, B, x[i+2], 15, 0x2ad7d2bb);
    B = ii(B, C, D, A, x[i+9], 21, 0xeb86d391);

    A = (A + AA) >>> 0;
    B = (B + BB) >>> 0;
    C = (C + CC) >>> 0;
    D = (D + DD) >>> 0;
  }

  return toHex(A) + toHex(B) + toHex(C) + toHex(D);
}

function toWordArray(bytes) {
  const len = bytes.length;
  const n = (((len + 8) >>> 6) + 1) * 16;
  const words = new Uint32Array(n);

  let i = 0;
  for (; i < len; i++) words[i >> 2] |= bytes[i] << ((i % 4) * 8);
  words[i >> 2] |= 0x80 << ((i % 4) * 8);

  const bitLen = len * 8;
  words[n - 2] = bitLen >>> 0;
  words[n - 1] = (bitLen / 0x100000000) >>> 0;
  return words;
}

function rotl(x, c) { return (x << c) | (x >>> (32 - c)); }
function add(x, y) { return (x + y) >>> 0; }
function cmn(q, a, b, x, s, t) { return add(rotl(add(add(a, q), add(x, t)), s), b); }
function ff(a, b, c, d, x, s, t) { return cmn((b & c) | (~b & d), a, b, x, s, t); }
function gg(a, b, c, d, x, s, t) { return cmn((b & d) | (c & ~d), a, b, x, s, t); }
function hh(a, b, c, d, x, s, t) { return cmn(b ^ c ^ d, a, b, x, s, t); }
function ii(a, b, c, d, x, s, t) { return cmn(c ^ (b | ~d), a, b, x, s, t); }

function toHex(x) {
  let s = "";
  for (let i = 0; i < 4; i++) s += ((x >>> (i * 8)) & 0xff).toString(16).padStart(2, "0");
  return s;
}