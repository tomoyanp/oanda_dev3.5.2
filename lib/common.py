# coding: utf-8
import json
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
import pytz

def jp_utc(local_time):
#    local_time = pytz.utc.localize(local_time).astimezone(pytz.timezone("Asia/Tokyo"))
#    print(local_time)
#    utc = pytz.utc
#    date = utc.normalize(local_time.astimezone(utc))
    local_time = datetime.strptime(local_time, "%Y-%m-%d %H:%M:%S")
    utc_time = local_time - timedelta(hours=9)

    return utc_time
 

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


def complement_offlinetime(start_time, end_time):
    target_time = start_time
    offline_minutes = 0

    while target_time < end_time:
        if decideMarket(target_time):
            pass
        else:
            offline_minutes = offline_minutes + 1
        target_time = target_time + timedelta(minutes=1)


    target_time = start_time
    while decideMarket(target_time) == False:
        target_time = target_time - timedelta(minutes=1)

    start_time = target_time

    start_time = start_time - timedelta(minutes=offline_minutes)

    return start_time

def get_targettime(base_time, table_type):
    if type(base_time) is str:
        base_time = datetime.strptime(base_time, "%Y-%m-%d %H:%M:%S")

    if table_type == "1m":
        target_time = base_time - timedelta(minutes=1)
    elif table_type == "5m":
        target_time = base_time - timedelta(minutes=5)
    elif table_type == "1h":
        target_time = base_time - timedelta(hours=1)
    elif table_type == "3h":
        target_time = base_time - timedelta(hours=3)
    elif table_type == "8h":
        target_time = base_time - timedelta(hours=8)
    elif table_type == "day":
        target_time = base_time - timedelta(days=1)

    else:
        raise

    return target_time


def calculate_time(base_time, instruments, table_type, con, index):
    initial_time = get_targettime(base_time, table_type)
    initial_time = initial_time.strftime("%Y-%m-%d %H:%M:%S")

    sql = "select insert_time from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit %s" % (instruments, table_type, initial_time, index+1)

    response = con.select_sql(sql)
    cal_time = response[-1][0]

    return cal_time
 
def change_to_targettime(base_time, table_type):
    if table_type == "5s":
        target_time = base_time - timedelta(seconds=5)
    elif table_type == "1m":
        target_time = base_time - timedelta(minutes=1)
    elif table_type == "5m":
        target_time = base_time - timedelta(minutes=5)
    elif table_type == "15m":
        target_time = base_time - timedelta(minutes=15)
    elif table_type == "30m":
        target_time = base_time - timedelta(minutes=30)
    elif table_type == "1h":
        target_time = base_time - timedelta(hours=1)
    elif table_type == "3h":
        target_time = base_time - timedelta(hours=3)
    elif table_type == "8h":
        target_time = base_time - timedelta(hours=8)
    elif table_type == "day":
        target_time = base_time - timedelta(days=1)
    else:
        raise

    return target_time

def change_to_nexttime(base_time, table_type, index):
    if table_type == "5s":
        target_time = base_time + timedelta(seconds=5*index)
    elif table_type == "1m":
        target_time = base_time + timedelta(minutes=1*index)
    elif table_type == "5m":
        target_time = base_time + timedelta(minutes=5*index)
    elif table_type == "15m":
        target_time = base_time + timedelta(minutes=15*index)
    elif table_type == "30m":
        target_time = base_time + timedelta(minutes=30*index)
    elif table_type == "1h":
        target_time = base_time + timedelta(hours=1*index)
    elif table_type == "3h":
        target_time = base_time + timedelta(hours=3*index)
    elif table_type == "8h":
        target_time = base_time + timedelta(hours=8*index)
    elif table_type == "day":
        target_time = base_time + timedelta(days=1*index)
    else:
        raise

    return target_time


def get_sma(instrument, target_time, table_type, length, con):
    sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit %s" % (instrument, table_type, target_time, length)

    response = con.select_sql(sql)
    ask = []
    bid = []

    for res in response:
        ask.append(res[0])
        bid.append(res[1])

    ask.reverse()
    bid.reverse()

    ask = np.array(ask)
    bid = np.array(bid)

    middle = (ask + bid) / 2
    sma = np.average(middle)

    return sma
    

def instrument_init(instrument, base_path, config_name):
    config_path = "%s/config" % base_path
    config_file = open("%s/instruments.config_%s" % (config_path, config_name), "r")
    jsonData = json.load(config_file)
    config_data = jsonData[instrument]
    return config_data

def account_init(mode, base_path):
    property_path = "%s/property" % base_path
    property_file = open("%s/account.properties" % property_path, "r")
    jsonData = json.load(property_file)
    account_data = jsonData[mode]
    return account_data


