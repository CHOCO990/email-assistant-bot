# 企业邮箱邮件助理 Skill

从企业邮箱 IMAP 收件箱增量读取新邮件，生成邮件摘要，并通过 SMTP 发送邮件；同时输出一份适合微信推送的精简摘要，供 WorkBuddy 自动化捕获后推送到个人微信。

## 功能

- **增量读取**：通过 IMAP UID 记录上次读取位置，只处理新邮件。
- **智能分类**：自动识别个人来信、账号安全、考试、作业、毕业手续、招聘面试、奖学金等类别。
- **合并去重**：自动合并撤回、更正、更改通知以及同一事项的重复提醒。
- **双通道输出**：
  - 邮件摘要（HTML + 纯文本）通过 SMTP 发送；
  - 微信摘要打印到 stdout，供 WorkBuddy 自动化捕获。
- **重要/一般分组**：微信摘要分为「重要通知」和「一般通知」，重要通知最多 5 项，写清楚「是什么、需要做什么、什么时候截止」。

## 文件说明

```
enterprise-mail-wechat-digest/
├── SKILL.md              # Skill 元数据和主说明
├── README.md             # 本文件（中文使用说明）
├── scripts/
│   └── mail_digest.py    # 核心脚本
├── assets/
│   └── .env.example      # 环境变量模板
└── references/
    └── setup.md          # 详细配置指南与兜底方案
```

## 快速开始

### 1. 复制文件到项目目录

```sh
mkdir ~/mail-digest
cp scripts/mail_digest.py ~/mail-digest/
cp assets/.env.example ~/mail-digest/
cd ~/mail-digest
```

### 2. 配置环境变量

```sh
cp .env.example .env
```

编辑 `.env`，填入真实信息：

```ini
WORK_IMAP_HOST=imap.example.com
WORK_IMAP_PORT=993
WORK_IMAP_USERNAME=you@example.com
WORK_IMAP_PASSWORD=your-imap-password
WORK_IMAP_FOLDER=INBOX

DIGEST_SMTP_HOST=smtp.example.com
DIGEST_SMTP_PORT=465
DIGEST_SMTP_USERNAME=you@example.com
DIGEST_SMTP_PASSWORD=your-smtp-password
DIGEST_TO=you@example.com
```

> **注意**：不要把 `.env` 提交到版本库或粘贴到聊天中。

### 3. 本地测试

```sh
set -a; source .env; set +a
python3 mail_digest.py
```

正常执行后你会收到邮件摘要，同时终端会打印微信版摘要。

## 接入微信 ClawBot（推荐）

### 绑定微信

1. 微信 → **我 → 设置 → 插件 → 微信 ClawBot** → 启用。
2. WorkBuddy → 头像 → **Claw 设置 → 集成 → 微信 ClawBot 集成** → 配置。
3. 用同一个微信账号扫码，状态显示「已绑定」即可。

### 创建 WorkBuddy 自动化

创建一个重复执行的自动化任务：

- **工作目录**：`~/mail-digest`（你的实际项目目录）
- **执行命令**：`set -a; source .env; set +a; python3 mail_digest.py`
- **后续动作**：捕获 stdout 中的微信摘要，通过微信 ClawBot 推送给用户
- **建议时间**：每天 10:00 和 20:00

自动化提示词示例：

```
在 ~/mail-digest 目录执行：set -a; source .env; set +a; python3 mail_digest.py
捕获 stdout 中的微信摘要，通过微信 ClawBot 发送到用户个人微信。
如果脚本失败，报告错误，不要发送陈旧内容。
不要读取或暴露 .env 文件。
```

## 微信摘要输出示例

```
📬 企业邮箱摘要 (2026-10-19 22:30 CST)
邮箱本轮共 3 封新邮件，整理为 2 个事项

🔔 重要通知：
1. 期末考试安排通知
   是什么：各科目考试时间已经公布，请及时查看考场安排并做好准备…
   需要做什么：请根据邮件正文处理；如无明确要求则无需操作。
   什么时候截止：2026-01-10 17:00
2. 周末聚会时间确认
   是什么：这周六晚上七点在老地方聚餐，有空的话记得回复我。
   需要做什么：请根据邮件正文处理；如无明确要求则无需操作。
   什么时候截止：未识别到明确截止时间

📋 一般通知：
1. 图书馆开放时间调整通知
   💡 自下周一起，图书馆开放时间调整为 8:00-22:00。
```

## 兜底方案

如果 ClawBot 不可用，可以用 PushPlus、Server酱、WxPusher 等第三方服务推送。详见 `references/setup.md`。

## 常见问题

**Q：为什么微信没有收到推送？**

1. 检查 WorkBuddy 里 ClawBot 是否仍显示「已绑定」。
2. 确认 WorkBuddy 正在运行（自动化需要 WorkBuddy 在线）。
3. 查看脚本 stdout 是否正常输出摘要。
4. 如果仍不行，考虑先用 PushPlus 等方案兜底。

**Q：可以把多封邮件合并吗？**

脚本已经会自动合并同一事项的重复提醒以及撤回/更正通知。

**Q：能监控多个邮箱吗？**

当前脚本默认只读取一个邮箱。如需多邮箱，可在 `main()` 中追加多个 `Account`。

## 安全提示

- `.env` 文件包含密码，请勿提交到 Git。
- `mail_digest_state.json` 记录读取进度，不要删除。
- 不要向任何人泄露 IMAP/SMTP 授权码。
