# coding: utf-8

import sys
import os
import traceback
import json

# 実行スクリプトのパスを取得して、追加
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path)

from mysql_connector import MysqlConnector
from datetime import datetime, timedelta
import oanda_wrapper
import re

from logging import getLogger, FileHandler, DEBUG

debug_logfilename = "%s.log" % datetime.now().strftime("%Y%m%d%H%M%S")
debug_logger = getLogger("debug")
debug_fh = FileHandler(debug_logfilename, "a+")
debug_logger.addHandler(debug_fh)
debug_logger.setLevel(DEBUG)

con = MysqlConnector()

instrument_list = ["EUR_GBP", "EUR_USD", "EUR_JPY", "GBP_USD", "GBP_JPY", "USD_JPY"]
#instrument_list = ["EUR_USD", "EUR_JPY", "GBP_USD", "GBP_JPY", "USD_JPY"]
insert_time = '2019-06-18 16:59:00'
insert_time = datetime.strptime(insert_time, "%Y-%m-%d %H:%M:%S")
now = datetime.now()

mode = sys.argv[1]

def decide_trade(length, insert_time, description):
    result_list = []
    insert_time = insert_time - timedelta(seconds=5)

    for instrument in instrument_list:
        sql = "select open_ask, open_bid, close_ask, close_bid, insert_time from %s_5s_TABLE where insert_time <= '%s' order by insert_time desc limit %s" % (instrument, insert_time, length)
        response = con.select_sql(sql)
    
    
        open_price = (response[-1][2]+response[-1][3])/2
        close_price = (response[0][2]+response[0][3])/2
        result = (close_price/open_price - 1.0) * 10000
        start_time = response[-1][4]
        end_time = response[0][4]
        result_list.append(result)
    
        #print("%s - %s : %s = %s" % (start_time, end_time, instrument, result))
        #print("========================================")
    
    value = {}
    
    # instrument_list = ["EUR_GBP", "EUR_USD", "EUR_JPY", "GBP_USD", "GBP_JPY", "USD_JPY"]
    if result_list[0] > 0.0 and result_list[1] > 0.0 and result_list[2] > 0.0 and result_list[5] > 0.0:
        value["currency"] = "EUR_JPY"
        value["key"] = "buy"
    if result_list[0] > 0.0 and result_list[1] > 0.0 and result_list[2] > 0.0 and result_list[5] < 0.0:
        value["currency"] = "EUR_USD"
        value["key"] = "buy"
    if result_list[0] < 0.0 and result_list[3] > 0.0 and result_list[4] > 0.0 and result_list[5] > 0.0:
        value["currency"] = "GBP_JPY"
        value["key"] = "buy"
    if result_list[0] < 0.0 and result_list[3] > 0.0 and result_list[4] > 0.0 and result_list[5] < 0.0:
        value["currency"] = "GBP_USD"
        value["key"] = "buy"


    if result_list[0] < 0.0 and result_list[1] < 0.0 and result_list[2] < 0.0 and result_list[5] < 0.0:
        value["currency"] = "EUR_JPY"
        value["key"] = "sell"
    if result_list[0] < 0.0 and result_list[1] < 0.0 and result_list[2] < 0.0 and result_list[5] > 0.0:
        value["currency"] = "EUR_USD"
        value["key"] = "sell"
    if result_list[0] > 0.0 and result_list[3] < 0.0 and result_list[4] < 0.0 and result_list[5] < 0.0:
        value["currency"] = "GBP_JPY"
        value["key"] = "sell"
    if result_list[0] > 0.0 and result_list[3] < 0.0 and result_list[4] < 0.0 and result_list[5] > 0.0:
        value["currency"] = "GBP_USD"
        value["key"] = "sell"

    value["description"] = description
    return value

def trade(insert_time, instrument, trade_side):
    insert_time = insert_time - timedelta(seconds=5)

    sql = "select close_ask, close_bid from %s_5s_TABLE where insert_time < '%s' order by insert_time desc limit 1" % (instrument, insert_time)
    response = con.select_sql(sql)

    price = (response[0][0]+response[0][1])/2

    return price, instrument, trade_side

