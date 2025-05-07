#!/usr/bin/env python3
import os, hashlib, datetime, requests, json, tempfile
import gspread
from slack_sdk.webhook import WebhookClient

# ── 環境変数 ───────────────────────────────────
SHEET_ID      = os.environ["SHEET_ID"]
SLACK_WEBHOOK = os.environ["SLACK_WEBHOOK"]
# JSON は workflow でファイルに書き出している
SERVICE_ACCOUNT = "service_account.json"

# ── Google Sheets ────────────────────────────
gc = gspread.service_account(filename=SERVICE_ACCOUNT)
ws = gc.open_by_key(SHEET_ID).worksheet("sources")

headers = ws.row_values(1)
col = {h: i + 1 for i, h in enumerate(headers)}

hook = WebhookClient(SLACK_WEBHOOK)

def md5_of_url(url: str) -> str:
    html = requests.get(url, timeout=15).text
    return hashlib.md5(html.encode()).hexdigest()

def main():
    records = ws.get_all_records()
    for i, r in enumerate(records, start=2):
        url   = r["url"]
        old   = r.get("last_checked", "")
        now   = datetime.datetime.now().isoformat()

        try:
            new = md5_of_url(url)
        except Exception as e:
            ws.update_cell(i, col["checked_at"], now)
            continue

        if new != old:
            hook.send(text=f"🔔 更新検知: <{url}|{r['subsidy_name']}>")
            ws.update_cell(i, col["status"],       "更新")
            ws.update_cell(i, col["last_checked"], new)
        else:
            ws.update_cell(i, col["status"], "変化なし")

        ws.update_cell(i, col["checked_at"], now)

if __name__ == "__main__":
    main()
