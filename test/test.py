# coding: utf-8

import sys
import os
import traceback
import json

# 実行スクリプトのパスを取得して、追加
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path)

from mysql_connector import MysqlConnector
from datetime import datetime, timedelta
import oanda_wrapper
import re
import traceback

from logging import getLogger, FileHandler, DEBUG
from send_mail import SendMail

mode = sys.argv[1]
debug_logfilename = "%s-%s.log" % (mode, datetime.now().strftime("%Y%m%d%H%M%S"))
debug_logger = getLogger("debug")
debug_fh = FileHandler(debug_logfilename, "a+")
debug_logger.addHandler(debug_fh)
debug_logger.setLevel(DEBUG)

con = MysqlConnector()

instrument_list = ["EUR_GBP", "EUR_USD", "EUR_JPY", "GBP_USD", "GBP_JPY", "USD_JPY"]
insert_time = '2019-06-01 00:00:00'
# insert_time = '2019-06-25 13:00:00'
insert_time = datetime.strptime(insert_time, "%Y-%m-%d %H:%M:%S")
now = datetime.now()
end_time = datetime.strptime('2019-07-10 00:00:00', "%Y-%m-%d %H:%M:%S")


def calc_instrument(length, insert_time, description):
    result_list = []
    insert_time = insert_time - timedelta(seconds=5)

    for instrument in instrument_list:
        sql = "select open_ask, open_bid, close_ask, close_bid, insert_time from %s_5s_TABLE where insert_time <= '%s' order by insert_time desc limit %s" % (instrument, insert_time, length)
        response = con.select_sql(sql)
    
    
        open_price = (response[-1][2]+response[-1][3])/2
        close_price = (response[0][2]+response[0][3])/2
        result = (close_price/open_price - 1.0) * 10000
        start_time = response[-1][4]
        end_time = response[0][4]
        result_list.append(result)
    
        #print("%s - %s : %s = %s" % (start_time, end_time, instrument, result))
        #print("========================================")
    
    value = {}
    
    # instrument_list = ["EUR_GBP", "EUR_USD", "EUR_JPY", "GBP_USD", "GBP_JPY", "USD_JPY"]
    if result_list[0] > 0.0 and result_list[1] > 0.0 and result_list[2] > 0.0 and result_list[5] > 0.0:
        value["currency"] = "EUR_JPY"
        value["key"] = "buy"
    if result_list[0] > 0.0 and result_list[1] > 0.0 and result_list[2] > 0.0 and result_list[5] < 0.0:
        value["currency"] = "EUR_USD"
        value["key"] = "buy"
    if result_list[0] < 0.0 and result_list[3] > 0.0 and result_list[4] > 0.0 and result_list[5] > 0.0:
        value["currency"] = "GBP_JPY"
        value["key"] = "buy"
    if result_list[0] < 0.0 and result_list[3] > 0.0 and result_list[4] > 0.0 and result_list[5] < 0.0:
        value["currency"] = "GBP_USD"
        value["key"] = "buy"


    if result_list[0] < 0.0 and result_list[1] < 0.0 and result_list[2] < 0.0 and result_list[5] < 0.0:
        value["currency"] = "EUR_JPY"
        value["key"] = "sell"
    if result_list[0] < 0.0 and result_list[1] < 0.0 and result_list[2] < 0.0 and result_list[5] > 0.0:
        value["currency"] = "EUR_USD"
        value["key"] = "sell"
    if result_list[0] > 0.0 and result_list[3] < 0.0 and result_list[4] < 0.0 and result_list[5] < 0.0:
        value["currency"] = "GBP_JPY"
        value["key"] = "sell"
    if result_list[0] > 0.0 and result_list[3] < 0.0 and result_list[4] < 0.0 and result_list[5] > 0.0:
        value["currency"] = "GBP_USD"
        value["key"] = "sell"

    value["description"] = description
    return value

def trade(insert_time, instrument, trade_side):
    trade_time = insert_time
    insert_time = trade_time - timedelta(seconds=5)

    sql = "select close_ask, close_bid from %s_5s_TABLE where insert_time < '%s' order by insert_time desc limit 1" % (instrument, insert_time)
    response = con.select_sql(sql)

    ask = response[0][0]
    bid = response[0][1]
    price = (response[0][0]+response[0][1])/2

    return ask, bid, price, instrument, trade_side

