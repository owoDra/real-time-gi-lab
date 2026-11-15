// Browser runs of src/web/rc.ts (or, with --page gl2, the WebGL2 tier src/web/gl2.ts): serves the page, the bundle and the assets on 127.0.0.1, opens the page in a browser,
// prints the page's log lines and stores what it posts (PNGs, summaries, irradiance dumps) in --out.
// Usage: node build/native/browser.mjs [--scene S] [--configs a,b] [--frames N] [--warmup N] [--exposure X] [--no-sky]
//   [--static-only] [--seed-fixed] [--pose-frame F] [--vox JSON] [--params JSON] [--dump-irr] [--bvh] [--dyn-stages] [--vox-bench]
//   [--response FROM,TO] [--seq EVERY,COUNT] [--out DIR]
//   [--page rc|gl2] (web/<page>.html; gl2 takes --scene, --configs (one gl2-... config), --frames, --warmup, --exposure, --no-sky)
//   [--browser CMD] (default brave) [--browser-flags "..."] (added to the launch flags) [--no-launch] (print the URL and wait: open it in a browser yourself) [--port P] [--timeout S]
// The flags mirror src/native/rc.ts. The browser is started with a fresh profile and closed when the page is done.
import { spawn } from 'node:child_process';
import { createReadStream, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { extname, join, normalize, resolve } from 'node:path';
import { PNG } from 'pngjs';

const ROOT = resolve(import.meta.dirname, '../..');
const args = process.argv.slice(2);
const arg = (name: string, dflt: string) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const flag = (name: string) => args.includes(name);
const scene = arg('--scene', 'sponza');
const page = arg('--page', 'rc');
if (!['rc', 'gl2'].includes(page)) throw new Error(`unknown page ${page}`);
const outDir = resolve(arg('--out', join(ROOT, 'box/out/rc/browser', scene)));
const q = new URLSearchParams({ scene, configs: arg('--configs', 'world-48-voxel-rc2-vrel'), frames: arg('--frames', '240'),
  warmup: arg('--warmup', '60'), exposure: arg('--exposure', '1.0') });
for (const [f, k] of [['--no-sky', 'nosky'], ['--static-only', 'static'], ['--seed-fixed', 'seedfixed'], ['--dump-irr', 'dumpirr'], ['--bvh', 'bvh'], ['--dyn-stages', 'dynstages'], ['--vox-bench', 'voxbench']]) if (flag(f)) q.set(k, '');
for (const [f, k] of [['--pose-frame', 'pose'], ['--vox', 'vox'], ['--params', 'params'], ['--response', 'response'], ['--seq', 'seq']]) if (flag(f)) q.set(k, arg(f, ''));

const TYPES: Record<string, string> = { '.html': 'text/html', '.js': 'text/javascript', '.gltf': 'model/gltf+json', '.bin': 'application/octet-stream',
  '.png': 'image/png', '.jpg': 'image/jpeg' };
const SAFE = /^[\w.-]+$/;
mkdirSync(outDir, { recursive: true });
let finish: (status: string) => void;
const done = new Promise<string>((r) => { finish = r; });

const server = createServer((req, res) => {
  const url = new URL(req.url ?? '/', 'http://localhost');
  if (req.method === 'POST') {
    const chunks: Buffer[] = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => {
      const body = Buffer.concat(chunks), [, kind, name] = url.pathname.split('/');
      if (kind === 'log') console.log(body.toString());
      else if (kind === 'done') finish(body.toString());
      else if (kind === 'out' && name && SAFE.test(name)) {
        const w = Number(url.searchParams.get('w')), h = Number(url.searchParams.get('h'));
        writeFileSync(join(outDir, name), w ? PNG.sync.write(Object.assign(new PNG({ width: w, height: h }), { data: body })) : body);
      } else { res.writeHead(400).end(); return; }
      res.writeHead(200).end();
    });
    return;
  }
  const rel = url.pathname === '/' ? `web/${page}.html` : normalize(decodeURIComponent(url.pathname)).replace(/^\/+/, '');
  if (!/^(web|build\/web|assets)\//.test(rel) || rel.includes('..')) { res.writeHead(404).end(); return; }
  const file = join(ROOT, rel);
  if (!existsSync(file) || !statSync(file).isFile()) { res.writeHead(404).end(); return; }
  res.writeHead(200, { 'content-type': TYPES[extname(file)] ?? 'application/octet-stream', 'cache-control': 'no-store' });
  createReadStream(file).pipe(res);
});
await new Promise<void>((r) => server.listen(Number(arg('--port', '0')), '127.0.0.1', r));
const port = (server.address() as { port: number }).port;
const pageUrl = `http://127.0.0.1:${port}/?${q}`;
console.log(`page ${pageUrl}; results -> ${outDir}`);

let browser: ReturnType<typeof spawn> | null = null;
let profile = '';
if (!flag('--no-launch')) {
  profile = mkdtempSync(join(tmpdir(), 'gi-lab-browser-'));
  // --enable-unsafe-webgpu: WebGPU is off by default on Linux (Brave 149: no adapter without it); --enable-webgpu-developer-features:
  // timestamps not rounded (Chromium builds may round them; Brave 149 did not, phase 30); --ignore-gpu-blocklist: the driver
  // may be on the blocklist. Machine-specific flags (for example the window system) come from --browser-flags.
  const launch = ['--enable-unsafe-webgpu', '--enable-webgpu-developer-features', '--ignore-gpu-blocklist',
    '--no-first-run', '--no-default-browser-check', `--user-data-dir=${profile}`, '--window-size=640,480',
    ...arg('--browser-flags', '').split(' ').filter(Boolean), pageUrl];
  // Own process group: the browser command may be a wrapper script that leaves the browser running when it alone is killed.
  browser = spawn(arg('--browser', 'brave'), launch, { stdio: 'ignore', detached: true });
}

/** Processes whose command line names the run's profile directory (the browser and all its helpers). */
function profileProcesses() {
  const pids: number[] = [];
  for (const d of readdirSync('/proc')) {
    if (!/^\d+$/.test(d) || Number(d) === process.pid) continue;
    try { if (readFileSync(`/proc/${d}/cmdline`, 'utf8').includes(profile)) pids.push(Number(d)); } catch { /* exited */ }
  }
  return pids;
}
/** Closes the browser: the process group, then anything still using the profile; waits until none is left. */
async function closeBrowser() {
  if (!browser) return;
  try { process.kill(-browser.pid!, 'SIGTERM'); } catch { /* already gone */ }
  for (let i = 0; i < 50; i++) {
    const left = existsSync('/proc') ? profileProcesses() : [];
    if (!left.length) break;
    for (const pid of left) try { process.kill(pid, i < 20 ? 'SIGTERM' : 'SIGKILL'); } catch { /* exited */ }
    await new Promise((r) => setTimeout(r, 200));
  }
  const left = existsSync('/proc') ? profileProcesses().length : 0;
  console.log(left ? `WARNING: ${left} browser processes still running (profile ${profile})` : 'browser closed');
  rmSync(profile, { recursive: true, force: true });
}
process.on('SIGINT', () => { void closeBrowser().then(() => process.exit(130)); });
const timeout = setTimeout(() => finish('timeout'), Number(arg('--timeout', '1800')) * 1000);
const status = await done;
clearTimeout(timeout);
await closeBrowser();
server.close();
console.log(`browser run ${status}`);
process.exit(status === 'ok' ? 0 : 1);
