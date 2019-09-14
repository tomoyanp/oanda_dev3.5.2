# coding: utf-8
# 1. 1時間 10本ボリンジャーシグマ3の幅が100pips以内
# 2. 5分足が21本ボリンジャーバンドシグマ2.5+5pipsに引っかかったらそっちについてく
# 3. 5分ごとに評価してマイナスなら即切る
# 4. sma21に引っかかったら利確
# 5. トレード時間は13時～22時

import sys
import os
import traceback
import json
import math
import pandas as pd



# 実行スクリプトのパスを取得して、追加
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path)

from mysql_connector import MysqlConnector
from datetime import datetime, timedelta
import oanda_wrapper
import re
import traceback
import numpy as np

from logging import getLogger, FileHandler, DEBUG
from send_mail import SendMail

from create_candle import candle_stick
from price_action import trend_line, supreg

#mode = sys.argv[1]
#filename = sys.argv[0].split(".")[0]
##print(filename)
#debug_logfilename = "%s-%s-%s.log" % (mode, filename, datetime.now().strftime("%Y%m%d%H%M%S"))
#debug_logger = getLogger("debug")
#debug_fh = FileHandler(debug_logfilename, "a+")
#debug_logger.addHandler(debug_fh)
#debug_logger.setLevel(DEBUG)

mode = "test"
con = MysqlConnector()

instrument_list = ["EUR_GBP", "EUR_USD", "EUR_JPY", "GBP_USD", "GBP_JPY", "USD_JPY"]
instrument_list = ["GBP_JPY", "EUR_JPY", "AUD_JPY", "GBP_USD", "EUR_USD", "AUD_USD", "USD_JPY"]
start_time = '2019-07-16 20:00:00'
end_time = '2019-07-17 00:00:00'

insert_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")

now = datetime.now()

def decide_season(base_time):
    year = int(base_time.year)
    month = int(base_time.month)

    if month == 3:
        start_time = "%s-03-01 00:00:00" % year
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        sunday = 6
        count = 0

        # 日曜日を数え上げ。2以上だったら夏時間
        while start_time < base_time:
            week_tmp = start_time.weekday()
            if week_tmp == sunday:
                count = count + 1
            start_time = start_time + timedelta(days=1)

        if count >= 2:
            season = "summer"
        else:
            season = "winter"


    elif month == 11:
        start_time = "%s-11-01 00:00:00" % year
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        sunday = 6
        count = 0

        # 日曜日を数え上げ。1以上だったら冬時間
        while start_time < base_time:
            week_tmp = start_time.weekday()
            if week_tmp == sunday:
                count = count + 1
            start_time = start_time + timedelta(days=1)

        if count >= 1:
            season = "winter"
        else:
            season = "summer"

    elif month == 4 or month == 5 or month == 6 or month == 7 or month == 8 or month == 9 or month == 10:
        season = "summer"
    elif month == 12 or month == 1 or month == 2:
        season = "winter"

    return season


# マーケットが休みであればfalseを返す
def decide_market(base_time):
    flag = True
    year = int(base_time.year)
    month = int(base_time.month)
    week = int(base_time.weekday())
    day = int(base_time.day)
    hour = int(base_time.hour)

    # 日曜日
    if week == 6:
        flag = False
    else:
        season = decide_season(base_time)
        if season == "summer":
            if week == 5 and hour > 5:
                flag = False
            elif week == 0 and hour < 6:
                flag = False
        if season == "winter":
            if week == 5 and hour > 6:
                flag = False
            elif week == 0 and hour < 7:
                flag = False

    return flag


def convertTime(insert_time, table_type):
    if table_type == "5s":
        insert_time = insert_time - timedelta(seconds=5)
    elif table_type == "1m":
        insert_time = insert_time - timedelta(minutes=1)
    elif table_type == "5m":
        insert_time = insert_time - timedelta(minutes=5)
    elif table_type == "15m":
        insert_time = insert_time - timedelta(minutes=15)
    elif table_type == "30m":
        insert_time = insert_time - timedelta(minutes=30)
    elif table_type == "1h":
        insert_time = insert_time - timedelta(hours=1)
    elif table_type == "3h":
        insert_time = insert_time - timedelta(hours=3)
    elif table_type == "8h":
        insert_time = insert_time - timedelta(hours=8)
    elif table_type == "day":
        insert_time = insert_time - timedelta(days=1)
    else:
        raise

    return insert_time

