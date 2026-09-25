#!/bin/zsh
# 素材理解用：让 agy 读一段视频/图片，自带新项目隔离 + 超时 + 代理。
# 用法: zsh agy_read.sh <素材文件> "<要它回答什么>" [超时秒=540] > 输出.txt
# 长视频先 ffmpeg 切 ≤25s 段并降 540p；prompt 已自动追加"禁后台 OCR/转录子任务"。
F="$1"; Q="$2"; T="${3:-540}"
[ -f "$F" ] || { echo "用法: agy_read.sh <文件> \"<问题>\" [超时秒]"; exit 2; }
[ -n "$JIANJI_PROXY" ] && export https_proxy=$JIANJI_PROXY http_proxy=$JIANJI_PROXY HTTPS_PROXY=$JIANJI_PROXY HTTP_PROXY=$JIANJI_PROXY
D=$(mktemp -d -t jianji_read); cp "$F" "$D/"; N=$(basename "$F")
AGY=$(command -v agy || echo ~/.local/bin/agy)
cd "$D" && perl -e "alarm $((T+60)); exec @ARGV" "$AGY" -p "看 @$N 。$Q
直接凭观看作答，禁止启动任何后台 OCR/转录/采样子任务，不要读取其它文件。" --new-project --add-dir . --model gemini-3.8-flash-high --dangerously-skip-permissions --print-timeout ${T}s
RC=$?; rm -rf "$D"; exit $RC
