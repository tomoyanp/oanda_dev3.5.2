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
from multi_model import train_save_model

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


    def decideReverseTrade(self, trade_flag, current_price, base_time):
        if self.order_flag == False:
            minutes = base_time.minute
            seconds = base_time.second

            if minutes % 5 == 0 and 0 < seconds <= 10:
                target_time = base_time - timedelta(minutes=5)
                model = self.train_model(target_time)

                table_type = "5m"
                start_time = base_time - timedelta(hours=1)
                end_time = base_time
                model_name = "multi_model"
                window_size = 12*3
                output_train_index = 6
                instruments = "EUR_JPY"
                right_string = "EUR_JPY"

                predict_price = predict_value(target_time, model, window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments=instruments, right_string=right_string)

                target_time = base_time - timdelta(minutes=5)
                ask_price, bid_price = self.get_current_price(target_time)
                current_price = (ask_price + bid_price) / 2

                target_time = base_time + timdelta(minutes=30)
                ask_price, bid_price = self.get_current_price(target_time)
                actual_price = (ask_price + bid_price) / 2

                self.result_logger.info("base_time: current_price, predict_price, actual_price")
                self.result_logger.info("%s: %s, %s, %s" % (base_time, current_price, predict_price, actual_price) 


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
        start_time = base_time - timedelta(hours=1)
        end_time = base_time
        model_name = "multi_model"
        window_size = 12*3
        output_train_index = 6
        filename = "%s_%s" % (model_name, table_type)
        learning_model = train_save_model(window_size=window_size, output_train_index=output_train_index, table_type=table_type, figure_filename="%s.png" % filename, model_filename="%s.json" % filename, weights_filename="%s.hdf5" % filename, start_time=start_time, end_time=end_time, term="all")
        return learning_model


