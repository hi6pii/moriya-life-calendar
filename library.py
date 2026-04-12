import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random

URL = "https://www.lib.moriya.ibaraki.jp/WebOpac/webopac/library.do"

LIBRARIES = {
    "91": "図書館",
    "92": "中央公民館",
    "93": "郷州公民館",
    "95": "高野公民館",
    "96": "北守谷公民館",
    "98": "駅東サービスセンター"
}

MAX_MONTHS = 13


def get_closed_days(year, month, lib_id):
    data = {
        "year": str(year),
        "month": str(month),
        "lcskbn": lib_id
    }

    try:
        res = requests.post(URL, data=data, timeout=10)
        res.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(res.text, "html.parser")

    table = soup.find("table", class_="calTbl")
    if table is None:
        return None

    closed_days = []

    for td in table.find_all("td"):
        if "休" in td.text:
            text = td.get_text(separator=" ").strip()
            parts = text.split()
            if len(parts) >= 2:
                closed_days.append(int(parts[0]))

    return closed_days


def collect_closed_days(lib_id):
    now = datetime.now()
    year = now.year
    month = now.month

    results = {}

    for i in range(MAX_MONTHS):
        days = get_closed_days(year, month, lib_id)

        if days is None:
            print(f"停止: {year}-{month}")
            break

        results[(year, month)] = days
        print(f"{year}-{month:02d}: {days}")

        # 次の月へ
        month += 1
        if month > 12:
            month = 1
            year += 1

        # サーバー負荷対策
        time.sleep(random.uniform(0.5, 1.5))

    return results


def build_ics(data, name="守谷市 図書室休館日"):
    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//moriya-life-calendar//library//JA
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:{name}
X-WR-TIMEZONE:Asia/Tokyo

"""
    for (year, month) in sorted(data.keys()):
        for day in sorted(data[(year, month)]):
            dt = datetime(year, month, day)
            date_str = dt.strftime("%Y%m%d")
            next_day = (dt + timedelta(days=1)).strftime("%Y%m%d")
            uid = f"{date_str}-library@moriya"
            ics += f"""BEGIN:VEVENT
UID:{uid}
DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}
DTSTART;VALUE=DATE:{date_str}
DTEND;VALUE=DATE:{next_day}
SUMMARY:{name}
END:VEVENT

"""
    ics += "END:VCALENDAR\n"
    return ics

def main():   
    results_list = collect_closed_days("92")
    ics = build_ics(results_list)
    with open("library.ics", "w", encoding="utf-8") as f:
        f.write(ics)

    print("library.ics を出力しました")

if __name__ == "__main__":
    main()
