import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta
import re
import time

BASE_YEAR = 2026
BASE_URL = "https://www.city.moriya.ibaraki.jp/kurashi_tetsuzuki/kankyo_gomi/1002052/1002060/1008307/index.html"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ===== 共通：ページ取得 =====
def fetch(url):
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    res.encoding = res.apparent_encoding
    time.sleep(1)  # 優しさ
    return BeautifulSoup(res.text, "html.parser")

# ===== 年度ページ取得 =====
def get_yearly_link(soup):
    target = f"{BASE_YEAR}年度版クリーンカレンダー（テキスト版）"
    for a in soup.find_all("a"):
        if target in a.get_text():
            return urljoin(BASE_URL, a["href"])
    return None

# ===== 月リンク一覧取得 =====
def get_monthly_links(soup, base_url):
    links = []
    for a in soup.find_all("a"):
        text = a.get_text()
        if "月クリーンカレンダー" in text:
            links.append((text, urljoin(base_url, a["href"])))
    return links

# ===== 月→年変換 =====
def resolve_year_month(name):
    month = int(re.search(r"(\d+)月", name).group(1))
    year = BASE_YEAR if month >= 4 else BASE_YEAR + 1
    return year, month

# ===== 日データ抽出 =====
def parse_daily(soup, year, month):
    results = []
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        match = re.match(r"(\d+)日.*?）(.*)", text)
        if match:
            day = int(match.group(1))
            garbage = match.group(2)

            if garbage == "無し":
                continue

            start = datetime(year, month, day)
            end = start + timedelta(days=1)

            results.append({
                "date": start.strftime("%Y%m%d"),
                "end_date": end.strftime("%Y%m%d"),
                "garbage": garbage
            })
    return results

# ===== ICS生成 =====
def build_event(data):
    # ★ UID改善（内容含める）
    uid = f"{data['date']}-garbage@moriya"

    return f"""BEGIN:VEVENT
UID:{uid}
DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}
DTSTART;VALUE=DATE:{data['date']}
DTEND;VALUE=DATE:{data['end_date']}
SUMMARY:{data['garbage']}
END:VEVENT

"""

# ===== メイン処理 =====
def main():
    events = []

    soup = fetch(BASE_URL)
    yearly_link = get_yearly_link(soup)

    soup2 = fetch(yearly_link)
    monthly_links = get_monthly_links(soup2, yearly_link)

    for name, link in monthly_links:
        year, month = resolve_year_month(name)
        print(f"開始: year={year}, month={month}")

        soup3 = fetch(link)
        daily_data = parse_daily(soup3, year, month)

        for d in daily_data:
            events.append(build_event(d))

    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//moriya-life-calendar//garbage//JA
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:守谷市 ゴミカレンダー
X-WR-TIMEZONE:Asia/Tokyo

{''.join(events)}
END:VCALENDAR
"""

    with open("garbage.ics", "w", encoding="utf-8") as f:
        f.write(ics)

    print("garbage.ics を出力しました")

if __name__ == "__main__":
    main()