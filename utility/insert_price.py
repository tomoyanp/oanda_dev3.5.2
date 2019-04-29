# coding: utf-8

# 実行スクリプトのパスを取得して、追加
import sys
import os
import traceback
current_path = os.path.abspath(os.path.dirname(__file__))
current_path = current_path + "/.."
sys.path.append(current_path)
sys.path.append(current_path + "/trade_algorithm")
sys.path.append(current_path + "/obj")
sys.path.append(current_path + "/lib")

from mysql_connector import MysqlConnector
from price_obj import PriceObj
from datetime import datetime, timedelta
from common import decideMarket, account_init, iso_jp, jp_utc, decideSeason
from get_indicator import getBollingerWrapper
import time

account_data = account_init("production", current_path)
account_id = account_data["account_id"]
token = account_data["token"]
env = account_data["env"]
import oandapyV20
import oandapyV20.endpoints.instruments as instruments

client = oandapyV20.API(access_token=token, environment=env)
 
from logging import getLogger, FileHandler, DEBUG


args = sys.argv
instrument = args[1].strip()
con = MysqlConnector()
start_date = args[2].strip()
base_time = datetime.strptime("%s 00:00:00" % start_date, "%Y-%m-%d %H:%M:%S")
mode = args[3].strip()
base_time = base_time.strftime("%Y-%m-%d 06:00:00")
base_time = datetime.strptime(base_time, "%Y-%m-%d %H:%M:%S")


table_mode = args[4].strip()

now = datetime.now()
logfilename = "/var/log/product/%s_%s.log" %(instrument, now.strftime("%Y%m%d%H%M%S"))
debug_logger = getLogger("debug")
debug_fh = FileHandler(logfilename, "a+")
debug_logger.addHandler(debug_fh)
debug_logger.setLevel(DEBUG)


# python insert_multi_table.py instrument table_type mode


def insert_table(base_time, instrument, con, table_type, count):
    debug_logger.info("%s: Start insert_table logic" % (base_time))
    if table_type == "5s":
        granularity = "S5"
    elif table_type == "1m":
        granularity = "M1"
    elif table_type == "5m":
        granularity = "M5"
    elif table_type == "15m":
        granularity = "M15"
    elif table_type == "30m":
        granularity = "M30"
    elif table_type == "1h":
        granularity = "H1"
    elif table_type == "3h":
        granularity = "H3"
    elif table_type == "8h":
        granularity = "H8"
    elif table_type == "day":
        granularity = "D"

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


    time.sleep(1)
    print("###################")
    if len(response) == 0:
        pass
    else:
        #print(len(response["candles"]))
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
            ##print(insert_time)
            insert_time = iso_jp(insert_time)
            insert_time = insert_time.strftime("%Y-%m-%d %H:%M:%S")
            print(insert_time)
    
            sql = "select insert_time from %s_%s_TABLE where insert_time = \'%s\'" % (instrument, table_type, insert_time)
            #print(sql)
            response = con.select_sql(sql)
        
            if len(response) == 0:
                sql = "insert into %s_%s_TABLE(open_ask, open_bid, close_ask, close_bid, high_ask, high_bid, low_ask, low_bid, insert_time) values(%s, %s, %s, %s, %s, %s, %s, %s, \'%s\')" % (instrument, table_type, open_ask_price, open_bid_price, close_ask_price, close_bid_price, high_ask_price, high_bid_price, low_ask_price, low_bid_price, insert_time)
            else:
                sql = "update %s_%s_TABLE set open_ask=%s, open_bid=%s, close_ask=%s, close_bid=%s, high_ask=%s, high_bid=%s, low_ask=%s, low_bid=%s, insert_time=\'%s\' where insert_time=\'%s\'" % (instrument, table_type, open_ask_price, open_bid_price, close_ask_price, close_bid_price, high_ask_price, high_bid_price, low_ask_price, low_bid_price, insert_time, insert_time)
            try:
                con.insert_sql(sql)

            except Exception as e:
                debug_logger.info(traceback.format_exc())

        return insert_time            

def bulk_insert(start_time, end_time, instrument, con, table_type):
    while start_time < end_time:
        if decideMarket(start_time):
            tmp_time = insert_table(start_time, instrument, con, table_type, count=5000)
            if type(tmp_time) == str:
                tmp_time = datetime.strptime(tmp_time, "%Y-%m-%d %H:%M:%S")
                if tmp_time <= start_time:
                    if table_type == "5s":
                        start_time = start_time + timedelta(seconds=5)
                    elif table_type == "1m" or table_type == "5m" or table_type == "15m" or table_type == "30m":
                        start_time = start_time + timedelta(minutes=1)
                    elif table_type == "1h" or table_type == "3h" or table_type == "8h" or table_type == "day":
                        start_time = start_time + timedelta(hours=1)
                else:
                    start_time = tmp_time
            else:
                start_time = start_time + timedelta(seconds=1)
        else:
            start_time = start_time + timedelta(seconds=1)

