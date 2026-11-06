"""
ربات جامع و فوق‌حرفه‌ای اخبار و تحلیل بازار فارکس (Pipversefactory)
قابلیت‌ها:
۱. گزارش جامع صبحگاهی تقویم اقتصادی و برنامه معاملاتی روزانه (ساعت ۸:۳۰ صبح به وقت ایران)
۲. پیش‌هشدار ۶۰ دقیقه قبل از خبر با تعیین صعودی یا نزولی بودن جفت‌ارزها و طلا
۳. گزارش لحظه اعلام خبر با محاسبه واکنش زنده چارت (کندل‌های ۵ و ۱۵ دقیقه‌ای)
۴. پایش شاخص دلار آمریکا (DXY)
۵. سطوح کلیدی حمایت، مقاومت و پیوت پوینت روزانه (Pivot Points: S1, R1, P)
۶. توضیح ۱ خطی و کاربردی ماهیت رویداد به زبان ساده
۷. دکمه‌های شیشه‌ای شکیل زیر تمام پیام‌های کانال
۸. پاسخ‌گویی خودکار و تعاملی به کاربران در پی‌وی ربات (/start, /gold, /dxy, /calendar, /levels, /pairs)
"""

import os
import sys
import time
import json
import requests
import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# وب‌سرور سبک داخلی برای فعال‌سازی هاست‌های رایگان ابری (مانند Render Web Service) بدون نیاز به کارت بانکی
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("ربات فارکس Pipverse به صورت ۲۴ ساعته فعال است.".encode("utf-8"))

    def log_message(self, format, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print(f"[وب‌سرور ابری] سرور سلامت روی پورت {port} فعال شد.")
    except Exception as e:
        print(f"[وب‌سرور ابری خطا]: {e}")

# تنظیم انکودینگ کنسول برای پشتیبانی کامل از حروف فارسی و ایموجی‌ها
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR / ".env"
CACHE_PATH = BASE_DIR / "calendar_cache.json"
SENT_EVENTS_PATH = BASE_DIR / "sent_events.json"
LAST_UPDATE_PATH = BASE_DIR / "last_update.txt"

IRAN_TZ = datetime.timezone(datetime.timedelta(hours=3, minutes=30))

# ======================= بارگذاری تنظیمات =======================
def load_config():
    config = {
        "TELEGRAM_BOT_TOKEN": "9085034519:AAFG7C4JauBsnzI1XB0jpJTLjKKS0ImNTSs",
        "TELEGRAM_CHANNEL_ID": "@pipversefactory",
        "PROXY_URL": "",
        "CHECK_INTERVAL_SECONDS": 10,       # پایش سریع برای پاسخ فوری در پی‌وی
        "CALENDAR_CACHE_TTL_HOURS": 2,
    }
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
    return config

CONFIG = load_config()

# پرچم کشورها
COUNTRY_FLAGS = {
    "USD": "🇺🇸 دلار آمریکا",
    "EUR": "🇪🇺 یورو اروپا",
    "GBP": "🇬🇧 پوند انگلستان",
    "JPY": "🇯🇵 ین ژاپن",
    "CAD": "🇨🇦 دلار کانادا",
    "AUD": "🇦🇺 دلار استرالیا",
    "CHF": "🇨🇭 فرانک سوئیس",
    "NZD": "🇳🇿 دلار نیوزیلند",
    "CNY": "🇨🇳 یوان چین"
}

# نگاشت جفت‌ارزها و شاخص‌ها
PAIRS_MAP = {
    "USD": [
        {"symbol": "GC=F", "name": "انس جهانی طلا (XAU/USD)"},
        {"symbol": "DX-Y.NYB", "name": "شاخص دلار آمریکا (DXY)"},
        {"symbol": "EURUSD=X", "name": "EUR/USD"},
        {"symbol": "GBPUSD=X", "name": "GBP/USD"},
        {"symbol": "USDJPY=X", "name": "USD/JPY"}
    ],
    "EUR": [
        {"symbol": "EURUSD=X", "name": "EUR/USD"},
        {"symbol": "EURGBP=X", "name": "EUR/GBP"},
        {"symbol": "EURJPY=X", "name": "EUR/JPY"}
    ],
    "GBP": [
        {"symbol": "GBPUSD=X", "name": "GBP/USD"},
        {"symbol": "EURGBP=X", "name": "EUR/GBP"},
        {"symbol": "GBPJPY=X", "name": "GBP/JPY"}
    ],
    "JPY": [
        {"symbol": "USDJPY=X", "name": "USD/JPY"},
        {"symbol": "EURJPY=X", "name": "EUR/JPY"},
        {"symbol": "GBPJPY=X", "name": "GBP/JPY"}
    ],
    "CAD": [
        {"symbol": "USDCAD=X", "name": "USD/CAD"},
        {"symbol": "CADJPY=X", "name": "CAD/JPY"}
    ],
    "AUD": [
        {"symbol": "AUDUSD=X", "name": "AUD/USD"},
        {"symbol": "AUDJPY=X", "name": "AUD/JPY"}
    ],
    "CHF": [
        {"symbol": "USDCHF=X", "name": "USD/CHF"},
        {"symbol": "EURCHF=X", "name": "EUR/CHF"}
    ],
    "NZD": [
        {"symbol": "NZDUSD=X", "name": "NZD/USD"},
        {"symbol": "NZDJPY=X", "name": "NZD/JPY"}
    ]
}

# فرهنگ توضیحات کاربردی اخبار به زبان ساده
NEWS_EXPLANATIONS = {
    "non-farm": "اشتغال غیرکشاورزی (NFP): نشان‌دهنده تعداد شغل‌های جدید ایجاد شده است؛ ارقام بالا نشانه رونق بازار کار و افزایش تمایل به رشد دلار است.",
    "unemployment": "نرخ بیکاری: درصد جمعیت آماده‌به‌کار بدون شغل؛ کاهش نرخ بیکاری نشانه تقویت بنیه اقتصادی و صعود ارز ملی است.",
    "cpi": "شاخص بهای مصرف‌کننده (تورم): مهم‌ترین شاخص تورمی؛ افزایش آن احتمال سخت‌گیری پولی و بالا ماندن نرخ بهره را تشدید می‌کند.",
    "pce": "شاخص PCE هسته: سنجه تورمی محبوب بانک مرکزی آمریکا (Fed)؛ ارقام صعودی تقاضا برای دلار و بازده اوراق را بالا می‌برد.",
    "gdp": "تولید ناخالص داخلی (رشد اقتصادی): حجم کل کالا و خدمات تولید شده؛ عدد بالاتر محرک اصلی رالی صعودی ارز است.",
    "pmi": "شاخص مدیران خرید (PMI): ارقام بالای ۵۰ نشانه گسترش و رونق، و زیر ۵۰ نشانه رکود اقتصادی است.",
    "rate": "نرخ بهره بانکی: قدرتمندترین ابزار پولی؛ افزایش نرخ بهره جذابیت سرمایه‌گذاری در ارز آن کشور را به شدت افزایش می‌دهد.",
    "retail": "خرده‌فروشی: نشان‌دهنده توان خرید مردم؛ مصرف قوی‌تر یعنی درآمد بیشتر شرکت‌ها و رونق پایدار اقتصادی.",
    "speaks": "سخنرانی مقامات پولی: سیگنال‌دهی درباره تصمیمات آتی نرخ بهره؛ لحن هاوکیش (شاهینی) مثبت و داویش (کبوتری) منفی است."
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    if CONFIG["PROXY_URL"]:
        s.proxies = {
            "http": CONFIG["PROXY_URL"],
            "https": CONFIG["PROXY_URL"]
        }
    return s

SESSION = get_session()

# ======================= دکمه‌های شیشه‌ای (Inline Keyboards) =======================
DEFAULT_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "📊 چارت زنده در تریدینگ‌ویو", "url": "https://www.tradingview.com/chart/?symbol=OANDA:XAUUSD"},
            {"text": "🌐 تقویم فارکس فکتوری", "url": "https://www.forexfactory.com/calendar"}
        ],
        [
            {"text": "📢 عضویت در کانال Pipverse", "url": "https://t.me/pipversefactory"}
        ]
    ]
}

