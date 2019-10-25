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
import subprocess
import time

mode = sys.argv[1].strip()

account_file = open("account.properties")
account_json = json.load(account_file)
account_id = account_json["account_id"]
token = account_json["token"]
env = account_json["env"]

from oanda_wrapper import OandaWrapper

oanda = OandaWrapper(env, account_id, token, units=200000)

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
from price_action import trend_line, supreg, inside_bar, outside_bar, barbwire

debug_logfilename = "%s_debug.log" % (datetime.now().strftime("%Y%m%d%H%M%S"))
debug_logger = getLogger("debug")
debug_fh = FileHandler(debug_logfilename, "a+")
debug_logger.addHandler(debug_fh)
debug_logger.setLevel(DEBUG)

trace_logfilename = "%s_trace.log" % (datetime.now().strftime("%Y%m%d%H%M%S"))
trace_logger = getLogger("trace")
trace_fh = FileHandler(trace_logfilename, "a+")
trace_logger.addHandler(trace_fh)
trace_logger.setLevel(DEBUG)



con = MysqlConnector()
instrument = "GBP_JPY"
#insert_time = datetime.strptime("2019-04-01 20:20:30", "%Y-%m-%d %H:%M:%S")
#insert_time = datetime.strptime("2019-04-01 00:00:30", "%Y-%m-%d %H:%M:%S")
insert_time = datetime.strptime("2019-04-01 19:00:30", "%Y-%m-%d %H:%M:%S")
end_time = datetime.strptime("2019-10-19 05:00:30", "%Y-%m-%d %H:%M:%S")
table_type = "5m"
base_candle_size = 5 #5分足を使う
window_size = 12*6 #6時間分
show_after_size = 12*2 #表示用は二時間後まで表示するようにする
ema_max_size = 100



def plot_chart(insert_time, all_price_df, long_trend, short_trend, ema, registance_line, support_line, current_price):
    # ローソク足の描画
    plt, ax = candle_stick(all_price_df)

    # 現在地点の描画
    ax.plot(insert_time, current_price, marker=".", color="yellow", markersize=10)
    ax.axvline(x=insert_time, linewidth="0.5", color="yellow")

    # 長期トレンドラインを描画する
    ax.plot(long_trend["insert_time"], long_trend["high_trend"], linewidth="1.0", color="green")
    ax.plot(long_trend["insert_time"], long_trend["low_trend"], linewidth="1.0", color="green")

    # 短期トレンドラインを描画する
    ax.plot(short_trend["insert_time"], short_trend["high_trend"], linewidth="1.0", color="green")
    ax.plot(short_trend["insert_time"], short_trend["low_trend"], linewidth="1.0", color="green")

    # EMAを描画する
    ax.plot(ema["insert_time"], ema["ema25"], linewidth="1.0", color="orange")
    ax.plot(ema["insert_time"], ema["ema100"], linewidth="1.0", color="red")

    # サポートレジスタンスラインを描画する
    for ln in registance_line:
        ax.axhline(y=ln, linewidth="1.0", color="red")
    for ln in support_line:
        ax.axhline(y=ln, linewidth="1.0", color="blue")

    plt.savefig("images/%s.png" % insert_time.strftime("%Y%m%d%H%M"))
    plt.close()

