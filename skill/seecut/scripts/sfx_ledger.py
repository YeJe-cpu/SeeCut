#!/usr/bin/env python3
"""给任意本地音效库建台账（开放给用户：用自己的音效，不用我们的）。
用法: python3 sfx_ledger.py <音效文件夹> --out <台账.json> [--listen]
  自动实测（免费、确定性）：时长、起音点 trim_start（能量包络首次到峰值 10%）、第一下长度 first_hit_len、共几下 hits。
  --listen：再用 agy（Gemini 能听音频）逐个听，补 类别/听感/适合配什么/口播适用度（4 路并行；只信音色描述，时间一律用实测）。
  不加 --listen 时，类别按文件名关键词猜（唰/转场→whoosh、叮→ding、咚/重击→impact、翻页→page、点击/咔→click、错误→error、正确→correct、金币/到账→money、出现/弹→pop），猜不到记 other，建议人工或 --listen 补。
然后：sfx.py plan --ledger <台账.json> --sfx-dir <音效文件夹> ...
"""
import argparse, json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

EXT = ('.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac')
GUESS = [('whoosh', '唰|转场|whoosh|swoosh|swish'), ('ding', '叮|ding|ping|bell|铃'), ('impact', '咚|重击|重磅|boom|hit|impact|拳'),
         ('page', '翻页|page|flip'), ('click', '点击|咔|click|key|按键'), ('error', '错误|error|wrong|fail'),
         ('correct', '正确|correct|success'), ('money', '金币|到账|收银|coin|cash|money'), ('pop', '出现|弹|pop|bubble|字幕')]


def pcm(path, sr=16000):
    import numpy as np
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'], capture_output=True).stdout
    return np.abs(np.frombuffer(raw, dtype=np.float32)), sr


def measure(path):
    import numpy as np
    a, sr = pcm(path)
    if not len(a):
        return None
    w = max(1, sr // 100)  # 10ms 包络
    env = np.convolve(a, np.ones(w) / w, 'same'); pk = env.max() or 1e-9
    on = env >= pk * 0.10
    trim = int(np.argmax(on)) / sr
    # 分段：有声段之间静音 ≥0.15s 算新的一下
    segs, i, n, gap = [], 0, len(on), int(0.15 * sr)
    while i < n:
        if not on[i]: i += 1; continue
        j = i
        while j < n:
            k = j
            while k < n and not on[k]: k += 1
            if k - j >= gap or k >= n: break
            j = k + 1
        while j < n and on[j]: j += 1
        segs.append((i / sr, j / sr)); i = j + 1
    return {'duration': round(len(a) / sr, 3), 'trim_start': round(trim, 3),
            'first_hit_len': round(segs[0][1] - segs[0][0], 3) if segs else round(len(a) / sr - trim, 3), 'hits': len(segs) or 1}


def guess(name):
    for cat, pat in GUESS:
        if re.search(pat, name, re.I): return cat
    return 'other'


def listen(path):
    skill = os.path.dirname(os.path.abspath(__file__))
    q = ('这是短视频剪辑用的一个音效文件。只输出一行 JSON（不要其它文字）：{"听感":"一句话描述音色","类别":"从[pop/whoosh/impact/ding/page/click/error/correct/money/hook/梗/氛围/other]选一",'
         '"适合配":["2-3个画面动作"],"口播科普适用度":"常用/偶尔/慎用"}')
    try:
        out = subprocess.run(['zsh', os.path.join(skill, 'agy_read.sh'), path, q, '180'], capture_output=True, text=True, timeout=260).stdout
        m = re.search(r'\{.*"听感".*\}', out, re.S)
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}


ap = argparse.ArgumentParser(); ap.add_argument('dir'); ap.add_argument('--out', required=True); ap.add_argument('--listen', action='store_true')
a = ap.parse_args()
files = sorted(f for f in os.listdir(a.dir) if f.lower().endswith(EXT))
if not files: sys.exit(f'{a.dir} 里没有音频文件')
rows = []
for f in files:
    m = measure(os.path.join(a.dir, f))
    if m: rows.append({'file': f, **m, 'category': guess(f), 'koubo_use': '偶尔', 'desc': ''})
if a.listen:
    with ThreadPoolExecutor(4) as ex:
        for r, d in zip(rows, ex.map(lambda r: listen(os.path.join(a.dir, r['file'])), rows)):
            if d:
                r['desc'] = d.get('听感', ''); r['fits'] = d.get('适合配', []); r['koubo_use'] = d.get('口播科普适用度', r['koubo_use'])
                if r['category'] == 'other' and d.get('类别'): r['category'] = d['类别']
json.dump(rows, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import Counter
print(f'{len(rows)} 个音效 → {a.out}；类别：{dict(Counter(r["category"] for r in rows))}；有 {sum(r["hits"] > 1 for r in rows)} 个不止一下（只取第一下）')
