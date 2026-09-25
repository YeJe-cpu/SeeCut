# ★ 口播动效渲染 · 避坑 SOP（一步到位版）

> 定位：**下一个做"口播 + HTML/GSAP 动效 + 逐帧渲染"的窗口/agent，动手前先读这份。** 把 Round2-2 踩过的坑全部前置，照做即可一次到位，别重新踩。
> 适用管线：Vox 卡蒙参考片令牌 → 竖版 HTML/GSAP composition → **无头 Chrome 逐帧捕获** → ffmpeg 合成 + 口播音轨。
> 完整原理见 作者本地过程记录（未收录）（§1-10）；可复现脚本见 作者本地过程记录（未收录）。

---

## 一、端到端正确管线（每步带⚠️坑）

### 0. 素材与转写
- 口播源转写**一次就沉淀**（SRT+逐词JSON），别每版重转。
- ⚠️ 粗剪时间轴 ≠ 全片 main.MOV 时间轴，别套错 SRT。用 ChatCut `preview_timeline` transcript / `find_transcript` 现扒粗剪的精确帧。

### 1. 人像层（A-roll）——★判过一次"卡顿"的坑
- **不要**在 HTML 里用 `<video>` + 每帧 `currentTime` scrub（无头 Chrome 密集 seek 解码器跟不上 → 人像半数帧冻结 = judder）。
- ✅ 正确：`ffmpeg -vf fps=30` 把人像**预抽成逐帧 JPG 序列**，HTML 里用 `<img>`，捕获脚本**每帧换 img.src**。0 冻结、还更快。
- 人像源先规范到 CFR 30fps（`-vf fps=30 -vsync cfr`）。

### 2. 设计层蒙皮（参考片质感）
- 真复制 Vox 卡（student-kit `01-vox-explainer/cards`）+ 覆盖 tokens：**思源黑体 Heavy**(替 Vox 衬线 Fraunces)、砖红/琥珀/青柠色族、点阵纸底。clip-path撕纸/报纸纹/GSAP弹入**原样复用**(守铁律①禁手写神似)。
- ⚠️ Vox 卡是横版 1920×1080，reel 竖版 2160×3840：**复用卡的 CSS/tokens/GSAP 按竖版重排布局**(owner 已判在铁律①内)，别硬塞横卡当带(会犯"卡飘空背景")。
- ⚠️ 荧光笔 wipe：父元素若是 inline，`transform:scaleX` **不生效** → 父元素设 `display:inline-block`；GSAP **不插值 clip-path 的%**，用 scaleX+fromTo。

### 3. 动效对齐（★作者发现的系统性坑，最容易翻车）
- ⚠️**别照句子级时间段的"句首"敲动效时间**。关键词常在句中后段才说出口(整句"海外AI大神从**147**次失败中",147 在句中)，句首锚点=系统性早 1~2 秒。
- ✅ 用 `find_transcript includeWordTimestamps` 拿**逐词精确帧**。把 payoff 元素(数字/高亮/名字/徽章)锚到**词被说出的那一帧**落下(词上或词后 0.1~0.2s，**绝不抢词前**=没揭示感)。背景/铺垫可略早，**句首→关键词的空档 = 揭示前悬念**(先"它有个名字，叫…"吊着，说到"Layer"才砸)。

### 4. 逐帧捕获（★"时间轴漂移"的隐蔽坑）
- ⚠️ 捕获脚本**必须按绝对时间 seek**：`timeline.time(i/fps)`，**不要**用 `progress(i/(N-1))`。
- 原因：GSAP 里任何循环动画(如 grain 噪点 repeat:60)会把时间轴总时长撑长(实测 30.5s ≠ 预期 29.7s)；progress×总时长 ≠ 音频时钟 → 动画比音频快、越后越偏(结尾差 0.8s)。`.time()` 与总时长无关，恒等音频。
- ⚠️ **GSAP `.from`/`.fromTo` 在 seek(非播放)渲染下 immediateRender 会提前揭示元素**(尤其父层做了 autoAlpha 动画时)。要"某时刻才出现"的元素：CSS 默认 `opacity:0`(回落态=隐藏) + `.set` 初始态 + `.to` 揭示(`.to` 无 immediateRender)。
- ✅ **护栏(早发现)**：渲染前自动比对"GSAP 动画钟总长 vs 视频时长"，差 >0.15s 报警(提示循环动效 repeat 设太长/内容超时)。capv3.mjs 已内置。根治靠 `.time()` 绝对 seek，护栏是双保险。

