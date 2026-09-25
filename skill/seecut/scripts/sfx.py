#!/usr/bin/env python3
"""音效：选点 → 算对齐/裁剪/音量 → 检查 → 混进成片（同一份 sfx_plan 也喂给 jianying_plan.py 进剪映草稿）。

1) 计划：python3 sfx.py plan --choices sfx_choices.json --voice 原声或成片.mp4 [--words seg_words.json] --out sfx_plan.json
   sfx_choices.json = 执行窗按 references/09-音效规范 挑的落点：
     [{"t": 4.40, "kind": "impact", "sfx": "咚-重击.mp3", "why": "割韭菜印章落地", "gain_db": -3}, ...]   （gain_db 可选）
     t = 画面事件时刻（元素出现帧，取自 layers/manifest.json 的 events 或 GSAP 时间轴）
     kind ∈ hook(开头抓耳) / pop(弹出) / whoosh(滑入换幕缩窗) / impact(砸下落定) / ding(要点完成) /
            click(按键点选) / page(翻页换图) / error(红叉翻车) / correct(对勾) / money(钱) / other
2) 混音：python3 sfx.py mix --plan sfx_plan.json --video 成片.mp4 --out 成片_带音效.mp4
音效文件：<skill>/references/sfx/音效库台账.json 里的文件名，到 $JIANJI_SFX_DIR（默认 ~/Downloads/音效）下找。
"""
import argparse, json, math, os, re, subprocess, sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(SKILL, 'references/sfx/音效库台账.json')  # 默认台账；用户自己的库用 sfx_ledger.py 生成后 --ledger 指过来
SFX_DIR = os.path.expanduser(os.environ.get('JIANJI_SFX_DIR', '~/Downloads/音效'))
# 声音起点相对画面事件的偏移（2-4.1 实测）：砸下类要等弹簧落地那帧；whoosh 要跨过切点
OFFSET = {'impact': 0.12, 'whoosh': -0.08}
# 目标峰值（相对人声峰值，dB）：压在人声下面（2-4.1 实配 -16~-11）
TARGET = {'hook': -12, 'impact': -12, 'error': -14, 'page': -14, 'whoosh': -15, 'pop': -16, 'ding': -16,
          'click': -15, 'correct': -15, 'money': -14, 'other': -15}
LOW_FREQ = {'impact'}  # 低频重击压在关键词上会"吃字"


