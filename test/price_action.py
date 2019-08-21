# coding: utf-8
# 1. 1時間 10本ボリンジャーシグマ3の幅が100pips以内
# 2. 5分足が21本ボリンジャーバンドシグマ2.5+5pipsに引っかかったらそっちについてく
# 3. 5分ごとに評価してマイナスなら即切る
# 4. sma21に引っかかったら利確
# 5. トレード時間は13時～22時

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

#mode = sys.argv[1]
#filename = sys.argv[0].split(".")[0]
##print(filename)
#debug_logfilename = "%s-%s-%s.log" % (mode, filename, datetime.now().strftime("%Y%m%d%H%M%S"))
#debug_logger = getLogger("debug")
#debug_fh = FileHandler(debug_logfilename, "a+")
#debug_logger.addHandler(debug_fh)
#debug_logger.setLevel(DEBUG)

con = MysqlConnector()

instrument_list = ["EUR_GBP", "EUR_USD", "EUR_JPY", "GBP_USD", "GBP_JPY", "USD_JPY"]
instrument_list = ["GBP_JPY", "EUR_JPY", "AUD_JPY", "GBP_USD", "EUR_USD", "AUD_USD", "USD_JPY"]
#insert_time = '2019-04-01 07:00:00'
insert_time = '2019-07-15 13:00:00'
insert_time = datetime.strptime(insert_time, "%Y-%m-%d %H:%M:%S")
now = datetime.now()
#end_time = datetime.strptime('2019-07-06 00:00:00', "%Y-%m-%d %H:%M:%S")
end_time = datetime.strptime('2019-07-17 09:00:00', "%Y-%m-%d %H:%M:%S")

def decide_season(base_time):
    year = int(base_time.year)
    month = int(base_time.month)

    if month == 3:
        start_time = "%s-03-01 00:00:00" % year
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        sunday = 6
        count = 0

        # 日曜日を数え上げ。2以上だったら夏時間
        while start_time < base_time:
            week_tmp = start_time.weekday()
            if week_tmp == sunday:
                count = count + 1
            start_time = start_time + timedelta(days=1)

        if count >= 2:
            season = "summer"
        else:
            season = "winter"


    elif month == 11:
        start_time = "%s-11-01 00:00:00" % year
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        sunday = 6
        count = 0

        # 日曜日を数え上げ。1以上だったら冬時間
        while start_time < base_time:
            week_tmp = start_time.weekday()
            if week_tmp == sunday:
                count = count + 1
            start_time = start_time + timedelta(days=1)

        if count >= 1:
            season = "winter"
        else:
            season = "summer"

    elif month == 4 or month == 5 or month == 6 or month == 7 or month == 8 or month == 9 or month == 10:
        season = "summer"
    elif month == 12 or month == 1 or month == 2:
        season = "winter"

    return season


# マーケットが休みであればfalseを返す
def decide_market(base_time):
    flag = True
    year = int(base_time.year)
    month = int(base_time.month)
    week = int(base_time.weekday())
    day = int(base_time.day)
    hour = int(base_time.hour)

    # 日曜日
    if week == 6:
        flag = False
    else:
        season = decide_season(base_time)
        if season == "summer":
            if week == 5 and hour > 5:
                flag = False
            elif week == 0 and hour < 6:
                flag = False
        if season == "winter":
            if week == 5 and hour > 6:
                flag = False
            elif week == 0 and hour < 7:
                flag = False

    return flag


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
    print(trade_obj["algo"])
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

    if trade_obj["algo"] == "bollinger":
        stl_minutes = 5
    else:
        stl_minutes = 20

    if trade_obj["trade_time"] + timedelta(minutes=stl_minutes) <= stl_time:
        if pips < 0:
            stl_flag = True

        if stl_time.minute % 5 == 0:
            sma = get_sma(trade_obj["instrument"], stl_time, "5m", 21)
            ask, bid = get_price(trade_obj["instrument"], stl_time)
            price = (ask + bid) / 2
            if trade_obj["side"] == "buy" and price < sma and pips > 0:
                stl_flag = True
            elif trade_obj["side"] == "sell" and price > sma and pips > 0:
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

    trade_obj["stl_flag"] = stl_flag
    #print(trade_obj)

    return trade_obj

def get_sma(instrument, insert_time, table_type, length):
    insert_time = convertTime(insert_time, table_type)
    sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < '%s' order by insert_time desc limit %s" % (instrument, table_type, insert_time, length)
    response = con.select_sql(sql)
    tmp_list = []
    for res in response:
        tmp_list.append(res[0])
        tmp_list.append(res[1])

    tmp_list = np.array(tmp_list)
    sma = np.average(tmp_list)

    return sma

