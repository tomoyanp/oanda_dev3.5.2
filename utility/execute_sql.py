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

property_path = current_path + "/property"
config_path = current_path + "/config"

from mysql_connector import MysqlConnector

sql = "show tables"
con = MysqlConnector()
response = con.select_sql(sql)


for table in response:
    #sql = "truncate table %s" % table[0]
    sql = "select insert_time from %s order by insert_time desc limit 1" % table[0]
    response = con.select_sql(sql)
    if len(response) != 0:
        print("%s -----> %s" % (table[0], response[0][0]))
    else:
        print("%s -----> No Data" % (table[0]))
