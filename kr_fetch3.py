# -*- coding: utf-8 -*-
"""알파가드 데이터 수집 v3 — 감사 대상 자산을 대폭 확대한다.

  py -m pip install yfinance pandas
  py kr_fetch3.py

기존 52종에서 국내 대표주 + 주요 ETF + 해외 배수형 상품으로 확대한다.
pykrx(KRX API)는 차단되는 환경이 있어 쓰지 않고, 검증된 고정 목록만 사용한다.
실패한 티커는 건너뛰고 나머지로 파일을 만든다(일부 실패해도 결과물은 나온다).
"""
import json, sys, time
from datetime import datetime

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("먼저 설치가 필요합니다:  py -m pip install yfinance pandas"); sys.exit(1)

START = "2015-01-01"
OUT = "alphaguard_data_v3.json"

# ── 배수형 상품 (기초자산 연결 필수) ────────────────────────────────
PRODUCTS = [
    # (티커, 표시명, 기초자산, 배수)
    ("122630.KS", "KODEX 레버리지",            "069500.KS",  2.0),
    ("123320.KS", "TIGER 레버리지",            "069500.KS",  2.0),
    ("252670.KS", "KODEX 200선물인버스2X",      "069500.KS", -2.0),
    ("114800.KS", "KODEX 인버스",              "069500.KS", -1.0),
    ("233740.KS", "KODEX 코스닥150레버리지",   "229200.KS",  2.0),
    ("251340.KS", "KODEX 코스닥150선물인버스", "229200.KS", -1.0),
    ("TQQQ",      "ProShares UltraPro QQQ (3X)",  "QQQ",  3.0),
    ("SQQQ",      "ProShares UltraPro Short QQQ(-3X)", "QQQ", -3.0),
    ("SOXL",      "Direxion 반도체 3X",        "SOXX",  3.0),
    ("SOXS",      "Direxion 반도체 -3X",       "SOXX", -3.0),
    ("TSLL",      "Direxion 테슬라 2X",        "TSLA",  2.0),
    ("UPRO",      "ProShares UltraPro S&P500 (3X)", "SPY", 3.0),
    ("SPXU",      "ProShares UltraPro Short S&P500(-3X)", "SPY", -3.0),
    ("SSO",       "ProShares Ultra S&P500 (2X)",   "SPY", 2.0),
    ("QLD",       "ProShares Ultra QQQ (2X)",      "QQQ", 2.0),
]

# ── 기초자산·지수·일반 ETF ─────────────────────────────────────────
BASES = [
    ("069500.KS", "KODEX 200",          "국내지수"),
    ("229200.KS", "KODEX 코스닥150",     "국내지수"),
    ("102110.KS", "TIGER 200",          "국내지수"),
    ("133690.KS", "TIGER 미국나스닥100", "해외지수"),
    ("360750.KS", "TIGER 미국S&P500",   "해외지수"),
    ("379800.KS", "KODEX 미국S&P500",   "해외지수"),
    ("381170.KS", "TIGER 미국테크TOP10","해외지수"),
    ("QQQ",  "Invesco QQQ",       "해외지수"),
    ("SPY",  "SPDR S&P500",       "해외지수"),
    ("SOXX", "iShares 반도체",     "해외섹터"),
    ("TSLA", "Tesla",             "해외개별"),
    ("NVDA", "NVIDIA",            "해외개별"),
    ("AAPL", "Apple",             "해외개별"),
    ("MSFT", "Microsoft",         "해외개별"),
    ("^KS11", "KOSPI",            "지수"),
    ("^KQ11", "KOSDAQ",           "지수"),
]

