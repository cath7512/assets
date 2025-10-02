import yfinance as yf
import pandas as pd
import json
import os
from pandas_datareader import data as pdr

# 티커 목록 읽기
with open("tickers.json", "r") as f:
    tj = json.load(f)
    tickers = tj["tickers"]
    key_indices = tj.get("key indices", [])
    all_tickers = list(set(tickers + key_indices))

# 데이터 저장 폴더 생성
os.makedirs("tickers", exist_ok=True)

# 조건 함수 직접 구현
def condition(row, df):
    idx = row.name
    try:
        pos = df.index.get_loc(idx)
    except KeyError:
        return False
    # 최근 20일, 60일 데이터가 부족하면 False
    if pos < 59:
        return False
    close = df['Close']
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    avg20 = close.iloc[pos-19:pos+1].mean()
    avg60 = close.iloc[pos-59:pos+1].mean()
    return float(avg20) < float(avg60)

for ticker in all_tickers:
    print(f"다운로드 중: {ticker}")
    if ticker in ["CPIAUCSL", "FEDFUNDS"]:
        try:
            df = pdr.DataReader(ticker, "fred", start="1990-01-01")
            df = df.rename(columns={ticker: "Close"})
        except Exception as e:
            print(f"FRED 데이터 오류: {e}")
            continue
    else:
        df = yf.download(ticker, start='1990-01-01', auto_adjust=True)
    if df.empty:
        print(f"데이터 없음: {ticker}")
        continue
    info = {}
    if ticker not in ["CPIAUCSL", "FEDFUNDS"]:
        info = yf.Ticker(ticker).info
    ticker_name = info.get('shortName', ticker)

    # 날짜, 가격, 색상 데이터 생성
    dates = [str(d.date()) for d in df.index]
    close = df['Close']
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    # CPIAUCSL이면 MoM 변동률로 저장
    if ticker == "CPIAUCSL":
        close = pd.to_numeric(close, errors="coerce")
        mom = close.pct_change() * 100
        prices = [round(float(p), 2) if pd.notnull(p) else None for p in mom]
    else:
        prices = [float(p) for p in close if isinstance(p, (int, float, complex))]
    colors = []
    for idx, row in df.iterrows():
        colors.append('red' if condition(row, df) else 'black')

    # 티커별 json 파일로 저장
    data = {
        "dates": dates,
        "prices": prices,
        "colors": colors,
        "name": ticker_name
    }
    with open(f"tickers/{ticker}.json", "w", encoding="utf-8") as jf:
        json.dump(data, jf, ensure_ascii=False)
    print(f"tickers/{ticker}.json 저장 완료")
