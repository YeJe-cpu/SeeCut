---
name: seecut
description: 网感口播精剪（v3.2）：口播视频加动效，自动剪成"网感口播精剪风格"竖版/横版样片，交付渲染成片+分层工程包（装了剪映引擎则再出剪映分层草稿，音效放草稿；没装则音效混进成片）。当用户给了口播粗剪(+B-roll/截图/录屏)并想要"口播动效/加卡片弹字/剪成短视频/做动效样片/网感口播精剪"时用。自循环:预检→素材理解→找真证据→编排→HyperFrames构建→硬门+两两对比自迭代(≤3版)→配音效→交付→用户终审。不做:纯字幕/纯配音/纯生图/BGM。
---

# SeeCut v3.2 · 网感口播精剪（口播动效自动剪辑）

把口播粗剪 + 素材，剪成"网感口播精剪风格"动效样片：数字人/真人口播打底，把画面让给高密度信息层（**真实证据** + chip/卡/大字 + 手作质感 + 弹簧动效），人像按"对你说露、给你看藏"调度。**你（执行窗）自己跑完整循环，交两份东西给用户终审：渲染成片（原声，不混音效）+ 剪映分层草稿（带音效轨）。长任务每 15 分钟往 runlog 写一行进度。**

## 0 · 开工前（必做）
1. **读** `references/00-总纲.md`（16 条，全 skill 最高规则；其它文件与它冲突时以它为准并在报告里指出）+ `references/08-避坑SOP.md`（渲染铁律）。
2. **预检**：`export JIANJI_PROXY=http://127.0.0.1:1087` 后 `zsh scripts/preflight.sh` —— 必需项缺失就先装或报告用户，别跑到一半才发现。hyperframes CLI 走 npx，是必需项（官方组件库靠它）。
3. 建工程目录（素材、`build/`、`qc/`、文档都放这里），`cd build && npm i playwright-core`（别 sudo）。
4. **先样片后全片**：素材超过 60 秒时，先截开头 20-30 秒跑完整循环出样片，交用户确认风格和方向后再跑全片（一次循环会出 2-3 版，全片耗时随时长和版本数一起涨，方向错了代价很大）。用户明确说直接出全片则跳过。

## 1 · 素材理解 → `素材台账.md`
- **视频素材**用 agy 读：`zsh scripts/agy_read.sh <文件> "<问题>"`（已含新项目隔离、超时、禁 OCR 子任务；长视频先切 ≤25s 段、降 540p），别只抽帧。**图片素材**执行窗自己读图（更准，也顺便逐张核敏感字、记 fp-manifest）。
- 判人像素材类型（`02` §6.5）：①半身口播（真人或数字人完整半身 A-roll）/ ②角落圆 PIP / ③点缀型数字人。
- 若 `references/金锚集/` 里有你自备的参考片，按功能挑 1-2 条看一遍；没有就跳过。

## 2 · 转写 → 词级时间轴
faster_whisper(small) 词级转写 → `seg_words.json`，转一次就沉淀。动效锚关键词被说出的那一帧（非句首）。

## 3 · 找真证据（v2 新增，参考片密度的来源）
- 逐句标"有据/无据"：提到真实产品/网页/文档/数据/操作 = 有据。
- 有据句按顺序拿证据：用户素材 → `node scripts/grab_evidence.mjs <素材目录> <url>...` 截真网页（在 build/ 下或工程根目录跑都行）→ 自己录屏；3D 比喻/场景图可 Grok 生成（不能当"真界面"用）。
- **每张截图入片前读图核敏感字**（总纲第 7 条），同时把图里看得清的字逐行记进 `build/fp-manifest.txt`（评委指纹核要用）；拿不到的列进"证据缺口清单"（`04` 第3步），按 `02` §3 第4条退回无据打法。
- **禁假证据**：不许用占位窗口/伪代码网格/假 Mac/假 App 界面冒充或"填满"（总纲第 5 条）。

## 4 · SHOTBOOK 编排（`references/04-SHOTBOOK施工规格.md`）
逐镜填：功能（`03` 决策表）→ 有据/无据 + 证据计划 → 人像层/信息层 → 选卡（**必须写 registry 组件名或"库里没有：原因"**，`npx -y hyperframes@latest catalog`；手绘件用 `assets/hf-hw/`）→ 背景底（`02` §3：有据铺真证据、无据半身或干净底）→ 镜内变化 → 动效 → 衔接。

## 5 · 构建（HyperFrames HTML/GSAP，守 08 避坑SOP）
- 人像 ffmpeg 预抽逐帧 JPG + `<img>` 换 src（禁 video scrub）；GSAP 主时间轴暴露为 `window.__timelines.master`；某刻才出现的元素 CSS `opacity:0` + `.set`/`.to`（禁 `.from`）。
- 给元素打标 `data-check="box|bg"` / `data-anchor` / `data-word`+`data-t`（几何自检用），**以及 `data-layer`/`data-layer-cat`（剪映分层用，契约见 `10`）**；写 `build/project.json`（契约见 `07` §配置契约，另加 `"source": 口播源片路径`）。
- 渲染：`node scripts/render.mjs build probe`（抽帧看）→ `full` → ffmpeg 合成源音轨。**迭代中间版用 `RENDER_SCALE=0.5`**（实测快一倍）；**终版分辨率 = 源片分辨率**：构图按 720 宽写、源片 1080 宽时，在 project.json 写 `"output_scale": 1.5`，终版不设 RENDER_SCALE 就按它出。

