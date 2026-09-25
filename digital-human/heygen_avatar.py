#!/usr/bin/env python3
"""数字人口播 A-roll（HeyGen）：生成一条竖屏口播 mp4，作为 skill 的输入素材。
需要：环境变量 HEYGEN_API_KEY；curl、ffmpeg/ffprobe。国内网络需要代理（curl 会读 https_proxy）。

  python3 heygen_avatar.py balance                                   # 查钱包余额（提交前先查：余额不足也会照扣钱，且不能取消）
  python3 heygen_avatar.py looks --avatar-group <网页里建好的分身组 id>  # 列出 look，并显示每个 look 支持的引擎
  # 基础方案 AV4：一张照片 + 一段口播音频
  python3 heygen_avatar.py av4 --photo 我.png --audio 口播.mp3 --out a_roll.mp4
  # 进阶方案 AV5：网页建好的数字分身 look + 口播音频（或文字 + 音色）
  python3 heygen_avatar.py av5 --look <LOOK_ID> --audio 口播.mp3 --out a_roll.mp4
  python3 heygen_avatar.py av5 --look <LOOK_ID> --script "文案" --voice <VOICE_ID> --out a_roll.mp4
音频建议先用 doubao_tts.py 配好（HeyGen 内置音色偏假、分身克隆声往往不稳）。输出统一为竖屏：AV5 目前默认出横屏（人像居中两边灰边），脚本会自动裁回竖屏。
"""
import argparse, json, os, subprocess, sys, time

API = 'https://api.heygen.com'


def key():
    k = os.environ.get('HEYGEN_API_KEY')
    if not k: sys.exit('先 export HEYGEN_API_KEY=...（HeyGen 网页 → Settings → API）')
    return k


def curl(method, path, body=None, form=None):
    cmd = ['curl', '-sS', '-X', method, API + path, '-H', f'X-Api-Key: {key()}']
    if body is not None: cmd += ['-H', 'Content-Type: application/json', '-d', json.dumps(body, ensure_ascii=False)]
    if form: cmd += ['-F', form]
    out = subprocess.run(cmd, capture_output=True, text=True)
    try: return json.loads(out.stdout)
    except Exception: sys.exit(f'HeyGen 返回异常：{out.stdout[:300]} {out.stderr[:300]}')


def upload(path):
    mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.m4a': 'audio/mp4'}
    ext = os.path.splitext(path)[1].lower()
    r = curl('POST', '/v3/assets', form=f'file=@{path};type={mime.get(ext, "application/octet-stream")}')  # 必须 multipart 的 file 字段
    d = r.get('data') or {}
    if not d.get('asset_id'): sys.exit(f'上传失败：{r}')
    return d


def balance():
    r = curl('GET', '/v3/users/me')
    return ((r.get('data') or {}).get('wallet') or {}).get('remaining_balance')


def submit_and_wait(body, out):
    b = balance(); print(f'钱包余额：{b}（AV4 约 $0.04/秒，AV5 约 $0.12/秒）')
    r = curl('POST', '/v3/videos', body)
    vid = (r.get('data') or {}).get('video_id')
    if not vid: sys.exit(f'提交失败：{r}')
    print('已提交', vid, '，渲染中（通常几分钟）…')
    for _ in range(180):
        time.sleep(10)
        s = (curl('GET', f'/v1/video_status.get?video_id={vid}').get('data') or {})
        st = s.get('status')
        if st == 'completed':
            raw = out + '.raw.mp4'
            subprocess.check_call(['curl', '-sSL', s['video_url'], '-o', raw]); to_vertical(raw, out); os.remove(raw)
            print('完成 →', out); return
        if st == 'failed': sys.exit(f'渲染失败：{s.get("error")}')
    sys.exit(f'30 分钟还没完成，稍后用 video_id={vid} 自己查')


def to_vertical(src, out):
    w, h = map(int, subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', src]).decode().strip().split(','))
    if h >= w:
        os.replace(src, out); return
    cw = int(h * 9 / 16) // 2 * 2  # 横屏里居中那条竖版人像
    subprocess.check_call(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', f'crop={cw}:{h}:{(w - cw) // 2}:0,scale=-2:1280',
                           '-c:v', 'libx264', '-crf', '18', '-c:a', 'copy', out])


def speech(a):
    if a.audio: return {'audio_asset_id': upload(a.audio)['asset_id']}
    if a.script and a.voice: return {'script': a.script, 'voice_id': a.voice}
    sys.exit('要么 --audio 口播音频，要么 --script 文案 + --voice 音色 id')


ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest='cmd', required=True)
sub.add_parser('balance')
l = sub.add_parser('looks'); l.add_argument('--avatar-group', required=True)
for name in ('av4', 'av5'):
    p = sub.add_parser(name); p.add_argument('--out', required=True); p.add_argument('--audio'); p.add_argument('--script'); p.add_argument('--voice')
    if name == 'av4': p.add_argument('--photo', required=True)
    else: p.add_argument('--look', required=True)
a = ap.parse_args()
if a.cmd == 'balance':
    print(balance())
elif a.cmd == 'looks':
    looks = (curl('GET', f'/v2/avatar_group/{a.avatar_group}/avatars').get('data') or {}).get('avatar_list', [])
    for lk in looks:
        lid = lk.get('id') or lk.get('avatar_id')  # 接口里不同 look 用的字段名不一样
        info = curl('GET', f"/v3/avatars/looks/{lid}").get('data') or {}
        print(lid, lk.get('name') or info.get('name', ''), info.get('avatar_type', ''), info.get('supported_api_engines', ''))
elif a.cmd == 'av4':
    body = {'type': 'image', 'image': {'type': 'asset_id', 'asset_id': upload(a.photo)['asset_id']}, **speech(a),
            'motion_prompt': '自然亲和的口播，双手基本放在身前，几乎不抬手，保持冷静从容，微微点头',  # 压手势，避免崩手指
            'expressiveness': 'low', 'aspect_ratio': '9:16', 'resolution': '1080p'}
    submit_and_wait(body, a.out)
else:
    submit_and_wait({'type': 'avatar', 'avatar_id': a.look, **speech(a), 'engine': {'type': 'avatar_v'}}, a.out)
