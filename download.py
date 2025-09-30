import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import json
import os

# 티커 목록 읽기
with open("tickers.json", "r") as f:
    tickers = json.load(f)["tickers"]

# 조건 함수 직접 구현
def condition(row, df):
    idx = row.name
    ma5 = df['Close'].rolling(5).mean()
    ma10 = df['Close'].rolling(10).mean()
    v5 = ma5.loc[idx]
    v10 = ma10.loc[idx]
    if isinstance(v5, pd.Series):
        v5 = v5.iloc[0]
    if isinstance(v10, pd.Series):
        v10 = v10.iloc[0]
    if pd.isna(v5) or pd.isna(v10):
        return False
    return v5 < v10

# 구간 분리 함수
def split_by_condition(df, cond_func):
    segments = []
    current_color = None
    current_x = []
    current_y = []
    for idx, row in df.iterrows():
        color = 'red' if cond_func(row, df) else 'black'
        if color != current_color and current_x:
            segments.append((current_color, current_x, current_y))
            current_x = []
            current_y = []
        current_color = color
        current_x.append(idx)
        current_y.append(row['Close'])
    if current_x:
        segments.append((current_color, current_x, current_y))
    return segments

# HTML 차트 코드 저장용 리스트
charts_html = []

for ticker in tickers:
    print(f"다운로드 중: {ticker}")
    df = yf.download(ticker, start='1990-01-01')
    if df.empty:
        print(f"데이터 없음: {ticker}")
        continue
    # 티커명 가져오기
    info = yf.Ticker(ticker).info
    ticker_name = info.get('shortName', ticker)

    # 조건에 따라 구간 분리
    segments = split_by_condition(df, condition)
    fig = go.Figure()
    for color, x, y in segments:
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines', line=dict(color=color), name=color))

    fig.update_layout(title=ticker_name, width=600, height=400)

    # 차트 HTML로 저장
    chart_html = fig.to_html(include_plotlyjs=False, full_html=False, default_height=400, default_width=600)
    charts_html.append({'ticker': ticker, 'name': ticker_name, 'chart': chart_html})

# index.html 생성
html_head = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>티커별 차트</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        .chart-container { margin-bottom: 40px; }
        .btn-group { margin-top: 10px; }
        button { margin-right: 5px; }
    </style>
</head>
<body>
'''
html_tail = '</body></html>'

# 티커별 데이터 JS로 embed
js_data = 'var tickerData = {};'  # 티커별 데이터 저장
for chart in charts_html:
    # 날짜, 가격, 색상 배열을 JS로 변환
    ticker = chart['ticker']
    df = yf.download(ticker, start='1990-01-01')
    dates = [str(d.date()) for d in df.index]
    # 안전하게 prices 리스트 생성
    if 'Close' in df.columns:
        close_col = df['Close']
        # Series 또는 DataFrame 구분
        if isinstance(close_col, pd.DataFrame):
            prices = close_col.iloc[:, 0].tolist()
        else:
            prices = close_col.tolist()
    else:
        prices = []
    colors = ['red' if condition(row, df) else 'black' for _, row in df.iterrows()]
    js_data += f"\ntickerData['{ticker}'] = {{dates: {dates}, prices: {prices}, colors: {colors}}};"

html_body = ''
for chart in charts_html:
    html_body += f'<div class="chart-container">\n        <h2>{chart["name"]} ({chart["ticker"]})</h2>\n        <div id="chart-{chart["ticker"]}"></div>\n        <div class="btn-group">\n            <button onclick="updateChart(\'{chart["ticker"]}\', \'3m\')">3m</button>\n            <button onclick="updateChart(\'{chart["ticker"]}\', \'6m\')">6m</button>\n            <button onclick="updateChart(\'{chart["ticker"]}\', \'1y\')">1y</button>\n            <button onclick="updateChart(\'{chart["ticker"]}\', \'5y\')">5y</button>\n            <button onclick="updateChart(\'{chart["ticker"]}\', \'all\')">all</button>\n        </div>\n    </div>'

# JS: 기간별 차트 업데이트 함수 구현
html_body += f'''
<script>
{js_data}

function getPeriodDates(dates, period) {{
    var end = new Date(dates[dates.length-1]);
    var start;
    if (period === '3m') {{
        start = new Date(end); start.setMonth(end.getMonth()-3);
    }} else if (period === '6m') {{
        start = new Date(end); start.setMonth(end.getMonth()-6);
    }} else if (period === '1y') {{
        start = new Date(end); start.setFullYear(end.getFullYear()-1);
    }} else if (period === '5y') {{
        start = new Date(end); start.setFullYear(end.getFullYear()-5);
    }} else {{
        start = new Date(dates[0]);
    }}
    return dates.filter(function(d) {{
        var dt = new Date(d);
        return dt >= start && dt <= end;
    }});
}}

function updateChart(ticker, period) {{
    var data = tickerData[ticker];
    var dates = data.dates;
    var prices = data.prices;
    var colors = data.colors;
    var periodDates = getPeriodDates(dates, period);
    var idxStart = dates.indexOf(periodDates[0]);
    var idxEnd = dates.indexOf(periodDates[periodDates.length-1]);
    var showDates = dates.slice(idxStart, idxEnd+1);
    var showPrices = prices.slice(idxStart, idxEnd+1);
    var showColors = colors.slice(idxStart, idxEnd+1);
    var trace = {{
        x: showDates,
        y: showPrices,
        mode: 'lines',
        line: {{color: 'black'}},
        marker: {{color: showColors}},
        name: ticker
    }};
    Plotly.react('chart-'+ticker, [trace], {{title: ticker, width:600, height:400}});
}}

window.onload = function() {{
    for (var ticker in tickerData) {{
        updateChart(ticker, 'all');
    }}
}}
</script>
'''

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_head + html_body + html_tail)
    print('index.html 생성 완료')
