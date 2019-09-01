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

    for elm in supreg_list:
        if elm["count"] > 5:
            print(elm)

if __name__ == "__main__":
    con = MysqlConnector()
    table_type = "5m"
    start_time = "2019-07-16 20:00:00"
    end_time = "2019-07-17 00:00:00"
    instrument = "GBP_JPY"
    supreg(con, instrument, table_type, start_time, end_time)
