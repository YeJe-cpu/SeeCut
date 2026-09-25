// 3A 几何自检（硬门 H1）。整套 seek+读 bbox 在浏览器内一次 evaluate 跑完（禁每帧往返）。
// 用法: node geom-check.mjs <build目录>     退出码 0=全绿 1=有FAIL 2/3=环境错误/超时
// 打标契约(见 references/07): data-check="box"|"bg" · data-anchor=目标id · data-word=关键词 + data-t=该词起始秒
//                         人像外框 #<person_wrap_id>；project.json 里 steady=各信息拍稳态秒, spring=[[选择器,入场秒],...]
import path from 'path';
import { loadProject, chromium, chromePath, watchdog } from './_common.mjs';
const buildDir=process.argv[2]; if(!buildDir){console.error('用法: node geom-check.mjs <build目录>');process.exit(2);}
const P=loadProject(buildDir);
const WD=watchdog(120000,'geom-check');
const C={N:P.N,FPS:P.fps,W:P.width,H:P.height,STEP:2,STEADY:P.steady,TL:P.timeline,PW:P.person_wrap_id,
  OVERLAP_MAX:P.overlap_max??0.15,ANCHOR_DIST:0.40,ANCHOR_COVER:0.60,NOFACE_MAX:P.noface_max??5.0,FULLFRAME:0.45};