def peak_db(path, start=0.0, dur=None):
    cmd = ['ffmpeg', '-hide_banner', '-ss', f'{start:.3f}', '-i', path]
    if dur: cmd += ['-t', f'{dur:.3f}']
    out = subprocess.run(cmd + ['-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True).stderr
    m = re.search(r'max_volume: (-?[\d.]+) dB', out)
    return float(m.group(1)) if m else -20.0


def cmd_plan(a):
    lp = a.ledger or LEDGER
    if not os.path.exists(lp):
        sys.exit('没有音效台账：先用 scripts/sfx_ledger.py <你的音效文件夹> --out 台账.json 建一份，再加 --ledger 台账.json --sfx-dir <文件夹>')
    led = {r['file']: r for r in json.load(open(lp, encoding='utf-8'))}
    sfx_dir = os.path.expanduser(a.sfx_dir or SFX_DIR)
    choices = json.load(open(a.choices, encoding='utf-8'))
    fps = a.fps
    vpk = peak_db(a.voice)
    words = []
    if a.words:
        w = json.load(open(a.words, encoding='utf-8'))
        if isinstance(w, dict) and 'segments' in w:  # faster_whisper 分段格式
            w = [x for sg in w['segments'] for x in sg.get('words', [])]
        elif isinstance(w, dict):
            w = w.get('words', [])
        for x in w:
            if isinstance(x, dict) and 'start' in x and 'end' in x:
                words.append((float(x['start']), float(x['end']), x.get('word', x.get('text', ''))))
    items, warns = [], []
    for c in sorted(choices, key=lambda c: c['t']):
        r = led.get(c['sfx'])
        if not r:
            sys.exit(f"台账里没有 {c['sfx']}（文件名要和 references/sfx/音效库台账.json 一致）")
        src = os.path.join(sfx_dir, r['file'])
        kind = c.get('kind', 'other')
        t = c['t'] + OFFSET.get(kind, 0.0)
        t = math.ceil(round(t * fps, 6)) / fps  # 向上取整到帧：声音不能早于画面
        trim = float(r['trim_start'])
        dur = min(float(r.get('first_hit_len') or r['duration']), 0.8 if kind != 'hook' else 1.5, float(r['duration']) - trim - 0.02)
        if dur <= 0.05:
            sys.exit(f"{r['file']} 起音点后几乎没有声音，换一个")
        gain_db = TARGET.get(kind, -15) + vpk - peak_db(src, trim, dur) + float(c.get('gain_db', 0))  # choices 可写 gain_db 单条微调（如 -3 避让口播）
        vol = round(min(1.0, 10 ** (gain_db / 20)), 3)
        if kind in LOW_FREQ and float(c.get('gain_db', 0)) > -3:
            hit = [(ws, we, wd) for ws, we, wd in words if ws - 0.05 <= t <= we + 0.05]
            if hit:
                we = max(h[1] for h in hit)
                warns.append(f"{t:.2f}s 的 {r['file']}（低频重击）压在口播「{''.join(h[2] for h in hit)}」上 → 挪到词说完 {math.ceil(we * fps) / fps:.2f}s，或降 3dB")
        if r.get('koubo_use') == '慎用':
            warns.append(f"{t:.2f}s 用了慎用音效 {r['file']}：确认语义特别贴，一条片最多 1 次")
        items.append({'at_us': int(round(t * 1e6)), 't': round(t, 3), 'event_t': c['t'], 'kind': kind, 'why': c.get('why', ''),
                      'source': src, 'source_start_us': int(round(trim * 1e6)), 'duration_us': int(round(dur * 1e6)), 'volume': vol})
    # 检查：开头抓耳 / 密度 / 重复
    ts = [i['t'] for i in items if i['kind'] != 'hook']  # 开头抓耳音效不计入密度（作者要求开头必须有）
    if not any(i['t'] <= 0.5 for i in items):
        warns.append('开头 0.5 秒内没有音效：总纲要求开头给一个醒目的音效（kind=hook，如 叮当声/叮叮_/重磅出场）')
    for i, t in enumerate(ts):
        win = [x for x in ts if t <= x < t + 3.0]
        if len(win) > 2:
            warns.append(f'{t:.2f}-{t + 3:.2f}s 有 {len(win)} 个音效，超过"任意 3 秒最多 2 个" → 删掉意义最弱的'); break
    total = a.duration or (max(ts) + 1 if ts else 1)
    if ts and len(ts) / total > 0.7:
        warns.append(f'全片 {len(ts)} 个 / {total:.1f}s = {len(ts) / total:.2f} 个每秒，超过 0.7')
    from collections import Counter
    for f, n in Counter(os.path.basename(i['source']) for i in items).items():
        if n > 2: warns.append(f'{f} 用了 {n} 次（>2 次易单调，换一个同类）')
    json.dump({'voice_peak_db': vpk, 'items': items, 'warnings': warns}, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(items)} 个音效 → {a.out}')
    for w in warns: print('  ⚠', w)
    if not warns: print('  ✓ 检查全过（开头抓耳 / 密度 / 关键词避让 / 重复）')


def cmd_mix(a):
    plan = json.load(open(a.plan, encoding='utf-8'))['items']
    inputs, fc, labels = ['-i', a.video], [], ['[0:a]']
    for k, e in enumerate(plan, 1):
        inputs += ['-i', e['source']]
        fc.append(f"[{k}:a]atrim=start={e['source_start_us'] / 1e6:.3f}:duration={e['duration_us'] / 1e6:.3f},asetpts=PTS-STARTPTS,"
                  f"volume={e['volume']},adelay={e['at_us'] // 1000}|{e['at_us'] // 1000}[s{k}]")
        labels.append(f'[s{k}]')
    fc.append(''.join(labels) + f'amix=inputs={len(labels)}:normalize=0:duration=first[aout]')
    subprocess.check_call(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', ';'.join(fc), '-map', '0:v', '-map', '[aout]',
                           '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', a.out])
    print('带音效成片:', a.out)


ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest='cmd', required=True)
p = sub.add_parser('plan'); p.add_argument('--choices', required=True); p.add_argument('--voice', required=True)
p.add_argument('--words'); p.add_argument('--out', required=True); p.add_argument('--ledger'); p.add_argument('--sfx-dir'); p.add_argument('--fps', type=float, required=True); p.add_argument('--duration', type=float)
m = sub.add_parser('mix'); m.add_argument('--plan', required=True); m.add_argument('--video', required=True); m.add_argument('--out', required=True)
a = ap.parse_args()
cmd_plan(a) if a.cmd == 'plan' else cmd_mix(a)
