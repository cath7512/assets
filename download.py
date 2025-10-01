import yfinance as yf
import pandas as pd
import json
import os

# 티커 목록 읽기
with open("tickers.json", "r") as f:
    tickers = json.load(f)["tickers"]

# 데이터 저장 폴더 생성
os.makedirs("tickers", exist_ok=True)

# 조건 함수 직접 구현
def condition(row, df):
    idx = row.name
    # idx가 Timestamp가 아닐 경우 처리
    try:
        pos = df.index.get_loc(idx)
    except KeyError:
        return False
    # 최근 5일, 10일 데이터가 부족하면 False
    if pos < 9:
        return False
    close = df['Close']
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    avg5 = close.iloc[pos-4:pos+1].mean()
    avg10 = close.iloc[pos-9:pos+1].mean()
    # mean()은 항상 단일 float을 반환하므로, 비교 결과는 단일 bool
    return float(avg5) < float(avg10)

for ticker in tickers:
    print(f"다운로드 중: {ticker}")
    df = yf.download(ticker, start='1990-01-01', auto_adjust=True)
    if df.empty:
        print(f"데이터 없음: {ticker}")
        continue
    info = yf.Ticker(ticker).info
    ticker_name = info.get('shortName', ticker)

    # 날짜, 가격, 색상 데이터 생성
    dates = [str(d.date()) for d in df.index]
    close = df['Close']
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
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