def get_bollinger(instrument, insert_time, table_type, window_size, sigma_valiable):
    insert_time = convertTime(insert_time, table_type)
    sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time <= '%s' order by insert_time desc limit %s" % (instrument, table_type, insert_time, window_size)
    response = con.select_sql(sql)

    tmp_list = []
    for res in response:
        tmp_list.append((res[0]+res[1])/2)
    tmp_list.reverse()

    # pandasの形式に変換
    price_list = pd.Series(tmp_list)

    # シグマと移動平均の計算
    sigma = price_list.rolling(window=window_size).std(ddof=0)
    base = price_list.rolling(window=window_size).mean()

    # ボリンジャーバンドの計算
    upper_sigmas = base + (sigma*sigma_valiable)
    lower_sigmas = base - (sigma*sigma_valiable)

    # 普通の配列型にキャストして返す
    upper_sigmas = upper_sigmas.values.tolist()
    lower_sigmas = lower_sigmas.values.tolist()
    base = base.values.tolist()

    data_set = { "upper_sigmas": upper_sigmas,
                 "lower_sigmas": lower_sigmas,
                 "base_lines": base }
    return data_set

def calc_pips(instrument, start_price, end_price):
    coefficient = 0
    if re.search("JPY", instrument) != None:
        coefficient = 100
    else:
        coefficient = 10000

    result = (end_price - start_price)*coefficient

    return result

def stl(insert_time, trade_obj, profit_rate, orderstop_rate):
    stl_time = insert_time
    ask, bid = get_price(trade_obj["instrument"], insert_time)

    stl_flag = False
    if trade_obj["side"] == "buy":
        # ここの計算おかしいからちゃんと調べる
        # pips = (price/trade_obj["price"] - 1.0) * 10000
        pips = calc_pips(trade_obj["instrument"], trade_obj["ask"], bid)
    elif trade_obj["side"] == "sell":
        # ここの計算おかしいからちゃんと調べる
        # pips = (trade_obj["price"]/price - 1.0) * 10000
        pips = calc_pips(trade_obj["instrument"], ask, trade_obj["bid"])
    else:
        raise

    if trade_obj["algo"] == "bollinger":
        stl_minutes = 5
    else:
        stl_minutes = 20

    if trade_obj["trade_time"] + timedelta(minutes=stl_minutes) <= stl_time:
        if pips < 0:
            stl_flag = True

        if stl_time.minute % 5 == 0:
            sma = get_sma(trade_obj["instrument"], stl_time, "5m", 21)
            ask, bid = get_price(trade_obj["instrument"], stl_time)
            price = (ask + bid) / 2
            if trade_obj["side"] == "buy" and price < sma and pips > 0:
                stl_flag = True
            elif trade_obj["side"] == "sell" and price > sma and pips > 0:
                stl_flag = True

    # 一応、損切利確判定をする
    if pips > profit_rate:
        stl_flag = True
    elif pips < orderstop_rate:
        stl_flag = True

    if stl_flag: 
        trade_obj["stl_time"] = stl_time
        trade_obj["stl_ask"] = ask
        trade_obj["stl_bid"] = bid
        trade_obj["profit"] = pips

    trade_obj["stl_flag"] = stl_flag

    return trade_obj

def get_sma(instrument, insert_time, table_type, length):
    insert_time = convertTime(insert_time, table_type)
    sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < '%s' order by insert_time desc limit %s" % (instrument, table_type, insert_time, length)
    response = con.select_sql(sql)
    tmp_list = []
    for res in response:
        tmp_list.append(res[0])
        tmp_list.append(res[1])

    tmp_list = np.array(tmp_list)
    sma = np.average(tmp_list)

    return sma

