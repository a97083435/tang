/**
 * @name Appx64 Clear Music
 * @description ID-based requests, verified audio
 * @version 2026.11.10
 * @author Local
 */

'use strict';

const CONFIG = {
  timeoutMs: 6500,
  totalTimeoutMs: 30000,
  cacheTtlMs: 180000,
  cacheMaxSize: 150,
  allowDowngrade: false,
  verifyAudio: true,
  debug: false,
  qqCookie: '',
  license: '',
  backends: { gd: true, xinghai: true, kuwoOfficial: true, wwwweb: true, tang: true, qqOfficial: true, vkeys: true },
};

const { EVENT_NAMES, request, on, send, env } = globalThis.lx;
const QUALITIES = {
  wy: ['128k', '320k', 'flac', 'flac24bit'],
  tx: ['128k', '320k', 'flac'],
  kw: ['128k', '320k', 'flac'],
  kg: ['128k', '320k', 'flac'],
  mg: ['128k', '320k', 'flac'],
};
const NAMES = { wy: 'Netease', tx: 'QQ Music', kw: 'Kuwo', kg: 'Kugou', mg: 'Migu' };
const cache = new Map();
const inflight = new Map();
const health = new Map();
const deviceId = 'lx-online-' + Math.random().toString(36).slice(2, 8) + Date.now().toString(36).slice(-4);
const TOKEN_TTL = 4 * 60 * 1000;
let serverToken = '';
let tokenAt = 0;
let tokenPromise = null;

function log(message) {
  if (CONFIG.debug) console.log('[Clear Music] ' + message);
}

function pick(info, fields, accept = () => true) {
  for (const field of fields) {
    for (const obj of [info, info.meta]) {
      const value = obj && obj[field];
      if ((typeof value === 'string' || typeof value === 'number') && String(value).trim() && accept(String(value).trim())) return String(value).trim();
    }
  }
  return '';
}

function songId(source, info) {
  if (source === 'tx') return pick(info, ['songmid', 'mid'], id => /^[A-Za-z0-9]{14}$/.test(id)) || pick(info, ['id', 'songId', 'songmid']);
  if (source === 'kw') return pick(info, ['rid', 'musicrid', 'songmid', 'id', 'songId']).replace(/^MUSIC_/i, '');
  if (source === 'kg') return pick(info, ['hash', 'FileHash', 'fileHash', 'songmid', 'id']);
  if (source === 'mg') {
    const id = pick(info, ['songmid', 'id', 'songId', 'musicId'], value => /^\d+$/.test(value));
    if (id) return id;
    throw new Error('Migu needs a numeric song id; copyrightId is a different identifier');
  }
  return pick(info, ['id', 'songId', 'songmid']);
}

function durationSeconds(info) {
  const interval = pick(info, ['interval']);
  if (/^\d+(?::\d{1,2}){1,2}$/.test(interval)) return interval.split(':').reduce((sum, part) => sum * 60 + Number(part), 0);
  const value = interval || pick(info, ['dt', 'duration']);
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? (interval ? number : number / 1000) : null;
}

