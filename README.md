# WeCom Mail Digest with WeChat Auto Push Skill

Incrementally reads new mail from an enterprise IMAP inbox, generates a digest, sends it via SMTP, and prints a WeChat-friendly summary to stdout so WorkBuddy automations can push it to a personal WeChat account.

## Features

- **Incremental reading**: Tracks the last read IMAP UID and only processes new messages.
- **Smart classification**: Automatically recognizes personal mail, account security, exams, homework, graduation procedures, recruitment/interviews, scholarships, and more.
- **Deduplication & merging**: Automatically merges withdrawn messages, corrections, updates, and duplicate reminders for the same matter.
- **Dual-channel output**:
  - Email digest (HTML + plain text) sent via SMTP.
  - WeChat summary printed to stdout for WorkBuddy automation capture.
- **Important / general split**: The WeChat summary separates "Important Notifications" (max 5 items) from "General Notifications", with each important item describing **what it is**, **what to do**, and **the deadline**.

## File Structure

```
enterprise-mail-wechat-digest/
├── SKILL.md              # Skill metadata and primary instructions
├── README.md             # This file (English usage guide)
├── README_CN.md          # Chinese usage guide
├── scripts/
│   └── mail_digest.py    # Core script
├── assets/
│   └── .env.example      # Environment variable template
└── references/
    └── setup.md          # Detailed setup guide and fallback options
```

## Quick Start

### 1. Copy Files to Your Project Directory

```sh
mkdir ~/mail-digest
cp scripts/mail_digest.py ~/mail-digest/
cp assets/.env.example ~/mail-digest/
cd ~/mail-digest
```

### 2. Configure Environment Variables

```sh
cp .env.example .env
```

Edit `.env` and fill in your real credentials:

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

> **Note**: Never commit `.env` or paste it into chat.

### 3. Test Locally

```sh
set -a; source .env; set +a
python3 mail_digest.py
```

You should receive the email digest, and the terminal should print the WeChat summary.

## Connect WeChat ClawBot (Recommended)

### Bind WeChat

1. WeChat → **Me → Settings → Plugins → WeChat ClawBot** → Enable.
2. WorkBuddy → Avatar → **Claw Settings → Integrations → WeChat ClawBot Integration** → Configure.
3. Scan the QR code with the same WeChat account used to log in to WorkBuddy.
4. Confirm the status shows "Bound".

### Create a WorkBuddy Automation

Create a recurring automation task:

- **Working directory**: `~/mail-digest` (your actual project directory)
- **Command**: `set -a; source .env; set +a; python3 mail_digest.py`
- **Follow-up action**: Capture the stdout WeChat summary and push it to the user's personal WeChat via ClawBot
- **Suggested schedule**: Daily at 10:00 and 20:00

Example automation prompt:

```
Run in ~/mail-digest: set -a; source .env; set +a; python3 mail_digest.py
Capture the stdout WeChat summary and send it to the user's personal WeChat via WeChat ClawBot.
If the script fails, report the error and do not send stale content.
Do not read or expose the .env file.
```

## WeChat Summary Example

```
📬 Enterprise Mail Digest (2026-10-19 22:30 CST)
3 new emails this round, merged into 2 items

🔔 Important Notifications:
1. Final Exam Schedule Notice
   What it is: The exam timetable has been announced. Please check the exam room arrangements and prepare in advance...
   What to do: Handle according to the email body; no action needed if no explicit requirement.
   Deadline: 2026-01-10 17:00
2. Weekend Gathering Confirmation
   What it is: Dinner at the usual place at 7 PM this Saturday. Please reply if you are free.
   What to do: Handle according to the email body; no action needed if no explicit requirement.
   Deadline: No clear deadline identified

📋 General Notifications:
1. Library Opening Hours Adjustment
   💡 Starting next Monday, library hours are adjusted to 8:00-22:00.
```

## Fallback Options

If ClawBot is unavailable, you can push the same stdout summary through third-party services such as PushPlus, ServerChan, or WxPusher. See `references/setup.md` for code examples.

## FAQ

**Q: Why didn't I receive the WeChat push?**

1. Check whether ClawBot still shows "Bound" in WorkBuddy.
2. Make sure WorkBuddy is running (automations require WorkBuddy to be online).
3. Verify the script stdout prints the summary correctly.
4. If it still doesn't work, use a fallback service like PushPlus.

**Q: Can it merge multiple emails?**

Yes. The script already merges duplicate reminders and withdrawn/correction notices for the same matter.

**Q: Can it monitor multiple mailboxes?**

By default, the script reads one mailbox. To support multiple mailboxes, add more `Account` instances in `main()`.

## Security Notes

- `.env` contains passwords; do not commit it to Git.
- `mail_digest_state.json` tracks reading progress; do not delete it.
- Never share your IMAP/SMTP authorization codes with others.