def get_price(instrument, insert_time, table_type, length):
    if type(insert_time) == str:
        insert_time = datetime.strptime(insert_time, "%Y-%m-%d %H:%M:%S")
    insert_time = convertTime(insert_time, table_type)

    sql = "select open_ask, open_bid, close_ask, close_bid, high_ask, high_bid, low_ask, low_bid, insert_time from %s_%s_TABLE where insert_time <= '%s' order by insert_time desc limit %s" % (instrument, table_type, insert_time, length)
    response = con.select_sql(sql)

    response_list = []
    for i in reversed(range(0, len(response))):
        response_list.append(list(response[i]))

    df = pd.DataFrame(response_list)
    df.rename(columns={
        0: "open_ask",
        1: "open_bid",
        2: "close_ask",
        3: "close_bid",
        4: "high_ask",
        5: "high_bid",
        6: "low_ask",
        7: "low_bid",
        8: "insert_time"
    }, inplace=True)

    return_df = pd.DataFrame()
    return_df["open"] = (df["open_ask"]+df["open_bid"])/2
    return_df["close"] = (df["close_ask"]+df["close_bid"])/2
    return_df["high"] = (df["high_ask"]+df["high_bid"])/2
    return_df["low"] = (df["low_ask"]+df["low_bid"])/2
    return_df["insert_time"] = df["insert_time"]

    return return_df


def decide_trade(insert_time, trade_obj):
    if trade_obj["algo"] == "bollinger":
        flag, trade_obj = kick_back(insert_time, trade_obj["instrument"], trade_obj, length=120)
        trade_obj["flag"] = flag
    else:
        for instrument in instrument_list:
            flag, trade_obj = over_bollinger(insert_time, instrument, trade_obj)
            if flag:
                trade_obj["flag"] = flag
                break

    if trade_obj["flag"]:
        trade_obj["trade_time"] = insert_time
    return trade_obj
         
def reset_tradeobj():
    return  {"flag": False, "stl_flag": False, "algo": "null"}

def decide_tradetime(insert_time):
    hour = insert_time.hour
    minute = insert_time.minute

    flag = False
    if 13 < hour < 22:
        flag = True

#    if hour < 4:
#        flag = True
#    elif hour > 8:
#        flag = True

    return flag


if __name__ == "__main__":
    instrument = "GBP_JPY"
    insert_time = datetime.strptime("2019-07-02 02:00:00", "%Y-%m-%d %H:%M:%S")
    table_type = "5m"
    base_candle_size = 5 #5分足を使う
    window_size = 12*6 #6時間分
    show_after_size = 12*2 #表示用は二時間後まで表示するようにする
    ema_max_size = 100

    # 計算用
    price_df = get_price(instrument, insert_time, table_type, length=window_size)
    # 描画用（売買後の値動きを見たいため）
    all_price_df = get_price(instrument, insert_time + timedelta(minutes=base_candle_size*show_after_size), table_type, length=show_after_size)
    # EMA用（過去のローソク足がないと計算できないため）
    all_price_df = get_price(instrument, insert_time + timedelta(minutes=base_candle_size*show_after_size), table_type, length=show_after_size+ema_max_size)

    ##########################################################################################################
    # EMAの計算
    ema25 = ema_price_df["close"].ewm(span=25).mean()
    ema100 = ema_price_df["close"].ewm(span=100).mean()
    ema = pd.DataFrame()
    ema["ema25"] = ema25.copy()
    ema["ema100"] = ema100.copy()
    ema["insert_time"] = ema_price_df["insert_time"].copy()

    # 過去分はそぎ落とす
    ema = ema[ema_max_size:]

    ##########################################################################################################
    # 短期トレンドラインの計算をする
    # トレンドラインを直近ので計算するといつまでもブレイクしないので30分前にする
    short_trend_df = get_price(instrument, insert_time, table_type, length=12+6)
    short_trend_df = short_trend_df[:-6]
    short_trend_fin_df = trend_line(short_trend_df)

    # x軸のインデックスを求める
    diff = insert_time - short_trend_fin_df["insert_time"][0]
    index = diff.seconds / 300

    # 現在のトレンドラインを求める
    current_short_trend_high = short_trend_fin_df["high_slope"] * index + short_trend_fin_df["high_intercept"]
    current_short_trend_low = short_trend_fin_df["low_slope"] * index + short_trend_fin_df["low_intercept"]

    ########################################################################################################
    # 長期トレンドラインの計算をする
    # トレンドラインを直近ので計算するといつまでもブレイクしないので30分前にする
    long_trend_df = price_df[:-6]
    long_trend_fin_df = trend_line(long_trend_df)

    # x軸のインデックスを求める
    diff = insert_time - long_trend_fin_df["insert_time"][0]
    index = diff.seconds / 300

    # 現在のトレンドラインを求める
    current_long_trend_high = long_trend_fin_df["high_slope"] * index + long_trend_fin_df["high_intercept"]
    current_long_trend_low = long_trend_fin_df["low_slope"] * index + long_trend_fin_df["low_intercept"]

    ########################################################################################################
    # サポートライン、レジスタンスラインを求める 
    supreg_list = supreg(price_df)
    for supreg in supreg_list:
        if price_df["close"].values[-1] < supreg["price"] and supreg["direction"] == "high":
            registance_line = supreg["price"]
        elif price_df["close"].values[-1] > supreg["price"] and supreg["direction"] == "low":
            support_line = supreg["price"]


    # ローソク足の描画
    plt, ax = candle_stick(all_price_df)

    # 長期トレンドラインを描画する
    ax.plot(long_trend_fin_df["insert_time"], long_trend_fin_df["high_trend"], linewidth="1.0", color="green")
    ax.plot(long_trend_fin_df["insert_time"], long_trend_fin_df["low_trend"], linewidth="1.0", color="green")

    # 短期トレンドラインを描画する
    ax.plot(short_trend_fin_df["insert_time"], short_trend_fin_df["high_trend"], linewidth="1.0", color="green")
    ax.plot(short_trend_fin_df["insert_time"], short_trend_fin_df["low_trend"], linewidth="1.0", color="green")

    # EMAを描画する
    ax.plot(ema["insert_time"], ema["ema25"], linewidth="1.0", color="orange")
    ax.plot(ema["insert_time"], ema["ema100"], linewidth="1.0", color="red")

    # サポートレジスタンスラインを描画する
    ax.axhline(y=registance_line, linewidth="1.0", color="red")
    ax.axhline(y=support_line, linewidth="1.0", color="blue")

    plt.savefig("sample.png")
    plt.close()

