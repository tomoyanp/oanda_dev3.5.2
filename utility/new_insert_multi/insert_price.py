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
from oandapy import oandapy
from price_obj import PriceObj
from datetime import datetime, timedelta
from common import decideMarket, account_init, iso_jp
import time

account_data = account_init("production", current_path)
account_id = account_data["account_id"]
token = account_data["token"]
env = account_data["env"]

oanda = oandapy.API(environment=env, access_token=token)
 
if __name__ == "__main__":
    args = sys.argv
    currency = args[1].strip()
    con = MysqlConnector()
    polling_time = 0.5
    sleep_time = 3600
    units = 1000

    while True:
        try:
            now = datetime.now()
            weekday = now.weekday()
            hour = now.hour

            if weekday >= 5 and hour > 12:
                break
            else:

                response = oanda.get_prices(instruments=currency)
                parsed_prices = response["prices"][0]
                iso_time = parsed_prices["time"]
                insert_time = iso_jp(iso_time)
                insert_time = insert_time.strftime("%Y-%m-%d %H:%M:%S")

                ask_price = parsed_prices["ask"]
                bid_price = parsed_prices["bid"]

                sql = u"insert into %s_TABLE(ask_price, bid_price, insert_time) values(%s, %s, \'%s\')" % (currency, ask_price, bid_price, insert_time)
                print(sql)
                con.insert_sql(sql)

                time.sleep(polling_time)

        except Exception as e:
            print(e.args)