def plot_result(trade_flags):
    diff = trade_flags["end_time"] - trade_flags["start_time"]
    diff_minutes = int(diff.total_seconds()/60/5)

    future_time = 7200

    all_price_df = get_price(instrument, trade_flags["end_time"] + timedelta(seconds=future_time), table_type, length=show_after_size+window_size+diff_minutes+(int(future_time/300)))

    # ローソク足の描画
    plt, ax = candle_stick(all_price_df)

    #print(trade_flags["position"])
    if trade_flags["direction"] == "buy":
        trade_color = "blue"
        stl_color = "red"
    else:
        trade_color = "red"
        stl_color = "blue"

    # 約定時点 
    ax.plot(trade_flags["start_time"], trade_flags["position_price"], marker=".", color=trade_color, markersize=10)
    ax.axvline(x=trade_flags["start_time"], linewidth="0.5", color=trade_color)

    # 決済時点 
    ax.plot(trade_flags["end_time"], trade_flags["stl_price"], marker=".", color=stl_color, markersize=10)
    ax.axvline(x=trade_flags["end_time"], linewidth="0.5", color=stl_color)

    # 回帰分析の結果を描画する
    ax.plot(trade_flags["trend"]["insert_time"], trade_flags["trend"]["price"], linewidth="1.0", color="green")

    # 長期トレンドラインを描画する
    #ax.plot(trade_flags["long_trend"]["insert_time"], trade_flags["long_trend"]["high_trend"], linewidth="1.0", color="green")
    #ax.plot(trade_flags["long_trend"]["insert_time"], trade_flags["long_trend"]["low_trend"], linewidth="1.0", color="green")

    # 短期トレンドラインを描画する
    #ax.plot(trade_flags["short_trend"]["insert_time"], trade_flags["short_trend"]["high_trend"], linewidth="1.0", color="green")
    #ax.plot(trade_flags["short_trend"]["insert_time"], trade_flags["short_trend"]["low_trend"], linewidth="1.0", color="green")

    # EMAを描画する
    ax.plot(trade_flags["ema"]["insert_time"], trade_flags["ema"]["ema25"], linewidth="1.0", color="orange")
    ax.plot(trade_flags["ema"]["insert_time"], trade_flags["ema"]["ema100"], linewidth="1.0", color="red")

    # サポートレジスタンスラインを描画する
    #for ln in trade_flags["registance_line"]:
    #    ax.axhline(y=ln, linewidth="1.0", color="red")
    #for ln in trade_flags["support_line"]:
    #    ax.axhline(y=ln, linewidth="1.0", color="blue")

    plt.savefig("results/%s-%s.png" % (trade_flags["start_time"].strftime("%Y%m%d%H%M"), trade_flags["end_time"].strftime("%Y%m%d%H%M")))
    plt.close()

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

def get_current_price(instrument, insert_time):
    table_type = "5s"
    if type(insert_time) == str:
        insert_time = datetime.strptime(insert_time, "%Y-%m-%d %H:%M:%S")
    insert_time = convertTime(insert_time, table_type)

    sql = "select close_ask, close_bid, insert_time from %s_%s_TABLE where insert_time <= '%s' order by insert_time desc limit 1" % (instrument, table_type, insert_time)
    response = con.select_sql(sql)

    ask = response[0][0]
    bid = response[0][1]
    insert_time = response[0][2]

    return ask, bid, insert_time

def reset_trade_flags():
    return  {"direction": "flat", "touched_ema": False, "position": False, "buildup_count": 0, "buildup": False, "price_action_count": 0, "stl": False}

def decide_tradetime(insert_time):
    hour = insert_time.hour
    minute = insert_time.minute

    return True
#    flag = False
#    if hour < 4 or 12 < hour:
#        flag = True
#
#    return flag

def getSlope(target_list):
    index_list = []
    tmp_list = []

    for i in range(1, len(target_list)+1):
        index_list.append(i)

    price_list = np.array(target_list)
    index_list = np.array(index_list)

    z = np.polyfit(index_list, price_list, 1)
    slope, intercept = np.poly1d(z)

    return slope, intercept

