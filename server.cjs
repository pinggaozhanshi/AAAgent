const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const PORT = Number(process.env.PORT || 5173);
const UI_DIR = path.join(__dirname, 'src', 'ui');

const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml; charset=utf-8',
};

function sendJson(res, status, payload) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(payload));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => {
      body += chunk;
      if (body.length > 2_000_000) {
        req.destroy();
        reject(new Error('Request body is too large'));
      }
    });
    req.on('end', () => resolve(body));
    req.on('error', reject);
  });
}

function resolveStaticPath(urlPath) {
  const cleanPath = decodeURIComponent(urlPath.split('?')[0]);
  const requested = cleanPath === '/' ? '/index.html' : cleanPath;
  const filePath = path.normalize(path.join(UI_DIR, requested));

  if (!filePath.startsWith(UI_DIR)) {
    return null;
  }

  return filePath;
}

async function proxyChat(req, res) {
  try {
    const body = JSON.parse(await readBody(req));
    const {
      provider,
      baseUrl,
      apiKey,
      model,
      messages,
      temperature = 0.7,
      maxTokens = 1024,
    } = body;

    if (!baseUrl || !model || !Array.isArray(messages)) {
      sendJson(res, 400, { error: 'baseUrl, model and messages are required.' });
      return;
    }

    if (provider !== 'ollama' && !apiKey) {
      sendJson(res, 400, { error: 'API Key is required for this provider.' });
      return;
    }

    const endpoint = `${String(baseUrl).replace(/\/$/, '')}/chat/completions`;
    const headers = { 'content-type': 'application/json' };

    if (apiKey) {
      headers.authorization = `Bearer ${apiKey}`;
    }

    const upstream = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        model,
        messages,
        temperature,
        max_tokens: maxTokens,
        stream: false,
      }),
    });

    const text = await upstream.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }

    if (!upstream.ok) {
      sendJson(res, upstream.status, {
        error: data?.error?.message || data?.message || upstream.statusText,
        details: data,
      });
      return;
    }

    const content = data?.choices?.[0]?.message?.content || '';
    sendJson(res, 200, {
      content,
      usage: data?.usage || null,
      raw: data,
    });
  } catch (error) {
    sendJson(res, 500, { error: error instanceof Error ? error.message : 'Unknown error' });
  }
}

const server = http.createServer(async (req, res) => {
  if (req.method === 'POST' && req.url === '/api/chat') {
    await proxyChat(req, res);
    return;
  }

  if (req.method !== 'GET') {
    sendJson(res, 405, { error: 'Method not allowed' });
    return;
  }

  const filePath = resolveStaticPath(req.url || '/');
  if (!filePath) {
    sendJson(res, 403, { error: 'Forbidden' });
    return;
  }

  fs.readFile(filePath, (error, content) => {
    if (error) {
      sendJson(res, error.code === 'ENOENT' ? 404 : 500, {
        error: error.code === 'ENOENT' ? 'Not found' : 'Failed to read file',
      });
      return;
    }

    const ext = path.extname(filePath);
    res.writeHead(200, { 'content-type': mimeTypes[ext] || 'application/octet-stream' });
    res.end(content);
  });
});

server.listen(PORT, () => {
  console.log(`AAAgent is running at http://localhost:${PORT}`);
});
