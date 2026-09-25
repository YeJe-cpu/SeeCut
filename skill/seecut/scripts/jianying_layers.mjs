// 剪映分层素材：把 master.html 拆成"纸底 PNG + 人像分状态视频 + 信息层逐元素透明 PNG + 原声"，外加音效候选事件。
// 用法: node jianying_layers.mjs <build目录> [输出目录=<build>/../jianying/layers]
// 打标契约（见 references/10-剪映分层工程.md）：
//   信息层元素加 data-layer="显示名"（可选 data-layer-cat= evbg|card|cardimg|hl|title|hand，默认 card；决定轨道上下顺序）
//   嵌套的 data-layer 子元素会在截父元素时自动隐藏（各自单独成段）
//   人像：#<person_wrap_id>（外框，含卡化边框/圆角）里放 <img id=person_img_id>；纸底/噪点等背景不打标
// 原理与坑（2-4.1 一线实测）：剪映引擎不收 alpha 视频 → 信息层用透明 PNG + 不透明度关键帧；关键帧要求素材从头开始 → 人像按状态切成独立视频。
import fs from 'fs'; import path from 'path'; import { execFileSync } from 'child_process';
import { loadProject, chromium, chromePath, watchdog } from './_common.mjs';
const [, , buildDir, outArg] = process.argv;
if (!buildDir) { console.error('用法: node jianying_layers.mjs <build目录> [输出目录]'); process.exit(2); }
const P = loadProject(buildDir);
const OUT = path.resolve(outArg || path.join(P.B, '../jianying/layers'));
const PNG = path.join(OUT, 'png'); fs.mkdirSync(PNG, { recursive: true });
const FPS = P.fps, N = P.N, W = P.width, H = P.height;
watchdog(Math.max(600000, N * 3000), 'jianying_layers');
const pad = n => String(n).padStart(4, '0');
const PD = path.join(P.B, P.person_dir);
const NP = fs.existsSync(PD) ? fs.readdirSync(PD).filter(f => /^p\d+\.jpg$/.test(f)).length : 0;

const b = await chromium(P.B).launch({ headless: true, executablePath: chromePath() });
const pg = await (await b.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })).newPage();
await pg.goto('file://' + path.join(P.B, P.html), { waitUntil: 'load', timeout: 30000 });
await pg.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
await new Promise(r => setTimeout(r, 400));
const setT = async (i) => pg.evaluate(async ({ t, tl, pid, src }) => {
  window.__timelines[tl].time(t);
  const im = document.getElementById(pid); if (im && src) { im.src = src; try { await im.decode(); } catch (e) {} }
}, { t: i / FPS, tl: P.timeline, pid: P.person_img_id, src: NP ? 'file://' + path.join(PD, 'p' + pad(Math.min(i + 1, NP)) + '.jpg') : null });

