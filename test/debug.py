# coding: utf-8
# 1. 1時間 10本ボリンジャーシグマ3の幅が100pips以内
# 2. 5分足が21本ボリンジャーバンドシグマ4に引っかかったらそっちについてく
# 3. 5分ごとに評価してマイナスなら即切る

import sys
import os
import traceback
import json
import pandas as pd



# 実行スクリプトのパスを取得して、追加
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path)

from mysql_connector import MysqlConnector
from datetime import datetime, timedelta
import oanda_wrapper
import re
import traceback
import numpy as np

from logging import getLogger, FileHandler, DEBUG
from send_mail import SendMail

mode = sys.argv[1]
filename = sys.argv[0].split(".")[0]
print(filename)
debug_logfilename = "%s-%s-%s.log" % (mode, filename, datetime.now().strftime("%Y%m%d%H%M%S"))
debug_logger = getLogger("debug")
debug_fh = FileHandler(debug_logfilename, "a+")
debug_logger.addHandler(debug_fh)
debug_logger.setLevel(DEBUG)

con = MysqlConnector()

instrument_list = ["EUR_GBP", "EUR_USD", "EUR_JPY", "GBP_USD", "GBP_JPY", "USD_JPY"]
instrument_list = ["GBP_JPY", "EUR_JPY", "AUD_JPY", "GBP_USD", "EUR_USD", "AUD_USD", "USD_JPY"]
#insert_time = '2019-06-01 00:00:00'
insert_time = '2019-07-02 15:50:00'
insert_time = datetime.strptime(insert_time, "%Y-%m-%d %H:%M:%S")
now = datetime.now()
end_time = datetime.strptime('2019-07-04 21:00:00', "%Y-%m-%d %H:%M:%S")

def convertTime(insert_time, table_type):
    if table_type == "5s":
        insert_time = insert_time - timedelta(seconds=5)
    elif table_type == "1m":
        insert_time = insert_time - timedelta(minutes=1)
    elif table_type == "5m":
        insert_time = insert_time - timedelta(minutes=5)
    elif table_type == "15m":
        insert_time = insert_time - timedelta(minutes=15)
    elif table_type == "30m":
        insert_time = insert_time - timedelta(minutes=30)
    elif table_type == "1h":
        insert_time = insert_time - timedelta(hours=1)
    elif table_type == "3h":
        insert_time = insert_time - timedelta(hours=3)
    elif table_type == "8h":
        insert_time = insert_time - timedelta(hours=8)
    elif table_type == "day":
        insert_time = insert_time - timedelta(days=1)
    else:
        raise

    return insert_time

def get_bollinger(instrument, insert_time, table_type, window_size, sigma_valiable):
    insert_time = convertTime(insert_time, table_type)
    sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < '%s' order by insert_time desc limit %s" % (instrument, table_type, insert_time, window_size)
    response = con.select_sql(sql)

    tmp_list = []
    for res in response:
        tmp_list.append((res[0]+res[1])/2)
    tmp_list.reverse()

    # pandasの形式に変換
    price_list = pd.Series(tmp_list)

    # シグマと移動平均の計算
    sigma = price_list.rolling(window=window_size).std(ddof=0)
    base = price_list.rolling(window=window_size).mean()

    # ボリンジャーバンドの計算
    upper_sigmas = base + (sigma*sigma_valiable)
    lower_sigmas = base - (sigma*sigma_valiable)

    # 普通の配列型にキャストして返す
    upper_sigmas = upper_sigmas.values.tolist()
    lower_sigmas = lower_sigmas.values.tolist()
    base = base.values.tolist()

    data_set = { "upper_sigmas": upper_sigmas,
                 "lower_sigmas": lower_sigmas,
                 "base_lines": base }
    return data_set

def calc_pips(instrument, start_price, end_price):
    coefficient = 0
    if re.search("JPY", instrument) != None:
        coefficient = 100
    else:
        coefficient = 10000

    result = (end_price - start_price)*coefficient

    return result

def stl(insert_time, trade_obj, profit_rate, orderstop_rate):
    stl_time = insert_time
    ask, bid = get_price(trade_obj["instrument"], insert_time)

    stl_flag = False
    if trade_obj["side"] == "buy":
        # ここの計算おかしいからちゃんと調べる
        # pips = (price/trade_obj["price"] - 1.0) * 10000
        pips = calc_pips(trade_obj["instrument"], trade_obj["ask"], bid)
    elif trade_obj["side"] == "sell":
        # ここの計算おかしいからちゃんと調べる
        # pips = (trade_obj["price"]/price - 1.0) * 10000
        pips = calc_pips(trade_obj["instrument"], ask, trade_obj["bid"])
    else:
        raise

    if stl_time.minutes % 5 == 0:
        if pips < 0:
            stl_flag = True

    # 一応、損切利確判定をする
    if pips > profit_rate:
        stl_flag = True
    elif pips < orderstop_rate:
        stl_flag = True

    if stl_flag: 
        trade_obj["stl_time"] = stl_time
        trade_obj["stl_ask"] = ask
        trade_obj["stl_bid"] = bid
        trade_obj["profit"] = pips

    return stl_flag, trade_obj

