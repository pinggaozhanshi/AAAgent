const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');

const PORT = Number(process.env.PORT || 5173);
const BACKEND_PORT = 8000;
const UI_DIR = path.join(__dirname, 'src', 'ui');
const mimeTypes = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml' };
let backendProcess = null;

function sendJson(res, status, payload) { res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' }); res.end(JSON.stringify(payload)); }
function delay(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function backendHealthy() {
  return new Promise((resolve) => {
    const request = http.get({ hostname: '127.0.0.1', port: BACKEND_PORT, path: '/health', timeout: 700 }, (response) => { response.resume(); resolve(response.statusCode === 200); });
    request.on('timeout', () => { request.destroy(); resolve(false); });
    request.on('error', () => resolve(false));
  });
}
async function ensureBackend() {
  if (await backendHealthy()) return true;
  if (!backendProcess || backendProcess.exitCode !== null) {
    backendProcess = spawn('python', ['-m', 'uvicorn', 'sse_server:app', '--app-dir', 'backend', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)], { cwd: __dirname, stdio: 'inherit', windowsHide: true });
    backendProcess.on('exit', (code) => { console.warn(`AAAgent backend exited with code ${code}.`); backendProcess = null; });
    backendProcess.on('error', (error) => { console.error(`Unable to start AAAgent backend: ${error.message}`); });
  }
  for (let attempt = 0; attempt < 20; attempt += 1) { if (await backendHealthy()) return true; await delay(250); }
  return false;
}
function stopBackend() { if (backendProcess && backendProcess.exitCode === null) backendProcess.kill(); }
process.once('SIGINT', stopBackend); process.once('SIGTERM', stopBackend); process.once('exit', stopBackend);

function proxyApi(req, res) {
  const backendPath = req.url === '/api/health' ? '/health' : req.url;
  const upstream = http.request({ hostname: '127.0.0.1', port: BACKEND_PORT, path: backendPath, method: req.method, headers: { ...req.headers, host: `127.0.0.1:${BACKEND_PORT}` } }, (upstreamResponse) => {
    res.writeHead(upstreamResponse.statusCode || 502, upstreamResponse.headers);
    upstreamResponse.pipe(res);
  });
  upstream.on('error', () => sendJson(res, 503, { error: 'AAAgent professional service is unavailable. Restart AAAgent-Run.bat.' }));
  req.pipe(upstream);
}
function resolveStaticPath(urlPath) {
  const requested = decodeURIComponent(urlPath.split('?')[0]) === '/' ? '/index.html' : decodeURIComponent(urlPath.split('?')[0]);
  const filePath = path.normalize(path.join(UI_DIR, requested));
  return filePath.startsWith(UI_DIR) ? filePath : null;
}
const server = http.createServer((req, res) => {
  if ((req.url || '').startsWith('/api/')) { proxyApi(req, res); return; }
  if (req.method !== 'GET') { sendJson(res, 405, { error: 'Method not allowed' }); return; }
  const filePath = resolveStaticPath(req.url || '/');
  if (!filePath) { sendJson(res, 403, { error: 'Forbidden' }); return; }
  fs.readFile(filePath, (error, content) => {
    if (error) { sendJson(res, error.code === 'ENOENT' ? 404 : 500, { error: error.code === 'ENOENT' ? 'Not found' : 'Failed to read file' }); return; }
    res.writeHead(200, { 'content-type': mimeTypes[path.extname(filePath)] || 'application/octet-stream' }); res.end(content);
  });
});

ensureBackend().then((ready) => {
  server.listen(PORT, () => console.log(`AAAgent is running at http://localhost:${PORT}${ready ? '' : ' (backend is still starting)'}`));
});