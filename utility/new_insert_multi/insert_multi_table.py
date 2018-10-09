# coding: utf-8

# 実行スクリプトのパスを取得して、追加
import sys
import os
current_path = os.path.abspath(os.path.dirname(__file__))
current_path = current_path + "/../.."
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
    hour = base_time.hour
    minutes = base_time.minute
    seconds = base_time.second


    if mode == "test":
        count=5000
    elif mode == "production":
        count=1

    flag = False
    if table_type == "1m":
        if seconds < 10:
            granularity = "M1"
            start_time = base_time - timedelta(minutes=1)
            flag = True
    elif table_type == "5m":
        if minutes % 5 == 0 and seconds < 10:
            granularity = "M5"
            start_time = base_time - timedelta(minutes=5)
            flag = True
    elif table_type == "1h":
        if minutes == 0 and seconds < 10:
            granularity = "H1"
            start_time = base_time - timedelta(hours=1)
            flag = True
    elif table_type == "day":
        if hour == 7 and minutes == 0 and seconds < 10:
            granularity = "D"
            start_time = base_time - timedelta(days=1)
            flag = True



    if flag:
        start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
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
            con.insert_sql(sql)

    if flag == False:
        insert_time = base_time
    else:
        insert_time = datetime.strptime(insert_time, "%Y-%m-%d %H:%M:%S")

    if flag:
        if table_type == "1m":
            if seconds < 10:
                insert_time = insert_time + timedelta(minutes=1)
        elif table_type == "5m":
            if minutes % 5 == 0 and seconds < 10:
                insert_time = insert_time + timedelta(minutes=5)
        elif table_type == "1h":
            if minutes == 0 and seconds < 10:
                insert_time = insert_time + timedelta(hours=1)
        elif table_type == "day":
            if hour == 7 and minutes == 0 and seconds < 10:
                insert_time = insert_time + timedelta(days=1)


    return insert_time


if __name__ == "__main__":
    args = sys.argv
    currency = args[1].strip()
    table_type = args[2].strip()
    mode = args[3].strip()
    con = MysqlConnector()
    polling_time = 10

    if mode == "test":
        base_time = "2008-01-01 00:00:00"
        base_time = datetime.strptime(base_time, "%Y-%m-%d %H:%M:%S")
        end_time = "2018-10-01 00:00:00"
        end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    else:
        base_time = datetime.now()
        end_time = datetime.now()

    while True:
        try:
            now = datetime.now()
#            flag = decideMarket(base_time)
            flag = True

            if flag == False:
                pass
            else:
                hour = base_time.hour
                minutes = base_time.minute
                seconds = base_time.second

                if base_time > now:
                    if mode == "test":
                        break
                    else:
                        time.sleep(polling_time)
                        base_time = base_time - timedelta(seconds=polling_time)
                else:
                    base_time = insert_table(base_time, currency, con, table_type)

            base_time = base_time + timedelta(seconds=polling_time)

            if mode == "test" and base_time > end_time:
                break

        except Exception as e:
            base_time = base_time + timedelta(seconds=polling_time)
            print(e.args)
