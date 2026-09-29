// server.js - 本地转发服务，解决浏览器跨域抓取
// 启动: node server.js
// 页面请求: http://127.0.0.1:8787/fetch?url=<目标地址(编码)>
const http = require('http');

const PORT = 8787;
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36';

function originOf(url) {
    try { return new URL(url).origin + '/'; } catch (e) { return ''; }
}

const server = http.createServer(async (req, res) => {
    // 统一加 CORS 头，本地页面(file:// 或 127.0.0.1)才能跨源调用
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', '*');
    if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

    const u = new URL(req.url, `http://127.0.0.1:${PORT}`);

    // 核心接口: 转发抓取任意 http(s) 页面
    if (u.pathname === '/fetch') {
        const target = u.searchParams.get('url') || '';
        if (!/^https?:\/\//i.test(target)) {
            res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
            res.end(JSON.stringify({ error: 'url 参数必须是 http(s) 地址' }));
            return;
        }
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 20000);
        try {
            const r = await fetch(target, {
                signal: controller.signal,
                headers: {
                    'User-Agent': UA,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Referer': originOf(target)
                }
            });
            if (!r.ok) throw new Error(`目标站点返回 HTTP ${r.status}`);
            const text = await r.text();
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(text);
        } catch (e) {
            res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
            res.end(JSON.stringify({ error: '抓取失败: ' + e.message }));
        } finally {
            clearTimeout(timer);
        }
        return;
    }

    // 二进制转发: 用于下载 TS 分片、AES 密钥等
    if (u.pathname === '/fetchbin') {
        const target = u.searchParams.get('url') || '';
        if (!/^https?:\/\//i.test(target)) {
            res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
            res.end(JSON.stringify({ error: 'url 参数必须是 http(s) 地址' }));
            return;
        }
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 30000);
        try {
            const r = await fetch(target, {
                signal: controller.signal,
                headers: {
                    'User-Agent': UA,
                    'Accept': '*/*',
                    'Referer': originOf(target)
                }
            });
            if (!r.ok) throw new Error(`目标站点返回 HTTP ${r.status}`);
            const buf = Buffer.from(await r.arrayBuffer());
            const ct = r.headers.get('content-type') || 'application/octet-stream';
            // 加 HTTP 缓存：封面图/TS 分片/AES 密钥 24 小时内浏览器自动复用，无需重复转发
            res.writeHead(200, {
                'Content-Type': ct,
                'Content-Length': buf.length,
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=86400'
            });
            res.end(buf);
        } catch (e) {
            res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
            res.end(JSON.stringify({ error: '抓取失败: ' + e.message }));
        } finally {
            clearTimeout(timer);
        }
        return;
    }

    // 服务端轮询可用节点: /findalive?prefix=hsck&suffix=.25img.com&start=1&end=123
    // 在服务端逐个检测（无浏览器跨域限制），返回第一个可用的完整域名
    if (u.pathname === '/findalive') {
        const prefix = u.searchParams.get('prefix') || 'hsck';
        const suffix = u.searchParams.get('suffix') || '.25img.com';
        const start = parseInt(u.searchParams.get('start')) || 1;
        const end = parseInt(u.searchParams.get('end')) || 123;
        let found = null;
        for (let i = start; i <= end; i++) {
            const host = `${prefix}${i}${suffix}`;
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), 3000);
            try {
                const r = await fetch(`https://${host}/`, {
                    signal: controller.signal,
                    headers: { 'User-Agent': UA, 'Accept': 'text/html,*/*' }
                });
                if (r.ok) { found = host; break; }
            } catch (e) {
                // 节点不可用，继续下一个
            } finally {
                clearTimeout(timer);
            }
        }
        if (found) {
            res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
            res.end(JSON.stringify({ host: found }));
        } else {
            res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
            res.end(JSON.stringify({ error: `未找到可用节点 (${prefix}${start}${suffix} ~ ${prefix}${end}${suffix})` }));
        }
        return;
    }

    // 健康检查
    if (u.pathname === '/' || u.pathname === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ ok: true, service: 'm3u8 本地转发服务', port: PORT }));
        return;
    }

    res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ error: 'not found' }));
});

server.listen(PORT, '127.0.0.1', () => {
    console.log(`✅ 本地转发服务已启动: http://127.0.0.1:${PORT}`);
    console.log(`   用法: http://127.0.0.1:${PORT}/fetch?url=${encodeURIComponent('https://目标站点/')}`);
});
