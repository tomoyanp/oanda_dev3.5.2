# coding: utf-8
# 単純なパターン+予測が外れたら決済する

from super_algo import SuperAlgo
from mysql_connector import MysqlConnector
from datetime import timedelta, datetime
from logging import getLogger

import traceback
import subprocess
import os

import pandas as pd

pd.set_option("display.max_colwidth", 2000)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

import numpy as np
np.set_printoptions(threshold=np.inf)
import matplotlib.pyplot as plt
plt.switch_backend("agg")

from keras.models import Sequential
from keras.layers import Activation, Dense
from keras.layers import LSTM
from keras.layers import Dropout
from keras.models import model_from_json

from sklearn.preprocessing import MinMaxScaler
from lstm_model_wrapper import predict_value
from common import get_sma

import json


class Scalping(SuperAlgo):
    def __init__(self, instrument, base_path, config_name, base_time):
        super(Scalping, self).__init__(instrument, base_path, config_name, base_time)
        self.setPrice(base_time)
        self.debug_logger = getLogger("debug")
        self.result_logger = getLogger("result")
        self.mysql_connector = MysqlConnector()
        self.first_flag = self.config_data["first_trail_mode"]
        self.second_flag = self.config_data["second_trail_mode"]
        self.most_high_price = 0
        self.most_low_price = 0
        self.mode = ""
        self.algorithm = ""
        self.log_max_price = 0
        self.log_min_price = 0
        self.stl_logic = "none"
        self.output_max_price = 0
        self.output_min_price = 0
        self.first_trade_flag = ""
        self.first_trade_time = None
        self.log_object = {}
        self.current_path = os.path.abspath(os.path.dirname(__file__))

        self.model_1h = self.load_model(model_filename="multi_model_1h.json", weights_filename="multi_model_1h.hdf5")
        self.model_30m = self.load_model(model_filename="multi_model_30m.json", weights_filename="multi_model_30m.hdf5")
        self.model_15m = self.load_model(model_filename="multi_model_15m.json", weights_filename="multi_model_15m.hdf5")
        self.model_5m = self.load_model(model_filename="multi_model_5m.json", weights_filename="multi_model_5m.hdf5")
        self.model_1m = self.load_model(model_filename="multi_model_1m.json", weights_filename="multi_model_1m.hdf5")


    # decide trade entry timing
    def decideTrade(self, base_time):
        trade_flag = "pass"
        try:
            weekday = base_time.weekday()
            hour = base_time.hour
            minutes = base_time.minute
            seconds = base_time.second
            current_price = self.getCurrentPrice()

            # if weekday == Saturday, we will have no entry.

            if weekday == 4 and hour >= 22:
                trade_flag = "pass"
            if weekday == 5:
                trade_flag = "pass"

            else:
                # if spread rate is greater than 0.5, we will have no entry
                if (self.ask_price - self.bid_price) >= 0.05:
                    pass

                else:
                    trade_flag = self.decideReverseTrade(trade_flag, current_price, base_time)


            #trade_flag = "buy"
            return trade_flag
        except:
            raise

    # settlement logic
    def decideStl(self, base_time):
        try:
            stl_flag = False
            ex_stlmode = self.config_data["ex_stlmode"]
            if self.order_flag:
                if ex_stlmode == "on":
                    weekday = base_time.weekday()
                    hour = base_time.hour
                    minutes = base_time.minute
                    seconds = base_time.second
                    current_price = self.getCurrentPrice()

                    self.updatePrice(current_price)

                    # if weekday == Saturday, we will settle one's position.
                    if weekday == 5 and hour >= 5:
                        self.result_logger.info("# weekend stl logic")
                        stl_flag = True

                    else:
                        stl_flag = self.decideReverseStl(stl_flag, base_time)
                        #pass

            else:
                pass

            return stl_flag
        except:
            raise


    # 単純に1時間後にする
    def decideReverseStl(self, stl_flag, base_time):
        if self.order_flag:
             target_time = base_time - timedelta(minutes=1)
             ask_price, bid_price = self.get_current_price(target_time)
             if self.order_kind == "buy" and self.take_profit_rate < bid_price:
                 stl_flag = True
             elif self.order_kind == "sell" and self.take_profit_rate > ask_price:
                 stl_flag = True

             if self.order_kind == "buy" and self.stop_loss_rate > bid_price:
                 stl_flag = True
             elif self.order_kind == "sell" and self.stop_loss_rate < ask_price:
                 stl_flag = True

