<div align="center">

# SeeCut · 网感口播精剪

**An AI editor that watches its own cut — see, cut, loop.**

中文 · [English](README.en.md) · [日本語](README.ja.md)

</div>

**数字人 / 真人口播 → AI 自动精剪成"网感"动效短视频 → 可选推成剪映分层草稿微调。**
一个给 coding agent（Claude Code 等）用的 skill：它自己理解素材、自己去找真证据、自己编排和渲染，再**用 AI 看视频给自己质检、自己迭代**，最后交你肉眼终审。

| 数字人原片（HeyGen AV5 + 豆包配音） | SeeCut 自动精剪后 |
|:---:|:---:|
| https://github.com/user-attachments/assets/6c5c821a-bb8b-48f0-bead-5509425835ce | https://github.com/user-attachments/assets/4702dc92-8bb3-4199-acc0-31fd3d98ae96 |

两条都有声音，点开即可播放。右边的画面由 agent 全程自动完成（真证据截图、卡片、手绘圈注、人像在全屏和小窗之间调度），最后只在剪映里调了音量。原始文件在 [Releases · demo-v1](https://github.com/YeJe-cpu/SeeCut/releases/tag/demo-v1)。

"精剪"不是去气口的粗剪；"口播"是有真人或数字人出镜；"网感"是画面有料、动效跟着每句话走。

---

## 亮点
1. **See：让 AI 真正"看"视频。** Claude、GPT 这类模型通常要先把视频抽成几张图片再看，看不出动效和节奏。SeeCut 接入 Gemini（通过 Antigravity CLI）直接看视频，素材理解和质检都靠它。
2. **看得准：评委是校准过的。** 同一条视频换个提示词，AI 能从"标准"说成"土味"。我们用答案已知的片子测评委，发现"打绝对分"不可靠、"两条比哪条好"才可靠，所以质检用两两对比，交换位置各跑一次都赢才算。
3. **Loop：自己改、自己挑。** 每版先过硬伤检查，再和上一版两两对比，赢了才采纳；最多 3 版，每版必须有肉眼可见的进步。眼睛准了，循环才会越改越好，而不是越改越偏。
4. **找真证据。** 口播提到什么，就去截真的网页、界面、案例当画面证据，禁止用假界面凑满画面。没有额外 B-roll 也能做得有料。
5. **有章法，不是堆特效。** 一套成体系的风格规范：设计令牌 → 组件库 → 编排决策表（"这句话是什么功能 → 画面怎么处理"）→ 逐镜施工单，层层有据。
6. **数字人也给了实打实的做法。** HeyGen AV5 数字分身出人像，**配音不用 HeyGen 内置音色（偏假），改用豆包语音合成**，demo 里的声音就是这么来的。脚本和步骤都在 [digital-human/](digital-human/)。
7. **能在剪映里微调。** 交成片的同时交分层工程包；装了剪映草稿引擎还能直接推成剪映里分轨可改的草稿，音效也能自动配。

## 最快跑通
1. 准备一个文件夹：**一段 20-30 秒竖屏半身口播**（自己拍的就行）+ 3-6 张口播里提到的东西的截图（可选）。
2. 装好下面"核心"部分的环境，运行 `zsh skill/seecut/scripts/preflight.sh`，直到必需项全绿。
3. 把 `skill/seecut` 放进 `~/.claude/skills/`（或你的 agent 的 skills 目录），新开对话：
   ```
   /seecut 素材：<你的文件夹>
   ```
4. 拿到：渲染成片（`~/Downloads`）+ 分层工程包 + 交付报告（每版改了什么、质检结论）。

**先样片、后全片。** 长视频请先拿开头 20-30 秒跑一遍，确认风格和方向没问题再跑全片（素材超过 60 秒时 skill 也会先问你）。一次循环会出 2-3 版，每版都要渲染和 AI 看片对比，一条 25 秒样片目前约 1 小时，片子越长越久。

## 三步流水线
| 步骤 | 做什么 | 说明 |
|---|---|---|
| [第 1 步 · 数字人](digital-human/) | 口播文案 → 配音 → 数字人 → 竖屏口播 A-roll | 我们的做法：豆包配音 + HeyGen 数字人；工具可以换。有真人口播就跳过 |
| [第 2 步 · 网感口播精剪](skill/seecut/) | 素材理解 → 找真证据 → 编排 → HyperFrames 渲染 → AI 质检自迭代 → 交付 | **核心** |
| [第 3 步 · 剪映草稿](jianying/) | 分层工程包 → 剪映里能打开、分轨微调的草稿 | 可选 |

## 开始之前：你需要准备
目前只在 macOS 上实测过。克隆下来交给你的 agent，它会按这里和 `preflight.sh` 帮你装。

**核心：精剪必需**（`preflight.sh` 会逐项检查）
| 内容 | 说明 |
|---|---|
| 一个 coding agent | Claude Code 已实测；Codex、WorkBuddy 等能跑 skill 的 agent 理论上通用。要跑多轮自迭代，额度要充足 |
| **Antigravity CLI（`agy`）** | AI"看视频"的眼睛，**没有它就没有自检和自迭代**。用 Google 账号登录即可，免费账号有按周刷新的额度；Google AI Pro 会员额度更高、每 5 小时刷新（一条片子要调很多次，免费额度可能不够跑完，以[官方说明](https://antigravity.google/docs/plans/)为准）。坑：Google 账号**底层地区**要是支持地区（看账号设置，不看 IP）；国内要代理；无头调用要加 `--dangerously-skip-permissions` |
| HyperFrames CLI | 免费开源，`npx -y hyperframes@latest` 即用；代理要设成**大写** `HTTPS_PROXY` |
| ffmpeg、Node 22+（HyperFrames 要求）、Python 3、`pip install faster-whisper`、工程目录里 `npm i playwright-core` | 均免费，用于渲染、转写、截证据 |

**数字人：要出数字人口播时需要**（工具可以换，下面是我们实际用的）
| 内容 | 说明 |
|---|---|
| 配音：火山引擎·豆包语音 | 比数字人平台的内置音色自然。新应用有免费额度（我们开通时控制台显示约 2 万字符），以[火山引擎控制台](https://console.volcengine.com/speech/service/10035)和官方最新文档为准 |
| 数字人：HeyGen 账号 + API 钱包 | AV4 照片驱动约 $0.04/秒，AV5 数字分身约 $0.12/秒 |

**可选增强**
| 内容 | 用途 |
|---|---|
| jianying-headless（第三方，非商业协议） | 生成剪映分层草稿 |
| 你自己的音效库 | `scripts/sfx_ledger.py` 一键建台账后自动配音效 |
| 一个生图工具 | 缺素材时自动生图补画面；任何生图模型都行，我们手边用的是 Grok CLI |

## 已知卡点
- agy 报 not eligible：Google 账号底层地区不对（改账号设置，不是换 IP）。
- `npx hyperframes` 下载超时：代理没设成大写 `HTTPS_PROXY`。
- 证书报错（CERTIFICATE_VERIFY_FAILED）：本机有代理做了 HTTPS 中间人，给 Python / Node 配上代理的 CA，或改用 curl。
- 数字人：AV5 需要在 HeyGen 网页人工建分身；AV4 只要一张照片，缩成小窗时足够用。
- 剪映：第三方引擎要自己适配；没有它也能拿到成片 + 分层素材。
- 录屏 + 角落头像类型的素材在当前版本没有充分测试，欢迎反馈。
- 一条片子要跑几十分钟到一小时，先用 20-30 秒样片试方向。

遇到问题请开 issue（有模板），附上 preflight 输出和交付报告里的"skill 问题"一节。

## 致谢
这套管线站在这些项目的肩膀上：
- [HyperFrames](https://github.com/heygen-com/hyperframes)：渲染引擎和官方组件库，画面里的大量动效靠它撑起来。
- [video-talkcraft](https://github.com/Vincentwei1021/video-talkcraft)：剪辑管线的整体编排思路（Design Reference → 组件库 → SHOTBOOK）。
- [hypit](https://github.com/hypit-ai/hypit)：爆款拆解的思路，帮助我们理解网感和素材。
- [hyperframes-student-kit](https://github.com/nateherkai/hyperframes-student-kit)：Vox Explainer 风格的设计令牌和卡片样式。
- [jianying-headless](https://github.com/mcncarl/jianying-headless)：剪映草稿引擎。
- [rachel-digital-human-production](https://github.com/Jingyi-Wu-Richael/rachel-digital-human-production)：数字人流程的起点；在它的基础上，我们又实测改进了 AV5 数字分身、豆包配音和竖屏裁切。

感谢这些项目的作者。本仓库包含的第三方组件与字体及其许可见 [NOTICE](NOTICE)。

## 协议
[PolyForm Noncommercial 1.0.0](LICENSE)