### 5. 合成 + 音轨
- `ffmpeg -framerate 30 -i frames/f%04d.png -i person_cfr.mp4 -map 0:v -map 1:a -shortest out.mp4`。
- 试拼走 1080p 快迭代；字幕/BGM/音效**留 作者剪映**(音效我方无法试听音色、剪映有库可听可换)。

---

## 二、避坑速查表（贴墙版）
| 坑 | 症状 | 正解 |
|---|---|---|
| video 逐帧 scrub | 人像卡顿/冻结 | 预抽 JPG 序列 + img 换 src |
| progress 取帧 | 动效整体偏早、越后越偏 | `.time(i/fps)` 绝对时间 seek |
| 句首锚点 | 动效抢在文案前 | 逐词时间戳锚关键词那帧 |
| `.from` seek 提前显 | 元素早于该出现的时刻 | CSS opacity:0 + `.set` + `.to` |
| inline 父元素 | scaleX/wipe 不动 | 父 `display:inline-block` |
| clip-path % | GSAP 不插值、瞬现 | 用 scaleX + fromTo |
| 横卡塞竖屏 | 卡飘空背景 | 复用零件按竖版重排 |

## 三、验收方法（★别被骗）
- 🔴 **时间维度问题(卡顿/对齐)别信 md5/freezedetect/agy/整帧比对**——画面有逐帧抖动的 grain 噪点会让整帧永远"不同"，骗过所有整帧检测(我早前就被骗、误判修好)。
- ✅ **卡顿**：裁人像区、量连续帧"近冻结帧数"(应=0)。
- ✅ **对齐**：抽"关键词前 0.2s / 词后 0.3s"两帧，确认元素**词前无、词到落**。
- ✅ 终判交**肉眼看播放**(作者)。

## 三.5、★长任务兜底（管线级硬约束，2026-09-20 institutionalize；作者睡觉时被静默空转烧过时间）
> 血泪：geom-check 首版**静默卡死 25 分钟**(每帧 Node↔浏览器往返延迟堆叠)；此前还有渲染僵尸进程、agy 后台子任务卡死。**静默空转在无人值守时(作者睡觉)浪费极大**。凡 playwright/agy/ffmpeg/渲染类长任务，一律套下面三条硬约束：
1. **超时看门狗**：每个长任务带超时 + "N 秒无进展即强制退出并触发失败通知"（自杀式看门狗）。别让任何步骤能无限挂着。
2. **进度可见**：长任务定期打印进度（如全渲每 150 帧打一行；agy 起止打时间戳），能一眼看出"在动还是挂了"。
3. **失败/超时主动冒泡到人**：任务失败或超时要显式报错/发通知，禁"发起后不管"的静默后台；后台任务必须有完成/失败回执。
- **几何自检实现铁律**（这次的具体坑）：**整个逐帧 scrub 塞进浏览器内一次 `page.evaluate` 跑完**(2.7s)，**别每帧一次 Node↔浏览器往返**(942 次往返≈挂死)。呼应 spec"渲染前秒级"。
- 关联记忆 `feedback_long_task_watchdog`。

## 四、关联文件
- 人话版原理复盘：作者本地过程记录（未收录）
- 过程轨(每版迭代)：作者本地过程记录（未收录）
- 可复现脚本：skill 内 `scripts/render.mjs`（逐帧渲染）+ `scripts/geom-check.mjs`（几何自检），配置契约见 `07` §配置契约。
- 决策表/设计令牌/质量地板：本目录 `references/01`-`05`
- 记忆：`reference_headless_video_scrub_judder`、`reference_motion_word_alignment`
