# coding: utf-8
# 単純なパターン+予測が外れたら決済する
from super_algo import SuperAlgo
from mysql_connector import MysqlConnector
from datetime import timedelta, datetime
from logging import getLogger

import traceback
import subprocess
import os
from memory_profiler import profile

import pandas as pd
pd.set_option("display.max_colwidth", 2000)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

import numpy as np
np.set_printoptions(threshold=np.inf)
import matplotlib.pyplot as plt
plt.switch_backend("agg")

from common import get_sma
from lstm_wrapper import LstmWrapper

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
        self.window_size = 20
        self.output_train_index = 1
        self.neurons = 400
        self.epochs = 20
        self.predict_currency = "EUR_JPY"
        self.lstm_wrapper = LstmWrapper(self.neurons, self.window_size)

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
                        pass

            else:
                pass

            return stl_flag
        except:
            raise



    def get_current_price(self, target_time):
        table_type = "1m"
        instruments = "EUR_JPY"
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instruments, table_type, target_time - timedelta(minutes=1)) 
        response = self.mysql_connector.select_sql(sql)
        self.ask_price = response[0][0]
        self.bid_price = response[0][1]
        return response[0][0], response[0][1]


    @profile
    def decideReverseTrade(self, trade_flag, current_price, base_time):
        if self.order_flag == False:
            minutes = base_time.minute
            seconds = base_time.second

            if minutes % 5 == 0 and 0 < seconds <= 10:
                target_time = base_time
                model5m, model1h = self.train_model(target_time)

                target_time = base_time - timedelta(minutes=5)
                table_type = "5m"
                predict_price5m = self.lstm_wrapper.predict_value(target_time, model5m, self.window_size, table_type, self.output_train_index, self.predict_currency)

                target_time = base_time - timedelta(hours=1)
                table_type = "1h"
                predict_price1h = self.lstm_wrapper.predict_value(target_time, model1h, self.window_size, table_type, self.output_train_index, self.predict_currency)

                target_time = base_time - timedelta(minutes=5)
                ask_price, bid_price = self.get_current_price(target_time)
                current_price = (ask_price + bid_price) / 2

                target_time = base_time + timedelta(hours=1)
                ask_price, bid_price = self.get_current_price(target_time)
                actual_price = (ask_price + bid_price) / 2

                if current_price < predict_price5m and current_price < predict_price1h:
                    self.result_logger.info("FOR Calculate, %s, %s, buy" % (base_time, current_price))
                elif current_price > predict_price5m and current_price > predict_price1h:
                    self.result_logger.info("FOR Calculate, %s, %s, sell" % (base_time, current_price))
                else:
                    self.result_logger.info("FOR Calculate, %s, %s, stl" % (base_time, current_price))
                      


                if current_price < predict_price5m:
                    flg5m = "buy"
                else:
                    flg5m = "sell"
                if current_price < predict_price1h:
                    flg1h = "buy"
                else:
                    flg1h = "sell"
                self.result_logger.info("%s, %s, %s, %s, %s, %s, %s" % (base_time, current_price, predict_price5m, predict_price1h, actual_price, flg5m, flg1h))

                del model5m
                del model1h

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
        meta_time = base_time - timedelta(hours=7)
        self.result_logger.info("%s: STL_PRICE=%s" % (meta_time, stl_price))
        self.result_logger.info("%s: LOG_MAX_PRICE=%s" % (meta_time, self.log_max_price))
        self.result_logger.info("%s: LOG_MIN_PRICE=%s" % (meta_time, self.log_min_price))
        self.result_logger.info("%s: PROFIT=%s" % (meta_time, profit))

    def load_model(self, model_filename, weights_filename):
        model_filename = "%s/../model/master/%s" % (self.current_path, model_filename)
        weights_filename = "%s/../model/master/%s" % (self.current_path, weights_filename)

        print(model_filename)
        print(weights_filename)

        json_string = open(model_filename).read()
        learning_model = model_from_json(json_string)
        learning_model.load_weights(weights_filename)

        return learning_model


    def train_model(self, base_time):
        table_type = "5m"
        start_time = base_time - timedelta(hours=3)
        end_time = start_time + timedelta(minutes=10)
        start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")

        model5m =  self.lstm_wrapper.create_model(self.window_size, self.output_train_index, table_type, start_time, end_time, self.neurons, self.epochs, self.predict_currency)

        table_type = "1h"
        start_time = base_time - timedelta(hours=24)
        end_time = start_time + timedelta(hours=2)
        start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")

        model1h =  self.lstm_wrapper.create_model(self.window_size, self.output_train_index, table_type, start_time, end_time, self.neurons, self.epochs, self.predict_currency)

        return model5m, model1h