function urlValue(value) {
  if (typeof value !== 'string') throw new Error('No playback URL');
  const url = value.trim().replace(/^\/\//, 'https://');
  const match = /^https?:\/\/([^/?#]+)(?:[/?#]|$)/i.exec(url);
  if (!match || /[\s\x00-\x1f]/.test(url) || /@/.test(match[1])) throw new Error('Invalid playback URL');
  const host = match[1].replace(/:\d+$/, '').toLowerCase();
  if (/^(localhost|127\.|10\.|192\.168\.|169\.254\.|0\.|172\.(1[6-9]|2\d|3[01])\.|\[)/.test(host) || /\.local$/.test(host)) throw new Error('Local playback address rejected');
  return url;
}

function query(params) {
  return Object.keys(params).filter(key => params[key] !== '' && params[key] != null)
    .map(key => encodeURIComponent(key) + '=' + encodeURIComponent(String(params[key]))).join('&');
}

function bytesOf(response) {
  let value = response.raw != null ? response.raw : response.body;
  if (value && value.type === 'Buffer' && Array.isArray(value.data)) value = value.data;
  if (Array.isArray(value)) return new Uint8Array(value);
  if (typeof ArrayBuffer !== 'undefined' && ArrayBuffer.isView(value)) return new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
  if (typeof ArrayBuffer !== 'undefined' && value instanceof ArrayBuffer) return new Uint8Array(value);
  throw new Error('Host did not provide binary data; use a current LX version');
}

function textAt(bytes, offset, length) {
  return Array.from(bytes.subarray(offset, offset + length), byte => String.fromCharCode(byte)).join('');
}

function numberAt(bytes, offset, length) {
  let value = 0;
  for (let i = offset; i < offset + length; i++) value = value * 256 + bytes[i];
  return value;
}

function inspectFlac(bytes, media, base, start = 0, frameOnly = false) {
  let position = start;
  if (!frameOnly) {
    while (true) {
      if (position + 4 > bytes.length) return { skip: base + position, flacInfo: media, flacFrame: false };
      const last = (bytes[position] & 128) !== 0;
      const length = numberAt(bytes, position + 1, 3);
      position += length + 4;
      if (position + (last ? 16 : 4) > bytes.length) return { skip: base + position, flacInfo: media, flacFrame: last };
      if (last) break;
    }
  }
  const frame = bytes.subarray(position);
  if (frame.length < 16 || frame[0] !== 255 || (frame[1] & 254) !== 248 || (frame[3] & 1) || (frame[3] >> 4) > 10) throw new Error('FLAC audio frame missing');
  const block = frame[2] >> 4;
  const rate = frame[2] & 15;
  const depth = frame[3] >> 1 & 7;
  if (!block || rate === 15 || depth === 3 || depth === 7) throw new Error('Invalid FLAC frame header');
  let count = 1;
  if (frame[4] & 128) {
    count = 0;
    for (let mask = 128; frame[4] & mask; mask >>= 1) count++;
    if (count < 2 || count > 7) throw new Error('Invalid FLAC frame number');
    for (let i = 1; i < count; i++) if ((frame[4 + i] & 192) !== 128) throw new Error('Invalid FLAC frame number');
  }
  const end = 4 + count + (block === 6 ? 1 : block === 7 ? 2 : 0) + (rate === 12 ? 1 : rate === 13 || rate === 14 ? 2 : 0);
  let crc = 0;
  for (let i = 0; i < end; i++) {
    crc ^= frame[i];
    for (let bit = 0; bit < 8; bit++) crc = (crc & 128 ? (crc << 1) ^ 7 : crc << 1) & 255;
  }
  if (crc !== frame[end]) throw new Error('Invalid FLAC frame checksum');
  return media;
}

function inspectAudio(bytes) {
  if (textAt(bytes, 0, 4) === 'fLaC' && bytes.length >= 42 && (bytes[4] & 127) === 0 && numberAt(bytes, 5, 3) === 34) {
    const sampleRate = bytes[18] * 4096 + bytes[19] * 16 + (bytes[20] >> 4);
    const channels = ((bytes[20] >> 1) & 7) + 1;
    const bitDepth = ((bytes[20] & 1) << 4 | bytes[21] >> 4) + 1;
    const samples = (bytes[21] & 15) * 4294967296 + numberAt(bytes, 22, 4);
    if (sampleRate < 8000 || sampleRate > 768000 || bitDepth < 8 || bitDepth > 32) throw new Error('Invalid FLAC metadata');
    if (!samples) throw new Error('FLAC duration is unavailable');
    return inspectFlac(bytes, { format: 'flac', bitDepth, sampleRate, channels, duration: samples / sampleRate }, 0, 4);
  }
  let offset = 0;
  if (textAt(bytes, 0, 3) === 'ID3' && bytes.length >= 10) {
    offset = 10 + (bytes[6] & 127) * 2097152 + (bytes[7] & 127) * 16384 + (bytes[8] & 127) * 128 + (bytes[9] & 127);
    if (bytes[3] === 4 && (bytes[5] & 16)) offset += 10;
    if (offset + 4096 > bytes.length) return { skip: offset };
  }
  for (let i = offset; i + 4 < bytes.length; i++) {
    if (bytes[i] !== 255 || (bytes[i + 1] & 224) !== 224) continue;
    const version = bytes[i + 1] >> 3 & 3;
    const layer = bytes[i + 1] >> 1 & 3;
    const index = bytes[i + 2] >> 4;
    const rate = bytes[i + 2] >> 2 & 3;
    if (version === 1 || layer !== 1 || index === 0 || index === 15 || rate === 3) continue;
    const bitrate = (version === 3 ? [0,32,40,48,56,64,80,96,112,128,160,192,224,256,320] : [0,8,16,24,32,40,48,56,64,80,96,112,128,144,160])[index];
    const sampleRate = [44100,48000,32000][rate] / (version === 3 ? 1 : version === 2 ? 2 : 4);
    const frameSize = Math.floor((version === 3 ? 144000 : 72000) * bitrate / sampleRate) + (bytes[i + 2] >> 1 & 1);
    if (i + frameSize + 4 > bytes.length || bytes[i + frameSize] !== 255 || (bytes[i + frameSize + 1] & 224) !== 224) continue;
    const channels = bytes[i + 3] >> 6 === 3 ? 1 : 2;
    const sideInfo = version === 3 ? (channels === 1 ? 17 : 32) : (channels === 1 ? 9 : 17);
    const xing = i + 4 + ((bytes[i + 1] & 1) ? 0 : 2) + sideInfo;
    let duration = null;
    let averageBitrate = bitrate;
    let cbr = true;
    let sampledFrames = 0;
    let cursor = i;
    while (cursor + 4 <= bytes.length) {
      if (bytes[cursor] !== 255 || (bytes[cursor + 1] & 224) !== 224 || (bytes[cursor + 1] >> 3 & 3) !== version || (bytes[cursor + 1] >> 1 & 3) !== layer || (bytes[cursor + 2] >> 2 & 3) !== rate) break;
      const nextIndex = bytes[cursor + 2] >> 4;
      const nextBitrate = (version === 3 ? [0,32,40,48,56,64,80,96,112,128,160,192,224,256,320] : [0,8,16,24,32,40,48,56,64,80,96,112,128,144,160])[nextIndex];
      if (!nextBitrate) break;
      const size = Math.floor((version === 3 ? 144000 : 72000) * nextBitrate / sampleRate) + (bytes[cursor + 2] >> 1 & 1);
      if (cursor + size > bytes.length) break;
      if (nextBitrate !== bitrate) cbr = false;
      sampledFrames++;
      cursor += size;
    }
    if (xing + 12 <= bytes.length && ['Xing', 'Info'].includes(textAt(bytes, xing, 4))) {
      const flags = numberAt(bytes, xing + 4, 4);
      if (flags & 1) {
        duration = numberAt(bytes, xing + 8, 4) * (version === 3 ? 1152 : 576) / sampleRate;
        if ((flags & 2) && xing + 16 <= bytes.length && duration) averageBitrate = numberAt(bytes, xing + 12, 4) * 8 / duration / 1000;
      }
    }
    const vbri = i + 36;
    if (!duration && vbri + 18 <= bytes.length && textAt(bytes, vbri, 4) === 'VBRI') {
      duration = numberAt(bytes, vbri + 14, 4) * (version === 3 ? 1152 : 576) / sampleRate;
      if (duration) averageBitrate = numberAt(bytes, vbri + 10, 4) * 8 / duration / 1000;
    }
    if (!duration && !cbr) throw new Error('VBR bitrate and duration cannot be verified');
    if (sampledFrames < 2) throw new Error('Too few complete MP3 frames');
    return { format: 'mp3', bitrate, averageBitrate, sampleRate, channels, duration, cbr };
  }
  throw new Error('Response is not a recognized MP3/FLAC stream');
}

function http(url, options, job) {
  return new Promise((resolve, reject) => {
    const remaining = job.deadline - Date.now();
    if (remaining <= 0) return reject(new Error('Total request deadline exceeded'));
    let settled = false;
    let cancel;
    const timeout = Math.min(CONFIG.timeoutMs, remaining);
    const deadline = Date.now() + timeout;
    const stop = () => {
      try { if (typeof cancel === 'function') cancel(); else if (cancel && typeof cancel.cancel === 'function') cancel.cancel(); } catch (_) {}
    };
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      stop();
      reject(Object.assign(new Error('Request timed out'), { transient: true }));
    }, timeout);
    try {
      cancel = request(url, { method: 'GET', ...options, timeout, headers: { 'User-Agent': 'LX-Music-Mobile', ...(options.headers || {}) } }, (error, response, body) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        if (Date.now() >= deadline) { stop(); return reject(Object.assign(new Error('Request deadline exceeded'), { transient: true })); }
        if (error) return reject(Object.assign(new Error('Network request failed'), { transient: true }));
        if (!response) return reject(new Error('Empty response'));
        const status = response.statusCode || response.status;
        if (!(status >= 200 && status < 300)) return reject(Object.assign(new Error('HTTP ' + status), { transient: status === 429 || status >= 500 }));
        const headers = {};
        for (const key of Object.keys(response.headers || {})) headers[key.toLowerCase()] = response.headers[key];
        resolve({ ...response, headers, statusCode: status, body: response.body != null ? response.body : body });
      });
    } catch (error) { settled = true; clearTimeout(timer); reject(new Error('Host request failed')); }
  });
}

async function json(url, options, job) {
  const response = await http(url, options || {}, job);
  let data = response.body;
  if (typeof data === 'string') {
    try { data = JSON.parse(data); } catch (_) { throw new Error('Endpoint did not return JSON'); }
  }
  if (!data || typeof data !== 'object') throw new Error('Invalid JSON response');
  const item = Array.isArray(data.data) ? data.data[0] : data.data;
  for (const value of [data, item].filter(Boolean)) {
    if (value.isTrial === true || value.isTrial === 1) throw new Error('Preview response rejected');
    for (const marker of [value.freeTrialInfo, value.trialInfo]) {
      if (marker === true || marker === 1) throw new Error('Preview response rejected');
      if (marker && typeof marker === 'object' && marker.isTrial !== false && marker.isTrial !== 0 && (marker.isTrial === true || Number(marker.end) > Number(marker.start || marker.begin || 0))) throw new Error('Preview response rejected');
    }
  }
  return data;
}

async function ensureToken(force) {
  if (!force && serverToken && Date.now() - tokenAt <= TOKEN_TTL) return serverToken;
  if (!tokenPromise) tokenPromise = (async () => {
    const data = await json('https://yy.zddyr.top/lx/api/token.php?device_id=' + encodeURIComponent(deviceId), {}, { deadline: Date.now() + 8000 });
    const token = data && data.data && data.data.token;
    if (typeof token !== 'string' || !token) throw new Error('Server token unavailable');
    return token;
  })();
  try {
    serverToken = await tokenPromise;
    tokenAt = Date.now();
    return serverToken;
  } finally {
    tokenPromise = null;
  }
}

async function xinghaiJson(params, job) {
  let refreshed = false;
  for (;;) {
    const token = await ensureToken(refreshed);
    const headers = { 'X-Token': token, 'X-Client': 'Appx64 Clear Music/2026.11.10' };
    if (CONFIG.license.trim()) headers['X-License'] = CONFIG.license.trim();
    let data;
    try {
      data = await json('https://yy.zddyr.top/lx/api/?' + query(params), { headers }, job);
    } catch (error) {
      if (!refreshed && /HTTP 403/.test(error.message)) { refreshed = true; serverToken = ''; tokenAt = 0; continue; }
      throw error;
    }
    if (Number(data.code) === 200 && data.url) return data;
    const auth = data.auth || {};
    if (!refreshed && (Number(data.code) === 403 || auth.tk_mismatch === true || auth.device_id === 'untrusted-token' || auth.tk_error)) {
      refreshed = true;
      serverToken = '';
      tokenAt = 0;
      continue;
    }
    throw new Error(data.msg ? String(data.msg).slice(0, 80) : 'Backend did not resolve the song');
  }
}

async function verify(url, quality, expectedDuration, job) {
  if (!CONFIG.verifyAudio) return null;
  // LX buffers the response before calling back; the timer limits time, not bytes.
  let offset = 0;
  let media;
  let continuation;
  let totalBytes;
  let audioOffset = 0;
  for (let attempt = 0; attempt < 8; attempt++) {
    const response = await http(url, { binary: true, headers: { Range: 'bytes=' + offset + '-' + (offset + 8191), 'Accept-Encoding': 'identity' } }, job);
    const bytes = bytesOf(response);
    if (response.statusCode === 206) {
      const range = /^bytes\s+(\d+)-(\d+)\/(\d+|\*)$/i.exec(String(response.headers['content-range'] || ''));
      if (!range || Number(range[1]) !== offset || Number(range[2]) - offset + 1 !== bytes.length) throw new Error('Invalid partial response');
      totalBytes = range[3] === '*' ? null : Number(range[3]);
    } else if (offset > 0 || bytes.length > 8192) throw new Error('Server ignored the audio range');
    else totalBytes = bytes.length;
    media = continuation && continuation.flacInfo ? inspectFlac(bytes, continuation.flacInfo, offset, 0, continuation.flacFrame) : inspectAudio(bytes);
    if (!media.skip) break;
    if (media.skip > 2 * 1024 * 1024) throw new Error('Audio metadata is too large');
    continuation = media;
    if (!media.flacInfo) audioOffset = media.skip;
    offset = media.skip;
  }
  if (!media || media.skip) throw new Error('Audio header unavailable');
  if (media.format === 'mp3' && !media.duration) {
    if (!media.cbr || !totalBytes || totalBytes <= audioOffset) throw new Error('MP3 duration is unavailable');
    media.duration = (totalBytes - audioOffset) * 8 / media.averageBitrate / 1000;
    media.estimatedDuration = true;
  }
  if ((quality === 'flac' || quality === 'flac24bit') && media.format !== 'flac') throw new Error('Requested lossless but received lossy audio');
  if (quality === 'flac24bit' && media.bitDepth < 24) throw new Error('Requested 24-bit but received lower bit depth');
  const minimum = quality === '320k' ? 300 : 120;
  if (media.format === 'mp3' && media.averageBitrate < minimum) throw new Error('Returned bitrate is below the requested quality');
  if (expectedDuration && media.duration && Math.abs(media.duration - expectedDuration) > Math.max(5, expectedDuration * 0.05)) throw new Error('Audio duration differs from the selected song');
  return media;
}

const BACKENDS = {
  gd: {
    sources: ['wy'],
    async fetch(source, id, quality, info, job) {
      const br = { '128k': 128, '320k': 320, flac: 740, flac24bit: 999 }[quality];
      const data = await json('https://music-api.gdstudio.xyz/api.php?' + query({ types: 'url', source: 'netease', id, br }), {}, job);
      return urlValue(data.url || (data.data && data.data.url));
    },
  },
  xinghai: {
    sources: ['tx', 'kw', 'kg', 'mg'],
    async fetch(source, id, quality, info, job) {
      const params = { source: { tx: 'qq', kw: 'kw', kg: 'kg', mg: 'migu' }[source], songmid: source === 'kg' ? pick(info, ['songmid', 'id']) || id : id, quality };
      if (source === 'kg') {
        params.mainHash = id;
        params.hash = info._types && info._types[quality] && info._types[quality].hash || id;
        params.albumId = pick(info, ['albumId']);
      } else {
        params.name = pick(info, ['name', 'songname', 'songName']);
        params.singer = pick(info, ['singer', 'artist']);
        params.albumName = pick(info, ['albumName', 'album']);
        params.interval = pick(info, ['interval']);
      }
      const data = await xinghaiJson(params, job);
      return urlValue(data.url);
    },
  },
  tang: {
    sources: ['tx'],
    async fetch(source, id, quality, info, job) {
      if (!/^[A-Za-z0-9]{14}$/.test(id)) throw new Error('QQ needs a string songmid');
      // This endpoint exposes one lossless stream; it can satisfy any lower requested tier.
      const data = await json('https://tang.api.s01s.cn/music_open_api.php?' + query({ mid: id }), {}, job);
      return urlValue(data.song_play_url_sq || data.song_play_url_pq);
    },
  },
  kuwoOfficial: {
    sources: ['kw'],
    async fetch(source, id, quality, info, job) {
      const br = { '128k': '128kmp3', '320k': '320kmp3', flac: '2000kflac' }[quality];
      const data = await json('https://mobi.kuwo.cn/mobi.s?' + query({ f: 'web', rid: id, br, source: 'jiakong', type: 'convert_url_with_sign', surl: 1 }), {}, job);
      return urlValue(data.data && (data.data.surl || data.data.url));
    },
  },
  wwwweb: {
    sources: ['wy'],
    async fetch(source, id, quality, info, job) {
      const data = await json('https://c.wwwweb.top/music/url', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source, musicId: id, quality }) }, job);
      if (Number(data.code) !== 200) throw new Error('Backend did not resolve the song');
      return urlValue(data.url);
    },
  },
  qqOfficial: {
    sources: ['tx'],
    async fetch(source, id, quality, info, job) {
      if (!/^[A-Za-z0-9]{14}$/.test(id)) throw new Error('QQ needs songmid, not a numeric song id');
      const cookie = CONFIG.qqCookie.trim();
      const uinMatch = /(?:^|;\s*)(?:uin|qqmusic_uin)=o?(\d+)/.exec(cookie);
      const uin = uinMatch ? uinMatch[1] : '0';
      const mediaMid = pick(info, ['strMediaMid', 'mediaMid', 'media_mid']) || id;
      const file = ({ '128k': 'M500', '320k': 'M800', flac: 'F000' }[quality]) + mediaMid + (quality === 'flac' ? '.flac' : '.mp3');
      const guid = String(Date.now());
      const payload = { comm: { uin: Number(uin), format: 'json', ct: 24, cv: 0 }, req_0: { module: 'vkey.GetVkeyServer', method: 'CgiGetVkey', param: { filename: [file], guid, songmid: [id], songtype: [0], uin, loginflag: cookie ? 1 : 0, platform: '20' } } };
      const headers = { 'Content-Type': 'application/json', Referer: 'https://y.qq.com/' };
      if (cookie) headers.Cookie = cookie;
      const data = await json('https://u.y.qq.com/cgi-bin/musicu.fcg', { method: 'POST', headers, body: JSON.stringify(payload) }, job);
      const result = data.req_0 && data.req_0.data;
      const entry = result && result.midurlinfo && result.midurlinfo[0];
      if (!entry || !entry.purl) throw new Error('QQ official returned no permitted stream');
      return urlValue((result.sip && result.sip[0] || 'https://isure.stream.qqmusic.qq.com/') + entry.purl);
    },
  },
  vkeys: {
    sources: ['tx'],
    async fetch(source, id, quality, info, job) {
      if (!/^[A-Za-z0-9]{14}$/.test(id)) throw new Error('QQ needs a string songmid');
      const data = await json('https://api.vkeys.cn/v2/music/tencent/geturl?' + query({ mid: id, quality: { '128k': 8, '320k': 9, flac: 10 }[quality] }), {}, job);
      return urlValue(data.data && data.data.url || data.url);
    },
  },
};
const ORDER = { wy: ['gd', 'wwwweb'], tx: ['qqOfficial', 'tang', 'vkeys', 'xinghai'], kw: ['xinghai', 'kuwoOfficial'], kg: ['xinghai'], mg: ['xinghai'] };

