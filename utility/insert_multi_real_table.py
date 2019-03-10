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
from price_obj import PriceObj
from datetime import datetime, timedelta
from common import decideMarket, account_init, iso_jp, jp_utc
from get_indicator import getBollingerWrapper
import time

account_data = account_init("production", current_path)
account_id = account_data["account_id"]
token = account_data["token"]
env = account_data["env"]
import oandapyV20
import oandapyV20.endpoints.instruments as instruments

client = oandapyV20.API(access_token=token, environment=env)
 
# python insert_multi_table.py instrument table_type mode

def check_table(base_time, instrument, con, table_type):
    if table_type == "1m":
        base_time = base_time - timedelta(minutes=1)
    elif table_type == "5m":
        base_time = base_time - timedelta(minutes=5)
    elif table_type == "1h":
        base_time = base_time - timedelta(hours=1)
    elif table_type == "3h":
        base_time = base_time - timedelta(hours=3)
    elif table_type == "8h":
        base_time = base_time - timedelta(hours=8)
    elif table_type == "day":
        base_time = base_time - timedelta(days=1)

    sql = "select insert_time from %s_%s_TABLE where insert_time = \'%s\'" % (instrument, table_type, insert_time)
    response = con.select_sql(sql)

    if len(response) == 0:
        print("below is no data")
        print(sql)
    

def insert_table(base_time, instrument, con, table_type):
    count=1
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

#    start_time = base_time.strftime("%Y-%m-%d %H:%M:%S")
#    start_time = jp_utc(start_time)
#    start_time = start_time.strftime("%Y-%m-%dT%H:%M:%S")
    start_time = (base_time - timedelta(hours=14)).strftime("%Y-%m-%dT%H:%M:%S")
    params = {
            "from": start_time,
            "granularity": granularity,
            "price": "ABM",
            "count": count
            }

    req = instruments.InstrumentsCandles(instrument=instrument, params=params)
    client.request(req)
    response = req.response

    for candle in response["candles"]:
        open_ask_price = candle["ask"]["o"]
        open_bid_price = candle["bid"]["o"]
        close_ask_price = candle["ask"]["c"]
        close_bid_price = candle["bid"]["c"]
        high_ask_price = candle["ask"]["h"]
        high_bid_price = candle["bid"]["h"]
        low_ask_price = candle["ask"]["l"]
        low_bid_price = candle["bid"]["l"]
        insert_time = candle["time"]
        insert_time = insert_time.split(".")[0]
        insert_time = insert_time + ".000000Z"
        print(insert_time)
        insert_time = iso_jp(insert_time)
        insert_time = insert_time.strftime("%Y-%m-%d %H:%M:%S")
        sql = "insert into %s_%s_TABLE(open_ask, open_bid, close_ask, close_bid, high_ask, high_bid, low_ask, low_bid, insert_time) values(%s, %s, %s, %s, %s, %s, %s, %s, \'%s\')" % (instrument, table_type, open_ask_price, open_bid_price, close_ask_price, close_bid_price, high_ask_price, high_bid_price, low_ask_price, low_bid_price, insert_time)
        print(sql)
        try:
            #con.insert_sql(sql)
            pass

        except Exception as e:
            print(e.args)

def decide_term(base_time, instrument, con):
    count=1
    granularity = "D"

    #start_time = base_time.strftime("%Y-%m-%d %H:%M:%S")
    #start_time = jp_utc(start_time)
    #start_time = start_time.strftime("%Y-%m-%dT%H:%M:%S")
    start_time = (base_time - timedelta(hours=14)).strftime("%Y-%m-%dT%H:%M:%S")
    params = {
            "from": start_time,
            "granularity": granularity,
            "price": "ABM",
            "count": count
            }

    req = instruments.InstrumentsCandles(instrument=instrument, params=params)
    client.request(req)
    response = req.response
    today = response["candles"][0]["time"]
    today = today.split(".")[0]
    today = today + ".000000Z"
 
    print(response)

    today = iso_jp(today)
    today = today.strftime("%Y-%m-%d %H:%M:%S")
    print(today)

    today = datetime.strptime(today, "%Y-%m-%d %H:%M:%S")

    term = None
    if today.hour == 6:
        term = "summer"
    elif today.hour == 7:
        term = "winter"
    else:
        raise

    return term

if __name__ == "__main__":
    args = sys.argv
    instrument = args[1].strip()
    con = MysqlConnector()
    base_time = datetime.now()
    base_time = datetime.now() - timedelta(days=7)
    term = decide_term(base_time, instrument, con)

    base_time = base_time.strftime("%Y-%m-%d 06:00:00")
    base_time = datetime.strptime(base_time, "%Y-%m-%d %H:%M:%S")

    while True:
        try:
            now = datetime.now()
            weekday = base_time.weekday()
            hour = base_time.hour
            minutes = base_time.minute
            seconds = base_time.second
            if base_time > now:
                time.sleep(1)

            else:
                if 5 < seconds < 30:
                    table_type = "1m"
                    target_time = base_time - timedelta(minutes=1)
                    target_time = target_time.strftime("%Y-%m-%d %H:%M:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                    insert_table(target_time, instrument, con, table_type)
                    check_table(base_time, instrument, con, table_type)
                if minutes % 5 == 0 and 5 < seconds < 30:
                    table_type = "5m"
                    target_time = base_time - timedelta(minutes=5)
                    target_time = target_time.strftime("%Y-%m-%d %H:%M:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                    insert_table(target_time, instrument, con, table_type)
                    check_table(base_time, instrument, con, table_type)
                if minutes == 0 and 5 < seconds < 30:
                    table_type = "1h"
                    target_time = base_time - timedelta(hours=1)
                    target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
 
                    insert_table(target_time, instrument, con, table_type)
                    check_table(base_time, instrument, con, table_type)

                if term == "summer" and hour % 3 == 0 and minutes == 0 and 5 < seconds < 30:
                    table_type = "3h"
                    target_time = base_time - timedelta(hours=3)
                    target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
 
                    insert_table(target_time, instrument, con, table_type)
                    check_table(base_time, instrument, con, table_type)
                elif term == "winter" and hour % 3 == 1 and minutes == 0 and 5 < seconds < 30:
                    table_type = "3h"
                    target_time = base_time - timedelta(hours=3)
                    target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                    insert_table(target_time, instrument, con, table_type)
                    check_table(base_time, instrument, con, table_type)

                if term == "summer" and (hour == 14 or hour == 22 or hour == 6) and minutes == 0 and 5 < seconds < 30:
                    table_type = "8h"
                    target_time = base_time - timedelta(hours=8)
                    target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
 
                    insert_table(target_time, instrument, con, table_type)
                    check_table(base_time, instrument, con, table_type)
                elif term == "winter" and (hour == 15 or hour == 23 or hour == 7) and minutes == 0 and 5 < seconds < 30:
                    table_type = "8h"
                    target_time = base_time - timedelta(hours=8)
                    target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                    insert_table(target_time, instrument, con, table_type)
                    check_table(base_time, instrument, con, table_type)

                if hour == 7 and minutes == 0 and 5 < seconds < 30: 
                    term = decide_term(target_time, instrument, con)

                    table_type = "day"
                    target_time = base_time - timedelta(days=1, hours=1)
                    target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                    insert_table(base_time, instrument, con, table_type)
                    check_table(base_time, instrument, con, table_type)
    
                base_time = base_time + timedelta(seconds=1)

            if weekday == 5 and hour > 10:
                break

        except Exception as e:
            print(e.args)
