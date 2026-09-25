#!/usr/bin/env python3
"""把 jianying_layers.mjs 的 manifest（+ 可选 sfx_plan.json）生成剪映分层工程 plan（jy14-headless-plan/v1）。
用法: python3 jianying_plan.py <layers/manifest.json> --name 草稿名 --out plan.json [--sfx sfx_plan.json] [--preview preview.mp4]
轨道：主轨=纸底 PNG；人像轨=按状态切的视频（x/y/scale 线性关键帧做过渡）；信息层=逐元素透明 PNG（不透明度关键帧淡入淡出，
      按 cat 从下到上 evbg→card→cardimg→hl→title→hand，不重叠的段挤进同一轨）；音频=原声 +（可选）音效轨。
坐标约定（2-4.1 实测，作者 UI 验收未报偏差）：scale=1 = 素材"适应画布"；x/y 以半个画布为 1、y 向上为正。
然后用 jianying-draft 引擎：build → verify-build → publish（publish 前剪映主程序须退出、先备份 root_meta_info.json）。
"""
import argparse, json, math, os, subprocess

ap = argparse.ArgumentParser()
ap.add_argument('manifest'); ap.add_argument('--name', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--sfx'); ap.add_argument('--preview')
a = ap.parse_args()
man = json.load(open(a.manifest, encoding='utf-8'))
FPS = man['fps']; CW, CH = man['width'], man['height']
US = lambda f: int(round(f * 1_000_000 / FPS))  # 帧→微秒（30fps 不能用整除，否则 build 报 Source trim exceeds，Round2-4.2 实测）
FR = US(1); TOTAL = US(man['frames'])


def media_us(path):
    return int(float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]).decode()) * 1e6)
ORDER = ['evbg', 'card', 'cardimg', 'hl', 'title', 'hand']
FADE_OUT = 5 * FR


def fit(w, h):
    return min(CW / w, CH / h)


def pos(cx, cy):
    return round((cx - CW / 2) / (CW / 2), 5), round((CH / 2 - cy) / (CH / 2), 5)


