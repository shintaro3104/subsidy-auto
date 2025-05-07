#!/usr/bin/env python3
"""
subsidy-auto  差分検知ツール
  - Google Sheets "sources" から URL 一覧を取得
  - MD5 ハッシュで差分検知
  - 変更時 Slack に通知 & Sheets を更新
  - checked_at は JST (%Y-%m-%dT%H:%M:%S+09:00) で保存
"""

import os
import hashlib
import datetime
from zoneinfo import ZoneInfo

import requests
import gspread
from slack_sdk.webhook import WebhookClient
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────
#  1. 設定・認証
# ─────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACC  = os.path.join(SCRIPT_DIR, "service_account.json")

# .env は存在しなくても OK（GitHub Actions では Secrets から渡す）
load_dotenv(os.path.join(os.path.dirname(SCRIPT_DIR), ".env"))

SHEET_ID      = os.getenv("SHEET_ID")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")

gc   = gspread.service_account(filename=SERVICE_ACC)
ws   = gc.open_by_key(SHEET_ID).worksheet("sources")
hook = WebhookClient(SLACK_WEBHOOK)

# シート見出し → 列番号マップ
headers = ws.row_values(1)
col_idx = {h: i + 1 for i, h in enumerate(headers)}

# JST 時刻を ISO(+09:00) で返す
def jst_now_iso() -> str:
    return datetime.datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds")

# URL → MD5 ハッシュ
def fetch_hash(url: str) -> str:
    html = requests.get(url, timeout=15).text
    return hashlib.md5(html.encode("utf-8")).hexdigest()

# ─────────────────────────────────────────────────────
#  2. メイン処理
# ─────────────────────────────────────────────────────
def main():
    print(f"---- START {jst_now_iso()} ----")

    for row_num, row in enumerate(ws.get_all_records(), start=2):
        name      = row.get("subsidy_name", "(no name)")
        url       = row["url"]
        old_hash  = row.get("last_checked", "")

        try:
            new_hash = fetch_hash(url)
        except Exception as e:
            print(f"[{row_num}] ERROR fetch {url}: {e}")
            ws.update_cell(row_num, col_idx["checked_at"], jst_now_iso())
            continue

        if new_hash != old_hash:
            print(f"[{row_num}] CHANGE → {name}")
            hook.send(text=f"🔔 更新検知: <{url}|{name}>")
            ws.update_cell(row_num, col_idx["status"],       "更新")
            ws.update_cell(row_num, col_idx["last_checked"], new_hash)
        else:
            ws.update_cell(row_num, col_idx["status"], "変化なし")

        ws.update_cell(row_num, col_idx["checked_at"], jst_now_iso())

    print(f"----  END  {jst_now_iso()} ----")


if __name__ == "__main__":
    main()