async function resolveMusic(source, info, quality) {
  if (!QUALITIES[source]) throw new Error('Unsupported music platform');
  if (!info || typeof info !== 'object') throw new Error('Missing musicInfo');
  if (!QUALITIES[source].includes(quality)) throw new Error('Unsupported quality');
  const id = songId(source, info);
  if (!id) throw new Error('Missing song identifier');
  const expectedDuration = durationSeconds(info);
  const hash = source === 'kg' && info._types && info._types[quality] && info._types[quality].hash || '';
  const key = JSON.stringify([source, id, quality, hash, expectedDuration, pick(info, ['albumId'])]);
  const cached = cache.get(key);
  if (cached && cached.expires > Date.now()) {
    cache.delete(key);
    cache.set(key, cached);
    return cached.url;
  }
  cache.delete(key);
  if (inflight.has(key)) return inflight.get(key);
  const operation = (async () => {
    const job = { deadline: Date.now() + CONFIG.totalTimeoutMs };
    const failures = [];
    const chain = ['flac24bit', 'flac', '320k', '128k'];
    const qualities = CONFIG.allowDowngrade ? chain.slice(chain.indexOf(quality)).filter(q => QUALITIES[source].includes(q)) : [quality];
    for (const q of qualities) {
      for (const name of ORDER[source]) {
        if (!CONFIG.backends[name] || !BACKENDS[name].sources.includes(source)) continue;
        const route = name + ':' + source + ':' + q;
        const state = health.get(route);
        if (state && state.until > Date.now()) { failures.push(name + ': temporarily cooling down'); continue; }
        if (Date.now() >= job.deadline) throw new Error('Total request deadline exceeded');
        try {
          const url = await BACKENDS[name].fetch(source, id, q, info, job);
          const media = await verify(url, q, expectedDuration, job);
          if (Date.now() >= job.deadline) throw new Error('Total request deadline exceeded');
          health.delete(route);
          cache.set(key, { url, expires: Date.now() + CONFIG.cacheTtlMs });
          if (cache.size > CONFIG.cacheMaxSize) cache.delete(cache.keys().next().value);
          if (q !== quality) console.warn('[Clear Music] Explicit fallback: ' + quality + ' -> ' + q);
          log(source + ' ' + q + ' via ' + name + (media ? ' (' + media.format + ')' : ' (unverified)'));
          return url;
        } catch (error) {
          if (error.transient) {
            const count = (state && state.count || 0) + 1;
            health.set(route, { count, until: count >= 2 ? Date.now() + 20000 : 0 });
          }
          failures.push(name + ': ' + error.message);
          log(source + ' ' + q + ' rejected ' + name + ': ' + error.message);
        }
      }
    }
    throw new Error('No verified ' + source + '/' + quality + ' stream. ' + failures.join('; '));
  })();
  inflight.set(key, operation);
  try { return await operation; } finally { inflight.delete(key); }
}

on(EVENT_NAMES.request, async ({ action, source, info } = {}) => {
  if (action !== 'musicUrl') throw new Error('Only musicUrl is supported');
  return resolveMusic(source, info && info.musicInfo, info && info.type);
});

const sources = {};
for (const source of Object.keys(QUALITIES)) sources[source] = { name: NAMES[source], type: 'music', actions: ['musicUrl'], qualitys: QUALITIES[source] };
send(EVENT_NAMES.inited, { status: true, sources, ...(env === 'desktop' ? { openDevTools: false } : {}) });
