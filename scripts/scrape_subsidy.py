#!/usr/local/bin/python3
import os
import hashlib
import datetime
import requests
import gspread
from dotenv import load_dotenv
from slack_sdk.webhook import WebhookClient

# ─── 設定 ────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))

# .env 読み込み
load_dotenv(os.path.join(ROOT, '.env'))

SERVICE_ACCOUNT = os.path.join(ROOT, 'service_account.json')
SHEET_ID        = os.getenv('SHEET_ID')
SLACK_WEBHOOK   = os.getenv('SLACK_WEBHOOK')

# ─── Google Sheets 接続 ───────────────────────────────
gc = gspread.service_account(filename=SERVICE_ACCOUNT)
sh = gc.open_by_key(SHEET_ID)
ws = sh.worksheet('sources')

# ヘッダーから列番号マップ
headers = ws.row_values(1)
col_idx = {h: i + 1 for i, h in enumerate(headers)}

# ─── Slack Webhook ────────────────────────────────────
hook = WebhookClient(SLACK_WEBHOOK)

# ─── ページ取得→MD5 ハッシュ化 ─────────────────────────
def fetch_hash(url):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return hashlib.md5(r.text.encode('utf-8')).hexdigest()

# ─── メイン処理 ───────────────────────────────────────
def main():
    start = datetime.datetime.now().isoformat()
    print(f"---- START {start} ----")

    records = ws.get_all_records()
    for idx, row in enumerate(records, start=2):
        name       = row.get('subsidy_name', '(no name)')
        url        = row.get('url', '')
        old_hash   = row.get('last_checked', '')
        now_iso    = datetime.datetime.now().isoformat()

        print(f"[{idx}] Checking {name} → {url}")

        try:
            new_hash = fetch_hash(url)
        except Exception as e:
            print(f"[{idx}] ERROR fetching: {e}")
            ws.update_cell(idx, col_idx['checked_at'], now_iso)
            continue

        if new_hash != old_hash:
            print(f"[{idx}] CHANGE detected")
            hook.send(text=f"🔔 更新検知: <{url}|{name}>")
            ws.update_cell(idx, col_idx['status'], '更新')
            ws.update_cell(idx, col_idx['last_checked'], new_hash)
        else:
            print(f"[{idx}] No change")
            ws.update_cell(idx, col_idx['status'], '変化なし')

        print(f"[{idx}] Updating checked_at")
        ws.update_cell(idx, col_idx['checked_at'], now_iso)

    end = datetime.datetime.now().isoformat()
    print(f"----  END  {end} ----")

if __name__ == '__main__':
    main()
