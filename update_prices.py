import yfinance as yf
from bs4 import BeautifulSoup
import re
import os
import time

# =========================================================
# 📝 正確な基準価格（四季報発売日時点の実績終値）
# =========================================================
BASE_PRICES = {
    "summer2026.html": {
        "NIKKEI": 69902.25,
        "1952": 3515.0,
        "1982": 3075.0,
        "4012": 1600.0,
        "4658": 1552.0,
        "7175": 1347.0,
        "7433": 4500.0,
        "8020": 2092.0,
        "8370": 4440.0,
        "8386": 2431.0,
        "8522": 5830.0,
        "8542": 1490.0,
        "8624": 1365.0,
    },
    "spring2026.html": {
        "NIKKEI": 53700.39,
        "2674": 1928.55,
        "296A": 637.89,
        "3231": 1039.48,
        "3766": 1217.56,
        "3934": 1910.5,
        "4012": 1509.0,
        "4221": 4571.11,
        "4463": 1677.44,
        "5576": 2574.13,
        "5832": 2760.0,
        "6349": 1616.0,
        "7337": 1775.76,
        "8334": 2052.8,
        "8554": 1494.0,  # 8554（南日本銀行）を手動設定
        "8622": 693.15,
    }
}

TARGET_FILES = ["summer2026.html", "spring2026.html", "weekly.html"]
price_cache = {}

def get_latest_price(code):
    if code in price_cache:
        return price_cache[code]
    try:
        ticker_symbol = "^N225" if code == "NIKKEI" else f"{code}.T"
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="5d")
        if hist.empty:
            return None
        
        latest_price = float(hist['Close'].iloc[-1])
        price_cache[code] = latest_price
        time.sleep(0.5)
        return latest_price
    except Exception as e:
        print(f"❌ {code} の取得に失敗: {e}")
        return None

def check_anomaly(old_text, new_price):
    match = re.search(r'([0-9,\.]+)', old_text)
    if not match:
        return False  # 「---円」の場合は更新を許可
        
    old_price = float(match.group(1).replace(',', ''))
    if old_price == 0:
        return False
        
    change_rate = abs(new_price - old_price) / old_price
    if change_rate > 0.30:  # 30%以上の異常変動はブロック
        return True
    return False

def update_html():
    for filename in TARGET_FILES:
        if not os.path.exists(filename):
            continue

        with open(filename, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, "html.parser")
            
        changed = False

        # --- 1. 現在株価の書き換え ---
        for el in soup.find_all(class_="stock-price"):
            code = el.get("data-code")
            if not code: continue
            
            latest_price = get_latest_price(code)
            if latest_price is None: continue

            if check_anomaly(el.text, latest_price):
                print(f"⚠️ {code} で30%以上の異常変動を検知。更新をスキップします。")
                continue

            new_text = f"{int(latest_price):,}円"
            if el.string != new_text:
                el.string = new_text
                changed = True

        # --- 2. 増減率（パフォーマンス）の書き換え ---
        perf_elements = soup.find_all(class_="stock-perf")
        for el in perf_elements:
            code = el.get("data-code")
            if not code: continue

            latest_price = get_latest_price(code)
            base_price = BASE_PRICES.get(filename, {}).get(code)
            
            if latest_price is None or base_price is None or base_price == 0:
                continue

            perf_rate = (latest_price / base_price) - 1
            perf_percentage = perf_rate * 100
            
            if perf_percentage >= 0:
                new_text = f"+{perf_percentage:.1f}%"
                new_class = "stock-perf highlight-blue"
            else:
                new_text = f"{perf_percentage:.1f}%"
                new_class = "stock-perf highlight-red"

            if el.string != new_text:
                el.string = new_text
                el['class'] = new_class
                changed = True

        # --- 3. 日経平均超えの「勝率」を自動計算 ---
        win_rate_el = soup.find(id="nikkei-win-rate")
        if win_rate_el:
            nikkei_el = soup.find(class_="stock-perf", attrs={"data-code": "NIKKEI"})
            if nikkei_el and "%" in nikkei_el.text:
                nikkei_val = float(nikkei_el.text.replace('%', '').replace('+', ''))
                win_count = 0
                total_count = 0
                
                for el in perf_elements:
                    code = el.get("data-code")
                    if code and code != "NIKKEI" and "%" in el.text:
                        total_count += 1
                        val = float(el.text.replace('%', '').replace('+', ''))
                        if val > nikkei_val:
                            win_count += 1
                
                if total_count > 0:
                    win_rate = (win_count / total_count) * 100
                    new_win_text = f"{win_rate:.1f}%"
                    
                    if win_rate_el.string != new_win_text:
                        win_rate_el.string = new_win_text
                        changed = True
                        count_el = win_rate_el.find_next_sibling("span")
                        if count_el:
                            count_el.string = f"（{win_count}銘柄 / {total_count}銘柄中）"

        # 変更があった場合のみHTMLを上書き保存
        if changed:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            print(f"✨ {filename} の更新が完了しました！")

if __name__ == "__main__":
    print("🤖 株価自動更新システムを起動します...")
    update_html()
    print("🏁 すべての処理が完了しました。")
