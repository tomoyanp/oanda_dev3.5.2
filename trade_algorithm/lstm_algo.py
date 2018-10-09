# coding: utf-8
####################################################
# Trade Decision
# if trade timing is between 14:00 - 04:00
# if upper and lower sigma value difference is smaller than 2 yen
# if current price is higher or lower than bollinger band 5m 3sigma
# if current_price is higher or lower than max(min) price last day
#
# Stop Loss Decision
# Same Method Above
#
# Take Profit Decision
# Special Trail mode
# if current profit is higher than 50Pips, 50Pips trail mode
# if current profit is higher than 100Pips, 30Pips trail mode
####################################################
# 1. decide perfect order and current_price <-> 5m_sma40
# 2. touch bolligner 2sigma 5m
# 3. break ewma20 1m value

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

import json


class LstmAlgo(SuperAlgo):
    def __init__(self, instrument, base_path, config_name, base_time):
        super(LstmAlgo, self).__init__(instrument, base_path, config_name, base_time)
        self.base_price = 0
        self.setPrice(base_time)
        self.debug_logger = getLogger("debug")
        self.result_logger = getLogger("result")
        self.mysql_connector = MysqlConnector()
        self.first_flag = self.config_data["first_trail_mode"]
        self.second_flag = self.config_data["second_trail_mode"]
        self.trail_third_flag = False
        self.most_high_price = 0
        self.most_low_price = 0
        self.mode = ""
        self.algorithm = ""
        self.log_max_price = 0
        self.log_min_price = 0
        self.stl_logic = "none"
        self.output_max_price = 0
        self.output_min_price = 0
        self.trade_first_flag = ""
        self.current_path = os.path.abspath(os.path.dirname(__file__))
        self.usdjpy_model = self.load_model(model_filename="usd_jpy.json", weights_filename="usd_jpy.hdf5")
        self.eurjpy_model = self.load_model(model_filename="eur_jpy.json", weights_filename="eur_jpy.hdf5")
        self.eurusd_model = self.load_model(model_filename="eur_usd.json", weights_filename="eur_usd.hdf5")
        self.gbpusd_model = self.load_model(model_filename="gbp_usd.json", weights_filename="gbp_usd.hdf5")
        self.gbpjpy_model = self.load_model(model_filename="gbp_jpy.json", weights_filename="gbp_jpy.hdf5")
        


    def test_predict(self, base_time):
        hour = base_time.hour
        minutes = base_time.minute
        seconds = base_time.second

        if minutes == 0 and seconds < 10:
            right_string = "close_price"
            window_size = 24
            output_train_index = 8
            table_type = "1h"
           
            instruments = "USD_JPY"
            usdjpy_predict = predict_value(base_time, self.usdjpy_model, window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments)
            sql = "select close_ask, close_bid, insert_time from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instruments, table_type, base_time - timedelta(hours=1))
            response = self.mysql_connector.select_sql(sql)
            usdjpy_current_price = (response[0][0] + response[0][1]) / 2
            current_time = response[0][2]


            sql = "select close_ask, close_bid, insert_time from %s_%s_TABLE where insert_time >= \'%s\' order by insert_time asc limit %s" % (instruments, table_type, base_time - timedelta(hours=1), output_train_index)
            response = self.mysql_connector.select_sql(sql)
            usdjpy_right_price = (response[-1][0] + response[-1][1]) / 2
            right_time = response[-1][2]


            instruments = "EUR_USD"
            eurusd_predict = predict_value(base_time, self.eurusd_model, window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments)
            sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instruments, table_type, base_time - timedelta(hours=1))
            response = self.mysql_connector.select_sql(sql)
            eurusd_current_price = (response[0][0] + response[0][1]) / 2
            sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time >= \'%s\' order by insert_time asc limit %s" % (instruments, table_type, base_time - timedelta(hours=1), output_train_index)
            response = self.mysql_connector.select_sql(sql)
            eurusd_right_price = (response[-1][0] + response[-1][1]) / 2


            instruments = "GBP_USD"
            gbpusd_predict = predict_value(base_time, self.gbpusd_model, window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments)
            sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instruments, table_type, base_time - timedelta(hours=1))
            response = self.mysql_connector.select_sql(sql)
            gbpusd_current_price = (response[0][0] + response[0][1]) / 2
            sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time >= \'%s\' order by insert_time asc limit %s" % (instruments, table_type, base_time - timedelta(hours=1), output_train_index)
            response = self.mysql_connector.select_sql(sql)
            gbpusd_right_price = (response[-1][0] + response[-1][1]) / 2


            instruments = "GBP_JPY"
            gbpjpy_predict = predict_value(base_time, self.gbpusd_model, window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments)
            sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instruments, table_type, base_time - timedelta(hours=1))
            response = self.mysql_connector.select_sql(sql)
            gbpjpy_current_price = (response[0][0] + response[0][1]) / 2
            sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time >= \'%s\' order by insert_time asc limit %s" % (instruments, table_type, base_time - timedelta(hours=1), output_train_index)
            response = self.mysql_connector.select_sql(sql)
            gbpjpy_right_price = (response[-1][0] + response[-1][1]) / 2


            instruments = "EUR_JPY"
            eurjpy_predict = predict_value(base_time, self.eurjpy_model, window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments)
            sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instruments, table_type, base_time - timedelta(hours=1))
            response = self.mysql_connector.select_sql(sql)
            eurjpy_current_price = (response[0][0] + response[0][1]) / 2
            sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time >= \'%s\' order by insert_time asc limit %s" % (instruments, table_type, base_time - timedelta(hours=1), output_train_index)
            response = self.mysql_connector.select_sql(sql)
            eurjpy_right_price = (response[-1][0] + response[-1][1]) / 2


            self.result_logger.info("base_time, current_time, right_time, usdjpy current price, usdjpy predict price, usdjpy right price, eurusd current price, eurusd predict price, eurusd right price, gbpusd current price, gbpusd predict price, gbpusd right price, gbpjpy current price, gbpjpy predict price, gbpjpy right price, eurjpy current price, eurjpy predict price, eurjpy right price")
            self.result_logger.info("%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s" % (base_time, current_time, right_time, usdjpy_current_price, usdjpy_predict, usdjpy_right_price, eurusd_current_price, eurusd_predict, eurusd_right_price, gbpusd_current_price, gbpusd_predict, gbpusd_right_price, gbpjpy_current_price, gbpjpy_predict, gbpjpy_right_price, eurjpy_current_price, eurjpy_predict, eurjpy_right_price))
        
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
            #if weekday == 5 and hour >= 5:

            if weekday == 4 and hour >= 22:
                trade_flag = "pass"
            if weekday == 5:
                trade_flag = "pass"

            else:
                # if spread rate is greater than 0.5, we will have no entry
                if (self.ask_price - self.bid_price) >= 0.05:
                    pass

                else:
