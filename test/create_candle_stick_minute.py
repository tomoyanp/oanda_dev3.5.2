#coding: utf-8
# 実行スクリプトのパスを取得して、追加
import sys, os
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path)
sys.path.append(current_path + '../lib')

import matplotlib
matplotlib.use('Agg')
from matplotlib.ticker import MultipleLocator
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mpl_finance
from matplotlib import ticker
import pandas as pd


from mysql_connector import MysqlConnector

con = MysqlConnector()

sql = "select insert_time, open_ask, open_bid, high_ask, high_bid, low_ask, low_bid, close_ask, close_bid from GBP_JPY_5m_TABLE where insert_time < '2019-07-01 00:00:00' order by insert_time desc limit 1000"
#sql = "select insert_time, open_ask, open_bid, high_ask, high_bid, low_ask, low_bid, close_ask, close_bid from GBP_JPY_day_TABLE where insert_time < '2019-07-01 00:00:00' order by insert_time desc limit 100"
res = con.select_sql(sql)

lst = []
for r in res:
    print(r)
    lst.append(list(r))


df = pd.DataFrame(lst)
insert_time = df[0]
op_price = (df[1] + df[2])/2
hi_price = (df[3] + df[4])/2
lw_price = (df[5] + df[6])/2
cl_price = (df[7] + df[8])/2

df = pd.DataFrame()

df['insert_time'] = mdates.date2num(insert_time)
df['open'] = op_price
df['high'] = hi_price
df['low'] = lw_price
df['close'] = cl_price

data = df.values

average_data = (df["open"] + df["high"] + df["low"] + df["close"]) / 4

fig = plt.figure(figsize=(100, 5))
ax = fig.add_subplot(1, 1, 1)
mpl_finance.candlestick_ohlc(ax, data, width=0.5/(24*12), alpha=0.5, colorup="r", colordown="b")

#average_data = average_data.values
#ax.plot(average_data, color="Green")
for i, line in enumerate(average_data):
    ax.plot(line, label=i)



ax.grid()



locator = mdates.MinuteLocator(byminute=None, interval=30, tz=None)
ax.xaxis.set_major_locator(locator)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%H:%M"))

#print(average_data.values[0])


plt.savefig("minute.svg")

#fig = plt.figure()
#ax = plt.subplot()
##mpl_finance.candlestick2_ohlc(ax, opens=df.open.values, closes=df.close.values, highs=df.high.values, lows=df.low.values, width=0.8, colorup="r", colordown="b")
#
#
#plt.close()