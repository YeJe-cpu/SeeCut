// 共用：读工程配置 project.json、定位 playwright-core 与无头 Chrome。
import fs from 'fs'; import path from 'path'; import os from 'os'; import { createRequire } from 'module';
export function loadProject(buildDir){
  const B=path.resolve(buildDir); const f=path.join(B,'project.json');
  if(!fs.existsSync(f)) throw new Error(`缺 ${f}（见 references/07 §配置契约）`);
  const c=JSON.parse(fs.readFileSync(f,'utf8'));
  const d={html:'master.html',timeline:'master',person_dir:'person',person_img_id:'person',person_wrap_id:'personWrap',steady:[],spring:[]};
  const P={...d,...c,B}; for(const k of ['fps','width','height','duration']) if(!P[k]) throw new Error(`project.json 缺 ${k}`);
  P.N=Math.round(P.fps*P.duration); return P;
}
export function chromium(buildDir){
  for(const base of [path.resolve(buildDir), path.resolve(buildDir,'build'), path.dirname(new URL(import.meta.url).pathname)]){
    try{ return createRequire(path.join(base,'package.json'))('playwright-core').chromium; }catch(e){}
  }
  throw new Error(`找不到 playwright-core：在工程目录执行 npm i playwright-core（别用 sudo）`);
}
export function chromePath(){
  if(process.env.JIANJI_CHROME) return process.env.JIANJI_CHROME;
  const root=path.join(os.homedir(),'Library/Caches/ms-playwright');
  if(fs.existsSync(root)) for(const d of fs.readdirSync(root).filter(x=>x.startsWith('chromium_headless_shell')).sort().reverse()){
    for(const sub of fs.readdirSync(path.join(root,d))){ const p=path.join(root,d,sub,'chrome-headless-shell'); if(fs.existsSync(p)) return p; }
  }
  return undefined; // 交给 playwright 默认
}
export function watchdog(ms,label){ const t=setTimeout(()=>{console.error(`⏰ WATCHDOG: ${label} 超 ${ms/1000}s，强退`);process.exit(3);},ms); t.unref&&t.unref(); return t; }
