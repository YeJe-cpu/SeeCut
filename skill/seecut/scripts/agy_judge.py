#!/usr/bin/env python3
"""agy 评委（v2）：硬伤清单 check / 两两对比 pair。

用法:
  python3 agy_judge.py check --video v2.mp4 [--html master.html] [--out qc/v2-check.json]
  python3 agy_judge.py pair  --a v2.mp4 --b v1.mp4 [--html-a a.html] [--html-b b.html] [--out qc/v2-vs-v1.json]

内置纪律（见 references/06-质检闭环spec.md §五）：
  每次 --new-project；JSON schema 输出；指纹核（照抄文字须在 html 源码里命中 ≥2 条，无 html 则跳过）；
  时长核（与 ffprobe 差 ≤3s）；无效重跑 1 次，仍无效则标 invalid；pair 自动交换位置跑两次求共识。
代理：继承当前环境的 https_proxy/http_proxy/all_proxy；若设了 JIANJI_PROXY=http://127.0.0.1:1087 则自动套用。
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS = {'check': 'references/prompt/硬伤清单.txt', 'pair': 'references/prompt/对比评委.txt'}
SCHEMAS = {'check': 'scripts/schemas/check.json', 'pair': 'scripts/schemas/pair.json'}
AGY = os.environ.get('AGY_BIN') or shutil.which('agy') or os.path.expanduser('~/.local/bin/agy')


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def duration(path):
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path])
    return float(out.decode().strip())


def to540(src, dst):
    sc = "scale='if(gt(iw,ih),-2,540)':'if(gt(iw,ih),540,-2)'"
    subprocess.check_call(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', sc, '-c:v', 'libx264', '-crf', '26',
                           '-c:a', 'aac', '-b:a', '96k', dst])


def norm(s):
    return re.sub(r'[\s\W_]+', '', s or '').lower()


def fp_source(html_path, extra=None):
    """指纹比对源 = 成片源码文字（去标签）+ 证据截图里的字（fp-manifest.txt：执行窗读图核敏感字时顺手转录）"""
    if not html_path:
        return None
    html = open(html_path, encoding='utf-8', errors='ignore').read()
    parts = [re.sub(r'<[^>]+>', '', html)]  # 去标签：页面文字常被 <span>/<br> 拆开
    auto = os.path.join(os.path.dirname(os.path.abspath(html_path)), 'fp-manifest.txt')
    for f in [auto] + list(extra or []):
        if f and os.path.exists(f):
            parts.append(open(f, encoding='utf-8', errors='ignore').read())
    return norm(' '.join(parts))


def fp_hits(texts, html_path, extra=None):
    src = fp_source(html_path, extra)
    if src is None:
        return None
    hits = 0
    for t in texts:
        n = norm(t)
        if len(n) >= 2 and (n in src or (len(n) >= 6 and n[:6] in src)):
            hits += 1
    return hits


def last_json(text, key):
    dec, found, i = json.JSONDecoder(), None, 0
    while True:
        i = text.find('{', i)
        if i < 0:
            return found
        try:
            obj, end = dec.raw_decode(text, i)
            if isinstance(obj, dict) and key in obj:
                found = obj
            i = end
        except ValueError:
            i += 1


RAW_DIR = None  # 设了就把每次 agy 原始输出留档到这里


class AuthError(Exception):
    pass


class Transient(Exception):
    """接口断连/超时：与内容无关，立即重试（2-4.1 实测：21 次调用 9 次败于 EOF/超时，每次白等 2-9 分钟）"""


def run_agy(mode, workdir, timeout):
    env = dict(os.environ)
    px = env.get('JIANJI_PROXY')
    if px:
        env.update(https_proxy=px, http_proxy=px, HTTPS_PROXY=px, HTTP_PROXY=px, no_proxy='localhost,127.0.0.1')
    prompt = open(os.path.join(SKILL, PROMPTS[mode]), encoding='utf-8').read() + '\n只根据本目录里的视频文件作答，不要读取、列出或搜索任何其他文件。'
    cmd = [AGY, '-p', prompt, '--new-project', '--add-dir', '.', '--model', 'gemini-3.8-flash-high',
           '--json-schema', os.path.join(SKILL, SCHEMAS[mode]), '--output-format', 'json',
           '--dangerously-skip-permissions', '--print-timeout', f'{timeout}s']
    try:
        p = subprocess.run(cmd, cwd=workdir, env=env, capture_output=True, text=True, timeout=timeout + 30)
        raw = p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        raise Transient(f'agy 超过 {timeout}s 未返回')
    if RAW_DIR:
        os.makedirs(RAW_DIR, exist_ok=True)
        open(os.path.join(RAW_DIR, f'{mode}-{time.strftime("%H%M%S")}-{os.path.basename(workdir)}.raw'), 'w', encoding='utf-8').write(raw)
    try:
        outer = json.loads(p.stdout)
        if outer.get('status') == 'ERROR':
            raise Transient('agy 接口报错: ' + str(outer.get('error', ''))[:120])
        so = outer.get('structured_output')
        if isinstance(so, dict) and ('checks' in so or 'dimensions' in so):
            return so
        resp = outer.get('response', '')
    except Transient:
        raise
    except Exception:
        resp = raw
        # 只在没拿到正常 JSON 时才判授权问题，避免视频内容里恰好有这些词被误判
        if re.search(r'Authentication required|not logged in|please (re-?)?log ?in', raw, re.I):
            raise AuthError('agy 授权过期/未登录：请人工在终端裸跑一次 agy 重新登录后再试')
        if re.search(r'time(d)? ?out|deadline', raw, re.I):
            raise Transient('agy 自身 print-timeout 超时')
    return last_json(resp, 'checks' if mode == 'check' else 'dimensions')


def judge_once(mode, files, htmls, timeout, extra=None):
    """files: {'A': path} 或 {'X': path, 'Y': path}；返回 (result, problems)"""
    wd = tempfile.mkdtemp(prefix='jianji_agy_')  # 系统 tmp：评委只能看到这两个 mp4，读不到工程源码/runlog（2-4.1 实证污染）
    try:
        real = {}
        for k, f in files.items():
            to540(f, os.path.join(wd, f'{k}.mp4'))
            real[k] = duration(f)
        r = run_agy(mode, wd, timeout)
    finally:
        shutil.rmtree(wd, ignore_errors=True)
    if not r:
        return None, ['无有效 JSON']
    probs = []
    fp = r.get('fingerprint', {})
    if mode == 'check':
        pairs = [('A', fp.get('texts', []), fp.get('duration_sec', 0))]
    else:
        pairs = [('X', fp.get('X_texts', []), fp.get('X_duration_sec', 0)),
                 ('Y', fp.get('Y_texts', []), fp.get('Y_duration_sec', 0))]
    for k, texts, d in pairs:
        if abs((d or 0) - real[k]) > 3:
            probs.append(f'{k} 时长不符 agy={d} 实测={real[k]:.1f}')
        h = fp_hits(texts, htmls.get(k), extra)
        if h is not None and h < 2:
            probs.append(f'{k} 指纹命中 {h}/≥2（疑似 confab）: {texts}')
    return r, probs


def judge(mode, files, htmls, timeout, extra=None):
    content_tries, probs, r = 0, [], None
    for attempt in range(1, 5):
        try:
            r, probs = judge_once(mode, files, htmls, timeout, extra)
        except Transient as e:
            log(f'第{attempt}次接口失败（{e}），立即重试')
            probs, r = [str(e)], None
            continue
        if r and not probs:
            return {'valid': True, 'result': r}
        content_tries += 1
        log(f'第{attempt}次结果无效:', '; '.join(probs))
        if content_tries >= 2:
            break
    return {'valid': False, 'problems': probs, 'result': r}


def secs(txt):
    """从证据文字里抽第一段时间：00:14-00:15 / 14.8s / 00:14 → [起, 止]"""
    m = re.findall(r'(\d{1,2}):(\d{2}(?:\.\d+)?)', txt or '')
    ts = [int(a) * 60 + float(b) for a, b in m[:2]]
    if not ts:
        ts = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*s', txt or '')[:2]]
    return ts


def grab_fail_frames(video, fails, outdir):
    """agy 报的 FAIL 自动抽帧，交执行窗读图核实（agy 会串相邻两拍，历史上多次误报穿模/残留）"""
    os.makedirs(outdir, exist_ok=True)
    made = []
    for c in fails:
        ts = secs(c.get('evidence', ''))
        if not ts:
            continue
        a, b = ts[0], (ts[1] if len(ts) > 1 else ts[0] + 1)
        for t in sorted({a, (a + b) / 2, b}):
            f = os.path.join(outdir, f"{c['id']}_{t:.1f}s.jpg")
            subprocess.call(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', video, '-frames:v', '1',
                             '-vf', 'scale=360:-2', f])
            made.append(f)
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['check', 'pair'])
    ap.add_argument('--video'); ap.add_argument('--html')
    ap.add_argument('--a'); ap.add_argument('--b'); ap.add_argument('--html-a'); ap.add_argument('--html-b')
    ap.add_argument('--out'); ap.add_argument('--timeout', type=int, default=240)  # 成功调用多在 60-240s；超时即判断连断重试
    ap.add_argument('--fp-extra', action='append', default=[],
                    help='额外指纹文字清单（证据截图里的字），可多次；html 同目录的 fp-manifest.txt 会自动读')
    a = ap.parse_args()
    global RAW_DIR
    if a.out:
        RAW_DIR = os.path.splitext(os.path.abspath(a.out))[0] + '_raw'

    if a.mode == 'check':
        log('check', a.video)
        res = judge('check', {'A': a.video}, {'A': a.html}, a.timeout, a.fp_extra)
        if res['valid']:
            fails = [c for c in res['result']['checks'] if not c['pass']]
            res['summary'] = {'valid': True, 'gate_pass': not fails, 'fails': [c['id'] for c in fails],
                              'evidence_gaps': len(res['result'].get('evidence_gaps', []))}
            if fails and a.out:
                fr = grab_fail_frames(a.video, fails, os.path.splitext(os.path.abspath(a.out))[0] + '_failframes')
                res['summary']['verify_frames'] = fr
                log(f'⚠ {len(fails)} 条 FAIL 待核：读这些帧确认是否 agy 误报（串场）→', os.path.dirname(fr[0]) if fr else '无时间码')
        else:
            res['summary'] = {'valid': False, 'gate_pass': None,
                              'note': 'agy 两次都无效，本次没有检查结果，不能当作通过/不通过'}
    else:
        log('pair 两序并行：X=a/Y=b 与 X=b/Y=a')
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(2) as ex:
            f1 = ex.submit(judge, 'pair', {'X': a.a, 'Y': a.b}, {'X': a.html_a, 'Y': a.html_b}, a.timeout, a.fp_extra)
            f2 = ex.submit(judge, 'pair', {'X': a.b, 'Y': a.a}, {'X': a.html_b, 'Y': a.html_a}, a.timeout, a.fp_extra)
            r1, r2 = f1.result(), f2.result()
        w1 = ('A' if r1['result']['winner'] == 'X' else 'B') if r1['valid'] else None
        w2 = ('B' if r2['result']['winner'] == 'X' else 'A') if r2['valid'] else None
        consensus = w1 if (w1 and w1 == w2) else ('invalid' if not (w1 and w2) else 'tie')
        res = {'a': a.a, 'b': a.b, 'order1': r1, 'order2': r2, 'winners': [w1, w2], 'consensus': consensus}
    out = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, 'w', encoding='utf-8').write(out)
    s = res.get('summary') or {'consensus': res.get('consensus'), 'winners': res.get('winners')}
    log('结果:', json.dumps(s, ensure_ascii=False), '→', a.out or '(stdout 未存)')
    if not a.out:
        print(out)
    # 退出码：0=通过/有共识  1=check 有 FAIL  2=无效（没结果）  3=授权过期
    if a.mode == 'check':
        sys.exit(2 if not res['summary']['valid'] else (0 if res['summary']['gate_pass'] else 1))
    sys.exit(2 if consensus == 'invalid' else 0)


if __name__ == '__main__':
    try:
        main()
    except AuthError as e:
        log('⛔', e)
        sys.exit(3)
