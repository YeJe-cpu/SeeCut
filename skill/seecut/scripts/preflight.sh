#!/bin/zsh
# 开工预检：缺什么先报，别跑到一半才发现（总纲第11/15条）。用法: zsh preflight.sh [build目录]
ok(){ print "  ✓ $1"; }; bad(){ print "  ✗ $1"; MISS=1; }; warn(){ print "  ⚠ $1"; }
print "=== SeeCut 预检 ==="
command -v ffmpeg >/dev/null && ok ffmpeg || bad "ffmpeg（brew install ffmpeg）"
if command -v node >/dev/null; then NV=$(node -v | sed 's/v//;s/\..*//'); [ "$NV" -ge 22 ] && ok "node $(node -v)" || bad "node $(node -v) 太旧（HyperFrames 要求 ≥ 22）"; else bad "node（≥ 22）"; fi
python3 -c "import faster_whisper" 2>/dev/null && ok faster_whisper || bad "faster_whisper（pip install --user faster-whisper）"
AGY=$(command -v agy || echo ~/.local/bin/agy); [ -x "$AGY" ] && ok "agy $($AGY --version 2>/dev/null | head -1)" || bad "agy（Antigravity CLI，见 README）"
[ -n "$https_proxy$JIANJI_PROXY" ] && ok "代理 ${JIANJI_PROXY:-$https_proxy}" || warn "未设代理（agy/海外截图需要：export JIANJI_PROXY=http://127.0.0.1:1087）"
ls ~/Library/Caches/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell >/dev/null 2>&1 && ok "无头 Chrome（ms-playwright 缓存）" || warn "无 ms-playwright headless shell（设 JIANJI_CHROME 指向现成 Chrome，别新下）"
[ -n "$JIANJI_PROXY" ] && export HTTPS_PROXY=${HTTPS_PROXY:-$JIANJI_PROXY} HTTP_PROXY=${HTTP_PROXY:-$JIANJI_PROXY}   # hyperframes CLI 只认大写
if command -v hyperframes >/dev/null; then ok "hyperframes CLI（全局）"
elif HV=$(perl -e 'alarm 60; exec @ARGV' npx -y hyperframes@latest --version 2>/dev/null); then ok "hyperframes CLI（npx，$HV）→ 用 npx -y hyperframes@latest catalog/add"
else bad "hyperframes CLI 不可用（npx 也失败：查代理，需大写 HTTPS_PROXY）→ 官方组件库用不了，先修再开工"; fi
JY=${JIANYING_HEADLESS_ROOT:-<未设置>}
[ -f "$JY/engine/jy14_headless.py" ] && ok "剪映草稿引擎（$JY）→ 交剪映分层草稿" || warn "没有剪映草稿引擎（可选，github.com/mcncarl/jianying-headless，非商业协议）→ 只交成片(带音效) + 分层工程包"
SD=${JIANJI_SFX_DIR:-$HOME/Downloads/音效}
[ -d "$SD" ] && ok "音效库 $SD（$(ls "$SD" | wc -l | tr -d ' ') 个）" || warn "音效库 $SD 不存在 → 设 JIANJI_SFX_DIR；自己的库先跑 scripts/sfx_ledger.py 建台账"
if [ -n "$1" ]; then
  [ -f "$1/project.json" ] && ok "project.json" || bad "$1/project.json（配置契约见 references/07）"
  node -e "require.resolve('playwright-core',{paths:['$1']})" 2>/dev/null && ok "playwright-core（工程目录）" || bad "playwright-core：cd $1 && npm i playwright-core（别 sudo）"
fi
[ -z "$MISS" ] && print "✅ 必需项齐全" || print "❌ 有必需项缺失，先装再开工（或报告用户）"