def decide_trade(trade_flags, insert_time):
    current_ask, current_bid, current_insert_time = get_current_price(instrument, insert_time)
    current_price = (current_ask + current_bid)/2

    # スプレッドが広い時はトレードはしない
    if current_ask - current_bid > 0.05 and trade_flags["position"] == False:
        pass
    # 週末の3時以降なら即切り
    elif insert_time.weekday() == 5 and insert_time.hour >= 3:
        if trade_flags["position"]:
            trade_flags["end_time"] = insert_time
            trade_flags["stl_price"] = current_bid
            trade_flags["stl"] = True
        else:
            pass
    elif trade_flags["position"] == False and decide_tradetime(insert_time):
        # 計算用
        price_df = get_price(instrument, insert_time, table_type, length=window_size)
        # 描画用（売買後の値動きを見たいため）
        all_price_df = get_price(instrument, insert_time + timedelta(minutes=base_candle_size*show_after_size), table_type, length=show_after_size+window_size)
        # EMA用（過去のローソク足がないと計算できないため）
        ema_price_df = get_price(instrument, insert_time + timedelta(minutes=base_candle_size*show_after_size), table_type, length=show_after_size+window_size+ema_max_size)

        ##########################################################################################################
        # EMAの計算
        ema25 = ema_price_df["close"].ewm(span=25).mean()
        # ema100 = ema_price_df["close"].ewm(span=100).mean()
        ema100 = ema_price_df["close"].ewm(span=200).mean()
        ema = pd.DataFrame()
        ema["ema25"] = ema25.copy()
        ema["ema100"] = ema100.copy()
        ema["insert_time"] = ema_price_df["insert_time"].copy()

        # 過去分はそぎ落とす
        ema = ema[ema_max_size:]

        ##########################################################################################################
        # 短期トレンドラインの計算をする
        short_trend_df = get_price(instrument, insert_time, table_type, length=6)
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
        #long_trend_df = price_df
        long_trend_df = get_price(instrument, insert_time, table_type, length=12*3)
        long_trend_fin_df = trend_line(long_trend_df)


        ########################################################################################################
        # サポートライン、レジスタンスラインを求める 
        # price_df = get_price(instrument, insert_time, table_type, length=5000)

        ### もっと短期のものにする
        # supreg_list = supreg(price_df["low"], price_df["high"], n=24, min_touches=2, stat_likeness_percent=5, bounce_percent=5)
        # support_line = supreg_list["sup"][supreg_list["sup"] > 0]
        # registance_line = supreg_list["res"][supreg_list["res"] > 0]


        supreg_list = supreg(price_df["low"], price_df["high"], n=6, min_touches=2, stat_likeness_percent=5, bounce_percent=5)
        support_line = supreg_list["sup"][supreg_list["sup"] > 0]
        registance_line = supreg_list["res"][supreg_list["res"] > 0]

        ########################################################################################################
        # 売買ロジック

        current_time = pd.to_datetime(price_df.tail(1)["insert_time"], "%Y-%m-%d %H:%M:%S").values[0]
        ema["insert_time"] = pd.to_datetime(ema["insert_time"], format="%Y-%m-%d %H:%M:%S")
        current_ema_df = ema[ema["insert_time"] == current_time]

        # 25emaと終値を比較して、連続して上回る（下回る）のであればトレンドが出ていると判断する
        trend_emas = ema[ema["insert_time"] <= current_time]

        length = 5

        up_count = 0
        down_count = 0


        ema100 = trend_emas["ema100"].tail(length).values

        trend_emas = trend_emas["ema25"].tail(length).values
        open_prices = price_df["open"].tail(length).values
        close_prices = price_df["close"].tail(length).values
        high_prices = price_df["high"].tail(length).values
        low_prices = price_df["low"].tail(length).values


        # 短期的にトレンドが出ているか
        for index in range(0, length):
            if (close_prices[index] > trend_emas[index]) or (open_prices[index] > trend_emas[index]):
                up_count += 1
            elif (close_prices[index] < trend_emas[index]) or (open_prices[index] < trend_emas[index]):
                down_count += 1

        tmp = price_df.tail(36)
        tmp = tmp.reset_index(drop=True)
        maxindex = tmp["close"].idxmax()
        minindex = tmp["close"].idxmin()
        max_price = tmp["close"][maxindex]
        max_time = tmp["insert_time"][maxindex]
        min_price = tmp["close"][minindex]
        min_time = tmp["insert_time"][minindex]

        candle_length = 0
        if min_time < max_time:
            trend_diff = max_price - min_price
            for i in range(minindex, maxindex+1):
                candle_length += abs(tmp["close"][i] - tmp["open"][i])
            trade_flags["candle_length"] = candle_length / (maxindex-minindex)


            start_index = minindex
            end_index = maxindex

            trend_close = tmp["close"][start_index:end_index]            
            trend_insert_time = tmp["insert_time"][start_index:end_index]            
            trend_slope, trend_intercept = getSlope(trend_close)
            trend_slope_price = []

            for i in range(1, len(trend_close)+1):
                trend_slope_price.append((i*trend_slope)+trend_intercept)
            trend_df = pd.DataFrame()
            trend_df["insert_time"] = trend_insert_time
            trend_df["price"] = trend_slope_price
            trade_flags["trend"] = trend_df
            trade_flags["slope"] = trend_slope

            test_df = pd.DataFrame()
            test_df["slope"] = trend_df["price"] 
            test_df["high"] = tmp["close"][start_index:end_index]
            test_df["low"] = tmp["open"][start_index:end_index]

            test_df = test_df.reset_index(drop=True)

            slope_percentage = 0
            slope_count = 0
            for i in range(0, len(test_df["slope"])):
                if test_df["low"][i] < test_df["slope"][i] < test_df["high"][i]:
                    slope_count += 1
                else:
                    pass
            trade_flags["slope_matching"] = (slope_count / len(test_df["slope"]))*100

        else:
            trend_diff = min_price - max_price
            for i in range(maxindex, minindex+1):
                candle_length += abs(tmp["close"][i] - tmp["open"][i])

            trade_flags["candle_length"] = candle_length / (minindex-maxindex)


            start_index = maxindex
            end_index = minindex

            trend_close = tmp["close"][start_index:end_index]            
            trend_insert_time = tmp["insert_time"][start_index:end_index]            
            trend_slope, trend_intercept = getSlope(trend_close)
            trend_slope_price = []
            trade_flags["slope"] = trend_slope

            for i in range(1, len(trend_close)+1):
                trend_slope_price.append((i*trend_slope)+trend_intercept)
            trend_df = pd.DataFrame()
            trend_df["insert_time"] = trend_insert_time
            trend_df["price"] = trend_slope_price
            trade_flags["trend"] = trend_df


            test_df = pd.DataFrame()
            test_df["slope"] = trend_df["price"] 
            test_df["high"] = tmp["open"][start_index:end_index]
            test_df["low"] = tmp["close"][start_index:end_index]

            test_df = test_df.reset_index(drop=True)

            slope_percentage = 0
            slope_count = 0
            for i in range(0, len(test_df["slope"])):
                if test_df["low"][i] < test_df["slope"][i] < test_df["high"][i]:
                    slope_count += 1
                else:
                    pass
            trade_flags["slope_matching"] = (slope_count / len(test_df["slope"]))*100





        if (up_count == down_count):
            pass
        elif (length == up_count) and trend_diff > 0.2 and trade_flags["slope_matching"] > 30:
        #if trend_diff > 0.3:
            if trade_flags["direction"] == "buy":
                pass
            elif trade_flags["direction"] == "sell":
                trade_flags = reset_trade_flags()
                trade_flags["direction"] = "buy"
                trade_flags["direction_time"] = insert_time
                trade_flags["diff"] = trend_diff
                    
            else:
                trade_flags["direction"] = "buy"
                trade_flags["direction_time"] = insert_time
                trade_flags["diff"] = trend_diff

        elif (length == down_count) and trend_diff < -0.3 and trade_flags["slope_matching"] > 30:
        #elif trend_diff < -0.3:
            if trade_flags["direction"] == "sell":
                pass
            elif trade_flags["direction"] == "buy":
                trade_flags = reset_trade_flags()
                trade_flags["direction"] = "sell"
                trade_flags["direction_time"] = insert_time
                trade_flags["diff"] = trend_diff
            else:
                trade_flags["direction"] = "sell"
                trade_flags["direction_time"] = insert_time
                trade_flags["diff"] = trend_diff

        if trade_flags["direction"] != "flat":
            trace_logger.info("%s: Direction=%s" % (insert_time, trade_flags["direction"]))
                

        # トレンドが出ている場合、ema25にタッチしたことを確認する
        if trade_flags["direction"] != "flat":
            # Dummy
            # ema25 = current_ema_df["ema25"].values[0]
            # trade_flags["touched_ema"] = True
            # trade_flags["touched_ema_time"] = insert_time

            threshold = 0.05
            ema25 = current_ema_df["ema25"].values[0]
            high_price = price_df["high"].tail(1).values[-1]
            low_price = price_df["low"].tail(1).values[-1]

            if trade_flags["direction"] == "buy" and low_price < ema25:
                trade_flags["touched_ema"] = True
            elif trade_flags["direction"] == "sell" and high_price < ema25:
                trade_flags["touched_ema"] = True
            if trade_flags["touched_ema"]:
                trade_flags["touched_ema_time"] = insert_time
            if trade_flags["touched_ema"]:
                trace_logger.info("%s: TouhcedEMA=True" % (insert_time))


        if trade_flags["direction"] != "flat" and trade_flags["touched_ema"]:
            open_prices = price_df["open"].tail(2).values
            close_prices = price_df["close"].tail(2).values
            high_prices = price_df["high"].tail(2).values
            low_prices = price_df["low"].tail(2).values

            barbwire_df = price_df.tail(1).reset_index(drop=True)
            barbwire_status = barbwire(barbwire_df)


            threshold = 0.05
            diff = abs(ema25 - current_price)

            if trade_flags["direction"] == "buy":
                # 最初の足が陰線
                if open_prices[0] > close_prices[0]:
                    # 最初の足より安値をつけること。最初の足より高値で終わること
                    # if low_prices[0] > low_prices[1] and (close_prices[0] < close_prices[1] or barbwire(barbwire_df)["status"] or open_prices[1] < close_prices[1]):
                    if low_prices[0] > low_prices[1] and barbwire_status["status"] and barbwire_status["direction"] == "buy":
                        trade_flags["position"] = True

            elif trade_flags["direction"] == "sell":
                # 最初の足が陽線
                if open_prices[0] < close_prices[0]:
                    # 最初の足より高値をつけること。最初の足より安値で終わること
                    # if high_prices[0] < high_prices[1] and (close_prices[0] > close_prices[1] or barbwire(barbwire_df)["status"] or open_prices[1] > close_prices[1]):
                    if high_prices[0] < high_prices[1] and barbwire_status["status"] and barbwire_status["direction"] == "sell":
                        trade_flags["position"] = True
                

                    
            if trade_flags["position"]:
                if trade_flags["direction"] == "buy":
                    trade_flags["position_price"] = current_ask
                else:
                    trade_flags["position_price"] = current_bid
    
                trade_flags["start_time"] = insert_time
                trade_flags["long_trend"] = long_trend_fin_df
                trade_flags["short_trend"] = short_trend_fin_df
                trade_flags["ema"] = ema
                trade_flags["registance_line"] = registance_line
                trade_flags["support_line"] = support_line
            else:
                trade_flags["price_action_count"] += 1

            # 1時間以上たったらリセットする
            if trade_flags["price_action_count"] >= 12:
                trade_flags = reset_trade_flags()

 

        #if trade_flags["direction"] != "flat" and trade_flags["touched_ema"]:
        #    open_prices = price_df["open"].tail(3).values
        #    close_prices = price_df["close"].tail(3).values
        #    high_prices = price_df["high"].tail(3).values
        #    low_prices = price_df["low"].tail(3).values

        #    barbwire_df = price_df.tail(2).reset_index(drop=True)


        #    threshold = 0.05
        #    diff = abs(ema25 - current_price)

        #    if diff < threshold:
        #        if trade_flags["direction"] == "buy":
        #            # 最初の足が陰線
        #            if open_prices[0] > close_prices[0]:
        #                # 最初の足より安値をつけること。最初の足より高値で終わること
        #                if low_prices[0] > low_prices[1] and (close_prices[0] < close_prices[1] or barbwire(barbwire_df)["status"]):
        #                    # 中間の足より高値で終わること
        #                    if high_prices[1] < close_prices[2]:
        #                        trade_flags["position"] = True
        #                        # 中間足の安値以下になったら損切
        #                        trade_flags["stop_rate"] = low_prices[1]

        #        elif trade_flags["direction"] == "sell":
        #            # 最初の足が陽線
        #            if open_prices[0] < close_prices[0]:
        #                # 最初の足より高値をつけること。最初の足より安値で終わること
        #                if high_prices[0] < high_prices[1] and (close_prices[0] > close_prices[1] or barbwire(barbwire_df)["status"]):
        #                    # 中間の足より安値で終わること
        #                    if low_prices[1] > close_prices[2]:
        #                        trade_flags["position"] = True
        #                        # 中間足の高値以上になったら損切
        #                        trade_flags["stop_rate"] = high_prices[1]
        #    else:
        #        trade_flags = reset_trade_flags()
        #        

        #            
        #    if trade_flags["position"]:
        #        if trade_flags["direction"] == "buy":
        #            trade_flags["position_price"] = current_ask
        #        else:
        #            trade_flags["position_price"] = current_bid
    
        #        trade_flags["start_time"] = insert_time
        #        trade_flags["long_trend"] = long_trend_fin_df
        #        trade_flags["short_trend"] = short_trend_fin_df
        #        trade_flags["ema"] = ema
        #        trade_flags["registance_line"] = registance_line
        #        trade_flags["support_line"] = support_line
        #    else:
        #        trade_flags["price_action_count"] += 1

        #    # 1時間以上たったらリセットする
        #    if trade_flags["price_action_count"] >= 12:
        #        trade_flags = reset_trade_flags()

                        
    elif trade_flags["position"]:
        profit = 0.3
        stoploss = 0.2

        if trade_flags["direction"] == "buy":
            if trade_flags["position_price"] + profit < current_bid:
                print("PROFIT BUY")
                print(trade_flags["position_price"]+profit)
                trade_flags["end_time"] = insert_time
                trade_flags["stl_price"] = current_bid
                trade_flags["stl"] = True

            #elif trade_flags["position_price"] - stoploss > current_bid or trade_flags["stop_rate"] > current_bid:
            elif trade_flags["position_price"] - stoploss > current_bid:
                print("STOPLOSS BUY")
                print(trade_flags["position_price"]-stoploss)
                trade_flags["end_time"] = insert_time
                trade_flags["stl_price"] = current_bid
                trade_flags["stl"] = True
        else:
            if trade_flags["position_price"] - profit > current_ask:
                print("PROFIT SELL")
                print(trade_flags["position_price"]-profit)
                trade_flags["end_time"] = insert_time
                trade_flags["stl_price"] = current_ask
                trade_flags["stl"] = True

            #elif trade_flags["position_price"] + stoploss < current_ask or trade_flags["stop_rate"] < current_ask:
            elif trade_flags["position_price"] + stoploss < current_ask:
                print("STOPLOSS SELL")
                print(trade_flags["position_price"]+stoploss)
                trade_flags["end_time"] = insert_time
                trade_flags["stl_price"] = current_ask
                trade_flags["stl"] = True

    return trade_flags


