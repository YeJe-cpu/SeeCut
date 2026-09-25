# hf-hw · HF 官方手绘组件的可直接嵌入版

来源：HyperFrames 官方 registry（github.com/heygen-com/hyperframes，Apache-2.0）的 `hw-callout-circle` / `hw-underline` / `hw-arrow` 组件 helper，**原样抽出、去掉了 self-preview**（2-4.1 实测可用，手作感明显好于手写 SVG）。字体 Caveat（OFL）。

## 为什么需要这层
registry 组件是独立 composition 形态（自带预览、自己注册 `__timelines`），不能直接塞进我们的单文件 master。这里已经抽好，拷进工程即可。

## 用法
1. `cp -r <skill>/assets/hf-hw <build>/lib/`
2. master.html：`<link rel="stylesheet" href="lib/hf-hw/hf-hw.css">`，GSAP 之后 `<script src="lib/hf-hw/hf-hw.js"></script>`。
3. 结构和调用照抄 `npx -y hyperframes@latest add hw-callout-circle` 生成的示例 HTML；时间轴里 `tl.set(sel,{opacity:0},0); tl.set(sel,{opacity:1},t); hwCalloutOn(tl, sel, t);`
4. **必须覆盖墨色**（默认 #f4f2ec 是给深色底的，米白底上看不见）：
   `.hw-callout{--hw-co-ink:var(--red);--hw-co-accent:var(--amber);} .hw-arrow{--hw-arrow-color:var(--red);}` 标记线用 `--hw-mark-color`。
5. **callout 的 label 很慢**：外圈→涂鸦→连线画完才弹 label（约 1.4s）。≤2s 的镜头要关掉 scribble、提前起笔，或者不用 label。
6. `hw-arrow` 在 720 宽竖版里默认尺寸偏小，像红点——至少 150px 宽，或换 `hw-underline`。
7. `hw-write-title` 只有 Caveat 拉丁字形，**中文手写做不了**；中文手写气泡目前手搭（在 SHOTBOOK 写明原因）。

## 其它 registry 组件
`npx -y hyperframes@latest catalog` 查全表（需大写 `HTTPS_PROXY`）；装上后若是带自预览的 composition，照本目录的办法抽 helper，并把抽好的版本也补进本目录，下次直接用。