#                    trade_flag = self.decideReverseTrade(trade_flag, current_price, base_time)
                     self.test_predict(base_time)

            if trade_flag != "pass" and self.order_flag:
                if trade_flag == "buy" and self.order_kind == "buy":
                    trade_flag = "pass"
                elif trade_flag == "sell" and self.order_kind == "sell":
                    trade_flag = "pass"
                else:
                    self.stl_logic = "allovertheworld settlement"
                    self.algorithm = self.algorithm + " by allovertheworld"


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
                        #stl_flag = self.decideReverseStl(stl_flag, base_time)
                        pass

            else:
                pass

            return stl_flag
        except:
            raise


    def decideReverseStl(self, stl_flag, base_time):
        if self.order_flag:
            hour = base_time.hour
            minutes = base_time.minute
            seconds = base_time.second


            hour = base_time.hour
            minutes = base_time.minute
            seconds = base_time.second

            if minutes == 0 and seconds < 10:

                term = self.decideTerm(hour)
                if term == "morning":
                    model_1h = self.learning_model1h_morning
                    model_5m = self.learning_model5m_morning
                elif term == "daytime":
                    model_1h = self.learning_model1h_daytime
                    model_5m = self.learning_model5m_daytime
                elif term == "night":
                    model_1h = self.learning_model1h_night
                    model_5m = self.learning_model5m_night

                self.predict_value1h = self.predict_value(base_time, model_1h, window_size=24, table_type="1h", output_train_index=1)
                self.predict_value5m = self.predict_value(base_time, model_5m, window_size=8*12, table_type="5m", output_train_index=12)

                if self.order_kind == "buy":
                    if self.predict_value5m > self.ask_price and self.predict_value1h > self.ask_price:
                        pass
                    else:
                        stl_flag = True
                elif self.order_kind == "sell":
                    if self.predict_value5m < self.bid_price and self.predict_value1h < self.bid_price:
                        pass
                    else:
                        stl_flag = True

        return stl_flag

    def decideCondition(self, table_type, target_time):
        sql = "select uppersigma3, lowersigma3 from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (self.instrument, "5m", target_time - timedelta(minutes=5))
        response = self.mysql_connector.select_sql(sql)
        uppersigma3 = response[0][0]
        lowersigma3 = response[0][1]

        flag = "none"
        if (self.ask_price > uppersigma3):
            flag = "up"
        elif (self.bid_price < lowersigma3):
            flag = "down"
    
        return flag



    def decideReverseTrade(self, trade_flag, current_price, base_time):
        if 1 == 1:
            hour = base_time.hour
            minutes = base_time.minute
            seconds = base_time.second
            if hour == 8 and seconds < 10:
                print("predict_value1d")
                self.predict_value1d = predict_value(base_time, self.learning_model1d, window_size=20, table_type="day", output_train_index=1)

                if base_time.weekday() == 0:
                    before_target_time = base_time - timedelta(days=4)
                else:
                    before_target_time = base_time - timedelta(days=1)

                print("predict_value1d_before")
                self.predict_value1d_before = predict_value(before_target_time, self.learning_model1d, window_size=20, table_type="day", output_train_index=1)

            if minutes % 5 == 0 and seconds < 10:
                if self.decideCondition("5m", base_time) == "up":
                    self.predict_value = predict_value(base_time, self.learning_upper1h, window_size=24, table_type="1h", output_train_index=1)

                    if self.ask_price < self.predict_value and self.predict_value1d_before < self.predict_value1d:
                        trade_flag = "buy"
                 
                    self.debug_logger.info("#######################")
                    self.debug_logger.info("# base_time = %s" % base_time)
                    self.debug_logger.info("# current_price = %s" % ((self.ask_price + self.bid_price)/2))
                    self.debug_logger.info("# trade_flag = %s" % trade_flag)
                    self.debug_logger.info("# predict_value1d_before = %s" % self.predict_value1d_before)
                    self.debug_logger.info("# predict_value1d = %s" % self.predict_value1d)
                    self.debug_logger.info("# predict_value = %s" % self.predict_value)




                elif self.decideCondition("5m", base_time) == "down":
                    self.predict_value = predict_value(base_time, self.learning_lower1h, window_size=24, table_type="1h", output_train_index=1)

                    if self.bid_price > self.predict_value and self.predict_value1d_before > self.predict_value1d:
                        trade_flag = "sell"

                    self.debug_logger.info("#######################")
                    self.debug_logger.info("# base_time = %s" % base_time)
                    self.debug_logger.info("# current_price = %s" % ((self.ask_price + self.bid_price)/2))
                    self.debug_logger.info("# trade_flag = %s" % trade_flag)
                    self.debug_logger.info("# predict_value1d_before = %s" % self.predict_value1d_before)
                    self.debug_logger.info("# predict_value1d = %s" % self.predict_value1d)
                    self.debug_logger.info("# predict_value = %s" % self.predict_value)


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
        self.trade_first_flag = ""
        self.mode = ""
        self.most_high_price = 0
        self.most_low_price = 0
        self.log_max_price = 0
        self.log_min_price = 0
        self.stl_logic = "none"
        super(LstmAlgo, self).resetFlag()


