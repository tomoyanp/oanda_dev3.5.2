#coding: utf-8

# 実行スクリプトのパスを取得して、追加
import sys
import os
current_path = os.path.abspath(os.path.dirname(__file__))
current_path = current_path + "/.."
sys.path.append(current_path)
sys.path.append(current_path + "/trade_algorithm")
sys.path.append(current_path + "/obj")
sys.path.append(current_path + "/lib")

from oanda_wrapper import OandaWrapper
from oandapy import oandapy
from price_obj import PriceObj
from datetime import datetime, timedelta
from common import decideMarket, account_init, iso_jp, jp_utc
import time

# modify
import oandapyV20
import oandapyV20.endpoints.instruments as instruments

def return_sql(response):
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
       print(insert_time)
       insert_time = iso_jp(insert_time)
       insert_time = insert_time.strftime("%Y-%m-%d %H:%M:%S")
       sql = "insert into %s_%s_TABLE(open_ask, open_bid, close_ask, close_bid, high_ask, high_bid, low_ask, low_bid, insert_time) values(%s, %s, %s, %s, %s, %s, %s, %s, \'%s\')" % (instrument, table_type, open_ask_price, open_bid_price, close_ask_price, close_bid_price, high_ask_price, high_bid_price, low_ask_price, low_bid_price, insert_time)
    
    return sql

def return_sqlv20(response):
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

    return sql






token = "8667a3c769f85ad5e92c3d16855b5ee7-64e7b74c5a4e377f83459eab8fbe05f1"
env = "live"
oanda = oandapy.API(environment=env, access_token=token)

instrument = "USD_JPY"

table_type = "1m"
#base_time = datetime.strptime("20190201000000", "%Y%m%d%H%M%S")
base_time = datetime.now()
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

start_time = base_time.strftime("%Y-%m-%d %H:%M:%S")
start_time = jp_utc(start_time)
start_time = start_time.strftime("%Y-%m-%dT%H:%M:%S")
#start_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
print(start_time)

print("================ v1 ===================")
response = oanda.get_history(
    instrument="USD_JPY",
    start=start_time,
    granularity=granularity,
    count=count
)
print(response)
print(return_sql(response))
print("================ v20 ==================")

#start_time = (base_time - timedelta(hours=14)).strftime("%Y-%m-%dT%H:%M:%S")
start_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
print(start_time)
url = "https://api-fxtrade.oanda.com/v3/instruments/%s/candles" % instrument
params = {
        "from": start_time,
        "granularity": granularity,
        "price": "ABM",
        "count": count,
        "alignmentTimezone": "Asia/Tokyo"
        }

env = "live"
client = oandapyV20.API(access_token=token, environment=env)
req = instruments.InstrumentsCandles(instrument=instrument, params=params)
client.request(req)
response = req.response
print(response)
print(return_sqlv20(response))



