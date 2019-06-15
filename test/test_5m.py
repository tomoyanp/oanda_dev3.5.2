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
insert_time = '2019-06-13 14:00:00'
insert_time = datetime.strptime(insert_time, "%Y-%m-%d %H:%M:%S")
now = datetime.now()

while insert_time < now:
    result_list = []
    for instrument in instrument_list:
        sql = "select open_ask, open_bid, close_ask, close_bid, insert_time from %s_30m_TABLE where insert_time < '%s' order by insert_time desc limit 1" % (instrument, insert_time)
        response = con.select_sql(sql)
    
    
        open_price = (response[0][0]+response[0][1])/2
        close_price = (response[0][2]+response[0][3])/2
        result = close_price/open_price
        res_insert_time = response[0][4]
        result_list.append(result)
    
#        print("%s : %s = %s" % (res_insert_time, instrument, result))
#        print("========================================")
    
    
    if result_list[0] > 1.0 and result_list[1] > 1.0 and result_list[2] > 1.0 and result_list[5] > 1.0:
        print("%s: EUR_JPY buy" % insert_time)
    if result_list[0] > 1.0 and result_list[1] > 1.0 and result_list[2] > 1.0 and result_list[5] < 1.0:
        print("%s: EUR_USD buy" % insert_time)
    if result_list[0] < 1.0 and result_list[3] > 1.0 and result_list[4] > 1.0 and result_list[5] > 1.0:
        print("%s: GBP_JPY buy" % insert_time)
    if result_list[0] < 1.0 and result_list[3] > 1.0 and result_list[4] > 1.0 and result_list[5] < 1.0:
        print("%s: GBP_USD buy" % insert_time)

    insert_time = insert_time + timedelta(minutes=30)
