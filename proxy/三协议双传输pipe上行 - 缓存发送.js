/*
// 代码基本都抄的CM和天书大佬的项目，在此感谢各位大佬的无私奉献。
// 支持xhttp和trojan和vless和ss和socks5协议入站,ss协议无密码，ss和socks5协议只能纯手搓，socks5协议不能在路径使用ed=2560参数
// ws模式的vless导入链接：vless://{这里写uuid}@104.16.40.11:2053?encryption=none&security=tls&sni={这里写域名}&alpn=http%2F1.1&fp=chrome&type=ws&host={这里写域名}#vless
// ws模式的trojan导入链接：trojan://{这里写密码}@104.16.40.11:2053?security=tls&sni={这里写域名}&alpn=http%2F1.1&fp=chrome&allowInsecure=1&type=ws&host={这里写域名}#trojan
// xhttp模式的vless导入链接：vless://{这里写uuid}@104.16.40.11:2053?encryption=none&security=tls&sni={这里写域名}&alpn=h2&fp=chrome&allowInsecure=1&type=xhttp&host={这里写域名}&mode=stream-one#vless-xhttp
// xhttp模式的trojan导入链接：trojan://passwd@104.16.40.11:2053?security=tls&sni=sni&alpn=h2&fp=chrome&allowInsecure=1&type=xhttp&host=host&path=%2F&mode=stream-one#trojan-xhttp
// 复制协议开头的导入链接导入再手动修改即可
 * ========================== URL路径参数速查表 =================================================================================
 * 多个参数用 & 连接, 示例: /?s5=host:port&ip=1.2.3.4:443   注: s5/http/nat64/ip 均支持逗号分隔多个地址以实现并发连接
 * s5/gs5/socks/s5all         - 直连失败SOCKS5代理 / 全局SOCKS5        示例: s5=user1:pass1@host1:port1,user2:pass2@host2:port2
 * http/ghttp/httpall         - 直连失败HTTP代理 / 全局HTTP            示例: http=user1:pass1@host1:port1,user2:pass2@host2:port2
 * nat64/gnat64/nat64all      - 直连失败NAT64转换 / 全局NAT64          示例: nat64=64:ff9b::,64:ff9b:1::
 * ip/pyip/proxyip            - 直连失败时的备用IP                     示例: ip=1.2.3.4:443,5.6.7.8:443
 * proxyall/globalproxy       - 全局代理标志,无s5和http参数时纯直连      示例: proxyall=1
 * ==========================================================================================================================*/