#if __name__ == "__main__":
#    trade_account = {
#        "accountId": "101-009-10684893-001",
#        "accessToken": "d6fa56ee0ced50ea925683cb9c316df1-8daba3977f5335ed52327c5cc54ebf5a",
#        "env": "practice"
#    }
#
#    trade_obj = reset_tradeobj()
#    stl_obj = {}
#    profit_rate = 50 
#    orderstop_rate = -20
#
#    instrument = "GBP_JPY"
#    table_type = "5m"
#
#    if mode == "demo":
#        insert_time = now
#
#    while True:
#        try: 
#            if insert_time >= end_time and mode == "test":
#                break
#            elif mode == "demo":
#                insert_time = datetime.now()
#            else:
#                insert_time = insert_time + timedelta(minutes=5)
#    
#            if decide_market(insert_time):
#                price_df = get_price(instrument, insert_time, table_type, length=48)
#
#                # トレンドラインを直近ので計算するといつまでもブレイクしないので2時間前にする
#                trend_df = price_df.copy()
#                trend_df = trend_df[:-24]
#                trend_fin_df = trend_line(trend_df)
#
#                candle_stick(price_df)
#                
#                #status = outside_bar(instrument, insert_time, table_type)
#                #if status["outside_bar"]:
#                #    print("%s outsidebar, direction=%s" % (insert_time, status["direction"]))
#
#                #status = inside_bar(instrument, insert_time, table_type)
#                #if status["inside_bar"]:
#                #    print("%s insidebar, direction=%s" % (insert_time, status["direction"]))
#
#                status = barbwire(instrument, insert_time, table_type)
#                if status["barbwire"]:
#                    print("%s barbwire, direction=%s" % (insert_time, status["barbwire"]))
#
#        except:
#            message = traceback.format_exc()
#            debug_logger.info(message)
#            sendmail = SendMail("tomoyanpy@gmail.com", "tomoyanpy@softbank.ne.jp", "../property")
#            sendmail.set_msg(message)
#            sendmail.send_mail()
#
#    candle_stick(con, instrument, table_type, start_time, end_time)