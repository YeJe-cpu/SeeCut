// 找证据：把口播提到的真实网页截成图（参考片"真实证据优先"）。截完必须读图核敏感字（总纲第7条）再入片。
// 用法: node grab_evidence.mjs <输出目录> <url> [<url>...]   可选环境: EVID_W=1280 EVID_H=800 EVID_FULL=1 JIANJI_PROXY=http://127.0.0.1:1087
// playwright-core 从当前目录或 skill scripts 目录解析（npm i playwright-core）。
import fs from 'fs'; import path from 'path'; import { chromium, chromePath, watchdog } from './_common.mjs';
const [,,outDir,...urls]=process.argv; if(!outDir||!urls.length){console.error('用法: node grab_evidence.mjs <输出目录> <url>...');process.exit(2);}
fs.mkdirSync(outDir,{recursive:true}); watchdog(60000*urls.length+30000,'grab_evidence');
const px=process.env.JIANJI_PROXY;
const b=await chromium(process.cwd()).launch({headless:true,executablePath:chromePath(),...(px?{proxy:{server:px}}:{})});
const ctx=await b.newContext({viewport:{width:+(process.env.EVID_W||1280),height:+(process.env.EVID_H||800)},deviceScaleFactor:2,locale:'zh-CN'});
for(const [i,u] of urls.entries()){const pg=await ctx.newPage();
  try{await pg.goto(u,{waitUntil:'networkidle',timeout:45000});}catch(e){console.log(`⚠ ${u} 加载未完全: ${e.message.split('\n')[0]}`);}
  await new Promise(r=>setTimeout(r,1500));
  const f=path.join(outDir,`evid_${String(i+1).padStart(2,'0')}_${new URL(u).hostname}.png`);
  await pg.screenshot({path:f,fullPage:!!process.env.EVID_FULL}); console.log('✓',f,'←',u); await pg.close();}
await b.close(); console.log('截完。下一步：逐张读图核敏感字，再登记到 素材台账.md');
