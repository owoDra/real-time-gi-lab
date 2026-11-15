// Config names of the runners (native src/native/rc.ts and the browser src/web/rc.ts). The name grammar and its tokens
// are documented at the top of src/native/rc.ts.
import { DEFAULT_DDGI, type DdgiParams } from '../core/ddgi.ts';
import { DEFAULT_GL2, type Gl2Params } from '../core/gl2.ts';
import { DEFAULT_PARAMS, type Method, type RcParams } from '../core/rc.ts';

// Phase 33, the WebGL2 tier: gl2-<tile px>-<dirs>[-s<steps>][-l<length m>][-t<thick m>][-tr<thick rel>][-f<filter radius>][-r<RSM res, 0 off>][-rn<RSM samples per ring>][-h<history weight of the new frame>|-nh]
function parseGl2(name: string, overrides: Partial<RcParams>): RcParams {
  const [, tile, dirs, ...tokens] = name.split('-');
  const g: Gl2Params = { ...DEFAULT_GL2, tile: Number(tile), dirs: Number(dirs) };
  for (const t of tokens) {
    if (/^s\d+$/.test(t)) g.steps = Number(t.slice(1));
    else if (/^l[\d.]+$/.test(t)) g.length = Number(t.slice(1));
    else if (/^tr[\d.]+$/.test(t)) g.thickRel = Number(t.slice(2));
    else if (/^t[\d.]+$/.test(t)) g.thick = Number(t.slice(1));
    else if (/^f\d+$/.test(t)) g.filter = Number(t.slice(1));
    else if (/^rn\d+$/.test(t)) g.rsmRing = Number(t.slice(2));
    else if (/^r\d+$/.test(t)) g.rsm = Number(t.slice(1));
    else if (/^h[\d.]+$/.test(t)) g.history = Number(t.slice(1));
    else if (t === 'nh') g.history = 0;
    else throw new Error(`unknown gl2 token ${t} in ${name}`);
  }
  return { ...DEFAULT_PARAMS, ...overrides, method: 'screen', world: 'none', gl2: g };
}

// DDGI comparator: ddgi-<spacing cm>-<rays>[-h<hysteresis>][-noadapt][-u<div>][-norel|-rg][-nocls][-sb<segBase m>][-g<gamma>][-vb<view bias>][-obj]
function parseDdgi(name: string, overrides: Partial<RcParams>): RcParams {
  const [, sp, rays, ...tokens] = name.split('-');
  const d: DdgiParams = { ...DEFAULT_DDGI, spacing: Number(sp) / 100, rays: Number(rays) };
  let objects = false;
  for (const t of tokens) {
    if (/^h[\d.]+$/.test(t)) d.hysteresis = Number(t.slice(1));
    else if (t === 'noadapt') d.adaptive = false;
    else if (/^u\d+$/.test(t)) d.updateDiv = Number(t.slice(1));
    else if (t === 'norel') d.relocate = 0;
    else if (t === 'rg') d.relocate = 2;
    else if (t === 'nocls') d.classify = false;
    else if (/^sb[\d.]+$/.test(t)) d.segBase = Number(t.slice(2));
    else if (/^g[\d.]+$/.test(t)) d.gamma = Number(t.slice(1));
    else if (/^vb[\d.]+$/.test(t)) d.viewBias = Number(t.slice(2));
    else if (t === 'obj') objects = true;
    else throw new Error(`unknown ddgi token ${t} in ${name}`);
  }
  return { ...DEFAULT_PARAMS, ...overrides, world: 'voxel', depthCascades: 0, ddgi: d, objects };
}

export function parseConfig(name: string, overrides: Partial<RcParams> = {}): RcParams {
  if (name.startsWith('ddgi-')) return parseDdgi(name, overrides);
  if (name.startsWith('gl2-')) return parseGl2(name, overrides);
  const [method, P, ...tokens] = name.split('-');
  const p: RcParams = { ...DEFAULT_PARAMS, ...overrides, method: method as Method, P: Number(P) };
  for (const t of tokens) {
    if (t === 'analytic') p.analytic = true;
    else if (t === 'depth') p.world = 'none';
    else if (t === 'voxel') { p.world = 'voxel'; p.depthCascades = 0; }
    else if (t === 'hybrid') { p.world = 'voxel'; p.depthCascades = 1; }
    else if (t === 'tri') { p.world = 'tri'; p.depthCascades = 0; }
    else if (t === 'trihybrid') { p.world = 'tri'; p.depthCascades = 1; }
    else if (t === 'l2') p.levelMap = 2;
    else if (t === 'norel') p.relocate = 'none';
    else if (t === 'vrel') p.relocate = 'voxel';
    else if (t === 'noemit') p.styleEmit = false;
    else if (t === 'norecv') p.styleRecv = false;
    else if (/^soft[\d.]+$/.test(t)) p.rampSoft = Number(t.slice(4));
    else if (/^rc\d$/.test(t)) p.resCap = Number(t.slice(2));
    else if (/^vs[\d.]+$/.test(t)) p.voxScale = Number(t.slice(2));
    else if (/^vo[\d.]+$/.test(t)) p.voxOffset = Number(t.slice(2));
    else if (/^vk[\d.]+$/.test(t)) p.voxSkip = Number(t.slice(2));
    else if (t === 'obj') p.objects = true;
    else throw new Error(`unknown config token ${t} in ${name}`);
  }
  return p;
}