// 1) 一次 evaluate 扫完全部帧：每个 data-layer 元素 + 人像外框的有效不透明度与 bbox
const scan = await pg.evaluate(({ N, FPS, W, H, tl, pw }) => {
  const T = window.__timelines[tl];
  const els = [...document.querySelectorAll('[data-layer]')];
  const eff = el => { let o = 1, n = el; while (n && n.nodeType === 1) { const cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden') return { op: 0 }; o *= parseFloat(cs.opacity); n = n.parentElement; }
    const r = el.getBoundingClientRect(); const on = r.width > 2 && r.height > 2 && r.bottom > 0 && r.top < H && r.right > 0 && r.left < W;
    return { op: on ? o : 0, x: r.left, y: r.top, w: r.width, h: r.height }; };
  const meta = els.map((el, k) => { if (!el.id) el.id = '__jl' + k;
    return { id: el.id, name: el.getAttribute('data-layer') || el.id, cat: el.getAttribute('data-layer-cat') || 'card',
      nest: [...el.querySelectorAll('[data-layer]')].map(c => { if (!c.id) c.id = '__jl' + els.indexOf(c); return '#' + c.id; }) }; });
  const res = els.map(() => []), person = [];
  const pwel = document.getElementById(pw);
  for (let i = 0; i < N; i++) { T.time(i / FPS); els.forEach((el, k) => res[k].push(eff(el))); person.push(pwel ? eff(pwel) : { op: 0 }); }
  return { meta, res, person };
}, { N, FPS, W, H, tl: P.timeline, pw: P.person_wrap_id });
if (!scan.meta.length) { console.error('master.html 里没有 data-layer 标记的元素（见 references/10 打标契约）'); process.exit(2); }

// 2) 信息层：可见 run → 按"位置移动"切状态（弹入缩放回弹不算新状态；第 0 帧初始化闪现丢弃）
const same = (a, c) => Math.hypot((a.x + a.w / 2) - (c.x + c.w / 2), (a.y + a.h / 2) - (c.y + c.h / 2)) < 20 && Math.abs(a.w / c.w - 1) < 0.08;
const ctr = q => [q.x + q.w / 2, q.y + q.h / 2];
const segs = [];
scan.meta.forEach((m, k) => {
  const f = scan.res[k]; let i = 0;
  while (i < N) {
    if (f[i].op <= 0.02) { i++; continue; }
    let j = i; while (j + 1 < N && f[j + 1].op > 0.02) j++;
    if (j - i < 2 && i === 0) { i = j + 1; continue; }
    const groups = []; let s = i;
    while (s <= j) { if (f[s].op < 0.98) { s++; continue; }
      let e = s; while (e + 1 <= j && f[e + 1].op >= 0.98 && same(f[e + 1], f[s])) e++;
      if (e - s + 1 >= 3) groups.push([s, e]); s = e + 1; }
    if (!groups.length) groups.push([Math.floor((i + j) / 2), Math.floor((i + j) / 2)]);
    for (let g = groups.length - 1; g > 0; g--) { const [a1, b1] = ctr(f[groups[g - 1][1]]), [a2, b2] = ctr(f[groups[g][0]]);
      if (Math.hypot(a1 - a2, b1 - b2) < 20) { groups[g - 1][1] = groups[g][1]; groups.splice(g, 1); } }
    groups.forEach(([gs, ge], g) => segs.push({ name: groups.length > 1 ? `${m.name}_态${g + 1}` : m.name, id: m.id, cat: m.cat, nest: m.nest,
      start: g === 0 ? i : groups[g - 1][1] + 1, end: g === groups.length - 1 ? j : ge, cap: Math.max(gs, ge - 1),
      fade_in: g === 0, fade_out: g === groups.length - 1 }));
    i = j + 1;
  }
});

// 3) 人像：外框 bbox 稳定 ≥0.3s 的段 = 状态；状态之间 = 过渡（剪映里用 x/y/scale 关键帧做）
const pf = scan.person, states = []; { let s = 0;
  while (s < N) { if (pf[s].op < 0.5) { s++; continue; }
    let e = s; while (e + 1 < N && pf[e + 1].op >= 0.5 && Math.abs(pf[e + 1].x - pf[s].x) < 0.5 && Math.abs(pf[e + 1].y - pf[s].y) < 0.5 && Math.abs(pf[e + 1].w - pf[s].w) < 0.5 && Math.abs(pf[e + 1].h - pf[s].h) < 0.5) e++;
    if (e - s + 1 >= Math.round(0.3 * FPS)) states.push({ s, e, box: [pf[s].x, pf[s].y, pf[s].w, pf[s].h].map(Math.round) });
    s = e + 1; } }
// 每个状态的时间段 = 从"进入它的过渡开始"到"离开它的过渡开始"
// 人像中途隐藏（opacity≈0）的时段不能算过渡（Round2-4.2 实测：隐藏段被记成 137 帧过渡，草稿里人像一直可见）
const vis = i => pf[i].op >= 0.5;
states.forEach((st, k) => {
  st.name = `人像_状态${k + 1}`; st.fade_in = false; st.fade_out = false;
  let from = k === 0 ? 0 : states[k - 1].e + 1;
  let h = -1; for (let i = from; i < st.s; i++) if (!vis(i)) h = i;     // 进入本状态前最后一个隐藏帧
  if (h >= 0) { from = h + 1; st.fade_in = true; }
  if (k === 0) { let f = st.s; while (f > 0 && vis(f - 1)) f--; if (f > 0) st.fade_in = true; from = f; }
  st.from = from; st.anim_frames = k === 0 || st.fade_in ? Math.max(0, st.s - from) : st.s - from;
  let to = k === states.length - 1 ? N - 1 : states[k].e;
  const nxt = k === states.length - 1 ? N : states[k + 1].s;
  let firstHide = -1; for (let i = st.e + 1; i < nxt; i++) if (!vis(i)) { firstHide = i; break; }
  if (firstHide >= 0) { to = firstHide - 1; st.fade_out = true; }
  else if (k === states.length - 1) to = N - 1;
  st.to = to;
});

// 4) 截图：背景 PNG、信息层透明 PNG、人像分状态视频
await pg.addStyleTag({ content: `#${P.person_wrap_id}{visibility:hidden !important;} [data-layer]{visibility:hidden !important;}` });
await setT(0); const paper = path.join(OUT, '纸底.png'); await pg.screenshot({ path: paper });
await pg.addStyleTag({ content: 'html,body{background:transparent !important;}' });
for (const s of segs) {
  s.file = path.join(PNG, `${String(s.start).padStart(4, '0')}_${s.name}.png`);
  await setT(s.cap);
  await pg.evaluate(({ id, nest }) => {
    let st = document.getElementById('__cap'); if (!st) { st = document.createElement('style'); st.id = '__cap'; document.head.appendChild(st); }
    st.textContent = `body *{visibility:hidden !important;} #${id}, #${id} *{visibility:visible !important;} ` + nest.map(n => `${n}, ${n} *{visibility:hidden !important;}`).join(' ');
  }, { id: s.id, nest: s.nest });
  await pg.screenshot({ path: s.file, omitBackground: true });
}
await pg.evaluate(() => { const st = document.getElementById('__cap'); if (st) st.remove(); });
// 人像：只显示外框子树，外框强制停在该状态的稳态几何，逐帧截取该区域（圆角外露出纸底色，和底层纸底同色）
await pg.addStyleTag({ content: `body *{visibility:hidden !important;} #${P.person_wrap_id}, #${P.person_wrap_id} *{visibility:visible !important;}` });
for (const st of states) {
  const dir = path.join(OUT, 'tmp_' + st.name); fs.mkdirSync(dir, { recursive: true });
  const [x, y, w, h] = st.box;
  for (let i = st.from; i <= st.to; i++) {
    await setT(i);
    await pg.evaluate(({ pw, x, y, w, h }) => { const el = document.getElementById(pw);
      Object.assign(el.style, { left: x + 'px', top: y + 'px', width: w + 'px', height: h + 'px', transform: 'none', opacity: 1 }); }, { pw: P.person_wrap_id, x, y, w, h });
    await pg.screenshot({ path: path.join(dir, `f${pad(i - st.from)}.png`), clip: { x, y, width: w + (w % 2), height: h + (h % 2) } });
  }
  st.file = path.join(OUT, st.name + '.mp4');
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-framerate', String(FPS), '-i', path.join(dir, 'f%04d.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', st.file]);
  fs.rmSync(dir, { recursive: true, force: true });
  console.log(`  人像 ${st.name} ${(st.from / FPS).toFixed(2)}-${((st.to + 1) / FPS).toFixed(2)}s box=${st.box} 过渡 ${st.anim_frames} 帧`);
}
// 5) 原声：从源片抽（project.json 的 source 字段；没有就从最终成片抽）
const src = P.source || P.final_video;
let voice = null;
if (src) { voice = path.join(OUT, '原声.m4a'); execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', path.resolve(P.B, src), '-vn', '-c:a', 'aac', '-b:a', '192k', voice]); }
// 6) 音效候选事件：信息层出现/换状态/换图 + 人像过渡
const events = [];
segs.forEach(s => events.push({ t: +(s.start / FPS).toFixed(3), kind: s.fade_in ? '出现' : '换状态', cat: s.cat, name: s.name }));
states.slice(1).forEach(st => events.push({ t: +(st.from / FPS).toFixed(3), kind: '人像过渡', cat: 'person', name: st.name }));
events.sort((a, c) => a.t - c.t);
fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify({ fps: FPS, frames: N, width: W, height: H, paper, voice, segs, person_states: states, events }, null, 1));
console.log(`信息层 ${scan.meta.length} 个元素 → ${segs.length} 段 PNG；人像 ${states.length} 个状态；音效候选事件 ${events.length} 个 → ${path.join(OUT, 'manifest.json')}`);
await b.close(); process.exit(0);
