"""
Price_Data_Tool V2.9 — Статистически пулт за канала (сезонност, серии, линии)
Модернизиран UI (customtkinter), 10 актива, 5s polling, multi-timeframe,
вграден график, real-time Telegram алерти.

V2.9 (03.08.2026): скенерът говори езика на канала — ДЕН % (тялото на
деня), СЕРИЯ (пореден едноцветен ден), ОТН.ОБЕМ (срещу 30-дневната средна),
ОТ ВРЪХ (под върха за годината); FIB 61.8% погребан. Нов бутон ⏳ ВРЪЩАНЕ:
медиана/средно дни до затваряне над нивото отпреди спад ≥3/5/7/10/15%.
V2.9.1: таблицата подредена — СЕДМИЦА/ПОСОКА колоните вън (стрелката и
отскокът следват ДЕНЯ), седмичният размах на първия ред от седмицата,
серията без емоджи (местеше колоните), дата на рекорда във ВРЪЩАНЕ.
V2.9.2: СЛЕД 3 ДНИ — и спадът, и отскокът, от затварянето на червения ден
(само „+отскок от дъното" беше почти винаги положителен = лъжеше).
V2.9.3 (спец. ui-ux-engineer): седмицата = фонова лента, денят = цвят на
текста; 6-цветната схема погребана (броят повторения е текст в СЕДМИЦАТА);
СЛЕД 3Д с ▼/▲ в двата цвята; неутрален текст по подразбиране (не зелен);
ОТН.ОБЕМ ≥2× свети в warn.
V2.9.4: СЕДМИЦАТА вертикално (номер/размах/повторения на 3 реда в полето);
докладите от бутоните през единна цветна граматика (_print_report): TITLE
лента, сиви рамки/етикети, числата по знак, уговорките оранж; СЕЗОНЕН
АНАЛИЗ и МОДЕЛИ на системата на скенера; служебните съобщения = info.
V2.9.5: ЛИНИИ ×10 в истински колони (АКТИВ|ЦЕНА СЕГА|200W|СПРЯМО|300W|
СПРЯМО, без повтарящи се етикети и емоджи); бутоните групирани по действие:
лилави = в таблицата, сини ↗ = отделен прозорец, сиви = помощни.
V2.9.6: ТРЕНД И НИВА ред по ред (300W със собствен цвят; Стена червена,
Под зелен); POL → макро активи (ЗЛАТО/DXY/SP500/RUSSELL) в списъка;
макро лента горе вдясно (🥇/DXY/SPX с дневния ход, при пълно опресняване).
V3.0: 🔻 СЕРИИ (след N поредни дни — следващият), 🔗 КОРЕЛАЦИИ (90д срещу
1г, крипто↔макро heatmap), 💧 ДЪНА (топ-10 просадки + подводна крива);
бутоните в два реда: ред А = в таблицата, ред Б = прозорци ↗.
V3.0.2: СЕЗОННОСТТА редизайн — ОТСКОК≥3% (вечно 100%) и ТРЕНД погребани,
календарни дати на седмиците, „N от X години", ⚖ двупосочните отбелязани,
фон само при ≥4 повторения, шумът е брояч, честна бележка под таблицата.
V2.3 (03.08.2026): нов интерфейс с карти (пасва на всякакъв екран), бутоните
закотвени долу, графиките в нормални прозорци ДО главния (без fullscreen/plt),
половинки на шрифта, човешки текстове.
V2.2 (03.08.2026): РЕДИЗАЙН КЪМ СТАТИСТИКА — всички „ВХОД/ИЗХОД/ЦЕЛ/Прогноза"
етикети станаха описателни (календарните сигнали са погребани с 6.5 г. данни);
📅 МЕСЕЧНА МАТРИЦА (години × месеци, цялата история, средно+медиана+дял зелени);
размер на текста с памет (за различни екрани); реален обем вместо Δкапитализация.
V2.1: 🎬 ВИДЕО ЧИСЛА панел · strftime бъг · POL вместо MATIC · .exe пътища.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import customtkinter as ctk
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime, timedelta
import threading
import pytz
import requests
import os
import re
import sys
import json
import logging
import seaborn as sns

# --- Logging ---
# При компилиран .exe (PyInstaller) __file__ сочи във вътрешната папка на пакета —
# config.json и логът трябва да живеят ДО екзето, иначе настройките се губят.
if getattr(sys, 'frozen', False):
    _SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# encoding='utf-8' е задължителен: Windows конзолата е cp1252 и всяко
# кирилско съобщение гърмеше с UnicodeEncodeError в компилирания .exe
# QA M4: delay=True — файлът се отваря при ПЪРВИЯ запис, не при import.
# Иначе екзе в папка без права за писане (Program Files) умира тихо преди GUI.
_handlers = [logging.StreamHandler()]
try:
    _handlers.append(logging.FileHandler(
        os.path.join(_SCRIPT_DIR, 'price_data_tool.log'),
        encoding='utf-8', delay=True))
except Exception:
    pass
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=_handlers
)
logger = logging.getLogger(__name__)

# --- Настройки ---
sns.set_theme(style="darkgrid")
plt.rcParams['figure.figsize'] = (12, 6)

# --- Config ---
def load_config():
    """Зарежда config.json."""
    cfg_path = os.path.join(_SCRIPT_DIR, 'config.json')
    cfg = {}
    try:
        with open(cfg_path, 'r') as f:
            cfg = json.load(f)
    except Exception as e:
        logger.warning(f"Не мога да заредя config.json: {e}")


    return cfg

CONFIG = load_config()

# Версията на едно място — заглавието на прозореца я чете оттук.
VERSION = "3.1"

# --- Символи (10 общо) ---
# V2.9.6 (Koko): POL вън; вътре макро пазарите, които движат крипто —
# злато, доларовият индекс, S&P 500, Russell 2000 (Yahoo кодове).
DEFAULT_SYMBOLS = [
    "BTC-USD", "XRP-USD", "ETH-USD", "SOL-USD", "DOGE-USD",
    "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD",
    "GC=F", "DX-Y.NYB", "^GSPC", "^RUT",
]

# Човешки имена за не-крипто тикерите (Yahoo кодовете са грозни)
PRETTY_SYM = {"GC=F": "ЗЛАТО", "DX-Y.NYB": "DXY",
              "^GSPC": "SP500", "^RUT": "RUSSELL"}


def pretty_sym(sym):
    return PRETTY_SYM.get(sym, sym.replace("-USD", ""))

# (V2.2) MARKET_CAP_APPROX премахнат — обемът е реалният от yfinance.

# ── V2.4: ПАЛИТРИ ЗА ТЕМА ────────────────────────────────────────────────
# Всеки цвят в интерфейса минава оттук — превключването е една смяна на речника.
THEMES = {
    "dark": dict(
        bg="#0E1117", card="#161B26", title="#6E7788", text="#D6DBE4",
        up="#00E676", down="#FF5252", warn="#FFB74D", info="#4FC3F7",
        wait="#FFEE58", muted="#8A93A2", blue="#00BFFF",
        log_bg="#0A0D12", pink="#FF00FF", recovery="#FFFF00",
        pump_bg="#006400", pump_fg="white",
        wk_bg_up="#0F2418", wk_bg_down="#261114",
        wk_bg_up_hot="#143A24", wk_bg_down_hot="#3A181C",
        title_bg="#1A2233",
    ),
    "light": dict(
        bg="#E9EDF3", card="#FFFFFF", title="#5A6472", text="#1A2230",
        up="#0E8A3E", down="#C62828", warn="#B26A00", info="#0B72B8",
        wait="#8A6D00", muted="#6B7482", blue="#0B72B8",
        log_bg="#F7F9FC", pink="#AD1457", recovery="#8B6E00",
        pump_bg="#1E7C46", pump_fg="white",
        wk_bg_up="#E1F2E6", wk_bg_down="#F9E3E3",
        wk_bg_up_hot="#C8E8D2", wk_bg_down_hot="#F3CFCF",
        title_bg="#DCE6F2",
    ),
}


# --- Помощни функции ---
def fmt_price(price):
    return ".4f" if price < 5 else ".2f" if price < 100 else ".0f"


def get_day_history(df, month, day):
    """Връща (avg_return, bulls_count, bears_count, last_bull_yr, last_bear_yr) за даден календарен ден."""
    mask = (df.index.month == month) & (df.index.day == day)
    stats = df[mask]
    if stats.empty:
        return 0, 0, 0, "--", "--"
    avg_ret = stats['Return'].mean()
    bulls_df = stats[stats['Return'] > 0]
    bears_df = stats[stats['Return'] < 0]
    last_bull = str(bulls_df.index.year.max())[2:] if not bulls_df.empty else "--"
    last_bear = str(bears_df.index.year.max())[2:] if not bears_df.empty else "--"
    return avg_ret, len(bulls_df), len(bears_df), last_bull, last_bear


def fix_multiindex(df):
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df.columns = df.columns.get_level_values(0)
        except Exception as e:
            logger.warning(f"fix_multiindex: {e}")
    if 'Close' not in df.columns and 'Adj Close' in df.columns:
        df['Close'] = df['Adj Close']


# ==========================================
# DATA ENGINE
# ==========================================

def bg_ord(n):
    """Наредният суфикс на български: 1-ви, 2-ри, 7-ми, 8-ми, иначе -ти."""
    if n % 100 in (11, 12):
        return "ти"
    last = n % 10
    if last == 1:
        return "ви"
    if last == 2:
        return "ри"
    if last in (7, 8):
        return "ми"
    return "ти"


class DataEngine:
    def __init__(self):
        self.symbol = CONFIG.get('default_symbol', 'XRP-USD')
        self.daily_data = None
        self.hourly_data = None
        self.tz_bg = pytz.timezone('Europe/Sofia')
        self._lock = threading.Lock()

    def set_symbol(self, sym):
        self.symbol = sym

    def fetch_all_data(self):
        logger.info(f"Тегля данни за {self.symbol}...")
        try:
            # А1 (03.08): period="max" — с "5y" скенерът и „Днес през годините" не
            # виждаха 2017-2020. Една дума = двойно повече история.
            daily = yf.download(self.symbol, period="max", interval="1d", auto_adjust=True, progress=False)
            fix_multiindex(daily)

            hourly = yf.download(self.symbol, period="730d", interval="1h", auto_adjust=True, progress=False)
            fix_multiindex(hourly)

            # Конвертиране часова зона
            if hourly is not None and not hourly.empty:
                hourly.index = hourly.index.tz_convert(self.tz_bg)
                hourly['Day'] = hourly.index.day_name()
                hourly['Hour'] = hourly.index.hour

            # Метрики
            if daily is not None and not daily.empty:
                daily['Day'] = daily.index.day_name()
                daily['Return'] = daily['Close'].pct_change() * 100
                daily['Month'] = daily.index.month_name()
                daily['WeekNum'] = daily.index.isocalendar().week
                daily['SMA200'] = daily['Close'].rolling(window=200).mean()
                daily['SMA300'] = daily['Close'].rolling(window=300).mean()

            with self._lock:
                self.daily_data = daily
                self.hourly_data = hourly

            logger.info(f"Успех! {self.symbol} зареден.")
            return True
        except Exception as e:
            logger.error(f"Грешка при теглене: {e}")
            return False

    def get_detailed_crash_info(self, crash_date):
        """Извлича час на старт, час на дъно и ценови рейндж."""
        if self.hourly_data is None or self.hourly_data.empty:
            return "N/A", "N/A", 0, 0
        # БЪГ ПОПРАВЕН (03.08.2026): беше '%Y-%M-%D' (%M = минути, %D = мм/дд/гг)
        # → .loc[] винаги гърмеше и функцията връщаше "Old" за ВСЕКИ срив.
        date_str = crash_date.strftime('%Y-%m-%d')
        try:
            day_slice = self.hourly_data.loc[date_str]
            if day_slice.empty:
                return "Old", "Old", 0, 0
            high_idx = day_slice['High'].idxmax()
            start_price = day_slice.loc[high_idx]['High']
            start_time = high_idx.strftime('%H:%M')
            low_idx = day_slice['Low'].idxmin()
            end_price = day_slice.loc[low_idx]['Low']
            end_time = low_idx.strftime('%H:%M')
            return start_time, end_time, start_price, end_price
        except Exception:
            return "Old", "Old", 0, 0

    def get_recovery_price(self, crash_date, bottom_price):
        """Търси най-високата цена (възстановяване) в следващите 3 дни"""
        recovery_max = 0
        next_days = [crash_date + timedelta(days=i) for i in range(1, 4)]
        try:
            if self.hourly_data is not None and not self.hourly_data.empty:
                for d in next_days:
                    d_str = d.strftime('%Y-%m-%d')
                    if d_str in self.hourly_data.index:
                        day_high = self.hourly_data.loc[d_str]['High'].max()
                        if day_high > recovery_max:
                            recovery_max = day_high
            if recovery_max == 0:
                for d in next_days:
                    if d in self.daily_data.index:
                        day_high = self.daily_data.loc[d]['High']
                        if day_high > recovery_max:
                            recovery_max = day_high
            return recovery_max
        except Exception as e:
            logger.warning(f"get_recovery_price: {e}")
            return 0

    def recovery_ladder(self, thresholds=(3, 5, 7, 10, 15)):
        """V2.9 (идея №5): след ден със спад ≥X% — колко дни до връщане?

        Епизод = ПЪРВИЯТ ден от поредица дни-спадове (съседните се броят
        за един, както при седмичните фитили — иначе един срив влиза в
        сметката три пъти). Върнат = първото ЗАТВАРЯНЕ обратно ≥
        затварянето от деня ПРЕДИ спада.
        """
        df = self.daily_data
        if df is None or len(df) < 40:
            return []
        closes = df['Close'].to_numpy()
        opens = df['Open'].to_numpy()
        day_pct = np.where(opens > 0, (closes - opens) / opens * 100, 0.0)
        out = []
        for thr in thresholds:
            drops = np.where(day_pct <= -thr)[0]
            drops = drops[drops > 0]          # трябва ни затваряне „преди"
            starts = [i for k, i in enumerate(drops)
                      if k == 0 or i - drops[k - 1] > 1]
            if not starts:
                continue
            days_list, still_open = [], 0
            worst_days, worst_start = -1, None
            for i in starts:
                target = closes[i - 1]
                after = np.where(closes[i + 1:] >= target)[0]
                if len(after):
                    d = int(after[0]) + 1
                    days_list.append(d)
                    if d > worst_days:
                        worst_days, worst_start = d, df.index[i]
                else:
                    still_open += 1
            out.append({
                'thr': thr, 'episodes': len(starts),
                'median': float(np.median(days_list)) if days_list else None,
                'mean': float(np.mean(days_list)) if days_list else None,
                'worst': int(worst_days) if days_list else None,
                'worst_date': (worst_start.strftime('%d.%m.%Y')
                               if worst_start is not None else None),
                'open': still_open,
            })
        return out

    def streak_stats(self, max_n=7):
        """V3.0: след N поредни едноцветни дни — какво прави СЛЕДВАЩИЯТ.

        runs[i] = кой пореден едноцветен ден е i (по тялото). Случай за
        „след N" = ден, на който серията ДОСТИГА N (може и да продължи
        после) — точно въпросът от ефира.
        """
        df = self.daily_data
        if df is None or len(df) < 60:
            return None
        o = df['Open'].to_numpy()
        c = df['Close'].to_numpy()
        dp = np.where(o > 0, (c - o) / o * 100, 0.0)
        sign = np.sign(np.round(dp, 4))
        runs = np.zeros(len(dp), dtype=int)
        for i in range(len(dp)):
            if sign[i] != 0 and i > 0 and sign[i] == sign[i - 1]:
                runs[i] = runs[i - 1] + 1
            elif sign[i] != 0:
                runs[i] = 1
        out = {'red': [], 'green': []}
        for want, key in ((-1.0, 'red'), (1.0, 'green')):
            for n in range(2, max_n + 1):
                idx = [i for i in range(len(dp) - 1)
                       if sign[i] == want and runs[i] == n]
                if len(idx) < 3:
                    continue
                nxt = dp[[i + 1 for i in idx]]
                out[key].append({
                    'n': n, 'cases': len(idx),
                    'med': float(np.median(nxt)),
                    'green_share': float((nxt > 0).mean() * 100),
                })
        return out

    def drawdown_table(self, top=10):
        """V3.0: топ просадки — връх→дъно→връщане + подводната крива."""
        df = self.daily_data
        if df is None or len(df) < 60:
            return [], None
        c = df['Close']
        runmax = c.cummax()
        dd = (c - runmax) / runmax * 100
        vals = c.to_numpy()
        rm = runmax.to_numpy()
        episodes = []
        start = trough = None
        peak_val = 0.0
        for i in range(1, len(vals)):
            if start is None:
                if vals[i] < rm[i]:
                    start, trough, peak_val = i - 1, i, rm[i]
            else:
                if vals[i] < vals[trough]:
                    trough = i
                if vals[i] >= peak_val:
                    episodes.append((start, trough, i, peak_val))
                    start = trough = None
        if start is not None:
            episodes.append((start, trough, None, peak_val))
        rows = []
        for st, tr, en, pk in episodes:
            if pk <= 0:
                continue
            rows.append({
                'peak_date': df.index[st], 'trough_date': df.index[tr],
                'depth': (vals[tr] - pk) / pk * 100,
                'days_down': (df.index[tr] - df.index[st]).days,
                'days_total': ((df.index[en] - df.index[st]).days
                               if en is not None else None),
            })
        rows.sort(key=lambda r: r['depth'])
        # −2% „просадка" не е просадка — прагът чисти шума от топ листата
        rows = [r for r in rows if r['depth'] <= -5.0]
        return rows[:top], dd

    def find_walls(self, lookback=180, tol=0.01, min_touches=2):
        """V2.5 (Koko): стени и подове — нива с многократни отхвърляния.

        Пример: юлската стена на XRP $1.117 — три докосвания, нула затваряния
        над нея. Алгоритъм: локални върхове/дъна (±2 дни) от последните
        `lookback` дни → клъстери в рамките на ±tol → най-близкият клъстер
        с ≥min_touches докосвания НАД цената (стена) и ПОД нея (под).

        Returns:
            dict: {'wall': {...}|None, 'floor': {...}|None}
        """
        out = {'wall': None, 'floor': None}
        df = self.daily_data
        if df is None or len(df) < 20:
            return out
        d = df.tail(lookback)
        price = d.iloc[-1]['Close']
        highs, lows = [], []
        h, l = d['High'].values, d['Low'].values
        idx = d.index
        for i in range(2, len(d) - 2):
            if h[i] == max(h[i - 2:i + 3]):
                highs.append((idx[i], h[i]))
            if l[i] == min(l[i - 2:i + 3]):
                lows.append((idx[i], l[i]))

        def clusters(points):
            """Групира близките нива (±tol) в клъстери."""
            res = []
            for t, v in sorted(points, key=lambda x: x[1]):
                if res and abs(v - res[-1]['price']) / res[-1]['price'] <= tol:
                    c = res[-1]
                    c['touches'] += 1
                    c['price'] = (c['price'] * (c['touches'] - 1) + v) / c['touches']
                    c['last'] = max(c['last'], t)
                    c['first'] = min(c['first'], t)
                else:
                    res.append({'price': v, 'touches': 1, 'first': t, 'last': t})
            return res

        now = idx[-1]
        # стена: най-близкият клъстер от върхове НАД цената, непробит със затваряне
        cands = [c for c in clusters(highs)
                 if c['touches'] >= min_touches and c['price'] > price
                 and not (d[d.index > c['last']]['Close'] > c['price'] * (1 + tol)).any()]
        if cands:
            c = min(cands, key=lambda c: c['price'])
            out['wall'] = {'price': c['price'], 'touches': c['touches'],
                           'age_days': (now - c['first']).days}
        # под: огледално — дъна ПОД цената
        cands = [c for c in clusters(lows)
                 if c['touches'] >= min_touches and c['price'] < price
                 and not (d[d.index > c['last']]['Close'] < c['price'] * (1 - tol)).any()]
        if cands:
            c = max(cands, key=lambda c: c['price'])
            out['floor'] = {'price': c['price'], 'touches': c['touches'],
                            'age_days': (now - c['first']).days}
        return out

    def get_mtf_summary(self):
        """Multi-timeframe обобщение: 1h/4h/1D/1W."""
        result = {}
        try:
            df = self.daily_data
            hdf = self.hourly_data
            if df is None or df.empty:
                return result

            last = df.iloc[-1]
            price = last['Close']

            # 1D
            result['1D'] = {
                'change': last['Return'],
                'high': last['High'],
                'low': last['Low'],
                'trend': '🐂' if price > last['SMA200'] else '🐻'
            }

            # 1W
            wk = last['WeekNum']
            yr = df.index[-1].year
            mask = (df.index.year == yr) & (df['WeekNum'] == wk)
            wdata = df[mask]
            if not wdata.empty:
                w_open = wdata.iloc[0]['Open']
                w_ret = (price - w_open) / w_open * 100
                result['1W'] = {
                    'change': w_ret,
                    'high': wdata['High'].max(),
                    'low': wdata['Low'].min(),
                }

            # 1h
            if hdf is not None and not hdf.empty and len(hdf) >= 2:
                last_h = hdf.iloc[-1]
                prev_h = hdf.iloc[-2]
                h_ret = (last_h['Close'] - prev_h['Close']) / prev_h['Close'] * 100
                result['1h'] = {'change': h_ret, 'high': last_h['High'], 'low': last_h['Low']}

            # 4h
            if hdf is not None and not hdf.empty and len(hdf) >= 5:
                last_4h = hdf.tail(4)
                h4_open = last_4h.iloc[0]['Open']
                h4_close = last_4h.iloc[-1]['Close']
                h4_ret = (h4_close - h4_open) / h4_open * 100
                result['4h'] = {
                    'change': h4_ret,
                    'high': last_4h['High'].max(),
                    'low': last_4h['Low'].min()
                }

        except Exception as e:
            logger.warning(f"MTF summary грешка: {e}")
        return result

    def monthly_matrix(self):
        """V2.2: Месечна доходност по години — ядрото на статистическата идея.

        Тегли ЦЯЛАТА налична месечна история (не 5-годишния дневен прозорец)
        и връща pivot: редове = години, колони = месеци, стойност = % промяна
        на месеца. Това е отговорът на „как се е движела цената през различните
        години и месеци и има ли повторяемост".

        Returns:
            (pivot DataFrame, str грешка или None)
        """
        try:
            mo = yf.download(self.symbol, period="max", interval="1mo",
                             auto_adjust=True, progress=False)
            fix_multiindex(mo)
        except Exception as e:
            return None, f"Грешка при теглене: {e}"
        if mo is None or len(mo) < 13:
            return None, "Няма достатъчно месечна история."

        mo = mo[mo['Close'].notna()].copy()
        mo['Ret'] = mo['Close'].pct_change() * 100
        mo = mo.iloc[1:]                       # първият месец няма промяна
        # текущият (незавършен) месец се маха — иначе изглежда като слаб месец
        now = datetime.now()
        mo = mo[~((mo.index.year == now.year) & (mo.index.month == now.month))]

        pivot = mo.pivot_table(index=mo.index.year, columns=mo.index.month,
                               values='Ret', aggfunc='first')
        pivot = pivot.reindex(columns=range(1, 13))
        return pivot, None

    # ==========================================
    # 🎬 ВИДЕО ЧИСЛА — седмичните линии (200W/300W)
    # ==========================================

    def weekly_lines_report(self):
        """Пакетът числа за видео ден: 200W/300W линии, серии, фитили, епизоди.

        Възпроизвежда ръчните скриптове от видеата (weekly_lines.py +
        xrp_witsove.py), с ЧЕСТНАТА математика от 03.08.2026:
        - SMA се смята към СЪОТВЕТНАТА седмица, не към днес (иначе броенето
          на серията излиза грешно);
        - серията брои само ЗАТВОРЕНИ седмици (последният ред е текущата);
        - епизодите с фитил под линията се ДЕ-ДУБЛИРАТ — съседни седмици
          (разстояние ≤2) са ЕДИН епизод, не няколко случая. Урокът от
          видео №9: без това средното излиза +125% вместо честните +6%.

        Returns:
            str: готов текстов доклад за телепромптер/описание.
        """
        sym = self.symbol
        try:
            wk = yf.download(sym, period="max", interval="1wk",
                             auto_adjust=True, progress=False)
            fix_multiindex(wk)
        except Exception as e:
            return f"Грешка при теглене на седмични данни: {e}"
        if wk is None or len(wk) < 60:
            return f"Няма достатъчно седмични данни за {sym}."

        wk = wk[wk['Close'].notna()]              # QA m5: NaN свещ чупи серията
        c = wk['Close'].tolist()
        l = wk['Low'].tolist()
        t = list(wk.index)
        n = len(c)
        last = n - 2                      # последната ЗАТВОРЕНА седмица

        def sma(i, length):
            """SMA към индекс i включително — линията на СЪОТВЕТНАТА седмица."""
            if i + 1 < length:
                return None
            return sum(c[i + 1 - length:i + 1]) / length

        price = c[n - 1]
        out = []
        out.append("=" * 58)
        out.append(f"🎬 ВИДЕО ЧИСЛА · {sym} · {datetime.now():%d.%m.%Y %H:%M}")
        out.append(f"   {n} седмични свещи · цена сега {price:,.4f}")
        out.append("=" * 58)

        for length in (200, 300):
            line_now = sma(n - 1, length)
            if line_now is None:
                out.append(f"\n{length}W: няма достатъчно история "
                           f"(трябват {length}, има {n})")
                continue
            line_prev = sma(n - 2, length)
            dist = (price - line_now) / line_now * 100
            # QA M2: при точно N == length line_prev е None → TypeError
            drift_txt = ("n/a (първа седмица с линия)" if line_prev is None else
                         f"{line_now - line_prev:+,.4f} "
                         f"({'качва се' if line_now > line_prev else 'слиза'})")

            out.append(f"\n──── {length}-СЕДМИЧНАТА ────")
            out.append(f"линия сега  : {line_now:,.4f}")
            out.append(f"цена спрямо : {dist:+.2f}%  ({price - line_now:+,.4f})")
            out.append(f"дрейф/седм. : {drift_txt}")

            # серия от затворени седмици над/под линията
            above = c[last] > sma(last, length)
            streak, i = 0, last
            while i >= 0:
                s = sma(i, length)
                if s is None or (c[i] > s) != above:
                    break
                streak += 1
                i -= 1
            posoka = "НАД" if above else "ПОД"
            out.append(f"серия       : {streak} затваряния {posoka} "
                       f"(от {t[last - streak + 1]:%d.%m.%Y})")

            # фитили под линията по време на серия НАД → епизоди с де-дублиране
            if above and streak >= 2:
                start = last - streak + 1
                cases = [i for i in range(start, last + 1)
                         if l[i] < sma(i, length)]
                if cases:
                    eps, cur = [], [cases[0]]
                    for x in cases[1:]:
                        if x - cur[-1] <= 2:
                            cur.append(x)
                        else:
                            eps.append(cur)
                            cur = [x]
                    eps.append(cur)
                    out.append(f"фитил под   : {len(cases)} седмици "
                               f"= {len(eps)} НЕЗАВИСИМИ епизода "
                               f"(съседни ≤2 седм. = един)")
                    fwd4 = []
                    for g in eps:
                        i0 = g[0]
                        marker = " ← сега" if i0 == last else ""
                        row = f"  · {t[i0]:%d.%m.%Y} ({len(g)} седм.)"
                        if i0 + 4 <= last:
                            r = (c[i0 + 4] - c[i0]) / c[i0] * 100
                            fwd4.append(r)
                            row += f"  +4с: {r:+.2f}%"
                        else:
                            row += "  +4с: —"
                        out.append(row + marker)
                    if len(fwd4) >= 2:
                        srt = sorted(fwd4)
                        m = len(srt)
                        med = (srt[m // 2] if m % 2 else
                               (srt[m // 2 - 1] + srt[m // 2]) / 2)
                        avg = sum(fwd4) / len(fwd4)
                        out.append(f"  → +4с средно {avg:+.2f}% · "
                                   f"МЕДИАНА {med:+.2f}% · "
                                   f"положителни {sum(1 for r in fwd4 if r > 0)}"
                                   f"/{len(fwd4)}")
                        out.append(f"  (само {len(fwd4)} завършени случая — тънка извадка)")
                else:
                    out.append("фитил под   : нито веднъж по време на серията")

        out.append("\n" + "=" * 58)
        out.append("Yahoo Finance данни — числата за ефир се сверяват с Binance.")
        return "\n".join(out)


# ==========================================
# ГЛАВЕН ИНТЕРФЕЙС (customtkinter)
# ==========================================

class SniperGUI:
    def __init__(self, root):
        self.trend_icon = None
        self.txt_log = None
        self.combo_sym = None
        self.lbl_status = None
        self.lbl_details = None
        self.crashes = None
        self.div = None
        self.month_stats = None

        self.root = root
        self.root.title(f"Летописец 📜 V{VERSION} · пазарна статистика")
        self.root.geometry("1500x900")
        # V3.0.1: 15 бутона на един ред ≈ 1600px — под това редът се реже
        self.root.minsize(1720, 700)
        try:
            self.root.state('zoomed')          # Windows: започва максимизиран
        except Exception:
            pass

        # V2.2: икона на прозореца/лентата. При PyInstaller ресурсите живеят
        # в _MEIPASS (вътрешната папка), не до екзето.
        try:
            _res_dir = getattr(sys, '_MEIPASS', _SCRIPT_DIR)
            _ico = os.path.join(_res_dir, 'icon.ico')
            if os.path.exists(_ico):
                self.root.iconbitmap(_ico)
        except Exception as e:
            logger.warning(f"Иконата не се зареди: {e}")

        self.engine = DataEngine()

        # Telegram
        self.TG_BOT_TOKEN = CONFIG.get('telegram_bot_token', '')
        self.TG_CHAT_ID = CONFIG.get('telegram_chat_id', '')
        self.last_sent_day = None
        self._alert_sent_today = False

        # Countdown
        self._countdown = 5

        # UI променливи
        self.var_symbol = ctk.StringVar(value=CONFIG.get('default_symbol', 'XRP-USD'))
        self.var_threshold = ctk.StringVar(value=str(int(CONFIG.get('crash_threshold', 10))))
        # V2.2: размер на текста в таблицата — помни се в config.json, за да
        # пасва на екрана (лаптоп 10-11, външен 4K монитор 13-16)
        # V2.4: тема (тъмна/светла) с памет в config.json
        self.theme_name = CONFIG.get('theme', 'dark')
        if self.theme_name not in THEMES:
            self.theme_name = 'dark'
        self.COL = THEMES[self.theme_name]
        ctk.set_appearance_mode("dark" if self.theme_name == "dark" else "light")

        try:
            _fs = float(CONFIG.get('log_font_size', 11))
        except (ValueError, TypeError):
            _fs = 11.0
        self.var_fontsize = ctk.StringVar(value=f"{_fs:g}")

        self.setup_ui()

        # Първоначално зареждане
        self.start_loading()

        # СТАРТИРАМЕ ЖИВИЯ ЪПДЕЙТ
        self.auto_refresh_price()

        # Стартираме таймера за проверки
        self.check_schedule()

        # Г: F5 = пълно обновяване (Koko държи тула отворен постоянно)
        self.root.bind("<F5>", lambda e: self.start_loading())

        # KOKO 3: пълно автоматично опресняване на всеки N часа (config:
        # full_refresh_hours, по подразбиране 4) — без ежедневен рестарт.
        # Цената живее отделно на 5с; това опреснява ИСТОРИЯТА и таблицата.
        self._schedule_full_refresh()

    def setup_ui(self):
        """V2.3: редизайн — контролен ред, решетка от карти (пасва на всякакъв
        екран, нищо не се реже), бутоните са закотвени ДОЛУ (pack side=bottom
        ПРЕДИ таблицата -> при малък прозорец се свива таблицата, не бутоните)."""
        C_BG = self.COL['bg']; C_CARD = self.COL['card']; C_TITLE = self.COL['title']
        self.root.configure(fg_color=C_BG)
        # V2.4: пазим референции за смяна на темата на живо
        self._themed_frames = []
        self._themed_titles = []

        # ── РЕД 1: КОНТРОЛИ ────────────────────────────────────────────
        ctrl = ctk.CTkFrame(self.root, corner_radius=10, fg_color=C_CARD)
        ctrl.pack(fill="x", padx=10, pady=(8, 4))
        self._themed_frames.append(ctrl)

        ctk.CTkButton(ctrl, text="🔄 ОБНОВИ", command=self.start_loading,
                      width=110, fg_color="#1E5C3A", hover_color="#2E7C4A",
                      font=("Fira Code", 13, "bold")).pack(side="left", padx=(10, 16), pady=8)

        ctk.CTkLabel(ctrl, text="АКТИВ", font=("Fira Code", 12), text_color=C_TITLE).pack(side="left")
        self.combo_sym = ctk.CTkComboBox(ctrl, variable=self.var_symbol,
                                         values=CONFIG.get('symbols', DEFAULT_SYMBOLS),
                                         width=125, command=self.on_symbol_change)
        self.combo_sym.pack(side="left", padx=(4, 16))

        ctk.CTkLabel(ctrl, text="ПРАГ %", font=("Fira Code", 12), text_color=C_TITLE).pack(side="left")
        self.combo_thresh = ctk.CTkComboBox(ctrl, variable=self.var_threshold,
                                            values=[str(i) for i in range(3, 101)],
                                            width=68, command=lambda _: (
                                                self._save_cfg('crash_threshold',
                                                               self.var_threshold.get()),
                                                self.update_crash_stats_live()))
        self.combo_thresh.pack(side="left", padx=(4, 16))

        ctk.CTkLabel(ctrl, text="ТЕКСТ", font=("Fira Code", 12), text_color=C_TITLE).pack(side="left")
        # V2.3: половинки — прилагат се като пиксели, за да пасват точно на екрана
        _sizes = [f"{v / 2:g}" for v in range(16, 41)]           # 8 .. 20 през 0.5
        self.combo_font = ctk.CTkComboBox(ctrl, variable=self.var_fontsize,
                                          values=_sizes, width=78,
                                          command=lambda _: self.apply_font_size())
        self.combo_font.pack(side="left", padx=(4, 16))

        ctk.CTkButton(ctrl, text="🌗 ТЕМА", command=self.toggle_theme,
                      width=90, fg_color="#3A3A55", hover_color="#4A4A66",
                      font=("Fira Code", 12, "bold")).pack(side="left", padx=(0, 8))

        # Г: кога за последно е опреснено всичко (цената е отделно, на живо)
        self.lbl_updated = ctk.CTkLabel(ctrl, text="", font=("Fira Code", 11),
                                        text_color=C_TITLE)
        self.lbl_updated.pack(side="right", padx=(0, 4))

        self.lbl_status = ctk.CTkLabel(ctrl, text="⏳ Зареждане...",
                                       font=("Fira Code", 13, "bold"),
                                       text_color=self.COL['wait'])
        self.lbl_status.pack(side="right", padx=12)

        # V2.9.6 (Koko): макро пулсът вдясно — злато/DXY/S&P, тегли се при
        # пълното опресняване, всяко с цвят по дневната си посока.
        # pack(side='right') нарежда отдясно наляво → визуално: 🥇 DXY SPX
        self._macro_labels = []
        for m_sym, m_name in (("^GSPC", "SPX"), ("DX-Y.NYB", "DXY"),
                              ("GC=F", "🥇")):
            lb = ctk.CTkLabel(ctrl, text="", font=("Fira Code", 12, "bold"))
            lb.pack(side="right", padx=5)
            self._macro_labels.append((lb, m_sym, m_name))

        # ── РЕШЕТКА ОТ КАРТИ (4 колони x 2 реда, разтягат се) ──────────
        grid = ctk.CTkFrame(self.root, fg_color="transparent")
        grid.pack(fill="x", padx=10, pady=2)
        for c in range(4):
            grid.grid_columnconfigure(c, weight=1, uniform="cards")

        def card(row, col, title):
            fr = ctk.CTkFrame(grid, corner_radius=10, fg_color=C_CARD)
            fr.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
            t = ctk.CTkLabel(fr, text=title, font=("Fira Code", 11),
                             text_color=C_TITLE)
            t.pack(anchor="w", padx=10, pady=(6, 0))
            self._themed_frames.append(fr)
            self._themed_titles.append(t)
            return fr

        # ред 0
        c_price = card(0, 0, "ЦЕНА · живо на 5с")
        self.lbl_dash_price = ctk.CTkLabel(c_price, text="--",
                                           font=("Fira Code", 19, "bold"))
        self.lbl_dash_price.pack(anchor="w", padx=10, pady=(0, 8))

        c_trend = card(0, 1, "ТРЕНД И НИВА · 200W/300W · стени")
        # V2.9.6 (Koko): всеки ред със свой цвят — 300W може да е бичи,
        # докато 200W е мечи; стената е винаги червена, подът зелен.
        self.trend_lines_box = ctk.CTkFrame(c_trend, fg_color="transparent")
        self.trend_lines_box.pack(anchor="w", fill="x", padx=10, pady=(0, 8))

        c_day = card(0, 2, "ДНЕШНИЯТ ХОД")
        self.lbl_dash_day_range = ctk.CTkLabel(c_day, text="--", justify="left",
                                               font=("Fira Code", 12), wraplength=330)
        self.lbl_dash_day_range.pack(anchor="w", padx=10, pady=(0, 8))

        c_week = card(0, 3, "СЕДМИЧЕН ДИАПАЗОН")
        self.lbl_dash_range = ctk.CTkLabel(c_week, text="--", justify="left",
                                           font=("Fira Code", 12), wraplength=330)
        self.lbl_dash_range.pack(anchor="w", padx=10, pady=(0, 8))

        # ред 1
        c_dayhist = card(1, 0, "ДНЕС ПРЕЗ ГОДИНИТЕ")
        self.day_stats_frame = ctk.CTkFrame(c_dayhist, fg_color="transparent")
        self.day_stats_frame.pack(anchor="w", padx=10, pady=(0, 8))
        self.lbl_day_base = ctk.CTkLabel(self.day_stats_frame, text="--", font=("Fira Code", 13, "bold"))
        self.lbl_day_base.pack(side="left")
        self.lbl_day_bull = ctk.CTkLabel(self.day_stats_frame, text="", font=("Fira Code", 13, "bold"), text_color=self.COL['up'])
        self.lbl_day_bull.pack(side="left")
        self.lbl_day_sep = ctk.CTkLabel(self.day_stats_frame, text="", font=("Fira Code", 13, "bold"), text_color=self.COL['muted'])
        self.lbl_day_sep.pack(side="left")
        self.lbl_day_bear = ctk.CTkLabel(self.day_stats_frame, text="", font=("Fira Code", 13, "bold"), text_color=self.COL['down'])
        self.lbl_day_bear.pack(side="left")
        self.lbl_day_end = ctk.CTkLabel(self.day_stats_frame, text="", font=("Fira Code", 13, "bold"))
        self.lbl_day_end.pack(side="left")

        c_weekhist = card(1, 1, "СЕДМИЦАТА ПРЕЗ ГОДИНИТЕ")
        self.lbl_dash_hist = ctk.CTkLabel(c_weekhist, text="--", justify="left",
                                          font=("Fira Code", 13, "bold"), wraplength=330)
        self.lbl_dash_hist.pack(anchor="w", padx=10, pady=(0, 8))

        c_mtf = card(1, 2, "ТАЙМФРЕЙМОВЕ")
        # V2.4: 2×2 решетка — един ред се режеше на по-тесни екрани
        mtf_grid = ctk.CTkFrame(c_mtf, fg_color="transparent")
        mtf_grid.pack(fill="x", padx=10, pady=(0, 8))
        mtf_grid.grid_columnconfigure((0, 1), weight=1)
        self.lbl_mtf_1h = ctk.CTkLabel(mtf_grid, text="1h --", font=("Fira Code", 12, "bold"), anchor="w")
        self.lbl_mtf_1h.grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.lbl_mtf_4h = ctk.CTkLabel(mtf_grid, text="4h --", font=("Fira Code", 12, "bold"), anchor="w")
        self.lbl_mtf_4h.grid(row=0, column=1, sticky="w")
        self.lbl_mtf_1d = ctk.CTkLabel(mtf_grid, text="1D --", font=("Fira Code", 12, "bold"), anchor="w")
        self.lbl_mtf_1d.grid(row=1, column=0, sticky="w", padx=(0, 6))
        self.lbl_mtf_1w = ctk.CTkLabel(mtf_grid, text="1W --", font=("Fira Code", 12, "bold"), anchor="w")
        self.lbl_mtf_1w.grid(row=1, column=1, sticky="w")

        c_thisweek = card(1, 3, "ТАЗИ СЕДМИЦА")
        days_line = ctk.CTkFrame(c_thisweek, fg_color="transparent")
        days_line.pack(anchor="w", padx=10, pady=(0, 8))
        self.lbl_wed = ctk.CTkLabel(days_line, text="Сря --", font=("Fira Code", 12, "bold"))
        self.lbl_wed.pack(side="left", padx=(0, 8))
        self.lbl_thu = ctk.CTkLabel(days_line, text="Чет --", font=("Fira Code", 12, "bold"))
        self.lbl_thu.pack(side="left", padx=8)
        self.lbl_sat = ctk.CTkLabel(days_line, text="Съб --", font=("Fira Code", 12, "bold"))
        self.lbl_sat.pack(side="left", padx=8)

        # ── БУТОНИ: ЗАКОТВЕНИ ДОЛУ (преди таблицата!) ──────────────────
        btns = ctk.CTkFrame(self.root, corner_radius=10, fg_color=C_CARD)
        btns.pack(side="bottom", fill="x", padx=10, pady=(4, 8))
        self._themed_frames.append(btns)

        # V3.0.1 (Koko): събират се на един ред за сега — по-добре така.
        # Лилави = В ТАБЛИЦАТА, сини ↗ = ОТДЕЛЕН ПРОЗОРЕЦ, сиви = помощни.
        def bt(text, cmd, color, hover, w=110):
            ctk.CTkButton(btns, text=text, command=cmd, width=w, height=30,
                          fg_color=color, hover_color=hover,
                          font=("Fira Code", 11, "bold")).pack(side="left", padx=2, pady=5)

        bt("🎬 ВИДЕО ЧИСЛА", self.show_video_numbers, "#7A2E8D", "#9A3EAD", 124)
        bt("🌐 ЛИНИИ ×10", self.show_multi_lines, "#7A2E8D", "#9A3EAD", 106)
        bt("🧾 РАЗПИСКА", self.show_month_receipt, "#7A2E8D", "#9A3EAD", 104)
        bt("⏳ ВРЪЩАНЕ", self.show_recovery_ladder, "#7A2E8D", "#9A3EAD", 100)
        bt("🔻 СЕРИИ", self.show_streak_stats, "#7A2E8D", "#9A3EAD", 90)
        bt("🧩 МОДЕЛИ", self.analyze_correlations, "#7A2E8D", "#9A3EAD", 90)
        bt("📰 НОВИНИ", self.show_news, "#7A2E8D", "#9A3EAD", 92)
        bt("📅 МАТРИЦА ↗", self.show_monthly_matrix, "#1F4E5E", "#2F5E6E", 108)
        bt("📈 ГОДИНИТЕ ↗", self.show_yearly_paths, "#1F4E5E", "#2F5E6E", 112)
        bt("🔗 КОРЕЛАЦИИ ↗", self.show_correlation_matrix, "#1F4E5E", "#2F5E6E", 122)
        bt("💧 ДЪНА ↗", self.show_drawdowns, "#1F4E5E", "#2F5E6E", 94)
        bt("📉 ГРАФИК ↗", self.show_line_chart, "#1F4E5E", "#2F5E6E", 102)
        bt("📊 СЕЗОННОСТ ↗", self.show_heatmap, "#1F4E5E", "#2F5E6E", 116)
        bt("⏰ ЧАСОВЕ ↗", self.show_hourly, "#1F4E5E", "#2F5E6E", 98)
        bt("💾 CSV", self.export_csv, "#3A3A3A", "#4A4A4A", 70)
        bt("📖 ПОМОЩ ↗", self.show_help_window, "#3A3A3A", "#4A4A4A", 96)

        # ── ТАБЛИЦАТА (запълва всичко останало) ────────────────────────
        log_frame = ctk.CTkFrame(self.root, corner_radius=10, fg_color=C_CARD)
        log_frame.pack(fill="both", expand=True, padx=10, pady=2)
        self._themed_frames.append(log_frame)

        self.txt_log = scrolledtext.ScrolledText(
            log_frame, height=18, bg=self.COL['log_bg'], fg=self.COL['up'],
            font=("Fira Code", 11), borderwidth=0, highlightthickness=0
        )
        self.txt_log.pack(fill="both", expand=True, padx=6, pady=6)
        self._config_log_tags()

        # прилага запомнения размер на текста при старт (без запис в config)
        self.apply_font_size(save=False)

    # ==========================================
    # ЖИВ ЪПДЕЙТ (5s polling + countdown)
    # ==========================================

    def auto_refresh_price(self):
        """Тегли само цената на всеки 5 секунди без да блокира"""
        self._countdown = 5
        self._tick_countdown()

        def quick_fetch():
            try:
                ticker = yf.Ticker(self.engine.symbol)
                todays_data = ticker.history(period="1d")

                if not todays_data.empty:
                    current_price = todays_data['Close'].iloc[-1]
                    with self.engine._lock:
                        if self.engine.daily_data is not None:
                            self.engine.daily_data.iloc[-1, self.engine.daily_data.columns.get_loc('Close')] = current_price
                            prev_close = self.engine.daily_data.iloc[-2]['Close']
                            new_ret = ((current_price - prev_close) / prev_close) * 100
                            self.engine.daily_data.iloc[-1, self.engine.daily_data.columns.get_loc('Return')] = new_ret

                    self.root.after(0, self.update_dashboard)
                    self.root.after(0, self.analyze_current_week)
                    self.root.after(0, self.update_mtf_dashboard)
                    self.root.after(0, self.check_realtime_alert)
            except Exception as e:
                logger.warning(f"Live update грешка: {e}")

        threading.Thread(target=quick_fetch, daemon=True).start()
        self.root.after(5000, self.auto_refresh_price)

    def _tick_countdown(self):
        if self._countdown > 0:
            self._countdown -= 1
            self.root.after(1000, self._tick_countdown)

    # ==========================================
    # REAL-TIME АЛЕРТИ
    # ==========================================

    def check_realtime_alert(self):
        """Telegram алерт при пробив на праг интрадей."""
        if self._alert_sent_today:
            return
        df = self.engine.daily_data
        if df is None or df.empty:
            return
        try:
            last = df.iloc[-1]
            intraday_move = abs(last['Return'])
            thresh = float(self.var_threshold.get())

            if intraday_move >= thresh * 0.5:
                direction = "🚀 ПОМПА" if last['Return'] > 0 else "📉 СРИВ"
                price = last['Close']
                pfmt = fmt_price(price)
                msg = (
                    f"⚠️ <b>АЛЕРТ: {self.engine.symbol}</b>\n"
                    f"{direction}: {last['Return']:+.2f}%\n"
                    f"💰 Цена: ${price:{pfmt}}\n"
                    f"📏 Рейндж: ${last['Low']:{pfmt}} - ${last['High']:{pfmt}}"
                )
                self.send_telegram_msg(msg)
                self._alert_sent_today = True
                logger.info(f"Real-time алерт изпратен: {direction} {last['Return']:+.2f}%")
        except Exception as e:
            logger.warning(f"Alert check грешка: {e}")

    # ==========================================
    # MTF ПАНЕЛ
    # ==========================================

    def update_mtf_dashboard(self):
        mtf = self.engine.get_mtf_summary()
        for tf, lbl in [('1h', self.lbl_mtf_1h), ('4h', self.lbl_mtf_4h),
                         ('1D', self.lbl_mtf_1d), ('1W', self.lbl_mtf_1w)]:
            if tf in mtf:
                chg = mtf[tf]['change']
                color = self.COL['up'] if chg >= 0 else self.COL['down']
                pfmt = fmt_price(mtf[tf].get('high', 0))
                txt = f"{tf}: {chg:+.2f}%"
                if 'high' in mtf[tf]:
                    txt += f" (${mtf[tf]['low']:{pfmt}}-${mtf[tf]['high']:{pfmt}})"
                lbl.configure(text=txt, text_color=color)

    # ==========================================
    # НАВИГАЦИЯ / СЪБИТИЯ
    # ==========================================

    def _save_cfg(self, key, value):
        """Г: общ безопасен запис на един ключ в config.json (атомарен,
        не пипа останалото, отказва при повредено четене)."""
        cfg_path = os.path.join(_SCRIPT_DIR, 'config.json')
        cfg = {}
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
            except Exception:
                return
        cfg[key] = value
        try:
            tmp = cfg_path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=4)
            os.replace(tmp, cfg_path)
        except Exception as e:
            logger.warning(f"config запис ({key}): {e}")

    def _schedule_full_refresh(self):
        """KOKO 3: пълно опресняване на всеки N часа, после се пренасрочва."""
        try:
            hours = float(CONFIG.get('full_refresh_hours', 4))
        except (ValueError, TypeError):
            hours = 4
        hours = max(1, min(24, hours))

        def tick():
            if not getattr(self, '_loading', False):
                logger.info(f"Автоматично пълно опресняване (на всеки {hours:g} ч).")
                self.start_loading()
            self.root.after(int(hours * 3600 * 1000), tick)

        self.root.after(int(hours * 3600 * 1000), tick)

    def on_symbol_change(self, _=None):
        self._alert_sent_today = False
        # Г: активът се помни — при следващо пускане тръгва от него
        self._save_cfg('default_symbol', self.var_symbol.get())
        self.start_loading()

    def start_loading(self):
        # А3: заключване — двойно натискане пускаше две надбягващи се нишки
        if getattr(self, '_loading', False):
            return
        self._loading = True
        self.lbl_status.configure(text="⏳ ТЕГЛЯ ДАННИ ОТ БОРСАТА...", text_color=self.COL['wait'])
        self.txt_log.delete(1.0, tk.END)
        sym = self.var_symbol.get()
        self.engine.set_symbol(sym)
        threading.Thread(target=self.load_data_thread, daemon=True).start()

    def load_data_thread(self):
        try:
            success = self.engine.fetch_all_data()
        except Exception as e:
            logger.error(f"load_data_thread: {e}")
            success = False
        # А3: отключваме бутона независимо от изхода
        self._loading = False
        if success:
            try:
                self._fetch_macro_strip()
            except Exception as e:
                logger.warning(f"macro strip: {e}")
            self.root.after(0, self.refresh_analysis)
        else:
            # А5: при грешка старите данни и таблицата ОСТАВАТ на екрана
            self.root.after(0, lambda: self.lbl_status.configure(
                text="❌ Грешка при връзката — показвам старите данни",
                text_color=self.COL['down']))

    def _fetch_macro_strip(self):
        """V2.9.6: злато/DXY/S&P за лентата — върви в нишката на пълното
        опресняване (мрежа!), етикетите се пипат само през root.after."""
        for lb, sym, name in self._macro_labels:
            try:
                d = yf.download(sym, period="5d", interval="1d",
                                auto_adjust=True, progress=False)
                fix_multiindex(d)
                d = d[d['Close'].notna()]
                if len(d) < 2:
                    continue
                px = float(d['Close'].iloc[-1])
                prev = float(d['Close'].iloc[-2])
                chg = (px - prev) / prev * 100 if prev else 0.0
                dec = 2 if px < 1000 else 0
                txt = f"{name} {px:,.{dec}f} {chg:+.1f}%"
                col = (self.COL['up'] if chg > 0
                       else self.COL['down'] if chg < 0
                       else self.COL['muted'])
                self.root.after(0, lambda l=lb, t=txt, c=col:
                                l.configure(text=t, text_color=c))
            except Exception as e:
                logger.warning(f"macro {sym}: {e}")

    def refresh_analysis(self):
        self.analyze_current_week()
        self.update_dashboard()
        self.update_mtf_dashboard()
        self.generate_report()
        self.week_report()
        # Г: кога за последно е опреснено всичко (цената живее отделно на 5с)
        self._last_full_refresh = datetime.now()
        self.lbl_updated.configure(
            text=f"обновено {self._last_full_refresh:%H:%M:%S}")

    def update_crash_stats_live(self):
        if self.engine.daily_data is not None:
            self.generate_report()
            self.week_report()

    def _config_log_tags(self):
        """V2.4: цветовете на таблицата идват от палитрата на темата."""
        C = self.COL
        # V2.9.3: „зелено = нагоре" вече е семантика — небоядисаният текст
        # е неутрален, не бичи.
        self.txt_log.configure(bg=C['log_bg'], fg=C['text'])
        self.txt_log.tag_config("NORMAL", foreground=C['text'])
        # Скенерът: денят като цвят на текста, седмицата като фонова лента.
        # Фоновите тагове нямат foreground (и обратно) — никога не се бият.
        self.txt_log.tag_config("DAY_UP", foreground=C['up'])
        self.txt_log.tag_config("DAY_DOWN", foreground=C['down'])
        self.txt_log.tag_config("NEUTRAL", foreground=C['text'])
        self.txt_log.tag_config("MUTED", foreground=C['muted'])
        self.txt_log.tag_config("WARN", foreground=C['warn'])
        # V2.9.4: заглавие = синкава лента (старото синьо оцелява само като
        # подпис на заглавията); INFO = служебни съобщения (зеленото значи
        # „нагоре", не „успех"). Шрифтът на TITLE се слага в apply_font_size.
        self.txt_log.tag_config("INFO", foreground=C['info'])
        self.txt_log.tag_config("TITLE", foreground=C['info'],
                                background=C['title_bg'])
        self.txt_log.tag_config("WK_BG_UP", background=C['wk_bg_up'])
        self.txt_log.tag_config("WK_BG_DOWN", background=C['wk_bg_down'])
        self.txt_log.tag_config("WK_BG_UP_HOT", background=C['wk_bg_up_hot'])
        self.txt_log.tag_config("WK_BG_DOWN_HOT", background=C['wk_bg_down_hot'])
        self.txt_log.tag_config("RECOVERY", foreground=C['recovery'])
        self.txt_log.tag_config("red", foreground=C['down'])
        self.txt_log.tag_config("pink", foreground=C['pink'])
        self.txt_log.tag_config("orange", foreground=C['warn'])
        self.txt_log.tag_config("WHITE_PUMP", foreground=C['pump_fg'], background=C['pump_bg'])
        self.txt_log.tag_config("BLUE_PUMP", foreground=C['blue'])
        self.txt_log.tag_config("GREEN_PUMP", foreground=C['up'])

    def _print_report(self, text):
        """V2.9.4 (спец. ui-ux): оцветен печат на текстов доклад.

        Една граматика за всички бутони: заглавие = TITLE лента, рамки/
        бележки/етикети = сиво, число СЪС знак = зелено/червено по знака,
        НАД/🐂/качва се = зелено, ПОД/🐻/слиза = червено, уговорките
        (тънка извадка, още чакат, ← сега, изкривяване) = оранж.
        Клипбордът получава чистия текст — тук се цветят само пикселите.
        """
        token_re = re.compile(
            r"([+\-]\d[\d.,]*%|[+\-][\d.,]*\d(?=[\s)]|$)"
            r"|НАД|ПОД|🐂|🐻|качва се|слиза)")
        warn_marks = ("още чакат", "тънка извадка", "← сега",
                      "нито един върнат", "изкривяване", "≥20", "≥30")
        muted_starts = ("Yahoo", "Средно >>", "медианата е", "с Binance",
                        "съставена", "връщане =", "ПРЕДИ спада", "Числата",
                        "Данните", "поредни червени", "АКТИВ")
        ins = self.txt_log.insert

        def colorize(chunk, band):
            pos = 0
            for m in token_re.finditer(chunk):
                if m.start() > pos:
                    ins(tk.END, chunk[pos:m.start()], band + ("NEUTRAL",))
                tok = m.group(0)
                neg = tok.startswith("-") or tok in ("ПОД", "🐻", "слиза")
                ins(tk.END, tok, band + ("DAY_DOWN" if neg else "DAY_UP",))
                pos = m.end()
            if pos < len(chunk):
                ins(tk.END, chunk[pos:], band + ("NEUTRAL",))

        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        for ln in lines:
            st = ln.strip()
            if not st:
                ins(tk.END, "\n")
                continue
            if len(st) > 2 and set(st) <= set("=-─·—"):
                ins(tk.END, ln + "\n", "MUTED")
                continue
            if st.startswith(("🎬", "🌐", "🧾", "⏳", "📊", "🔻", "💧", "📰",
                              "────")):
                ins(tk.END, ln + "\n", "TITLE")
                continue
            if st.startswith(muted_starts):
                ins(tk.END, ln + "\n", "MUTED")
                continue
            # разписката: гръбначните редове носят лента по знака си
            band = ()
            if st.startswith(("медиана", "Досега този месец")):
                mm = re.search(r"[+\-]\d", st)
                if mm:
                    band = (("WK_BG_DOWN" if mm.group(0)[0] == "-"
                             else "WK_BG_UP"),)
            wi = min((ln.find(w) for w in warn_marks if w in ln), default=-1)
            if wi >= 0:
                colorize(ln[:wi], band)
                ins(tk.END, ln[wi:], band + ("WARN",))
                ins(tk.END, "\n", band)
                continue
            # „етикет : стойност" — етикетът сив, ако сам не носи знак.
            # Редове, почващи с цифра (напр. „05.08 14:32 · ...") не са
            # етикети — двоеточието им е час, не разделител.
            ci = ln.find(":")
            if (0 < ci < 24 and not re.search(r"[+\-]\d", ln[:ci])
                    and not st[0].isdigit()):
                ins(tk.END, ln[:ci + 1], band + ("MUTED",))
                colorize(ln[ci + 1:], band)
            else:
                colorize(ln, band)
            ins(tk.END, "\n", band)

    def toggle_theme(self):
        """V2.4: 🌗 — превключва тъмна/светла тема на живо и я помни."""
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.COL = THEMES[self.theme_name]
        ctk.set_appearance_mode("dark" if self.theme_name == "dark" else "light")

        self.root.configure(fg_color=self.COL['bg'])
        for fr in self._themed_frames:
            fr.configure(fg_color=self.COL['card'])
        for t in self._themed_titles:
            t.configure(text_color=self.COL['title'])
        self._config_log_tags()
        self.apply_font_size(save=False)
        self.lbl_day_bull.configure(text_color=self.COL['up'])
        self.lbl_day_bear.configure(text_color=self.COL['down'])

        # опресняваме динамичните цветове по лентата (ако има данни)
        if self.engine.daily_data is not None:
            self.update_dashboard()
            self.analyze_current_week()
            self.update_mtf_dashboard()

        # темата се помни (същият безопасен запис като шрифта)
        cfg_path = os.path.join(_SCRIPT_DIR, 'config.json')
        cfg = {}
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
            except Exception:
                return
        cfg['theme'] = self.theme_name
        try:
            tmp = cfg_path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=4)
            os.replace(tmp, cfg_path)
        except Exception as e:
            logger.warning(f"Темата не се записа: {e}")

    def _popup(self, title, w=1380, h=820):
        """V2.3: единен прозорец за графики — до ГЛАВНИЯ прозорец (не на
        произволен монитор), с нормална рамка: влачи се, преоразмерява се,
        затваря се с Escape."""
        win = ctk.CTkToplevel(self.root)
        win.title(title)
        try:
            x = self.root.winfo_x() + 60
            y = self.root.winfo_y() + 60
            win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        except Exception:
            win.geometry(f"{w}x{h}")
        win.minsize(760, 480)
        win.bind("<Escape>", lambda e: win.destroy())
        win.lift()
        win.focus_force()
        return win

    def _style_fig(self, fig, ax):
        """Г: фигурите следват темата — бяла графика в тъмно приложение дразни."""
        C = self.COL
        fig.patch.set_facecolor(C['card'])
        ax.set_facecolor(C['card'])
        ax.title.set_color(C['text'])
        ax.xaxis.label.set_color(C['text'])
        ax.yaxis.label.set_color(C['text'])
        ax.tick_params(colors=C['muted'])

    def _embed_figure(self, win, fig, export_name="izgled"):
        """Вгражда matplotlib фигура в прозорец/рамка + лента за зуум +
        бутон 📷 КАДЪР — брандиран PNG 1920×1080 за видео (партида Б)."""
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        bar = ctk.CTkFrame(win, fg_color="transparent")
        bar.pack(side="bottom", fill="x")
        toolbar = NavigationToolbar2Tk(canvas, bar, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(bar, text="📷 КАДЪР 1920×1080",
                      command=lambda: self._export_fig(fig, export_name),
                      width=170, fg_color="#7A2E8D", hover_color="#9A3EAD",
                      font=("Fira Code", 12, "bold")).pack(side="right", padx=6, pady=3)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        return canvas

    def _export_fig(self, fig, name):
        """📷 Партида Б: брандиран кадър за видео — 1920×1080, тъмен фон,
        долен ред с източника. Пада в exports/ до програмата."""
        try:
            from PIL import Image
            import io
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150,
                        facecolor=fig.get_facecolor(), bbox_inches="tight")
            buf.seek(0)
            chart = Image.open(buf).convert("RGB")

            W, H, BAR = 1920, 1080, 64
            bg = Image.new("RGB", (W, H), "#0E1117")
            # вписваме графиката в полето над долната лента
            avail_w, avail_h = W - 40, H - BAR - 40
            r = min(avail_w / chart.width, avail_h / chart.height)
            chart = chart.resize((int(chart.width * r), int(chart.height * r)),
                                 Image.LANCZOS)
            bg.paste(chart, ((W - chart.width) // 2,
                             (H - BAR - chart.height) // 2 + 12))

            from PIL import ImageDraw, ImageFont
            d = ImageDraw.Draw(bg)
            try:
                f_small = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 26)
            except Exception:
                f_small = ImageFont.load_default()
            years = ""
            if self.engine.daily_data is not None:
                yrs = self.engine.daily_data.index
                years = f"{yrs[0].year}–{yrs[-1].year} · "
            cap = (f"{self.engine.symbol} · {years}Yahoo Finance, сверено с Binance"
                   f" · {datetime.now():%d.%m.%Y}")
            d.text((28, H - BAR + 16), cap, font=f_small, fill="#8A93A2")
            d.text((W - 220, H - BAR + 16), "@TAkripto", font=f_small, fill="#4FC3F7")

            exp_dir = os.path.join(_SCRIPT_DIR, "exports")
            os.makedirs(exp_dir, exist_ok=True)
            fname = os.path.join(
                exp_dir,
                f"{self.engine.symbol}_{name}_{datetime.now():%Y%m%d_%H%M%S}.png")
            bg.save(fname)
            self.txt_log.insert(tk.END, f"📷 Кадърът е записан: {fname}\n", "INFO")
            self.txt_log.see(tk.END)
        except Exception as e:
            logger.warning(f"PNG експорт: {e}")
            self.txt_log.insert(tk.END, f"❌ PNG експорт: {e}\n", "red")

    def show_monthly_matrix(self):
        """📅 Месечна матрица: години × месеци, цялата история + обобщение.

        Три реда отдолу: среден %, медиана и дял зелени години на месец —
        средно И медиана едновременно, за да се вижда кога едно рали изкривява
        средната (урокът от +125% срещу +6%).
        """
        self.txt_log.insert(tk.END, "\n⏳ Тегля месечната история (period=max)...\n", "INFO")
        self.txt_log.see(tk.END)

        def work():
            # QA M3: изключение в нишката не бива да оставя „⏳" завинаги
            try:
                pivot, err = self.engine.monthly_matrix()
            except Exception as e:
                pivot, err = None, f"❌ Грешка при матрицата: {e}"

            def done():
                if err:
                    self.txt_log.insert(tk.END, err + "\n", "red")
                    return
                months_bg = ["Яну", "Фев", "Мар", "Апр", "Май", "Юни",
                             "Юли", "Авг", "Сеп", "Окт", "Ное", "Дек"]

                win = self._popup(f"📅 Месечна доходност по години — {self.engine.symbol}",
                                  1500, 820)

                n_years = len(pivot)
                fig = Figure(figsize=(15, 8), dpi=100)
                ax = fig.add_subplot(111)

                # обобщителните редове се залепят под матрицата
                summary = pd.DataFrame({
                    'СРЕДНО': pivot.mean(),
                    'МЕДИАНА': pivot.median(),
                    'ЗЕЛЕНИ %': (pivot > 0).sum() / pivot.notna().sum() * 100
                }).T
                full = pd.concat([pivot, summary])
                full.columns = months_bg

                # QA m6: скалата се затяга по САМИТЕ месеци — иначе редът
                # „ЗЕЛЕНИ %" (0-100) издува vmax и месеците избледняват
                vlim = max(abs(pivot.min().min()), abs(pivot.max().max()))
                sns.heatmap(full, annot=True, fmt=".1f", cmap="RdYlGn", center=0,
                            vmin=-vlim, vmax=vlim,
                            cbar=False, linewidths=.5, ax=ax,
                            annot_kws={"size": 9})
                # разделителна линия между годините и обобщението
                ax.hlines(n_years, *ax.get_xlim(), colors="white", linewidths=2)
                ax.set_title(
                    f"{self.engine.symbol} · месечна промяна % · {n_years} години",
                    fontsize=12)
                ax.set_ylabel("")
                self._style_fig(fig, ax)
                fig.tight_layout()
                self._embed_figure(win, fig, export_name='mesechna_matrica')

                self.txt_log.insert(tk.END,
                                    f"📅 Матрицата е отворена ({n_years} години).\n",
                                    "GREEN_PUMP")
                self.txt_log.see(tk.END)
            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def show_multi_lines(self):
        """🌐 V2.7: 200W/300W за всичките активи наведнъж — резервен материал
        за Пон/Съб веригата на канала. Тегли седмични данни за всеки символ
        (бавно е — върви в нишка с прогрес)."""
        syms = CONFIG.get('symbols', DEFAULT_SYMBOLS)
        self.txt_log.insert(tk.END,
                            f"\n⏳ Смятам 200W/300W за {len(syms)} актива "
                            f"(по едно теглене на актив)...\n", "INFO")
        self.txt_log.see(tk.END)

        def work():
            # V2.9.5 (Koko): истински колони с хедър — ЦЕНА СЕГА обозначена,
            # без повтарящите се "200W"/"300W" етикети на всеки ред и без
            # емоджи в клетките (цветът на ±% казва посоката, а емоджито
            # разместваше колоните при редове без него).
            rows = []
            for sym in syms:
                try:
                    wk = yf.download(sym, period="max", interval="1wk",
                                     auto_adjust=True, progress=False)
                    fix_multiindex(wk)
                    wk = wk[wk['Close'].notna()]
                    c = wk['Close'].tolist()
                    n = len(c)
                    price = c[-1]
                    cells = [f"{pretty_sym(sym):<8}",
                             f"{price:>12.4f}"]
                    short = False
                    for L in (200, 300):
                        if n - 1 >= L:      # линия към последната ЗАТВОРЕНА
                            sma = sum(c[n - 1 - L:n - 1]) / L
                            d = (price - sma) / sma * 100
                            cells.append(f"{sma:>12.4f}")
                            cells.append(f"{d:>+7.1f}%")
                        else:
                            short = True
                            cells.append(f"{'—':>12}")
                            cells.append(f"{'—':>8}")
                    row = " | ".join(cells)
                    if short:
                        row += f"   ({n} седм. история)"
                    rows.append(row)
                except Exception as e:
                    rows.append(f"{sym:<6} | грешка: {e}")

            hdr = (f"{'АКТИВ':<8} | {'ЦЕНА СЕГА':>12} | {'200W ЛИНИЯ':>12} | "
                   f"{'СПРЯМО':>8} | {'300W ЛИНИЯ':>12} | {'СПРЯМО':>8}")
            report = ("=" * 72 + f"\n🌐 200W / 300W СЕДМИЧНИ ЛИНИИ · "
                      f"{len(syms)} актива · "
                      f"{datetime.now():%d.%m.%Y %H:%M}\n" + "=" * 72 + "\n"
                      + hdr + "\n" + "-" * 72 + "\n"
                      + "\n".join(rows) + "\n"
                      + "Yahoo Finance данни — за ефир се сверяват с Binance.\n")

            def done():
                self._print_report(report)
                self.txt_log.see(tk.END)
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(report)
                    self.txt_log.insert(tk.END, "📋 Копирано в клипборда.\n", "INFO")
                except Exception:
                    pass
            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def show_yearly_paths(self):
        """📈 V2.7 (изглед В1): годишна крива на натрупване — всяка година
        от 1 януари като линия, текущата удебелена с點 „днес"."""
        df = self.engine.daily_data
        if df is None or df.empty:
            return
        win = self._popup(f"📈 Годините една върху друга — {self.engine.symbol}",
                          1400, 820)
        fig = Figure(figsize=(15.5, 8), dpi=100)
        ax = fig.add_subplot(111)

        cur_year = datetime.now().year
        years = sorted(df.index.year.unique())
        paths = {}
        for y in years:
            yd = df[df.index.year == y]
            if len(yd) < 10:
                continue
            base = yd.iloc[0]['Open']
            if base <= 0:
                continue
            paths[y] = ((yd['Close'] / base) - 1) * 100

        # V2.8 (Koko): годините да се ВИЖДАТ — отделен цвят на година +
        # легенда с финалния % на всяка, средна пътека до медианната,
        # и факти (най-добра/най-лоша година, най-голям дневен скок/спад).
        done_years = [y for y in paths if y != cur_year]
        if done_years:
            grid = {}
            for y in done_years:
                for ts, v in paths[y].items():
                    grid.setdefault(ts.dayofyear, []).append(v)
            days = sorted(grid)
            med = [float(np.median(grid[d])) for d in days]
            avg = [float(np.mean(grid[d])) for d in days]
            ax.plot(days, med, color="#FFB74D", linewidth=2.6,
                    label=f"── медиана ({len(done_years)} г.)", zorder=4)
            ax.plot(days, avg, color="#EF9A9A", linewidth=1.6, linestyle="--",
                    label="-- средна (ралитата я дърпат)", zorder=3)

        cmap = plt.get_cmap("tab20")
        for i, y in enumerate(sorted(paths)):
            x = [ts.dayofyear for ts in paths[y].index]
            fin = paths[y].values[-1]
            if y == cur_year:
                ax.plot(x, paths[y].values, color="#4FC3F7", linewidth=3.0,
                        label=f"{y} · {fin:+.0f}% ◄ днес", zorder=5)
                ax.scatter([x[-1]], [paths[y].values[-1]], s=70,
                           color="#4FC3F7", zorder=6)
            else:
                ax.plot(x, paths[y].values, linewidth=1.1, alpha=0.75,
                        color=cmap(i % 20), label=f"{y} · {fin:+.0f}%")

        # фактите: най-добра/най-лоша завършена година + рекордните дни
        facts = []
        if done_years:
            finals = {y: paths[y].values[-1] for y in done_years}
            by, wy = max(finals, key=finals.get), min(finals, key=finals.get)
            facts.append(f"най-добра: {by} {finals[by]:+.0f}% · "
                         f"най-лоша: {wy} {finals[wy]:+.0f}%")
        rets = df['Return'].dropna()
        if not rets.empty:
            bd, wd = rets.idxmax(), rets.idxmin()
            facts.append(f"рекорден ден: +{rets[bd]:.1f}% ({bd:%d.%m.%Y}) · "
                         f"най-лош: {rets[wd]:.1f}% ({wd:%d.%m.%Y})")
        if facts:
            ax.text(0.99, 0.02, "\n".join(facts), transform=ax.transAxes,
                    ha="right", va="bottom", fontsize=10,
                    color=self.COL['text'],
                    bbox=dict(facecolor=self.COL['bg'], alpha=0.85,
                              edgecolor=self.COL['muted']))

        ax.axhline(0, color="#8A93A2", linewidth=0.8)
        ax.set_xlabel("ден от годината")
        ax.set_ylabel("% от 1 януари")
        ax.set_title(f"{self.engine.symbol} · всяка година от 1 януари · "
                     f"{len(paths)} години", fontsize=12)
        # легендата извън платното — годините се четат, нищо не се покрива
        ax.legend(loc="upper left", bbox_to_anchor=(1.005, 1.0), fontsize=9,
                  framealpha=0.9)
        self._style_fig(fig, ax)
        leg = ax.get_legend()
        if leg:
            leg.get_frame().set_facecolor(self.COL['card'])
            for t in leg.get_texts():
                t.set_color(self.COL['text'])
        # НЕ tight_layout — той реже легендата извън платното;
        # даваме ѝ място вдясно ръчно
        fig.subplots_adjust(left=0.055, right=0.845, top=0.94, bottom=0.08)
        self._embed_figure(win, fig, export_name='godishni_krivi')

    def show_month_receipt(self):
        """🧾 Партида Б: Месечната разписка — рубриката-гръбнак на канала.

        Един прозорец, две действия:
        - РАЗПИСКА (началото на месеца): какво казва историята за ТОЗИ месец —
          медиана, средно, зелени/всички години. Записва се в receipts.json
          (доказуемост: числото е обявено ПРЕДИ месеца да мине).
        - ОТЧЕТ (края/средата): какъв е месецът ДОСЕГА и на кое място се
          нарежда сред всички същи месеци в историята.
        """
        self.txt_log.insert(tk.END, "\n⏳ Смятам месечната разписка...\n", "INFO")
        self.txt_log.see(tk.END)

        def work():
            try:
                pivot, err = self.engine.monthly_matrix()
                if err:
                    raise RuntimeError(err)
                now = datetime.now()
                m = now.month
                months_bg = ["януари", "февруари", "март", "април", "май", "юни",
                             "юли", "август", "септември", "октомври",
                             "ноември", "декември"]
                hist = pivot[m].dropna()
                med = hist.median()
                avg = hist.mean()
                pos = int((hist > 0).sum())
                n = len(hist)

                # месецът ДОСЕГА (от първото дневно отваряне на месеца)
                df = self.engine.daily_data
                cur = df[(df.index.year == now.year) & (df.index.month == m)]
                sofar = None
                rank_txt = ""
                if not cur.empty:
                    sofar = (cur.iloc[-1]['Close'] - cur.iloc[0]['Open']) / cur.iloc[0]['Open'] * 100
                    worse = int((hist < sofar).sum())
                    rank_txt = (f"по-добре от {worse} и по-зле от {n - worse} "
                                f"от {n}-те {months_bg[m - 1]}")

                lines = [
                    "=" * 54,
                    f"🧾 МЕСЕЧНА РАЗПИСКА · {months_bg[m - 1].upper()} · {self.engine.symbol}",
                    f"   съставена {now:%d.%m.%Y %H:%M}",
                    "=" * 54,
                    f"История ({n} години):",
                    f"  медиана : {med:+.2f}%",
                    f"  средно  : {avg:+.2f}%   (разлика с медианата = изкривяване)",
                    f"  зелени  : {pos} от {n} години",
                    f"  диапазон: [{hist.min():+.1f}% … {hist.max():+.1f}%]",
                ]
                # V2.7: детектор на изкривяване (leave-one-out по година) —
                # коя ЕДНА година мести средното най-много
                if n >= 4:
                    best_y, best_shift, best_rest = None, 0.0, avg
                    for y in hist.index:
                        rest = hist.drop(y).mean()
                        if abs(avg - rest) > abs(best_shift):
                            best_shift = avg - rest
                            best_y, best_rest = y, rest
                    if best_y is not None and abs(best_shift) >= 1:
                        lines.append(
                            f"  изкривяване: без {best_y} средното е {best_rest:+.2f}% "
                            f"(само тя го мести с {best_shift:+.1f} п.п.)")
                if sofar is not None:
                    lines += [
                        "-" * 54,
                        f"Досега този месец: {sofar:+.2f}%",
                        f"  → {rank_txt}",
                    ]
                # V3.1: новината на деня от архива на News_app (контекст,
                # не тригер) — какво СЕ ГОВОРЕШЕ в деня на разписката
                nod = self._news_of_day()
                if nod:
                    lines += ["-" * 54,
                              f"Новината на деня: „{nod.get('t', '')[:60]}“ "
                              f"({nod.get('s', 'RSS')[:20]})"]
                lines += ["=" * 54,
                          "Yahoo Finance данни — за ефир се сверяват с Binance."]
                report = "\n".join(lines)

                receipt = dict(
                    type="receipt", symbol=self.engine.symbol,
                    month=m, year=now.year,
                    created=now.strftime("%Y-%m-%d %H:%M"),
                    median_pct=round(float(med), 2), mean_pct=round(float(avg), 2),
                    positive=pos, n_years=int(n),
                    sofar_pct=round(float(sofar), 2) if sofar is not None else None,
                )
            except Exception as e:
                report, receipt = f"❌ Разписката се провали: {e}", None

            def done():
                self._print_report(report + "\n")
                self.txt_log.see(tk.END)
                if receipt:
                    # доказуемост: всяка разписка се трупа в receipts.json
                    try:
                        rj = os.path.join(_SCRIPT_DIR, "receipts.json")
                        data = []
                        if os.path.exists(rj):
                            with open(rj, "r", encoding="utf-8") as f:
                                data = json.load(f)
                        data.append(receipt)
                        tmp = rj + ".tmp"
                        with open(tmp, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        os.replace(tmp, rj)
                        self.txt_log.insert(
                            tk.END, f"🧾 Записана в receipts.json (№{len(data)}).\n",
                            "INFO")
                    except Exception as e:
                        self.txt_log.insert(tk.END, f"⚠ receipts.json: {e}\n", "orange")
                    try:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(report)
                        self.txt_log.insert(tk.END, "📋 Копирано в клипборда.\n", "INFO")
                    except Exception:
                        pass
                self.txt_log.see(tk.END)
            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    # ── 📰 НОВИНИТЕ (V3.1): архивът, който News_app пише ────────────────
    # News_app (третият инструмент) трупа XRP заглавията в append-only
    # архив; пултът само ЧЕТЕ. Новината тук е контекст и постфактум
    # проверка — никога тригер (правилото от 03/05.08).

    @staticmethod
    def _news_archive():
        """{norm_link: {t,s,l,d}} от %LOCALAPPDATA%/XRPNews/news_archive.json
        (форматът на news_core.py в News_app). Празен dict при липса."""
        path = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                            "XRPNews", "news_archive.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _news_of_day(self, when=None):
        """Последното заглавие от деня (за разписката); None при нищо.
        Архивът е в UTC — сравняваме ЛОКАЛНА дата с локална, иначе в
        София между 00:00 и 03:00 „днес" излиза празно."""
        arch = self._news_archive()
        target = (when or datetime.now().astimezone()).date()
        best = None
        for v in arch.values():
            try:
                loc = datetime.fromisoformat(v.get("d", "")).astimezone()
            except (ValueError, TypeError):
                continue
            if loc.date() == target and (
                    best is None or v.get("d", "") > best.get("d", "")):
                best = v
        return best

    def show_news(self):
        """📰 Последните заглавия от архива + седмичният брояч (бъдещият
        „шумомер" — медианата се гради с натрупването на седмици)."""
        arch = self._news_archive()
        if not arch:
            self._print_report("📰 НОВИНИ · архивът е празен — пусни "
                               "News_app (v13+) да събира заглавия.\n")
            self.txt_log.see(tk.END)
            return
        rows = sorted(arch.values(), key=lambda v: v.get("d", ""),
                      reverse=True)
        iso = datetime.now().astimezone().isocalendar()
        wk_key = f"{iso.year}-W{iso.week:02d}"
        wk_count = 0
        first_day = None
        for v in arch.values():
            try:
                # UTC запис → локално време (седмицата на Koko, не на Гринуич)
                dtv = datetime.fromisoformat(v.get("d", "")).astimezone()
            except (ValueError, TypeError):
                continue
            if dtv.year < 1971:      # спасена нечетима дата от стар архив
                continue
            if first_day is None or dtv < first_day:
                first_day = dtv
            i = dtv.isocalendar()
            if f"{i.year}-W{i.week:02d}" == wk_key:
                wk_count += 1
        lines = [
            "=" * 54,
            f"📰 НОВИНИ ОТ АРХИВА · XRP · {datetime.now():%d.%m.%Y %H:%M}",
            "=" * 54,
            f"Тази седмица: {wk_count} заглавия · архив общо {len(arch)}",
        ]
        if first_day is not None:
            # first_day е датата на НАЙ-СТАРОТО ЗАГЛАВИЕ (фийдовете връщат
            # и стари статии) — не кога архивът е тръгнал да пише
            lines.append(f"  най-старото заглавие: {first_day:%d.%m.%Y} — "
                         f"тънка извадка, медианата на шума се гради")
        lines.append("-" * 54)
        for v in rows[:12]:
            try:
                loc = datetime.fromisoformat(v.get("d", "")).astimezone()
                stamp = f"{loc:%d.%m %H:%M}"
            except (ValueError, TypeError):
                stamp = "?"
            src = (v.get("s") or "RSS")[:18]
            title = (v.get("t") or "")[:76]
            lines.append(f"{stamp} · {src:18} · {title}")
        lines += ["=" * 54,
                  "Архивът помни какво СЕ ГОВОРЕШЕ; пултът — какво Е "
                  "ПРАВИЛА цената.",
                  "Заглавието лъже, свещта решава — контекст, не сигнал."]
        report = "\n".join(lines)
        self._print_report(report + "\n")
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(report)
            self.txt_log.insert(tk.END, "📋 Копирано в клипборда.\n", "INFO")
        except Exception:
            pass
        self.txt_log.see(tk.END)

    def show_recovery_ladder(self):
        """⏳ V2.9 (идея №5): след ден със спад ≥X% — колко дни чака
        историята за затваряне обратно над нивото отпреди спада.
        Връзва се с разписките: „след −5% ден медианата е N дни"."""
        self.txt_log.insert(tk.END, "\n⏳ Смятам дните до връщане...\n", "INFO")
        self.txt_log.see(tk.END)

        def work():
            try:
                rows = self.engine.recovery_ladder()
                if not rows:
                    raise RuntimeError("няма достатъчно данни")
                n_days = len(self.engine.daily_data)
                yrs = n_days / 365.25
                lines = [
                    "=" * 64,
                    f"⏳ ДНИ ДО ВРЪЩАНЕ · {self.engine.symbol} · "
                    f"{yrs:.1f} год. история ({n_days} дни)",
                    "   връщане = затваряне обратно НАД затварянето от деня",
                    "   ПРЕДИ спада · поредни червени дни = ЕДИН епизод",
                    "=" * 64,
                ]
                for r in rows:
                    if r['median'] is None:
                        lines.append(f"  ден ≤ −{r['thr']:>2}%: {r['episodes']:>3} "
                                     f"епизода — нито един върнат още")
                        continue
                    row_txt = (f"  ден ≤ −{r['thr']:>2}%: {r['episodes']:>3} епизода → "
                               f"медиана {r['median']:g} дни · "
                               f"средно {r['mean']:.1f} · "
                               f"най-дълго {r['worst']} дни "
                               f"({r['worst_date']})")
                    if r['open']:
                        row_txt += f" · {r['open']} още чакат"
                    lines.append(row_txt)
                lines += [
                    "-" * 64,
                    "Средно >> медиана = няколко дълги зими дърпат средното;",
                    "медианата е типичният случай. Числата за ефир се сверяват",
                    "с Binance (тук е Yahoo Finance).",
                    "=" * 64,
                ]
                report = "\n".join(lines)
            except Exception as e:
                report = f"❌ Дните до връщане се провалиха: {e}"

            def done():
                self._print_report(report + "\n")
                self.txt_log.see(tk.END)
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(report)
                    self.txt_log.insert(tk.END, "📋 Копирано в клипборда.\n",
                                        "INFO")
                except Exception:
                    pass
                self.txt_log.see(tk.END)
            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def show_streak_stats(self):
        """🔻 V3.0: сериите — какво прави следващият ден след N поредни."""
        self.txt_log.insert(tk.END, "\n⏳ Смятам сериите...\n", "INFO")
        self.txt_log.see(tk.END)

        def work():
            try:
                st = self.engine.streak_stats()
                if not st:
                    raise RuntimeError("няма достатъчно данни")
                yrs = len(self.engine.daily_data) / 365.25
                lines = [
                    "=" * 64,
                    f"🔻 СЕРИИ ОТ ЕДНОЦВЕТНИ ДНИ · {self.engine.symbol} · "
                    f"{yrs:.1f} год. история",
                    "   случай = денят, в който серията ДОСТИГА N",
                    "=" * 64,
                    "След N поредни ЧЕРВЕНИ дни — следващият ден:",
                ]
                for r in st['red']:
                    lines.append(
                        f"  след {r['n']}: {r['cases']:>3} случая → "
                        f"медиана {r['med']:+.2f}% · "
                        f"зелен в {r['green_share']:.0f}% от случаите")
                lines.append("")
                lines.append("След N поредни ЗЕЛЕНИ дни — следващият ден:")
                for r in st['green']:
                    lines.append(
                        f"  след {r['n']}: {r['cases']:>3} случая → "
                        f"медиана {r['med']:+.2f}% · "
                        f"зелен в {r['green_share']:.0f}% от случаите")
                lines += [
                    "-" * 64,
                    "Средно >> медиана около нулата и дял ~50% = серията НЕ",
                    "предсказва следващия ден — казвай го честно в ефир.",
                    "=" * 64,
                ]
                report = "\n".join(lines)
            except Exception as e:
                report = f"❌ Сериите се провалиха: {e}"

            def done():
                self._print_report(report + "\n")
                self.txt_log.see(tk.END)
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(report)
                    self.txt_log.insert(tk.END, "📋 Копирано в клипборда.\n",
                                        "INFO")
                except Exception:
                    pass
            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def show_drawdowns(self):
        """💧 V3.0: топ-10 просадки (текст в таблицата) + подводна крива
        (прозорец) — колко под върха е била цената през цялата история."""
        self.txt_log.insert(tk.END, "\n⏳ Смятам дъната...\n", "INFO")
        self.txt_log.see(tk.END)

        def work():
            try:
                rows, dd = self.engine.drawdown_table()
                if not rows:
                    raise RuntimeError("няма достатъчно данни")
                lines = [
                    "=" * 70,
                    f"💧 ТОП-{len(rows)} ДЪНА (просадки) · {self.engine.symbol}",
                    "   дълбочина = затваряне на дъното срещу върха преди него",
                    "=" * 70,
                ]
                for k, r in enumerate(rows, 1):
                    tail = (f"върнат след {r['days_total']} дни"
                            if r['days_total'] is not None
                            else "още чакат върха")
                    lines.append(
                        f"  {k:>2}. {r['depth']:+6.1f}%  "
                        f"връх {r['peak_date']:%d.%m.%Y} → "
                        f"дъно {r['trough_date']:%d.%m.%Y} "
                        f"({r['days_down']} дни надолу) · {tail}")
                lines.append("=" * 70)
                report = "\n".join(lines)
            except Exception as e:
                rows, dd, report = None, None, f"❌ Дъната се провалиха: {e}"

            def done():
                self._print_report(report + "\n")
                self.txt_log.see(tk.END)
                if dd is None:
                    return
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(report)
                    self.txt_log.insert(tk.END, "📋 Копирано в клипборда.\n",
                                        "INFO")
                except Exception:
                    pass
                win = self._popup(f"💧 Подводна крива · {self.engine.symbol}")
                fig = Figure(figsize=(14, 7), dpi=100)
                ax = fig.add_subplot(111)
                ax.fill_between(dd.index, dd.values, 0,
                                color="#FF5252", alpha=0.55)
                ax.plot(dd.index, dd.values, color="#FF5252", linewidth=0.8)
                ax.axhline(0, color="#8A93A2", linewidth=0.8)
                ax.set_ylabel("% под върха (затваряния)")
                ax.set_title(f"{self.engine.symbol} · подводна крива — "
                             f"колко под върха е била цената", fontsize=12)
                self._style_fig(fig, ax)
                self._embed_figure(win, fig, "drawdown")
            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def show_correlation_matrix(self):
        """🔗 V3.0 (Koko): крипто ↔ макро — 90 дни срещу 1 година,
        корелация на дневните доходности на всичките активи."""
        syms = CONFIG.get('symbols', DEFAULT_SYMBOLS)
        self.txt_log.insert(tk.END,
                            f"\n⏳ Тегля 1 г. дневни за {len(syms)} актива "
                            f"(по едно теглене на актив)...\n", "INFO")
        self.txt_log.see(tk.END)

        def work():
            rets = {}
            for sym in syms:
                try:
                    d = yf.download(sym, period="1y", interval="1d",
                                    auto_adjust=True, progress=False)
                    fix_multiindex(d)
                    d = d[d['Close'].notna()]
                    if len(d) > 40:
                        rets[pretty_sym(sym)] = d['Close'].pct_change()
                except Exception as e:
                    logger.warning(f"corr {sym}: {e}")

            def done():
                if len(rets) < 3:
                    self.txt_log.insert(tk.END,
                                        "❌ Корелации: няма данни.\n", "WARN")
                    return
                R = pd.DataFrame(rets)
                c_all = R.corr(min_periods=30)
                c_90 = R.tail(90).corr(min_periods=20)
                win = self._popup(f"🔗 Корелации · {len(rets)} актива")
                fig = Figure(figsize=(15.5, 7.2), dpi=100)
                for k, (cm, ttl) in enumerate(
                        ((c_90, "последните 90 дни"),
                         (c_all, "последната 1 година")), 1):
                    ax = fig.add_subplot(1, 2, k)
                    sns.heatmap(cm, ax=ax, annot=True, fmt=".2f",
                                cmap="RdYlGn", vmin=-1, vmax=1, cbar=False,
                                annot_kws={"size": 8}, linewidths=0.5)
                    ax.set_title(f"Дневни доходности · {ttl}", fontsize=11)
                    self._style_fig(fig, ax)
                fig.subplots_adjust(left=0.07, right=0.98, top=0.92,
                                    bottom=0.14, wspace=0.28)
                self._embed_figure(win, fig, "correlations")
                self.txt_log.insert(
                    tk.END,
                    "🔗 Корелациите са в прозореца — сравнявай 90д срещу 1г:"
                    " разминаването Е историята за видео.\n", "INFO")
            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def apply_font_size(self, save=True):
        """V2.2: сменя размера на текста в таблицата и го помни в config.json.

        Таблицата е широка ~172 знака — на лаптоп 10-11pt я събира, на 4K
        монитор 14-16pt я разпъва да запълни полето вместо да виси в ъгъла.

        Args:
            save: False при старт (само прилага, не пише файла).
        """
        try:
            size = max(8.0, min(20.0, float(self.var_fontsize.get())))
        except (ValueError, TypeError):
            size = 11.0
        # V2.3: половинки. Tk приема само ЦЕЛИ точки, но отрицателен размер
        # значи ПИКСЕЛИ — а пикселната стъпка е по-фина (10.5pt = 14px).
        # Така 0.5-те стъпки стават реални и таблицата пасва точно на екрана.
        px = -max(10, round(size * 4 / 3))
        self.txt_log.configure(font=("Fira Code", px))
        # таговете със собствен шрифт трябва да следват същия размер
        self.txt_log.tag_config("WHITE_PUMP", font=("Fira Code", px))
        self.txt_log.tag_config("BLUE_PUMP", font=("Fira Code", px))
        self.txt_log.tag_config("TITLE", font=("Fira Code", px, "bold"))

        if save:
            # QA M1: ако файлът СЪЩЕСТВУВА, но четенето гръмне (повреден/заключен),
            # НЕ записваме — иначе изтриваме Telegram токените и настройките.
            # Записът е атомарен: временен файл + os.replace.
            cfg_path = os.path.join(_SCRIPT_DIR, 'config.json')
            cfg = {}
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                except Exception as e:
                    logger.warning(f"config.json не се чете ({e}) — "
                                   f"размерът НЕ е записан, за да не изтрия настройките.")
                    return
            cfg['log_font_size'] = round(size, 1)
            try:
                tmp_path = cfg_path + '.tmp'
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=4)
                os.replace(tmp_path, cfg_path)
            except Exception as e:
                logger.warning(f"Не мога да запиша размера на текста: {e}")

    def show_video_numbers(self):
        """🎬 Пакетът числа за видео ден — в лога + в клипборда.

        Тежкото теглене върви в нишка, за да не замръзва интерфейсът;
        печатът и клипбордът се връщат в главната нишка през root.after
        (tkinter не е нишково-безопасен).
        """
        self.txt_log.insert(tk.END, "\n⏳ Смятам видео числата (тегля седмични данни)...\n", "INFO")
        self.txt_log.see(tk.END)

        def work():
            # QA M3: без try/except изключение в нишката = вечен „⏳" без обяснение
            try:
                report = self.engine.weekly_lines_report()
            except Exception as e:
                report = f"❌ Грешка при видео числата: {e}"

            def done():
                self._print_report(report + "\n")
                self.txt_log.see(tk.END)
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(report)
                    self.txt_log.insert(tk.END, "📋 Копирано в клипборда.\n", "INFO")
                except Exception:
                    pass
            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def export_csv(self):
        if self.crashes is None or self.crashes.empty:
            messagebox.showwarning("Внимание", "Няма данни за експорт!")
            return
        # QA m3: абсолютен път — при .exe работната папка е произволна
        filename = os.path.join(
            _SCRIPT_DIR,
            f"Analysis_{self.var_symbol.get()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        try:
            self.crashes.to_csv(filename, index=True)
            messagebox.showinfo("Успех", f"Данните са запазени в:\n{filename}")
        except Exception as e:
            messagebox.showerror("Грешка", f"Неуспешен запис: {e}")

    # ==========================================
    # АНАЛИЗ НА ТЕКУЩАТА СЕДМИЦА
    # ==========================================

    def analyze_current_week(self):
        df = self.engine.daily_data
        if df is None:
            return

        # 1. Данни за текущата ситуация (последните дни)
        last_7 = df.tail(7)
        today_name = datetime.now().strftime("%A")
        current_week = datetime.now().isocalendar()[1]

        # Взимаме прага от менюто
        try:
            mag_threshold = float(self.var_threshold.get())
        except (ValueError, TypeError):
            mag_threshold = 5.0

        # Извличаме процентите за ключовите дни
        def get_day_ret(day_name):
            try:
                val = last_7[last_7['Day'] == day_name].iloc[-1]['Return']
                return val, f"{val:+.2f}%"
            except (IndexError, KeyError):
                return 0, "N/A"

        wed_ret, wed_str = get_day_ret('Wednesday')
        thu_ret, thu_str = get_day_ret('Thursday')
        sat_ret, sat_str = get_day_ret('Saturday')

        # РЕДИЗАЙН V2.2 (03.08.2026): статусът е ОПИСАНИЕ, не съвет.
        # Старите лампи („🟢 ВХОД: СЪБОТА СУТРИН", „НЕДЕЛЯ Е КЪРВАВА") бяха
        # календарни сигнали — клас, погребан с 6.5 г. данни (дните от
        # седмицата са бета-артефакти; като сделка EV е отрицателна).
        # Инструментът е статистически пулт: показва какво Е СТАНАЛО.
        activity_threshold = 1.5

        # V2.4: статусът носи контекст — номер на седмицата, най-големият
        # дневен ход досега и седмичният диапазон, не само „спокойна".
        wk_rows = df[(df.index.year == datetime.now().year) &
                     (df['WeekNum'] == current_week)]
        rng_txt = ""
        big_txt = ""
        if not wk_rows.empty:
            w_hi, w_lo = wk_rows['High'].max(), wk_rows['Low'].min()
            if w_lo > 0:
                rng_txt = f" · диапазон {((w_hi - w_lo) / w_lo * 100):.1f}%"
            rets = wk_rows['Return'].dropna()
            if not rets.empty:
                bi = rets.abs().idxmax()
                dni = {"Monday": "Пон", "Tuesday": "Вто", "Wednesday": "Сря",
                       "Thursday": "Чет", "Friday": "Пет", "Saturday": "Съб",
                       "Sunday": "Нед"}
                big_txt = f" · най-голям ход: {dni.get(bi.day_name(), '?')} {rets[bi]:+.1f}%"

        # V2.9.5 (Koko): лентата най-горе не стои полупразна и сива —
        # носи ДНЕС (тялото на деня) + серията и се цвети по посоката.
        last = df.iloc[-1]
        day_pct_now = ((last['Close'] - last['Open']) / last['Open'] * 100
                       if last['Open'] else 0.0)
        sign_now = 1 if day_pct_now > 0 else (-1 if day_pct_now < 0 else 0)
        run = 0
        if sign_now:
            for o_, c_ in zip(df['Open'].iloc[::-1], df['Close'].iloc[::-1]):
                s_ = 1 if c_ > o_ else (-1 if c_ < o_ else 0)
                if s_ == sign_now:
                    run += 1
                else:
                    break
        dnes_txt = f"ДНЕС {day_pct_now:+.2f}%"
        if run >= 2:
            dnes_txt += (f" · {run}-{bg_ord(run)} пореден "
                         f"{'зелен' if sign_now > 0 else 'червен'} ден")

        moved = [d for d, r in (("Сря", wed_ret), ("Чет", thu_ret), ("Съб", sat_ret))
                 if abs(r) >= activity_threshold]
        if moved:
            status_txt = (f"📊 {dnes_txt} · седмица №{current_week} · раздвижена "
                          f"({', '.join(moved)} ≥ {activity_threshold}%){big_txt}{rng_txt}")
        else:
            status_txt = (f"📊 {dnes_txt} · седмица №{current_week} · спокойна"
                          f"{big_txt}{rng_txt}")
        status_col = (self.COL['up'] if sign_now > 0
                      else self.COL['down'] if sign_now < 0
                      else self.COL['muted'])

        # А2: докато тече пълно теглене, статусът показва „⏳ ТЕГЛЯ" — живият
        # 5-сек цикъл не бива да го презаписва
        if not getattr(self, '_loading', False):
            self.lbl_status.configure(text=status_txt, text_color=status_col)

        # А4 (03.08): тук стоеше историята спрямо прага — смятана,
        # но никъде непоказвана от V2.2 насам. Изтрита.

        # --- ЦВЕТНИ ДНИ ГОРЕ ВДЯСНО ---
        wed_col = self.COL['up'] if wed_ret >= 0 else self.COL['down']
        self.lbl_wed.configure(text=f"Сряда: {wed_str}", text_color=wed_col)

        thu_col = self.COL['up'] if thu_ret >= 0 else self.COL['down']
        self.lbl_thu.configure(text=f"Четвъртък: {thu_str}", text_color=thu_col)

        sat_col = self.COL['up'] if sat_ret >= 0 else self.COL['down']
        self.lbl_sat.configure(text=f"Събота: {sat_str}", text_color=sat_col)

    def update_dashboard(self):
        """Попълва информацията в лентата (V7: Рейндж с ЦЕНИ и ТАРГЕТИ)"""
        df = self.engine.daily_data
        if df is None or df.empty:
            return

        now = datetime.now()

        # 1. Текущи данни
        last_row = df.iloc[-1]
        curr_price = last_row['Close']
        curr_ret = last_row['Return']

        fmt = fmt_price(curr_price)

        price_col = self.COL['up'] if curr_ret >= 0 else self.COL['down']
        self.lbl_dash_price.configure(
            text=f"$ЦЕНА: {curr_price:{fmt}} ({curr_ret:+.2f}%)", text_color=price_col)

        # 2. Тренд — V2.6: СЕДМИЧНИТЕ 200W/300W (линиите от канала, съвпадат
        # с TradingView), не дневните. Смятат се от седмичните затваряния
        # (resample, седмица Пон-Нед като Binance). Дневните 1.35/1.63 бяха
        # верни, но никой не гледа тях.
        # V2.9.6 (Koko): всеки ред носи цвета СИ — 300W +12.6% беше
        # червена само защото 200W е мечи. Стена = down, Под = up.
        rows_tr = []
        wk_close = df['Close'].resample('W-SUN').last().dropna()
        for length, name in ((200, '200W'), (300, '300W')):
            if len(wk_close) >= length:
                sma = wk_close.tail(length).mean()
                d_pct = (curr_price - sma) / sma * 100
                d_usd = curr_price - sma
                ico = "🐂" if curr_price > sma else "🐻"
                col = self.COL['up'] if curr_price > sma else self.COL['down']
                rows_tr.append((f"{name} ${sma:{fmt}} {ico} "
                                f"{d_pct:+.1f}% ({d_usd:+{fmt}})", col))
        # V2.5 (Koko): стените — нива с многократни отхвърляния
        walls = self.engine.find_walls()
        if walls.get('wall'):
            w = walls['wall']
            rows_tr.append((f"Стена ${w['price']:{fmt}} · {w['touches']} "
                            f"отхв. · {w['age_days']}д", self.COL['down']))
        if walls.get('floor'):
            w = walls['floor']
            rows_tr.append((f"Под  ${w['price']:{fmt}} · {w['touches']} "
                            f"отскока · {w['age_days']}д", self.COL['up']))
        if rows_tr:
            for wdg in self.trend_lines_box.winfo_children():
                wdg.destroy()
            for txt, col in rows_tr:
                ctk.CTkLabel(self.trend_lines_box, text=txt, justify="left",
                             anchor="w", font=("Fira Code", 12, "bold"),
                             text_color=col).pack(anchor="w")

        # 3. ДНЕВЕН РЕЙНДЖ (С ЦЕНИ И ТАРГЕТ)
        d_high = last_row['High']
        d_low = last_row['Low']

        d_rng_text = f"Дневен Рейндж: ${d_low:{fmt}}-${d_high:{fmt}}"
        # V2.9.5 (Koko): цветът следва движението на деня, не е вечно син
        d_col = (self.COL['up'] if last_row['Close'] > last_row['Open']
                 else self.COL['down'] if last_row['Close'] < last_row['Open']
                 else self.COL['info'])

        # Смятаме ПРОГНОЗАТА
        hist_mask = (df.index.month == now.month) & (df.index.day == now.day) & (df.index.year >= now.year - 5)
        hist_stats = df[hist_mask]

        if not hist_stats.empty:
            # V2.2: без „Цел" — това беше среден исторически диапазон, представен
            # като прогноза. Сега казва каквото Е: типичен ход за тази дата и
            # колко от него е изминат днес.
            ranges_pct = (hist_stats['High'] - hist_stats['Low']) / hist_stats['Open']
            avg_vol_pct = ranges_pct.mean()

            expected_move_val = curr_price * avg_vol_pct
            current_move_val = d_high - d_low
            used = current_move_val / expected_move_val * 100 if expected_move_val else 0

            d_rng_text += (f" · типичен за {now.day:02d}.{now.month:02d}: "
                           f"±{avg_vol_pct * 100:.1f}% ({len(hist_stats)} год. история) · "
                           f"изминат {used:.0f}%")

            if current_move_val > expected_move_val:
                d_col = self.COL['warn']
                d_rng_text += " 🔥 над типичния"

        self.lbl_dash_day_range.configure(text=d_rng_text, text_color=d_col)

        # 4. СЕДМИЧЕН РЕЙНДЖ (SMART ZONES)
        current_week_num = last_row['WeekNum']
        current_year = df.index[-1].year
        mask = (df.index.year == current_year) & (df['WeekNum'] == current_week_num)
        this_week_data = df[mask]

        if not this_week_data.empty:
            w_high = this_week_data['High'].max()
            w_low = this_week_data['Low'].min()

            w_str = "W: N/A"
            w_col = self.COL['muted']

            if w_high != w_low:
                w_pos = ((curr_price - w_low) / (w_high - w_low)) * 100

                if w_pos <= 20:
                    dist_to_break = curr_price - w_low
                    pct = (dist_to_break / curr_price) * 100
                    zone_name = "💎 Дъно"
                    w_col = self.COL['up']
                    w_str = f"Седмичен диапазон: {int(w_pos)}% ({zone_name}) · до дъното: ${dist_to_break:{fmt}} ({pct:.1f}%)"

                elif w_pos >= 80:
                    dist_to_break = w_high - curr_price
                    pct = (dist_to_break / curr_price) * 100
                    zone_name = "🔥 Връх"
                    w_col = self.COL['warn']
                    w_str = f"Седмичен диапазон: {int(w_pos)}% ({zone_name}) · до върха: ${dist_to_break:{fmt}} ({pct:.1f}%)"

                else:
                    zone_name = "⚖️ Среда"
                    w_col = self.COL['info']

                    if w_pos > 50:
                        dist_to_break = w_high - curr_price
                        pct = (dist_to_break / curr_price) * 100
                        w_str = f"Седмичен диапазон: {int(w_pos)}% ({zone_name}) · до върха: ${dist_to_break:{fmt}} ({pct:.1f}%)"
                    else:
                        dist_to_break = curr_price - w_low
                        pct = (dist_to_break / curr_price) * 100
                        w_str = f"Седмичен диапазон: {int(w_pos)}% ({zone_name}) · до дъното: ${dist_to_break:{fmt}} ({pct:.1f}%)"

                # V2.9.5 (Koko): цветът = движението на седмицата (цена
                # срещу отварянето ѝ), не зоната; и самото % се вижда
                w_open = this_week_data.iloc[0]['Open']
                if w_open:
                    w_chg = (curr_price - w_open) / w_open * 100
                    w_str += f" · седмицата: {w_chg:+.1f}%"
                    w_col = (self.COL['up'] if w_chg > 0
                             else self.COL['down'] if w_chg < 0
                             else self.COL['muted'])

            self.lbl_dash_range.configure(text=w_str, text_color=w_col)
        else:
            self.lbl_dash_range.configure(text="W: Нова Седмица", text_color=self.COL['muted'])

        # 5. ИСТОРИЯ ЗА СЕДМИЦАТА
        df_copy = df.copy()
        df_copy['WeekNum'] = df_copy.index.isocalendar().week
        w_hist = df_copy[df_copy['WeekNum'] == current_week_num]

        avg_hist_return = w_hist['Return'].mean() * 7
        bull_years = 0
        bear_years = 0
        for yr, group in w_hist.groupby(w_hist.index.year):
            if group.iloc[-1]['Close'] > group.iloc[0]['Open']:
                bull_years += 1
            else:
                bear_years += 1

        hist_col = self.COL['up'] if avg_hist_return > 0 else self.COL['down']
        hist_text = (f"Седмица №{current_week_num:02d} исторически: "
                     f"{avg_hist_return:+.1f}% ср. · {bull_years}🐂/{bear_years}🐻 "
                     f"· {bull_years + bear_years} години")

        self.lbl_dash_hist.configure(text=hist_text, text_color=hist_col)

        # 6. ИСТОРИЯ ЗА ДЕНЯ
        date_str = now.strftime("%A %d.%b")
        avg_ret, n_bulls, n_bears, last_bull, last_bear = get_day_history(df, now.month, now.day)

        if n_bulls + n_bears > 0:
            base_col = self.COL['up'] if avg_ret > 0 else self.COL['down']
            self.lbl_day_base.configure(text=f"{date_str}: {avg_ret:+.2f}% (", text_color=base_col)
            self.lbl_day_bull.configure(text=f"{n_bulls}🐂'{last_bull}")
            self.lbl_day_sep.configure(text="/")
            self.lbl_day_bear.configure(text=f"{n_bears}🐻'{last_bear}")
            self.lbl_day_end.configure(text=")", text_color=base_col)

    # ==========================================
    # АНАЛИЗ НА КОРЕЛАЦИИ
    # ==========================================

    def analyze_correlations(self):
        """Търси зависимости между W-1 (Сряда, Четвъртък, Събота) и текущата седмица."""
        if self.crashes is None or self.crashes.empty:
            messagebox.showinfo("Инфо", "Първо обновете данните и намерете събития.")
            return

        self.txt_log.delete(1.0, tk.END)
        self.txt_log.insert(tk.END, f"{self.div}\n", "MUTED")
        self.txt_log.insert(tk.END,
                            "🧩 АНАЛИЗ НА КОРЕЛАЦИИ: ПРЕДХОДНА СЕДМИЦА (W-1)"
                            " -> ТЕКУЩ РЕЗУЛТАТ\n", "TITLE")
        self.txt_log.insert(tk.END, f"{self.div}\n", "MUTED")
        self.txt_log.insert(tk.END,
                            "Какви Сря/Чет/Съб модели са предшествали големите седмици "
                            "(по 1-3 случая на модел).\n\n",
                            "MUTED")

        patterns = []
        df = self.engine.daily_data

        for (year, week), group in self.crashes.groupby(['Year', 'WeekNum']):
            event_type = group.iloc[0]['MoveType']
            event_date = group.index[-1]

            prev_date_ref = event_date - timedelta(days=7)
            p_year, p_week, _ = prev_date_ref.isocalendar()
            prev_data = df[(df.index.year == p_year) & (df['WeekNum'] == p_week)]
            if prev_data.empty:
                continue

            def get_sign(day_name):
                d_row = prev_data[prev_data['Day'] == day_name]
                if not d_row.empty:
                    ret = d_row.iloc[0]['Return']
                    return "БИЧИ" if ret > 0 else "МЕЧИ"
                return "----"

            s_wed = get_sign("Wednesday")
            s_thu = get_sign("Thursday")
            s_sat = get_sign("Saturday")

            pattern_sig = f"{s_wed} {s_thu} {s_sat}"
            patterns.append({
                'Pattern': pattern_sig,
                'Result': event_type,
                'Week': f"W{week}-{str(year)[2:]}"
            })

        pat_df = pd.DataFrame(patterns)

        if pat_df.empty:
            self.txt_log.insert(tk.END, "Няма достатъчно данни за анализ.\n")
            return

        summary = pat_df.groupby(['Pattern', 'Result']).size().unstack(fill_value=0)
        if 'CRASH' not in summary.columns:
            summary['CRASH'] = 0
        if 'PUMP' not in summary.columns:
            summary['PUMP'] = 0
        summary['Total'] = summary['CRASH'] + summary['PUMP']
        summary = summary.sort_values('Total', ascending=False)

        header = f"{'МОДЕЛ (СЕДМИЦА: Сря Чет Съб)':<26} | {'ОБЩО':<6} | {'СРИВОВЕ':<9} | {'ПОМПИ':<9} | {'ДЯЛ'}"
        self.txt_log.insert(tk.END, f"{header}\n{'-' * 50}\n", "MUTED")

        for pattern, row in summary.iterrows():
            total = row['Total']
            crashes = row['CRASH']
            pumps = row['PUMP']

            if crashes > pumps:
                prob = (crashes / total) * 100
                direction = "🐻 МЕЧА"
                col = "DAY_DOWN"
            elif pumps > crashes:
                prob = (pumps / total) * 100
                direction = "🐂 БИЧА"
                col = "DAY_UP"
            else:
                prob = 50.0
                direction = "⚖️ МИКС"
                col = "NEUTRAL"

            # --- ПРИНТИРАНЕ НА ЧАСТИ ---
            # A) МОДЕЛА (всяка дума с цвета си)
            parts = pattern.split()
            current_len = 0

            for i, part in enumerate(parts):
                color = "NEUTRAL"
                if "МЕЧИ" in part:
                    color = "DAY_DOWN"
                elif "БИЧИ" in part:
                    color = "DAY_UP"

                self.txt_log.insert(tk.END, part, color)
                current_len += len(part)

                if i < len(parts) - 1:
                    self.txt_log.insert(tk.END, " ", "NORMAL")
                    current_len += 1

            padding = 28 - current_len
            if padding > 0:
                self.txt_log.insert(tk.END, " " * padding, "NORMAL")

            # B) ОБЩО
            self.txt_log.insert(tk.END, f" | {total:<6} | ", "NORMAL")
            # C) СРИВОВЕ (Червено)
            self.txt_log.insert(tk.END, f"{crashes:<9}", "DAY_DOWN")
            self.txt_log.insert(tk.END, " | ", "NORMAL")
            # D) ПОМПИ (Зелено)
            self.txt_log.insert(tk.END, f"{pumps:<9}", "DAY_UP")
            self.txt_log.insert(tk.END, " | ", "NORMAL")
            # E) ВЕРОЯТНОСТ
            self.txt_log.insert(tk.END, f"{prob:.0f}% {direction}\n", col)

        self.txt_log.insert(tk.END, "\n🔍 ЛЕГЕНДА: ", "MUTED")
        self.txt_log.insert(tk.END, "МЕЧИ ", "DAY_DOWN")
        self.txt_log.insert(tk.END, "/ ", "MUTED")
        self.txt_log.insert(tk.END, "БИЧИ ", "DAY_UP")
        self.txt_log.insert(tk.END, "= Посока на деня.\n", "MUTED")

    # ==========================================
    # ГЕНЕРИРАНЕ НА РЕПОРТ
    # ==========================================

    def generate_report(self):
        # Взимаме стойността като абсолютен процент (Магнитуд)
        try:
            mag_threshold = float(self.var_threshold.get())
        except (ValueError, TypeError):
            mag_threshold = 10.0

        df = self.engine.daily_data.copy()
        if df is None:
            return
        df['Year'] = df.index.year

        # V2.9: колонните метрики — веднъж върху целия df, групите ги
        # наследяват при concat. Серията се брои по ТЯЛОТО на деня.
        df['DayPct'] = np.where(df['Open'] > 0,
                                (df['Close'] - df['Open']) / df['Open'] * 100,
                                0.0)
        streak, prev_sign, run = [], 0.0, 0
        for sgn in np.sign(df['DayPct'].round(4).to_numpy()):
            if sgn != 0 and sgn == prev_sign:
                run += 1
            elif sgn != 0:
                run = 1
            else:
                run = 0
            prev_sign = sgn
            streak.append(run)
        df['Streak'] = streak
        vol30 = df['Volume'].rolling(30).mean()
        df['RelVol'] = np.where(vol30 > 0, df['Volume'] / vol30, np.nan)
        ytd_high = df.groupby('Year')['High'].cummax()
        df['OffYTDHigh'] = np.where(ytd_high > 0,
                                    (df['Close'] - ytd_high) / ytd_high * 100,
                                    np.nan)

        # 1. Групираме
        weekly_groups = df.groupby(['Year', 'WeekNum'])
        events_frames = []

        for (year, week), group in weekly_groups:
            if group.empty:
                continue
            group = group.sort_index()

            week_high = group['High'].max()
            week_low = group['Low'].min()
            week_open = group.iloc[0]['Open']
            week_close = group.iloc[-1]['Close']

            if week_high == 0 or week_low == 0:
                continue

            is_crash = week_close < week_open

            if is_crash:
                move_pct = ((week_low - week_high) / week_high) * 100
            else:
                move_pct = ((week_high - week_low) / week_low) * 100

            if abs(move_pct) >= mag_threshold:
                group = group.copy()
                group['MoveType'] = 'CRASH' if is_crash else 'PUMP'
                group['MovePct'] = move_pct
                group['WeekHigh'] = week_high
                group['WeekLow'] = week_low
                events_frames.append(group)

        # 2. Обединяваме
        if events_frames:
            self.crashes = pd.concat(events_frames).sort_index(ascending=False)
        else:
            self.crashes = pd.DataFrame(columns=df.columns)
            if 'MoveType' not in self.crashes.columns:
                self.crashes['MoveType'] = None
                self.crashes['MovePct'] = 0

        self.crashes['Year'] = self.crashes.index.year
        self.crashes['SMA200'] = df.loc[self.crashes.index]['SMA200'].fillna(0)
        # (03.08.2026) MARKET_CAP_APPROX вече не се ползва — обемът е реалният
        # от yfinance, не Δкапитализация по хардкодната таблица.

        # 3. Броячи за корелациите
        unique_events = self.crashes[['Year', 'WeekNum', 'MoveType']].drop_duplicates()
        event_counts = unique_events.groupby(['WeekNum', 'MoveType']).size().to_dict()

        weekly_stats = {}
        for (year, week), group in self.crashes.groupby(['Year', 'WeekNum']):
            m_type = group.iloc[0]['MoveType']
            w_pct = group.iloc[0]['MovePct']
            days_cnt = len(group)
            # V2.9.4 (Koko): полето е високо 7 реда — инфото се реди
            # ВЕРТИКАЛНО под номера, не се разтяга настрани.
            cnt = event_counts.get((week, m_type), 0)
            wk_lines = [f"W{int(week):02d}", f"размах {w_pct:+.1f}%"]
            if cnt >= 2:
                wk_lines.append(f"{cnt}× в историята")
            weekly_stats[(year, week)] = wk_lines

        # Хедър
        header = (
            f"{'ДАТА':<12} | {'±':<4} | {'ДЕН':<9} | "
            f"{'ДВИЖЕНИЕ НА ЦЕНАТА':<24} | "
            f"{'ДЕН %':<7} | "
            f"{'СЕРИЯ':<6} | "
            f"{'ОБЕМ ($)':<10} | "
            f"{'ОТН.ОБЕМ':<8} | "
            f"{'ОТ ВРЪХ':<8} | "
            f"{'СЛЕД 3Д ▼/▲':<15} | "
            f"{'СЕДМИЦАТА'}"
        )

        self.div = "=" * 147
        self.txt_log.delete(1.0, tk.END)

        # V2.8 (Koko я хвана): стълбата мереше РАЗМАХА връх-дъно — а той при
        # крипто е ≥5% почти всяка седмица (444/458 = безсмислица). Истинският
        # „ход на седмицата" е ЗАТВАРЯНЕ спрямо ОТВАРЯНЕ — той казва колко
        # рядко седмицата реално ЗАВЪРШВА с голямо движение.
        ladder = []
        wk_moves = []
        for (yy, ww), gg in weekly_groups:
            if gg.empty:
                continue
            o, c = gg.iloc[0]['Open'], gg.iloc[-1]['Close']
            if o > 0:
                wk_moves.append(abs(c - o) / o * 100)
        n_weeks = len(wk_moves)
        if n_weeks:
            for thr in (5, 10, 15, 20, 30):
                cnt = sum(1 for m in wk_moves if m >= thr)
                if cnt:
                    per = n_weeks / cnt
                    kolko = (f"~{per * 7 / 30.4:.1f} месеца" if per >= 8
                             else f"{per:.1f} седмици")
                    ladder.append(f"  затваря с ≥{thr:>2}%: {cnt:>3} от {n_weeks} "
                                  f"→ средно веднъж на {kolko}")
        self._print_report("📊 КОЛКО ЧЕСТО СЕДМИЦАТА ЗАВЪРШВА С ГОЛЯМ ХОД "
                           "(затваряне спрямо отваряне)\n"
                           + "\n".join(ladder) + "\n\n")

        self.txt_log.insert(tk.END,
                            f"🔎 СКЕНЕР ЗА ВОЛАТИЛНОСТ (> {mag_threshold}%)\n",
                            "NORMAL")
        self.txt_log.insert(tk.END, f"{self.div}\n{header}\n{self.div}\n",
                            "MUTED")

        self.month_stats = {}
        printed_weeks = {}

        for date, row in self.crashes.iterrows():
            pct = row['Return']
            close = row['Close']
            wk = row['WeekNum']
            yr = date.year
            sma = row['SMA200']
            m_type = row['MoveType']

            # V2.9: денят се описва с ТЯЛОТО си (отваряне→затваряне) —
            # точно както го казваме в ефир. Иконата (V2.7, Koko) и „ДЕН %"
            # ползват едно и също число, за да не спорят помежду си.
            day_pct = row.get('DayPct', pct)
            if pd.isna(day_pct):
                day_pct = pct
            trend_icon = "🐂" if day_pct > 0 else ("🐻" if day_pct < 0 else "—")

            d_high = row['High']
            d_low = row['Low']

            # V2.9.1 (Koko го хвана): стрелката следва ДЕНЯ, не типа на
            # седмицата — иначе зелен ден в червена седмица показваше
            # „$високо -> $ниско" до положителен ДЕН %.
            pfmt = fmt_price(d_low)
            if day_pct < 0:
                price_display = f"${d_high:<9{pfmt}} -> ${d_low:<9{pfmt}}"
            else:
                price_display = f"${d_low:<9{pfmt}} -> ${d_high:<9{pfmt}}"

            # V2.9: серия (от 2-рия пореден ден нагоре — 1-ви е шум).
            # V2.9.1: без емоджи — то е по-широко от 1 знак и местеше
            # всички колони след себе си; цветът на реда казва посоката.
            stk = int(row.get('Streak', 0) or 0)
            seriya = f"{stk}-{bg_ord(stk)}" if stk >= 2 and day_pct != 0 else "—"
            rv = row.get('RelVol', np.nan)
            relvol_str = f"{rv:.1f}×" if pd.notna(rv) else "—"
            offh = row.get('OffYTDHigh', np.nan)
            offh_str = f"{offh:+.1f}%" if pd.notna(offh) else "—"

            # ПОПРАВЕНО (03.08.2026): колоната показваше (Δцена × хардкоднат
            # съплай) = промяна на капитализацията, ЕТИКЕТИРАНА като обем —
            # измислено число. yfinance дава РЕАЛЕН обем в същите данни.
            vol = row.get('Volume', 0)
            vol = 0 if pd.isna(vol) else vol          # QA m1: NaN минава през `or 0`
            if vol >= 1_000_000_000:
                mf_str = f"{vol / 1_000_000_000:.1f} B"
            elif vol >= 1_000_000:
                mf_str = f"{vol / 1_000_000:.0f} M"
            else:
                mf_str = f"{vol:,.0f}"

            # V2.9.2 (Koko): само „+отскок от дъното" лъжеше — следващите
            # дни почти винаги имат връх над дъното на червения ден, дори
            # когато пазарът продължава надолу. Честната мярка: от
            # ЗАТВАРЯНЕТО на червения ден — докъде надолу / докъде нагоре
            # в следващите 3 дни. V2.9.3: ▼/▲ — стрелката Е знакът, всяка
            # в своя цвят (▼0.0 = не е падала по-надолу).
            rec_pair = None
            if day_pct < 0 and close > 0:
                try:
                    pos = df.index.get_loc(date)
                    nxt = df.iloc[pos + 1: pos + 4]
                    if not nxt.empty:
                        dn = abs(min((nxt['Low'].min() - close) / close * 100,
                                     0.0))
                        up = max((nxt['High'].max() - close) / close * 100,
                                 0.0)
                        rec_pair = (f"▼{dn:.1f}", f"▲{up:.1f}")
                except KeyError:
                    pass

            # Седмично Инфо
            wk_key = (yr, wk)
            n_seen = printed_weeks.get(wk_key, 0)
            wk_lines = weekly_stats.get(wk_key, [])
            wk_info = wk_lines[n_seen] if n_seen < len(wk_lines) else ''
            printed_weeks[wk_key] = n_seen + 1

            # V2.9.3 (спец. ui-ux-engineer): седмицата = ФОН (лента),
            # денят = ЦВЯТ на текста. 6-те цвята тип×повторения бяха
            # неразчетими без легенда — фонът кодира само посоката
            # (+наситено ниво при ≥3 повторения), броят отива като текст
            # в колоната СЕДМИЦАТА. Нюлайнът също носи фоновия таг —
            # иначе лентата свършва нащърбено там, където свършва текстът.
            count = event_counts.get((wk, m_type), 0)
            hot = "_HOT" if count >= 3 else ""
            bg = ("WK_BG_UP" if m_type == 'PUMP' else "WK_BG_DOWN") + hot
            day_tag = ("DAY_UP" if day_pct > 0
                       else "DAY_DOWN" if day_pct < 0 else "MUTED")
            wk_tag = "DAY_UP" if m_type == 'PUMP' else "DAY_DOWN"
            rv_tag = "WARN" if (pd.notna(rv) and rv >= 2.0) else "NEUTRAL"

            ins = self.txt_log.insert
            ins(tk.END, f"{date.strftime('%Y-%m-%d'):<12} | ", (bg, "MUTED"))
            ins(tk.END, f"{trend_icon:<3} | ", (bg, day_tag))
            ins(tk.END, f"{row['Day']:<9} | ", (bg, "MUTED"))
            ins(tk.END, f"{price_display:<22} | {day_pct:>6.2f}% | "
                        f"{seriya:<6} | ", (bg, day_tag))
            ins(tk.END, f"{mf_str:<10} | ", (bg, "NEUTRAL"))
            ins(tk.END, f"{relvol_str:<8} | ", (bg, rv_tag))
            ins(tk.END, f"{offh_str:<8} | ", (bg, "NEUTRAL"))
            if rec_pair:
                pad = max(15 - len(rec_pair[0]) - 1 - len(rec_pair[1]), 0)
                ins(tk.END, rec_pair[0], (bg, "DAY_DOWN"))
                ins(tk.END, " ", (bg,))
                ins(tk.END, rec_pair[1] + " " * pad, (bg, "DAY_UP"))
                ins(tk.END, "| ", (bg, "MUTED"))
            else:
                ins(tk.END, f"{'—':<15}| ", (bg, "MUTED"))
            ins(tk.END, wk_info, (bg, wk_tag))
            ins(tk.END, "\n", (bg,))

            self.month_stats[row['Month']] = self.month_stats.get(row['Month'], 0) + 1

    def week_report(self):
        """V3.0.2: СЕЗОННОСТ по календарни седмици — редизайн.

        Погребани: ОТСКОК≥3% (отскок ≥3% от седмичното дъно в крипто е
        почти гарантиран → колоната беше вечно 100% — метрика, която не
        може да излезе лоша, не мери) и ТРЕНД (SMA200 „към онзи момент" —
        нечетима семантика). Ново: календарните дати на седмицата,
        „N от X години", ⚖ бележка при движение и в двете посоки, фон
        само за наистина повтарящите се (≥6 наситен, 4-5 лек), шумът
        (1-2 повторения) е само брояч под таблицата.
        """
        self.txt_log.insert(tk.END, f"\n{self.div}\n", "MUTED")
        self.txt_log.insert(
            tk.END, "📊 СЕЗОННОСТ: кои календарни седмици се повтарят\n",
            "TITLE")
        if self.crashes is None or self.crashes.empty:
            return
        n_years = int(self.engine.daily_data.index.year.nunique())
        self.txt_log.insert(
            tk.END,
            f"{'СЕДМИЦА':<20} | {'ПОСОКА':<8} | ГОДИНИ (от {n_years} с данни)\n"
            + "-" * 100 + "\n", "MUTED")

        mn = ["ян", "фев", "мар", "апр", "май", "юни",
              "юли", "авг", "сеп", "окт", "ное", "дек"]
        cur_y = datetime.now().year

        def wk_label(w):
            try:
                d1 = datetime.fromisocalendar(cur_y, int(w), 1).date()
            except ValueError:
                return f"W{int(w):02d}"
            d2 = d1 + timedelta(days=6)
            if d1.month == d2.month:
                return f"W{int(w):02d} · {d1.day:02d}–{d2.day:02d} {mn[d1.month - 1]}"
            return (f"W{int(w):02d} · {d1.day:02d} {mn[d1.month - 1]}"
                    f"–{d2.day:02d} {mn[d2.month - 1]}")

        counts = {}
        for (week_num, m_type), group in self.crashes.groupby(['WeekNum', 'MoveType']):
            counts[(int(week_num), m_type)] = sorted(
                group['Year'].unique(), reverse=True)

        rows = sorted(counts.items(),
                      key=lambda kv: (len(kv[1]), kv[0][0]), reverse=True)
        shum = 0
        ins = self.txt_log.insert
        for (wk, m_type), yrs in rows:
            cnt = len(yrs)
            if cnt < 3:
                shum += 1
                continue
            fg = "DAY_DOWN" if m_type == 'CRASH' else "DAY_UP"
            posoka = "↓ СПАД" if m_type == 'CRASH' else "↑ РАЛИ"
            if cnt >= 6:
                bg = (("WK_BG_DOWN_HOT" if m_type == 'CRASH'
                       else "WK_BG_UP_HOT"),)
            elif cnt >= 4:
                bg = (("WK_BG_DOWN" if m_type == 'CRASH' else "WK_BG_UP"),)
            else:
                bg = ()
            years_str = ", ".join(map(str, yrs))
            opp = len(counts.get(
                (wk, 'PUMP' if m_type == 'CRASH' else 'CRASH'), []))
            ins(tk.END, f"{wk_label(wk):<20} | ", bg + ("NEUTRAL",))
            ins(tk.END, f"{posoka:<8}", bg + (fg,))
            ins(tk.END, " | ", bg + ("MUTED",))
            ins(tk.END, f"{cnt} от {n_years}: {years_str}", bg + (fg,))
            if opp >= 2:
                ins(tk.END, f"   ⚖ и {opp}× обратно", bg + ("WARN",))
            ins(tk.END, "\n", bg)
        if shum:
            ins(tk.END,
                f"… още {shum} комбинации с по 1-2 повторения — шум, "
                f"не сезонност.\n", "MUTED")
        ins(tk.END,
            "Повторението е наблюдение, не прогноза: „6 от 9 години с ход"
            " ≥ прага\u201c значи волатилна зона, не посока.\n", "MUTED")

    # ==========================================
    # TELEGRAM
    # ==========================================

    def send_telegram_msg(self, message):
        """Праща съобщение към Telegram"""
        if not self.TG_BOT_TOKEN or not self.TG_CHAT_ID:
            return
        url = f"https://api.telegram.org/bot{self.TG_BOT_TOKEN}/sendMessage"
        data = {"chat_id": self.TG_CHAT_ID, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, data=data, timeout=10)
        except Exception as e:
            logger.warning(f"Telegram Error: {e}")

    def check_schedule(self):
        """Проверява часа всяка минута и праща репорти"""
        now = datetime.now()

        if now.hour == 8 and now.minute == 0:
            today_str = now.strftime("%Y-%m-%d")
            if self.last_sent_day != today_str:
                self.send_daily_report()
                if now.weekday() == 0:
                    self.send_weekly_report()
                self.last_sent_day = today_str

        # Нулираме алерта в полунощ
        if now.hour == 0 and now.minute == 0:
            self._alert_sent_today = False

        self.root.after(60000, self.check_schedule)

    def send_daily_report(self):
        """Праща репорт в Telegram с Цена, Тренд, ИСТОРИЯ и РЕЙНДЖОВЕ"""
        df = self.engine.daily_data
        if df is None or df.empty:
            return

        last_row = df.iloc[-1]
        price = last_row['Close']
        ret = last_row['Return']
        fmt = fmt_price(price)
        trend = "🐂 БИЧИ" if price > last_row['SMA200'] else "🐻 МЕЧИ"

        now = datetime.now()
        avg_h, bulls, bears, last_bull, last_bear = get_day_history(df, now.month, now.day)

        hist_txt = "N/A"
        if bulls + bears > 0:
            hist_txt = f"{avg_h:+.2f}% ({bulls}🐂'{last_bull} / {bears}🐻'{last_bear})"

        # ДНЕВЕН РЕЙНДЖ И ТАРГЕТ
        d_high = last_row['High']
        d_low = last_row['Low']
        d_rng_str = f"${d_low:{fmt}}-${d_high:{fmt}}"

        hist_mask = (df.index.month == now.month) & (df.index.day == now.day) & (df.index.year >= now.year - 5)
        hist_5y = df[hist_mask]

        if not hist_5y.empty:
            # V2.2: без „ЦЕЛ" — показва типичния ход за датата, не прогноза
            avg_vol = ((hist_5y['High'] - hist_5y['Low']) / hist_5y['Open']).mean()
            d_rng_str += (f"\n📐 Типичен ход за датата: "
                          f"±{avg_vol * 100:.1f}% ({len(hist_5y)} год.)")

        # СЕДМИЧЕН РЕЙНДЖ
        curr_week = last_row['WeekNum']
        curr_year = df.index[-1].year
        mask = (df.index.year == curr_year) & (df['WeekNum'] == curr_week)
        w_data = df[mask]

        w_pos_str = "N/A"
        if not w_data.empty:
            w_high = w_data['High'].max()
            w_low = w_data['Low'].min()

            if w_high != w_low:
                pos = ((price - w_low) / (w_high - w_low)) * 100

                if pos <= 20:
                    zone = "💎 Близко до Дъно"
                    dist = price - w_low
                    pct = (dist / price) * 100
                    detail = f"Над Дъното: +${dist:{fmt}}({pct:.1f}%)"
                elif pos >= 80:
                    zone = "🔥 Висок Връх"
                    dist = w_high - price
                    pct = (dist / price) * 100
                    detail = f"До върха: ${dist:{fmt}} ({pct:.1f}%)"
                else:
                    zone = "⚖️ Средно Ниво"
                    if pos > 50:
                        dist = price - w_low
                        pct = (dist / price) * 100
                        detail = f"Към Върха: ${w_high - price:{fmt}}({pct:.1f}%)"
                    else:
                        dist = w_high - price
                        pct = (dist / price) * 100
                        detail = f"Към Дъното: ${price - w_low:{fmt}}({pct:.1f}%)"

                w_pos_str = f"{int(pos)}% ({zone})\n   👉 {detail}"
            else:
                w_pos_str = "50% (Нова Седмица)"

        msg = (
            f"🌞 <b>Дневна статистика: {self.engine.symbol}</b>\n"
            f"📅 {now.strftime('%d.%b.%Y')}\n\n"
            f"💰 Цена: <b>${price:{fmt}}</b> ({ret:+.2f}%)\n"
            f"📊 Тренд: {trend}\n\n"
            f"📏 Рейндж: {d_rng_str}\n"
            f"🌊 Позиция в седмицата: {w_pos_str}\n\n"
            f"📜 История: {hist_txt}"
        )
        self.send_telegram_msg(msg)

    def send_weekly_report(self):
        """Събира инфото за седмицата и го праща"""
        df = self.engine.daily_data
        if df is None:
            return

        curr_week = datetime.now().isocalendar()[1]

        df_copy = df.copy()
        df_copy['WeekNum'] = df_copy.index.isocalendar().week
        w_group = df_copy[df_copy['WeekNum'] == curr_week]

        bull_years = 0
        bear_years = 0

        for yr, group in w_group.groupby(w_group.index.year):
            w_open = group.iloc[0]['Open']
            w_close = group.iloc[-1]['Close']

            if w_close > w_open:
                bull_years += 1
            else:
                bear_years += 1

        total = bull_years + bear_years

        # V2.2: без „Sentiment/Outlook" — само историческото броене
        msg = (
            f"📅 <b>Седмица №{curr_week} — исторически</b>\n\n"
            f"🐂 Зелени години: {bull_years}\n"
            f"🐻 Червени години: {bear_years}\n"
            f"📜 {total} години история"
        )
        self.send_telegram_msg(msg)

    # ==========================================
    # ГРАФИКИ (Popup)
    # ==========================================

    def show_line_chart(self):
        """Линеен график с избор на период: 1Д / 7Д / 30Д"""
        hdf = self.engine.hourly_data
        if hdf is None or hdf.empty:
            messagebox.showwarning("Внимание", "Няма часови данни за графика!")
            return

        # V2.3: НЕ fullscreen — той кацаше на произволен монитор и не се
        # местеше. Нормален прозорец до главния, влачи се и се преоразмерява.
        self._chart_win = self._popup(f"📈 {self.engine.symbol} — Линеен график")

        # Бутони за период
        btn_frame = ctk.CTkFrame(self._chart_win, corner_radius=6)
        btn_frame.pack(fill="x", padx=10, pady=5)

        self._chart_btn_1d = ctk.CTkButton(
            btn_frame, text="1 ДЕН", width=120, font=("Fira Code", 13, "bold"),
            command=lambda: self._draw_line_chart(24, "1 Ден"),
            fg_color="#333333", hover_color="#555555")
        self._chart_btn_1d.pack(side="left", padx=5)

        self._chart_btn_7d = ctk.CTkButton(
            btn_frame, text="7 ДНИ", width=120, font=("Fira Code", 13, "bold"),
            command=lambda: self._draw_line_chart(168, "7 Дни"),
            fg_color="#333333", hover_color="#555555")
        self._chart_btn_7d.pack(side="left", padx=5)

        self._chart_btn_30d = ctk.CTkButton(
            btn_frame, text="30 ДНИ", width=120, font=("Fira Code", 13, "bold"),
            command=lambda: self._draw_line_chart(720, "30 Дни"),
            fg_color="#333333", hover_color="#555555")
        self._chart_btn_30d.pack(side="left", padx=5)

        # Бутон за затваряне (Escape или бутон)
        ctk.CTkButton(btn_frame, text="✕ ЗАТВОРИ", width=120, font=("Fira Code", 13, "bold"),
                       command=self._chart_win.destroy,
                       fg_color="#8B0000", hover_color="#AA0000").pack(side="right", padx=5)

        self._chart_win.bind("<Escape>", lambda e: self._chart_win.destroy())

        # Контейнер за графика
        self._chart_container = ctk.CTkFrame(self._chart_win, fg_color="#1a1a2e")
        self._chart_container.pack(fill="both", expand=True, padx=10, pady=5)

        # Показваме 7Д по подразбиране
        self._draw_line_chart(168, "7 Дни")

    def _draw_line_chart(self, bars, label):
        """Рисува линеен график с дадения брой часови барове."""
        hdf = self.engine.hourly_data
        if hdf is None or hdf.empty:
            return

        # Обновяваме цвета на бутоните — активният е зелен, останалите сиви
        btn_map = {24: self._chart_btn_1d, 168: self._chart_btn_7d, 720: self._chart_btn_30d}
        for b, btn in btn_map.items():
            if b == bars:
                btn.configure(fg_color="#006400")
            else:
                btn.configure(fg_color="#333333")

        # Изчистваме стария график
        for w in self._chart_container.winfo_children():
            w.destroy()

        plot_data = hdf.tail(bars).copy()
        if plot_data.empty:
            return

        fig = Figure(figsize=(14, 7), dpi=110, facecolor='#1a1a2e')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#1a1a2e')

        closes = plot_data['Close'].values
        x = range(len(closes))
        color = '#00FF00' if closes[-1] >= closes[0] else '#FF3333'
        ax.plot(x, closes, color=color, linewidth=2)
        ax.fill_between(x, closes, closes.min(), alpha=0.1, color=color)

        # X-axis: показваме дати на равни интервали
        n = len(plot_data)
        step = max(1, n // 10)
        tick_positions = list(range(0, n, step))
        tick_labels = [plot_data.index[i].strftime('%d.%m %H:%M') for i in tick_positions]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=30, ha='right',
                           fontfamily='monospace', fontsize=11)

        ax.tick_params(colors='#888888', labelsize=12)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#333')
        ax.spines['left'].set_color('#333')

        # Y-axis с по-голям шрифт
        pfmt = fmt_price(closes[-1])
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda val, pos: f"${val:{pfmt}}"))
        for lbl in ax.yaxis.get_ticklabels():
            lbl.set_fontfamily('monospace')
            lbl.set_fontsize(12)

        pct_change = (closes[-1] - closes[0]) / closes[0] * 100
        title_color = '#00FF00' if pct_change >= 0 else '#FF3333'
        ax.set_title(f"{self.engine.symbol}  —  {label}  ({pct_change:+.2f}%)",
                     color=title_color, fontsize=18, fontfamily='monospace', fontweight='bold')

        fig.tight_layout(pad=2)

        # Г: през _embed_figure — toolbar за зуум/местене/запис като PNG
        for w in self._chart_container.winfo_children():
            w.destroy()
        self._embed_figure(self._chart_container, fig, export_name='grafik')

    def show_heatmap(self):
        # V2.3: вграден прозорец до главния — не plt.show() на случаен монитор
        if self.engine.daily_data is None:
            return
        data = self.engine.daily_data.copy()
        data['Year'] = data.index.year
        pivot = data.pivot_table(index='Day', columns='Year', values='Return', aggfunc='mean')
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        days_bg = ['Понеделник', 'Вторник', 'Сряда', 'Четвъртък', 'Петък', 'Събота', 'Неделя']
        pivot = pivot.reindex(days_order)
        pivot.index = days_bg

        win = self._popup(f"📊 Сезонност по дни — {self.engine.symbol}", 1100, 700)
        fig = Figure(figsize=(11, 6.5), dpi=100)
        ax = fig.add_subplot(111)
        sns.heatmap(pivot, annot=True, fmt=".2f", cmap="RdYlGn", center=0,
                    cbar=False, linewidths=.5, ax=ax)
        ax.set_title(f"{self.engine.symbol} · среден дневен % по ден от седмицата и година",
                     fontsize=12)
        self._style_fig(fig, ax)
        ax.set_ylabel("")
        fig.tight_layout()
        self._embed_figure(win, fig, export_name='sezonnost_dni')

    def show_hourly(self):
        # V2.3: вграден прозорец до главния
        if self.engine.hourly_data is None:
            return
        saturdays = self.engine.hourly_data[self.engine.hourly_data['Day'] == 'Saturday']
        bottom_hours = []
        grouped = saturdays.groupby(saturdays.index.date)
        for date, group in grouped:
            bottom_hours.append(group['Low'].idxmin().hour)

        win = self._popup(f"⏰ Час на дъното в събота — {self.engine.symbol}", 1050, 640)
        fig = Figure(figsize=(10.5, 6), dpi=100)
        ax = fig.add_subplot(111)
        sns.histplot(bottom_hours, bins=24, kde=True, color="cyan", ax=ax)
        ax.set_title(f"{self.engine.symbol} · в колко часа е дъното в събота "
                     f"({len(bottom_hours)} съботи)", fontsize=12)
        ax.set_xticks(range(0, 24))
        ax.set_xlabel("час (БГ време)")
        self._style_fig(fig, ax)
        fig.tight_layout()
        self._embed_figure(win, fig, export_name='chas_na_danoto')

    def show_help_window(self):
        """Показва прозорец с легенда и инструкции"""
        help_win = ctk.CTkToplevel(self.root)
        help_win.title("📖 Ръководство")
        help_win.geometry("900x700")

        txt = scrolledtext.ScrolledText(help_win, font=("Consolas", 11), bg="#1e1e1e", fg="#dddddd")
        txt.pack(fill="both", expand=True, padx=10, pady=10)

        guide_text = """
============================================================
📊 PRICE_DATA_TOOL — РЪКОВОДСТВО
============================================================

Показва как се е движела цената през годините, месеците и
седмиците — с колко години данни стои зад всяко число.

1. ГОРЕН ПАНЕЛ
------------------------------------------------------------
💰 ЦЕНА — текуща, обновява се на 5 секунди.
📈 ТРЕНД (SMA200) — над/под 200-дневната средна (описателно).
📏 ДНЕВЕН РЕЙНДЖ — днешният ход + „типичен за датата" =
   средният диапазон на СЪЩАТА дата в предишните години (n
   показва колко години). 🔥 = днешният ход вече надви типичния.
🌊 СЕДМИЧЕН ДИАПАЗОН — къде е цената между върха и дъното
   на текущата седмица (0% = на дъното, 100% = на върха).
📊 СТАТУС — раздвижена/спокойна седмица (праг |ход| ≥ 1.5%).
СЕДМИЦАТА ПРЕЗ ГОДИНИТЕ — как е затваряла същата календарна
   седмица в миналите години (🐂 зелени / 🐻 червени).

2. ТАБЛИЦАТА (СКЕНЕР ЗА ВОЛАТИЛНОСТ)
------------------------------------------------------------
Показва всички седмици с ход ≥ прага (меню „ПРАГ ЗА СРИВ").
- ДЕН % — тялото на деня (отваряне→затваряне), както го
  казваме в ефир. Стрелката в ДВИЖЕНИЕ следва същия знак.
- СЕРИЯ — кой пореден едноцветен ден е това; цветът на
  реда казва зелен или червен. Показва се от 2-рия.
- ОБЕМ — реалният обем от Yahoo за деня.
- ОТН.ОБЕМ — днешният обем спрямо 30-дневната средна
  (2.3× = движението има истинско гориво зад себе си).
- ОТ ВРЪХ — колко под най-високата цена за ГОДИНАТА
  (към тази дата) е затворил денят.
- СЛЕД 3Д — след червен ден, спрямо ЗАТВАРЯНЕТО му:
  ▼ докъде надолу и ▲ докъде нагоре е стигала цената
  в следващите 3 дни (▼0.0 = не е падала по-надолу).
- СЕДМИЦАТА — на първия ред от всяка седмица: номер,
  размах връх-дъно (по него работи прагът) и колко
  пъти същата календарна седмица се повтаря в
  историята (изписва се при 2 и повече).
- ЦВЕТОВЕТЕ: фоновата лента = посоката на СЕДМИЦАТА
  (наситена = повтаряща се ≥3 пъти); цветът на числата
  = самият ДЕН. Оранжев ОТН.ОБЕМ = ≥2× над нормалния.
- ТЕКСТ (меню) — размер на шрифта 8-20, помни се. Нагласи
  го така, че таблицата да запълва екрана ти.

3. БУТОНИ
------------------------------------------------------------
ЛИЛАВИТЕ пишат резултата В ТАБЛИЦАТА (и в клипборда).
СИНИТЕ със ↗ отварят ОТДЕЛЕН ПРОЗОРЕЦ с графика.

🧩 МОДЕЛИ — какви Сря/Чет/Съб комбинации са предшествали
   големите седмици (по 1-3 случая на комбинация).
📈 ЛИНЕЕН ГРАФИК / 📊 ТОПЛИННА КАРТА / ⏰ ЧАСОВИ АНАЛИЗ —
   визуализации на сезонността (ден×час, месец).
💾 ЗАПАЗИ CSV — таблицата като файл (до програмата).
🎬 ВИДЕО ЧИСЛА — 200W/300W седмични линии: серия от
   затваряния над/под, фитилни слизания групирани в
   НЕЗАВИСИМИ епизоди (съседни седмици = един епизод),
   изходи след 4 седмици със СРЕДНО и МЕДИАНА. Копира се
   в клипборда. Числата за ефир се сверяват с Binance.
📅 МЕСЕЧНА МАТРИЦА — всяка година × всеки месец, цялата
   налична история. Отдолу: СРЕДНО, МЕДИАНА и ДЯЛ ЗЕЛЕНИ.
   Гледай средно срещу медиана: разминават ли се силно,
   едно рали изкривява средната.
⏳ ВРЪЩАНЕ — след ден със спад ≥3/5/7/10/15%: медиана и
   средно дни до затваряне обратно над нивото отпреди
   спада. Поредните червени дни са ЕДИН епизод. Копира
   се в клипборда — готово за разписка/видео.
🔻 СЕРИИ — след N поредни червени/зелени дни: какво прави
   СЛЕДВАЩИЯТ ден (медиана + дял зелени). Медиана около
   нулата и дял ~50% = серията не предсказва нищо.
🔗 КОРЕЛАЦИИ — дневните доходности на всичките активи
   (вкл. ЗЛАТО/DXY/SP500/RUSSELL): 90 дни срещу 1 година.
   Разминаването между двете карти е видео материалът.
💧 ДЪНА — топ-10 просадки (връх→дъно→връщане) в таблицата
   + подводна крива (% под върха) в прозорец.

4. TELEGRAM (ако е настроен в config.json)
------------------------------------------------------------
- Дневна статистика в 8:00 + седмично историческо броене
  в понеделник. Алерт при дневен ход ≥ прага.

5. КАК СЕ ЧЕТАТ ЧИСЛАТА
------------------------------------------------------------
- СРЕДНО и МЕДИАНА вървят заедно: разминават ли се силно,
  едно голямо рали изкривява средната.
- Съседни седмици се броят като ЕДИН случай — иначе едно
  рали влиза в сметката три пъти.
- Данните са от Yahoo Finance; за публикация се сверяват
  с Binance.
"""

        txt.insert(tk.END, guide_text)
        txt.configure(state="disabled")


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = SniperGUI(root)
    root.mainloop()