if __name__ == "__main__":
    if mode == "bulk":
        end_time = base_time.now()
        start_time = base_time

        if table_mode == "5s":
            table_type = "5s"
            target_time = start_time - timedelta(seconds=5)
            bulk_insert(target_time, end_time, instrument, con, table_type)
    
        if table_mode == "1m":
            table_type = "1m"
            target_time = start_time - timedelta(minutes=1)
            bulk_insert(target_time, end_time, instrument, con, table_type)
    
        if table_mode == "5m":
            table_type = "5m"
            target_time = start_time - timedelta(minutes=5)
            bulk_insert(target_time, end_time, instrument, con, table_type)
    
        if table_mode == "15m":
            table_type = "15m"
            target_time = start_time - timedelta(minutes=15)
            bulk_insert(target_time, end_time, instrument, con, table_type)
    
        if table_mode == "30m":
            table_type = "30m"
            target_time = start_time - timedelta(minutes=30)
            bulk_insert(target_time, end_time, instrument, con, table_type)
    
        if table_mode == "1h":
            table_type = "1h"
            target_time = start_time - timedelta(hours=1)
            bulk_insert(target_time, end_time, instrument, con, table_type)
    
        if table_mode == "3h":
            table_type = "3h"
            target_time = start_time - timedelta(hours=3)
            bulk_insert(target_time, end_time, instrument, con, table_type)
    
        if table_mode == "8h":
            table_type = "8h"
            target_time = start_time - timedelta(hours=8)
            bulk_insert(target_time, end_time, instrument, con, table_type)
    
        if table_mode == "day":
            table_type = "day"
            target_time = start_time - timedelta(days=1)
            bulk_insert(target_time, end_time, instrument, con, table_type)

    elif mode == "production":
        count = 100
        while True:
            try:
                term = decideSeason(base_time)
                now = datetime.now()
                weekday = base_time.weekday()
                hour = base_time.hour
                minutes = base_time.minute
                seconds = base_time.second
                return_time = None
                if base_time > now:
                    time.sleep(1)
                else:
                    if seconds % 5 == 0:
                        if table_mode == "5s":
                            table_type = "5s"
                            target_time = base_time - timedelta(minutes=1)
                            target_time = target_time.strftime("%Y-%m-%d %H:%M:00")
                            target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                            return_time = insert_table(target_time, instrument, con, table_type, count)

                    if seconds % 15 == 0:
                        if table_mode == "1m":
                            table_type = "1m"
                            target_time = base_time - timedelta(minutes=10)
                            target_time = target_time.strftime("%Y-%m-%d %H:%M:00")
                            target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                            return_time = insert_table(target_time, instrument, con, table_type, count)

                        if table_mode == "5m":
                            table_type = "5m"
                            target_time = base_time - timedelta(minutes=50)
                            target_time = target_time.strftime("%Y-%m-%d %H:%M:00")
                            target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                            return_time = insert_table(target_time, instrument, con, table_type, count)


                        if table_mode == "15m":
                            table_type = "15m"
                            target_time = base_time - timedelta(minutes=150)
                            target_time = target_time.strftime("%Y-%m-%d %H:%M:00")
                            target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                            return_time = insert_table(target_time, instrument, con, table_type, count)


                        if table_mode == "30m":
                            table_type = "30m"
                            target_time = base_time - timedelta(minutes=300)
                            target_time = target_time.strftime("%Y-%m-%d %H:%M:00")
                            target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                            return_time = insert_table(target_time, instrument, con, table_type, count)

                    if minutes % 15 == 0 and seconds % 15 == 0:
                        if table_mode == "1h":
                            table_type = "1h"
                            target_time = base_time - timedelta(hours=10)
                            target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                            target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                            return_time = insert_table(target_time, instrument, con, table_type, count)

                        if table_mode == "3h":
                            table_type = "3h"
                            target_time = base_time - timedelta(hours=30)
                            target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                            target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                            return_time = insert_table(target_time, instrument, con, table_type, count)
    
                        if table_mode == "8h":
                            table_type = "8h"
                            target_time = base_time - timedelta(hours=80)
                            target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                            target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                            return_time = insert_table(target_time, instrument, con, table_type, count)
    
                    if minutes == 0 and seconds % 15 == 0:
                        if table_mode == "day":
                            table_type = "day"
                            target_time = base_time - timedelta(days=10)
                            target_time = target_time.strftime("%Y-%m-%d %H:00:00")
                            target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                            return_time = insert_table(target_time, instrument, con, table_type, count)
        
                    if type(return_time) == str:
                        return_time = datetime.strptime(return_time, "%Y-%m-%d %H:%M:%S")

                    if return_time is None or now < return_time:
                        base_time = base_time + timedelta(seconds=1)
                        count = 100
                    else:
                        base_time = return_time
                        count = 5000

                    if weekday == 5 and hour > 9:
                        break
            except Exception as e:
                debug_logger.info(traceback.format_exc())

        else:
            pass
            #print("Offline time = %s" % base_time)