def stl(insert_time, trade_obj, profit_rate, orderstop_rate):
    stl_time = insert_time
    insert_time = stl_time - timedelta(seconds=5)
    sql = "select close_ask, close_bid from %s_5s_TABLE where insert_time < '%s' order by insert_time desc limit 1" % (trade_obj["instrument"], insert_time)
    response = con.select_sql(sql)

    coefficient = 0
    if re.search("JPY", trade_obj["instrument"]) != None:
        coefficient = 100
    else:
        coefficient = 10000

    ask = response[0][0]
    bid = response[0][1]
    price = (response[0][0]+response[0][1])/2

    stl_flag = False

    if trade_obj["side"] == "buy":
        # ここの計算おかしいからちゃんと調べる
        # pips = (price/trade_obj["price"] - 1.0) * 10000
        pips = (price - trade_obj["price"])*coefficient
    elif trade_obj["side"] == "sell":
        # ここの計算おかしいからちゃんと調べる
        # pips = (trade_obj["price"]/price - 1.0) * 10000
        pips = (trade_obj["price"]-price)*coefficient
    else:
        raise

    # 20分経ったら決済する
    if trade_obj["trade_time"] + timedelta(minutes=20) < stl_time:
        stl_flag = True
        debug_logger.info("SETTLE!!! pass 20 minutes")
    # 5分経過後から、陽線、陰線を見て逆だったら決済する
    # ここのロジックおかしい
    # 多分5秒足でがんばらないとダメ
    elif trade_obj["trade_time"] + timedelta(minutes=5) < stl_time:
        if stl_time.minute % 5 == 0 and 0 < stl_time.second <= 5:
            print("========= DEBUGGING =========")
            print(trade_obj["trade_time"])
            print(stl_time)
            insert_time = stl_time - timedelta(minutes=1)
            sql = "select open_ask, open_bid, close_ask, close_bid, insert_time from %s_1m_TABLE where insert_time < '%s' order by insert_time desc limit 2" % (trade_obj["instrument"], insert_time)
            response = con.select_sql(sql)

            tmp_list = []
            for res in response:
                tmp_list.append((res[2]+res[3]) - (res[0]+res[1]))

            if trade_obj["side"] == "buy" and tmp_list[0] < 0 and tmp_list[1] < 0:
                stl_flag = True
                debug_logger.info("SETTLE!!! 5 minutes goes reverse side")
            elif trade_obj["side"] == "sell" and tmp_list[0] > 0 and tmp_list[1] > 0:
                stl_flag = True
                debug_logger.info("SETTLE!!! 5 minutes goes reverse side")

    # 一応、損切利確判定をする
    if 0 < stl_time.second <= 5:
        if pips > profit_rate:
            stl_flag = True
            debug_logger.info("SETTLE!!! price goes profit_rate")
        elif pips < orderstop_rate:
            stl_flag = True
            debug_logger.info("SETTLE!!! price goes order_stop_rate")

    profit = 0
    if stl_flag:
        if trade_obj["side"] == "buy":
            profit = (bid - trade_obj["ask"])*coefficient
        elif trade_obj["side"] == "sell":
            profit = (trade_obj["bid"] - ask)*coefficient

    return stl_flag, insert_time, price, profit

def decide_trade(insert_time, length_list):
    value_list = []
    for length in length_list:
        value = calc_instrument(length, insert_time, ("%s seconds" % (length*5)))
        value_list.append(value)

    print(value_list)
    flag = True
    for value in value_list:
        if len(value) > 1:
            pass
        else:
            flag = False

    trade_flag = True
    if flag:
        for i in range(1, len(value_list)):
            if value_list[i-1]["key"] == value_list[i]["key"] and value_list[i-1]["currency"] == value_list[i]["currency"]:
                pass
            else:
                trade_flag = False

    trade_obj = {"flag": False}
    if trade_flag and flag:
        debug_logger.info("TRADE %s: %s %s" % (insert_time, value_list[0]["currency"], value_list[0]["key"]))
        ask, bid, price, instrument, trade_side = trade(insert_time, value_list[0]["currency"], value_list[0]["key"])
        trade_obj["flag"] = True
        trade_obj["instrument"] = instrument
        trade_obj["price"] = price
        trade_obj["ask"] = ask 
        trade_obj["bid"] = bid
        trade_obj["side"] = trade_side
        trade_obj["trade_time"] = insert_time
 
    print(trade_obj)
    print("==========================================")
    return trade_obj

if __name__ == "__main__":
    trade_account = {
        "accountId": "101-009-10684893-001",
        "accessToken": "d6fa56ee0ced50ea925683cb9c316df1-8daba3977f5335ed52327c5cc54ebf5a",
        "env": "practice"
    }

    trade_obj = {"flag": False}
    profit_rate = 20
    orderstop_rate = -10

    if mode == "demo":
        insert_time = now

    while True:
        try: 
            if insert_time >= end_time and mode == "test":
                break
            elif mode == "demo":
                insert_time = datetime.now()
            else:
                insert_time = insert_time + timedelta(seconds=5)
    
            print("%s" % insert_time)
            if trade_obj["flag"] == False:
                length_list = [2, 12, 12*5, 12*15]
                trade_obj = decide_trade(insert_time, length_list)
                if trade_obj["flag"]:
                    if mode != "test":
                    # if 1 == 1:
                        #units = oanda_wrapper.calc_unit(trade_account, instrument, con)
                        units = 100000
                        response = oanda_wrapper.open_order(trade_account, trade_obj["instrument"], trade_obj["side"], units, 0, 0)
                        print(response)
                        
    
            if trade_obj["flag"]:
                stl_flag, stl_time, price, profit = stl(insert_time, trade_obj, profit_rate, orderstop_rate)
                if stl_flag:
                    debug_logger.info("SETTLE %s %s - %s: %s - %s, %s %s" % (trade_obj["instrument"], trade_obj["trade_time"], stl_time, trade_obj["price"], price, trade_obj["side"], profit))
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
