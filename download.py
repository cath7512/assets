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
charts_data = []
js_data = 'var tickerData = {}\n'
for ticker in tickers:
    print(f"다운로드 중: {ticker}")
    df = yf.download(ticker, start='1990-01-01', auto_adjust=True)
    if df.empty:
        print(f"데이터 없음: {ticker}")
        continue
    info = yf.Ticker(ticker).info
    ticker_name = info.get('shortName', ticker)

    # 조건에 따라 구간 분리
    segments = split_by_condition(df, condition)
    fig = go.Figure()
    for color, x, y in segments:
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines', line=dict(color=color), name=color))
    fig.update_layout(title=ticker_name, width=600, height=400)
    chart_html = fig.to_html(include_plotlyjs=False, full_html=False, default_height=200, default_width=300)
    charts_data.append({'ticker': ticker, 'name': ticker_name, 'chart': chart_html, 'df': df})

    # JS 데이터 생성
    dates = [str(d.date()) for d in df.index]
    close = df['Close']
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    prices = [float(p) for p in close if isinstance(p, (int, float, complex))]
    colors = []
    for idx, row in df.iterrows():
        colors.append('red' if condition(row, df) else 'black')
    js_data += f"tickerData['{ticker}'] = {{dates: {dates}, prices: {prices}, colors: {colors}}};\n"

# index.html 생성
html_head = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>티커별 차트</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        .chart-container { margin-bottom: 30px; }
        .btn-group { margin-top: 0px; display: flex; justify-content: center; }
        button { margin: 2px; }
    </style>
</head>
<body>
'''
html_tail = '</body></html>'

html_body = ''
for chart in charts_data:
    html_body += f'<div class="chart-container">\n        <div id="chart-{chart["ticker"]}"></div>\n        <div class="btn-group">\n            <button onclick="updateChart(\'{chart["ticker"]}\', \'3m\')">3m</button>\n            <button onclick="updateChart(\'{chart["ticker"]}\', \'6m\')">6m</button>\n            <button onclick="updateChart(\'{chart["ticker"]}\', \'1y\')">1y</button>\n            <button onclick="updateChart(\'{chart["ticker"]}\', \'5y\')">5y</button>\n            <button onclick="updateChart(\'{chart["ticker"]}\', \'all\')">all</button>\n        </div>\n    </div>'

# JS: 기간별 차트 업데이트 함수 구현 (초기값 5y)
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
        name: ''
    }};
    Plotly.react('chart-'+ticker, [trace], {{title: '', width:300, height:200}});
}}

window.onload = function() {{
    for (var ticker in tickerData) {{
        updateChart(ticker, '5y');
    }}
}}
</script>
'''

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_head + html_body + html_tail)
    print('index.html 생성 완료')
