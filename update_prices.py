import yfinance as yf
from bs4 import BeautifulSoup
import re
import os
import time

# =========================================================
# 📝 事前設定：四季報発売日時点の「基準価格」を入力してください
# （※この数字をもとに、プログラムが増減率を自動計算します）
# =========================================================
BASE_PRICES = {
    "summer2026.html": {
        "NIKKEI": 38102.44, # TODO: 6月17日の日経平均終値を入れてください
        "1952": 2500,       # TODO: 1952(新日本空調)の6/17終値を入力...
        "1982": 1000,
        "4012": 1000,
        "4658": 1000,
        "7175": 1000,
        "7433": 1000,
        "8020": 1000,
        "8370": 1000,
        "8386": 1000,
        "8522": 1000,
        "8542": 1000,
        "8624": 1000
    },
    "spring2026.html": {
        "NIKKEI": 38707.64, # TODO: 3月17日(直前営業日)の日経平均終値を入れてください
        "2674": 1000,       # TODO: 各銘柄の3/17直前終値を入力...
        "296A": 1000,
        "3231": 1000,
        "3766": 1000,
        "3934": 1000,
        "4012": 1000,
        "4221": 1000,
        "4463": 1000,
        "5576": 1000,
        "5832": 1000,
        "6349": 1000,
        "7337": 1000,
        "8334": 1000,
        "8554": 1000,
        "8622": 1000
    }
}

TARGET_FILES = ["summer2026.html", "spring2026.html", "hotstocks.html"]
price_cache = {}

def get_latest_price(code):
    if code in price_cache:
        return price_cache[code]
    try:
        ticker_symbol = "^N225" if code == "NIKKEI" else f"{code}.T"
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="5d") # 直近5日分を取得し、最新の取引日を確実にとる
        if hist.empty:
            return None
        
        latest_price = float(hist['Close'].iloc[-1])
        price_cache[code] = latest_price
        time.sleep(0.5) # APIへの優しさ（負荷軽減）
        return latest_price
    except Exception as e:
        print(f"❌ {code} の取得に失敗: {e}")
        return None

def check_anomaly(old_text, new_price):
    # HTML内の「1,500円」などから数字だけを抽出
    match = re.search(r'([0-9,\.]+)', old_text)
    if not match:
        return False # 最初が「---円」などの場合はスキップ
        
    old_price = float(match.group(1).replace(',', ''))
    if old_price == 0:
        return False
        
    change_rate = abs(new_price - old_price) / old_price
    # 安全装置：前回から30%以上一気に変動した場合はストップ（株式分割やAPIエラー対策）
    if change_rate > 0.30:
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

            # 増減率の計算: (現在株価 / 基準価格) - 1
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
                        # 隣の (X銘柄 / Y銘柄中) も自動更新
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
