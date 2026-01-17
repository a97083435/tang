export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // 【修改点 1】填写你绑定在 Snippets 上的域名
    // 注意：不要带 https://，只写域名，例如 node.example.com
    const targetHost = 'sss4.sss4.ccwu.cc'; 

    // 修改请求的 Host，确保 Snippets 能正确识别
    const newRequest = new Request(url.toString(), request);
    newRequest.headers.set('Host', targetHost);

    // 构造发往 Snippets 的目标 URL
    const targetUrl = `https://${targetHost}${url.pathname}${url.search}`;

    // 使用 fetch 转发请求
    return fetch(targetUrl, {
      method: request.method,
      headers: newRequest.headers,
      body: request.body,
      redirect: 'manual'
    });
  }
};

//把host和sni改成你自己的
//vless://d342d11e-d424-4583-b36e-524ab1f0afa4@cf.525355.xyz:2083?encryption=none&security=tls&sni=sss4.sss4.ccwu.cc&insecure=1&allowInsecure=1&type=ws&host=sss4.sss4.ccwu.cc&path=%2F%3Fed%3D2560#5s4
