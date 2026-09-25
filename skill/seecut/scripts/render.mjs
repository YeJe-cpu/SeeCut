// 逐帧渲染：人像 <img> 逐帧换 src（禁 video scrub）+ timeline.time(i/fps) 绝对 seek。带进度+看门狗。
// 用法: node render.mjs <build目录> [full|probe] [probe帧号,逗号分隔]
// 迭代版提速：RENDER_SCALE=0.5 node render.mjs build full → 半分辨率出帧（版式不变），终版不设（全分辨率）
// 前置: <build>/project.json；ffmpeg -i 源片 -vf fps=<fps> -vsync cfr -q:v 3 -start_number 1 <build>/person/p%04d.jpg
import fs from 'fs'; import path from 'path';
import { loadProject, chromium, chromePath, watchdog } from './_common.mjs';
const [,,buildDir,mode='probe',list]=process.argv;
if(!buildDir){console.error('用法: node render.mjs <build目录> [full|probe] [帧号]');process.exit(2);}
const P=loadProject(buildDir);
const OUT=path.join(P.B, mode==='full'?'frames':'probe_frames'); fs.mkdirSync(OUT,{recursive:true});
const frames = mode==='full' ? [...Array(P.N).keys()]
  : (list ? list.split(',').map(Number) : [...Array(12).keys()].map(i=>Math.round((i+0.5)*P.N/12)));
const pad=n=>String(n).padStart(4,'0');
const PD=path.join(P.B,P.person_dir); const NP=fs.existsSync(PD)?fs.readdirSync(PD).filter(f=>/^p\d+\.jpg$/.test(f)).length:0;
watchdog(mode==='full'?Math.max(900000,P.N*4000):120000,`render(${mode})`);
let last=Date.now(); const st=setInterval(()=>{if(Date.now()-last>60000){console.error('⏰ 60s 无帧进展，退出');process.exit(4);}},15000); st.unref&&st.unref();
const b=await chromium(P.B).launch({headless:true,executablePath:chromePath()});
const SCALE=+(process.env.RENDER_SCALE||P.output_scale||1);  // 终版=output_scale（源片宽/构图宽，如 1080/720=1.5）；迭代版设 RENDER_SCALE=0.5
const pg=await (await b.newContext({viewport:{width:P.width,height:P.height},deviceScaleFactor:SCALE})).newPage();
const errs=[]; pg.on('console',m=>{if(m.type()==='error')errs.push(m.text());});
await pg.goto('file://'+path.join(P.B,P.html),{waitUntil:'load',timeout:30000});
await pg.evaluate(()=>document.fonts&&document.fonts.ready).catch(()=>{});
await new Promise(r=>setTimeout(r,400));
const gd=await pg.evaluate(n=>window.__timelines&&window.__timelines[n]?window.__timelines[n].duration():null,P.timeline);
if(gd==null){console.error(`找不到 window.__timelines.${P.timeline}`);process.exit(2);}
const dd=gd-P.duration;
console.log(`${dd<-0.15?'⚠️ 动画比视频短(结尾会空)':dd>0.15?'ℹ️ 动画比视频长 '+dd.toFixed(2)+'s(尾部溢出，按绝对时间取帧不影响画面；若是循环动画撑长要查)':'✓ 时长'}: GSAP=${gd.toFixed(2)}s 视频=${P.duration}s；人像帧 ${NP}；输出 ${frames.length} 帧 ×${SCALE} → ${OUT}`);
for(const i of frames){
  const psrc=NP?'file://'+path.join(PD,'p'+pad(Math.min(i+1,NP))+'.jpg'):null;
  await pg.evaluate(async({t,psrc,tl,pid})=>{window.__timelines[tl].time(t);
    const im=document.getElementById(pid); if(im&&psrc){im.src=psrc; try{await im.decode();}catch(e){}}},
    {t:i/P.fps,psrc,tl:P.timeline,pid:P.person_img_id});
  await pg.screenshot({path:path.join(OUT,`f${pad(i)}.png`)}); last=Date.now();
  if(mode==='full'&&i%50===0) console.log(`  ${i}/${P.N} ${new Date().toLocaleTimeString()}`);
}
if(errs.length) console.log('页面报错:',errs.slice(0,5));
console.log('DONE',new Date().toLocaleTimeString()); await b.close(); process.exit(0);
