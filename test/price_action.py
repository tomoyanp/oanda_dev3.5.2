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
import numpy as np
import math
from scipy.stats import linregress

from mysql_connector import  MysqlConnector

def supreg(low, high, n, min_touches, stat_likeness_percent, bounce_percent):
    df = pd.concat([high, low], keys = ['high', 'low'], axis=1)
    df['sup'] = pd.Series(np.zeros(len(low)))
    df['res'] = pd.Series(np.zeros(len(low)))
    df['sup_break'] = pd.Series(np.zeros(len(low)))
    df['sup_break'] = 0
    df['res_break'] = pd.Series(np.zeros(len(high)))
    df['res_break'] = 0
    
    for x in range((n-1)+n, len(df)):
        tempdf = df[x-n:x+1].copy()
        sup = None
        res = None
        maxima = tempdf.high.max()
        minima = tempdf.low.min()
        move_range = maxima - minima
        move_allowance = move_range * (stat_likeness_percent / 100)
        bounce_distance = move_range * (bounce_percent / 100)
        touchdown = 0
        awaiting_bounce = False
        for y in range(0, len(tempdf)):
            if abs(maxima - tempdf.high.iloc[y]) < move_allowance and not awaiting_bounce:
                touchdown = touchdown + 1
                awaiting_bounce = True
            elif abs(maxima - tempdf.high.iloc[y]) > bounce_distance:
                awaiting_bounce = False
        if touchdown >= min_touches:
            res = maxima
 
        touchdown = 0
        awaiting_bounce = False
        for y in range(0, len(tempdf)):
            if abs(tempdf.low.iloc[y] - minima) < move_allowance and not awaiting_bounce:
                touchdown = touchdown + 1
                awaiting_bounce = True
            elif abs(tempdf.low.iloc[y] - minima) > bounce_distance:
                awaiting_bounce = False
        if touchdown >= min_touches:
            sup = minima
        if sup:
            df['sup'].iloc[x] = sup
        if res:
            df['res'].iloc[x] = res
    res_break_indices = list(df[(np.isnan(df['res']) & ~np.isnan(df.shift(1)['res'])) & (df['high'] > df.shift(1)['res'])].index)
    for index in res_break_indices:
        df['res_break'].at[index] = 1
    sup_break_indices = list(df[(np.isnan(df['sup']) & ~np.isnan(df.shift(1)['sup'])) & (df['low'] < df.shift(1)['sup'])].index)
    for index in sup_break_indices:
        df['sup_break'].at[index] = 1
    ret_df = pd.concat([df['sup'], df['res'], df['sup_break'], df['res_break']], keys = ['sup', 'res', 'sup_break', 'res_break'], axis=1)
    return ret_df

# support & registance line
#def supreg(price_df):
#    # 高値、安値が近似している足同士をまとめて、より足が集中しているところをラインとする
#    supreg_list = []
#    threshold = 0.025
#
#    # ローソク足の数だけ繰り返す
#    for i in range(len(price_df["open"])):
#        flag = False
#        # サポレジリストの分だけ繰り返す
#        for n in range(len(supreg_list)):
#            # 高値の場合
#            if supreg_list[n]["direction"] == "high":
#                # リストの高値と近似している場合カウントをプラスする
#                if math.sqrt((supreg_list[n]["price"] - price_df["high"][i])**2) < threshold:
#                    supreg_list[n]["count"] += 1
#                    flag = True
#            # 安値の場合
#            if supreg_list[n]["direction"] == "low":
#                # リストの安値と近似している場合カウントをプラスする
#                if math.sqrt((supreg_list[n]["price"] - price_df["low"][i])**2) < threshold:
#                    supreg_list[n]["count"] += 1
#                    flag = True
#
#        # サポレジリスト内と近似しない場合はサポレジリストに追加する
#        if flag == False:
#            append_high = {
#                "direction": "high",
#                "price": price_df["high"][i],
#                "count": 0
#            }
#            append_low = {
#                "direction": "low",
#                "price": price_df["low"][i],
#                "count": 0
#            }
#            supreg_list.append(append_high)
#            supreg_list.append(append_low)
#
#    # 近似しているcount数が閾値以上のものだけサポレジリストとする
#    touchdown_threshold = 5
#    tmp_list = []
#    for sup in supreg_list:
#        if sup["count"] > touchdown_threshold:
#            tmp_list.append(sup)
#    supreg_list = tmp_list
#
#
#    # サポレジリストの中でもさらに近似しているものをまとめる
#    price_threshold = 0.2
#    return_list = []
#    for sup in supreg_list:
#        flag = False
#        for i in range(len(return_list)):
#            if return_list[i]["direction"] == "high" and sup["direction"] == "high":
#                if math.sqrt((sup["price"] - return_list[i]["price"])**2) < price_threshold:
#                    price = (max([sup["price"], return_list[i]["price"]]))
#                    return_list[i]["price"] = price 
#                    flag = True
#                    break
#            elif return_list[i]["direction"] == "low" and sup["direction"] == "low":
#                if math.sqrt((sup["price"] - return_list[i]["price"])**2) < price_threshold:
#                    price = (min([sup["price"], return_list[i]["price"]]))
#                    return_list[i]["price"] = price 
#                    flag = True
#                    break
#        if flag == False:
#            return_list.append(sup)
#
#    return return_list