def get_price(instrument, insert_time, table_type, length):
    insert_time = convertTime(insert_time, table_type)

    sql = "select open_ask, open_bid, close_ask, close_bid, high_ask, high_bid, low_ask, low_bid, insert_time from %s_%s_TABLE where insert_time < '%s' order by insert_time desc limit %s" % (instrument, table_type, insert_time, length)
    response = con.select_sql(sql)

    response_list = []
    for i in reversed(range(0, len(response))):
        response_list.append(list(response[i]))

    df = pd.DataFrame(response_list)
    df.rename(columns={
        0: "open_ask",
        1: "open_bid",
        2: "close_ask",
        3: "close_bid",
        4: "high_ask",
        5: "high_bid",
        6: "low_ask",
        7: "low_bid",
        8: "insert_time"
    }, inplace=True)

    return df

def over_bollinger(insert_time, instrument, trade_obj):
    trade_time = insert_time
    threshold = 100
    data_set = get_bollinger(instrument, insert_time, table_type="1h", window_size=10, sigma_valiable=3)
    pips = calc_pips(instrument, data_set["lower_sigmas"][-1], data_set["upper_sigmas"][-1])

    bollinger_flag = True if pips < threshold else False

    flag = False
    if bollinger_flag:
        trade_obj["uppersigma_1h10"] = data_set["upper_sigmas"][-1]
        trade_obj["lowersigma_1h10"] = data_set["lower_sigmas"][-1]
        trade_obj["1h10bollinger_pips"] = pips

        data_set = get_bollinger(instrument, insert_time, table_type="5m", window_size=21, sigma_valiable=2.5)
        sma_day5 = get_sma(instrument, insert_time, table_type="day", length=5)
        ask, bid = get_price(instrument, insert_time)

        # bollinger bandからどの程度乖離があるか
        threshold = 5
        upper_momentum = calc_pips(instrument, data_set["upper_sigmas"][-1], ask)
        lower_momentum = calc_pips(instrument, bid, data_set["lower_sigmas"][-1])

        trade_obj["instrument"] = instrument
        trade_obj["ask"] = ask
        trade_obj["bid"] = bid
        trade_obj["uppersigma_5m21"] = data_set["upper_sigmas"][-1]
        trade_obj["lowersigma_5m21"] = data_set["lower_sigmas"][-1]
        trade_obj["sma_day5"] = sma_day5

        if threshold < upper_momentum and sma_day5 < ask:
            flag = True
            trade_obj["side"] = "buy"
            trade_obj["algo"] = "bollinger"
        elif threshold < lower_momentum and sma_day5 > bid:
            flag = True
            trade_obj["side"] = "sell"
            trade_obj["algo"] = "bollinger"

    return flag, trade_obj

def kick_back(insert_time, instrument, trade_obj, length):
    trade_time = insert_time
    flag = False
    if trade_obj["trade_time"] + timedelta(minutes=120) < trade_time:
        trade_obj = reset_tradeobj()
    elif "sma_first_flag" not in trade_obj:
        sma = get_sma(instrument, trade_time, "5m", 21)
        ask, bid = get_price(instrument, trade_time)
        if trade_obj["side"] == "buy" and ask < sma:
            trade_obj["sma_first_time"] = trade_time
            trade_obj["sma_first_flag"] = True
        elif trade_obj["side"] == "sell" and bid > sma:
            trade_obj["sma_first_time"] = trade_time
            trade_obj["sma_first_flag"] = True

    elif trade_obj["sma_first_flag"]:
        # 終値を狙う
        if trade_time.minute % 5 == 0 and trade_time.second < 10:
            sma = get_sma(instrument, trade_time, "5m", 21)
            ask, bid = get_price(instrument, trade_time)
            if trade_obj["side"] == "buy" and ask < sma:
                trade_obj["sma_second_time"] = trade_time
                trade_obj["algo"] = "kick_back"
                flag = True
            elif trade_obj["side"] == "sell" and bid > sma:
                trade_obj["sma_second_time"] = trade_time
                trade_obj["algo"] = "kick_back"
                flag = True


    #print("logic end %s" % trade_time)
       
    return flag, trade_obj


# つつみ足
def outside_bar(instrument, insert_time, table_type):
    price_df = get_price(instrument, insert_time, table_type, 2)
    high_bef = (price_df["high_ask"][0] + price_df["high_bid"][0])/2
    low_bef = (price_df["low_ask"][0] + price_df["low_bid"][0])/2

    high_aft = (price_df["high_ask"][1] + price_df["high_bid"][1])/2
    low_aft = (price_df["low_ask"][1] + price_df["low_bid"][1])/2

    close = (price_df["close_ask"][0] + price_df["close_bid"][0])/2
    open = (price_df["open_ask"][0] + price_df["open_bid"][0])/2

    status = {}
    if high_bef <= high_aft and  low_bef >= low_aft:
        status["outside_bar"] = True
    else:
        status["outside_bar"] = False

    if open < close:
        status["direction"] = True
    else:
        status["direction"] = False

    return status


