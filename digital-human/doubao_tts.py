#!/usr/bin/env python3
"""口播配音（豆包语音合成）：文案 → mp3，再交给 heygen_avatar.py 驱动数字人。
我们不用 HeyGen 内置音色（听起来假），也不用分身克隆声（不稳），而是先用豆包 TTS 配好音再喂给数字人。
需要：环境变量 VOLC_APPID、VOLC_ACCESS_TOKEN（火山引擎控制台 → 豆包语音），ffmpeg/ffprobe。

  python3 doubao_tts.py --text "你的口播文案" --out 口播.mp3
  python3 doubao_tts.py --file 文案.txt --out 口播.mp3 --speed 1.1 --voice zh_male_liufei_uranus_bigtts
文案按行分句逐句合成，句间留 0.16 秒气口再拼接（长文案一次合成容易超字数、语气也平）。
"""
import argparse, base64, json, os, subprocess, sys, tempfile, uuid

API = 'https://openspeech.bytedance.com/api/v1/tts'
GAP = 0.16


def tts(text, out, voice, speed):
    appid, token = os.environ.get('VOLC_APPID'), os.environ.get('VOLC_ACCESS_TOKEN')
    if not appid or not token: sys.exit('先 export VOLC_APPID=... VOLC_ACCESS_TOKEN=...（别写进任何文件或仓库）')
    body = {'app': {'appid': appid, 'token': token, 'cluster': 'volcano_tts'},
            'user': {'uid': 'seecut'},
            'audio': {'voice_type': voice, 'encoding': 'mp3', 'speed_ratio': speed, 'rate': 24000},
            'request': {'reqid': str(uuid.uuid4()), 'text': text, 'operation': 'query', 'text_type': 'plain'}}
    r = subprocess.run(['curl', '-sS', '--max-time', '60', '-X', 'POST', API, '-H', f'Authorization: Bearer;{token}',
                        '-H', 'Content-Type: application/json', '-d', json.dumps(body, ensure_ascii=False)],
                       capture_output=True, text=True)
    try: d = json.loads(r.stdout)
    except Exception: sys.exit(f'豆包返回异常：{r.stdout[:300]} {r.stderr[:300]}')
    if not d.get('data'): sys.exit(f'合成失败：{json.dumps(d, ensure_ascii=False)[:300]}')
    open(out, 'wb').write(base64.b64decode(d['data']))


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--text'); g.add_argument('--file')
    p.add_argument('--out', required=True)
    p.add_argument('--voice', default='zh_male_liufei_uranus_bigtts', help='音色 id，控制台音色列表里挑')
    p.add_argument('--speed', type=float, default=1.1)
    a = p.parse_args()
    lines = [a.text] if a.text else [l.strip() for l in open(a.file, encoding='utf-8') if l.strip()]
    tmp = tempfile.mkdtemp()
    gap = os.path.join(tmp, 'gap.mp3')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-t', str(GAP), '-q:a', '9', gap], check=True)
    parts = []
    for i, t in enumerate(lines):
        seg = os.path.join(tmp, f'seg_{i:03d}.mp3'); tts(t, seg, a.voice, a.speed)
        parts += [seg] + ([gap] if i < len(lines) - 1 else [])
        print(f'  {i + 1}/{len(lines)} {t[:20]}')
    lst = os.path.join(tmp, 'list.txt')
    open(lst, 'w').write(''.join(f"file '{x}'\n" for x in parts))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c:a', 'libmp3lame', '-b:a', '128k', a.out], check=True)
    d = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a.out]).decode().strip()
    print(f'完成 → {a.out}（{float(d):.1f} 秒）')


if __name__ == '__main__':
    main()