def trend_line(price_df):
    id_list = []
    for index in range(1, len(price_df["open"])+1):
        id_list.append(index)

    price_df["time_id"] = id_list

    df_high = price_df.copy()
    df_low = price_df.copy()

    # 安値トレンドの計算
    # 安値で回帰分析をして、回帰分析ラインを下回るものだけ残していく
    while len(df_low["low"])>2:
        reg_low = linregress(
            x = df_low["time_id"],
            y = df_low["low"],
        )
        tmp_df = df_low.loc[df_low["low"] < reg_low[0] * df_low["time_id"] + reg_low[1]]
        if len(tmp_df) < 2:
            break
        else:
            df_low = tmp_df

    reg_low = linregress(
        x = df_low["time_id"],
        y = df_low["low"]
    )

    # 高値トレンドの計算
    # 高値で回帰分析をして、回帰分析ラインを上回るものだけ残していく
    while len(df_high["high"])>2:
        reg_high = linregress(
            x = df_high["time_id"],
            y = df_high["high"],
        )
        tmp_df = df_high.loc[df_high["high"] > reg_high[0] * df_high["time_id"] + reg_high[1]]
        if len(tmp_df) < 2:
            break
        else:
            df_high = tmp_df

    reg_high = linregress(
        x = df_high["time_id"],
        y = df_high["high"]
    )

    df_fin = pd.DataFrame()
    df_fin["low_trend"] = reg_low[0] * price_df["time_id"] + reg_low[1]
    df_fin["low_slope"] = reg_low[0]
    df_fin["low_intercept"] = reg_low[1]

    df_fin["high_trend"] = reg_high[0] * price_df["time_id"] + reg_high[1]
    df_fin["high_slope"] = reg_high[0]
    df_fin["high_intercept"] = reg_high[1]
    df_fin["insert_time"] = price_df["insert_time"]

    return df_fin

# つつみ足
def outside_bar(price_df):
    high_bef = price_df["high"][0]
    high_aft = price_df["high"][1]
    low_bef = price_df["low"][0]
    low_aft = price_df["low"][1]

    cl = price_df["close"][0]
    op = price_df["open"][0]

    status = {}
    if high_bef <= high_aft and  low_bef >= low_aft:
        status["status"] = True
    else:
        status["status"] = False

    if op < cl:
        status["direction"] = "buy"
    else:
        status["direction"] = "sell"

    return status

# はらみ足
def inside_bar(price_df):
    high_bef = price_df["high"][0]
    high_aft = price_df["high"][1]
    low_bef = price_df["low"][0]
    low_aft = price_df["low"][1]

    cl = price_df["close"][0]
    op = price_df["open"][0]

    status = {}
    if high_bef >= high_aft and  low_bef <= low_aft:
        status["status"] = True
    else:
        status["status"] = False

    if op < cl:
        status["direction"] = "buy"
    else:
        status["direction"] = "sell"

    return status

# 同時線
def barbwire(price_df):
    cl = price_df["close"][0]
    op = price_df["open"][0]
    high = price_df["high"][0]
    low = price_df["low"][0]

    real_stick_diff = (cl - op) ** 2
    line_stick_diff = (high - low) ** 2

    barbwire_threshold = 0.1

    # 実線がひげの何割か計算
    status = {}
    if real_stick_diff / line_stick_diff < barbwire_threshold:
        status["status"] = True
    else:
        status["status"] = False

    if op < cl:
        status["direction"] = "buy"
    else:
        status["direction"] = "sell"

    return status

# 過去24時間のローソク足実線の平均
def average_real_stick(price_df):
    # 呼び出し元で作る
    length = 24 * 12

    op = price_df["open"]
    cl = price_df["close"]

    diff = cl - op

    diff = diff**2
    diff_list = []
    for elem in diff:
        diff_list.append(math.sqrt(elem))

    max_diff = max(diff_list)
    avg_diff = sum(diff_list)/len(diff_list)

    return max_diff, avg_diff

if __name__ == "__main__":
    con = MysqlConnector()
    table_type = "5m"
    start_time = "2019-07-16 20:00:00"
    end_time = "2019-07-17 00:00:00"
    instrument = "GBP_JPY"
    supreg(con, instrument, table_type, start_time, end_time)