def stl(insert_time, trade_obj, profit_rate, orderstop_rate):
    insert_time = insert_time - timedelta(seconds=5)
    sql = "select close_ask, close_bid from %s_5s_TABLE where insert_time < '%s' order by insert_time desc limit 1" % (trade_obj["instrument"], insert_time)
    response = con.select_sql(sql)

    coefficient = 0
    if re.search("JPY", trade_obj["instrument"]) != None:
        coefficient = 100
    else:
        coefficient = 10000

    price = (response[0][0]+response[0][1])/2

    stl_flag = False
    if trade_obj["side"] == "buy":
        # ここの計算おかしいからちゃんと調べる
        # pips = (price/trade_obj["price"] - 1.0) * 10000
        pips = (price - trade_obj["price"])*coefficient
    elif trade_obj["side"] == "sell":
        # ここの計算おかしいからちゃんと調べる
        # pips = (trade_obj["price"]/price - 1.0) * 10000
        pips = (trade_obj["price"]-price)*coefficient
    else:
        raise

    if pips > profit_rate:
        stl_flag = True
    elif pips < orderstop_rate:
        stl_flag = True

    profit = 0
    if stl_flag:
        if trade_obj["side"] == "buy":
            profit = price - trade_obj["price"]
        elif trade_obj["side"] == "sell":
            profit = trade_obj["price"] - price

    return stl_flag, insert_time, price, profit


if __name__ == "__main__":
    trade_account = {
        "accountId": "101-009-10684893-001",
        "accessToken": "d6fa56ee0ced50ea925683cb9c316df1-8daba3977f5335ed52327c5cc54ebf5a",
        "env": "practice"
    }

    trade_obj = {"flag": False}
    profit_rate = 10
    orderstop_rate = -5

    if mode == "demo":
        insert_time = now

    while True:
        if insert_time > now and mode == "test":
            break
        elif mode == "demo":
            insert_time = datetime.now()
        else:
            insert_time = insert_time + timedelta(seconds=5)

        print("%s" % insert_time)
        if trade_obj["flag"] == False:
            length = 2
            value5s = decide_trade(length, insert_time, "5 seconds")

            length = 12
            value1m = decide_trade(length, insert_time, "1 minutes")

            length = 12 * 5
            value5m = decide_trade(length, insert_time, "5 minutes")

            length = 12 * 60
            value1h = decide_trade(length, insert_time, "1 hour")

            if len(value5s) > 1 and len(value1m) > 1 and len(value5m) > 1 and len(value1h) > 1:
                if value5s["key"] == value1m["key"] == value5m["key"] == value1h["key"] and value5s["currency"] == value1m["currency"] == value5m["currency"] == value1h["currency"]:
                    debug_logger.info("TRADE %s: %s %s" % (insert_time, value5s["currency"], value5s["key"]))
                    price, instrument, trade_side = trade(insert_time, value5s["currency"], value5s["key"])
                    trade_obj["flag"] = True
                    trade_obj["instrument"] = instrument
                    trade_obj["price"] = price
                    trade_obj["side"] = trade_side
                    trade_obj["trade_time"] = insert_time

                    if mode != "test":
                        units = oanda_wrapper.calc_unit(trade_account, instrument, con)
                        units = 100000
                        response = oanda_wrapper.open_order(trade_account, instrument, trade_side, units, 0, 0)
                        print(response)
                    

        if trade_obj["flag"]:
            stl_flag, stl_time, price, profit = stl(insert_time, trade_obj, profit_rate, orderstop_rate)
            if stl_flag:
                debug_logger.info("SETTLE %s %s - %s: %s - %s, %s %s" % (trade_obj["instrument"], trade_obj["trade_time"], stl_time, trade_obj["price"], price, trade_obj["side"], profit))
                trade_obj = {"flag": False}

                if mode != "test":
                    response = oanda_wrapper.close_position(trade_account)
                    print(response)