def get_sma(instrument, insert_time, table_type, length):
    sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < '%s' order by insert_time desc limit %s" % (instrument, table_type, insert_time, length)
    response = con.select_sql(sql)
    tmp_list = []
    for res in response:
        tmp_list.append(res[0])
        tmp_list.append(res[1])

    tmp_list = np.array(tmp_list)
    sma = np.average(tmp_list)

    return sma

def get_price(instrument, insert_time):
    table_type = "5s"
    insert_time = convertTime(insert_time, table_type)

    sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < '%s' order by insert_time desc limit 1" % (instrument, table_type, insert_time)
    response = con.select_sql(sql)

    ask = response[0][0]
    bid = response[0][1]

    return ask, bid



def decide_trade(insert_time, trade_obj):
    trade_time = insert_time
    for instrument in instrument_list:
        table_type = "1h"
        window_size = 10
        sigma_valiable = 3 
        threshold = 100
        data_set = get_bollinger(instrument, insert_time, table_type, window_size, sigma_valiable)
        pips = calc_pips(instrument, data_set["lower_sigmas"][-1], data_set["upper_sigmas"][-1])

        bollinger_flag = True if pips < threshold else False

        if bollinger_flag:
            trade_obj["uppersigma_1h10"] = data_set["upper_sigmas"][-1]
            trade_obj["lowersigma_1h10"] = data_set["lower_sigmas"][-1]
            trade_obj["1h10bollinger_pips"] = pips

            table_type = "5m"
            window_size =21 
            sigma_valiable = 4 
            data_set = get_bollinger(instrument, insert_time, table_type, window_size, sigma_valiable)
            ask, bid = get_price(instrument, insert_time)
            trade_obj["instrument"] = instrument
            trade_obj["ask"] = ask
            trade_obj["bid"] = bid
            trade_obj["trade_time"] = trade_time
            trade_obj["uppersigma_5m21"] = data_set["upper_sigmas"][-1]
            trade_obj["lowersigma_5m21"] = data_set["lower_sigmas"][-1]

            if data_set["upper_sigmas"][-1] < ask:
                trade_obj["flag"] = True
                trade_obj["side"] = "buy"
                break
            elif data_set["lower_sigmas"][-1] > bid:
                trade_obj["flag"] = True
                trade_obj["side"] = "sell"
                break
            else:
                print(trade_obj)
                trade_obj = {"flag": False}

    return trade_obj
         
if __name__ == "__main__":
    trade_account = {
        "accountId": "101-009-10684893-001",
        "accessToken": "d6fa56ee0ced50ea925683cb9c316df1-8daba3977f5335ed52327c5cc54ebf5a",
        "env": "practice"
    }

    trade_obj = {"flag": False}
    profit_rate = 50
    orderstop_rate = -20

    if mode == "demo":
        insert_time = now

    while True:
        try: 
            if insert_time >= end_time and mode == "test":
                break
            elif mode == "demo":
                insert_time = datetime.now()
            else:
                insert_time = insert_time + timedelta(minutes=1)
    
            print("%s" % insert_time)
            if trade_obj["flag"] == False:
                length_list = [6]
                trade_obj = decide_trade(insert_time, trade_obj)
                if trade_obj["flag"]:
                    if mode != "test":
                    # if 1 == 1:
                        #units = oanda_wrapper.calc_unit(trade_account, instrument, con)
                        units = 100000
                        response = oanda_wrapper.open_order(trade_account, trade_obj["instrument"], trade_obj["side"], units, 0, 0)
                        print(response)
                else:
                    print(trade_obj)
                        
    
            if trade_obj["flag"]:
                stl_flag, trade_obj = stl(insert_time, trade_obj, profit_rate, orderstop_rate)
                if stl_flag:
                    debug_logger.info(trade_obj)
                    trade_obj = {"flag": False}
    
                    if mode != "test":
                    # if 1 == 1:
                        response = oanda_wrapper.close_position(trade_account)
                        print(response)
        except:
            message = traceback.format_exc()
            debug_logger.info(message)
            sendmail = SendMail("tomoyanpy@gmail.com", "tomoyanpy@softbank.ne.jp", "../property")
            sendmail.set_msg(message)
            sendmail.send_mail()