# ── 국내 개별 종목 (업종별) ────────────────────────────────────────
STOCKS = """
005930.KS 삼성전자 반도체
000660.KS SK하이닉스 반도체
042700.KS 한미반도체 반도체
009150.KS 삼성전기 반도체
403870.KS HPSP 반도체
058470.KQ 리노공업 반도체
039030.KQ 이오테크닉스 반도체
036930.KQ 주성엔지니어링 반도체
240810.KQ 원익IPS 반도체
000990.KS DB하이텍 반도체
373220.KS LG에너지솔루션 2차전지
006400.KS 삼성SDI 2차전지
051910.KS LG화학 2차전지
247540.KQ 에코프로비엠 2차전지
086520.KQ 에코프로 2차전지
003670.KS 포스코퓨처엠 2차전지
066970.KQ 엘앤에프 2차전지
207940.KS 삼성바이오로직스 바이오
068270.KS 셀트리온 바이오
196170.KQ 알테오젠 바이오
000100.KS 유한양행 바이오
128940.KS 한미약품 바이오
302440.KS SK바이오사이언스 바이오
005380.KS 현대차 자동차
000270.KS 기아 자동차
012330.KS 현대모비스 자동차
204320.KS HL만도 자동차
011210.KS 현대위아 자동차
105560.KS KB금융 금융
055550.KS 신한지주 금융
086790.KS 하나금융지주 금융
316140.KS 우리금융지주 금융
024110.KS 기업은행 금융
032830.KS 삼성생명 금융
000810.KS 삼성화재 금융
005830.KS DB손해보험 금융
323410.KS 카카오뱅크 금융
035420.KS NAVER 인터넷
035720.KS 카카오 인터넷
259960.KS 크래프톤 인터넷
036570.KS 엔씨소프트 인터넷
251270.KS 넷마블 인터넷
263750.KQ 펄어비스 인터넷
112040.KQ 위메이드 인터넷
377300.KS 카카오페이 인터넷
352820.KS 하이브 엔터
041510.KQ 에스엠 엔터
122870.KQ 와이지엔터테인먼트 엔터
035900.KQ JYP Ent. 엔터
035760.KQ CJ ENM 엔터
253450.KS 스튜디오드래곤 엔터
012450.KS 한화에어로스페이스 방산·전력
034020.KS 두산에너빌리티 방산·전력
267260.KS HD현대일렉트릭 방산·전력
047810.KS 한국항공우주 방산·전력
079550.KS LIG넥스원 방산·전력
064350.KS 현대로템 방산·전력
015760.KS 한국전력 방산·전력
005490.KS POSCO홀딩스 소재·화학
096770.KS SK이노베이션 소재·화학
010950.KS S-Oil 소재·화학
011170.KS 롯데케미칼 소재·화학
011780.KS 금호석유 소재·화학
011790.KS SKC 소재·화학
010140.KS 삼성중공업 조선·운송
009540.KS HD한국조선해양 조선·운송
042660.KS 한화오션 조선·운송
011200.KS HMM 조선·운송
028670.KS 팬오션 조선·운송
003490.KS 대한항공 조선·운송
028260.KS 삼성물산 건설·유통
000720.KS 현대건설 건설·유통
006360.KS GS건설 건설·유통
375500.KS DL이앤씨 건설·유통
139480.KS 이마트 건설·유통
023530.KS 롯데쇼핑 건설·유통
282330.KS BGF리테일 건설·유통
066570.KS LG전자 소비재
097950.KS CJ제일제당 소비재
271560.KS 오리온 소비재
004370.KS 농심 소비재
090430.KS 아모레퍼시픽 소비재
021240.KS 코웨이 소비재
161390.KS 한국타이어앤테크놀로지 소비재
017670.KS SK텔레콤 통신
030200.KS KT 통신
032640.KS LG유플러스 통신
"""


def fetch(ticker, tries=3):
    for k in range(tries):
        try:
            df = yf.download(ticker, start=START, progress=False,
                             auto_adjust=True, threads=False)
            if df is not None and len(df) > 200:
                c = df["Close"]
                if hasattr(c, "columns"):
                    c = c.iloc[:, 0]
                return c.dropna()
        except Exception as e:
            if k == tries - 1:
                print(f"    ! {ticker}: {e}")
        time.sleep(1.2)
    return None


def main():
    universe = []
    for tk, nm, base, mult in PRODUCTS:
        universe.append((tk, nm, "lev", base, mult, "배수형상품"))
    for tk, nm, grp in BASES:
        universe.append((tk, nm, "base", "", 1.0, grp))
        
    for line in STOCKS.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 3:
            tk = parts[0]
            grp = parts[-1]
            nm = " ".join(parts[1:-1])
            universe.append((tk, nm, "stock", "", 1.0, grp))

    print(f"수집 대상 {len(universe)}종  (시작 {START})\n")
    series, meta, fail = {}, {}, []
    for i, (tk, nm, cat, base, mult, grp) in enumerate(universe, 1):
        print(f"  [{i:3d}/{len(universe)}] {nm} ({tk})", flush=True)
        s = fetch(tk)
        if s is None or len(s) < 200:
            fail.append(f"{nm}({tk})"); continue
        series[tk] = s
        meta[tk] = dict(name=nm, cat=cat, base=base, mult=mult, grp=grp)

    # 기초자산이 없는 배수형 상품은 제외한다(계산이 성립하지 않는다)
    for tk in [t for t, m in meta.items() if m["cat"] == "lev" and m["base"] not in series]:
        print(f"    - {meta[tk]['name']}: 기초자산 미수집으로 제외")
        series.pop(tk); meta.pop(tk)

    idx = sorted(set().union(*[set(s.index) for s in series.values()]))
    dates = [d.strftime("%Y-%m-%d") for d in idx]
    assets = {}
    for tk, s in series.items():
        r = s.reindex(idx)
        assets[tk] = dict(meta[tk],
                          px=[None if pd.isna(v) else round(float(v), 6) for v in r.values])

    out = dict(schema="alphaguard/3.0",
               generated=datetime.now().strftime("%Y-%m-%d"),
               dates=dates, assets=assets)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    import os
    print(f"\n완료: {OUT}  ({os.path.getsize(OUT)/1024/1024:.2f} MB)")
    print(f"  자산 {len(assets)}종 | 거래일 {len(dates)}일 | {dates[0]} ~ {dates[-1]}")
    n = {}
    for m in assets.values():
        n[m["cat"]] = n.get(m["cat"], 0) + 1
    print(f"  구성: 배수형 {n.get('lev',0)} · 기초/지수 {n.get('base',0)} · 개별종목 {n.get('stock',0)}")
    if fail:
        print(f"  수집 실패 {len(fail)}종: {', '.join(fail[:12])}{' 외' if len(fail)>12 else ''}")
        print("  (상장 이력이 짧거나 티커가 변경된 종목입니다. 나머지로 정상 동작합니다.)")


if __name__ == "__main__":
    main()