# はらみ足
def inside_bar(instrument, insert_time, table_type):
    price_df = get_price(instrument, insert_time, table_type, 2)
    high_bef = (price_df["high_ask"][0] + price_df["high_bid"][0])/2
    low_bef = (price_df["low_ask"][0] + price_df["low_bid"][0])/2

    high_aft = (price_df["high_ask"][1] + price_df["high_bid"][1])/2
    low_aft = (price_df["low_ask"][1] + price_df["low_bid"][1])/2

    close = (price_df["close_ask"][0] + price_df["close_bid"][0])/2
    open = (price_df["open_ask"][0] + price_df["open_bid"][0])/2

    status = {}
    if high_bef >= high_aft and  low_bef <= low_aft:
        status["inside_bar"] = True
    else:
        status["inside_bar"] = False

    if open < close:
        status["direction"] = True
    else:
        status["direction"] = False

    return status

# 同時線
def barbwire(instrument, insert_time, table_type):
    price_df = get_price(instrument, insert_time, table_type, 1)
    close = (price_df["close_ask"][0] + price_df["close_bid"][0])/2
    open = (price_df["open_ask"][0] + price_df["open_bid"][0])/2
    high = (price_df["high_ask"][0] + price_df["high_bid"][0])/2
    low = (price_df["low_ask"][0] + price_df["low_bid"][0])/2

    real_stick_diff = (close - open) ** 2
    line_stick_diff = (high - low) ** 2

    barbwire_threshold = 0.3
    print(real_stick_diff)
    print(line_stick_diff)

    # 実線がひげの何割か計算
    status = {}
    if real_stick_diff / line_stick_diff < barbwire_threshold:
        status["barbwire"] = True
    else:
        status["barbwire"] = False

    if open < close:
        status["direction"] = True
    else:
        status["direction"] = False

    return status


def decide_trade(insert_time, trade_obj):
    if trade_obj["algo"] == "bollinger":
        print("============== kick back")
        flag, trade_obj = kick_back(insert_time, trade_obj["instrument"], trade_obj, length=120)
        trade_obj["flag"] = flag
    else:
        print("############## bollinger")
        for instrument in instrument_list:
            flag, trade_obj = over_bollinger(insert_time, instrument, trade_obj)
            if flag:
                trade_obj["flag"] = flag
                break

    if trade_obj["flag"]:
        trade_obj["trade_time"] = insert_time
    return trade_obj
         
def reset_tradeobj():
    return  {"flag": False, "stl_flag": False, "algo": "null"}

def decide_tradetime(insert_time):
    hour = insert_time.hour
    minute = insert_time.minute

    flag = False
    if 13 < hour < 22:
        flag = True

#    if hour < 4:
#        flag = True
#    elif hour > 8:
#        flag = True

    return flag

if __name__ == "__main__":
    trade_account = {
        "accountId": "101-009-10684893-001",
        "accessToken": "d6fa56ee0ced50ea925683cb9c316df1-8daba3977f5335ed52327c5cc54ebf5a",
        "env": "practice"
    }

    trade_obj = reset_tradeobj()
    stl_obj = {}
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
    
            if decide_market(insert_time):
                #print("%s" % insert_time)
                if trade_obj["flag"] == False:
                    if decide_tradetime(insert_time):
                        trade_obj = decide_trade(insert_time, trade_obj)
                        if trade_obj["flag"]:
                            if mode != "test":
                            # if 1 == 1:
                                #units = oanda_wrapper.calc_unit(trade_account, instrument, con)
                                units = 100000
                                response = oanda_wrapper.open_order(trade_account, trade_obj["instrument"], trade_obj["side"], units, 0, 0)
                                #print(response)
                        else:
                            pass
                    else:
                        trade_obj = reset_tradeobj()

    
                if trade_obj["flag"]:
                    trade_obj = stl(insert_time, trade_obj, profit_rate, orderstop_rate)
                    #print(trade_obj)
                    if trade_obj["stl_flag"]:
                        debug_logger.info("========================================")
                        for key in trade_obj:
                            debug_logger.info("%s=%s" % (key, trade_obj[key]))

                        if trade_obj["profit"] > 0:
                            trade_obj = reset_tradeobj()
                        elif trade_obj["algo"] == "bollinger":
                            trade_obj["flag"] = False
                            trade_obj["stl_flag"] = False
                        else:
                            trade_obj = reset_tradeobj()
    
                        if mode != "test":
                        # if 1 == 1:
                            response = oanda_wrapper.close_position(trade_account)
                            #print(response)
        except:
            message = traceback.format_exc()
            debug_logger.info(message)
            sendmail = SendMail("tomoyanpy@gmail.com", "tomoyanpy@softbank.ne.jp", "../property")
            sendmail.set_msg(message)
            sendmail.send_mail()