#            if self.first_trade_time + timedelta(minutes=5) < base_time:
#                stl_flag = True

#        if self.order_flag:
#            predict_price_list = self.getPredictPrice(base_time)
#            ask_price, bid_price = self.get_current_price(base_time)
#
#            if self.order_kind == "buy":
#                flag = self.decidePredictList(predict_price_list, bid_price)
#            elif self.order_kind == "sell":
#                flag = self.decidePredictList(predict_price_list, ask_price)
#
#            if flag == self.order_kind:
#                stl_flag = False
#            else:
#                stl_flag = True
#                self.result_logger.info("%s: ======== Execute Settlement ========" % base_time)
#                self.result_logger.info("%s: ask_price=%s" % (base_time, ask_price))
#                self.result_logger.info("%s: bid_price=%s" % (base_time, bid_price))
#                self.result_logger.info("%s: predict_price_1m=%s" % (base_time, predict_price_list[0]))
#                self.result_logger.info("%s: predict_price_5m=%s" % (base_time, predict_price_list[1]))
#                self.result_logger.info("%s: predict_price_15m=%s" % (base_time, predict_price_list[2]))
#                self.result_logger.info("%s: predict_price_30m=%s" % (base_time, predict_price_list[3]))
#                self.result_logger.info("%s: predict_price_1h=%s" % (base_time, predict_price_list[4]))
 

        return stl_flag

    def get_current_price(self, target_time):
        table_type = "1m"
        instruments = "EUR_JPY"
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instruments, table_type, target_time - timedelta(minutes=1)) 
        response = self.mysql_connector.select_sql(sql)
        self.ask_price = response[0][0]
        self.bid_price = response[0][1]
        return response[0][0], response[0][1]