# write log function
    def writeDebugTradeLog(self, base_time, trade_flag):
        self.debug_logger.info("# %s "% base_time)
        self.debug_logger.info("# trade_flag=            %s" % trade_flag)
        self.debug_logger.info("#############################################")

    def writeDebugStlLog(self, base_time, stl_flag):
        self.debug_logger.info("# %s "% base_time)
        self.debug_logger.info("# stl_flag=           %s" % stl_flag)
        self.debug_logger.info("#############################################")


    def entryLogWrite(self, base_time):
        self.result_logger.info("#######################################################")
        self.result_logger.info("# in %s Algorithm" % self.algorithm)
        self.result_logger.info("# EXECUTE ORDER at %s" % base_time)
        self.result_logger.info("# trade_flag=%s" % self.order_kind)
        self.result_logger.info("# ORDER_PRICE=%s" % ((self.ask_price + self.bid_price)/2 ))
        self.result_logger.info("# predict_value1d_before=%s" % self.predict_value1d_before)
        self.result_logger.info("# predict_value1d=%s" % self.predict_value1d)
        self.result_logger.info("# predict_value=%s" % self.predict_value)
#        self.result_logger.info("# self.uppersigma3=%s" % self.uppersigma3)
#        self.result_logger.info("# self.lowersigma3=%s" % self.lowersigma3)


    def settlementLogWrite(self, profit, base_time, stl_price, stl_method):
        self.result_logger.info("# %s at %s" % (stl_method, base_time))
        self.result_logger.info("# self.ask_price=%s" % self.ask_price)
        self.result_logger.info("# self.bid_price=%s" % self.bid_price)
        self.result_logger.info("# self.log_max_price=%s" % self.log_max_price)
        self.result_logger.info("# self.log_min_price=%s" % self.log_min_price)
        self.result_logger.info("# self.stl_logic=%s" % self.stl_logic)
        self.result_logger.info("# STL_PRICE=%s" % stl_price)
        self.result_logger.info("# PROFIT=%s" % profit)

    def load_model(self, model_filename, weights_filename):
        model_filename = "%s/../model/%s" % (self.current_path, model_filename)
        weights_filename = "%s/../model/%s" % (self.current_path, weights_filename)

        print(model_filename)
        print(weights_filename)

        json_string = open(model_filename).read()
        learning_model = model_from_json(json_string)
        learning_model.load_weights(weights_filename)

        return learning_model


