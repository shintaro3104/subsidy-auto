### Setup

```bash
git clone https://github.com/your-name/subsidy-auto.git
cd subsidy-auto
pip install -r requirements.txt
cp .env.example .env   # ← ローカル実行時のみ
# .env に SHEET_ID / SLACK_WEBHOOK を記入
python scripts/scrape_subsidy.py
