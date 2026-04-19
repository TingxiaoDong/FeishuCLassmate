#!/usr/bin/env node
/**
 * Dashboard server — reads openclaw + classmate state from ~/.openclaw/,
 * fetches a tenant_access_token, serves index.html with injected config.
 *
 * Usage:
 *   node dashboard/server.mjs --port 9100
 */

import { createServer } from 'node:http';
import { readFileSync, existsSync } from 'node:fs';
import { join, extname } from 'node:path';
import { homedir } from 'node:os';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const PORT = Number(process.argv.includes('--port') ? process.argv[process.argv.indexOf('--port') + 1] : 9100);

const OPENCLAW_CFG = join(homedir(), '.openclaw', 'openclaw.json');
const CLASSMATE_STATE = join(homedir(), '.openclaw', 'state', 'feishu-classmate.json');

async function getTenantToken(appId, appSecret) {
  const res = await fetch('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ app_id: appId, app_secret: appSecret }),
  });
  const d = await res.json();
  if (d.code !== 0) throw new Error(d.msg || 'tenant token failed');
  return d.tenant_access_token;
}

function loadConfig() {
  if (!existsSync(OPENCLAW_CFG)) throw new Error(`missing ${OPENCLAW_CFG}`);
  const cfg = JSON.parse(readFileSync(OPENCLAW_CFG, 'utf-8'));
  const fs = cfg.channels?.feishu;
  if (!fs?.appId || !fs?.appSecret) throw new Error('channels.feishu.appId / appSecret missing');

  if (!existsSync(CLASSMATE_STATE)) throw new Error(`missing ${CLASSMATE_STATE} — run setup-bitable first`);
  const state = JSON.parse(readFileSync(CLASSMATE_STATE, 'utf-8'));
  return { appId: fs.appId, appSecret: fs.appSecret, appToken: state.appToken, tableIds: state.tableIds };
}

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg' };

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host}`);

    if (url.pathname === '/' || url.pathname === '/index.html') {
      let { appId, appSecret, appToken, tableIds } = loadConfig();
      const token = await getTenantToken(appId, appSecret);
      const html = readFileSync(join(__dirname, 'index.html'), 'utf-8').replace(
        '</head>',
        `<script>window.__DASHBOARD_CONFIG__ = ${JSON.stringify({ appToken, tableIds, token })};</script></head>`,
      );
      res.writeHead(200, { 'Content-Type': MIME['.html'] });
      return res.end(html);
    }

    const filePath = join(__dirname, url.pathname.replace(/^\/+/, ''));
    if (!existsSync(filePath)) { res.writeHead(404); return res.end('not found'); }
    res.writeHead(200, { 'Content-Type': MIME[extname(filePath)] || 'application/octet-stream' });
    return res.end(readFileSync(filePath));
  } catch (err) {
    res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end(`server error: ${err.message ?? err}`);
  }
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[dashboard] http://127.0.0.1:${PORT}/`);
  console.log(`[dashboard] mock:  http://127.0.0.1:${PORT}/?mock=1`);
});
