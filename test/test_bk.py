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
insert_time = '2019-06-01 00:00:00'
insert_time = datetime.strptime(insert_time, "%Y-%m-%d %H:%M:%S")
now = datetime.now()

def decide_trade(table_type, insert_time):
    result_list = []
    if table_type == "5m":
        insert_time = insert_time - timedelta(minutes=5)
    elif table_type == "15m":
        insert_time = insert_time - timedelta(minutes=15)
    elif table_type == "day":
        insert_time = insert_time - timedelta(days=1)
    else:
        raise

    for instrument in instrument_list:
        sql = "select open_ask, open_bid, close_ask, close_bid, insert_time from %s_%s_TABLE where insert_time <= '%s' order by insert_time desc limit 1" % (instrument, table_type, insert_time)
        response = con.select_sql(sql)
    
    
        open_price = (response[0][0]+response[0][1])/2
        close_price = (response[0][2]+response[0][3])/2
        result = close_price/open_price
        res_insert_time = response[0][4]
        result_list.append(result)
    
        #print("%s : %s = %s" % (res_insert_time, instrument, result))
        #print("========================================")
    
    value = {}
    
    if result_list[0] > 1.0 and result_list[1] > 1.0 and result_list[2] > 1.0 and result_list[5] > 1.0:

        value["currency"] = "EUR_JPY"
        value["key"] = "buy"
    if result_list[0] > 1.0 and result_list[1] > 1.0 and result_list[2] > 1.0 and result_list[5] < 1.0:
        value["currency"] = "EUR_USD"
        value["key"] = "buy"
    if result_list[0] < 1.0 and result_list[3] > 1.0 and result_list[4] > 1.0 and result_list[5] > 1.0:
        value["currency"] = "GBP_JPY"
        value["key"] = "buy"
    if result_list[0] < 1.0 and result_list[3] > 1.0 and result_list[4] > 1.0 and result_list[5] < 1.0:
        value["currency"] = "GBP_USD"
        value["key"] = "buy"


    if result_list[0] < 1.0 and result_list[1] < 1.0 and result_list[2] < 1.0 and result_list[5] < 1.0:
        value["currency"] = "EUR_JPY"
        value["key"] = "sell"
    if result_list[0] < 1.0 and result_list[1] < 1.0 and result_list[2] < 1.0 and result_list[5] > 1.0:
        value["currency"] = "EUS_USD"
        value["key"] = "sell"
    if result_list[0] > 1.0 and result_list[3] < 1.0 and result_list[4] < 1.0 and result_list[5] < 1.0:
        value["currency"] = "GBP_JPY"
        value["key"] = "sell"
    if result_list[0] > 1.0 and result_list[3] < 1.0 and result_list[4] < 1.0 and result_list[5] > 1.0:
        value["currency"] = "GBP_USD"
        value["key"] = "sell"

    return value

while insert_time < now:
    table_type = "5m"
    value5m = decide_trade(table_type, insert_time)

    table_type = "15m"
    value15m = decide_trade(table_type, insert_time)

    table_type = "day"
    valueday = decide_trade(table_type, insert_time)


    if len(value5m) != 0 and len(value15m) != 0 and len(valueday) != 0:
        if value5m["key"] == value15m["key"] == valueday["key"] and value5m["currency"] == value15m["currency"] == valueday["currency"]:
            print("%s: %s %s" % (insert_time, value5m["currency"], value5m["key"]))

    insert_time = insert_time + timedelta(minutes=5)