## 6 · 质检闭环（`references/06-质检闭环spec.md`）
每版 vN：
1. **硬门 H1**：`node scripts/geom-check.mjs build`（撞位/压人像/圈锚/无脸/抢拍/弹簧）→ 有 FAIL 先改。
2. **硬门 H2**：`python3 scripts/agy_judge.py check --video vN.mp4 --html build/master.html --out qc/vN-check.json`（假证据/版面/人像乱跳/读不完/敏感字/空拍）→ 有 FAIL 先改；agy 报的 FAIL 先抽帧核实。
3. **采纳判定**：`python3 scripts/agy_judge.py pair --a vN.mp4 --b vN-1.mp4 --html-a ... --out qc/vN-vs-prev.json` → consensus=A 采纳；B 回退；tie 平手。
4. **找方向**：`pair --a vN.mp4 --b <同类参考片>`，只读各维度差距证据当下一版改动清单。`金锚集/` 里没有参考片时，改为拿 `03` 决策表 + `05` 质量地板逐条对照 vN，列出差距最大的 1-2 处当改动清单。
5. **停**：硬门全过 且（对比不胜上一版 或 到 **v3** 或 只剩肉眼看不出的小修补）→ 进入交付。每一版必须至少改一处第4步找出的大差距，小修补合并进同一版。**不追任何百分比，不自判"够了"，也不无限死磕**；卡住就带证据报告用户。
**agy（Antigravity）是必需项**：AI 看视频做质检和自迭代是本管线的核心，不提供无 agy 的降级模式；preflight 里 agy 不通就先修好再开工。
（代理：`export JIANJI_PROXY=http://127.0.0.1:1087` 或按本机 VPN 端口。agy_judge 退出码 2=无结果、3=agy 要重新登录→停下找用户。）

## 7 · 音效（`references/09-音效规范.md`）
1. 从 `jianying/layers/manifest.json` 的 `events`（先跑第 8 步的 `jianying_layers.mjs`）+ SHOTBOOK 语义挑落点，写 `sfx_choices.json`（开头 0.5 秒内必须有一个 `hook`）。
2. `python3 scripts/sfx.py plan --choices sfx_choices.json --voice jianying/layers/原声.m4a --words seg_words.json --fps <帧率> --duration <秒> --out sfx_plan.json` → 有 ⚠ 就改 choices 重跑（压字可在 choices 里给该条写 `"gain_db": -3`）。
3. 有剪映引擎：音效只进剪映草稿（第 8 步 `--sfx`），成片只带原声。**没有剪映引擎：`python3 scripts/sfx.py mix --plan sfx_plan.json --video 成片.mp4 --out 成片_带音效.mp4`**，交带音效的成片。
- 用户自己的音效库：`python3 scripts/sfx_ledger.py <音效文件夹> --out 台账.json [--listen]` 生成台账，之后 `sfx.py plan` 加 `--ledger 台账.json --sfx-dir <音效文件夹>`。

## 8 · 分层工程包 → 剪映分层草稿（`references/10-剪映分层工程.md`；剪映引擎可选，没装就交分层工程包 + plan，跳过第 3 步）
1. `node scripts/jianying_layers.mjs build` → 纸底 / 人像分状态视频 / 信息层透明 PNG / 原声 / 候选事件。
2. `python3 scripts/jianying_plan.py jianying/layers/manifest.json --name "<片名>_分层工程" --out jianying/plan.json --sfx sfx_plan.json --preview jianying/preview.mp4` → 预览和成片同时间点抽帧对比。
3. jianying-draft 引擎 build → verify-build → publish（剪映主程序须退出；先备份 root_meta_info.json；publish 后核对首页 +1、原有条目未变）。

## 9 · 交付
- `~/Downloads/<片名>_vN.mp4`（渲染成片，全分辨率；有剪映引擎时只带原声，没有时带音效）+ 分层工程包（`jianying/`）+（有剪映引擎时）剪映首页「<片名>_分层工程」草稿（带音效轨）。ffmpeg 预览若也放出来，文件名注明"非剪映原生导出"。
- 报告（`06` §六）：每版硬门与对比结论 + 改了什么；证据拿到/没拿到 + 敏感字核查 + 截图打码核查；音效清单与 ⚠ 处理；剪映草稿轨道说明；agy 误报清单；需要用户定的主观项。**用户肉眼终审为准。**

## 依赖
见 `README.md`。改规则请改 `references/00-总纲.md` 或对应文件并记 `CHANGELOG.md`。
