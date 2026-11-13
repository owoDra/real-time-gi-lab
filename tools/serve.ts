// Local server for the browser runs. Binds to 127.0.0.1 only.
// GET  /                     -> web/index.html
// GET  /build/..., /assets/...  -> files under the repository (no directory listing)
// POST /result/<name>        -> out/s0/web/<name>
// POST /image/<name>?w=&h=   -> out/s0/web/<name>.png (body: tightly packed RGBA8)
import { createServer } from 'node:http';
import { createReadStream, existsSync, mkdirSync, statSync, writeFileSync } from 'node:fs';
import { extname, join, normalize, resolve } from 'node:path';
import { PNG } from 'pngjs';

const root = resolve(import.meta.dirname, '../..');
const port = Number(process.env.PORT ?? 8765);
const outDir = resolve(process.env.OUT ?? join(root, 'out/s0/web'));
const TYPES: Record<string, string> = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.gltf': 'model/gltf+json',
  '.bin': 'application/octet-stream', '.png': 'image/png', '.jpg': 'image/jpeg' };
const SAFE_NAME = /^[\w.-]+$/;

createServer((req, res) => {
  const url = new URL(req.url ?? '/', 'http://localhost');
  if (req.method === 'POST') {
    const chunks: Buffer[] = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => {
      const body = Buffer.concat(chunks);
      const [, kind, name] = url.pathname.split('/');
      if (!name || !SAFE_NAME.test(name)) { res.writeHead(400).end(); return; }
      mkdirSync(outDir, { recursive: true });
      if (kind === 'result') writeFileSync(join(outDir, name), body);
      else if (kind === 'image') {
        const w = Number(url.searchParams.get('w')), h = Number(url.searchParams.get('h'));
        const png = new PNG({ width: w, height: h }); png.data = body;
        writeFileSync(join(outDir, `${name}.png`), PNG.sync.write(png));
      } else { res.writeHead(404).end(); return; }
      console.log(`saved ${kind}/${name} (${body.length} bytes)`);
      res.writeHead(200).end();
    });
    return;
  }
  const rel = url.pathname === '/' ? 'web/index.html' : normalize(decodeURIComponent(url.pathname)).replace(/^\/+/, '');
  if (!/^(web|build\/web|assets)\//.test(rel) || rel.includes('..')) { res.writeHead(404).end(); return; }
  const file = join(root, rel);
  if (!existsSync(file) || !statSync(file).isFile()) { res.writeHead(404).end(); return; }
  res.writeHead(200, { 'content-type': TYPES[extname(file)] ?? 'application/octet-stream', 'cache-control': 'no-store' });
  createReadStream(file).pipe(res);
}).listen(port, '127.0.0.1', () => console.log(`serving http://127.0.0.1:${port}/ (results -> ${outDir})`));
