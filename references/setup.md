# Setup Guide

## 1. Create a Project Directory

Create a directory for the mail digest (for example `~/mail-digest/`) and copy the bundled files into it:

- `scripts/mail_digest.py`
- `assets/.env.example`

## 2. Configure Credentials

```sh
cp assets/.env.example .env
```

Edit `.env` with the real IMAP/SMTP credentials. Do not commit `.env`.

## 3. Test Locally

```sh
set -a; source .env; set +a
python3 scripts/mail_digest.py
```

You should receive the email digest, and a WeChat-friendly summary should be printed to stdout.

## 4. Bind WeChat ClawBot (Optional, for native WeChat push)

1. WeChat → Me → Settings → Plugins → WeChat ClawBot → Enable.
2. WorkBuddy → Avatar → Claw Settings → Integrations → WeChat ClawBot Integration → Configure.
3. Scan the QR code with the same WeChat account used for WorkBuddy login.
4. Confirm status shows "Bound".

## 5. Create WorkBuddy Automations

Create recurring automations in WorkBuddy with the project directory as the working directory.

Example prompt:

```
Run the enterprise mail digest and push the summary to WeChat.

1. In the project directory, execute: set -a; source .env; set +a; python3 scripts/mail_digest.py
2. Capture the stdout WeChat summary.
3. Send the summary to the user's personal WeChat via WorkBuddy's native WeChat ClawBot integration.
4. If ClawBot is unavailable, report the failure and do not send stale content.

Do not read or expose the .env file. Do not delete mail_digest_state.json.
```

Suggested schedule: `FREQ=DAILY;BYHOUR=10;BYMINUTE=0` and `FREQ=DAILY;BYHOUR=20;BYMINUTE=0`.

## 6. Fallback Push Channels

If ClawBot is not available, wrap the stdout summary with one of these services:

### PushPlus

```python
import os, requests

def push_pushplus(title: str, content: str) -> None:
    token = os.getenv("PUSHPLUS_TOKEN", "").strip()
    if not token:
        return
    requests.post(
        "http://www.pushplus.plus/send",
        json={"token": token, "title": title, "content": content, "template": "txt"},
        timeout=10,
    )
```

### ServerChan

```python
import os, requests

def push_serverchan(title: str, content: str) -> None:
    key = os.getenv("SERVERCHAN_SENDKEY", "").strip()
    if not key:
        return
    requests.post(
        f"https://sctapi.ftqq.com/{key}.send",
        data={"title": title, "desp": content},
        timeout=10,
    )
```

Add the chosen function to the end of `mail_digest.py` and call it after `print(build_wechat_summary(all_items))`.