if __name__ == "__main__":
#    subprocess.getoutput("rm -f images/*.png")
#    subprocess.getoutput("rm -f results/*.png")

    trade_flags = reset_trade_flags()

    if mode != "test":
        insert_time = datetime.now()
        insert_time = insert_time - timedelta(minutes=(insert_time.minute % 5))
        diff = 30 - insert_time.second
        insert_time = insert_time + timedelta(seconds=diff)


    print(mode)
    print(insert_time)
    while True:
        now = datetime.now()
        trace_logger.info(insert_time.strftime("%Y-%m-%d %H:%M:%S"))
        if insert_time < now: 
            trade_flags = decide_trade(trade_flags, insert_time)

            if trade_flags["position"] == True and trade_flags["position"] != "done":
                if mode == "test":
                    pass
                else:
                    response = oanda.order(trade_flags["direction"], instrument, 0.5, 0.5)

                trade_flags["position"] = "done"

            elif trade_flags["stl"]:
                if mode == "test":
                    pass
                else:
                    response = oanda.close_trade(instrument)
                plot_result(trade_flags)

                debug_logger.info("=====================")
                debug_logger.info("Direction_time=%s" % trade_flags["direction_time"])
                debug_logger.info("Direction_slope=%s" % trade_flags["slope"])
                debug_logger.info("Direction_diff=%s" % trade_flags["diff"])
                debug_logger.info("Candle_length=%s" % trade_flags["candle_length"])
                debug_logger.info("Slope_matching=%s" % trade_flags["slope_matching"])
                debug_logger.info("Touched_EMA_time=%s" % trade_flags["touched_ema_time"])
                debug_logger.info("Ordered_time=%s" % trade_flags["start_time"])
                debug_logger.info("Ordered_price=%s" % trade_flags["position_price"])
                debug_logger.info("Ordered_side=%s" % trade_flags["direction"])
                debug_logger.info("Stled_time=%s" % trade_flags["end_time"])
                debug_logger.info("Stled_price=%s" % trade_flags["stl_price"])
                if trade_flags["direction"] == "buy":
                    debug_logger.info("Profit=%s" % (trade_flags["stl_price"]-trade_flags["position_price"]))
                else:
                    debug_logger.info("Profit=%s" % (trade_flags["position_price"]-trade_flags["stl_price"]))

                insert_time = insert_time - timedelta(minutes=(insert_time.minute % 5))
                diff = 30 - insert_time.second
                insert_time = insert_time + timedelta(seconds=diff)

                trade_flags = reset_trade_flags()



            if insert_time > end_time and mode == "test":
                break

            # ポジションがない && トレード時間じゃない場合は早める
            if decide_tradetime(insert_time) == False and trade_flags["position"] == False:
                insert_time = insert_time + timedelta(minutes=15)
            elif trade_flags["position"]:
                insert_time = insert_time + timedelta(seconds=5)
            else:
                insert_time = insert_time + timedelta(minutes=5)

        else:
            time.sleep(1)