#    # LSTMがうまく効いているのか妥当性を確認する
#    def checkPredict(self, base_time):
#        # 予測は1時間前をインプットに現在値を予測
#        predict_target_time = base_time - timedelta(hours=2)
#
#        # 実際は現在値を1時間足から取得
#        actual_target_time = base_time - timedelta(hours=1)
#
#        # 1時間足から終わり値取得
#        table_type = "1h"
#        instruments = "EUR_JPY"
#        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 2" % (instruments, table_type, actual_target_time) 
#        response = self.mysql_connector.select_sql(sql)
#        current_close_price = (response[0][0] + response[0][1])/2
#        before_close_price = (response[1][0] + response[1][1])/2
#
#        # 予測
#        right_string = "EUR_JPY"
#        instruments = "EUR_JPY"
#        window_size = 20 
#        output_train_index = 1 
#        table_type = "1h"
#        predict_price_1h = predict_value(predict_target_time, self.model_1h, window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments=instruments, right_string=right_string)
#
#
#        flag = False
#        if before_close_price < current_close_price and before_close_price < predict_price_1h:
#            flag = True
#        elif before_close_price > current_close_price and before_close_price > predict_price_1h:
#            flag = True
#
#        if flag:
#            self.result_logger.info("%s: ======== Check Predict Logic ========" % base_time)
#            self.result_logger.info("%s: before_close_price=%s" % (base_time, before_close_price))
#            self.result_logger.info("%s: current_close_price=%s" % (base_time, current_close_price))
#            self.result_logger.info("%s: before_predict_price_1h=%s" % (base_time, predict_price_1h))
#
#        return flag


    # LSTMがうまく効いているのか妥当性を確認する
    def checkPredict(self, base_time):
        # 予測は1時間前をインプットに現在値を予測
        predict_target_time = base_time - timedelta(minutes=10)

        # 実際は現在値を1時間足から取得
        actual_target_time = base_time - timedelta(minutes=5)

        # 1時間足から終わり値取得
        table_type = "5m"
        instruments = "EUR_JPY"
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 2" % (instruments, table_type, actual_target_time) 
        response = self.mysql_connector.select_sql(sql)
        current_close_price = (response[0][0] + response[0][1])/2
        before_close_price = (response[1][0] + response[1][1])/2

        # 予測
        right_string = "EUR_JPY"
        instruments = "EUR_JPY"
        window_size = 20 
        output_train_index = 1 
        table_type = "5m"
        predict_price_5m = predict_value(predict_target_time, self.model_1h, window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments=instruments, right_string=right_string)

        flag = False
        if before_close_price < current_close_price and before_close_price < predict_price_5m:
            flag = True
        elif before_close_price > current_close_price and before_close_price > predict_price_5m:
            flag = True

        if flag:
            self.result_logger.info("%s: ======== Check Predict Logic ========" % base_time)
            self.result_logger.info("%s: before_close_price=%s" % (base_time, before_close_price))
            self.result_logger.info("%s: current_close_price=%s" % (base_time, current_close_price))
            self.result_logger.info("%s: before_predict_price_5m=%s" % (base_time, predict_price_5m))

        return flag

    def getPredictPrice(self, base_time):
        right_string = "EUR_JPY"
        instruments = "EUR_JPY"
        window_size = 20 
        output_train_index = 1
        
        target_time = base_time - timedelta(minutes=1)
        table_type = "1m"
        predict_price_1m = predict_value(target_time, self.model_1m, window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments=instruments, right_string=right_string)
        
        target_time = base_time - timedelta(minutes=5)
        table_type = "5m"
        predict_price_5m = predict_value(target_time, self.model_5m, window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments=instruments, right_string=right_string)
        
        target_time = base_time - timedelta(minutes=15)
        table_type = "15m"
        predict_price_15m = predict_value(target_time, self.model_1h, window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments=instruments, right_string=right_string)
        
        target_time = base_time - timedelta(minutes=30)
        table_type = "30m"
        predict_price_30m = predict_value(target_time, self.model_1h, window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments=instruments, right_string=right_string)

        target_time = base_time - timedelta(hours=1)
        table_type = "1h"
        predict_price_1h = predict_value(target_time, self.model_1h, window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments=instruments, right_string=right_string)

        return [predict_price_1m, predict_price_5m, predict_price_15m, predict_price_30m, predict_price_1h]

    def decidePredictList(self, predict_list, current_price):
        flag = "pass"
        for predict_price in predict_list:
            if current_price < predict_price:
                flag = "buy"
            else:
                flag = "pass"
                break

        if flag == "pass":
            for predict_price in predict_list:
                if current_price > predict_price:
                    flag = "sell"
                else:
                    flag = "pass"
                    break

        return flag

    def get_bollinger(self, target_time, table_type, instruments, window_size, sigma_valiable):
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit %s" % (instruments, table_type, target_time, window_size)
        response = self.mysql_connector.select_sql(sql)
        price_list = []
        for res in response:
            price_list.append((res[0] + res[1])/2)
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


 
    def decideReverseTrade(self, trade_flag, current_price, base_time):
        if self.order_flag == False:
            minutes = base_time.minute
            seconds = base_time.second
    
            if self.first_trade_flag == "" and 0 < seconds <= 10:
                if self.checkPredict(base_time):
                    predict_price_list = self.getPredictPrice(base_time)
                    ask_price, bid_price = self.get_current_price(base_time)
                    current_price = (ask_price + bid_price)/2
                    del(predict_price_list[3:5])
                    ask_flag = self.decidePredictList(predict_price_list, ask_price)
                    bid_flag = self.decidePredictList(predict_price_list, bid_price)
    
                    if ask_flag == "buy":
                        self.take_profit_rate = max(predict_price_list)
                        self.stop_loss_rate = bid_price - (self.take_profit_rate - current_price)
                        self.first_trade_flag = "buy"
                        self.first_trade_time = base_time
                    elif bid_flag == "sell":
                        self.take_profit_rate = min(predict_price_list)
                        self.stop_loss_rate = ask_price + (current_price - self.take_profit_rate)
                        self.first_trade_flag = "sell"
                        self.first_trade_time = base_time

                    if self.first_trade_flag != "":
                        self.result_logger.info("%s: ======== Pass First Trade Logic ========" % base_time)
                        self.result_logger.info("%s: first_trade_flag=%s" % (base_time, self.first_trade_flag))
                        self.result_logger.info("%s: ask_price=%s" % (base_time, ask_price))
                        self.result_logger.info("%s: bid_price=%s" % (base_time, bid_price))
                        self.result_logger.info("%s: predict_price_1m=%s" % (base_time, predict_price_list[0]))
                        self.result_logger.info("%s: predict_price_5m=%s" % (base_time, predict_price_list[1]))
                        self.result_logger.info("%s: predict_price_15m=%s" % (base_time, predict_price_list[2]))
                        #self.result_logger.info("%s: predict_price_30m=%s" % (base_time, predict_price_list[3]))
                        #self.result_logger.info("%s: predict_price_1h=%s" % (base_time, predict_price_list[4]))
                        self.result_logger.info("%s: current_price=%s" % (base_time, current_price))


            elif self.first_trade_flag != "" and 0 < seconds <= 10:
                ask_price, bid_price = self.get_current_price(base_time)
                current_price = (ask_price + bid_price)/2

                target_time = base_time - timedelta(minutes=1)
                table_type = "1m"
                instruments = "EUR_JPY"
                window_size = 21
                sigma_valiable = 2
                data_set = self.get_bollinger(target_time, table_type, instruments, window_size, sigma_valiable)
                upper_sigma = data_set["upper_sigmas"][-1]
                lower_sigma = data_set["lower_sigmas"][-1]

                #if self.first_trade_flag == "buy" and ask_price < lower_sigma:
                if self.first_trade_flag == "buy":
                    trade_flag = "buy"
                #elif self.first_trade_flag == "sell" and bid_price > upper_sigma:
                elif self.first_trade_flag == "sell":
                    trade_flag = "sell"
                    #self.take_profit_rate = min(predict_price_list)
                    #self.stop_loss_rate = ask_price + (current_price - self.take_profit_rate)
                if trade_flag != "pass": 
                    self.result_logger.info("%s: ======== Execute Order ========" % base_time)
                    self.result_logger.info("%s: trade_flag=%s" % (base_time, trade_flag))
                    self.result_logger.info("%s: ask_price=%s" % (base_time, ask_price))
                    self.result_logger.info("%s: bid_price=%s" % (base_time, bid_price))
                    self.result_logger.info("%s: current_price=%s" % (base_time, current_price))
                    self.result_logger.info("%s: upper_sigma=%s" % (base_time, upper_sigma))
                    self.result_logger.info("%s: lower_sigma=%s" % (base_time, lower_sigma))
                    self.result_logger.info("%s: stoploss_rate=%s" % (base_time, self.stop_loss_rate))
                    self.result_logger.info("%s: takeprofit_rate=%s" % (base_time, self.take_profit_rate))


        return trade_flag

    def updatePrice(self, current_price):
        if self.log_max_price == 0:
            self.log_max_price = current_price
        elif self.log_max_price < current_price:
            self.log_max_price = current_price
        if self.log_min_price == 0:
            self.log_min_price = current_price
        elif self.log_min_price > current_price:
            self.log_min_price = current_price


