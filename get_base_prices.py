import yfinance as yf
from datetime import datetime, timedelta

# 取得したい基準日（※指定日が土日の場合は、直後の営業日の終値を自動取得します）
SUMMER_DATE = "2026-06-17"
SPRING_DATE = "2026-03-17"

summer_codes = ["NIKKEI", "1952", "1982", "4012", "4658", "7175", "7433", "8020", "8370", "8386", "8522", "8542", "8624"]
spring_codes = ["NIKKEI", "2674", "296A", "3231", "3766", "3934", "4012", "4221", "4463", "5576", "5832", "6349", "7337", "8334", "8554", "8622"]

def fetch_price(code, date_str):
    symbol = "^N225" if code == "NIKKEI" else f"{code}.T"
    start_date = datetime.strptime(date_str, "%Y-%m-%d")
    # 休日を考慮して1週間分を取得し、最初の取引日の価格を採用
    end_date = start_date + timedelta(days=7) 
    
    try:
        hist = yf.Ticker(symbol).history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
        if not hist.empty:
            return round(hist['Close'].iloc[0], 2)
    except Exception as e:
        pass
    return 0

print("⏳ 夏号の基準価格(6/17)を自動検索中...")
print('    "summer2026.html": {')
for code in summer_codes:
    price = fetch_price(code, SUMMER_DATE)
    print(f'        "{code}": {price},')
print('    },')

print("\n⏳ 春号の基準価格(3/17)を自動検索中...")
print('    "spring2026.html": {')
for code in spring_codes:
    price = fetch_price(code, SPRING_DATE)
    print(f'        "{code}": {price},')
print('    }')
print("\n✅ 完了！この結果を update_prices.py の BASE_PRICES の部分にコピペして上書きしてください。")
