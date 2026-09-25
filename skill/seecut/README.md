# SeeCut skill（网感口播精剪）

把口播视频（真人或数字人出镜 + 截图/录屏/B-roll）自动剪成网感动效短视频：口播打底，把画面让给高密度信息层（**真实证据** + chip/卡/大字 + 手绘/撕纸/像素手作 + 弹簧动效），人像按"对你说露、给你看藏"调度。

自循环：预检 → 素材理解 → 找真证据 → 编排 → HyperFrames 构建 → 硬门 + 两两对比自迭代（≤3 版）→ 配音效 → 交付 → 你肉眼终审。
交付：**渲染成片 + 分层工程包**；装了剪映引擎再出**剪映分层草稿**（音效放草稿音效轨，成片只带原声），没装则音效混进成片。

## 用法
把本目录放进 `~/.claude/skills/seecut/`，新开对话：
```
/seecut 素材：<你的素材文件夹>
```
素材超过 60 秒时，skill 会先剪开头 20-30 秒样片给你确认，再跑全片。字幕、BGM 请在剪映等编辑器里自己补。

## 依赖
见仓库根目录 README 的"开始之前"；`scripts/preflight.sh` 会逐项检查。

## 结构
```
SKILL.md                    入口：自循环步骤
CHANGELOG.md                规则变更记录
references/
  00-总纲.md                ★最高规则 + 信源优先级（冲突以它为准）
  01-方法论 / 03-编排层决策表   风格拆解结论（"这句话是什么功能 → 画面怎么处理"）
  02-设计令牌               色/字/动效/背景选底规则/人像/素材类型
  04-SHOTBOOK施工规格        逐镜编排（含有据/无据 + 证据计划）
  05-视觉质量地板 / 08-避坑SOP  护栏与渲染铁律
  06-质检闭环spec            硬门 H1/H2 + 两两对比 + 停止条件（含校准实证）
  07-几何规则自检spec         几何规则 + project.json 配置契约
  09-音效规范               落点/映射/对齐/密度音量（配 sfx.py）
  10-剪映分层工程            打标契约/流程/能力边界（配 jianying_layers + jianying_plan）
  prompt/                   对比评委.txt / 硬伤清单.txt
  金锚集/                   可选：你自备的参考片
  sfx/                      你的音效台账放这里（sfx_ledger.py 生成）
assets/hf-hw/               HyperFrames 官方手绘组件（圈注/下划线/箭头）可嵌入版
scripts/
  preflight.sh              开工预检
  render.mjs                逐帧渲染
  geom-check.mjs            几何自检（硬门 H1）
  agy_judge.py              AI 评委：check 硬伤清单 / pair 两两对比（交换位置求共识）
  agy_read.sh               素材理解：agy 读单个文件
  grab_evidence.mjs         截真网页当证据
  sfx.py / sfx_ledger.py    音效：建台账、对齐、检查、混音
  jianying_layers.mjs / jianying_plan.py   分层工程包 → 剪映草稿 plan
  schemas/                  评委 JSON schema
```

说明：文档里的"参考片"指作者拆解时用的同风格样片（不随仓分发）；"作者/维护者"指本仓作者；文中提到的 Round2-x 等是作者本地的测试轮次记录，未收录。