def format_event_time_iran(event_date_str):
    try:
        dt = datetime.datetime.fromisoformat(event_date_str)
        dt_iran = dt.astimezone(IRAN_TZ)
        return dt_iran.strftime("%H:%M (به وقت تهران)")
    except Exception:
        return event_date_str

def get_explanation(title):
    t_lower = title.lower()
    for k, v in NEWS_EXPLANATIONS.items():
        if k in t_lower:
            return v
    return "شاخص معتبر تقویم اقتصادی؛ نوسانات وابسته به فاصله عدد نهایی با ارقام پیش‌بینی بازار است."

# ======================= داده‌های بازار و پیوت پوینت‌ها =======================
def get_forex_precision_data(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=5m"
    try:
        r = SESSION.get(url, timeout=8)
        if r.status_code == 200:
            res = r.json()["chart"]["result"][0]
            meta = res.get("meta", {})
            quotes = res.get("indicators", {}).get("quote", [{}])[0]
            closes = [c for c in quotes.get("close", []) if c is not None]
            if not closes:
                return None
            current_price = closes[-1]
            prev_close = meta.get("chartPreviousClose") or closes[0]
            ref_idx = -4 if len(closes) >= 4 else 0
            price_15m_ago = closes[ref_idx]
            reaction_15m_pct = ((current_price - price_15m_ago) / price_15m_ago) * 100
            daily_change_pct = ((current_price - prev_close) / prev_close) * 100
            return {
                "price": current_price,
                "reaction_15m": reaction_15m_pct,
                "daily_change": daily_change_pct
            }
    except Exception as e:
        print(f"[خطا در استخراج قیمت {symbol}]: {e}")
    return None

def get_pivot_points(symbol="GC=F"):
    """محاسبه سطوح کلیدی پیوت پوینت (Pivot, Support 1, Resistance 1) از کندل روز گذشته"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
    try:
        r = SESSION.get(url, timeout=8)
        if r.status_code == 200:
            res = r.json()["chart"]["result"][0]
            quotes = res["indicators"]["quote"][0]
            highs = [x for x in quotes.get("high", []) if x is not None]
            lows = [x for x in quotes.get("low", []) if x is not None]
            closes = [x for x in quotes.get("close", []) if x is not None]
            if len(closes) >= 2:
                h, l, c = highs[-2], lows[-2], closes[-2]
                pivot = (h + l + c) / 3
                r1 = (2 * pivot) - l
                s1 = (2 * pivot) - h
                return {"pivot": pivot, "r1": r1, "s1": s1}
    except Exception as e:
        print(f"[خطا در محاسبه پیوت {symbol}]: {e}")
    return None

def parse_numeric(val):
    if not val:
        return None
    try:
        clean = val.replace("%", "").replace("K", "").replace("M", "").replace("B", "").strip()
        return float(clean)
    except Exception:
        return None

def fetch_calendar_data():
    calendar_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    if CACHE_PATH.exists():
        modified_time = CACHE_PATH.stat().st_mtime
        age_hours = (time.time() - modified_time) / 3600
        if age_hours < CONFIG["CALENDAR_CACHE_TTL_HOURS"]:
            try:
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    try:
        r = SESSION.get(calendar_url, timeout=12)
        if r.status_code == 200:
            data = r.json()
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] تقویم هفتگی بروز شد.")
            return data
    except Exception as e:
        print(f"[خطا در تقویم]: {e}")
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# ======================= ۱. گزارش جامع صبحگاهی (Morning Briefing) =======================
def build_morning_briefing():
    events = fetch_calendar_data()
    now_iran = datetime.datetime.now(IRAN_TZ)
    today_date_str = now_iran.strftime("%Y-%m-%d")
    
    # فیلتر رویدادهای امروز
    today_events = []
    for ev in events:
        d_str = ev.get("date", "")
        try:
            ev_dt_iran = datetime.datetime.fromisoformat(d_str).astimezone(IRAN_TZ)
            if ev_dt_iran.strftime("%Y-%m-%d") == today_date_str:
                today_events.append((ev_dt_iran, ev))
        except Exception:
            pass
            
    today_events.sort(key=lambda x: x[0])
    
    # ساخت خطوط رویدادها
    event_lines = []
    for dt_obj, ev in today_events:
        impact = ev.get("impact")
        if impact in ["High", "Medium"]:
            icon = "🔴" if impact == "High" else "🟡"
            t_str = dt_obj.strftime("%H:%M")
            title = ev.get("title")
            country = ev.get("country")
            fc = ev.get("forecast") or "---"
            event_lines.append(f"{icon} <b>ساعت {t_str}:</b> #{country} | {title} (پیش‌بینی: <code>{fc}</code>)")
            
    events_block = "\n".join(event_lines) if event_lines else "▫️ رویداد با درجه اهمیت بالا برای امروز ثبت نشده است."
    
    # استخراج سطوح پیوت و شاخص دلار
    pivots = get_pivot_points("GC=F")
    pivot_text = ""
    if pivots:
        pivot_text = (
            f"📍 <b>سطوح پیوت و حمایت/مقاومت انس طلا (امروز):</b>\n"
            f"▫️ مقاومت اول (R1): <code>{pivots['r1']:.1f}</code>\n"
            f"▫️ پیوت اصلی (P): <code>{pivots['pivot']:.1f}</code>\n"
            f"▫️ حمایت اول (S1): <code>{pivots['s1']:.1f}</code>\n"
        )
        
    dxy_data = get_forex_precision_data("DX-Y.NYB")
    dxy_text = ""
    if dxy_data:
        sign = "+" if dxy_data["daily_change"] >= 0 else ""
        dxy_text = f"💵 <b>شاخص دلار (DXY):</b> <code>{dxy_data['price']:.2f}</code> | <b>{sign}{dxy_data['daily_change']:.2f}%</b>\n"

    message = f"""☀️ <b>برنامه معاملاتی و تقویم اقتصادی امروز ({now_iran.strftime('%Y/%m/%d')})</b>

<i>صبح بخیر همراهان عزیز؛ رویدادهای مهم امروز به وقت تهران:</i>

{events_block}

─────────────────
{pivot_text}{dxy_text}
⚠️ <i>توصیه روز: در ساعات قبل و بعد از رویدادهای قرمز، اسپرد کارگزاری‌ها باز می‌شود. پوزیشن‌های خود را با استاپ‌لاس و مدیریت سرمایه ایمن کنید.</i>
─────────────────
🆔 @pipversefactory | #برنامه_معاملاتی #تقویم_روز
"""
    return message

# ======================= ۲. پیش‌هشدار ۶۰ دقیقه قبل از خبر =======================
def determine_market_expectation(title, country, forecast, previous):
    fc_val = parse_numeric(forecast)
    prev_val = parse_numeric(previous)
    if fc_val is None or prev_val is None:
        return None, "انتظارات بر اساس بیانیه و سخنرانی مشخص می‌شود"
    is_neg = any(w in title.lower() for w in ["unemployment", "jobless", "claims"])
    if fc_val > prev_val:
        is_bullish = not is_neg
    elif fc_val < prev_val:
        is_bullish = is_neg
    else:
        return None, "پیش‌بینی تغییر خاصی نسبت به دوره قبل نشان نمی‌دهد"
    if is_bullish:
        return True, f"انتظار رشد و تقویت #{country}"
    else:
        return False, f"انتظار افت و تضعیف #{country}"

def get_pair_projected_direction(country, symbol, is_currency_bullish):
    if is_currency_bullish is None:
        return "⚪ وابسته به ارقام نهایی"
    if "GC=F" in symbol:
        return "🔴 نزولی (احتمال افت طلا)" if is_currency_bullish else "🟢 صعودی (احتمال رشد طلا)"
    if "DX-Y.NYB" in symbol:
        return "🟢 صعودی (تقویت شاخص دلار)" if is_currency_bullish else "🔴 نزولی (تضعیف شاخص دلار)"
    clean = symbol.replace("=X", "")
    base = clean[:3]
    quote = clean[3:]
    if country == base:
        return "🟢 صعودی (Bullish)" if is_currency_bullish else "🔴 نزولی (Bearish)"
    elif country == quote:
        return "🔴 نزولی (Bearish)" if is_currency_bullish else "🟢 صعودی (Bullish)"
    return "⚪ خنثی"

def build_pre_news_alert(event):
    country = event.get("country", "")
    title = event.get("title", "")
    forecast = event.get("forecast") or "نامشخص"
    previous = event.get("previous") or "نامشخص"
    time_str = format_event_time_iran(event.get("date", ""))
    
    country_display = COUNTRY_FLAGS.get(country, f"🌐 #{country}")
    is_bullish, expectation_desc = determine_market_expectation(title, country, forecast, previous)
    explanation = get_explanation(title)
    
    pairs = PAIRS_MAP.get(country, [])
    pairs_lines = []
    for item in pairs:
        data = get_forex_precision_data(item["symbol"])
        decimals = 2 if ("GC=F" in item["symbol"] or "DX-Y.NYB" in item["symbol"]) else 4
        price_str = f"<code>{data['price']:.{decimals}f}</code>" if data else "..."
        projected_dir = get_pair_projected_direction(country, item["symbol"], is_bullish)
        pairs_lines.append(f"▪️ <b>{item['name']}</b>: {price_str}\n   ↳ جهت احتمالی: <b>{projected_dir}</b>")
        
    pairs_text = "\n\n".join(pairs_lines) if pairs_lines else "▫️ جفت‌ارزهای ماژور بازار"
    
    pivots_text = ""
    if country == "USD":
        pv = get_pivot_points("GC=F")
        if pv:
            pivots_text = f"\n📍 <b>سطوح کلیدی انس طلا:</b> مقاومت: <code>{pv['r1']:.1f}</code> | پیوت: <code>{pv['pivot']:.1f}</code> | حمایت: <code>{pv['s1']:.1f}</code>\n"

    message = f"""⏳ <b>هشدار تقویم فارکس (۱ ساعت تا رویداد مهم)</b>

📌 <b>رویداد پیش‌رو:</b> {title}
🌍 <b>ارز تحت تأثیر:</b> {country_display}
⏰ <b>زمان دقیق انتشار:</b> <code>{time_str}</code>

📋 <b>داده‌های پیش‌بینی بازار:</b>
▫️ <b>پیش‌بینی (Forecast):</b> <code>{forecast}</code>
▫️ <b>دوره قبل (Previous):</b> <code>{previous}</code>
▫️ <b>دیدگاه کلی بازار:</b> <b>{expectation_desc}</b>

📝 <b>توضیح کاربردی رویداد:</b>
<i>{explanation}</i>
{pivots_text}
🎯 <b>تأثیر و جهت احتمالی حرکت نمادها (صعودی/نزولی):</b>
{pairs_text}

💡 <b>سناریوهای مشروط لحظه انتشار:</b>
🔹 <b>اگر رقم نهایی قوی‌تر از پیش‌بینی اعلام شود:</b> تقویت #{country} (افت طلا و جفت‌ارزهای معکوس)
🔹 <b>اگر رقم نهایی ضعیف‌تر از پیش‌بینی اعلام شود:</b> تضعیف #{country} (صعود طلا و جفت‌ارزهای معکوس)

⚠️ <i>توصیه: در آستانه رویدادهای سنگین از ورود هیجانی خودداری نمایید.</i>
─────────────────
🆔 @pipversefactory | #{country} #پیش_بینی_فارکس #طلا
"""
    return message

# ======================= ۳. گزارش لحظه اعلام خبر و واکنش چارت =======================
def build_post_news_alert(event):
    country = event.get("country", "")
    title = event.get("title", "")
    forecast = event.get("forecast") or "---"
    previous = event.get("previous") or "---"
    actual = event.get("actual") or "اعلام نشده"
    time_str = format_event_time_iran(event.get("date", ""))
    country_display = COUNTRY_FLAGS.get(country, f"🌐 #{country}")
    
    act_num = parse_numeric(actual)
    fc_num = parse_numeric(forecast)
    analysis_line = "⏳ در انتظار انتشار ارقام نهایی"
    if act_num is not None and fc_num is not None:
        is_neg = any(w in title.lower() for w in ["unemployment", "jobless", "claims"])
        act_better = (act_num > fc_num) if not is_neg else (act_num < fc_num)
        if act_better:
            analysis_line = f"🟢 <b>عدد بهتر از انتظارات منتشر شد:</b> عامل محرک برای <b>تقویت #{country}</b>"
        else:
            analysis_line = f"🔴 <b>عدد ضعیف‌تر از انتظارات منتشر شد:</b> عامل محرک برای <b>تضعیف #{country}</b>"
            
    pairs = PAIRS_MAP.get(country, [])
    pairs_lines = []
    for item in pairs:
        data = get_forex_precision_data(item["symbol"])
        if data:
            decimals = 2 if ("GC=F" in item["symbol"] or "DX-Y.NYB" in item["symbol"]) else 4
            r_15 = data["reaction_15m"]
            r_sign = "+" if r_15 >= 0 else ""
            r_icon = "🟢 صعودی" if r_15 > 0.03 else ("🔴 نزولی" if r_15 < -0.03 else "⚪ نوسان اندک")
            d_chg = data["daily_change"]
            d_sign = "+" if d_chg >= 0 else ""
            pairs_lines.append(
                f"🔸 <b>{item['name']}</b>: <code>{data['price']:.{decimals}f}</code>\n"
                f"   ▫️ واکنش لحظه‌ای (۱۵ دقیقه): {r_icon} <b>({r_sign}{r_15:.2f}%)</b>\n"
                f"   ▫️ نوسان ۲۴ ساعته: <code>{d_sign}{d_chg:.2f}%</code>"
            )
    pairs_block = "\n\n".join(pairs_lines) if pairs_lines else "▫️ داده‌های زنده قیمت در دسترس نیست."

    message = f"""🚨 <b>گزارش نهایی انتشار خبر فارکس (High Impact)</b>

📌 <b>رویداد:</b> {title}
🌍 <b>ارز پایه:</b> {country_display}
⏰ <b>زمان اعلام:</b> <code>{time_str}</code>

📋 <b>ارقام قطعی تقویم اقتصادی:</b>
▫️ <b>واقعی (Actual):</b> <code>{actual}</code>
▫️ <b>پیش‌بینی (Forecast):</b> <code>{forecast}</code>
▫️ <b>دوره قبل (Previous):</b> <code>{previous}</code>

💡 <b>تفسیر بنیادی گزارش:</b>
{analysis_line}

📈 <b>واکنش واقعی و زنده چارت (درصد سود/ضرر لحظه‌ای):</b>
{pairs_block}

─────────────────
🆔 @pipversefactory | #{country} #Forex #طلا #DXY
"""
    return message

# ======================= ارسال پیام به تلگرام =======================
def send_telegram_message(chat_id, text, reply_markup=None):
    token = CONFIG["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = SESSION.post(url, json=payload, timeout=12)
        res = r.json()
        if res.get("ok"):
            return True
        else:
            print(f"[خطای ارسال به {chat_id}]: {res.get('description')}")
    except Exception as e:
        print(f"[خطای شبکه تلگرام]: {e}")
    return False

# ======================= ۴. بخش تعاملی پی‌وی ربات (پاسخ به کاربران) =======================
def get_last_update_id():
    if LAST_UPDATE_PATH.exists():
        try:
            return int(LAST_UPDATE_PATH.read_text().strip())
        except Exception:
            pass
    return 0

def save_last_update_id(uid):
    try:
        LAST_UPDATE_PATH.write_text(str(uid))
    except Exception:
        pass

def handle_user_command(chat_id, text, first_name):
    cmd = text.strip().lower()
    
    if cmd in ["/start", "شروع", "سلام", "راهنما"]:
        welcome_text = f"""سلام <b>{first_name}</b> عزیز! 👋
به ربات تخصصی و هوشمند تحلیل فارکس <b>Pipverse</b> خوش آمدید.

📌 <b>دستورات قابل استفاده:</b>
▫️ <code>/gold</code> - قیمت لحظه‌ای، نوسان و پیوت پوینت‌های انس طلا
▫️ <code>/dxy</code> - وضعیت زنده شاخص دلار آمریکا
▫️ <code>/calendar</code> - رویدادهای مهم تقویم اقتصادی امروز
▫️ <code>/levels</code> - سطوح حمایت و مقاومت کلیدی طلا
▫️ <code>/pairs</code> - نرخ جفت‌ارزهای ماژور فارکس

📢 برای دریافت لحظه‌ای اخبار، به کانال ما بپیوندید: @pipversefactory
"""
        send_telegram_message(chat_id, welcome_text, DEFAULT_KEYBOARD)
        
    elif cmd in ["/gold", "طلا", "انس"]:
        gold = get_forex_precision_data("GC=F")
        pv = get_pivot_points("GC=F")
        if gold:
            r_sign = "+" if gold["reaction_15m"] >= 0 else ""
            d_sign = "+" if gold["daily_change"] >= 0 else ""
            icon = "🟢" if gold["reaction_15m"] >= 0 else "🔴"
            reply = f"""🥇 <b>وضعیت لحظه‌ای انس جهانی طلا (XAU/USD):</b>

💵 <b>قیمت کنونی:</b> <code>{gold['price']:.2f}</code> دلار
▫️ واکنش ۱۵ دقیقه اخیر: {icon} <b>{r_sign}{gold['reaction_15m']:.2f}%</b>
▫️ نوسان ۲۴ ساعته: <code>{d_sign}{gold['daily_change']:.2f}%</code>
"""
            if pv:
                reply += f"""
📍 <b>سطوح پیوت امروز:</b>
▪️ مقاومت اول (R1): <code>{pv['r1']:.1f}</code>
▪️ پیوت مرکزی (P): <code>{pv['pivot']:.1f}</code>
▪️ حمایت اول (S1): <code>{pv['s1']:.1f}</code>
"""
            send_telegram_message(chat_id, reply, DEFAULT_KEYBOARD)
            
    elif cmd in ["/dxy", "دلار"]:
        dxy = get_forex_precision_data("DX-Y.NYB")
        if dxy:
            d_sign = "+" if dxy["daily_change"] >= 0 else ""
            icon = "🟢" if dxy["daily_change"] >= 0 else "🔴"
            reply = f"""💵 <b>وضعیت زنده شاخص دلار آمریکا (DXY):</b>

▫️ <b>شاخص فعلی:</b> <code>{dxy['price']:.3f}</code>
▫️ نوسان امروز: {icon} <b>{d_sign}{dxy['daily_change']:.2f}%</b>
"""
            send_telegram_message(chat_id, reply, DEFAULT_KEYBOARD)
            
    elif cmd in ["/levels", "سطوح", "پیوت"]:
        pv = get_pivot_points("GC=F")
        if pv:
            reply = f"""🎯 <b>سطوح کلیدی و پیوت پوینت‌های انس طلا:</b>

▫️ مقاومت اول (R1): <code>{pv['r1']:.1f}</code>
▫️ پیوت اصلی (Pivot): <code>{pv['pivot']:.1f}</code>
▫️ حمایت اول (S1): <code>{pv['s1']:.1f}</code>

💡 <i>بالای پیوت تمایل به صعود، و زیر پیوت احتمال اصلاح بیشتر است.</i>
"""
            send_telegram_message(chat_id, reply, DEFAULT_KEYBOARD)
            
    elif cmd in ["/calendar", "تقویم", "اخبار"]:
        msg = build_morning_briefing()
        send_telegram_message(chat_id, msg, DEFAULT_KEYBOARD)
        
    elif cmd in ["/pairs", "جفت ارزها"]:
        p_lines = []
        for s, n in [("EURUSD=X", "EUR/USD"), ("GBPUSD=X", "GBP/USD"), ("USDJPY=X", "USD/JPY"), ("USDCAD=X", "USD/CAD")]:
            dt = get_forex_precision_data(s)
            if dt:
                sgn = "+" if dt["daily_change"] >= 0 else ""
                ic = "🟢" if dt["daily_change"] >= 0 else "🔴"
                p_lines.append(f"▪️ <b>{n}</b>: <code>{dt['price']:.4f}</code> | {ic} <b>{sgn}{dt['daily_change']:.2f}%</b>")
        reply = "📊 <b>نرخ جفت‌ارزهای اصلی بازار فارکس:</b>\n\n" + "\n".join(p_lines)
        send_telegram_message(chat_id, reply, DEFAULT_KEYBOARD)

def process_telegram_updates(last_id):
    token = CONFIG["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/getUpdates?offset={last_id + 1}&timeout=1"
    try:
        r = SESSION.get(url, timeout=5)
        if r.status_code == 200:
            res = r.json()
            if res.get("ok"):
                for upd in res.get("result", []):
                    uid = upd.get("update_id")
                    last_id = max(last_id, uid)
                    msg = upd.get("message")
                    if msg and "text" in msg:
                        chat_id = msg["chat"]["id"]
                        text = msg["text"]
                        fname = msg.get("from", {}).get("first_name", "دوست گرامی")
                        # فقط اگر پیام خصوصی باشد پاسخ بدهد
                        if msg.get("chat", {}).get("type") == "private":
                            handle_user_command(chat_id, text, fname)
                save_last_update_id(last_id)
    except Exception:
        pass
    return last_id

# ======================= ذخیره و بارگذاری رویدادها =======================
def load_sent_events():
    if SENT_EVENTS_PATH.exists():
        try:
            with open(SENT_EVENTS_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_sent_events(sent_set):
    try:
        with open(SENT_EVENTS_PATH, "w", encoding="utf-8") as f:
            json.dump(list(sent_set), f, ensure_ascii=False)
    except Exception as e:
        print(f"خطا در ذخیره رویدادها: {e}")

# ======================= حلقه اصلی پردازش ربات =======================
def run_bot():
    run_health_server()
    print("=" * 65)
    print("   ربات پیشرفته و چندمنظوره فارکس Pipversefactorybot فعال شد   ")
    print(f"   کانال تلگرام: {CONFIG['TELEGRAM_CHANNEL_ID']}")
    print("   امکانات: گزارش صبحگاهی + پیش‌هشدار + واکنش قیمت + پاسخ تعاملی")
    print("=" * 65)
    
    sent_events = load_sent_events()
    last_update_id = get_last_update_id()
    
    while True:
        try:
            # ۱. پاسخ به دستورات کاربران در چت خصوصی
            last_update_id = process_telegram_updates(last_update_id)
            
            # ۲. بررسی زمان ارسال گزارش صبحگاهی (ساعت 08:30 صبح به وقت ایران)
            now_iran = datetime.datetime.now(IRAN_TZ)
            today_str = now_iran.strftime("%Y-%m-%d")
            morning_key = f"morning_sent_{today_str}"
            
            # اگر بعد از ساعت 08:00 صبح است و هنوز گزارش امروز ارسال نشده
            if now_iran.hour >= 8 and morning_key not in sent_events:
                print(f"[{now_iran.strftime('%H:%M:%S')}] ارسال گزارش جامع صبحگاهی به کانال...")
                morning_msg = build_morning_briefing()
                if send_telegram_message(CONFIG["TELEGRAM_CHANNEL_ID"], morning_msg, DEFAULT_KEYBOARD):
                    sent_events.add(morning_key)
                    save_sent_events(sent_events)
                    time.sleep(2)

            # ۳. پایش تقویم اقتصادی هفتگی
            events = fetch_calendar_data()
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            
            for ev in events:
                if ev.get("impact") != "High":
                    continue
                
                base_id = f"{ev.get('country')}_{ev.get('title')}_{ev.get('date')}"
                pre_id = f"pre_{base_id}"
                post_id = f"post_{base_id}"
                
                event_date_str = ev.get("date", "")
                try:
                    event_dt = datetime.datetime.fromisoformat(event_date_str)
                    diff_minutes = (event_dt - now_utc).total_seconds() / 60
                    
                    # الف) ارسال پیش‌هشدار ۱ ساعت قبل از خبر (بازه ۵۰ تا ۷۰ دقیقه قبل)
                    if 50 <= diff_minutes <= 70 and pre_id not in sent_events:
                        print(f"\n[!] پیش‌هشدار ۱ ساعت قبل: {ev.get('title')} ({ev.get('country')})")
                        msg = build_pre_news_alert(ev)
                        if send_telegram_message(CONFIG["TELEGRAM_CHANNEL_ID"], msg, DEFAULT_KEYBOARD):
                            sent_events.add(pre_id)
                            save_sent_events(sent_events)
                            time.sleep(2)
                            
                    # ب) ارسال گزارش انتشار خبر و واکنش زنده چارت (از ۵ دقیقه قبل تا ۳۰ دقیقه بعد)
                    if -30 <= diff_minutes <= 5 and post_id not in sent_events:
                        print(f"\n[!] گزارش لحظه اعلام خبر: {ev.get('title')} ({ev.get('country')})")
                        msg = build_post_news_alert(ev)
                        if send_telegram_message(CONFIG["TELEGRAM_CHANNEL_ID"], msg, DEFAULT_KEYBOARD):
                            sent_events.add(post_id)
                            save_sent_events(sent_events)
                            time.sleep(2)
                except Exception:
                    pass

        except Exception as e:
            print(f"[خطای پایش]: {e}")
            
        time.sleep(CONFIG["CHECK_INTERVAL_SECONDS"])


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--morning":
            print("ارسال تست گزارش جامع صبحگاهی به کانال...")
            m = build_morning_briefing()
            send_telegram_message(CONFIG["TELEGRAM_CHANNEL_ID"], m, DEFAULT_KEYBOARD)
        elif arg == "--test-pre":
            print("ارسال تست پیش‌هشدار ۱ ساعت قبل با دکمه‌های شیشه‌ای...")
            test_event = {
                "title": "Non-Farm Employment Change (NFP)",
                "country": "USD",
                "date": "2026-11-06T08:30:00-05:00",
                "impact": "High",
                "forecast": "65K",
                "previous": "29K"
            }
            m = build_pre_news_alert(test_event)
            send_telegram_message(CONFIG["TELEGRAM_CHANNEL_ID"], m, DEFAULT_KEYBOARD)
        elif arg == "--test":
            print("ارسال تست گزارش انتشار خبر...")
            test_event = {
                "title": "Non-Farm Employment Change (NFP)",
                "country": "USD",
                "date": "2026-11-06T08:30:00-05:00",
                "impact": "High",
                "forecast": "65K",
                "previous": "29K",
                "actual": "72K"
            }
            m = build_post_news_alert(test_event)
            send_telegram_message(CONFIG["TELEGRAM_CHANNEL_ID"], m, DEFAULT_KEYBOARD)
    else:
        run_bot()