# reset flag and valiables function after settlement
    def resetFlag(self):
        self.first_trade_flag = ""
        self.mode = ""
        self.most_high_price = 0
        self.most_low_price = 0
        self.log_max_price = 0
        self.log_min_price = 0
        self.stl_logic = "none"
        super(Scalping, self).resetFlag()

    def setLogObject(self, key, value):
        self.log_object[key] = value

# write log function
    def writeLog(self, logger):
        key_list = self.log_object.keys()
        logger.info("####################################")
        for key in key_list:
            logger.info("%s=%s" % (key, self.log_object[key]))
        
        self.log_object = {}

    def entryLogWrite(self, base_time):
        pass

    def settlementLogWrite(self, profit, base_time, stl_price, stl_method):
        self.result_logger.info("%s: STL_PRICE=%s" % (base_time, stl_price))
        self.result_logger.info("%s: LOG_MAX_PRICE=%s" % (base_time, self.log_max_price))
        self.result_logger.info("%s: LOG_MIN_PRICE=%s" % (base_time, self.log_min_price))
        self.result_logger.info("%s: PROFIT=%s" % (base_time, profit))

    def load_model(self, model_filename, weights_filename):
        model_filename = "%s/../model/master/%s" % (self.current_path, model_filename)
        weights_filename = "%s/../model/master/%s" % (self.current_path, weights_filename)

        print(model_filename)
        print(weights_filename)

        json_string = open(model_filename).read()
        learning_model = model_from_json(json_string)
        learning_model.load_weights(weights_filename)

        return learning_model


