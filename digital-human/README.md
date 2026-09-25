# 第 1 步（可选）· 数字人口播 A-roll

流程：口播文案 →（豆包）配音 mp3 →（HeyGen）数字人竖屏口播 mp4 → 交给第 2 步精剪。用别的数字人工具也行，只要最后是一条竖屏半身口播 mp4。

**有自己拍的口播就跳过这步**，直接进第 2 步。想先跑通最小闭环的，也建议先拿一段自己拍的 20-60 秒竖屏半身口播试。

## 两种方案
| | 基础：AV4（照片驱动） | 进阶：AV5（数字分身） |
|---|---|---|
| 你要准备 | 一张清晰正脸半身照（自己的或生成的） | 在 HeyGen 网页建好数字分身：上传 15-600 秒真人训练视频 + 摄像头现录授权（consent） |
| 像不像 | 脸忠实原图，动起来五官会漂、动作少 | 高，口型和微表情从你的视频学来 |
| 价格（参考） | 约 $0.04/秒 | 约 $0.12/秒 |
| 够不够用 | **够**：精剪里人像大多缩成小窗、不常全屏，AV4 的瑕疵大都看不出来 | 更真，做系列内容推荐 |

## 准备
1. HeyGen 账号 → Settings → API 拿 key，`export HEYGEN_API_KEY=...`（**别写进任何文件或仓库**）。
2. API 钱包充值（最低 $5）。**不需要**网页的月度订阅。**余额不足也会照扣钱，而且任务不能取消** → 提交前先 `python3 heygen_avatar.py balance`，一次只交一个任务。
3. 口播音频：推荐先用豆包语音合成配好音（见下面"配音"一节），也可以用自己的录音或别的 TTS。HeyGen 内置音色听起来偏假，分身自带的克隆声往往不稳，我们都没用。
4. AV5 另外：网页 `Avatars → Clone a Real Person` → 上传训练视频 → 现录 consent → 等训练完成。训练视频要求：竖版、单人正对镜头连续说话、光线均匀，**手和麦克风别挡嘴**（否则生成时口型穿帮）。

## 配音（豆包语音合成）
demo 里的声音不是 HeyGen 的，是先用豆包 TTS 配好音，再拿这段音频驱动数字人。

**开通**（一次性）
1. [火山引擎控制台 →「豆包语音」](https://console.volcengine.com/speech/service/10035) → 新建应用，开通"豆包语音合成模型"的试用包。
2. 同一页的"服务接口认证信息"里拿 **AppID** 和 **Access Token**。
3. 坑：开了试用包后，音色列表可能还是空的，要再点"开通服务试用"把音色激活，否则调不通。
4. 额度：新应用有免费额度，我们开通时控制台显示约 2 万字符，具体以控制台和火山引擎官方最新文档为准。一条 20 秒口播约 100 字，够试很多条。

**生成**
```bash
export VOLC_APPID=... VOLC_ACCESS_TOKEN=...          # 别写进任何文件或仓库
python3 doubao_tts.py --file 文案.txt --out 口播.mp3   # 一行一句，逐句合成后拼接
```
- 默认音色 `zh_male_liufei_uranus_bigtts`（男声），语速 1.1，就是 demo 用的。换音色用 `--voice`，音色 id 在控制台音色列表里查。
- 逐句合成更稳：一次塞太长的文案容易超字数，连发太快会被瞬时限流（报错就等几秒重跑）。
- 合成完建议听一遍，或用 whisper 转写核对有没有漏句。

## 出片
```bash
python3 heygen_avatar.py balance
python3 heygen_avatar.py av4 --photo 我.png --audio 口播.mp3 --out a_roll.mp4        # 基础
python3 heygen_avatar.py looks --avatar-group <分身组 id>                           # 进阶：先找 look id
python3 heygen_avatar.py av5 --look <LOOK_ID> --audio 口播.mp3 --out a_roll.mp4     # 进阶
```
输出统一是竖屏 mp4（AV5 目前默认出横屏、人像在中间，脚本会自动裁回竖屏），直接当第 2 步的素材。

## 常见坑
- 手一抬就崩手指（AV4）：脚本已用 `motion_prompt` 压手势 + `expressiveness: low`；还崩就剪辑时缩小人像或裁掉手。
- `dimension` 字段会被接口拒：别加，竖屏靠脚本后处理。
- 上传音频必须用 multipart 的 `file` 字段（脚本已处理）。
- 更多参数和最新接口以 HeyGen 官方文档为准（https://docs.heygen.com），让你的 agent 去查即可。

## 我们实际是怎么做的（上面 demo 的那条数字人）
- **训练片**：自己的口播原片前 45 秒，竖版 1080×1920，单人正对镜头连续说话，手和麦克风不挡嘴（第一版 30 秒训练片手持麦在嘴边，生成的口型穿帮，换掉后正常）。
- **建分身**：HeyGen 网页 `Clone a Real Person` → 上传训练片 → 摄像头现录 consent → 训练完成后得到竖版 720×1280 的 look。
- **配音**：没用 HeyGen 内置音色和分身克隆声，另用豆包语音合成（`zh_male_liufei_uranus_bigtts`，语速 1.1）把 110 字文案配成 17.9 秒 mp3：`python3 doubao_tts.py --file 文案.txt --out 口播.mp3`。
- **出片**：`heygen_avatar.py av5 --look <你的 look> --audio 口播.mp3`（引擎 avatar_v）。接口默认出 1280×720 横屏、人像在中间，脚本自动裁回竖屏。
- **花费**：这一条约 $2（从钱包余额差推算）。
- 然后把这条竖屏 mp4 当素材交给第 2 步精剪，就是上面的 demo。
