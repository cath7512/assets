import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

# S&P 500 (^GSPC) 데이터 다운로드 (1960-01-01 ~ 2025-09-30)
data = yf.download('^GSPC', start='1960-01-01', end='2025-09-30')

# Plotly로 그래프 생성
fig = go.Figure()
fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='S&P 500 Close'))
fig.update_layout(title='S&P 500 Daily Close (1960-2025)',
				  xaxis_title='Date',
				  yaxis_title='Index Value',
				  template='plotly_white')

# HTML 파일로 저장 (Plotly.js를 embed하여 오프라인에서도 보이게)
fig.write_html('sp500_plot.html', include_plotlyjs='embed')
print('그래프가 sp500_plot.html 파일로 저장되었습니다. (Plotly.js 포함)')

# Start a simple HTTP server
import os
os.system('python3 -m http.server 8080')
