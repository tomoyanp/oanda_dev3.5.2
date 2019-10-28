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

def candle_stick(price_df):
    price_df["insert_time"] = mdates.date2num(price_df["insert_time"])

    candle_df = pd.DataFrame()
    candle_df["insert_time"] = price_df["insert_time"]
    candle_df["open"] = price_df["open"]
    candle_df["high"] = price_df["high"]
    candle_df["low"] = price_df["low"]
    candle_df["close"] = price_df["close"]
    data = candle_df.values
    

    fig = plt.figure(figsize=(10, 5))
    ax = fig.add_subplot(1, 1, 1)
    mpl_finance.candlestick_ohlc(ax, data, width=0.5/(24*12), alpha=0.5, colorup="r", colordown="b")

    ax.grid()

    locator = mdates.MinuteLocator(byminute=None, interval=60, tz=None)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%H:%M"))

    #plt.savefig("candle.png")
    #plt.close()

    return plt, ax

if __name__ == "__main__":
    from main import get_price
    instrument = "GBP_JPY"
    table_type = "5m"
    insert_time = "2019-07-02 10:00:00"
    price_df = get_price(instrument, insert_time, table_type, length=12*10)
    plt, ax = candle_stick(price_df)
    plt.savefig("simple_candle.png")
    plt.close()

