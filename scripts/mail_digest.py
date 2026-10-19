#!/usr/bin/env python3
"""Collect new mail from the enterprise IMAP account and send a digest email.

This script is bundled with the enterprise-mail-wechat-digest skill. It reads
all configuration from environment variables (see assets/.env.example) and
prints a WeChat-friendly summary to stdout so WorkBuddy automations can push
it to a personal WeChat account.
"""

from __future__ import annotations

import email
import html
import json
import os
import re
import smtplib
import ssl
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from imaplib import IMAP4_SSL
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATE_FILE = Path(os.getenv("MAIL_DIGEST_STATE", ROOT / "mail_digest_state.json"))


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def decode_text(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except (LookupError, UnicodeError):
        return value


def clean_body(message: email.message.Message) -> str:
    parts = []
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_disposition() == "attachment":
                continue
            if part.get_content_type() == "text/plain":
                parts.append(part.get_payload(decode=True) or b"")
    elif message.get_content_type() == "text/plain":
        parts.append(message.get_payload(decode=True) or b"")
    for raw in parts:
        charset = message.get_content_charset() or "utf-8"
        text = raw.decode(charset, errors="replace")
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            return text[:800]
    return "(无纯文本正文)"


def classify(item: dict[str, str]) -> str:
    text = f"{item['subject']} {item['body']}".lower()

    # Personal emails often come from public consumer mail domains.
    sender = item.get("from", "").lower()
    public_domains = r"@(qq\.com|gmail\.com|163\.com|126\.com|sina\.com|sohu\.com|outlook\.com|hotmail\.com|foxmail\.com|yeah\.net|aliyun\.com)\b"
    if re.search(public_domains, sender, re.I):
        return "个人来信"

    rules = [
        ("账号安全", r"安全|登录|登陆|密码|验证码|异常|盗用|security|login|password"),
        ("考试", r"考试|测验|test|exam|quiz|final"),
        ("作业", r"作业|报告|论文|assignment|homework|coursework|submission"),
        ("毕业手续", r"毕业|学位|答辩|离校|graduation|thesis|defense"),
        ("招聘面试", r"招聘|面试|职位|录用|实习|recruit|interview|job|career"),
        ("奖学金", r"奖学金|资助|scholarship|bursary|funding"),
    ]
    for name, pattern in rules:
        if re.search(pattern, text, re.I):
            return name
    if re.search(r"撤回|更正|更改|修正|recall|correction|updated", text, re.I):
        return "通知更正"
    return "其他"


def importance(item: dict[str, str]) -> int:
    text = f"{item['subject']} {item['body']}".lower()
    score = 0
    high_priority = {"个人来信", "账号安全", "考试", "作业", "毕业手续", "招聘面试", "奖学金"}
    if classify(item) in high_priority:
        score += 4
    if re.search(r"截止|截至|必须|需要|请于|deadline|due|action required|urgent|important", text, re.I):
        score += 3
    if re.search(r"撤回|更正|更改|修正|recall|correction|updated", text, re.I):
        score -= 2
    return score


def deadline(item: dict[str, str]) -> str:
    text = f"{item['subject']} {item['body']}"
    patterns = [
        r"(?:截止|截至|请于|完成于|due|deadline)\s*[:：]?\s*([^，。;；\n]{2,32})",
        r"\b(20\d{2}[年/-]\d{1,2}[月/-]\d{1,2}(?:日)?(?:\s*\d{1,2}:\d{2})?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).strip(" ：:，,。.;；")
    return "未识别到明确截止时间"


def merge_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for item in items:
        key = re.sub(r"(?:撤回|更正|更改|修正|recall|correction|updated)", "", item["subject"], flags=re.I)
        key = re.sub(r"\s+", "", key).lower() or item["subject"].lower()
        if key in merged:
            merged[key]["body"] = f"{merged[key]['body']}；{item['body']}"
            merged[key]["subject"] = item["subject"] if importance(item) >= importance(merged[key]) else merged[key]["subject"]
        else:
            merged[key] = dict(item)
    return list(merged.values())


@dataclass
class Account:
    label: str
    host: str
    port: int
    username: str
    password: str
    folder: str = "INBOX"


def load_state() -> dict[str, int]:
    if not STATE_FILE.exists():
        return {}
    try:
        return {k: int(v) for k, v in json.loads(STATE_FILE.read_text()).items()}
    except (OSError, ValueError, TypeError):
        return {}


def save_state(state: dict[str, int]) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def fetch_new(account: Account, last_uid: int) -> tuple[list[dict[str, str]], int]:
    with IMAP4_SSL(account.host, account.port) as client:
        client.login(account.username, account.password)
        client.select(account.folder, readonly=True)
        status, data = client.uid("SEARCH", None, f"UID {last_uid + 1}:*")
        if status != "OK":
            raise RuntimeError(f"IMAP SEARCH failed for {account.label}")
        uids = [int(value) for value in data[0].split()] if data and data[0] else []
        messages = []
        for uid in uids:
            status, fetched = client.uid("FETCH", str(uid), "(BODY.PEEK[])")
            if status != "OK":
                continue
            raw = next((item[1] for item in fetched if isinstance(item, tuple)), None)
            if not raw:
                continue
            message = email.message_from_bytes(raw)
            date = decode_text(message.get("Date"))
            try:
                date = parsedate_to_datetime(date).astimezone().strftime("%Y-%m-%d %H:%M")
            except (TypeError, ValueError, OverflowError):
                pass
            messages.append({
                "account": account.label,
                "from": decode_text(message.get("From")),
                "to": decode_text(message.get("To")),
                "subject": decode_text(message.get("Subject")) or "(无主题)",
                "date": date,
                "body": clean_body(message),
            })
        return messages, max([last_uid, *uids])


def send_digest(items: list[dict[str, str]]) -> None:
    smtp_host = required("DIGEST_SMTP_HOST")
    smtp_port = int(os.getenv("DIGEST_SMTP_PORT", "465"))
    smtp_user = required("DIGEST_SMTP_USERNAME")
    smtp_password = required("DIGEST_SMTP_PASSWORD")
    recipient = required("DIGEST_TO")
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    raw_count = len(items)
    items = merge_items(items)
    subject = f"企业邮箱汇总 {now}（{raw_count} 封新邮件）"
    if items:
        categories = defaultdict(list)
        for item in items:
            categories[classify(item)].append(item)
        important = sorted(items, key=importance, reverse=True)[:5]
        text_lines = [subject, "", f"本轮收到 {raw_count} 封新邮件，合并后按 {len(items)} 个事项整理；重复提醒和更正通知已合并。", ""]
        text_lines.append("重点邮件（最多5项）：")
        for index, item in enumerate(important, 1):
            text_lines.extend([
                f"{index}. {item['subject']}",
                f"   是什么：{item['body']}",
                "   需要做什么：请根据邮件正文处理；如无明确要求则无需操作。",
                f"   什么时候截止：{deadline(item)}",
            ])
        text_lines.extend(["", "分类概括："])
        for category, category_items in sorted(categories.items()):
            text_lines.append(f"- {category}：{len(category_items)} 封")
        text_lines.append("")
        html_items = []
        for category, category_items in sorted(categories.items()):
            html_items.append(f"<h3>{html.escape(category)}（{len(category_items)}封）</h3>")
            for item in category_items:
                html_items.append(
                    "<article><b>{}</b><p>发件人：{}<br>时间：{}<br>{}</p></article>".format(
                        html.escape(item["subject"]), html.escape(item["from"]),
                        html.escape(item["date"]), html.escape(item["body"]),
                    )
                )
        html_items.insert(0, "<h3>重点邮件（最多5项）</h3><ol>{}</ol>".format("".join(
            "<li><b>{}</b><br>是什么：{}<br>需要做什么：请根据邮件正文处理；如无明确要求则无需操作。<br>什么时候截止：{}</li>".format(
                html.escape(item["subject"]), html.escape(item["body"]), html.escape(deadline(item))
            ) for item in important
        )))
        text = "\n".join(text_lines)
        body_html = "<html><body><h2>{}</h2>{}</body></html>".format(
            html.escape(subject), "".join(html_items)
        )
    else:
        text = f"{subject}\n本次没有发现新邮件。"
        body_html = f"<html><body><h2>{html.escape(subject)}</h2><p>本次没有发现新邮件。</p></body></html>"

    message = EmailMessage()
    message["From"] = smtp_user
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text)
    message.add_alternative(body_html, subtype="html")
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
        server.login(smtp_user, smtp_password)
        server.send_message(message)


def _summarize_body(body: str, max_len: int = 70) -> str:
    """Return a short, WeChat-friendly summary of the email body."""
    body = body.strip()
    if not body or body == "(无纯文本正文)":
        return ""
    if len(body) <= max_len:
        return body
    # Try not to break a word right in the middle.
    truncated = body[:max_len]
    if truncated[-1] not in " ，。；：！？、\"'":
        truncated = truncated.rsplit(" ", 1)[0] if " " in truncated else truncated
    return truncated + "…"


def build_wechat_summary(items: list[dict[str, str]]) -> str:
    """Build a compact summary suitable for pushing to WeChat."""
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    if not items:
        return f"📭 企业邮箱摘要 ({now})\n本次没有新邮件。"

    raw_count = len(items)
    # merge_items already handles withdrawn/correction/duplicate merges.
    merged = merge_items(items)

    # Important = high-priority categories or explicit deadline/action keywords.
    important = sorted(
        [item for item in merged if classify(item) in {"个人来信", "账号安全", "考试", "作业", "毕业手续", "招聘面试", "奖学金"} or importance(item) >= 4],
        key=importance,
        reverse=True,
    )[:5]
    important_ids = {id(item) for item in important}
    general = [item for item in merged if id(item) not in important_ids]

    lines = [
        f"📬 企业邮箱摘要 ({now})",
        f"邮箱本轮共 {raw_count} 封新邮件，整理为 {len(merged)} 个事项",
    ]

    if important:
        lines.extend(["", "🔔 重要通知："])
        for index, item in enumerate(important, 1):
            lines.append(f"{index}. {item['subject']}")
            summary = _summarize_body(item['body'], max_len=100)
            if summary:
                lines.append(f"   是什么：{summary}")
            lines.append("   需要做什么：请根据邮件正文处理；如无明确要求则无需操作。")
            lines.append(f"   什么时候截止：{deadline(item)}")

    if general:
        lines.extend(["", "📋 一般通知："])
        for index, item in enumerate(general, 1):
            lines.append(f"{index}. {item['subject']}")
            summary = _summarize_body(item['body'], max_len=60)
            if summary:
                lines.append(f"   💡 {summary}")
            due = deadline(item)
            if due != "未识别到明确截止时间":
                lines.append(f"   ⏰ 截止：{due}")

    return "\n".join(lines)


def main() -> None:
    accounts = [Account(
        "企业邮箱",
        required("WORK_IMAP_HOST"),
        int(os.getenv("WORK_IMAP_PORT", "993")),
        required("WORK_IMAP_USERNAME"),
        required("WORK_IMAP_PASSWORD"),
        os.getenv("WORK_IMAP_FOLDER", "INBOX"),
    )]
    state = load_state()
    all_items: list[dict[str, str]] = []
    new_state = dict(state)
    for account in accounts:
        key = account.label
        items, latest_uid = fetch_new(account, state.get(key, 0))
        all_items.extend(items)
        new_state[key] = latest_uid
    send_digest(all_items)
    save_state(new_state)
    # Also print a WeChat-friendly summary to stdout so WorkBuddy automations can capture it.
    print(build_wechat_summary(all_items))


if __name__ == "__main__":
    main()
