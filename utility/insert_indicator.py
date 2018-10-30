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
from common import decideMarket, account_init, iso_jp, jp_utc, get_sma, getBollingerDataSet
from get_indicator import getBollingerWrapper
import time
import pandas as pd
import traceback

account_data = account_init("production", current_path)
account_id = account_data["account_id"]
token = account_data["token"]
env = account_data["env"]

oanda = oandapy.API(environment=env, access_token=token)
 
# python insert_multi_table.py instrument table_type mode

def get_original_data(base_time, currency, con, table_type, length):
    sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit %s" % (currency, table_type, base_time, length)
    response = con.select_sql(sql)
    close_price = []
    for res in response:
        close_price.append((res[0]+res[1])/2)

    close_price.reverse()

    return close_price

def insert_table(base_time, currency, con, table_type):
    length = 20
    sma20 = get_sma(currency, base_time, table_type, length, con)

    length = 40
    sma40 = get_sma(currency, base_time, table_type, length, con)

    length = 80
    sma80 = get_sma(currency, base_time, table_type, length, con)

    length = 21
    sigma = 2
    data = get_original_data(base_time, currency, con, table_type, length)
    dataset_sigma2 = getBollingerDataSet(data, length, sigma)
    upper_sigma2 = dataset_sigma2["upper_sigmas"][-1]
    lower_sigma2 = dataset_sigma2["lower_sigmas"][-1]

    sigma = 3
    dataset_sigma3 = getBollingerDataSet(data, length, sigma)
    upper_sigma3 = dataset_sigma3["upper_sigmas"][-1]
    lower_sigma3 = dataset_sigma3["lower_sigmas"][-1]

    sql = "insert into INDICATOR_TABLE(table_type, currency, sma20, sma40, sma80, upper_sigma2, lower_sigma2, upper_sigma3, lower_sigma3, insert_time) values(\'%s\', \'%s\', %s, %s, %s, %s, %s, %s, %s, \'%s\')" % (table_type, currency, sma20, sma40, sma80, upper_sigma2, lower_sigma2, upper_sigma3, lower_sigma3, base_time)

    con.insert_sql(sql)

def decide_term(base_time, currency, con):
    count=1
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

    today = response["candles"][0]["time"]
    today = iso_jp(today)
    today = today.strftime("%Y-%m-%d %H:%M:%S")

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
    currency = args[1].strip()
    mode = args[2].strip()
    con = MysqlConnector()
    base_time = datetime.now()

    if mode == "test":
        base_time = "2009-01-01 00:00:00"
        base_time = datetime.strptime(base_time, "%Y-%m-%d %H:%M:%S")
        end_time = "2018-10-01 00:00:00"
        end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        term = "winter"
    else:    
        base_time = base_time.strftime("%Y-%m-%d 06:00:00")
        base_time = datetime.strptime(base_time, "%Y-%m-%d %H:%M:%S")
        term = decide_term(base_time, currency, con)

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
                if 30 < seconds < 60:
                    table_type = "1m"
                    target_time = base_time - timedelta(minutes=1)
                    target_time = target_time.strftime("%Y-%m-%d %H:%M:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                    
                     
                    insert_table(target_time, currency, con, table_type)
                if minutes % 5 == 0 and 30 < seconds < 60:
                    table_type = "5m"
                    target_time = base_time - timedelta(minutes=5)
                    target_time = target_time.strftime("%Y-%m-%d %H:%M:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
 
                    insert_table(target_time, currency, con, table_type)
                if minutes == 0 and 30 < seconds < 60:
                    table_type = "1h"
                    target_time = base_time - timedelta(hours=1)
                    target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
 
                    insert_table(target_time, currency, con, table_type)

                if term == "summer" and hour % 3 == 0 and minutes == 0 and 30 < seconds < 60:
                    table_type = "3h"
                    target_time = base_time - timedelta(hours=3)
                    target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
 
                    insert_table(target_time, currency, con, table_type)
                elif term == "winter" and hour % 3 == 1 and minutes == 0 and 30 < seconds < 60:
                    table_type = "3h"
                    target_time = base_time - timedelta(hours=3)
                    target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
 
                    insert_table(target_time, currency, con, table_type)

                if term == "summer" and (hour == 14 or hour == 22 or hour == 6) and minutes == 0 and 30 < seconds < 60:
                    table_type = "8h"
                    target_time = base_time - timedelta(hours=8)
                    target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
 
                    insert_table(target_time, currency, con, table_type)
                elif term == "winter" and (hour == 15 or hour == 23 or hour == 7) and minutes == 0 and 30 < seconds < 60:
                    table_type = "8h"
                    target_time = base_time - timedelta(hours=8)
                    target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
 
                    insert_table(target_time, currency, con, table_type)

                if hour == 7 and minutes == 0 and 30 < seconds < 60: 
                    term = decide_term(target_time, currency, con)

                    table_type = "day"
                    target_time = base_time - timedelta(days=1, hours=1)
                    target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
 
 
                    insert_table(base_time, currency, con, table_type)
    
                base_time = base_time + timedelta(seconds=1)

            if weekday == 5 and hour > 10:
                break

            if mode == "test" and end_time < base_time:
                break

        except Exception as e:
            base_time = base_time + timedelta(seconds=1)
            traceback.print_exc() 
