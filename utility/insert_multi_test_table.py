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
from oandapy import oandapy
from price_obj import PriceObj
from datetime import datetime, timedelta
from common import decideMarket, account_init, iso_jp, jp_utc
from get_indicator import getBollingerWrapper
import time

account_data = account_init("production", current_path)
account_id = account_data["account_id"]
token = account_data["token"]
env = account_data["env"]

oanda = oandapy.API(environment=env, access_token=token)
 
# python insert_multi_table.py instrument table_type mode

def insert_table(base_time, currency, con, table_type):
    count=5000
    if table_type == "1m":
        granularity = "M1"
    elif table_type == "5m":
        granularity = "M5"
    elif table_type == "1h":
        granularity = "H1"
    elif table_type == "3h":
        granularity = "H3"
    elif table_type == "8h":
        granularity = "H8"
    elif table_type == "day":
        granularity = "D"

    start_time = base_time.strftime("%Y-%m-%d %H:%M:%S")
    start_time = jp_utc(start_time)
    start_time = start_time.strftime("%Y-%m-%dT%H:%M:%S")
    response = oanda.get_history(
        instrument=currency,
        start=start_time,
        granularity=granularity,
        count=count
    )

    for candle in response["candles"]:
        open_ask_price = candle["openAsk"]
        open_bid_price = candle["openBid"]
        close_ask_price = candle["closeAsk"]
        close_bid_price = candle["closeBid"]
        high_ask_price = candle["highAsk"]
        high_bid_price = candle["highBid"]
        low_ask_price = candle["lowAsk"]
        low_bid_price = candle["lowBid"]
        insert_time = candle["time"]
        insert_time = iso_jp(insert_time)
        insert_time = insert_time.strftime("%Y-%m-%d %H:%M:%S")

        sql = "insert into %s_%s_TABLE(open_ask, open_bid, close_ask, close_bid, high_ask, high_bid, low_ask, low_bid, insert_time) values(%s, %s, %s, %s, %s, %s, %s, %s, \'%s\')" % (currency, table_type, open_ask_price, open_bid_price, close_ask_price, close_bid_price, high_ask_price, high_bid_price, low_ask_price, low_bid_price, insert_time)
        print(sql)
        try:
            con.insert_sql(sql)

        except Exception as e:
            print(e.args)

    return insert_time


if __name__ == "__main__":
    args = sys.argv
    currency = args[1].strip()
    table_type = args[2].strip()
    con = MysqlConnector()
    base_time = "2018-10-01 00:00:00"
    base_time = datetime.strptime(base_time, "%Y-%m-%d %H:%M:%S")
    end_time = "2018-10-21 00:00:00"
    end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")

    while True:
        try:
            base_time = insert_table(base_time, currency, con, table_type)
            print(base_time)

            if type(base_time) is str:
                base_time = datetime.strptime(base_time, "%Y-%m-%d %H:%M:%S")
            if base_time > end_time:
                break

        except Exception as e:
            print(e.args)