# ---------- 人像 ----------
person = []
sts = man['person_states']
for k, st in enumerate(sts):
    x, y, w, h = st['box']; sc = round(w / (w * fit(w, h)), 4); px, py = pos(x + w / 2, y + h / 2)
    seg = {'source': st['file'], 'start_us': US(st['from']), 'duration_us': min(US(st['to'] + 1) - US(st['from']), media_us(st['file'])), 'volume': 0.0}
    if k == 0 or st['anim_frames'] <= 0:
        seg.update(scale=sc, x=px, y=py)
    else:  # 从上一状态的几何线性过渡到本状态
        x0, y0, w0, h0 = sts[k - 1]['box']; qx, qy = pos(x0 + w0 / 2, y0 + h0 / 2); d = st['anim_frames'] * FR
        d = min(d, seg['duration_us'])
        seg['keyframes'] = {'scale': [{'at_us': 0, 'value': round(sc * w0 / w, 4)}, {'at_us': d, 'value': sc}],
                            'x': [{'at_us': 0, 'value': qx}, {'at_us': d, 'value': px}],
                            'y': [{'at_us': 0, 'value': qy}, {'at_us': d, 'value': py}]}
    op = []  # 人像中途隐藏/再出现：不透明度淡入淡出（3 帧）
    if st.get('fade_in') and seg['start_us'] > 0: op += [(0, 0.0), (min(3 * FR, seg['duration_us'] // 2), 1.0)]
    if st.get('fade_out'):
        if not op: op = [(0, 1.0)]
        t = seg['duration_us'] - min(3 * FR, seg['duration_us'] // 2)
        if t > op[-1][0]: op.append((t, 1.0))
        op.append((seg['duration_us'], 0.0))
    if len(op) >= 2:
        seg.setdefault('keyframes', {})['opacity'] = [{'at_us': a, 'value': v} for a, v in op]
    person.append(seg)


# ---------- 信息层 ----------
def seg_of(s):
    # 淡入提前 1 帧起、2 帧淡满：元素在成片出现的那一帧已可见，音效落点对得上画面（2-4.1 实测）
    st = US(max(0, s['start'] - 1)) if s['fade_in'] else US(s['start'])
    d = US(s['end'] + 1) - st
    seg = {'source': s['file'], 'start_us': st, 'duration_us': d}
    kf = []
    if s['fade_in'] and st > 0:
        kf += [(0, 0.0), (min(2 * FR, d // 2), 1.0)]
    if s['fade_out'] and st + d < TOTAL:
        fo = min(FADE_OUT, d // 2)
        if not kf: kf = [(0, 1.0)]
        if d - fo > kf[-1][0]: kf.append((d - fo, 1.0))
        kf.append((d, 0.0))
    if len(kf) >= 2:
        seg['keyframes'] = {'opacity': [{'at_us': t, 'value': v} for t, v in kf]}
    return seg


def pack(items):
    lanes = []
    for sg in items:
        for lane in lanes:
            if lane[-1]['start_us'] + lane[-1]['duration_us'] <= sg['start_us']:
                lane.append(sg); break
        else:
            lanes.append([sg])
    return lanes


tracks = [{'type': 'video', 'segments': [{'source': man['paper'], 'start_us': 0, 'duration_us': TOTAL}]}]
layout = ['主轨: 纸底 PNG（静态，可换底色/底图）']
BELOW_PERSON = ['evbg']  # 证据背景（满屏截图底）在人像下面，其余信息层在人像上面（2-4.1 回归测试发现）
for cat in (BELOW_PERSON + ['__person__'] + [c for c in ORDER if c not in BELOW_PERSON] + sorted({s['cat'] for s in man['segs']} - set(ORDER))):
    if cat == '__person__':
        tracks.append({'type': 'video', 'segments': person})
        layout.append('人像: ' + ' | '.join(f"{s['name']} {s['from'] / FPS:.2f}-{(s['to'] + 1) / FPS:.2f}s" for s in sts))
        continue
    items = sorted([seg_of(s) for s in man['segs'] if s['cat'] == cat], key=lambda g: g['start_us'])
    for n, lane in enumerate(pack(items)):
        tracks.append({'type': 'video', 'segments': lane})
        layout.append(f'信息层 {cat}#{n + 1}: ' + ' | '.join(os.path.basename(g['source'])[5:-4] for g in lane))
if man.get('voice'):
    tracks.append({'type': 'audio', 'segments': [{'source': man['voice'], 'start_us': 0, 'duration_us': TOTAL, 'volume': 1.0}]})
    layout.append('音频: 原声')
sfx = []
if a.sfx:
    sfx = json.load(open(a.sfx, encoding='utf-8'))['items']
    items = sorted([{'source': e['source'], 'start_us': e['at_us'], 'duration_us': e['duration_us'],
                     'source_start_us': e['source_start_us'], 'source_duration_us': e['duration_us'], 'volume': e['volume']} for e in sfx],
                   key=lambda g: g['start_us'])
    for lane in pack(items):
        tracks.append({'type': 'audio', 'segments': lane})
    layout.append(f'音效: {len(sfx)} 个')
plan = {'schema': 'jy14-headless-plan/v1', 'name': a.name, 'canvas': {'width': CW, 'height': CH, 'fps': FPS}, 'tracks': tracks}
json.dump(plan, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(os.path.splitext(a.out)[0] + '_轨道说明.txt', 'w', encoding='utf-8').write('\n'.join(layout) + '\n')
print(f"{a.out}：{len(tracks)} 轨（视频 {sum(t['type'] == 'video' for t in tracks)} / 音频 {sum(t['type'] == 'audio' for t in tracks)}）")

# ---------- 可选：ffmpeg 按同一 plan 合成预览（非剪映原生导出，只供快速看） ----------
if a.preview:
    def lin(kfs, st):
        e = f"{kfs[-1]['value']}"
        for p, q in reversed(list(zip(kfs, kfs[1:]))):
            t0, t1 = st + p['at_us'] / 1e6, st + q['at_us'] / 1e6
            e = f"if(lt(t,{t1:.4f}),{p['value']}+({q['value']}-{p['value']})*(t-{t0:.4f})/{t1 - t0:.4f},{e})"
        return f"if(lt(t,{st + kfs[0]['at_us'] / 1e6:.4f}),{kfs[0]['value']},{e})"
    probe = lambda f, k: int(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', f'stream={k}', '-of', 'csv=p=0', f]).decode().split()[0])
    inputs = ['-loop', '1', '-t', f'{TOTAL / 1e6:.3f}', '-i', man['paper']]; fc = [f'[0:v]format=rgba,scale={CW}:{CH}[b0]']; last, k = 'b0', 1
    for t in tracks[1:]:  # 严格按轨道顺序从下往上叠
        if t['type'] != 'video': continue
        for sg in t['segments']:
            st, d = sg['start_us'] / 1e6, sg['duration_us'] / 1e6
            if t['segments'] is person:
                inputs += ['-itsoffset', f'{st:.3f}', '-i', sg['source']]
                w0, h0 = probe(sg['source'], 'width'), probe(sg['source'], 'height'); f0 = fit(w0, h0); kf = sg.get('keyframes', {})
                S = lin(kf['scale'], st) if 'scale' in kf else str(sg.get('scale', 1))
                X = lin(kf['x'], st) if 'x' in kf else str(sg.get('x', 0))
                Y = lin(kf['y'], st) if 'y' in kf else str(sg.get('y', 0))
                fc.append(f"[{k}:v]scale=w='trunc({w0}*{f0}*({S})/2)*2':h='trunc({h0}*{f0}*({S})/2)*2':eval=frame[p{k}]")
                fc.append(f"[{last}][p{k}]overlay=x='{CW / 2}+({X})*{CW / 2}-w/2':y='{CH / 2}-({Y})*{CH / 2}-h/2':eval=frame:enable='between(t,{st:.3f},{st + d - 0.001:.3f})'[v{k}]")
            else:
                inputs += ['-loop', '1', '-t', f'{st + d:.3f}', '-i', sg['source']]; f = f'[{k}:v]format=rgba'
                op = sg.get('keyframes', {}).get('opacity', [])
                if len(op) >= 2:
                    if op[0]['value'] == 0: f += f",fade=t=in:st={st:.3f}:d={op[1]['at_us'] / 1e6:.3f}:alpha=1"
                    if op[-1]['value'] == 0: f += f",fade=t=out:st={st + op[-2]['at_us'] / 1e6:.3f}:d={(op[-1]['at_us'] - op[-2]['at_us']) / 1e6:.3f}:alpha=1"
                fc.append(f + f'[o{k}]'); fc.append(f"[{last}][o{k}]overlay=0:0:enable='between(t,{st:.3f},{st + d - 0.001:.3f})'[v{k}]")
            last, k = f'v{k}', k + 1
    amap = []
    if man.get('voice'):
        inputs += ['-i', man['voice']]; amap.append(f'[{k}:a]'); k += 1
    for e in sfx:
        inputs += ['-i', e['source']]
        fc.append(f"[{k}:a]atrim=start={e['source_start_us'] / 1e6:.3f}:duration={e['duration_us'] / 1e6:.3f},asetpts=PTS-STARTPTS,"
                  f"volume={20 * math.log10(max(e['volume'], 1e-4)):.1f}dB,adelay={e['at_us'] // 1000}|{e['at_us'] // 1000}[a{k}]")
        amap.append(f'[a{k}]'); k += 1
    audio = []
    if amap:
        fc.append(''.join(amap) + f'amix=inputs={len(amap)}:normalize=0:duration=first[aout]'); audio = ['-map', '[aout]', '-c:a', 'aac', '-b:a', '192k']
    subprocess.check_call(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', ';'.join(fc), '-map', f'[{last}]', *audio,
                           '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-r', str(FPS), '-t', f'{TOTAL / 1e6:.3f}', a.preview])
    print('预览（非剪映原生导出）:', a.preview)
