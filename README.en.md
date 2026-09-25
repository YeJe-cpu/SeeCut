<div align="center">

# SeeCut

**An AI editor that watches its own cut — see, cut, loop.**

[中文](README.md) · English · [日本語](README.ja.md)

</div>

**Talking-head video (real person or AI avatar) → an automatically edited, high-energy short video with motion graphics → optionally pushed into a layered JianYing (CapCut China) draft for fine-tuning.**
SeeCut is a skill for coding agents such as Claude Code. The agent understands your footage, finds real on-screen evidence, plans and renders every shot, then **watches its own output with a video-native AI to review and improve it**, and finally hands it to you for the last look.

| Raw AI-avatar footage (HeyGen AV5 + Doubao TTS voice) | After SeeCut |
|:---:|:---:|
| https://github.com/user-attachments/assets/6c5c821a-bb8b-48f0-bead-5509425835ce | https://github.com/user-attachments/assets/4702dc92-8bb3-4199-acc0-31fd3d98ae96 |

Both videos have sound; click to play. Everything on the right was produced by the agent (real screenshots as evidence, cards, hand-drawn callouts, the speaker moving between full screen and picture-in-picture); only the volume was adjusted afterwards in JianYing. Original files: [Releases · demo-v1](https://github.com/YeJe-cpu/SeeCut/releases/tag/demo-v1). The demo is in Chinese.

The skill's own docs (under `skill/`, `digital-human/`, `jianying/`) are written in Chinese. Your agent reads them fine; ask it to explain anything you need.

---

## Highlights
1. **See: the AI actually watches the video.** Models like Claude and GPT usually have to look at a few frames extracted from a video, which can't show motion or pacing. SeeCut uses Gemini (through the Antigravity CLI) to watch video directly, both to understand the footage and to review its own cuts.
2. **Seeing accurately: a calibrated judge.** Change the prompt and the same AI will call one video "polished" or "tacky". We tested the judge on videos with known answers: absolute scores were unreliable, while "which of these two is better" was reliable. So every review is a pairwise comparison, run twice with the order swapped, and a version only wins if it wins both times.
3. **Loop: it edits and chooses by itself.** Each version must pass hard checks, then beat the previous version head-to-head before it is adopted. At most 3 versions, each with a visible improvement. With an accurate eye, the loop gets better instead of drifting.
4. **Real evidence, not fake UI.** Whatever the speaker mentions, the agent captures the real web page, product screen or example as visual evidence. Mock interfaces used to "fill the frame" are forbidden. You get a rich video even without extra B-roll.
5. **A method, not a pile of effects.** A structured style system: design tokens → component library → an editing decision table ("what is this sentence doing → how should the frame handle it") → a shot-by-shot build sheet.
6. **A real, reproducible AI-avatar recipe.** HeyGen AV5 digital twin for the picture; for the voice, **not HeyGen's built-in voices (they sound artificial) but Doubao (ByteDance) TTS**. That is how the demo was made. Scripts and steps are in [digital-human/](digital-human/).
7. **Editable in JianYing.** Besides the rendered video you get a layered project package; with the optional draft engine installed it becomes a JianYing draft with separate tracks you can adjust, including auto-placed sound effects.

## Quick start
1. Make a folder with **a 20–30 s vertical, half-body talking-head clip** (a phone recording is fine) plus, optionally, 3–6 screenshots of things you mention.
2. Install the "Core" items below and run `zsh skill/seecut/scripts/preflight.sh` until all required checks pass.
3. Copy `skill/seecut` into `~/.claude/skills/` (or your agent's skills folder), open a new conversation and run:
   ```
   /seecut 素材：<your folder>
   ```
   (`素材` means "footage".)
4. You get: the rendered video (in `~/Downloads`), a layered project package, and a delivery report (what changed in each version and the review results).

**Sample first, then the full video.** For longer footage, run the first 20–30 seconds, confirm the style and direction, then run the whole thing (the skill will ask you first when the footage is longer than 60 s). One loop produces 2–3 versions, each rendered and reviewed by the AI, so a 25-second sample currently takes about an hour, and longer videos take longer.

## Three-step pipeline
| Step | What it does | Notes |
|---|---|---|
| [1 · AI avatar](digital-human/) | Script → voice → avatar → vertical talking-head A-roll | What we use: Doubao TTS + HeyGen; the tools are swappable. Skip if you record yourself |
| [2 · SeeCut edit](skill/seecut/) | Understand footage → find real evidence → plan → render with HyperFrames → AI review loop → deliver | **Core** |
| [3 · JianYing draft](jianying/) | Layered package → a draft you can open and adjust track by track in JianYing | Optional |

## Before you start
Tested on macOS only so far. Clone the repo and hand it to your agent; it can install things following this section and `preflight.sh`.

**Core: required for editing** (checked by `preflight.sh`)
| Item | Notes |
|---|---|
| A coding agent | Claude Code is tested; Codex, WorkBuddy and other skill-capable agents should work in principle. The self-review loop makes many calls, so make sure you have enough quota |
| **Antigravity CLI (`agy`)** | The AI's eyes. **Without it there is no self-review and no loop.** A Google account is enough: free accounts get a weekly quota; Google AI Pro gets a higher quota that refreshes every 5 hours (one video needs many calls, so the free quota may not last a full run; see the [official plans page](https://antigravity.google/docs/plans/)). Gotchas: the Google account's **country setting** must be a supported region (the account setting, not your IP); headless calls need `--dangerously-skip-permissions` |
| HyperFrames CLI | Free and open source, runs via `npx -y hyperframes@latest`. Behind a proxy, set the **uppercase** `HTTPS_PROXY` |
| ffmpeg, Node 22+ (required by HyperFrames), Python 3, `pip install faster-whisper`, `npm i playwright-core` in the project folder | All free; used for rendering, transcription and capturing evidence |

**AI avatar: needed when you generate avatar footage** (the tools are swappable; these are what we use)
| Item | Notes |
|---|---|
| Voice: Volcengine · Doubao Speech | Sounds more natural than avatar platforms' built-in voices. New apps get a free quota (about 20,000 characters as shown in the console when we signed up); check the [Volcengine console](https://console.volcengine.com/speech/service/10035) and the latest official docs |
| Avatar: HeyGen account + API wallet | AV4 from a photo ≈ $0.04/s; AV5 digital twin ≈ $0.12/s |

**Optional extras**
| Item | Used for |
|---|---|
| jianying-headless (third party, non-commercial license) | Building layered JianYing drafts |
| Your own sound-effect library | `scripts/sfx_ledger.py` indexes it, then effects are placed automatically |
| An image generator | Fills gaps when footage is missing; any image model works, we happen to use Grok CLI |

## Known issues
- `agy` says "not eligible": the Google account's country setting is not supported (change the account setting; a VPN won't help).
- `npx hyperframes` times out: the proxy isn't set as uppercase `HTTPS_PROXY`.
- `CERTIFICATE_VERIFY_FAILED`: a local proxy is intercepting HTTPS; add its CA for Python/Node, or use curl.
- AI avatar: AV5 requires creating the digital twin manually on the HeyGen website; AV4 only needs one photo and is good enough when the speaker is shown small.
- JianYing: the third-party engine needs to be set up on your machine; without it you still get the video and the layered assets.
- Screen recording + corner webcam footage has not been tested much in this version. Feedback welcome.
- One video takes from tens of minutes to an hour; try the direction on a 20–30 s sample first.

Please open an issue (there is a template) with your preflight output and the "skill issues" section of the delivery report.

## Acknowledgements
This pipeline stands on the shoulders of:
- [HyperFrames](https://github.com/heygen-com/hyperframes): the rendering engine and official component library behind much of the motion on screen.
- [video-talkcraft](https://github.com/Vincentwei1021/video-talkcraft): the overall editing-pipeline structure (Design Reference → component library → SHOTBOOK).
- [hypit](https://github.com/hypit-ai/hypit): its approach to breaking down viral videos helped us understand what makes footage feel native to the feed.
- [hyperframes-student-kit](https://github.com/nateherkai/hyperframes-student-kit): the Vox Explainer-style design tokens and card styling.
- [jianying-headless](https://github.com/mcncarl/jianying-headless): the JianYing draft engine.
- [rachel-digital-human-production](https://github.com/Jingyi-Wu-Richael/rachel-digital-human-production): the starting point of our AI-avatar workflow; on top of it we tested and improved the AV5 digital twin, the Doubao voice and vertical cropping.

Thanks to the authors of these projects. Third-party components and fonts included in this repository, and their licenses, are listed in [NOTICE](NOTICE).

## License
[PolyForm Noncommercial 1.0.0](LICENSE)