import {connect} from 'cloudflare:sockets';
const uuid = 'd342d11e-d424-4583-b36e-524ab1f0afa4';//vless使用的uuid
//**警告**:trojan使用的sha224密钥，需要自己计算，当前设置为密码666的密钥
//**警告**:trojan使用的sha224密钥，需要自己计算，当前设置为密码666的密钥
//**警告**:trojan使用的sha224密钥，需要自己计算，当前设置为密码666的密钥
//**警告**:trojan使用的sha224密钥计算网址：https://www.lzltool.com/data-sha224
const passWordSha224 = '509eece82eb6910bebef9af9496092d3244b6c0d69ef3aaa4b12c565';
const socks5User = 'admin';//socsk5协议用户名
const socks5Pass = '123456';//socsk5协议密码
// ---------------------------------------------------------------------------------
// 理论最大带宽计算公式 (Theoretical Max Bandwidth Calculation):
//    - 速度上限 (Mbps) = (bufferSize (字节) / flushTime (毫秒)) * 0.008
//    - 示例: (512 * 1024 字节 / 10 毫秒) * 0.008 ≈ 419 Mbps
//    - 在此模式下，这两个参数共同构成了一个精确的速度限制器。
// ---------------------------------------------------------------------------------
/** 缓冲区最大大小。用于计算速度上限。*/
const bufferSize = 480 * 1024; // 512KB
/** 缓冲区写入占比。用于平衡slice和subarray的开销。*/
const flushRatio = 0.75;  // 缓冲区写入小于75%bufferSize使用slice，大于就使用subarray
/** 发送调用刷新时间(毫秒)。设定固定的发送频率以控制速度。*/
/**- **警告**: 设置过低  会因定时器精度和高频创建/销毁开销导致 CPU 负担加重。*/
const flushTime = 3; // 3ms，想要测速数字跑到180MB/s改到1即可
// ---------------------------------------------------------------------------------
/** TCPsocket并发获取，可提高tcp连接成功率*/
const concurrentOnlyDomain = false;//只对域名并发开关
/**- **警告**: snippets只能设置为1，worker最大支持6，超过6没意义*/
let concurrency = 4;//socket获取并发数
// ---------------------------------------------------------------------------------
//三者的socket获取顺序，全局模式下为这三个的顺序，非全局为：直连>socks>http>nat64>proxyip>finallyProxyHost
/**- **警告**: snippets只支持最大两次connect，所以snippets全局nat64不能使用域名访问，snippets访问cf失败的备用只有第一个有效*/
const proxyStrategyOrder = ['socks', 'http', 'nat64'];
const dohEndpoints = ['https://cloudflare-dns.com/dns-query', 'https://dns.google/dns-query'];
const dohNatEndpoints = ['https://cloudflare-dns.com/dns-query', 'https://dns.google/resolve'];
const proxyIpAddrs = {EU: 'ProxyIP.DE.CMLiussss.net', AS: 'ProxyIP.SG.CMLiussss.net', JP: 'ProxyIP.JP.CMLiussss.net', US: 'ProxyIP.US.CMLiussss.net'};//分区域proxyip
const finallyProxyHost = 'ProxyIP.CMLiussss.net';//兜底proxyip
const coloRegions = {
    JP: new Set(['FUK', 'ICN', 'KIX', 'NRT', 'OKA']),
    EU: new Set([
        'ACC', 'ADB', 'ALA', 'ALG', 'AMM', 'AMS', 'ARN', 'ATH', 'BAH', 'BCN', 'BEG', 'BGW', 'BOD', 'BRU', 'BTS', 'BUD', 'CAI',
        'CDG', 'CPH', 'CPT', 'DAR', 'DKR', 'DMM', 'DOH', 'DUB', 'DUR', 'DUS', 'DXB', 'EBB', 'EDI', 'EVN', 'FCO', 'FRA', 'GOT',
        'GVA', 'HAM', 'HEL', 'HRE', 'IST', 'JED', 'JIB', 'JNB', 'KBP', 'KEF', 'KWI', 'LAD', 'LED', 'LHR', 'LIS', 'LOS', 'LUX',
        'LYS', 'MAD', 'MAN', 'MCT', 'MPM', 'MRS', 'MUC', 'MXP', 'NBO', 'OSL', 'OTP', 'PMO', 'PRG', 'RIX', 'RUH', 'RUN', 'SKG',
        'SOF', 'STR', 'TBS', 'TLL', 'TLV', 'TUN', 'VIE', 'VNO', 'WAW', 'ZAG', 'ZRH']),
    AS: new Set([
        'ADL', 'AKL', 'AMD', 'BKK', 'BLR', 'BNE', 'BOM', 'CBR', 'CCU', 'CEB', 'CGK', 'CMB', 'COK', 'DAC', 'DEL', 'HAN', 'HKG',
        'HYD', 'ISB', 'JHB', 'JOG', 'KCH', 'KHH', 'KHI', 'KTM', 'KUL', 'LHE', 'MAA', 'MEL', 'MFM', 'MLE', 'MNL', 'NAG', 'NOU',
        'PAT', 'PBH', 'PER', 'PNH', 'SGN', 'SIN', 'SYD', 'TPE', 'ULN', 'VTE'])
};
const coloToProxyMap = new Map();
for (const [region, colos] of Object.entries(coloRegions)) {for (const colo of colos) coloToProxyMap.set(colo, proxyIpAddrs[region])}
const uuidBytes = new Uint8Array(16), hashBytes = new Uint8Array(56), offsets = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 4, 4, 4, 4];
for (let i = 0, c; i < 16; i++) uuidBytes[i] = (((c = uuid.charCodeAt(i * 2 + offsets[i])) > 64 ? c + 9 : c) & 0xF) << 4 | (((c = uuid.charCodeAt(i * 2 + offsets[i] + 1)) > 64 ? c + 9 : c) & 0xF);
for (let i = 0; i < 56; i++) hashBytes[i] = passWordSha224.charCodeAt(i);
const [textEncoder, textDecoder, socks5Init, socks5req] = [new TextEncoder(), new TextDecoder(), new Uint8Array([5, 2, 0, 2]), new Uint8Array([5, 0, 0, 1, 0, 0, 0, 0, 0, 0])];
let socks5Pkg;
if (socks5User && socks5Pass) {
    const userBytes = textEncoder.encode(socks5User), passBytes = textEncoder.encode(socks5Pass);
    socks5Pkg = new Uint8Array(3 + userBytes.length + passBytes.length);
    socks5Pkg[0] = 1, socks5Pkg[1] = userBytes.length, socks5Pkg.set(userBytes, 2), socks5Pkg[2 + userBytes.length] = passBytes.length, socks5Pkg.set(passBytes, 3 + userBytes.length);
}
const html = `<html><head><title>404 Not Found</title></head><body><center><h1>404 Not Found</h1></center><hr><center>nginx/1.25.3</center></body></html>`;
const binaryAddrToString = (addrType, addrBytes) => {
    if (addrType === 3) return textDecoder.decode(addrBytes);
    if (addrType === 1) return `${addrBytes[0]}.${addrBytes[1]}.${addrBytes[2]}.${addrBytes[3]}`;
    if (addrType === 4) {
        let ipv6 = ((addrBytes[0] << 8) | addrBytes[1]).toString(16);
        for (let i = 1; i < 8; i++) ipv6 += ':' + ((addrBytes[i * 2] << 8) | addrBytes[i * 2 + 1]).toString(16);
        return `[${ipv6}]`;
    }
};
const parseHostPort = (addr, defaultPort) => {
    if (addr.charCodeAt(0) === 91) {
        const sepIndex = addr.indexOf(']:');
        if (sepIndex !== -1) return [addr.substring(0, sepIndex + 1), addr.substring(sepIndex + 2)];
        return [addr, defaultPort];
    }
    const tpIndex = addr.indexOf('.tp');
    const lastColon = addr.lastIndexOf(':');
    if (tpIndex !== -1 && lastColon === -1) return [addr, addr.substring(tpIndex + 3, addr.indexOf('.', tpIndex + 3))];
    if (lastColon === -1) return [addr, defaultPort];
    return [addr.substring(0, lastColon), addr.substring(lastColon + 1)];
};
const parseAuthString = (authParam) => {
    let username, password, hostStr;
    const atIndex = authParam.lastIndexOf('@');
    if (atIndex === -1) {hostStr = authParam} else {
        const cred = authParam.substring(0, atIndex);
        hostStr = authParam.substring(atIndex + 1);
        const colonIndex = cred.indexOf(':');
        if (colonIndex === -1) {username = cred} else {
            username = cred.substring(0, colonIndex);
            password = cred.substring(colonIndex + 1);
        }
    }
    const [hostname, port] = parseHostPort(hostStr, 1080);
    return {username, password, hostname, port};
};
const isIPv4optimized = (str) => {
    if (str.length > 15 || str.length < 7) return false;
    let part = 0, dots = 0, partLen = 0;
    for (let i = 0; i < str.length; i++) {
        const charCode = str.charCodeAt(i);
        if (charCode === 46) {
            dots++;
            if (dots > 3 || partLen === 0 || (str.charCodeAt(i - 1) === 48 && partLen > 1)) return false;
            part = 0;
            partLen = 0;
        } else if (charCode >= 48 && charCode <= 57) {
            partLen++;
            part = part * 10 + (charCode - 48);
            if (part > 255 || partLen > 3) return false;
        } else {return false}
    }
    return !(dots !== 3 || partLen === 0 || (str.charCodeAt(str.length - partLen) === 48 && partLen > 1));
};
const isDomainName = (inputStr) => {
    if (!concurrentOnlyDomain) return true;
    if (!inputStr || inputStr.charCodeAt(0) === 91) return false;
    if (inputStr[0].charCodeAt(0) < 48 || inputStr[0].charCodeAt(0) > 57) return true;
    return !isIPv4optimized(inputStr);
};
const createConnect = (hostname, port, socket = connect({hostname, port})) => socket.opened.then(() => socket);
const concurrentConnect = (hostname, port, addrType, limit = concurrency) => {
    if (limit === 1 || (concurrentOnlyDomain && addrType !== 3)) return createConnect(hostname, port);
    return Promise.any(Array(limit).fill(null).map(() => createConnect(hostname, port)));
};
const connectViaSocksProxy = async (targetAddrType, targetPortNum, socksAuth, addrBytes, limit) => {
    const addrType = isDomainName(socksAuth.hostname) ? 3 : 0;
    const socksSocket = await concurrentConnect(socksAuth.hostname, socksAuth.port, addrType, limit);
    const writer = socksSocket.writable.getWriter();
    const reader = socksSocket.readable.getReader();
    await writer.write(socks5Init);
    const {value: authResponse} = await reader.read();
    if (!authResponse || authResponse[0] !== 5 || authResponse[1] === 0xFF) return null;
    if (authResponse[1] === 2) {
        if (!socksAuth.username) return null;
        const userBytes = textEncoder.encode(socksAuth.username);
        const passBytes = textEncoder.encode(socksAuth.password || '');
        const uLen = userBytes.length, pLen = passBytes.length, authReq = new Uint8Array(3 + uLen + pLen)
        authReq[0] = 1, authReq[1] = uLen, authReq.set(userBytes, 2), authReq[2 + uLen] = pLen, authReq.set(passBytes, 3 + uLen);
        await writer.write(authReq);
        const {value: authResult} = await reader.read();
        if (!authResult || authResult[0] !== 1 || authResult[1] !== 0) return null;
    } else if (authResponse[1] !== 0) {return null}
    const isDomain = targetAddrType === 3, socksReq = new Uint8Array(6 + addrBytes.length + (isDomain ? 1 : 0));
    socksReq[0] = 5, socksReq[1] = 1, socksReq[2] = 0, socksReq[3] = targetAddrType;
    isDomain ? (socksReq[4] = addrBytes.length, socksReq.set(addrBytes, 5)) : socksReq.set(addrBytes, 4);
    socksReq[socksReq.length - 2] = targetPortNum >> 8, socksReq[socksReq.length - 1] = targetPortNum & 0xff;
    await writer.write(socksReq);
    const {value: finalResponse} = await reader.read();
    if (!finalResponse || finalResponse[1] !== 0) return null;
    writer.releaseLock(), reader.releaseLock();
    return socksSocket;
};
const staticHeaders = `User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36\r\nProxy-Connection: Keep-Alive\r\nConnection: Keep-Alive\r\n\r\n`;
const encodedStaticHeaders = textEncoder.encode(staticHeaders);
const connectViaHttpProxy = async (targetAddrType, targetPortNum, httpAuth, addrBytes, limit) => {
    const {username, password, hostname, port} = httpAuth;
    const addrType = isDomainName(hostname) ? 3 : 0;
    const proxySocket = await concurrentConnect(hostname, port, addrType, limit);
    const writer = proxySocket.writable.getWriter();
    const httpHost = binaryAddrToString(targetAddrType, addrBytes);
    let dynamicHeaders = `CONNECT ${httpHost}:${targetPortNum} HTTP/1.1\r\nHost: ${httpHost}:${targetPortNum}\r\n`;
    if (username) dynamicHeaders += `Proxy-Authorization: Basic ${btoa(`${username}:${password || ''}`)}\r\n`;
    const fullHeaders = new Uint8Array(dynamicHeaders.length * 3 + encodedStaticHeaders.length);
    const {written} = textEncoder.encodeInto(dynamicHeaders, fullHeaders);
    fullHeaders.set(encodedStaticHeaders, written);
    await writer.write(fullHeaders.subarray(0, written + encodedStaticHeaders.length));
    writer.releaseLock();
    const reader = proxySocket.readable.getReader();
    const buffer = new Uint8Array(256);
    let bytesRead = 0, statusChecked = false;
    while (bytesRead < buffer.length) {
        const {value, done} = await reader.read();
        if (done || bytesRead + value.length > buffer.length) return null;
        const prevBytesRead = bytesRead;
        buffer.set(value, bytesRead);
        bytesRead += value.length;
        if (!statusChecked && bytesRead >= 12) {
            if (buffer[9] !== 50) return null;
            statusChecked = true;
        }
        const searchStart = Math.max(15, prevBytesRead - 3);
        for (let i = searchStart; i <= bytesRead - 4; i++) {
            const found = buffer[i] === 13 && buffer[i + 1] === 10 && buffer[i + 2] === 13 && buffer[i + 3] === 10;
            if (found) {
                reader.releaseLock();
                if (bytesRead > i + 4) {
                    const {readable, writable} = new TransformStream();
                    const writer = writable.getWriter();
                    writer.write(buffer.subarray(i + 4, bytesRead));
                    writer.releaseLock();
                    proxySocket.readable.pipeTo(writable).catch(() => {});
                    // @ts-ignore
                    proxySocket.readable = readable;
                }
                return proxySocket;
            }
        }
    }
    return null;
};
const parseAddress = (buffer, offset, addrType) => {
    const addressLength = addrType === 3 ? buffer[offset++] : addrType === 1 ? 4 : addrType === 4 ? 16 : null;
    if (addressLength === null) return null;
    const dataOffset = offset + addressLength;
    if (dataOffset > buffer.length) return null;
    const addrBytes = buffer.subarray(offset, dataOffset);
    return {addrBytes, dataOffset};
};
const parseRequestData = (firstChunk) => {
    for (let i = 0; i < 16; i++) if (firstChunk[i + 1] !== uuidBytes[i]) return null;
    let offset = 19 + firstChunk[17];
    const port = (firstChunk[offset] << 8) | firstChunk[offset + 1];
    let addrType = firstChunk[offset + 2];
    if (addrType !== 1) addrType += 1;
    const addrInfo = parseAddress(firstChunk, offset + 3, addrType);
    if (!addrInfo) return null;
    return {addrType, addrBytes: addrInfo.addrBytes, dataOffset: addrInfo.dataOffset, port, isDns: port === 53};
};
const parseTransparent = (firstChunk) => {
    for (let i = 0; i < 56; i++) if (firstChunk[i] !== hashBytes[i]) return null;
    const addrType = firstChunk[59];
    const addrInfo = parseAddress(firstChunk, 60, addrType);
    if (!addrInfo) return null;
    const port = (firstChunk[addrInfo.dataOffset] << 8) | firstChunk[addrInfo.dataOffset + 1];
    return {addrType, addrBytes: addrInfo.addrBytes, dataOffset: addrInfo.dataOffset + 4, port, isDns: port === 53};
};
const parseShadow = (firstChunk) => {
    const addrType = firstChunk[0];
    const addrInfo = parseAddress(firstChunk, 1, addrType);
    if (!addrInfo) return null;
    const port = (firstChunk[addrInfo.dataOffset] << 8) | firstChunk[addrInfo.dataOffset + 1];
    return {addrType, addrBytes: addrInfo.addrBytes, dataOffset: addrInfo.dataOffset + 2, port, isDns: port === 53};
};
const parseSocks5 = (firstChunk) => {
    if (firstChunk[2] !== 0) return null;
    const addrType = firstChunk[3];
    const addrInfo = parseAddress(firstChunk, 4, addrType);
    if (!addrInfo) return null;
    const port = (firstChunk[addrInfo.dataOffset] << 8) | firstChunk[addrInfo.dataOffset + 1];
    return {addrType, addrBytes: addrInfo.addrBytes, dataOffset: addrInfo.dataOffset + 2, port, isSocks5: true};
};
const ipv4ToNat64Ipv6 = (ipv4Address, nat64Prefixes) => {
    const parts = ipv4Address.split('.');
    let hexStr = "";
    for (let i = 0; i < 4; i++) {
        let h = (parts[i] | 0).toString(16);
        hexStr += (h.length === 1 ? "0" + h : h);
        if (i === 1) hexStr += ":";
    }
    return `[${nat64Prefixes}${hexStr}]`;
};
const dohJsonOptions = {headers: {'Accept': 'application/dns-json'}}, dohHeaders = {'content-type': 'application/dns-message'};
const concurrentDnsResolve = async (hostname, recordType) => {
    const dnsResult = await Promise.any(dohNatEndpoints.map(endpoint =>
        fetch(`${endpoint}?name=${hostname}&type=${recordType}`, dohJsonOptions).then(response => {
            if (!response.ok) throw new Error();
            return response.json();
        })
    ));
    const answer = dnsResult.Answer || dnsResult.answer;
    if (!answer || answer.length === 0) return null;
    return answer;
};
const dohDnsHandler = async (payload) => {
    if (payload.byteLength < 2) throw new Error();
    const dnsQueryData = payload.subarray(2);
    const resp = await Promise.any(dohEndpoints.map(endpoint =>
        fetch(endpoint, {method: 'POST', headers: dohHeaders, body: dnsQueryData}).then(response => {
            if (!response.ok) throw new Error();
            return response;
        })
    ));
    const dnsQueryResult = await resp.arrayBuffer();
    const udpSize = dnsQueryResult.byteLength;
    const packet = new Uint8Array(2 + udpSize);
    packet[0] = (udpSize >> 8) & 0xff, packet[1] = udpSize & 0xff;
    packet.set(new Uint8Array(dnsQueryResult), 2);
    return packet;
};
const connectNat64 = async (addrType, port, nat64Auth, addrBytes, proxyAll, limit) => {
    const nat64Prefixes = nat64Auth.charCodeAt(0) === 91 ? nat64Auth.slice(1, -1) : nat64Auth;
    if (!proxyAll) return concurrentConnect(`[${nat64Prefixes}6815:3598]`, port, 4, limit);
    if (addrType === 4) return null;
    const hostname = binaryAddrToString(addrType, addrBytes);
    if (addrType === 1) return concurrentConnect(ipv4ToNat64Ipv6(hostname, nat64Prefixes), port, 4, limit);
    if (addrType === 3) {
        const answer = await concurrentDnsResolve(hostname, 'A');
        if (!answer) return null;
        const aRecord = answer.find(record => record.type === 1);
        if (aRecord && aRecord.data) return concurrentConnect(ipv4ToNat64Ipv6(aRecord.data, nat64Prefixes), port, 4, limit);
    }
    return null;
};
const williamResult = async (william) => {
    const answer = await concurrentDnsResolve(william, 'TXT');
    if (!answer) return null;
    let txtData, i = 0, len = answer.length;
    for (; i < len; i++) if (answer[i].type === 16) {
        txtData = answer[i].data;
        break;
    }
    if (!txtData) return null;
    if (txtData.charCodeAt(0) === 34 && txtData.charCodeAt(txtData.length - 1) === 34) txtData = txtData.slice(1, -1);
    const raw = txtData.split(/,|\\010|\n/), prefixes = [];
    for (i = 0, len = raw.length; i < len; i++) {
        const s = raw[i].trim();
        if (s) prefixes.push(s);
    }
    return prefixes.length ? prefixes : null;
};
const proxyIpRegex = /\.(william|sni2025\.netlib)/;
const connectProxyIp = async (param, limit) => {
    if (proxyIpRegex.test(param)) {
        const resolvedIps = await williamResult(param);
        if (!resolvedIps || resolvedIps.length === 0) return null;
        const connectionPromises = resolvedIps.map(ip => {
            const [host, port] = parseHostPort(ip, 443);
            return createConnect(host, port);
        });
        return await Promise.any(connectionPromises);
    }
    const [host, port] = parseHostPort(param, 443);
    const addrType = isDomainName(host) ? 3 : 0;
    return concurrentConnect(host, port, addrType, limit);
};
const strategyExecutorMap = new Map([
    [0, async ({addrType, port, addrBytes}) => {
        const hostname = binaryAddrToString(addrType, addrBytes);
        return concurrentConnect(hostname, port, addrType);
    }],
    [1, async ({addrType, port, addrBytes}, param, limit) => {
        const socksAuth = parseAuthString(param);
        return connectViaSocksProxy(addrType, port, socksAuth, addrBytes, limit);
    }],
    [2, async ({addrType, port, addrBytes}, param, limit) => {
        const httpAuth = parseAuthString(param);
        return connectViaHttpProxy(addrType, port, httpAuth, addrBytes, limit);
    }],
    [3, async (_parsedRequest, param, limit) => {
        return connectProxyIp(param, limit);
    }],
    [4, async ({addrType, port, addrBytes}, param, limit) => {
        const {nat64Auth, proxyAll} = param;
        return connectNat64(addrType, port, nat64Auth, addrBytes, proxyAll, limit);
    }]
]);
const paramRegex = /(gs5|s5all|ghttp|gnat64|nat64all|httpall|s5|socks|http|ip|nat64)(?:=|:\/\/|%3A%2F%2F)([^&]+)|(proxyall|globalproxy)/gi;
const establishTcpConnection = async (parsedRequest, request) => {
    let u = request.url, clean = u.slice(u.indexOf('/', 10) + 1, u.charCodeAt(u.length - 1) === 47 ? -1 : undefined), list = [];
    if (clean.length < 6) {list.push({type: 0}, {type: 3, param: coloToProxyMap.get(request.cf?.colo) ?? proxyIpAddrs.US}, {type: 3, param: finallyProxyHost})} else {
        paramRegex.lastIndex = 0;
        let m, p = Object.create(null);
        while ((m = paramRegex.exec(clean))) p[(m[1] || m[3]).toLowerCase()] = m[2] ? (m[2].charCodeAt(m[2].length - 1) === 61 ? m[2].slice(0, -1) : m[2]) : true;
        const s5 = p.gs5 || p.s5all || p.s5 || p.socks, http = p.ghttp || p.httpall || p.http, nat64 = p.gnat64 || p.nat64all || p.nat64;
        const proxyAll = !!(p.gs5 || p.s5all || p.ghttp || p.httpall || p.gnat64 || p.nat64all || p.proxyall || p.globalproxy);
        if (!proxyAll) list.push({type: 0});
        const add = (v, t) => {
            if (!v) return;
            const parts = decodeURIComponent(v).split(',').filter(Boolean);
            if (parts.length) list.push({type: t, param: parts.map(part => t === 4 ? {nat64Auth: part, proxyAll} : part), concurrent: true});
        };
        for (let i = 0; i < proxyStrategyOrder.length; i++) {
            const k = proxyStrategyOrder[i];
            add(k === 'socks' ? s5 : k === 'http' ? http : nat64, k === 'socks' ? 1 : k === 'http' ? 2 : 4);
        }
        if (proxyAll) {if (!list.length) list.push({type: 0})} else {
            add(p.ip, 3);
            list.push({type: 3, param: coloToProxyMap.get(request.cf?.colo) ?? proxyIpAddrs.US}, {type: 3, param: finallyProxyHost});
        }
    }
    for (let i = 0; i < list.length; i++) {
        try {
            const exec = strategyExecutorMap.get(list[i].type);
            const sub = (list[i]['concurrent'] && Array.isArray(list[i].param)) ? Math.max(1, Math.floor(concurrency / list[i].param.length)) : undefined;
            const socket = await (list[i]['concurrent'] && Array.isArray(list[i].param) ? Promise.any(list[i].param.map(ip => exec(parsedRequest, ip, sub))) : exec(parsedRequest, list[i].param));
            if (socket) return socket;
        } catch {}
    }
    return null;
};
const safeBufferSize = bufferSize - 4096, flushThreshold = Math.trunc(bufferSize * flushRatio);
const manualPipe = async (readable, writable) => {
    let buffer = new Uint8Array(bufferSize), chunkBuf = new ArrayBuffer(4096), offset = 0, timerId = null, resume = null;
    const flushBuffer = () => {
        offset > 0 && (offset >= flushThreshold ? (writable.send(buffer.subarray(0, offset)), buffer = new Uint8Array(bufferSize)) : writable.send(buffer.slice(0, offset)), offset = 0);
        timerId && (clearTimeout(timerId), timerId = null), resume?.(), resume = null;
    };
    const reader = readable.getReader({mode: 'byob'});
    try {
        while (true) {
            const {done, value} = await reader.read(new Uint8Array(chunkBuf));
            if (done) break;
            chunkBuf = value.buffer;
            if (value.byteLength < 4096) {
                flushBuffer();
                writable.send(value.slice());
            } else {
                buffer.set(value, offset);
                offset += 4096;
                timerId || (timerId = setTimeout(flushBuffer, flushTime));
                if (offset > safeBufferSize) await new Promise(resolve => resume = resolve);
            }
        }
    } finally {flushBuffer(), reader.releaseLock()}
};
const handleWebSocketConn = async (webSocket, request) => {
    const protocolHeader = request.headers.get('sec-websocket-protocol');
    // @ts-ignore
    const earlyData = protocolHeader ? Uint8Array.fromBase64(protocolHeader, {alphabet: 'base64url'}) : null;
    const webSocketStream = new ReadableStream({
        start(controller) {
            if (earlyData) controller.enqueue(earlyData);
            webSocket.addEventListener("message", event => controller.enqueue(event.data));
        },
        cancel() {if (!earlyData) webSocket.close()}
    });
    let messageHandler, parsedRequest, tcpSocket, socks5State = 0;
    const closeSocket = () => {if (!earlyData) {tcpSocket?.close(), webSocket?.close()}};
    webSocketStream.pipeTo(new WritableStream({
        async write(chunk) {
            if (messageHandler) return messageHandler(chunk);
            chunk = earlyData ? chunk : new Uint8Array(chunk);
            if (socks5State === 1) {
                let match = chunk.length === socks5Pkg.length;
                for (let i = 0; match && i < socks5Pkg.length; i++) if (chunk[i] !== socks5Pkg[i]) match = false;
                if (match) {
                    webSocket.send(new Uint8Array([1, 0])), socks5State = 2;
                    return;
                }
                webSocket.send(new Uint8Array([1, 1]));
                return closeSocket();
            }
            if (chunk[0] === 5) {
                if (!socks5State) {
                    const required = socks5User ? 2 : 0;
                    const methods = chunk.subarray(2, 2 + chunk[1]);
                    if (methods.indexOf(required) === -1) {
                        webSocket.send(new Uint8Array([5, 255]));
                        return closeSocket();
                    }
                    webSocket.send(new Uint8Array([5, required])), socks5State = required === 2 ? 1 : 2;
                    return;
                }
                if (socks5State === 2 && chunk[1] === 1) parsedRequest = parseSocks5(chunk);
            } else if (!socks5State) {
                if (chunk.length > 58 && chunk[56] === 0x0d && chunk[57] === 0x0a) {
                    parsedRequest = parseTransparent(chunk);
                } else if ((parsedRequest = parseRequestData(chunk))) {
                    webSocket.send(new Uint8Array([chunk[0], 0]));
                } else {parsedRequest = parseShadow(chunk)}
            }
            if (!parsedRequest) throw new Error();
            if (parsedRequest.isSocks5) webSocket.send(socks5req);
            const payload = chunk.subarray(parsedRequest.dataOffset);
            if (parsedRequest.isDns) {
                webSocket.send(await dohDnsHandler(payload));
                if (!earlyData) webSocket.close();
            } else {
                tcpSocket = await establishTcpConnection(parsedRequest, request);
                if (!tcpSocket) throw new Error();
                const tcpWriter = tcpSocket.writable.getWriter();
                if (payload.byteLength) tcpWriter.write(payload);
                messageHandler = (chunk) => tcpWriter.write(chunk);
                manualPipe(tcpSocket.readable, webSocket);
            }
        }
    })).catch(closeSocket).finally(closeSocket);
};
const xhttpResponseHeaders = {'Content-Type': 'application/octet-stream', 'X-Accel-Buffering': 'no', 'Cache-Control': 'no-store'};
const handleXhttp = async (request) => {
    const reader = request.body.getReader();
    let buffer = new Uint8Array(4096), used = 0, parsedRequest = null, resVersion = null, respStream;
    while (true) {
        const {value, done} = await reader.read();
        if (done) return new Response(null, {status: 500});
        if (used + value.length > buffer.length) {
            const newBuffer = new Uint8Array(Math.max(buffer.length * 2, used + value.length));
            newBuffer.set(buffer.subarray(0, used));
            buffer = newBuffer;
        }
        buffer.set(value, used);
        used += value.length;
        if (used < 30) continue;
        const currentBuffer = buffer.subarray(0, used);
        if (currentBuffer.length > 58 && currentBuffer[56] === 0x0d && currentBuffer[57] === 0x0a) {
            parsedRequest = parseTransparent(currentBuffer);
        } else if ((parsedRequest = parseRequestData(currentBuffer))) {
            resVersion = new Uint8Array([buffer[0], 0]);
        } else {parsedRequest = parseShadow(currentBuffer)}
        if (parsedRequest) break;
    }
    if (!parsedRequest) return new Response(null, {status: 500});
    try {
        const payload = buffer.subarray(parsedRequest.dataOffset, used);
        if (parsedRequest.isDns) {
            const dohResult = await dohDnsHandler(payload);
            resVersion ? (respStream = new Uint8Array(2 + dohResult.byteLength), respStream.set(resVersion), respStream.set(dohResult, 2)) : respStream = dohResult;
        } else {
            const tcpSocket = await establishTcpConnection(parsedRequest, request);
            if (!tcpSocket) return new Response(null, {status: 500});
            const requestToTcp = async () => {
                const writer = tcpSocket.writable.getWriter();
                if (payload.byteLength) writer.write(payload);
                writer.releaseLock();
                reader.releaseLock();
                await request.body.pipeTo(tcpSocket.writable);
            };
            requestToTcp().catch(() => tcpSocket.close());
            respStream = new ReadableStream({
                start(controller) {
                    if (resVersion) controller.enqueue(resVersion);
                    const writable = {send: (chunk) => controller.enqueue(chunk)};
                    manualPipe(tcpSocket.readable, writable).then(() => controller.close()).catch(err => controller.error(err));
                }
            });
        }
        return new Response(respStream, {headers: xhttpResponseHeaders});
    } catch {return new Response(null, {status: 500})}
};
export default {
    async fetch(request) {
        if (request.method === 'POST') return handleXhttp(request);
        if (request.headers.get('Upgrade') === 'websocket') {
            const {0: clientSocket, 1: webSocket} = new WebSocketPair();
            webSocket.accept();
            handleWebSocketConn(webSocket, request);
            return new Response(null, {status: 101, webSocket: clientSocket});
        }
        return new Response(html, {status: 404, headers: {'Content-Type': 'text/html; charset=UTF-8'}});
    }
};