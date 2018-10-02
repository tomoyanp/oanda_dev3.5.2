# coding: utf-8

import sys
import os
import traceback
import json
import pytz

# 実行スクリプトのパスを取得して、追加
current_path = os.path.abspath(os.path.dirname(__file__))
current_path = current_path + "/.."
sys.path.append(current_path)
sys.path.append(current_path + "/trade_algorithm")
sys.path.append(current_path + "/obj")
sys.path.append(current_path + "/lib")

from datetime import datetime, timedelta
from mysql_connector import MysqlConnector
from db_wrapper import DBWrapper
from oanda_wrapper import OandaWrapper
from send_mail import SendMail
from oandapy import oandapy
import time

account_id = 4093685
token = 'e93bdc312be2c3e0a4a18f5718db237a-32ca3b9b94401fca447d4049ab046fad'
env = 'live'


def iso_jp(iso):
    date = None
    try:
        date = datetime.strptime(iso, '%Y-%m-%dT%H:%M:%S.%fZ')
        date = pytz.utc.localize(date).astimezone(pytz.timezone("Asia/Tokyo"))
    except ValueError:
        try:
            date = datetime.strptime(iso, '%Y-%m-%dT%H:%M:%S.%f%z')
            date = dt.astimezone(pytz.timezone("Asia/Tokyo"))
        except ValueError:
            pass
    return date
 

# 通貨
instrument = "GBP_JPY"
oanda = oandapy.API(environment=env, access_token=token)
#response = oanda.get_positions(account_id)
#response = oanda.get_account(account_id)

#response = oanda.get_transaction_history(account_id)
#response = oanda.get_history(
#    instrument="GBP_JPY",
#    start="2018-01-02T10:00:00",
#    granularity="S5",
#    candleFormat="midpoint"
#)

#print("get_history")
#print(response)

response = oanda.get_prices(instruments="GBP_JPY")

for res in response["prices"]:
    iso_time = res["time"]
    insert_time = iso_jp(iso_time)
    insert_time = insert_time.strftime("%Y-%m-%d %H:%M:%S")
    print(insert_time)

print("current_price")
print(response)

#time.sleep(1)
#
#response = oanda.get_prices(instruments="GBP_JPY")
#print("current_price")
#print(response)
#
#
#response = oanda.get_prices(instruments="GBP_JPY")
#print("current_price")
#print(response)
#
##response = json.load(response)
#
#
##response = oanda.get_historical_position_ratios()
##response = oanda.get_history(instrument)
##response = oanda.get_position(account_id, instrument)
##response = oanda.get_trades(
##                 accountId=account_id,
##                 instruments=instrument)
##response = oanda.get_trades(account_id)
#
##response = oanda_wrapper.order("buy", instrument, 0, 0)
##
##order_id = response["tradeOpened"]["id"]
##time.sleep(5)
##response = oanda_wrapper.close_trade(order_id)
