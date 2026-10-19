---
name: enterprise-mail-wechat-digest
description: Collect new mail from enterprise IMAP accounts, generate a categorized digest, and push a WeChat-friendly summary to a personal WeChat account via WorkBuddy's ClawBot integration or other push channels. Use this skill when the user wants to build a recurring email digest that is delivered to WeChat.
agent_created: true
---

# Enterprise Mail WeChat Digest

## Overview

This skill sets up a reusable daily email digest pipeline:

1. Reads new messages from an enterprise IMAP inbox incrementally (tracked by UID).
2. Classifies and merges emails (security, exams, homework, graduation, jobs, scholarships, personal mail, etc.).
3. Generates an email digest via SMTP and prints a WeChat-friendly summary to stdout.
4. WorkBuddy automation captures the stdout summary and pushes it to the user's personal WeChat through the native ClawBot integration.

## When to Use

Use this skill when the user asks for:

- A daily/scheduled digest of enterprise or school email.
- Pushing email summaries to personal WeChat.
- Classifying incoming mail into important vs. general notifications.
- Merging duplicate reminders, withdrawals, and correction notices before output.

## Workflow

### 1. Inspect Existing Files

Look for a project directory containing `mail_digest.py`, `.env`, and `mail_digest_state.json`. If they do not exist, copy the bundled script and template into the requested workspace.

### 2. Configure Environment Variables

Use the bundled `assets/.env.example` as a template. Copy it to `.env` in the project directory and fill in the real credentials:

- `WORK_IMAP_HOST`, `WORK_IMAP_PORT`, `WORK_IMAP_USERNAME`, `WORK_IMAP_PASSWORD`
- `DIGEST_SMTP_HOST`, `DIGEST_SMTP_PORT`, `DIGEST_SMTP_USERNAME`, `DIGEST_SMTP_PASSWORD`
- `DIGEST_TO` (the recipient of the email digest)
- Optional: `MAIL_DIGEST_STATE` (defaults to `./mail_digest_state.json`)

Never commit `.env` or expose credentials in chat output.

### 3. Test the Script Locally

Run the digest manually before enabling automation:

```sh
set -a; source .env; set +a
python3 mail_digest.py
```

The script should send the email digest and print the WeChat summary to stdout.

### 4. Bind WeChat ClawBot

If the user wants WeChat push via WorkBuddy's native channel:

1. WeChat → Me → Settings → Plugins → WeChat ClawBot → Enable.
2. WorkBuddy → Avatar → Claw Settings → Integrations → WeChat ClawBot Integration → Configure.
3. Scan the QR code with the same WeChat account used to log in to WorkBuddy.
4. Confirm status shows "Bound".

### 5. Create WorkBuddy Automations

Create one or more recurring automations that:

1. Load `.env` in the project directory.
2. Run `python3 mail_digest.py`.
3. Capture the stdout summary.
4. Push it to the user's personal WeChat via the ClawBot integration.

Example automation prompt:

```
Run the enterprise mail digest in /path/to/project and push the WeChat summary.

1. Execute in the project directory: set -a; source .env; set +a; python3 mail_digest.py
2. Capture the stdout WeChat summary.
3. Send the summary to the user's personal WeChat via WorkBuddy's native WeChat ClawBot integration.
4. If the script fails, report the error and do not send stale content.

Do not read or expose the .env file. Do not delete mail_digest_state.json.
```

### 6. Fallback Channels

If ClawBot is unavailable or unstable, the same stdout summary can be pushed through third-party services such as PushPlus, ServerChan, or WxPusher by adding a small HTTP wrapper. See `references/setup.md` for examples.

## Resources

- `scripts/mail_digest.py` — Core digest script (parameterized, no hardcoded credentials).
- `assets/.env.example` — Environment variable template.
- `references/setup.md` — Setup guide, scheduling tips, and fallback push options.