def decideSeason(base_time):
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
def decideMarket(base_time):
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
        season = decideSeason(base_time)
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

def get_bollinger(con, instrument, targettime, tabletype, window_size, sigma_valiable):
    sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit %s" % (
            instrument, tabletype, window_size)
    response = con.select_sql(sql)

    price_list = []
    for res in response:
        price_list.append((res[0]+res[1])/2)

    price_list.reverse()

    # pandasの形式に変換
    price_list = pd.Series(price_list)

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

def change_to_ptime(target_time):
    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")

    return target_time

def extraBollingerDataSet(data_set, sigma_length, candle_width):
    # 過去5本分（50分）のsigmaだけ抽出
    sigma_length = sigma_length * candle_width
    sigma_length = sigma_length * -1

    upper_sigmas = data_set["upper_sigmas"]
    lower_sigmas = data_set["lower_sigmas"]
    price_list   = data_set["price_list"]
    base_lines   = data_set["base_lines"]

    upper_sigmas = upper_sigmas[sigma_length:]
    lower_sigmas = lower_sigmas[sigma_length:]
    price_list = price_list[sigma_length:]
    base_lines = base_lines[sigma_length:]

    data_set = { "upper_sigmas": upper_sigmas,
                 "lower_sigmas": lower_sigmas,
                 "price_list": price_list,
                 "base_lines": base_lines}

    return data_set


# 加重移動平均を計算
# wma_length = 期間（200日移動平均、など）
def getOriginalEWMA(ask_price_list, bid_price_list, wma_length, candle_width):
    ask_price_list = pd.Series(ask_price_list)
    bid_price_list = pd.Series(bid_price_list)
    average_price_list = (ask_price_list + bid_price_list) / 2
    average_price_list = average_price_list.values.tolist()
    #logging.info("wma_length = %s" % wma_length)
    #logging.info("candle_width = %s" % candle_width)

    wma_length = (candle_width * wma_length) * -1
    #logging.info("wma_length = %s" % wma_length)

    # wma_lengthの分だけ抽出
    average_price_list = average_price_list[wma_length:]
    #logging.info("average_price_list length = %s" % len(average_price_list))

    # wma_lengthの分だけ、重みの積を積み上げる
    tmp_value = 0
    denominator = 0
    for i in range(0, len(average_price_list)):
        weight = i + 1
        denominator = denominator + weight
        tmp_value = tmp_value + (average_price_list[i]*weight)

   # 総数をwma_lengthの総和（シグマ）で割る⇒ 移動平均点
    wma_value = tmp_value / denominator
    #logging.info("denominator = %s" % denominator)
    #logging.info("tmp_value = %s" % tmp_value)
    #logging.info("wma_value = %s" % wma_value)

    return wma_value


def getEWMA(price_list, wma_length):

    price_list = pd.Series(price_list)
#    wma_length = len(price_list)
    wma_value_list = price_list.ewm(ignore_na=False, span=wma_length, min_periods=0, adjust=True).mean()
    wma_value_list = wma_value_list.values.tolist()

    return wma_value_list

def getSlope(target_list):
    index_list = []
    tmp_list = []

    slope = np.gradient([target_list[0], target_list[-1]])[0]
    print(slope)
#    for i in range(1, len(target_list)+1):
#        index_list.append(float(i)/10)
#
#    price_list = np.array(target_list)
#    index_list = np.array(index_list)
#
#    z = np.polyfit(index_list, price_list, 1)
#    slope, intercept = np.poly1d(z)

    return slope


# trendcheckとかの補助的な計算は毎回やる必要ないので
# ここでindex形式でスリープさせる
def countIndex(index, candle_width):
    flag = False
    if index != candle_width:
        index = index + 1
        flag = False
    else:
        index = 0
        flag = True

    return flag, index

def sleepTransaction(sleep_time, test_mode, base_time):
    sleep_time = int(sleep_time)
    if test_mode:
        base_time = base_time + timedelta(seconds=sleep_time)
    else:
        time.sleep(sleep_time)
        base_time = datetime.now()

    return base_time

def getHiLowPriceBeforeDay(base_time):
    before_end_time = base_time.strftime("%Y-%m-%d 06:59:59")
    before_day = base_time - timedelta(days=1)
    before_start_time = before_day.strftime("%Y-%m-%d 07:00:00")
    sql = "select max(ask_price_list), bid_price_list from GBP_JPY_TABLE where insert_time > \'%s\' and insert_time < \'%s\'" % (before_start_time, before_end_time)