const b=await chromium(P.B).launch({headless:true,executablePath:chromePath()});
const pg=await (await b.newContext({viewport:{width:P.width,height:P.height},deviceScaleFactor:1})).newPage();
await pg.goto('file://'+path.join(P.B,P.html),{waitUntil:'load',timeout:30000});
await pg.evaluate(()=>document.fonts&&document.fonts.ready).catch(()=>{});
await new Promise(r=>setTimeout(r,400));
const R=await pg.evaluate((C)=>{
  const tl=(window.__timelines||{})[C.TL]; if(!tl) return {err:'找不到 window.__timelines.'+C.TL};
  const {N,FPS,W,H,STEP,STEADY,OVERLAP_MAX,ANCHOR_DIST,ANCHOR_COVER,NOFACE_MAX,FULLFRAME}=C;
  const eff=el=>{let o=1,n=el;while(n&&n!==document.body){const cs=getComputedStyle(n);
    if(cs.display==='none'||cs.visibility==='hidden')return{vis:false};o*=parseFloat(cs.opacity)||0;n=n.parentElement;}
    const r=el.getBoundingClientRect();
    return{vis:o>0.1&&r.width>2&&r.height>2&&r.bottom>0&&r.top<H&&r.right>0&&r.left<W,x:r.left,y:r.top,w:r.width,h:r.height,cx:r.left+r.width/2,cy:r.top+r.height/2};};
  const inter=(a,c)=>Math.max(0,Math.min(a.x+a.w,c.x+c.w)-Math.max(a.x,c.x))*Math.max(0,Math.min(a.y+a.h,c.y+c.h)-Math.max(a.y,c.y));
  const FAILS=[],WARN=[];
  if(!STEADY.length) WARN.push('[配置] project.json 未给 steady(信息拍稳态秒)，撞位/圈锚/密度未检');
  for(const t of STEADY){tl.time(t);
    const boxes=[...document.querySelectorAll('[data-check="box"]')].map(el=>({id:el.id||el.className,...eff(el)})).filter(e=>e.vis);
    for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i],c=boxes[j];
      const r=inter(a,c)/Math.min(a.w*a.h,c.w*c.h); if(r>OVERLAP_MAX)FAILS.push(`[撞位] t=${t}s "${a.id}"✕"${c.id}" ${(r*100)|0}%`);}
    if(boxes.length<2)WARN.push(`[空拍?] t=${t}s 可见 box 仅 ${boxes.length} 个`);
    const pw=document.getElementById(C.PW);const Pp=pw?eff(pw):{vis:false};
    if(Pp.vis&&(Pp.w*Pp.h)/(W*H)<FULLFRAME)for(const bx of boxes){const r=inter(bx,Pp)/Math.min(bx.w*bx.h,Pp.w*Pp.h);
      if(r>0.12)FAILS.push(`[压人像] t=${t}s "${bx.id}" ${(r*100)|0}%`);}
    // 被人像盖住（z 序遮挡）：不管人像多大都查——Round2-4.2 实测字卡被人像盖 1.5s，bbox 撞位和 agy 都没抓到
    if(Pp.vis){ const pwEl=document.getElementById(C.PW);
      for(const el of document.querySelectorAll('[data-check="box"]')){ const E=eff(el); if(!E.vis) continue;
        const pts=[[.5,.5],[.25,.25],[.75,.25],[.25,.75],[.75,.75]].map(([u,v])=>[E.x+E.w*u,E.y+E.h*v]).filter(([x,y])=>x>=0&&y>=0&&x<W&&y<H);
        const hid=pts.filter(([x,y])=>{const top=document.elementFromPoint(x,y); return top&&pwEl.contains(top)&&!el.contains(top);}).length;
        if(pts.length&&hid>=3) FAILS.push(`[被人像盖住] t=${t}s "${el.id||el.className}" ${hid}/${pts.length} 采样点在人像下面`);}}
    for(const ae of document.querySelectorAll('[data-anchor]')){const te=document.getElementById(ae.getAttribute('data-anchor'));if(!te)continue;
      const A=eff(ae),T=eff(te);if(!A.vis||!T.vis)continue;const dist=Math.hypot(A.cx-T.cx,A.cy-T.cy);
      const cov=Math.max(0,Math.min(A.x+A.w,T.x+T.w)-Math.max(A.x,T.x))/T.w;
      if(dist>T.h*ANCHOR_DIST)FAILS.push(`[圈歪] t=${t}s "${te.id}" 偏 ${dist|0}px`);
      if(cov<ANCHOR_COVER)FAILS.push(`[圈偏] t=${t}s "${te.id}" 覆盖 ${(cov*100)|0}%`);}}
  const words=[...document.querySelectorAll('[data-word]')].map(el=>({l:el.getAttribute('data-word'),t:parseFloat(el.getAttribute('data-t')),el}));
  const first={};let nf=0,nfMax=0;
  for(let i=0;i<N;i+=STEP){tl.time(i/FPS);const pw=document.getElementById(C.PW);const pv=pw?eff(pw).vis:true;
    if(!pv){nf+=STEP;nfMax=Math.max(nfMax,nf);}else nf=0;
    for(const w of words)if(first[w.l]===undefined&&eff(w.el).vis)first[w.l]=i/FPS;}
  const nfs=nfMax/FPS; if(nfs>NOFACE_MAX)FAILS.push(`[无脸] 最长 ${nfs.toFixed(1)}s > ${NOFACE_MAX}s`);
  for(const w of words){const f=first[w.l]; if(isNaN(w.t)){WARN.push(`[timing] "${w.l}" 缺 data-t`);continue;}
    if(f===undefined)WARN.push(`[timing] "${w.l}" 全程未见`); else if(f<w.t-0.05)FAILS.push(`[抢拍] "${w.l}" @${f.toFixed(2)}s 早于词 @${w.t}s`);}
  return{FAILS,WARN,nfs,words:words.map(w=>({l:w.l,t:w.t,f:first[w.l]}))};
},C);
if(R.err){console.error(R.err);process.exit(2);}
const spring=await pg.evaluate(({items,TL})=>{const tl=window.__timelines[TL];
  const sc=el=>{try{const m=new DOMMatrixReadOnly(getComputedStyle(el).transform);return Math.hypot(m.a,m.b);}catch(e){return 1;}};
  return items.map(([sel,t])=>{const el=document.querySelector(sel);if(!el)return{sel,miss:true};let pk=0;
    for(let x=t;x<=t+0.6;x+=0.02){tl.time(x);pk=Math.max(pk,sc(el));}return{sel,peak:+pk.toFixed(3),ok:pk>1.02};});},{items:P.spring,TL:P.timeline});
spring.filter(s=>!s.miss&&!s.ok).forEach(s=>R.FAILS.push(`[无弹簧] ${s.sel} 峰值 ${s.peak}`));
if(!P.spring.length) R.WARN.push('[配置] project.json 未给 spring 采样点，弹簧 overshoot 未检');
console.log(`=== 3A 几何自检 · ${P.B} ===`);
console.log('弹簧: '+(spring.map(s=>`${s.sel}=${s.miss?'缺':s.peak}${s.ok?'✓':'✗'}`).join(' ')||'—'));
console.log(`无脸最长: ${R.nfs.toFixed(2)}s`);
R.words.forEach(w=>console.log(`  ${w.l}: 首现 @${w.f?.toFixed(2)??'??'} / 词 @${w.t} ${w.f!==undefined&&w.f>=w.t-0.05?'✓':'✗'}`));
console.log(`FAIL ${R.FAILS.length}`);R.FAILS.forEach(f=>console.log('  ✗ '+f));
console.log(`WARN ${R.WARN.length}`);R.WARN.forEach(w=>console.log('  ⚠ '+w));
console.log(R.FAILS.length?'❌ 有 FAIL':'✅ 3A 全绿');
clearTimeout(WD); await b.close(); process.exit(R.FAILS.length?1:0);
