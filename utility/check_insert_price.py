# coding: utf-8

# 実行スクリプトのパスを取得して、追加
import sys
import os
current_path = os.path.abspath(os.path.dirname(__file__))
current_path = current_path + "/.."
sys.path.append(current_path)
sys.path.append(current_path + "/trade_algorithm")
sys.path.append(current_path + "/obj")
sys.path.append(current_path + "/lib")

from mysql_connector import MysqlConnector
from oanda_wrapper import OandaWrapper
from price_obj import PriceObj
from datetime import datetime, timedelta
from common import decideMarket
from send_mail import SendMail
import time

import traceback


# if check value is empty, insert record before 1 seconds
def follow_record(con, base_time, currency):
    base_time_bef = base_time - timedelta(seconds=1)
    sql = "select ask_price, bid_price from %s_TABLE where insert_time = \'%s\'" % (currency, base_time_bef.strftime("%Y-%m-%d %H:%M:%S"))
    response = con.select_sql(sql)

    ask_price = response[0][0]
    bid_price = response[0][1]

    sql = "insert into %s_TABLE (ask_price, bid_price, insert_time) values (%s, %s, \'%s\')" % (currency, ask_price, bid_price, base_time.strftime("%Y-%m-%d %H:%M:%S"))
    con.insert_sql(sql)

if __name__ == "__main__":
    args = sys.argv
    currency = args[1].strip()
    con = MysqlConnector()

    now = datetime.now()
    base_time = now
    base_time = now - timedelta(days=5)

    # for TEST
#    base_time = datetime.strptime("2018-05-18 13:38:29", "%Y-%m-%d %H:%M:%S")
#    base_time = datetime.strptime("2018-05-18 13:38:29", "%Y-%m-%d %H:%M:%S")

    try:
        while True:
            flag = decideMarket(base_time)

            now = datetime.now()
            tmp_time = now - timedelta(seconds=10)
            if tmp_time < base_time:
                flag = False
                time.sleep(10)
            else:
                base_time = base_time + timedelta(seconds=1)


            if flag == False:
                pass
            else:
                sql = u"select insert_time from %s_TABLE where insert_time = \'%s\'" % (currency, base_time.strftime("%Y-%m-%d %H:%M:%S"))
                print(sql)
                response = con.select_sql(sql)
                print(response)
                print(len(response))
                if len(response) == 0:
                    follow_record(con, base_time, currency)
                else:
                    pass

    except Exception as e:
        message = "*** insert_check.py %s is Failed ***\n" % currency
        print(traceback.format_exc())
        print(message)
