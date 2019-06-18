# coding: utf-8

import sys
import os
import traceback
import json

# 実行スクリプトのパスを取得して、追加
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path)
sys.path.append(current_path + "/../trade_algorithm")
sys.path.append(current_path + "/../obj")
sys.path.append(current_path + "/../lib")
sys.path.append(current_path + "/../lstm_lib")

from mysql_connector import MysqlConnector
from datetime import datetime, timedelta

con = MysqlConnector()

instrument_list = ["EUR_GBP", "EUR_USD", "EUR_JPY", "GBP_USD", "GBP_JPY", "USD_JPY"]
#instrument_list = ["EUR_USD", "EUR_JPY", "GBP_USD", "GBP_JPY", "USD_JPY"]
insert_time = '2019-06-18 16:59:00'
insert_time = datetime.strptime(insert_time, "%Y-%m-%d %H:%M:%S")
now = datetime.now()

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
        value["currency"] = "EUS_USD"
        value["key"] = "sell"
    if result_list[0] > 0.0 and result_list[3] < 0.0 and result_list[4] < 0.0 and result_list[5] < 0.0:
        value["currency"] = "GBP_JPY"
        value["key"] = "sell"
    if result_list[0] > 0.0 and result_list[3] < 0.0 and result_list[4] < 0.0 and result_list[5] > 0.0:
        value["currency"] = "GBP_USD"
        value["key"] = "sell"

    value["description"] = description
    return value

while insert_time < now:
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
            print("%s: %s %s" % (insert_time, value5s["currency"], value5s["key"]))

    insert_time = insert_time + timedelta(seconds=5)



