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

def candle_stick(con, instrument, table_type, start_time, end_time):
    sql = "select insert_time, open_ask, open_bid, high_ask, high_bid, low_ask, low_bid, close_ask, close_bid from %s_%s_TABLE where '%s' < insert_time and insert_time < '%s'" % (instrument, table_type, start_time, end_time)
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

    fig = plt.figure(figsize=(10, 5))
    ax = fig.add_subplot(1, 1, 1)
    mpl_finance.candlestick_ohlc(ax, data, width=0.5/(24*12), alpha=0.5, colorup="r", colordown="b")

    ax.grid()

    locator = mdates.MinuteLocator(byminute=None, interval=30, tz=None)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%H:%M"))

    plt.savefig("candle.png")
    plt.close()