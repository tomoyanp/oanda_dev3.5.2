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
import math
from scipy.stats import linregress

from mysql_connector import  MysqlConnector

# support & registance line
def supreg(con, instrument, table_type, start_time, end_time):
    sql = "select insert_time, open_ask, open_bid, high_ask, high_bid, low_ask, low_bid, close_ask, close_bid from %s_%s_TABLE where '%s' < insert_time and insert_time < '%s'" % (instrument, table_type, start_time, end_time)
    res = con.select_sql(sql)

    lst = []
    for r in res:
        lst.append(list(r))


    df = pd.DataFrame(lst)
    insert_time = df[0]
    op_price = ((df[1] + df[2])/2).values
    hi_price = ((df[3] + df[4])/2).values
    lw_price = ((df[5] + df[6])/2).values
    cl_price = ((df[7] + df[8])/2).values

    supreg_list = []
    threshold = 0.025

    for i in range(len(op_price)):
        flag = False
        for n in range(len(supreg_list)):
            if supreg_list[n]["direction"] == "high":
                if math.sqrt((supreg_list[n]["price"] - hi_price[i])**2) < threshold:
                    supreg_list[n]["count"] += 1
                    # supreg_list[n]["price"] = (supreg_list[n]["price"]+hi_price[i])/2
                    flag = True
            if supreg_list[n]["direction"] == "low":
                if math.sqrt((supreg_list[n]["price"] - lw_price[i])**2) < threshold:
                    supreg_list[n]["count"] += 1
                    # supreg_list[n]["price"] = (supreg_list[n]["price"]+lw_price[i])/2
                    flag = True

        if flag == False:
            append_high = {
                "direction": "high",
                "price": hi_price[i],
                "count": 0
            }
            append_low = {
                "direction": "low",
                "price": lw_price[i],
                "count": 0
            }
            supreg_list.append(append_high)
            supreg_list.append(append_low)

    touchdown_threshold = 5
    tmp_list = []
    for sup in supreg_list:
        if sup["count"] > touchdown_threshold:
            tmp_list.append(sup)
    supreg_list = tmp_list


    price_threshold = 0.1
    return_list = []
    for sup in supreg_list:
        flag = False
        for i in range(len(return_list)):
            if return_list[i]["direction"] == "high" and sup["direction"] == "high":
                if math.sqrt((sup["price"] - return_list[i]["price"])**2) < price_threshold:
                    price = (max([sup["price"], return_list[i]["price"]]))
                    return_list[i]["price"] = price 
                    flag = True
                    break
            elif return_list[i]["direction"] == "low" and sup["direction"] == "low":
                if math.sqrt((sup["price"] - return_list[i]["price"])**2) < price_threshold:
                    price = (min([sup["price"], return_list[i]["price"]]))
                    return_list[i]["price"] = price 
                    flag = True
                    break
        if flag == False:
            return_list.append(sup)
    print(len(supreg_list))
    print(len(return_list))

    #for elm in supreg_list:
    #    if elm["count"] > touchdown_threshold:
    #        return_list.append(elm)

    return return_list


def trend_line(con, instrument, table_type, start_time, end_time):
    sql = "select insert_time, open_ask, open_bid, high_ask, high_bid, low_ask, low_bid, close_ask, close_bid from %s_%s_TABLE where '%s' < insert_time and insert_time < '%s'" % (instrument, table_type, start_time, end_time)
    res = con.select_sql(sql)

    lst = []
    id_list = []
    index = 1
    for r in res:
        lst.append(list(r))
        id_list.append(index)
        index += 1
        


    df = pd.DataFrame(lst)
    insert_time = df[0]
    op_price = ((df[1] + df[2])/2).values
    hi_price = ((df[3] + df[4])/2).values
    lw_price = ((df[5] + df[6])/2).values
    cl_price = ((df[7] + df[8])/2).values

    df = pd.DataFrame()
    df["high"] = hi_price
    df["low"] = lw_price
    df["open"] = op_price
    df["close"] = cl_price
    df["time_id"] = id_list

    df_fin = df.copy()

    while len(df["high"])>3:
        reg_1 = linregress(
            x = df["time_id"],
            y = df["high"],
        )
        df = df.loc[df["high"] > reg_1[0] * df["time_id"] + reg_1[1]]

    reg_1 = linregress(
        x = df["time_id"],
        y = df["high"]
    )

    df_fin["high_trend"] = reg_1[0] * df_fin["time_id"] + reg_1[1]
    print(df_fin)

    return df_fin

if __name__ == "__main__":
    con = MysqlConnector()
    table_type = "5m"
    start_time = "2019-07-16 20:00:00"
    end_time = "2019-07-17 00:00:00"
    instrument = "GBP_JPY"
    supreg(con, instrument, table_type, start_time, end_time)
