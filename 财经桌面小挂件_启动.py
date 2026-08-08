#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全球金融市场实时数据桌面小挂件 — 桌面宠物版
无边框 / 置顶 / 可拖拽 / 可收起 / 右键菜单 / K线图
数据来源：新浪财经（实时）+ 东方财富/腾讯/新浪（K线多源fallback）
"""

# ── DPI Awareness：必须在 tkinter import 之前声明 ──
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import tkinter as tk
import urllib.request
import urllib.error
import re
import time
import threading
import os
import sys
 
import traceback
import json as json_module
from PIL import Image, ImageTk, ImageDraw

# ═══════════════════════════════════════════════════════════
#  日志
# ═══════════════════════════════════════════════════════════

try:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _BASE_DIR = os.getcwd()

_LOG_DIR = os.path.join(_BASE_DIR, '.temp')
if not os.path.exists(_LOG_DIR):
    try:
        os.makedirs(_LOG_DIR)
    except Exception:
        _LOG_DIR = _BASE_DIR
_LOG_FILE = os.path.join(_LOG_DIR, 'widget_error.log')


def _log(msg):
    try:
        with open(_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {msg}\n')
    except Exception:
        pass


def _install_excepthook():
    def handler(etype, value, tb):
        _log('CRASH:\n' + ''.join(traceback.format_exception(etype, value, tb)))
    sys.excepthook = handler


# ═══════════════════════════════════════════════════════════
#  品种配置
# ═══════════════════════════════════════════════════════════

INSTRUMENTS = [
    ('hf_GC',       '黄金',       'hf'),
    ('hf_SI',       '白银',       'hf'),
    ('hf_CL',       '原油',       'hf'),
    ('s_sh000001',  '上证指数',   's'),
    ('s_sz399001',  '深证成指',   's'),
    ('rt_hkHSI',    '恒生指数',   'hk'),
    ('gb_dji',      '道琼斯',     'gb'),
    ('gb_ixic',     '纳斯达克',   'gb'),
    ('gb_inx',      '标普',       'gb'),
    ('gb_n225',     '日经',       'b'),   # 用 b_NKY 格式获取真正指数（非期货）
    ('b_KOSPI',     '韩国',       'b'),
    ('b_DAX',       '德国',       'b'),
]

# K线东方财富 secid
KLINE_SECIDS = {
    'hf_GC':       '101.GC00Y',
    'hf_SI':       '101.SI00Y',
    'hf_CL':       '101.CL00Y',
    's_sh000001':  '1.000001',
    's_sz399001':  '0.399001',
    'rt_hkHSI':    '100.HSI',
    'gb_dji':      '100.DJIA',
    'gb_ixic':     '100.NDX',
    'gb_inx':      '100.SPX',
    'gb_n225':      '100.N225',
    'b_KOSPI':     '100.KS11',
    'b_DAX':       '100.GDAXI',
}

# 日经实时数据用 b_NKY（真正指数）代替 gb_n225（返回空）
# 新浪 gb_n225 返回空字符串，b_NKY 返回日经225指数实时行情

SINA_FUTURES_KL = {
    'hf_GC': 'GC', 'hf_SI': 'SI', 'hf_CL': 'CL',
    'rt_hkHSI': 'HSI',
    'gb_dji': 'YM', 'gb_ixic': 'NQ', 'gb_inx': 'ES',
    'gb_n225': 'NK',
}
SINA_A_KL = {'s_sh000001': 'sh000001', 's_sz399001': 'sz399001'}
TENCENT_KL = {
    's_sh000001': 'sh000001',
    's_sz399001': 'sz399001',
    'rt_hkHSI': 'hkHSI',
}
# 新浪全球指数日K线（gi.finance.sina.com.cn/hq/daily）
# 用于韩国/德国/日经等全球指数日K线
SINA_GI_KL = {
    'b_KOSPI': 'KOSPI',
    'b_DAX':   'DAX',
    'gb_n225': 'NKY',
}

# 腾讯实时行情映射（第二数据源，用于交叉验证）
# 格式: 品种code -> 腾讯代码
TENCENT_QUOTE = {
    's_sh000001':  'sh000001',
    's_sz399001':  'sz399001',
    'rt_hkHSI':    'hkHSI',
    'gb_dji':      'usDJI',
    'gb_ixic':     'usIXIC',
    'gb_inx':      'usINX',
}

# 新浪实时行情代码映射（品种code -> 新浪请求代码）
# 日经 gb_n225 在新浪返回空，用 b_NKY 代替
SINA_REALTIME_ALIAS = {
    'gb_n225': 'b_NKY',
}

# FX678汇通财经实时行情映射（品种code -> (exchName, symbol)）
# API: https://api-q.fx678img.com/exchangeSymbol.php?exchName=<exch>
# 返回JSON数组: [{"i":symbol, "c":current, "p":prev_close, "name":name, ...}]
FX678_QUOTE = {
    # 商品期货: COMEX=纽约连续(与新浪hf_GC一致), WGJS=现货(备用)
    'hf_GC':   [('COMEX', 'GLNC'), ('WGJS', 'XAU')],   # 纽约黄金连续 + 现货黄金
    'hf_SI':   [('COMEX', 'SLNC'), ('WGJS', 'XAG')],   # 纽约白银连续 + 现货白银
    'hf_CL':   [('NYMEX', 'CONC')],                      # WTI原油连续
    # 全球指数: GJZS=全球指数
    'rt_hkHSI': [('GJZS', 'HSI')],     # 恒生指数
    'gb_dji':   [('GJZS', 'DJIA')],    # 道琼工业指数
    'gb_inx':   [('GJZS', 'SP500')],   # 标普500
    'gb_n225':  [('GJZS', 'NIKKI')],   # 日经225
    'b_KOSPI':  [('GJZS', 'KSE')],     # 南韩综合
    'b_DAX':    [('GJZS', 'DAX')],      # 德国DAX30
}

# 新浪全球指数分时（品种code -> symbol）
# API: https://gi.finance.sina.com.cn/hq/min?symbol=<SYM>&num=1
# 返回JSON: {"result":{"data":[[time, price, chg, vol, date, prev_close], ...]}}
SINA_GI_REALTIME = {
    'gb_n225':  'NKY',     # 日经225
    'b_KOSPI':  'KOSPI',   # 韩国KOSPI
    'b_DAX':    'DAX',     # 德国DAX
}

# 百度财经全球指数映射（品种code -> 百度code）
# API: https://finance.pae.baidu.com/vapi/v1/globalindexrank?area=all&pn=0&rn=50
# 返回JSON: Result.body[] 每项含 name, code, market, last_px, px_change, px_change_rate
# 百度不覆盖商品期货（黄金/白银/原油）
BAIDU_QUOTE = {
    's_sh000001':  '000001',   # 上证指数
    's_sz399001':  '399001',   # 深证成指
    'rt_hkHSI':    'HSI',       # 恒生指数
    'gb_n225':     'NK225',     # 日经225
    'b_KOSPI':     'KOSPI',     # 韩国综指
    'gb_dji':      'DJI',       # 道琼斯
    'gb_ixic':     'IXIC',      # 纳斯达克
    'gb_inx':      'SPX',       # 标普500
    'b_DAX':       'DAX',       # 德国DAX
}

# 东方财富实时行情 secid 映射
EM_QUOTE_SECIDS = {
    'hf_GC':       '101.GC00Y',
    'hf_SI':       '101.SI00Y',
    'hf_CL':       '101.CL00Y',
    's_sh000001':  '1.000001',
    's_sz399001':  '0.399001',
    'rt_hkHSI':    '100.HSI',
    'gb_dji':      '100.DJIA',
    'gb_ixic':     '100.NDX',
    'gb_inx':      '100.SPX',
    'gb_n225':     '100.N225',
    'b_KOSPI':     '100.KS11',
    'b_DAX':       '100.GDAXI',
}

REFRESH_MS = 30000  # 默认 30 秒


# ═══════════════════════════════════════════════════════════
#  HTTP 公共方法（带重试）
# ═══════════════════════════════════════════════════════════

def _http_get(url, decode='utf-8', timeout=10, retries=2):
    """新浪系 HTTP GET，带重试"""
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                'Referer': 'https://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            })
            resp = urllib.request.urlopen(req, timeout=timeout)
            return resp.read().decode(decode, errors='replace')
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
    _log(f'HTTP GET failed ({retries+1} tries): {url[:80]} — {last_err}')
    return None


# ═══════════════════════════════════════════════════════════
#  东方财富熔断器（连续失败触发冷却，避免无效重试）
# ═══════════════════════════════════════════════════════════

_EM_CIRCUIT = {
    'fail_count': 0,       # 连续失败次数
    'tripped': False,      # 是否熔断
    'trip_time': 0,        # 熔断时间戳
}
_EM_FAIL_THRESHOLD = 3    # 连续失败3次触发熔断
_EM_COOLDOWN_SEC = 60     # 冷却60秒后自动半开重试
_EM_CIRCUIT_LOCK = threading.Lock()


def _em_circuit_is_open():
    """检查东方财富熔断器是否打开（冷却期内跳过请求）"""
    with _EM_CIRCUIT_LOCK:
        if not _EM_CIRCUIT['tripped']:
            return False
        # 冷却期已过，半开
        if time.time() - _EM_CIRCUIT['trip_time'] >= _EM_COOLDOWN_SEC:
            _EM_CIRCUIT['tripped'] = False
            _EM_CIRCUIT['fail_count'] = 0
            _log('EM circuit breaker: cooldown elapsed, entering half-open state')
            return False
        return True


def _em_circuit_record_success():
    """记录东方财富请求成功"""
    with _EM_CIRCUIT_LOCK:
        _EM_CIRCUIT['fail_count'] = 0
        _EM_CIRCUIT['tripped'] = False


def _em_circuit_record_failure():
    """记录东方财富请求失败，达到阈值则触发熔断"""
    with _EM_CIRCUIT_LOCK:
        _EM_CIRCUIT['fail_count'] += 1
        if _EM_CIRCUIT['fail_count'] >= _EM_FAIL_THRESHOLD and not _EM_CIRCUIT['tripped']:
            _EM_CIRCUIT['tripped'] = True
            _EM_CIRCUIT['trip_time'] = time.time()
            _log(f'EM circuit breaker: TRIPPED after {_EM_CIRCUIT["fail_count"]} consecutive failures, '
                 f'cooldown {_EM_COOLDOWN_SEC}s')


def _http_get_em(url, timeout=10, retries=2):
    """东方财富 HTTP GET，带重试 + 熔断器"""
    # 熔断检查
    if _em_circuit_is_open():
        return None

    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                'Referer': 'https://quote.eastmoney.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            })
            resp = urllib.request.urlopen(req, timeout=timeout)
            body = resp.read().decode('utf-8', errors='replace')
            _em_circuit_record_success()
            return body
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
    _em_circuit_record_failure()
    _log(f'EM GET failed ({retries+1} tries): {url[:80]} — {last_err}')
    return None


# ═══════════════════════════════════════════════════════════
#  腾讯实时行情
# ═══════════════════════════════════════════════════════════

def _fetch_tencent_quote(codes):
    """从腾讯获取实时行情（批量），返回 {品种code: {price, pct, chg}} 映射。
    codes: dict {品种code: 腾讯代码}"""
    if not codes:
        return {}
    tc_codes = ','.join(codes.values())
    url = f'http://qt.gtimg.cn/q={tc_codes}'
    body = _http_get(url, decode='gbk', timeout=8, retries=1)
    if not body:
        return {}
    result = {}
    # 构建反向映射：腾讯代码 -> 品种code
    tc_to_inst = {v: k for k, v in codes.items()}
    for line in body.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'v_(\w+)="([^"]*)"', line)
        if not m:
            continue
        tc_code, data_str = m.group(1), m.group(2)
        if tc_code not in tc_to_inst:
            continue
        p = data_str.split('~')
        if len(p) < 33:
            continue
        try:
            price = float(p[3]) if p[3] else 0
            pct = float(p[32]) if p[32] else 0
            if price <= 0:
                continue
            chg = price * pct / 100 if pct else 0
            result[tc_to_inst[tc_code]] = {
                'price': round(price, 2),
                'change': round(chg, 2),
                'changePct': round(pct, 2),
            }
        except (ValueError, IndexError):
            continue
    return result


# ═══════════════════════════════════════════════════════════
#  FX678汇通财经实时行情
# ═══════════════════════════════════════════════════════════

def _fetch_fx678_quote():
    """从FX678汇通财经获取实时行情，返回 {inst_code: {price, change, changePct}}
    批量请求各交易所API，对每品种取第一个有效数据源"""
    if not FX678_QUOTE:
        return {}
    # 收集需要请求的交易所
    exch_set = set()
    for sources in FX678_QUOTE.values():
        for exch, _ in sources:
            exch_set.add(exch)

    exch_data = {}  # exch -> {symbol: {price, prev, name}}
    for exch in exch_set:
        url = f'https://api-q.fx678img.com/exchangeSymbol.php?exchName={exch}'
        try:
            req = urllib.request.Request(url, headers={
                'Referer': 'https://quote.fx678.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            })
            resp = urllib.request.urlopen(req, timeout=8)
            raw = resp.read().decode('utf-8', errors='replace')
            if not raw or raw == 'false':
                continue
            items = json_module.loads(raw)
            exch_data[exch] = {}
            for item in items:
                sym = item.get('i', '')
                price_str = str(item.get('c', '0'))
                prev_str = str(item.get('p', '0'))
                name = item.get('name', '')
                if sym and price_str and float(price_str) > 0:
                    exch_data[exch][sym] = {
                        'price': float(price_str),
                        'prev': float(prev_str) if prev_str else 0,
                        'name': name,
                    }
        except Exception:
            continue

    # 为每个品种匹配数据
    result = {}
    for inst, sources in FX678_QUOTE.items():
        for exch, sym in sources:
            data = exch_data.get(exch, {}).get(sym)
            if data and data['price'] > 0:
                price = data['price']
                prev = data['prev']
                chg = price - prev if prev > 0 else 0
                pct = (chg / prev * 100) if prev > 0 else 0
                result[inst] = {
                    'price': round(price, 2),
                    'change': round(chg, 2),
                    'changePct': round(pct, 2),
                }
                break  # 取第一个有效源
    return result


# ═══════════════════════════════════════════════════════════
#  新浪全球指数分时（实时行情补充源）
# ═══════════════════════════════════════════════════════════

def _fetch_sina_gi_realtime():
    """从新浪全球指数分时接口获取实时行情，返回 {inst_code: {price, change, changePct}}
    API: https://gi.finance.sina.com.cn/hq/min?symbol=<SYM>&num=1
    返回JSON: {"result":{"data":[[time, price, chg, vol, date, prev_close], ...]}}
    最后一条数据的price=当前价格，首条数据的prev_close=昨收价"""
    if not SINA_GI_REALTIME:
        return {}
    result = {}
    for inst, symbol in SINA_GI_REALTIME.items():
        url = f'https://gi.finance.sina.com.cn/hq/min?symbol={symbol}&num=1'
        body = _http_get(url, timeout=8, retries=1)
        if not body:
            continue
        try:
            j = json_module.loads(body)
            data_list = j.get('result', {}).get('data', [])
            if not data_list:
                continue
            last = data_list[-1]
            # [time, price, chg, vol, (date, prev_close) — 仅首条有6个字段]
            price = float(last[1]) if len(last) > 1 and last[1] else 0
            if price <= 0:
                continue
            # 找昨收价：首条数据有6个字段，last[5]=prev_close
            prev_close = 0
            if len(data_list[0]) >= 6:
                prev_close = float(data_list[0][5]) if data_list[0][5] else 0
            if prev_close > 0:
                chg = price - prev_close
                pct = chg / prev_close * 100
            else:
                chg = 0
                pct = 0
            result[inst] = {
                'price': round(price, 2),
                'change': round(chg, 2),
                'changePct': round(pct, 2),
            }
        except Exception:
            continue
    return result


# ═══════════════════════════════════════════════════════════
#  百度财经全球指数实时行情
# ═══════════════════════════════════════════════════════════

def _fetch_baidu_quote():
    """从百度财经全球指数排行接口获取实时行情（单次请求获取全部指数）。
    返回 {inst_code: {price, change, changePct}}
    API: https://finance.pae.baidu.com/vapi/v1/globalindexrank?area=all&pn=0&rn=50
    百度code映射见 BAIDU_QUOTE"""
    if not BAIDU_QUOTE:
        return {}
    url = ('https://finance.pae.baidu.com/vapi/v1/globalindexrank'
           '?area=all&pn=0&rn=50&finClientType=pc')
    try:
        req = urllib.request.Request(url, headers={
            'Accept': 'application/vnd.finance-web.v1+json',
            'Referer': 'https://finance.baidu.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        })
        resp = urllib.request.urlopen(req, timeout=8)
        raw = resp.read().decode('utf-8', errors='replace')
    except Exception:
        return {}
    if not raw:
        return {}
    try:
        j = json_module.loads(raw)
        body = j.get('Result', {}).get('body', [])
    except Exception:
        return {}
    if not body:
        return {}
    # 百度code -> 品种code 反向映射
    bd_to_inst = {v: k for k, v in BAIDU_QUOTE.items()}
    result = {}
    for item in body:
        bd_code = item.get('code', '')
        inst_code = bd_to_inst.get(bd_code)
        if not inst_code:
            continue
        price_str = str(item.get('last_px', '0'))
        if not price_str or price_str == '0':
            continue
        price = float(price_str)
        if price <= 0:
            continue
        # 涨跌额
        chg_str = str(item.get('px_change', '0'))
        chg = float(chg_str) if chg_str else 0
        # 涨跌幅，如 "+1.02%"
        pct_str = str(item.get('px_change_rate', ''))
        pct_str = pct_str.replace('%', '').replace('+', '')
        pct = float(pct_str) if pct_str else 0
        result[inst_code] = {
            'price': round(price, 2),
            'change': round(chg, 2),
            'changePct': round(pct, 2),
        }
    return result


# ═══════════════════════════════════════════════════════════
#  实时行情
# ═══════════════════════════════════════════════════════════

def _fetch_sina_realtime():
    """从新浪获取全部12品种实时行情，返回 {inst_code: {price,change,changePct,name}}"""
    parse_map = {item[0]: (item[1], item[2]) for item in INSTRUMENTS}
    # 构建请求代码列表，日经用 b_NKY 代替 gb_n225
    sina_codes = []
    code_map = {}  # sina_code -> inst_code
    for item in INSTRUMENTS:
        inst = item[0]
        sina_code = SINA_REALTIME_ALIAS.get(inst, inst)
        sina_codes.append(sina_code)
        code_map[sina_code] = inst

    url = 'http://hq.sinajs.cn/list=' + ','.join(sina_codes)
    content = _http_get(url, decode='gbk', timeout=8, retries=2)
    if not content:
        return {}

    result = {}
    for line in content.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'var\s+(?:hq_str_)?(\w+)="([^"]*)"', line)
        if not m:
            continue
        sina_code, data_str = m.group(1), m.group(2)
        inst_code = code_map.get(sina_code)
        if not inst_code or not data_str:
            continue
        name, fmt = parse_map[inst_code]
        parsed = _parse(name, fmt, data_str)
        if parsed and parsed.get('price', 0) > 0:
            parsed['code'] = inst_code
            result[inst_code] = parsed
    return result


def _fetch_em_realtime(codes):
    """从东方财富获取实时行情（urllib带熔断器）
    codes: [inst_code,...]
    返回 {inst_code: {price,change,changePct}}"""
    if not codes:
        return {}
    if _em_circuit_is_open():
        return {}
    secids = []
    inst_to_emcode = {}
    for inst in codes:
        secid = EM_QUOTE_SECIDS.get(inst)
        if secid:
            secids.append(secid)
            inst_to_emcode[inst] = secid.split('.')[1]
    if not secids:
        return {}

    path = (f'/api/qt/ulist.np/get?'
            f'fields=f2,f3,f12,f14&secids={",".join(secids)}')

    em_url = f'http://push2.eastmoney.com{path}'
    body = _http_get_em(em_url, timeout=8, retries=1)
    if not body:
        return {}
    try:
        j = json_module.loads(body)
        diff = j.get('data', {}).get('diff', [])
    except Exception:
        return {}
    if not diff:
        return {}

    em_map = {str(d['f12']): d for d in diff}
    result = {}
    for inst, em_code in inst_to_emcode.items():
        d = em_map.get(em_code)
        if d and d.get('f2') and d['f2'] > 0:
            price = d['f2'] / 100
            raw_f3 = d.get('f3', 0) or 0
            if raw_f3 != 0:
                pct = raw_f3 / 100 if abs(raw_f3) > 1 else raw_f3
            else:
                pct = 0
            chg = price * pct / 100 if pct else 0
            result[inst] = {'price': round(price, 2),
                            'change': round(chg, 2),
                            'changePct': round(pct, 2)}
    return result


def _cross_validate(sina_data, em_data, tencent_data, fx678_data,
                    gi_data, baidu_data):
    """六源交叉验证：对每个品种取多数一致的价格，或中位数。
    返回最终 results 列表
    sina_data: 新浪实时, em_data: 东方财富, tencent_data: 腾讯
    fx678_data: FX678汇通, gi_data: 新浪全球指数分时
    baidu_data: 百度财经全球指数"""
    parse_map = {item[0]: (item[1], item[2]) for item in INSTRUMENTS}
    results = []

    for inst, (name, fmt) in parse_map.items():
        candidates = []
        # 收集各源数据
        if inst in sina_data:
            d = sina_data[inst]
            candidates.append(('sina', d['price'], d['change'], d['changePct']))
        if inst in em_data:
            d = em_data[inst]
            candidates.append(('em', d['price'], d['change'], d['changePct']))
        if inst in tencent_data:
            d = tencent_data[inst]
            candidates.append(('tencent', d['price'], d['change'], d['changePct']))
        if inst in fx678_data:
            d = fx678_data[inst]
            candidates.append(('fx678', d['price'], d['change'], d['changePct']))
        if inst in gi_data:
            d = gi_data[inst]
            candidates.append(('gi', d['price'], d['change'], d['changePct']))
        if inst in baidu_data:
            d = baidu_data[inst]
            candidates.append(('baidu', d['price'], d['change'], d['changePct']))

        if not candidates:
            continue

        if len(candidates) == 1:
            src, price, chg, pct = candidates[0]
        else:
            # 交叉验证：检查价格差异
            prices = [c[1] for c in candidates]
            max_p = max(prices)
            min_p = min(prices)
            # 若差异小于1%，取中位数；否则取多数一致
            if max_p > 0 and (max_p - min_p) / max_p < 0.01:
                # 差异小，取中位数
                sorted_c = sorted(candidates, key=lambda x: x[1])
                src, price, chg, pct = sorted_c[len(sorted_c) // 2]
            else:
                # 差异大，检查是否有2个源一致
                price_groups = {}
                for c in candidates:
                    key = round(c[1] / max(prices) * 100) if max(prices) > 0 else 0
                    price_groups.setdefault(key, []).append(c)
                # 取最多票数的组
                best_group = max(price_groups.values(), key=len)
                if len(best_group) >= 2:
                    src, price, chg, pct = best_group[0]
                else:
                    # 无多数一致，取中位数
                    sorted_c = sorted(candidates, key=lambda x: x[1])
                    src, price, chg, pct = sorted_c[len(sorted_c) // 2]

        r = _b(name, price, chg, pct)
        r['code'] = inst
        r['_src'] = src
        r['_sources'] = len(candidates)
        results.append(r)
    return results


def fetch_all_data():
    """六源交叉验证实时行情：新浪 + 东方财富(带熔断) + 腾讯 + FX678
    + 新浪gi分时 + 百度财经
    所有品种尽量从多家获取后交叉验证，少数服从多数"""

    # ── 1. 新浪（全量12品种）──
    sina_data = _fetch_sina_realtime()

    # ── 2. 东方财富（全量12品种，带熔断器）──
    em_data = _fetch_em_realtime([item[0] for item in INSTRUMENTS])

    # ── 3. 腾讯（支持的6品种）──
    tencent_data = _fetch_tencent_quote(TENCENT_QUOTE)

    # ── 4. FX678汇通财经（商品期货+全球指数，9品种）──
    fx678_data = _fetch_fx678_quote()

    # ── 5. 新浪全球指数分时（日经/韩国/德国，3品种）──
    gi_data = _fetch_sina_gi_realtime()

    # ── 6. 百度财经全球指数（9品种，单次请求）──
    baidu_data = _fetch_baidu_quote()

    # ── 7. 六源交叉验证 ──
    results = _cross_validate(sina_data, em_data, tencent_data,
                              fx678_data, gi_data, baidu_data)

    return results if results else None


def _parse(name, fmt, s):
    if not s:
        return None
    p = s.split(',')
    try:
        if fmt == 's':
            return _b(name, float(p[1]), float(p[2]), float(p[3]))
        elif fmt == 'hk':
            return _b(name, float(p[6]), float(p[7]), float(p[8]))
        elif fmt == 'gb':
            price = float(p[1]) if len(p) > 1 and p[1] else 0
            pct = float(p[2]) if len(p) > 2 and p[2] else 0
            chg = float(p[4]) if len(p) > 4 and p[4] else (price * pct / 100 if price and pct else 0)
            return _b(name, price, chg, pct)
        # 日经/韩国/DAX: 新浪int_/b_格式，增加容错
        elif fmt == 'int':
            # 新浪int_格式: 名称,现价,涨跌,涨跌幅(%),...
            price = float(p[1]) if len(p) > 1 and p[1] else 0
            chg = float(p[2]) if len(p) > 2 and p[2] else 0
            pct = float(p[3]) if len(p) > 3 and p[3] else 0
            # 新浪可能返回涨跌幅为小数（如0.5表示0.5%）或已乘100，做修正
            if abs(pct) > 50 and price > 0:
                pct = pct / 100
            return _b(name, price, chg, pct)
        elif fmt == 'b':
            price = float(p[1]) if len(p) > 1 and p[1] else 0
            chg = float(p[2]) if len(p) > 2 and p[2] else 0
            pct = float(p[3]) if len(p) > 3 and p[3] else 0
            if abs(pct) > 50 and price > 0:
                pct = pct / 100
            return _b(name, price, chg, pct)
        elif fmt == 'hf':
            cur = float(p[0]); prev = float(p[7])
            chg = cur - prev
            pct = (chg / prev * 100) if prev else 0
            return _b(p[13], cur, chg, pct)
    except (ValueError, IndexError):
        return None
    return None


def _b(name, price, chg, pct):
    return {'name': name, 'price': round(price, 2),
            'change': round(chg, 2), 'changePct': round(pct, 2)}


# ═══════════════════════════════════════════════════════════
#  K线数据获取（增强版：支持周K/月K + 分钟K线 + 期货汇率换算）
# ═══════════════════════════════════════════════════════════

# --- 期货品种 -> akshare symbol 映射 ---
_FUTURES_AKSHARE_MAP = {
    'hf_GC': 'AU0',
    'hf_SI': 'AG0',
    'hf_CL': 'SC0',
}

# --- klt -> 新浪scale 映射 ---
_KLT_TO_SINA_SCALE = {
    '5':   '5',
    '15':  '15',
    '30':  '30',
    '60':  '60',
    '101': '240',
}

# --- klt -> 腾讯 period 映射 ---
_KLT_TO_TENCENT_PERIOD = {
    '101': 'day',
    '102': 'week',
    '103': 'month',
}

# --- 汇率缓存 ---
_usdcny_cache = {'value': None, 'time': 0}
_usdcny_lock = threading.Lock()


def _get_usdcny():
    now = time.time()
    with _usdcny_lock:
        if _usdcny_cache['value'] is not None and (now - _usdcny_cache['time']) < 300:
            return _usdcny_cache['value']
    try:
        url = 'https://hq.sinajs.cn/list=fx_susdcny'
        req = urllib.request.Request(url, headers={
            'Referer': 'https://finance.sina.com.cn',
            'User-Agent': 'Mozilla/5.0'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('gbk')
            parts = content.split('"')[1].split(',')
            rate = float(parts[1])
            with _usdcny_lock:
                _usdcny_cache['value'] = rate
                _usdcny_cache['time'] = now
            return rate
    except Exception:
        with _usdcny_lock:
            return _usdcny_cache['value'] or 6.75


def _convert_au0_to_gc(price_cny_per_gram, usdcny):
    return price_cny_per_gram / usdcny * 31.1035

def _convert_ag0_to_si(price_cny_per_kg, usdcny):
    return (price_cny_per_kg / 1.13) * 31.1035 / 1000 / usdcny

def _convert_sc0_to_cl(price_cny_per_barrel, usdcny):
    return price_cny_per_barrel / usdcny


_FUTURES_CONVERTERS = {
    'hf_GC': _convert_au0_to_gc,
    'hf_SI': _convert_ag0_to_si,
    'hf_CL': _convert_sc0_to_cl,
}

_futures_cache = {}
_futures_cache_lock = threading.Lock()
_futures_cache_time = {}


def _fetch_futures_minute_kline(code, klt, count):
    ak_symbol = _FUTURES_AKSHARE_MAP.get(code)
    if not ak_symbol:
        return None
    now = time.time()
    with _futures_cache_lock:
        if code in _futures_cache and klt in _futures_cache[code]:
            cache_age = now - _futures_cache_time.get(code, 0)
            if cache_age < 300:
                data = _futures_cache[code][klt]
                if data and len(data) > 0:
                    return data[-count:]
    try:
        import akshare as ak
        import pandas as pd
        df = ak.futures_zh_minute_sina(symbol=ak_symbol)
        if df is None or len(df) == 0:
            return None
        _col_map = {
            '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low',
            '成交量': 'volume', '日期': 'datetime', '时间': 'datetime',
        }
        df = df.rename(columns=_col_map)
        for col in ['open', 'high', 'low', 'close']:
            if col not in df.columns:
                return None
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        for col in ['open', 'high', 'low', 'close']:
            df = df[df[col].notna() & (df[col] > 0)]
        if len(df) == 0:
            return None
        usdcny = _get_usdcny()
        converter = _FUTURES_CONVERTERS.get(code)
        if converter:
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].apply(lambda x: converter(x, usdcny))
        minutes = int(klt)
        df2 = df.copy()
        if 'datetime' in df2.columns:
            df2['datetime'] = pd.to_datetime(df2['datetime'])
            df2 = df2.set_index('datetime')
        resampled = df2.resample(f'{minutes}min', closed='right', label='right').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum',
        }).dropna(how='all')
        resampled = resampled[
            resampled['open'].notna() & (resampled['open'] > 0) &
            resampled['high'].notna() & (resampled['high'] > 0) &
            resampled['low'].notna() & (resampled['low'] > 0) &
            resampled['close'].notna() & (resampled['close'] > 0)
        ]
        if len(resampled) == 0:
            return None
        result = []
        for idx, row in resampled.iterrows():
            result.append({
                'date': idx.strftime('%Y-%m-%d %H:%M'),
                'open': round(float(row['open']), 2),
                'close': round(float(row['close']), 2),
                'high': round(float(row['high']), 2),
                'low': round(float(row['low']), 2),
                'volume': round(float(row['volume']), 0) if pd.notna(row.get('volume')) else 0,
            })
        with _futures_cache_lock:
            if code not in _futures_cache:
                _futures_cache[code] = {}
            _futures_cache[code][klt] = result
            _futures_cache_time[code] = now
        return result[-count:] if result else None
    except Exception:
        return None


_tencent_week_month_cache = {}
_tencent_wm_cache_lock = threading.Lock()
_tencent_wm_cache_time = {}


def _fetch_tencent_period_kline(code, period, count=120):
    try:
        url = ('https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?'
               f'param={code},{period},,,640,qfq')
        body = _http_get(url, timeout=15, retries=2)
        if not body:
            return None
        data = json_module.loads(body)
        body_dict = data.get('data', {})
        if not isinstance(body_dict, dict):
            return None
        keys = list(body_dict.keys())
        if not keys:
            return None
        kline_dict = body_dict.get(keys[0], {})
        raw = kline_dict.get(period)
        if raw is None:
            raw = kline_dict.get('qfq' + period)
        if raw is None:
            raw = kline_dict.get('day')
        if raw is None:
            return None
        result = []
        for item in raw:
            try:
                d = {
                    'date': item[0],
                    'open': float(item[1]),
                    'close': float(item[2]),
                    'high': float(item[3]),
                    'low': float(item[4]),
                    'volume': float(item[5]) if len(item) > 5 and item[5] else 0,
                }
                result.append(d)
            except (ValueError, IndexError, TypeError):
                continue
        return result[-count:] if result else None
    except Exception:
        return None


def _fetch_tencent_period_kline_cached(code, period, count=120):
    now = time.time()
    cache_key = code + '_' + period
    with _tencent_wm_cache_lock:
        if cache_key in _tencent_week_month_cache:
            cache_age = now - _tencent_wm_cache_time.get(cache_key, 0)
            if cache_age < 1800:
                data = _tencent_week_month_cache[cache_key]
                if data and len(data) > 0:
                    return data[-count:]
    data = _fetch_tencent_period_kline(code, period, count)
    if data:
        with _tencent_wm_cache_lock:
            _tencent_week_month_cache[cache_key] = data
            _tencent_wm_cache_time[cache_key] = now
    return data


def _fetch_sina_gi_kline(symbol, count):
    """新浪全球指数日K线（gi.finance.sina.com.cn/hq/daily）
    symbol: 全球指数代码，如 KOSPI/DAX/NKY"""
    url = (f'https://gi.finance.sina.com.cn/hq/daily?symbol={symbol}&num=10000')
    body = _http_get(url, timeout=10, retries=2)
    if not body:
        return None
    try:
        j = json_module.loads(body)
        raw = j.get('result', {}).get('data', [])
    except Exception:
        return None
    if not raw:
        return None
    result = []
    for item in raw:
        try:
            close = float(item.get('c', 0) or 0)
            if close <= 0:
                continue  # 跳过收盘价为0的无效数据（当天未收盘/延迟）
            result.append({
                'date': str(item.get('d', '')),
                'open': float(item.get('o', 0) or 0),
                'close': close,
                'high': float(item.get('h', 0) or 0),
                'low': float(item.get('l', 0) or 0),
                'volume': float(item.get('v', 0) or 0),
            })
        except (ValueError, TypeError):
            continue
    return result[-count:] if len(result) > count else result


def _aggregate_day_to_period(day_data, period):
    if not day_data:
        return None
    try:
        import pandas as pd
        df = pd.DataFrame(day_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        for col in ['open', 'close', 'high', 'low', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        if period == 'week':
            resampled = df.resample('W-SUN', closed='right', label='right').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum',
            }).dropna(how='all')
        elif period == 'month':
            resampled = df.resample('M', closed='right', label='right').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum',
            }).dropna(how='all')
        else:
            return None
        if len(resampled) == 0:
            return None
        result = []
        for idx, row in resampled.iterrows():
            result.append({
                'date': idx.strftime('%Y-%m-%d'),
                'open': round(float(row['open']), 2) if pd.notna(row['open']) else 0,
                'close': round(float(row['close']), 2) if pd.notna(row['close']) else 0,
                'high': round(float(row['high']), 2) if pd.notna(row['high']) else 0,
                'low': round(float(row['low']), 2) if pd.notna(row['low']) else 0,
                'volume': round(float(row['volume']), 0) if pd.notna(row['volume']) else 0,
            })
        return result if result else None
    except Exception:
        return None


def _fetch_day_kline_for_minute(code, count):
    """日K降级：对无免费分时源的品种（道琼斯/纳指/标普），用日K数据填充分时周期"""
    try:
        data, src = fetch_kline_data(code, '101', count)
        if data and len(data) >= 2:
            return data
    except Exception:
        pass
    return None


def fetch_kline_data(code, klt='101', count=90):
    """获取K线数据（多源 fallback — 东方财富优先，覆盖全周期全品种）"""
    secid = KLINE_SECIDS.get(code)

    # 所有周期统一优先用东方财富（支持 5/15/30/60/101/102/103）
    if secid:
        data = _fetch_em_kline(secid, klt, count)
        if data:
            return data, '东方财富'

    if klt in ('102', '103'):
        period = _KLT_TO_TENCENT_PERIOD.get(klt)
        if period and code in TENCENT_KL:
            data = _fetch_tencent_period_kline_cached(TENCENT_KL[code], period, count)
            if data:
                return data, '腾讯'
        if code in SINA_A_KL:
            symbol = SINA_A_KL[code]
            day_data = _fetch_sina_kline(symbol, '240', count * 7 if klt == '102' else count * 31)
            if day_data and len(day_data) > 0:
                aggregated = _aggregate_day_to_period(day_data, period)
                if aggregated:
                    return aggregated[-count:], '新浪聚合'
        # 新浪指数聚合优先于新浪期货聚合（日经/韩国/德国用真实指数数据）
        if code in SINA_GI_KL:
            gi_symbol = SINA_GI_KL[code]
            day_data = _fetch_sina_gi_kline(gi_symbol, count * 7 if klt == '102' else count * 31)
            if day_data and len(day_data) > 0:
                aggregated = _aggregate_day_to_period(day_data, period)
                if aggregated:
                    return aggregated[-count:], '新浪指数聚合'
        if code in SINA_FUTURES_KL:
            futures_code = SINA_FUTURES_KL[code]
            day_data = _fetch_sina_futures_kline(futures_code, count * 7 if klt == '102' else count * 31)
            if day_data and len(day_data) > 0:
                aggregated = _aggregate_day_to_period(day_data, period)
                if aggregated:
                    return aggregated[-count:], '新浪期货聚合'
        return None, None

    if klt == '101':
        if code in SINA_GI_KL:
            data = _fetch_sina_gi_kline(SINA_GI_KL[code], count)
            if data:
                return data, '新浪指数'
        if code in TENCENT_KL:
            data = _fetch_tencent_kline(TENCENT_KL[code])
            if data:
                return data[-count:], '腾讯'
        if code in SINA_A_KL:
            data = _fetch_sina_kline(SINA_A_KL[code], '240', count)
            if data:
                return data, '新浪'
        if code in SINA_FUTURES_KL:
            data = _fetch_sina_futures_kline(SINA_FUTURES_KL[code], count)
            if data:
                return data, '新浪期货'
        return None, None

    if klt not in ('5', '15', '30', '60'):
        return None, None
    # 分时K线多源fallback：
    # 1. 新浪A股（上证/深证）
    # 2. 新浪期货→akshare（黄金/白银/原油）
    # 3. 新浪全球指数分时聚合（日经/韩国/德国）
    # 4. 百度getquotation K线API（道琼斯/纳指/标普）
    # 5. 百度getbanner分时聚合（恒生）
    if code in SINA_A_KL:
        symbol = SINA_A_KL[code]
        scale = _KLT_TO_SINA_SCALE.get(klt)
        if scale:
            data = _fetch_sina_kline(symbol, scale, count)
            if data:
                return data, '新浪'
    if code in _FUTURES_AKSHARE_MAP:
        data = _fetch_futures_minute_kline(code, klt, count)
        if data:
            return data, '新浪期货'
    if code in SINA_GI_MIN:
        data = _fetch_sina_gi_min_kline(SINA_GI_MIN[code], klt, count)
        if data:
            return data, '新浪指数分时'
    if code in BAIDU_KLINE_MAP:
        data = _fetch_baidu_kline(code, klt, count)
        if data:
            return data, '百度K线'
    if code in BAIDU_MIN_MAP:
        data = _fetch_baidu_min_kline(code, klt, count)
        if data:
            return data, '百度分时'
    return None, None


def _fetch_em_kline(secid, klt, count):
    """东方财富K线（urllib带熔断器）"""
    path = (f'/api/qt/stock/kline/get?'
            f'secid={secid}&fields1=f1,f2,f3,f4,f5,f6'
            f'&fields2=f51,f52,f53,f54,f55,f56,f57'
            f'&klt={klt}&fqt=1&end=20500101&lmt={count}')

    url = f'http://push2his.eastmoney.com{path}'
    body = _http_get_em(url, timeout=10, retries=1)
    if not body:
        return None
    try:
        j = json_module.loads(body)
        klines = j.get('data', {}).get('klines', [])
    except Exception:
        return None
    if not klines:
        return None
    result = []
    for line in klines:
        p = line.split(',')
        if len(p) < 6:
            continue
        try:
            result.append({
                'date': p[0],
                'open': float(p[1]),
                'close': float(p[2]),
                'high': float(p[3]),
                'low': float(p[4]),
                'volume': float(p[5]) if p[5] else 0,
            })
        except (ValueError, IndexError):
            continue
    return result if result else None


# ═══ 新浪全球指数分时→OHLC聚合 ═══
# SINA_GI_MIN mapping: 品种code -> gi symbol（支持分时数据的品种）
SINA_GI_MIN = {
    'gb_n225':  'NKY',
    'b_KOSPI':  'KOSPI',
    'b_DAX':    'DAX',
}

_gi_min_cache = {}  # (symbol, klt) -> data
_gi_min_cache_time = {}
_gi_min_lock = threading.Lock()


def _fetch_sina_gi_min_kline(symbol, klt, count):
    """从新浪全球指数分时接口获取逐笔数据，聚合为OHLC K线
    symbol: NKY/KOSPI/DAX
    klt: 5/15/30/60
    """
    now = time.time()
    with _gi_min_lock:
        cache_key = (symbol, klt)
        if cache_key in _gi_min_cache and (now - _gi_min_cache_time.get(cache_key, 0)) < 60:
            data = _gi_min_cache[cache_key]
            if data:
                return data[-count:]

    url = f'https://gi.finance.sina.com.cn/hq/min?symbol={symbol}&num=2000'
    body = _http_get(url, timeout=10, retries=2)
    if not body:
        return None
    try:
        j = json_module.loads(body)
        raw = j.get('result', {}).get('data', [])
    except Exception:
        return None
    if not raw:
        return None

    # 解析逐笔数据，提取 datetime + price
    from datetime import datetime as _dt, timedelta as _td
    bars = []
    current_date = None
    for item in raw:
        if not item or len(item) < 2:
            continue
        t_str = item[0]       # "08:00"
        try:
            price = float(item[1])
        except (ValueError, IndexError):
            continue
        if len(item) >= 5:
            current_date = item[4]  # "2026-08-07"
        if not current_date:
            continue
        try:
            dt = _dt.strptime(f'{current_date} {t_str}', '%Y-%m-%d %H:%M')
        except ValueError:
            continue
        if price > 0:
            bars.append((dt, price))

    if not bars:
        return None

    # 按klt分钟聚合为OHLC
    period = int(klt)
    result = []
    i = 0
    n = len(bars)
    while i < n:
        dt_start = bars[i][0]
        aligned_min = (dt_start.minute // period) * period
        bucket_start = dt_start.replace(minute=aligned_min, second=0)
        bucket_end = bucket_start + _td(minutes=period)
        prices = []
        j = i
        while j < n and bars[j][0] < bucket_end:
            prices.append(bars[j][1])
            j += 1
        if prices:
            result.append({
                'date': bucket_start.strftime('%Y-%m-%d %H:%M'),
                'open': round(prices[0], 2),
                'close': round(prices[-1], 2),
                'high': round(max(prices), 2),
                'low': round(min(prices), 2),
                'volume': 0,
            })
        i = j

    if not result:
        return None

    with _gi_min_lock:
        _gi_min_cache[cache_key] = result
        _gi_min_cache_time[cache_key] = now

    return result[-count:]


# ═══ 百度getquotation K线API（道琼斯/纳指/标普 分时+日周月K） ═══
_baidu_kline_cache = {}
_baidu_kline_cache_time = {}
_baidu_kline_lock = threading.Lock()

# 百度getquotation覆盖的品种：美股三大指数
# 百度页面: https://finance.baidu.com/index/us-DJI
BAIDU_KLINE_MAP = {
    'gb_dji':  ('DJI',  '道琼斯'),
    'gb_ixic': ('IXIC', '纳斯达克'),
    'gb_inx':  ('SPX',  '标普500'),
}

# klt → 百度ktype
_KLT_TO_BAIDU_KTYPE = {
    '5':   'min5',
    '15':  'min15',
    '30':  'min30',
    '60':  'min60',
    '101': 'day',
    '102': 'week',
    '103': 'month',
}


def _fetch_baidu_kline(code, klt, count):
    """从百度getquotation接口获取K线数据
    覆盖道琼斯/纳指/标普，支持 5/15/30/60分 + 日/周/月K
    """
    if code not in BAIDU_KLINE_MAP:
        return None
    baidu_code, baidu_name = BAIDU_KLINE_MAP[code]
    ktype = _KLT_TO_BAIDU_KTYPE.get(klt)
    if not ktype:
        return None

    now = time.time()
    with _baidu_kline_lock:
        cache_key = (code, klt)
        if cache_key in _baidu_kline_cache and (now - _baidu_kline_cache_time.get(cache_key, 0)) < 60:
            data = _baidu_kline_cache[cache_key]
            if data:
                return data[-count:]

    # group=quotation_index_kline 适用于所有K线周期（min5/min15/min30/min60/day/week/month）
    # group=quotation_index_minute 适用于分时走势（不需要ktype）
    if ktype == 'min' or klt not in _KLT_TO_BAIDU_KTYPE:
        group = 'quotation_index_minute'
        url = (f'https://finance.pae.baidu.com/vapi/v1/getquotation?'
               f'srcid=5353&pointType=string&group={group}'
               f'&query={baidu_code}&code={baidu_code}&market_type=us'
               f'&newFormat=1&name={urllib.parse.quote(baidu_name)}&is_kc=0')
    else:
        group = 'quotation_index_kline'
        url = (f'https://finance.pae.baidu.com/vapi/v1/getquotation?'
               f'srcid=5353&pointType=string&group={group}'
               f'&query={baidu_code}&code={baidu_code}&market_type=us'
               f'&newFormat=1&name={urllib.parse.quote(baidu_name)}&is_kc=0'
               f'&ktype={ktype}')

    body = _http_get(url, timeout=10, retries=2)
    if not body:
        return None
    try:
        j = json_module.loads(body)
        result = j.get('Result', {})
        market_data = result.get('newMarketData', {})
        raw = market_data.get('marketData', [])
    except Exception:
        return None
    if not raw:
        return None

    # marketData 是一个用分号分隔的字符串，每条记录用逗号分隔的CSV格式:
    # "ts,time,open,close,vol,high,low,...;ts,time,open,...;..."
    # fields: [0]=timestamp, [1]=time, [2]=open, [3]=close,
    #         [4]=volume, [5]=high, [6]=low, ...
    if isinstance(raw, str):
        records = raw.split(';')
    elif isinstance(raw, list):
        # 如果API返回的是列表，看元素是字符串还是单字符
        if raw and isinstance(raw[0], str) and len(raw[0]) <= 1:
            # 扁平字符数组，拼接后按分号分割
            records = ''.join(raw).split(';')
        else:
            records = raw
    else:
        return None

    result_list = []
    for entry in records:
        if isinstance(entry, str):
            parts = entry.split(',')
        elif isinstance(entry, list):
            parts = [str(x) for x in entry]
        else:
            continue
        if len(parts) < 7:
            continue
        try:
            dt_str = parts[1]   # time ("2026-07-22 10:45")
            o = float(parts[2]) # open
            c = float(parts[3]) # close
            v = float(parts[4]) if parts[4] and parts[4] != '--' else 0
            h = float(parts[5]) # high
            l = float(parts[6]) # low
            result_list.append({
                'date': dt_str,
                'open': o,
                'close': c,
                'high': h,
                'low': l,
                'volume': v,
            })
        except (ValueError, IndexError):
            continue

    if not result_list:
        return None

    with _baidu_kline_lock:
        _baidu_kline_cache[cache_key] = result_list
        _baidu_kline_cache_time[cache_key] = now

    return result_list[-count:]


# ═══ 百度getbanner分时→OHLC聚合（恒生指数） ═══
_baidu_min_cache = {}
_baidu_min_cache_time = {}
_baidu_min_lock = threading.Lock()

# 百度getbanner 只覆盖恒生（其他品种不稳定）
BAIDU_MIN_MAP = {
    'rt_hkHSI': 'HSI',
}


def _fetch_baidu_min_kline(code, klt, count):
    """从百度getbanner接口获取恒生当日分时价格序列，聚合成OHLC K线
    限制：只有当日数据，返回的K线数量较少
    """
    now = time.time()
    with _baidu_min_lock:
        cache_key = (code, klt)
        if cache_key in _baidu_min_cache and (now - _baidu_min_cache_time.get(cache_key, 0)) < 60:
            data = _baidu_min_cache[cache_key]
            if data:
                return data[-count:]

    url = 'https://finance.pae.baidu.com/api/getbanner?market=hk&group=quaternion_kline'
    headers_baidu = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://finance.baidu.com/',
    }
    try:
        req = urllib.request.Request(url, headers=headers_baidu)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8')
        j = json_module.loads(body)
    except Exception:
        return None

    result_list = j.get('Result', {}).get('list', [])
    if not result_list:
        return None

    # 找到目标品种
    target_code = BAIDU_MIN_MAP.get(code)
    if not target_code:
        return None
    target_item = None
    for item in result_list:
        if item.get('code') == target_code:
            target_item = item
            break
    if not target_item:
        return None

    p_str = target_item.get('p', '')
    if not p_str:
        return None

    prices_raw = p_str.split(',')
    prices = []
    for p in prices_raw:
        try:
            v = float(p)
            if v > 0:
                prices.append(v)
        except ValueError:
            continue

    if len(prices) < 2:
        return None

    # 百度返回50个价格点（当日的），间隔约6分钟（恒生交易时间 9:30-16:00 = 390分钟 / 50 ≈ 8分钟）
    # 按 klt 分钟聚合
    period = int(klt)
    # 估算每个价格点间隔（恒生 9:30~16:00 = 390min, 50点 → ~8min/点）
    step_min = max(1, 390 // max(len(prices), 1))
    from datetime import datetime as _dt2, timedelta as _td2
    base_dt = _dt2.now().replace(hour=9, minute=30, second=0, microsecond=0)

    # 生成带时间戳的价格序列
    timed_prices = []
    for idx, p in enumerate(prices):
        dt = base_dt + _td2(minutes=idx * step_min)
        timed_prices.append((dt, p))

    # 聚合为OHLC
    result = []
    i = 0
    n = len(timed_prices)
    while i < n:
        dt_start = timed_prices[i][0]
        aligned_min = (dt_start.minute // period) * period
        bucket_start = dt_start.replace(minute=aligned_min, second=0)
        bucket_end = bucket_start + _td2(minutes=period)
        bucket_prices = []
        j = i
        while j < n and timed_prices[j][0] < bucket_end:
            bucket_prices.append(timed_prices[j][1])
            j += 1
        if bucket_prices:
            result.append({
                'date': bucket_start.strftime('%Y-%m-%d %H:%M'),
                'open': round(bucket_prices[0], 2),
                'close': round(bucket_prices[-1], 2),
                'high': round(max(bucket_prices), 2),
                'low': round(min(bucket_prices), 2),
                'volume': 0,
            })
        i = j

    if not result:
        return None

    with _baidu_min_lock:
        _baidu_min_cache[cache_key] = result
        _baidu_min_cache_time[cache_key] = now

    return result[-count:]


def _fetch_sina_futures_kline(symbol, count):
    url = (f'https://stock2.finance.sina.com.cn/futures/api/jsonp.php'
           f'/var_/GlobalFuturesService.getGlobalFuturesDailyKLine?symbol={symbol}')
    body = _http_get(url, timeout=10, retries=2)
    if not body:
        return None
    m = re.search(r'var_\((.+)\)', body, re.S)
    if not m:
        return None
    try:
        raw = json_module.loads(m.group(1))
    except Exception:
        return None
    result = []
    for item in raw:
        try:
            result.append({
                'date': item.get('date', ''),
                'open': float(item.get('open', 0)),
                'close': float(item.get('close', 0)),
                'high': float(item.get('high', 0)),
                'low': float(item.get('low', 0)),
                'volume': float(item.get('volume', 0) or 0),
            })
        except (ValueError, TypeError):
            continue
    return result[-count:] if len(result) > count else result


def _fetch_sina_kline(symbol, scale, count):
    url = (f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/'
           f'CN_MarketData.getKLineData?symbol={symbol}&scale={scale}'
           f'&ma=no&datalen={count}')
    body = _http_get(url, timeout=10, retries=2)
    if not body:
        return None
    try:
        raw = json_module.loads(body)
    except Exception:
        return None
    if not raw:
        return None
    result = []
    for item in raw:
        try:
            result.append({
                'date': item.get('day', ''),
                'open': float(item.get('open', 0)),
                'close': float(item.get('close', 0)),
                'high': float(item.get('high', 0)),
                'low': float(item.get('low', 0)),
                'volume': float(item.get('volume', 0) or 0),
            })
        except (ValueError, TypeError):
            continue
    return result if result else None


def _fetch_tencent_kline(code):
    url = (f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?'
           f'param={code},day,,,640,qfq')
    body = _http_get(url, timeout=10, retries=2)
    if not body:
        return None
    try:
        data = json_module.loads(body)
    except Exception:
        return None
    body_dict = data.get('data', {})
    if not isinstance(body_dict, dict):
        return None
    kline_dict = body_dict.get(code, {})
    raw = kline_dict.get('day') or kline_dict.get('qfqday')
    if not raw:
        return None
    result = []
    for item in raw:
        try:
            result.append({
                'date': item[0],
                'open': float(item[1]),
                'close': float(item[2]),
                'high': float(item[3]),
                'low': float(item[4]),
                'volume': float(item[5]) if len(item) > 5 and item[5] else 0,
            })
        except (ValueError, IndexError, TypeError):
            continue
    return result if result else None


# ═══════════════════════════════════════════════════════════
#  配色（白底主题）
# ═══════════════════════════════════════════════════════════

C_TRANS  = '#000000'
C_PANEL_T = '#ffffff'
C_PANEL_B = '#f4f6f9'
C_PANEL2 = '#e8ecf2'
C_BORDER = '#d4dae5'
C_TEXT   = '#1e293b'
C_DIM    = '#64748b'
C_FAINT  = '#94a3b8'
C_RED    = '#ef4444'
C_GREEN  = '#22c55e'
C_GRAY   = '#94a3b8'
C_ACCENT = '#3b82f6'
C_GOLD   = '#f59e0b'
C_BTN_BG = '#f1f5f9'
C_BTN_HOVER = '#e2e8f0'
C_BTN_PRESS = '#cbd5e1'
C_BTN_ACTIVE_BG = '#dbeafe'
C_BTN_ACTIVE_BORDER = '#3b82f6'

# 品种分类配色: {fmt: (btn_bg, btn_border, arrow_color, name_color)}
CAT_COLORS = {
    'hf':  ('#fef3c7', '#f59e0b', '#d97706', '#92400e'),  # 期货 — 琥珀金
    's':   ('#dbeafe', '#3b82f6', '#2563eb', '#1e40af'),  # A股 — 蓝色
    'hk':  ('#fee2e2', '#ef4444', '#dc2626', '#991b1b'),  # 港股 — 红色
    'gb':  ('#ede9fe', '#8b5cf6', '#7c3aed', '#5b21b6'),  # 海外指数 — 紫色
    'b':   ('#dcfce7', '#22c55e', '#16a34a', '#166534'),   # 外围指数 — 绿色
}

# 小窗品种图标（单个汉字，一眼识别品种）
MINI_ICONS = {
    'hf_GC':       '\u91d1',  # 金 黄金
    'hf_SI':       '\u94f6',  # 银 白银
    'hf_CL':       '\u6cb9',  # 油 原油
    's_sh000001':  '\u6caa',  # 沪 上证
    's_sz399001':  '\u6df1',  # 深 深证
    'rt_hkHSI':    '\u6e2f',  # 港 恒生
    'gb_dji':      '\u9053',  # 道 道琼斯
    'gb_ixic':     '\u7eb3',  # 纳 纳斯达克
    'gb_inx':      '\u666e',  # 普 标普500
    'gb_n225':     '\u65e5',  # 日 日经225
    'b_KOSPI':     '\u97e9',  # 韩 韩国
    'b_DAX':       '\u5fb7',  # 德 德国
}

# 每种分类的图标符号
CAT_ICONS = {
    'hf':  '\u26AB',  # ⚫ 期货
    's':   '\u25C6',  # ◆ A股
    'hk':  '\u25C9',  # ◉ 港股
    'gb':  '\u25C8',  # ◈ 海外
    'b':   '\u25CA',  # ◊ 外围
}

C_K_T = '#ffffff'
C_K_B = '#f8fafc'
C_K_BORDER = '#d4dae5'

C_MA5    = '#f59e0b'
C_MA10   = '#a855f7'
C_MA20   = '#f97316'


# ═══════════════════════════════════════════════════════════
#  Pillow 图形
# ═══════════════════════════════════════════════════════════

def _hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _lerp_color(c1, c2, t):
    r1, g1, b1 = _hex2rgb(c1)
    r2, g2, b2 = _hex2rgb(c2)
    return (int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t),
            255)


def _rrect_shadow(w, h, r, fill_top, fill_bot=None, outline=None, bw=1):
    pad = 6
    total_w, total_h = w + pad * 2, h + pad * 2
    base = Image.new('RGBA', (total_w, total_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    for i in range(pad, 0, -1):
        a = int(35 * (1 - i / pad))
        d.rounded_rectangle(
            [pad - i, pad - i + 1, w + pad + i - 1, h + pad + i - 1],
            radius=r + i, fill=(0, 0, 0, a))
    use_grad = fill_bot is not None and fill_bot != fill_top
    if use_grad:
        grad = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        for y in range(h):
            t = y / max(1, h - 1)
            gd.line([(0, y), (w - 1, y)], fill=_lerp_color(fill_top, fill_bot, t))
        mask = Image.new('L', (w, h), 0)
        md = ImageDraw.Draw(mask)
        md.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
        base.paste(grad, (pad, pad), mask)
    else:
        d2 = ImageDraw.Draw(base)
        d2.rounded_rectangle([pad, pad, w + pad - 1, h + pad - 1], radius=r, fill=fill_top)
    if outline:
        d3 = ImageDraw.Draw(base)
        d3.rounded_rectangle([pad, pad, w + pad - 1, h + pad - 1], radius=r, outline=outline, width=bw)
    return base, pad


def _circle_shadow(diameter, fill_top, fill_bot=None, outline=None, bw=1):
    """生成带阴影的圆形背景图，返回 (image, pad)"""
    pad = 6
    total = diameter + pad * 2
    base = Image.new('RGBA', (total, total), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    # 阴影
    for i in range(pad, 0, -1):
        a = int(35 * (1 - i / pad))
        d.ellipse([pad - i, pad - i + 1, diameter + pad + i - 1, diameter + pad + i - 1], fill=(0, 0, 0, a))
    # 渐变填充
    use_grad = fill_bot is not None and fill_bot != fill_top
    if use_grad:
        grad = Image.new('RGBA', (diameter, diameter), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        for y in range(diameter):
            t = y / max(1, diameter - 1)
            gd.line([(0, y), (diameter - 1, y)], fill=_lerp_color(fill_top, fill_bot, t))
        mask = Image.new('L', (diameter, diameter), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse([0, 0, diameter - 1, diameter - 1], fill=255)
        base.paste(grad, (pad, pad), mask)
    else:
        d2 = ImageDraw.Draw(base)
        d2.ellipse([pad, pad, pad + diameter - 1, pad + diameter - 1], fill=fill_top)
    # 边框
    if outline:
        d3 = ImageDraw.Draw(base)
        d3.ellipse([pad, pad, pad + diameter - 1, pad + diameter - 1], outline=outline, width=bw)
    return base, pad


def _circle_sectors_shadow(diameter, fill_top, fill_bot=None, outline=None, bw=1, sector_lines=True):
    """生成带阴影+扇形分割线的圆形背景图，返回 (image, pad)"""
    pad = 6
    total = diameter + pad * 2
    base = Image.new('RGBA', (total, total), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    for i in range(pad, 0, -1):
        a = int(35 * (1 - i / pad))
        d.ellipse([pad - i, pad - i + 1, diameter + pad + i - 1, diameter + pad + i - 1], fill=(0, 0, 0, a))
    use_grad = fill_bot is not None and fill_bot != fill_top
    if use_grad:
        grad = Image.new('RGBA', (diameter, diameter), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        for y in range(diameter):
            t = y / max(1, diameter - 1)
            gd.line([(0, y), (diameter - 1, y)], fill=_lerp_color(fill_top, fill_bot, t))
        mask = Image.new('L', (diameter, diameter), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse([0, 0, diameter - 1, diameter - 1], fill=255)
        base.paste(grad, (pad, pad), mask)
    else:
        d2 = ImageDraw.Draw(base)
        d2.ellipse([pad, pad, pad + diameter - 1, pad + diameter - 1], fill=fill_top)
    if sector_lines:
        import math
        cx_p, cy_p = pad + diameter // 2, pad + diameter // 2
        r = diameter // 2
        line_color = _hex2rgb(C_BORDER) + (120,)
        d3 = ImageDraw.Draw(base)
        for angle_deg in [210, 330]:
            rad = math.radians(angle_deg)
            x2 = cx_p + int(r * math.cos(rad))
            y2 = cy_p + int(r * math.sin(rad))
            d3.line([(cx_p, cy_p), (x2, y2)], fill=line_color, width=1)
        d3.line([(cx_p - r + 2, cy_p), (cx_p + r - 2, cy_p)], fill=line_color, width=1)
    if outline:
        d4 = ImageDraw.Draw(base)
        d4.ellipse([pad, pad, pad + diameter - 1, pad + diameter - 1], outline=outline, width=bw)
    return base, pad
# ═══════════════════════════════════════════════════════════

class KLineWindow:
    WIN_W = 840
    WIN_H = 600
    TITLE_H = 57
    KLINE_H = 375
    VOL_H = 87
    PAD_L = 12
    PAD_R = 72
    PAD_T = 15
    PAD_B_K = 12
    GAP_V = 6

    PERIODS = [
        ('5',   '5'),
        ('15',  '15'),
        ('30',  '30'),
        ('60',  '60'),
        ('101', '日'),
        ('102', '周'),
        ('103', '月'),
    ]

    def __init__(self, parent_root, code, name, on_close_cb=None, latest_quote=None):
        self.code = code
        self.name = name
        self.period = '101'
        self.data = None
        self.running = True
        self._drag = None
        self._on_close_cb = on_close_cb
        self._drawn_items = []
        self._req_seq = 0
        self._latest_quote = latest_quote
        self._source_name = ''
        self.win = tk.Toplevel(parent_root)
        self.win.overrideredirect(True)
        self.win.attributes('-topmost', True)
        self.win.configure(bg=C_K_B)
        pos = self._load_pos()
        self.win.geometry(f'{self.WIN_W}x{self.WIN_H}+{pos[0]}+{pos[1]}')
        self._build_ui()
        try:
            self._rebuild_period_buttons()
        except Exception:
            pass
        self._fetch_and_draw()

    def _rebuild_period_buttons(self):
        cv = self.cv
        for klt_key, tid in list(self._period_text.items()):
            try:
                cv.delete(tid)
            except:
                pass
        self._period_rects = []
        self._period_text = {}
        btn_w = 48
        btn_gap = 6
        font_period = ('Microsoft YaHei', 14)
        try:
            w = int(cv.cget('width'))
        except:
            w = 1170
        bx = w - 30
        for klt, label in reversed(self.PERIODS):
            x1 = bx
            x0 = bx - btn_w
            tid = cv.create_text((x0 + x1) // 2, 21, text=label,
                fill=C_GOLD if klt == self.period else C_DIM,
                font=font_period, anchor='center')
            self._period_text[klt] = tid
            self._period_rects.append((x0, x1, klt))
            bx = x0 - btn_gap

    def _build_ui(self):
        w, h = self.WIN_W, self.WIN_H
        bg_img, _ = _rrect_shadow(w - 12, h - 12, 21, C_K_T, C_K_B, C_K_BORDER, 1)
        self._bg = ImageTk.PhotoImage(bg_img)
        cv = tk.Canvas(self.win, width=w, height=h, bg=C_K_B, highlightthickness=0)
        cv.pack()
        cv.create_image(6, 6, image=self._bg, anchor='nw')
        self.cv = cv
        title_id = cv.create_text(30, 17, text=self.name, fill=C_TEXT,
                       font=('Microsoft YaHei', 18, 'bold'), anchor='nw')
        # 用 bbox 测量标题实际宽度，避免固定偏移导致重叠
        self.win.update_idletasks()
        try:
            bbox = cv.bbox(title_id)
            title_w = (bbox[2] - bbox[0]) if bbox else 20 * len(self.name)
        except Exception:
            title_w = 20 * len(self.name)
        self._title_price = cv.create_text(30 + title_w + 14, 20,
            text='', fill=C_DIM, font=('Consolas', 15), anchor='nw')
        self._period_rects = []
        self._period_text = {}
        bx = w - 405
        for klt, label in self.PERIODS:
            x0_b = bx; x1_b = bx + 60
            self._period_rects.append((x0_b, x1_b, klt))
            tid = cv.create_text((x0_b + x1_b) / 2, 29, text=label,
                fill=C_GOLD if klt == self.period else C_DIM,
                font=('Microsoft YaHei', 14), anchor='center')
            self._period_text[klt] = tid
            bx += 66
        self._close_x = w - 27
        self._close_item = cv.create_text(self._close_x, 27, text='\u2715',
            fill=C_DIM, font=('Segoe UI', 21, 'bold'), anchor='center')
        self._status = cv.create_text(w // 2, self.TITLE_H // 2 + 3,
            text='\u52A0\u8F7D\u4E2D...', fill=C_GOLD,
            font=('Microsoft YaHei', 17), anchor='center')
        self._legend_y = self.TITLE_H + self.PAD_T + 2
        self._update_title_quote()

        def on_click(e):
            # 点击状态文字区域可重新请求（失败重试）
            try:
                status_text = self.cv.itemcget(self._status, 'text')
            except Exception:
                status_text = ''
            if status_text and self.TITLE_H < e.y < self.TITLE_H + 60:
                # 点击"暂无数据"等状态文字时重新请求
                self._fetch_and_draw()
                return
            # 拖拽区域：只在标题栏上方（排除周期按钮和关闭按钮区域）
            if 3 < e.y < self.TITLE_H:
                if e.x > self._close_x - 16:
                    self._on_close(); return
                for x0_b, x1_b, klt in self._period_rects:
                    if x0_b - 2 <= e.x <= x1_b + 2:
                        self._switch_period(klt); return
                # 只在标题左侧区域（品种名+价格）允许拖拽，避免误触周期按钮
                period_x0 = self.WIN_W - 405
                if e.x < period_x0 - 10 or e.x > self._close_x + 16:
                    self._drag = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())
        def on_drag(e):
            if not self._drag: return
            x = e.x_root - self._drag[0]; y = max(0, e.y_root - self._drag[1])
            sw = self.win.winfo_screenwidth(); sh = self.win.winfo_screenheight() - 40
            self.win.geometry(f'+{max(0,min(x,sw-self.WIN_W))}+{max(0,min(y,sh-self.WIN_H))}')
        def on_release(e):
            if self._drag: self._drag = None; self._save_pos()
        def on_motion(e):
            if 3 < e.y < self.TITLE_H:
                self.cv.itemconfig(self._close_item, fill=C_RED if e.x > self._close_x - 16 else C_DIM)
                for x0_b, x1_b, klt in self._period_rects:
                    if x0_b - 2 <= e.x <= x1_b + 2:
                        if klt != self.period: self.cv.itemconfig(self._period_text[klt], fill=C_ACCENT)
                    else:
                        if klt != self.period: self.cv.itemconfig(self._period_text[klt], fill=C_DIM)
        cv.bind('<Button-1>', on_click); cv.bind('<B1-Motion>', on_drag)
        cv.bind('<ButtonRelease-1>', on_release); cv.bind('<Motion>', on_motion)
        self.win.bind('<Escape>', lambda e: self._on_close()); self.win.focus_force()

    def _update_title_quote(self):
        if not self._latest_quote: return
        q = self._latest_quote; price = q.get('price', 0); chg = q.get('change', 0); pct = q.get('changePct', 0)
        c = C_RED if chg > 0 else C_GREEN if chg < 0 else C_GRAY
        arrow = '\u25B2' if chg > 0 else '\u25BC' if chg < 0 else '\u2500'
        # 周期按钮区域起始x
        period_x0 = self.WIN_W - 405
        # 标题价格文字起始x
        price_x = self.cv.coords(self._title_price)[0]
        max_w = period_x0 - price_x - 12  # 留12px间距
        # 先尝试完整格式
        full_text = f'{price:,.2f}  {arrow} {pct:+.2f}%'
        self.cv.itemconfig(self._title_price, text=full_text, fill=c)
        self.win.update_idletasks()
        try:
            bbox = self.cv.bbox(self._title_price)
            tw = (bbox[2] - bbox[0]) if bbox else 0
        except Exception:
            tw = 0
        # 如果超出，逐步省略：去掉小数
        if tw > max_w:
            alt_text = f'{price:,.0f}  {arrow} {pct:+.2f}%'
            self.cv.itemconfig(self._title_price, text=alt_text, fill=c)
            self.win.update_idletasks()
            try:
                bbox = self.cv.bbox(self._title_price)
                tw = (bbox[2] - bbox[0]) if bbox else 0
            except Exception:
                tw = 0
            # 如果还是超出，去掉涨幅只保留价格
            if tw > max_w:
                alt_text = f'{price:,.0f}  {arrow} {pct:+.1f}%'
                self.cv.itemconfig(self._title_price, text=alt_text, fill=c)

    def _switch_period(self, klt):
        if klt == self.period: return
        self.period = klt
        for k, tid in self._period_text.items():
            self.cv.itemconfig(tid, fill=C_GOLD if k == klt else C_DIM)
        self._fetch_and_draw()

    def _fetch_and_draw(self):
        self._clear_drawn()
        self.cv.itemconfig(self._status, text='\u52A0\u8F7D\u4E2D...', fill=C_GOLD)
        self._req_seq += 1; my_seq = self._req_seq
        def worker():
            try:
                data, src = fetch_kline_data(self.code, self.period, 90)
            except Exception as e:
                _log(f'KLine fetch exception ({self.code}): {e}'); data, src = None, None
            if self.running and my_seq == self._req_seq:
                self.win.after(0, lambda d=data, s=src: self._on_data(d, s))
        threading.Thread(target=worker, daemon=True).start()

    def _auto_refresh_kline(self):
        """主窗口刷新时调用，自动刷新分时K线（5/15/30/60分），避免频繁刷新日周月"""
        if not self.running or not self.data:
            return
        if self.period not in ('5', '15', '30', '60'):
            return  # 日/周/月K不自动刷新
        self._fetch_and_draw()

    def _on_data(self, data, source=None):
        if not data or len(data) < 2:
            self._source_name = ''
            self.cv.itemconfig(self._status, text='\u6682\u65E0\u6570\u636E \u00B7 \u70B9\u51FB\u6B64\u5904\u91CD\u8BD5', fill=C_RED)
            return
        self.data = data; self._source_name = source or ''
        self.cv.itemconfig(self._status, text=''); self._draw()

    def _clear_drawn(self):
        for item in self._drawn_items:
            try: self.cv.delete(item)
            except tk.TclError: pass
        self._drawn_items = []

    def _draw(self):
        cv = self.cv; data = self.data; n = len(data); self._clear_drawn()
        x0 = self.PAD_L; x1 = self.WIN_W - self.PAD_R
        k_y0 = self.TITLE_H + self.PAD_T; k_y1 = self.TITLE_H + self.KLINE_H - self.PAD_B_K
        v_y0 = self.TITLE_H + self.KLINE_H + self.GAP_V; v_y1 = v_y0 + self.VOL_H - 6
        plot_w = x1 - x0; bar_step = plot_w / n; bar_w = max(1.5, min(8, bar_step * 0.7))
        highs = [d['high'] for d in data]; lows = [d['low'] for d in data]
        p_max = max(highs); p_min = min(lows); p_range = p_max - p_min
        if p_range == 0: p_range = max(p_max * 0.01, 1)
        p_pad = p_range * 0.08; p_max += p_pad; p_min -= p_pad; p_range = p_max - p_min
        def p2y(p): return k_y0 + (p_max - p) / p_range * (k_y1 - k_y0)
        vols = [d['volume'] for d in data]; v_max = max(vols) if vols else 1
        if v_max == 0: v_max = 1
        def v2y(v): return v_y1 - (v / v_max) * (v_y1 - v_y0) if v_max else v_y1
        # 计算现价标签Y位置（提前计算，用于Y轴刻度跳过）
        last = data[-1]; last_c = last['close']; last_o = last['open']; last_y = p2y(last_c)
        last_color = C_RED if last_c >= last_o else C_GREEN

        steps = 4
        for i in range(steps + 1):
            gy = k_y0 + (k_y1 - k_y0) * i / steps; price = p_max - p_range * i / steps
            self._add(cv.create_line(x0, gy, x1, gy, fill=C_BORDER, width=1, dash=(1, 3)))
            # Y轴价格文字右对齐到窗口右边界，跳过现价标签所在行
            if abs(gy - last_y) > 14:
                self._add(cv.create_text(self.WIN_W - 4, gy, text=f'{price:.2f}', fill=C_DIM, font=('Consolas', 11), anchor='ne'))
        self._add(cv.create_line(x0, v_y1, x1, v_y1, fill=C_BORDER, width=1))
        self._add(cv.create_text(self.WIN_W - 4, v_y0 + (v_y1 - v_y0) / 2, text='\u91CF', fill=C_FAINT, font=('Microsoft YaHei', 11), anchor='ne'))
        # 成交量全为0时显示提示
        _all_vol_zero = all(d['volume'] == 0 for d in data)
        if _all_vol_zero:
            self._add(cv.create_text((x0 + x1) / 2, v_y0 + (v_y1 - v_y0) / 2,
                text='\u65E0\u91CF\u6570\u636E', fill=C_FAINT,
                font=('Microsoft YaHei', 12), anchor='center'))
        def calc_ma(p):
            ma = []
            for i in range(n):
                if i < p - 1: ma.append(None)
                else: ma.append(sum(data[j]['close'] for j in range(i - p + 1, i + 1)) / p)
            return ma
        ma5 = calc_ma(5); ma10 = calc_ma(10); ma20 = calc_ma(20)
        for i, d in enumerate(data):
            cx = x0 + bar_step * (i + 0.5); o, c = d['open'], d['close']; hh, ll = d['high'], d['low']
            oy, cy = p2y(o), p2y(c); hy, ly = p2y(hh), p2y(ll)
            color = C_RED if c > o else C_GREEN if c < o else C_GRAY
            self._add(cv.create_line(cx, hy, cx, ly, fill=color, width=1))
            body_h = max(abs(cy - oy), 1)
            self._add(cv.create_rectangle(cx - bar_w / 2, min(cy, oy), cx + bar_w / 2, max(cy, oy), fill=color, outline=color, width=1))
            if d['volume'] > 0:
                vy = v2y(d['volume'])
                self._add(cv.create_rectangle(cx - bar_w / 2, vy, cx + bar_w / 2, v_y1, fill=color, outline=''))
        def draw_ma(ma, color):
            pts = []
            for i, val in enumerate(ma):
                if val is not None: cx = x0 + bar_step * (i + 0.5); pts.extend([cx, p2y(val)])
            if len(pts) >= 4: self._add(cv.create_line(*pts, fill=color, width=1, smooth=True))
        draw_ma(ma5, C_MA5); draw_ma(ma10, C_MA10); draw_ma(ma20, C_MA20)
        self._add(cv.create_line(x0, last_y, x1, last_y, fill=last_color, width=1, dash=(3, 2)))
        # 现价标签：放在Y轴价格刻度右侧、窗口最右边缘
        price_text = f'{last_c:.0f}'
        tid = cv.create_text(0, 0, text=price_text, fill='#ffffff', font=('Consolas', 11, 'bold'), anchor='w')
        self.win.update_idletasks()
        try:
            bbox = cv.bbox(tid); tw = (bbox[2] - bbox[0]) if bbox else 40
        except Exception:
            tw = 40
        cv.delete(tid)
        lbl_w = tw + 10
        lbl_x1 = self.WIN_W - 4
        lbl_x0 = lbl_x1 - lbl_w
        self._add(cv.create_rectangle(lbl_x0, last_y - 9, lbl_x1, last_y + 9, fill=last_color, outline=''))
        self._add(cv.create_text((lbl_x0 + lbl_x1) / 2, last_y, text=price_text, fill='#ffffff', font=('Consolas', 11, 'bold'), anchor='center'))
        # 日期标签（5个，避免最右侧与数据来源文字重叠）
        label_count = min(5, n)
        is_minute = self.period in ('5', '15', '30', '60')
        for i in range(label_count):
            idx = int(i * (n - 1) / (label_count - 1)) if label_count > 1 else 0
            ds = data[idx]['date']
            try:
                if is_minute:
                    parts = ds.split(' ')
                    if len(parts) == 2: ds = parts[1][:5]
                else:
                    date_part = ds.split(' ')[0]; parts = date_part.split('-')
                    if len(parts) >= 2:
                        year = parts[0][-2:]; month = str(int(parts[1]))
                        day = str(int(parts[2])) if len(parts) >= 3 else ''
                        ds = year + '-' + month + '-' + day if day else year + '-' + month
            except:
                if ' ' in ds: ds = ds[5:10]
                elif len(ds) >= 10: ds = ds[5:10]
            cx = x0 + bar_step * (idx + 0.5)
            # 边界保护：首尾日期用左/右对齐避免溢出，中间居中
            if i == 0:
                anchor = 'nw'; cx = max(x0, 14)
            elif i == label_count - 1:
                anchor = 'ne'; cx = min(x1, self.WIN_W - 14)
            else:
                anchor = 'n'; cx = max(36, min(cx, self.WIN_W - 36))
            self._add(cv.create_text(cx, v_y1 + 18, text=ds, fill=C_FAINT, font=('Consolas', 11), anchor=anchor))
        # MA均线数值（动态间距，避免重叠）
        lx = x0 + 2; ly = self._legend_y
        for text, color in [
            (f'MA5={ma5[-1]:.2f}' if ma5[-1] is not None else 'MA5=--', C_MA5),
            (f'MA10={ma10[-1]:.2f}' if ma10[-1] is not None else 'MA10=--', C_MA10),
            (f'MA20={ma20[-1]:.2f}' if ma20[-1] is not None else 'MA20=--', C_MA20),
        ]:
            tid = self._add(cv.create_text(lx, ly, text=text, fill=color, font=('Consolas', 11), anchor='nw'))
            try:
                bbox = cv.bbox(tid)
                tw = (bbox[2] - bbox[0]) if bbox else 100
            except Exception:
                tw = 100
            lx += tw + 16
        if self._source_name:
            self._add(cv.create_text(self.WIN_W - 8, v_y1 + 38, text=self._source_name, fill=C_FAINT, font=('Microsoft YaHei', 10), anchor='ne'))

    def _add(self, item):
        self._drawn_items.append(item); return item

    def _save_pos(self):
        try:
            x, y = self.win.winfo_x(), self.win.winfo_y()
            with open(os.path.join(_LOG_DIR, 'kline_pos.json'), 'w') as f: json_module.dump({'x': x, 'y': y}, f)
        except Exception: pass

    def _load_pos(self):
        try:
            p = os.path.join(_LOG_DIR, 'kline_pos.json')
            if os.path.exists(p):
                with open(p) as f: d = json_module.load(f); return (d['x'], d['y'])
        except Exception: pass
        sw = self.win.winfo_screenwidth(); sh = self.win.winfo_screenheight()
        return (max(20, (sw - self.WIN_W) // 2), max(20, (sh - self.WIN_H) // 2))

    def _on_close(self):
        self.running = False; self._save_pos()
        try: self.win.destroy()
        except tk.TclError: pass
        if self._on_close_cb: self._on_close_cb(self.code)


# ═══════════════════════════════════════════════════════════
#  估值分析窗口
# ═══════════════════════════════════════════════════════════

def _sma(values, period):
    """简单移动平均"""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period

def _ema(values, period):
    """指数移动平均"""
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
    return ema

def _rsi(closes, period=14):
    """RSI 相对强弱指标"""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(0, diff))
        losses.append(max(0, -diff))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)

def _bollinger(closes, period=20, num_std=2):
    """布林带：返回 (中轨, 上轨, 下轨)"""
    if len(closes) < period:
        return None, None, None
    slice_c = closes[-period:]
    mid = sum(slice_c) / period
    variance = sum((c - mid) ** 2 for c in slice_c) / period
    std = variance ** 0.5
    return mid, mid + num_std * std, mid - num_std * std

def _support_resistance(data, lookback=30):
    """找出近期的支撑位和阻力位"""
    recent = data[-lookback:] if len(data) >= lookback else data
    lows = [d['low'] for d in recent]
    highs = [d['high'] for d in recent]
    # 找近N根K线中的最低点和最高点
    support = min(lows)
    resistance = max(highs)
    # 找次级支撑/阻力
    sorted_lows = sorted(set(lows))
    sorted_highs = sorted(set(highs))
    support2 = sorted_lows[1] if len(sorted_lows) > 1 else support
    resistance2 = sorted_highs[-2] if len(sorted_highs) > 1 else resistance
    return support, support2, resistance2, resistance

def _calc_valuation(code, name, kline_data, current_price):
    """根据K线数据计算估值和买入建议，返回分析结果字典"""
    if not kline_data or len(kline_data) < 5:
        return None

    closes = [d['close'] for d in kline_data]
    highs = [d['high'] for d in kline_data]
    lows = [d['low'] for d in kline_data]
    vols = [d['volume'] for d in kline_data]

    # 均线
    ma5 = _sma(closes, 5)
    ma10 = _sma(closes, 10)
    ma20 = _sma(closes, 20)
    ma60 = _sma(closes, 60) if len(closes) >= 60 else None

    # RSI
    rsi = _rsi(closes, 14)

    # 布林带
    boll_mid, boll_up, boll_low = _bollinger(closes, 20, 2)

    # 支撑/阻力位
    sup1, sup2, res2, res1 = _support_resistance(kline_data, 30)

    # 成交量趋势
    vol_now = vols[-1] if vols else 0
    vol_avg = sum(vols[-20:]) / min(20, len(vols)) if vols else 1
    vol_ratio = vol_now / vol_avg if vol_avg else 1

    # 近期涨跌幅
    chg_5d = ((closes[-1] - closes[-6]) / closes[-6] * 100) if len(closes) >= 6 else 0
    chg_20d = ((closes[-1] - closes[-21]) / closes[-21] * 100) if len(closes) >= 21 else 0

    # 均线排列方向
    if ma5 and ma10 and ma20:
        if ma5 > ma10 > ma20:
            ma_trend = '多头排列（上涨趋势）'
            ma_signal = '看多'
        elif ma5 < ma10 < ma20:
            ma_trend = '空头排列（下跌趋势）'
            ma_signal = '看空'
        else:
            ma_trend = '均线交织（震荡）'
            ma_signal = '中性'
    else:
        ma_trend = '数据不足'
        ma_signal = '中性'

    # RSI判断
    if rsi is not None:
        if rsi > 70:
            rsi_desc = '超买区域（偏高）'
            rsi_signal = '看空'
        elif rsi < 30:
            rsi_desc = '超卖区域（偏低）'
            rsi_signal = '看多'
        elif rsi > 55:
            rsi_desc = '偏强'
            rsi_signal = '偏多'
        elif rsi < 45:
            rsi_desc = '偏弱'
            rsi_signal = '偏空'
        else:
            rsi_desc = '中性'
            rsi_signal = '中性'
    else:
        rsi_desc = '数据不足'
        rsi_signal = '中性'

    # 布林带位置
    if boll_mid and boll_up and boll_low:
        if current_price >= boll_up:
            boll_desc = '触及上轨（偏高）'
            boll_signal = '看空'
        elif current_price <= boll_low:
            boll_desc = '触及下轨（偏低）'
            boll_signal = '看多'
        elif current_price > boll_mid:
            boll_desc = '中上轨之间（偏强）'
            boll_signal = '偏多'
        else:
            boll_desc = '中下轨之间（偏弱）'
            boll_signal = '偏空'
    else:
        boll_desc = '数据不足'
        boll_signal = '中性'

    # 成交量
    if vol_ratio > 1.5:
        vol_desc = f'放量（{vol_ratio:.1f}倍均量）'
        vol_signal = '关注'
    elif vol_ratio < 0.5:
        vol_desc = f'缩量（{vol_ratio:.1f}倍均量）'
        vol_signal = '观望'
    else:
        vol_desc = f'正常（{vol_ratio:.1f}倍均量）'
        vol_signal = '中性'

    # 综合评分
    score = 0
    signals = [ma_signal, rsi_signal, boll_signal, vol_signal]
    for s in signals:
        if '看多' in s or s == '偏多':
            score += 2
        elif '看空' in s or s == '偏空':
            score -= 2
        elif s == '关注':
            score += 1
        elif s == '观望':
            score -= 1
    # 近期趋势加成
    if chg_5d > 3:
        score += 1
    elif chg_5d < -3:
        score -= 1
    if chg_20d > 5:
        score += 1
    elif chg_20d < -5:
        score -= 1

    # 买入建议
    if score >= 4:
        advice = '建议买入'
        advice_color = C_RED  # 红色=涨/买入
    elif score >= 2:
        advice = '可逢低买入'
        advice_color = C_RED
    elif score >= -1:
        advice = '观望为主'
        advice_color = C_DIM
    elif score >= -3:
        advice = '建议减仓'
        advice_color = C_GREEN  # 绿色=跌/卖出
    else:
        advice = '建议离场'
        advice_color = C_GREEN

    return {
        'name': name,
        'code': code,
        'price': current_price,
        'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'ma60': ma60,
        'rsi': rsi, 'rsi_desc': rsi_desc, 'rsi_signal': rsi_signal,
        'boll_mid': boll_mid, 'boll_up': boll_up, 'boll_low': boll_low,
        'boll_desc': boll_desc, 'boll_signal': boll_signal,
        'ma_trend': ma_trend, 'ma_signal': ma_signal,
        'vol_desc': vol_desc, 'vol_signal': vol_signal,
        'sup1': sup1, 'sup2': sup2, 'res2': res2, 'res1': res1,
        'chg_5d': chg_5d, 'chg_20d': chg_20d,
        'score': score, 'advice': advice, 'advice_color': advice_color,
    }


class ValuationWindow:
    """估值分析窗口"""
    WIN_W = 420
    WIN_H = 560

    def __init__(self, parent_root, code, name, on_close_cb=None, latest_quote=None):
        self.code = code
        self.name = name
        self.running = True
        self._drag = None
        self._on_close_cb = on_close_cb
        self._latest_quote = latest_quote
        self.analysis = None

        self.win = tk.Toplevel(parent_root)
        self.win.overrideredirect(True)
        self.win.attributes('-topmost', True)
        self.win.configure(bg=C_K_B)
        pos = self._load_pos()
        self.win.geometry(f'{self.WIN_W}x{self.WIN_H}+{pos[0]}+{pos[1]}')

        self._build_ui()
        self._fetch_and_analyze()

        # 拖拽
        self.win.bind('<Button-1>', self._on_click)
        self.win.bind('<B1-Motion>', self._on_drag)
        self.win.bind('<ButtonRelease-1>', self._on_release)
        self.win.bind('<Button-3>', self._on_close)
        self.win.bind('<Escape>', lambda e: self._on_close())

    def _load_pos(self):
        import os
        p = os.path.join(_LOG_DIR, 'val_pos.json')
        try:
            if os.path.exists(p):
                with open(p) as f:
                    d = json_module.load(f)
                    return (d['x'], d['y'])
        except Exception:
            pass
        sw = self.win.winfo_screenwidth()
        return (max(50, (sw - self.WIN_W) // 2), 100)

    def _save_pos(self):
        try:
            x, y = self.win.winfo_x(), self.win.winfo_y()
            with open(os.path.join(_LOG_DIR, 'val_pos.json'), 'w') as f:
                json_module.dump({'x': x, 'y': y}, f)
        except Exception:
            pass

    def _build_ui(self):
        cv = tk.Canvas(self.win, width=self.WIN_W, height=self.WIN_H,
                       bg=C_K_B, highlightthickness=0)
        cv.pack(fill='both', expand=True)
        self.cv = cv

        # 渐变背景
        from PIL import Image as _Img, ImageDraw as _IDraw
        img = _Img.new('RGB', (self.WIN_W, self.WIN_H), (255, 255, 255))
        d = _IDraw.Draw(img)
        for y in range(self.WIN_H):
            t = y / max(1, self.WIN_H - 1)
            r1, g1, b1 = 255, 255, 255
            r2, g2, b2 = 244, 246, 249
            r, g, b = int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t)
            d.line([(0, y), (self.WIN_W-1, y)], fill=(r, g, b))
        self._bg = ImageTk.PhotoImage(img)
        cv.create_image(0, 0, image=self._bg, anchor='nw')

        # 标题栏
        cv.create_rectangle(0, 0, self.WIN_W, 44, fill='#1e293b', outline='')
        cv.create_text(20, 22, text=f'\U0001F4CA {self.name} 估值分析',
                       fill='#ffffff', font=('Microsoft YaHei', 14, 'bold'), anchor='w')
        # 关闭按钮
        cv.create_text(self.WIN_W - 20, 22, text='\u2715', fill='#ef4444',
                       font=('Segoe UI', 13, 'bold'), anchor='center', tags='close')
        # 拖拽提示
        cv.create_text(self.WIN_W - 50, 22, text='拖拽移动', fill='#64748b',
                       font=('Microsoft YaHei', 8), anchor='center')

        # 状态文字
        self._status = cv.create_text(self.WIN_W // 2, 220, text='正在获取数据...',
                                      fill=C_GOLD, font=('Microsoft YaHei', 13), anchor='center')

    def _fetch_and_analyze(self):
        def worker():
            try:
                data, src = fetch_kline_data(self.code, '101', 90)
            except Exception as e:
                _log(f'Valuation fetch exception ({self.code}): {e}')
                data, src = None, None
            if self.running:
                self.win.after(0, lambda d=data: self._on_data(d))
        threading.Thread(target=worker, daemon=True).start()

    def _on_data(self, kline_data):
        if not self.running:
            return
        current_price = None
        if self._latest_quote and self._latest_quote.get('price'):
            current_price = self._latest_quote['price']
        if not current_price and kline_data:
            current_price = kline_data[-1]['close']
        if not current_price:
            self.cv.itemconfig(self._status, text='数据获取失败', fill=C_RED)
            return

        self.analysis = _calc_valuation(self.code, self.name, kline_data, current_price)
        if self.analysis:
            self._draw_analysis()
        else:
            self.cv.itemconfig(self._status, text='K线数据不足，无法分析', fill=C_RED)

    def _draw_analysis(self):
        cv = self.cv
        a = self.analysis
        # 清除加载文字
        cv.itemconfig(self._status, text='')

        y = 56
        # 当前价格
        cv.create_text(20, y, text=f'当前价格: {a["price"]}',
                       fill=C_TEXT, font=('Consolas', 16, 'bold'), anchor='nw', tags='info')
        y += 30

        # 近期涨跌
        c5_color = C_RED if a['chg_5d'] > 0 else C_GREEN if a['chg_5d'] < 0 else C_DIM
        c20_color = C_RED if a['chg_20d'] > 0 else C_GREEN if a['chg_20d'] < 0 else C_DIM
        cv.create_text(20, y,
                       text=f'近5日 {a["chg_5d"]:+.2f}%   近20日 {a["chg_20d"]:+.2f}%',
                       fill=c5_color, font=('Consolas', 11), anchor='nw', tags='info')
        y += 28

        # 分隔线
        cv.create_line(20, y, self.WIN_W - 20, y, fill=C_BORDER, width=1, tags='info')
        y += 12

        # 均线
        def fmt_ma(val):
            return f'{val:.2f}' if val else '--'
        cv.create_text(20, y, text='均线MA',
                       fill=C_TEXT, font=('Microsoft YaHei', 11, 'bold'), anchor='nw', tags='info')
        y += 22
        ma_text1 = f'MA5: {fmt_ma(a["ma5"])}   MA10: {fmt_ma(a["ma10"])}'
        ma_text2 = f'MA20: {fmt_ma(a["ma20"])}   MA60: {fmt_ma(a["ma60"])}'
        cv.create_text(20, y, text=ma_text1,
                       fill=C_DIM, font=('Consolas', 10), anchor='nw', tags='info')
        y += 18
        cv.create_text(20, y, text=ma_text2,
                       fill=C_DIM, font=('Consolas', 10), anchor='nw', tags='info')
        y += 20
        trend_color = C_RED if '多' in a['ma_signal'] else C_GREEN if '空' in a['ma_signal'] else C_DIM
        cv.create_text(20, y, text=f'排列: {a["ma_trend"]}',
                       fill=trend_color, font=('Microsoft YaHei', 10), anchor='nw', tags='info')
        y += 26

        # RSI
        cv.create_line(20, y, self.WIN_W - 20, y, fill=C_BORDER, width=1, tags='info')
        y += 10
        rsi_val = f'{a["rsi"]:.1f}' if a['rsi'] is not None else '--'
        rsi_color = C_GREEN if a['rsi_signal'] == '看多' else C_RED if a['rsi_signal'] == '看空' else C_DIM
        cv.create_text(20, y, text=f'RSI(14): {rsi_val}  —  {a["rsi_desc"]}',
                       fill=rsi_color, font=('Microsoft YaHei', 11), anchor='nw', tags='info')
        y += 26

        # 布林带
        cv.create_line(20, y, self.WIN_W - 20, y, fill=C_BORDER, width=1, tags='info')
        y += 10
        if a['boll_mid']:
            boll_text1 = f'布林带: 上轨 {a["boll_up"]:.2f}  中轨 {a["boll_mid"]:.2f}'
            boll_text2 = f'  下轨 {a["boll_low"]:.2f}'
        else:
            boll_text1 = '布林带: 数据不足'
            boll_text2 = ''
        cv.create_text(20, y, text=boll_text1,
                       fill=C_DIM, font=('Consolas', 10), anchor='nw', tags='info')
        y += 18
        if boll_text2:
            cv.create_text(20, y, text=boll_text2,
                           fill=C_DIM, font=('Consolas', 10), anchor='nw', tags='info')
            y += 16
        boll_color = C_GREEN if '看多' in a['boll_signal'] else C_RED if '看空' in a['boll_signal'] else C_DIM
        cv.create_text(20, y, text=f'位置: {a["boll_desc"]}',
                       fill=boll_color, font=('Microsoft YaHei', 10), anchor='nw', tags='info')
        y += 24

        # 成交量
        cv.create_line(20, y, self.WIN_W - 20, y, fill=C_BORDER, width=1, tags='info')
        y += 10
        cv.create_text(20, y, text=f'成交量: {a["vol_desc"]}',
                       fill=C_DIM, font=('Microsoft YaHei', 11), anchor='nw', tags='info')
        y += 26

        # 支撑/阻力位
        cv.create_line(20, y, self.WIN_W - 20, y, fill=C_BORDER, width=1, tags='info')
        y += 10
        cv.create_text(20, y, text='关键价位',
                       fill=C_TEXT, font=('Microsoft YaHei', 11, 'bold'), anchor='nw', tags='info')
        y += 22
        cv.create_text(20, y,
                       text=f'  阻力位: {a["res1"]:.2f} / {a["res2"]:.2f}',
                       fill=C_RED, font=('Consolas', 10), anchor='nw', tags='info')
        y += 18
        cv.create_text(20, y,
                       text=f'  支撑位: {a["sup1"]:.2f} / {a["sup2"]:.2f}',
                       fill=C_GREEN, font=('Consolas', 10), anchor='nw', tags='info')
        y += 26

        # 综合评分 + 买入建议
        cv.create_line(20, y, self.WIN_W - 20, y, fill=C_BORDER, width=1, tags='info')
        y += 14
        score_text = f'综合评分: {a["score"]:+d}'
        cv.create_text(20, y, text=score_text,
                       fill=C_TEXT, font=('Microsoft YaHei', 12, 'bold'), anchor='nw', tags='info')
        y += 28

        # 建议框
        advice_y = y
        cv.create_rectangle(20, advice_y, self.WIN_W - 20, advice_y + 50,
                            fill=a['advice_color'], outline='', tags='info')
        cv.create_text(self.WIN_W // 2, advice_y + 25,
                       text=a['advice'],
                       fill='#ffffff', font=('Microsoft YaHei', 18, 'bold'), anchor='center', tags='info')
        y += 62

        # 免责声明
        cv.create_text(20, y,
                       text='* 以上分析基于技术指标，仅供参考，不构成投资建议',
                       fill=C_FAINT, font=('Microsoft YaHei', 8), anchor='nw', tags='info')

    def _on_click(self, event):
        # 关闭按钮
        cx, cy = event.x, event.y
        if self.WIN_W - 35 <= cx <= self.WIN_W - 5 and 5 <= cy <= 40:
            self._on_close()
            return
        self._drag = (event.x_root - self.win.winfo_x(), event.y_root - self.win.winfo_y())

    def _on_drag(self, event):
        if not self._drag:
            return
        x = event.x_root - self._drag[0]
        y = max(0, event.y_root - self._drag[1])
        self.win.geometry(f'+{x}+{y}')

    def _on_release(self, event):
        self._drag = None
        self._save_pos()

    def _on_close(self, event=None):
        self.running = False
        self._save_pos()
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        if self._on_close_cb:
            self._on_close_cb(self.code)


# ═══════════════════════════════════════════════════════════
#  主窗口
# ═══════════════════════════════════════════════════════════

class FinanceWidget:
    W = 780; H = 348; MINI_W = 54; MINI_H = 54; ROW_H = 42

    SORT_MODES = ['默认', '涨幅', '价格', '自定义']
    SORT_LABELS = {'默认': '\u2630', '涨幅': '\u2191\u2193', '价格': '\u00A4', '自定义': '\u270E'}

    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True); self.root.attributes('-topmost', True)
        self.root.wm_attributes('-transparentcolor', C_TRANS); self.root.configure(bg=C_TRANS)
        self.cards = {}; self.card_regions = {}; self.running = True; self.is_mini = False
        self.topmost = True; self._drag = None; self._flash = {};         self.kline_windows = {}; self._fail_count = 0
        self.valuation_windows = {}
        self._hover_code = None
        self._btn_items = {}
        self._sort_rects = []
        self._drag_start = None
        self._sort_idx = 0  # 0=默认, 1=涨幅, 2=价格
        self._sorted_codes = []  # 当前显示顺序（空=尚未布局）
        self._latest_items = []  # 最近一次行情数据
        self._refresh_ms = self._load_refresh_freq()  # 当前刷新频率（毫秒，持久化）
        self._refreshing = False  # 是否正在刷新中（用于状态栏视觉反馈）
        pos = self._load_pos()
        self._build_full(); self._build_mini(); self._show_full()
        self.root.geometry(f'+{pos[0]}+{pos[1]}')
        self.root.bind('<Button-1>', self._on_click)
        self.root.bind('<B1-Motion>', self._on_drag)
        self.root.bind('<ButtonRelease-1>', self._on_release)
        self.root.bind('<Double-Button-1>', self._on_double_click)
        self.root.bind('<Motion>', self._on_motion)
        self.root.bind('<Button-3>', self._show_menu)
        self.root.bind('<Escape>', lambda e: self._on_close())
        self._start_refresh()

    def _get_fmt(self, code):
        """获取品种的分类格式"""
        for c, _, fmt in INSTRUMENTS:
            if c == code: return fmt
        return 's'

    @staticmethod
    def _fit_name(name, max_chars=4):
        """截断超长品种名，超出 max_chars 个字用省略号"""
        if len(name) > max_chars:
            return name[:max_chars] + '…'
        return name

    def _get_name(self, code):
        """获取品种的显示名称"""
        for c, n, _ in INSTRUMENTS:
            if c == code: return n
        return code

    def _build_full(self):
        self.full_cv = tk.Canvas(self.root, width=self.W, height=self.H, bg=C_TRANS, highlightthickness=0)
        # 4x超采样生成精确圆角mask，缩小时用阈值过滤消除黑边
        from PIL import Image as _Img, ImageDraw as _IDraw
        bg_r = 20
        SCALE = 4
        sw, sh = self.W * SCALE, self.H * SCALE
        # 高分辨率mask
        hi_mask = _Img.new('L', (sw, sh), 0)
        hmd = _IDraw.Draw(hi_mask)
        hmd.rounded_rectangle([0, 0, sw - 1, sh - 1], radius=bg_r * SCALE, fill=255)
        # 缩小到原尺寸，用阈值二值化
        mask = hi_mask.resize((self.W, self.H), _Img.LANCZOS)
        # 阈值化：>128 的保留，其余设为透明色
        mask = mask.point(lambda v: 255 if v > 128 else 0, 'L')
        # 渐变背景图（RGB）
        trans_rgb = (0, 0, 0)  # #000000 = C_TRANS
        bg_img = _Img.new('RGB', (self.W, self.H), trans_rgb)
        bgd = _IDraw.Draw(bg_img)
        for y in range(self.H):
            t = y / max(1, self.H - 1)
            r1,g1,b1 = int(C_PANEL_T[1:3],16),int(C_PANEL_T[3:5],16),int(C_PANEL_T[5:7],16)
            r2,g2,b2 = int(C_PANEL_B[1:3],16),int(C_PANEL_B[3:5],16),int(C_PANEL_B[5:7],16)
            r,g,b = int(r1+(r2-r1)*t),int(g1+(g2-g1)*t),int(b1+(b2-b1)*t)
            bgd.line([(0, y), (self.W - 1, y)], fill=(r,g,b))
        final_bg = _Img.new('RGB', (self.W, self.H), trans_rgb)
        final_bg.paste(bg_img, (0, 0), mask)
        self._bg_full = ImageTk.PhotoImage(final_bg)
        self.full_cv.create_image(0, 0, image=self._bg_full, anchor='nw', tags='bg')
        # 标题行
        self.full_cv.create_text(20, 12, text='全球行情', fill=C_TEXT, font=('Microsoft YaHei', 14, 'bold'), anchor='nw')
        # 排序按钮（4个，做成按钮样式）
        self._sort_btns = []
        self._sort_rects = []
        sort_cfgs = [
            ('默认', 155),
            ('涨幅', 231),
            ('价格', 307),
            ('自定义', 383),
        ]
        bw_list = [70, 70, 70, 82]
        for i, (label, bx) in enumerate(sort_cfgs):
            bw = bw_list[i]
            rect = self.full_cv.create_rectangle(
                bx, 8, bx + bw, 34,
                fill=C_BTN_BG if i != 0 else C_BTN_ACTIVE_BG,
                outline=C_BORDER if i != 0 else C_BTN_ACTIVE_BORDER,
                width=1, tags=f'sort_{i}')
            tid = self.full_cv.create_text(
                bx + bw / 2, 21, text=label,
                fill=C_GOLD if i == 0 else C_DIM,
                font=('Microsoft YaHei', 11), anchor='center', tags=f'sort_{i}')
            self._sort_btns.append(tid)
            self._sort_rects.append(rect)
        # 右上角按钮区域 — 缩小 + 关闭
        self.full_cv.create_oval(
            self.W - 91, 6, self.W - 56, 41,
            fill='', outline='', tags='colbtn')
        self.full_cv.create_text(self.W - 73, 23, text='─', fill=C_DIM, font=('Segoe UI', 16, 'bold'), anchor='center', tags='colbtn')
        self.full_cv.create_oval(
            self.W - 48, 6, self.W - 13, 41,
            fill='', outline='', tags='closebtn')
        self.full_cv.create_text(self.W - 30, 23, text='✕', fill='#ef4444', font=('Segoe UI', 14, 'bold'), anchor='center', tags='closebtn')
        self._status_full = self.full_cv.create_text(self.W - 109, 23, text='', fill=C_GREEN, font=('Microsoft YaHei', 10), anchor='ne')
        # 分割线
        self.full_cv.create_line(20, 42, self.W - 20, 42, fill=C_BORDER, width=1)
        # 左右分栏中线
        mid_x = self.W // 2
        self.full_cv.create_line(mid_x, 46, mid_x, self.H - 20, fill=C_BORDER, width=1, dash=(2, 4))
        # 品种卡片 — 动态创建所有12个位置（按列分配：左列6行+右列6行）
        self._slot_codes = []  # 各slot对应的code
        self._slot_positions = []  # 各slot的(x0, y)坐标
        mid_x = self.W // 2
        for i in range(12):
            col = i // 6  # 0=左列, 1=右列
            row = i % 6   # 行号0-5
            x0 = 20 if col == 0 else mid_x + 8
            y = 48 + row * self.ROW_H
            default_code = INSTRUMENTS[i][0] if i < len(INSTRUMENTS) else None
            self._slot_codes.append(default_code)
            self._slot_positions.append((x0, y))
        self._create_card_items()

    def _create_card_items(self):
        """为每个slot创建canvas item（仅在初始化时调用一次）"""
        self._card_slots = []  # 每个slot: {rect, arrow, name, price, change, btn_w, x0, y}
        for i in range(12):
            pos = self._slot_positions[i]
            if pos is None:
                self._card_slots.append(None); continue
            x0, y = pos
            code = self._slot_codes[i]
            if code is None:
                self._card_slots.append(None); continue
            fmt = self._get_fmt(code)
            name = self._get_name(code)
            cat = CAT_COLORS.get(fmt, CAT_COLORS['s'])
            icon = CAT_ICONS.get(fmt, '\u25B8')
            btn_w = 110   # 名称按钮宽度（图标8+名称≤96+内边距）
            btn_h = 32    # 按钮高度
            yc = y + 2 + btn_h // 2  # 垂直中心
            col_end = (self.W // 2) - 10 if x0 < self.W // 2 else self.W - 14
            # 按钮背景
            btn_rect = self.full_cv.create_rectangle(
                x0, y + 2, x0 + btn_w, y + 2 + btn_h,
                fill=cat[0], outline=cat[1], width=1, tags=f'btn_{i}')
            # 图标
            btn_arrow = self.full_cv.create_text(
                x0 + 8, yc, text=icon, fill=cat[2],
                font=('Segoe UI', 11), anchor='w', tags=f'btn_{i}')
            # 名称（自动截断超长名称）
            display_name = self._fit_name(name)
            name_item = self.full_cv.create_text(
                x0 + 24, yc, text=display_name, fill=cat[3],
                font=('Microsoft YaHei', 12, 'bold'), anchor='w', tags=f'btn_{i}')
            # 涨幅（右对齐到列尾）
            change_item = self.full_cv.create_text(
                col_end, yc, text='--', fill=C_GRAY,
                font=('Consolas', 13), anchor='e')
            # 价格（右对齐到涨幅左侧，留间隙10px）
            price_item = self.full_cv.create_text(
                col_end - 104, yc, text='--', fill=C_TEXT,
                font=('Consolas', 13, 'bold'), anchor='e')
            slot = {
                'rect': btn_rect, 'arrow': btn_arrow, 'name': name_item,
                'price': price_item, 'change': change_item,
                'btn_w': btn_w, 'x0': x0, 'y': y,
            }
            self._card_slots.append(slot)
            self.card_regions[code] = (x0, y + 2, x0 + btn_w, y + 2 + btn_h)
            self._btn_items[code] = {'rect': btn_rect, 'arrow': btn_arrow, 'name': name_item}
            self.cards[code] = {'price': price_item, 'change': change_item, 'prev': None}
        # 底部提示
        self.full_cv.create_text(self.W // 2, self.H - 8, text='点击名称看K线  \u00B7  右键菜单  \u00B7  双击收起', fill=C_FAINT, font=('Microsoft YaHei', 11), anchor='center')

    def _apply_sort(self, items):
        """根据当前排序模式对品种重新排列，返回按列排序的code列表（左列6+右列6）"""
        if self._sort_idx == 0:  # 默认
            return [item[0] for item in INSTRUMENTS]
        elif self._sort_idx == 1:  # 按涨幅
            price_map = {it['code']: it['changePct'] for it in items}
            return sorted([c for c, _, _ in INSTRUMENTS],
                          key=lambda c: price_map.get(c, 0), reverse=True)
        elif self._sort_idx == 2:  # 按价格
            price_map = {it['code']: it['price'] for it in items}
            return sorted([c for c, _, _ in INSTRUMENTS],
                          key=lambda c: price_map.get(c, 0), reverse=True)
        elif self._sort_idx == 3:  # 自定义
            custom = self._load_custom_sort()
            if custom:
                return custom
            return [item[0] for item in INSTRUMENTS]
        return [item[0] for item in INSTRUMENTS]

    def _custom_sort_path(self):
        return os.path.join(_LOG_DIR, 'custom_sort.json')

    def _load_custom_sort(self):
        """加载自定义排序"""
        path = self._custom_sort_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json_module.load(f)
                    return data.get('order', [])
            except Exception:
                return []
        return []

    def _save_custom_sort(self, order):
        """保存自定义排序"""
        path = self._custom_sort_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json_module.dump({'order': order}, f, ensure_ascii=False)
        except Exception:
            pass

    def _apply_sort_column(self, items):
        """按列纵向填充：第1名→左列第1行，第2名→左列第2行...第7名→右列第1行..."""
        sorted_codes = self._apply_sort(items)
        # 直接按顺序填入：[0-5]左列从上到下，[6-11]右列从上到下
        result = [None] * 12
        for idx, code in enumerate(sorted_codes[:12]):
            result[idx] = code
        return result

    def _refresh_layout(self, sorted_codes):
        """根据排序后的code列表刷新卡片内容（sorted_codes已是按列排列的12元素列表）"""
        # 转成简单的顺序列表供 _update_mini_from_sort 等使用
        self._sorted_codes = [c for c in sorted_codes if c]
        # 重新分配每个slot的code
        new_slot_codes = []
        for i in range(12):
            if i < len(sorted_codes):
                new_slot_codes.append(sorted_codes[i])
            else:
                new_slot_codes.append(None)
        # 更新每个slot的显示
        old_codes_set = set(self.cards.keys())
        self.card_regions.clear()
        self._btn_items.clear()
        self.cards.clear()
        for i in range(12):
            slot = self._card_slots[i] if i < len(self._card_slots) else None
            if slot is None: continue
            code = new_slot_codes[i]
            if code is None:
                # 隐藏空slot
                self.full_cv.itemconfig(slot['rect'], state='hidden')
                self.full_cv.itemconfig(slot['arrow'], state='hidden')
                self.full_cv.itemconfig(slot['name'], state='hidden')
                self.full_cv.itemconfig(slot['price'], state='hidden')
                self.full_cv.itemconfig(slot['change'], state='hidden')
                continue
            # 显示slot
            self.full_cv.itemconfig(slot['rect'], state='normal')
            self.full_cv.itemconfig(slot['arrow'], state='normal')
            self.full_cv.itemconfig(slot['name'], state='normal')
            self.full_cv.itemconfig(slot['price'], state='normal')
            self.full_cv.itemconfig(slot['change'], state='normal')
            # 更新样式
            fmt = self._get_fmt(code)
            name = self._get_name(code)
            cat = CAT_COLORS.get(fmt, CAT_COLORS['s'])
            icon = CAT_ICONS.get(fmt, '\u25B8')
            self.full_cv.itemconfig(slot['rect'], fill=cat[0], outline=cat[1])
            self.full_cv.itemconfig(slot['arrow'], text=icon, fill=cat[2])
            self.full_cv.itemconfig(slot['name'], text=self._fit_name(name), fill=cat[3])
            self.full_cv.itemconfig(slot['price'], text='--', fill=C_TEXT)
            self.full_cv.itemconfig(slot['change'], text='--', fill=C_GRAY)
            # 重建映射
            x0 = slot['x0']; y = slot['y']; btn_w = slot['btn_w']
            self.card_regions[code] = (x0, y + 2, x0 + btn_w, y + 2 + 32)
            self._btn_items[code] = {'rect': slot['rect'], 'arrow': slot['arrow'], 'name': slot['name']}
            self.cards[code] = {'price': slot['price'], 'change': slot['change'], 'prev': None}
        # 更新mini窗口显示排序首位
        self._update_mini_from_sort(self._sorted_codes)

    def _update_mini_from_sort(self, sorted_codes):
        """mini窗口显示排序首位的品种"""
        if not sorted_codes: return
        top_code = sorted_codes[0]
        self._mini_top_code = top_code
        top_item = next((it for it in self._latest_items if it['code'] == top_code), None)
        if top_item:
            # 左半圆：品种专用图标
            icon = MINI_ICONS.get(top_code, '\u25C8')
            fmt = self._get_fmt(top_code)
            cat_color = CAT_COLORS.get(fmt, CAT_COLORS['s'])
            self._mini_icon_color = cat_color[2]
            self.mini_cv.itemconfig(self._mini_icon, text=icon)
            # 右半圆：涨跌幅数字+动态背景色
            chg = top_item['changePct']; change = top_item['change']
            if change > 0: bg = C_RED
            elif change < 0: bg = C_GREEN
            else: bg = C_GRAY
            self._mini_q2_color = bg
            self._redraw_mini_sectors()
            # 只显示数字（取绝对值），限制长度适应小窗
            num = abs(chg)
            if num >= 10:
                text = f'{num:.0f}'
            else:
                text = f'{num:.1f}'
            self.mini_cv.itemconfig(self._mini_change, text=text)

    def _redraw_mini_sectors(self):
        """重画mini左右半圆背景图（4x超采样mask消除边缘黑边）"""
        from PIL import Image as _Img, ImageDraw as _IDraw
        d = self.MINI_W
        cx = d // 2
        trans_rgb = (0, 0, 0)  # #000000 = C_TRANS
        SCALE = 4
        sd = d * SCALE
        # 高分辨率渲染
        hi = _Img.new('RGB', (sd, sd), trans_rgb)
        hd = _IDraw.Draw(hi)
        bbox = [0, 0, sd - 1, sd - 1]
        # 左半圆
        left_color = getattr(self, '_mini_icon_color', C_ACCENT)
        hd.pieslice(bbox, 90, 270, fill=left_color, outline=None)
        # 右半圆
        hd.pieslice(bbox, 270, 90, fill=self._mini_q2_color, outline=None)
        # 分割线
        hd.line([(sd // 2, 0), (sd // 2, sd - 1)], fill='#ffffff', width=SCALE)
        # 用圆形mask缩小+阈值化，消除圆外残余黑边
        hi_mask = _Img.new('L', (sd, sd), 0)
        hmd = _IDraw.Draw(hi_mask)
        hmd.ellipse(bbox, fill=255)
        mask = hi_mask.resize((d, d), _Img.LANCZOS).point(lambda v: 255 if v > 128 else 0, 'L')
        sector_img = hi.resize((d, d), _Img.LANCZOS)
        # 圆外像素强制设为透明色
        out_img = _Img.new('RGB', (d, d), trans_rgb)
        out_img.paste(sector_img, (0, 0), mask)
        self._mini_sector_img = ImageTk.PhotoImage(out_img)
        self.mini_cv.itemconfig(self._mini_sector_img_id, image=self._mini_sector_img)

    def _on_sort_click(self, event):
        """点击排序按钮"""
        if not self.is_mini:
            sort_xs = [155, 231, 307, 383]
            bw_list = [70, 70, 70, 82]
            for i, sx in enumerate(sort_xs):
                if sx <= event.x <= sx + bw_list[i] and 8 <= event.y <= 34:
                    self._select_sort(i)
                    return True
        return False

    def _select_sort(self, idx):
        """选择排序模式（idx=3 自定义时弹出编辑窗口）"""
        if idx == 3:
            self._open_custom_sort_dialog()
            return
        self._sort_idx = idx
        for j in range(len(self._sort_btns)):
            self.full_cv.itemconfig(self._sort_btns[j], fill=C_GOLD if j == idx else C_DIM)
            if self._sort_rects:
                self.full_cv.itemconfig(self._sort_rects[j],
                    fill=C_BTN_ACTIVE_BG if j == idx else C_BTN_BG,
                    outline=C_BTN_ACTIVE_BORDER if j == idx else C_BORDER)
        column_codes = self._apply_sort_column(self._latest_items)
        self._refresh_layout(column_codes)
        if self._latest_items:
            self._update_ui(self._latest_items)

    def _open_custom_sort_dialog(self):
        """弹出自定义排序编辑窗口（4列网格，带序号和边框，可点击交换顺序）"""
        win = tk.Toplevel(self.root)
        win.title('自定义排序')
        win.geometry('440x340')
        win.configure(bg='#ffffff')
        win.attributes('-topmost', True)
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)

        # 居中显示
        win.update_idletasks()
        w, h = 440, 340
        sw = win.winfo_screenwidth(); sh = win.winfo_screenheight()
        win.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')

        tk.Label(win, text='点击两个品种交换顺序，序号代表排列优先级',
                 font=('Microsoft YaHei', 10), bg='#ffffff', fg=C_DIM).pack(pady=(12, 10))

        # 当前排序的品种列表
        current_order = self._load_custom_sort()
        all_codes = [c for c, _, _ in INSTRUMENTS]
        if current_order:
            ordered = [c for c in current_order if c in all_codes]
            for c in all_codes:
                if c not in ordered:
                    ordered.append(c)
        else:
            ordered = all_codes[:]

        name_map = {c: n for c, n, _ in INSTRUMENTS}
        # 品种分类颜色
        cat_map = {}
        for c, n, fmt in INSTRUMENTS:
            cat_map[c] = CAT_COLORS.get(fmt, CAT_COLORS['s'])

        COLS = 4
        grid_frame = tk.Frame(win, bg='#ffffff')
        grid_frame.pack(padx=15, pady=(0, 8), fill='both', expand=True)

        # 状态：选中的品种code
        selected = {'code': None}
        # code -> (row, col) 当前网格位置
        code_pos = {}

        cell_labels = {}  # code -> tk.Label widget

        def refresh_grid():
            # 把每个 Label 换到它当前在 ordered 中的位置
            for i, code in enumerate(ordered):
                if code not in cell_labels:
                    continue
                row = i // COLS
                col = i % COLS
                lbl = cell_labels[code]
                cat = cat_map.get(code, CAT_COLORS['s'])
                name = name_map.get(code, code)
                code_pos[code] = (row, col)
                lbl.grid(row=row, column=col, padx=3, pady=3, sticky='nsew')
                if selected['code'] == code:
                    lbl.config(bg=C_BTN_ACTIVE_BORDER, fg='#ffffff',
                               text=f'{i+1}\n{name}')
                else:
                    lbl.config(bg=cat[0], fg=cat[3],
                               text=f'{i+1}\n{name}')

        def on_cell_click(code):
            if selected['code'] is None:
                selected['code'] = code
                refresh_grid()
            elif selected['code'] == code:
                selected['code'] = None
                refresh_grid()
            else:
                # 交换两个品种在 ordered 中的位置
                c1 = selected['code']
                i1 = ordered.index(c1)
                i2 = ordered.index(code)
                ordered[i1], ordered[i2] = ordered[i2], ordered[i1]
                selected['code'] = None
                refresh_grid()

        ROWS = (len(ordered) + COLS - 1) // COLS  # 12品种=3行4列

        for i, code in enumerate(ordered):
            cat = cat_map.get(code, CAT_COLORS['s'])
            lbl = tk.Label(grid_frame, text='', font=('Microsoft YaHei', 11, 'bold'),
                           bg=cat[0], fg=cat[3], borderwidth=1, relief='solid',
                           width=6, height=2, cursor='hand2')
            lbl.bind('<Button-1>', lambda e, c=code: on_cell_click(c))
            cell_labels[code] = lbl

        # 配置列等宽
        for col in range(COLS):
            grid_frame.columnconfigure(col, weight=1)
        for row in range(ROWS):
            grid_frame.rowconfigure(row, weight=1)

        refresh_grid()

        # 确定按钮回调
        def on_confirm():
            self._save_custom_sort(ordered)
            self._sort_idx = 3
            for j in range(len(self._sort_btns)):
                self.full_cv.itemconfig(self._sort_btns[j], fill=C_GOLD if j == 3 else C_DIM)
                if self._sort_rects:
                    self.full_cv.itemconfig(self._sort_rects[j],
                        fill=C_BTN_ACTIVE_BG if j == 3 else C_BTN_BG,
                        outline=C_BTN_ACTIVE_BORDER if j == 3 else C_BORDER)
            column_codes = self._apply_sort_column(self._latest_items)
            self._refresh_layout(column_codes)
            if self._latest_items:
                self._update_ui(self._latest_items)
            win.destroy()

        # 底部按钮
        btn_frame = tk.Frame(win, bg='#ffffff')
        btn_frame.pack(pady=(5, 12))

        def reset_default():
            nonlocal ordered
            ordered = all_codes[:]
            selected['code'] = None
            refresh_grid()

        tk.Button(btn_frame, text='恢复默认', font=('Microsoft YaHei', 11), command=reset_default,
                  bg='#e2e8f0', fg=C_TEXT, borderwidth=0, padx=16, pady=6, cursor='hand2').pack(side='left', padx=8)
        tk.Button(btn_frame, text='确定', font=('Microsoft YaHei', 12, 'bold'), command=on_confirm,
                  bg=C_ACCENT, fg='#ffffff', borderwidth=0, padx=30, pady=6, cursor='hand2').pack(side='left', padx=8)

    def _build_mini(self):
        d = self.MINI_W
        cx = d // 2
        self.mini_cv = tk.Canvas(self.root, width=d, height=d, bg=C_TRANS, highlightthickness=0)
        # 4x超采样渲染圆形背景
        from PIL import Image as _Img, ImageDraw as _IDraw
        trans_rgb = (0, 0, 0)  # #000000 = C_TRANS
        SCALE = 4
        sd = d * SCALE
        hi = _Img.new('RGB', (sd, sd), trans_rgb)
        hd = _IDraw.Draw(hi)
        bbox = [0, 0, sd - 1, sd - 1]
        # 左半圆：品种分类色
        hd.pieslice(bbox, 90, 270, fill=C_ACCENT, outline=None)
        # 右半圆：涨跌幅色（动态）
        hd.pieslice(bbox, 270, 90, fill=C_GRAY, outline=None)
        # 中间分割线
        hd.line([(sd // 2, 0), (sd // 2, sd - 1)], fill='#ffffff', width=SCALE)
        # 圆形mask缩小+阈值化
        hi_mask = _Img.new('L', (sd, sd), 0)
        hmd = _IDraw.Draw(hi_mask)
        hmd.ellipse(bbox, fill=255)
        mask = hi_mask.resize((d, d), _Img.LANCZOS).point(lambda v: 255 if v > 128 else 0, 'L')
        sector_img = hi.resize((d, d), _Img.LANCZOS)
        out_img = _Img.new('RGB', (d, d), trans_rgb)
        out_img.paste(sector_img, (0, 0), mask)
        self._mini_sector_img = ImageTk.PhotoImage(out_img)
        self._mini_sector_img_id = self.mini_cv.create_image(0, 0, image=self._mini_sector_img, anchor='nw')
        # ---- 左半圆：品种图标（单个汉字） ----
        self._mini_icon = self.mini_cv.create_text(
            cx // 2, cx, text='\u91d1', fill='#ffffff',
            font=('Microsoft YaHei', 16, 'bold'), anchor='center', tags='mini_icon')
        # ---- 右半圆：涨跌幅数字（只显示数字，无符号无%） ----
        self._mini_change = self.mini_cv.create_text(
            cx + cx // 2, cx, text='--', fill='#ffffff',
            font=('Consolas', 10, 'bold'), anchor='center', tags='mini_change')
        self._mini_q2_color = C_GRAY

    def _show_full(self):
        self.is_mini = False; self.mini_cv.pack_forget(); self.full_cv.pack(); self.root.geometry(f'{self.W}x{self.H}')
    def _show_mini(self):
        self.is_mini = True; self.full_cv.pack_forget(); self.mini_cv.pack(); self.root.geometry(f'{self.MINI_W}x{self.MINI_H}')
    def _toggle_mode(self, event=None):
        if self.is_mini: self._show_full()
        else: self._show_mini()
        self._save_pos()

    def _update_ui(self, items):
        self._latest_items = items
        self._fail_count = 0
        self._refreshing = False
        freq_label = f'{self._refresh_ms // 1000}s'
        self.full_cv.itemconfig(self._status_full, text=f'{time.strftime("%H:%M:%S")}  \u25CF  {freq_label}', fill=C_GREEN)
        # 排序（仅在排序结果变化时刷新布局）
        sorted_codes = self._apply_sort(items)
        if sorted_codes != self._sorted_codes:
            column_codes = self._apply_sort_column(items)
            self._refresh_layout(column_codes)
        # 更新mini窗口
        self._update_mini_from_sort(sorted_codes)
        # 更新每个品种的数据
        for item in items:
            code = item['code']
            if code not in self.cards: continue
            card = self.cards[code]; price = item['price']; chg = item['change']; pct = item['changePct']
            if chg > 0: color, arrow = C_RED, '\u25B2'
            elif chg < 0: color, arrow = C_GREEN, '\u25BC'
            else: color, arrow = C_GRAY, '\u2500'
            self.full_cv.itemconfig(card['price'], text=f'{price:,.2f}')
            self.full_cv.itemconfig(card['change'], text=f'{arrow} {pct:+.2f}%', fill=color)
            prev = card['prev']
            if prev is not None and abs(prev - price) > 0.001:
                if code in self._flash: self.root.after_cancel(self._flash[code])
                flash_c = C_GOLD if price > prev else C_ACCENT
                self.full_cv.itemconfig(card['price'], fill=flash_c)
                self._flash[code] = self.root.after(800, lambda ci=card['price']: self.full_cv.itemconfig(ci, fill=C_TEXT))
            card['prev'] = price
            if code in self.kline_windows:
                kw = self.kline_windows[code]
                if kw.running: kw._latest_quote = item; kw._update_title_quote(); kw._auto_refresh_kline()

    def _on_fetch_fail(self):
        self._fail_count += 1
        self._refreshing = False
        if self._fail_count >= 2:
            self.full_cv.itemconfig(self._status_full, text=f'\u25CF  \u8FDE\u63A5\u5F02\u5E38  \u00B7  \u91CD\u8BD5\u4E2D... ({self._fail_count})', fill=C_RED)

    def _on_click(self, event):
        if not self.is_mini:
            # 检查排序按钮
            if self._on_sort_click(event): return
            # 缩小按钮
            if self._hit_collapse_btn(event.x, event.y): self._toggle_mode(); return
            # 关闭按钮
            if self._hit_close_btn(event.x, event.y): self._on_close(); return
        if self.is_mini:
            # mini模式：纯展示，点击仅用于拖拽（双击展开）
            pass
        self._drag_start = (event.x, event.y)
        self._drag = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())
        # 按下效果
        if not self.is_mini:
            for code, (rx0, ry0, rx1, ry1) in self.card_regions.items():
                if rx0 <= event.x <= rx1 and ry0 <= event.y <= ry1:
                    btn = self._btn_items.get(code)
                    if btn:
                        fmt = self._get_fmt(code)
                        cat = CAT_COLORS.get(fmt, CAT_COLORS['s'])
                        self.full_cv.itemconfig(btn['rect'], fill=C_BTN_PRESS, outline=cat[2])
                        self.full_cv.itemconfig(btn['arrow'], fill=cat[2])
                    break

    def _hit_collapse_btn(self, x, y):
        """判断是否点中缩小按钮"""
        return self.W - 91 <= x <= self.W - 56 and 6 <= y <= 41

    def _hit_close_btn(self, x, y):
        """判断是否点中关闭按钮"""
        return self.W - 48 <= x <= self.W - 13 and 6 <= y <= 41

    def _hit_mini_expand_btn(self, x, y):
        """mini无展开按钮，双击展开"""
        return False

    def _hit_mini_close_btn(self, x, y):
        """mini无关闭按钮"""
        return False

    def _on_drag(self, event):
        if not self._drag: return
        x = event.x_root - self._drag[0]; y = max(0, event.y_root - self._drag[1])
        sw = self.root.winfo_screenwidth(); sh = self.root.winfo_screenheight() - 40
        w = self.root.winfo_width(); h = self.root.winfo_height()
        self.root.geometry(f'+{max(0,min(x,sw-w))}+{max(0,min(y,sh-h))}')
        self._drag_start = None
    def _on_release(self, event):
        # 恢复按钮外观
        if not self.is_mini:
            for code, btn in self._btn_items.items():
                fmt = self._get_fmt(code)
                cat = CAT_COLORS.get(fmt, CAT_COLORS['s'])
                hover_code = self._get_code_at(event.x, event.y)
                if code == hover_code:
                    self.full_cv.itemconfig(btn['rect'], fill=cat[0], outline=cat[1])
                    self.full_cv.itemconfig(btn['arrow'], fill=cat[2])
                    self.full_cv.itemconfig(btn['name'], fill=cat[3])
                else:
                    self.full_cv.itemconfig(btn['rect'], fill=cat[0], outline=cat[1])
                    self.full_cv.itemconfig(btn['arrow'], fill=cat[2])
                    self.full_cv.itemconfig(btn['name'], fill=cat[3])
        # 判断是否为点击
        if self._drag_start:
            dx = abs(event.x - self._drag_start[0])
            dy = abs(event.y - self._drag_start[1])
            if dx < 5 and dy < 5:
                code = self._get_code_at(event.x, event.y)
                if code:
                    name = self._get_name(code)
                    self._open_kline(code, name)
        self._drag = None; self._drag_start = None; self._save_pos()

    def _get_code_at(self, x, y):
        for code, (rx0, ry0, rx1, ry1) in self.card_regions.items():
            if rx0 <= x <= rx1 and ry0 <= y <= ry1:
                return code
        return None

    def _on_double_click(self, event):
        self._toggle_mode()

    def _on_motion(self, event):
        # 全屏模式下品种按钮悬停
        if not self.is_mini:
            new_hover = self._get_code_at(event.x, event.y)
            if new_hover != self._hover_code:
                if self._hover_code and self._hover_code in self._btn_items:
                    old_btn = self._btn_items[self._hover_code]
                    fmt = self._get_fmt(self._hover_code)
                    cat = CAT_COLORS.get(fmt, CAT_COLORS['s'])
                    self.full_cv.itemconfig(old_btn['rect'], fill=cat[0], outline=cat[1])
                    self.full_cv.itemconfig(old_btn['arrow'], fill=cat[2])
                    self.full_cv.itemconfig(old_btn['name'], fill=cat[3])
                if new_hover and new_hover in self._btn_items:
                    btn = self._btn_items[new_hover]
                    fmt = self._get_fmt(new_hover)
                    cat = CAT_COLORS.get(fmt, CAT_COLORS['s'])
                    # 悬停时稍微亮一点的背景
                    hover_bg = cat[1]  # 用border色做hover背景
                    self.full_cv.itemconfig(btn['rect'], fill=hover_bg, outline=cat[2])
                    self.full_cv.itemconfig(btn['arrow'], fill='#ffffff')
                    self.full_cv.itemconfig(btn['name'], fill='#ffffff')
                self._hover_code = new_hover

    def _show_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0, bg='#ffffff', fg=C_TEXT, activebackground=C_PANEL2, activeforeground=C_TEXT, borderwidth=0, font=('Microsoft YaHei', 10))
        if self.is_mini:
            # mini模式精简菜单：只保留核心功能
            menu.add_command(label='  展开  ', command=self._toggle_mode)
            menu.add_command(label='  立即刷新  ', command=self._force_refresh)
            freq_menu = tk.Menu(menu, tearoff=0, bg='#ffffff', fg=C_TEXT, activebackground=C_PANEL2, activeforeground=C_TEXT, borderwidth=0, font=('Microsoft YaHei', 10))
            for ms, label in [(15000, '15 秒'), (30000, '30 秒'), (60000, '60 秒')]:
                mark = ' \u2713' if self._refresh_ms == ms else ''
                freq_menu.add_command(label=f'  {label}{mark}  ', command=lambda m=ms: self._set_refresh_freq(m))
            menu.add_cascade(label='  刷新频率  \u25B6  ', menu=freq_menu)
            menu.add_command(label='  置顶: 开  ' if self.topmost else '  置顶: 关  ', command=self._toggle_topmost)
            menu.add_separator()
            menu.add_command(label='  退出  ', command=self._on_close)
            menu.tk_popup(event.x_root, event.y_root)
            return
        # 排序子菜单
        sort_menu = tk.Menu(menu, tearoff=0, bg='#ffffff', fg=C_TEXT, activebackground=C_PANEL2, activeforeground=C_TEXT, borderwidth=0, font=('Microsoft YaHei', 10))
        for i, mode in enumerate(self.SORT_MODES):
            mark = ' \u2713' if i == self._sort_idx else ''
            sort_menu.add_command(label=f'  {mode}{mark}  ', command=lambda idx=i: self._menu_sort(idx))
        menu.add_cascade(label='  排序  \u25B6  ', menu=sort_menu)
        menu.add_command(label='  立即刷新  ', command=self._force_refresh)
        # 刷新频率子菜单
        freq_menu = tk.Menu(menu, tearoff=0, bg='#ffffff', fg=C_TEXT, activebackground=C_PANEL2, activeforeground=C_TEXT, borderwidth=0, font=('Microsoft YaHei', 10))
        for ms, label in [(15000, '15 秒'), (30000, '30 秒'), (60000, '60 秒')]:
            mark = ' \u2713' if self._refresh_ms == ms else ''
            freq_menu.add_command(label=f'  {label}{mark}  ', command=lambda m=ms: self._set_refresh_freq(m))
        menu.add_cascade(label='  刷新频率  \u25B6  ', menu=freq_menu)
        menu.add_command(label='  置顶: 开  ' if self.topmost else '  置顶: 关  ', command=self._toggle_topmost)
        menu.add_command(label='  收起  ', command=self._toggle_mode)
        menu.add_separator()
        kline_menu = tk.Menu(menu, tearoff=0, bg='#ffffff', fg=C_TEXT, activebackground=C_PANEL2, activeforeground=C_TEXT, borderwidth=0, font=('Microsoft YaHei', 10))
        for code, name, _ in INSTRUMENTS:
            kline_menu.add_command(label=f'  {name}  ', command=lambda c=code, n=name: self._open_kline(c, n))
        menu.add_cascade(label='  图表 K线  \u25B6  ', menu=kline_menu)
        menu.add_separator()
        val_menu = tk.Menu(menu, tearoff=0, bg='#ffffff', fg=C_TEXT, activebackground=C_PANEL2, activeforeground=C_TEXT, borderwidth=0, font=('Microsoft YaHei', 10))
        for code, name, _ in INSTRUMENTS:
            val_menu.add_command(label=f'  {name}  ', command=lambda c=code, n=name: self._open_valuation(c, n))
        menu.add_cascade(label='  估值分析  \u25B6  ', menu=val_menu)
        menu.add_separator()
        menu.add_command(label='  退出  ', command=self._on_close)
        menu.tk_popup(event.x_root, event.y_root)

    def _menu_sort(self, idx):
        self._select_sort(idx)

    def _set_refresh_freq(self, ms):
        """切换刷新频率并持久化"""
        self._refresh_ms = ms
        self._save_refresh_freq(ms)
        self._force_refresh()

    def _refresh_freq_path(self):
        return os.path.join(_LOG_DIR, 'refresh_freq.json')

    def _load_refresh_freq(self):
        """从文件加载刷新频率，默认30秒"""
        try:
            p = self._refresh_freq_path()
            if os.path.exists(p):
                with open(p) as f:
                    d = json_module.load(f)
                    ms = d.get('ms', 30000)
                    if ms in (15000, 30000, 60000):
                        return ms
        except Exception:
            pass
        return REFRESH_MS

    def _save_refresh_freq(self, ms):
        """保存刷新频率到文件"""
        try:
            with open(self._refresh_freq_path(), 'w') as f:
                json_module.dump({'ms': ms}, f)
        except Exception:
            pass

    def _toggle_topmost(self):
        self.topmost = not self.topmost; self.root.attributes('-topmost', self.topmost)
    def _force_refresh(self):
        if self._refreshing:
            return
        self._refreshing = True
        self.full_cv.itemconfig(self._status_full, text='\u5237\u65B0\u4E2D...', fill=C_ACCENT)
        threading.Thread(target=self._do_fetch, daemon=True).start()
    def _do_fetch(self):
        data = fetch_all_data()
        if data: self.root.after(0, lambda d=data: self._update_ui(d))
        else: self.root.after(0, self._on_fetch_fail)

    def _open_kline(self, code, name):
        if code in self.kline_windows:
            kw = self.kline_windows[code]
            try:
                kw.win.lift(); kw.win.attributes('-topmost', True)
                kw.win.after(100, lambda: kw.win.attributes('-topmost', False)); return
            except tk.TclError: self.kline_windows.pop(code, None)
        def on_kw_close(c=code): self.kline_windows.pop(c, None)
        latest = None
        card = self.cards.get(code)
        if card and card.get('prev') is not None:
            latest = {'price': card['prev'], 'change': 0, 'changePct': 0}
        kw = KLineWindow(self.root, code, name, on_close_cb=on_kw_close, latest_quote=latest)
        self.kline_windows[code] = kw

    def _open_valuation(self, code, name):
        if code in self.valuation_windows:
            vw = self.valuation_windows[code]
            try:
                vw.win.lift(); vw.win.attributes('-topmost', True)
                vw.win.after(100, lambda: vw.win.attributes('-topmost', False)); return
            except tk.TclError:
                self.valuation_windows.pop(code, None)
        def on_vw_close(c=code):
            self.valuation_windows.pop(c, None)
        latest = None
        card = self.cards.get(code)
        if card and card.get('prev') is not None:
            latest = {'price': card['prev'], 'change': 0, 'changePct': 0}
        vw = ValuationWindow(self.root, code, name, on_close_cb=on_vw_close, latest_quote=latest)
        self.valuation_windows[code] = vw

    def _start_refresh(self):
        def worker():
            while self.running:
                data = fetch_all_data()
                if data: self.root.after(0, lambda d=data: self._update_ui(d))
                else: self.root.after(0, self._on_fetch_fail)
                # 失败时缩短等待时间快速重试，成功时按设定频率
                if self._fail_count >= 2:
                    wait_ms = 5000  # 失败后5秒快速重试
                else:
                    wait_ms = self._refresh_ms
                for _ in range(wait_ms // 200):
                    if not self.running: return
                    time.sleep(0.2)
        threading.Thread(target=worker, daemon=True).start()

    def _save_pos(self):
        try:
            x, y = self.root.winfo_x(), self.root.winfo_y()
            with open(os.path.join(_LOG_DIR, 'widget_pos.json'), 'w') as f: json_module.dump({'x': x, 'y': y}, f)
        except Exception: pass
    def _load_pos(self):
        try:
            p = os.path.join(_LOG_DIR, 'widget_pos.json')
            if os.path.exists(p):
                with open(p) as f: d = json_module.load(f); return (d['x'], d['y'])
        except Exception: pass
        return (50, 60)

    def _on_close(self):
        self.running = False; self._save_pos()
        for kw in list(self.kline_windows.values()):
            try: kw._on_close()
            except Exception: pass
        for vw in list(self.valuation_windows.values()):
            try: vw._on_close()
            except Exception: pass
        self.root.destroy()


# ═══════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════

def main():
    _install_excepthook()
    _log('--- Widget starting (standalone, no pyc dependency) ---')
    _log(f'Python: {sys.version}')
    _log(f'CWD: {os.getcwd()}')
    # DPI感知：让tkinter按物理像素渲染，避免缩放导致PIL图片不铺满
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    root = tk.Tk()
    FinanceWidget(root)
    _log('UI built, entering mainloop')
    root.mainloop()
    _log('Widget closed')


if __name__ == '__main__':
    main()
