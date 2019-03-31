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
from common import get_sma

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
        self.first_trade_flag = ""
        self.first_trade_time = None
        self.current_path = os.path.abspath(os.path.dirname(__file__))

        self.usdjpy_current_price = None
        self.usdjpy1h = None
        self.usdjpy3h = None
        self.usdjpyday = None
        self.eurusd_current_price = None
        self.eurusd1h = None
        self.eurusd3h = None
        self.eurusdday = None
        self.eurjpy_current_price = None
        self.eurjpy1h = None
        self.eurjpy3h = None
        self.eurjpyday = None
        self.usdjpy_sma = None
        self.eurusd_sma = None
        self.eurjpy_sma = None
        
        self.usdjpy_1hmodel = self.load_model(model_filename="multi_model_USD_JPY_1h.json", weights_filename="multi_model_USD_JPY_1h.hdf5")
        self.usdjpy_3hmodel = self.load_model(model_filename="multi_model_USD_JPY_3h.json", weights_filename="multi_model_USD_JPY_3h.hdf5")
        self.usdjpy_daymodel = self.load_model(model_filename="multi_model_USD_JPY_day.json", weights_filename="multi_model_USD_JPY_day.hdf5")

        self.eurusd_1hmodel = self.load_model(model_filename="multi_model_EUR_USD_1h.json", weights_filename="multi_model_EUR_USD_1h.hdf5")
        self.eurusd_3hmodel = self.load_model(model_filename="multi_model_EUR_USD_3h.json", weights_filename="multi_model_EUR_USD_3h.hdf5")
        self.eurusd_daymodel = self.load_model(model_filename="multi_model_EUR_USD_day.json", weights_filename="multi_model_EUR_USD_day.hdf5")

        self.gbpusd_1hmodel = self.load_model(model_filename="multi_model_GBP_USD_1h.json", weights_filename="multi_model_GBP_USD_1h.hdf5")
        self.gbpusd_3hmodel = self.load_model(model_filename="multi_model_GBP_USD_3h.json", weights_filename="multi_model_GBP_USD_3h.hdf5")
        self.gbpusd_daymodel = self.load_model(model_filename="multi_model_GBP_USD_day.json", weights_filename="multi_model_GBP_USD_day.hdf5")

        self.gbpjpy_1hmodel = self.load_model(model_filename="multi_model_GBP_JPY_1h.json", weights_filename="multi_model_GBP_JPY_1h.hdf5")
        self.gbpjpy_3hmodel = self.load_model(model_filename="multi_model_GBP_JPY_3h.json", weights_filename="multi_model_GBP_JPY_3h.hdf5")
        self.gbpjpy_daymodel = self.load_model(model_filename="multi_model_GBP_JPY_day.json", weights_filename="multi_model_GBP_JPY_day.hdf5")

        self.eurjpy_1hmodel = self.load_model(model_filename="multi_model_EUR_JPY_1h.json", weights_filename="multi_model_EUR_JPY_1h.hdf5")
        self.eurjpy_3hmodel = self.load_model(model_filename="multi_model_EUR_JPY_3h.json", weights_filename="multi_model_EUR_JPY_3h.hdf5")
        self.eurjpy_daymodel = self.load_model(model_filename="multi_model_EUR_JPY_day.json", weights_filename="multi_model_EUR_JPY_day.hdf5")



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
                    trade_flag = self.decideReverseTrade(trade_flag, current_price, base_time)


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


    def decideReverseStl(self, stl_flag, base_time):
        seconds = base_time.second
        if 15 < seconds < 30:
            target_time = base_time
            self.set_current_price(target_time)

#        if self.order_flag:
#            hour = base_time.hour
#            minutes = base_time.minute
#            seconds = base_time.second
#
#
#            hour = base_time.hour
#            minutes = base_time.minute
#            seconds = base_time.second
#
#            if minutes == 0 and seconds < 10:
#
#                term = self.decideTerm(hour)
#                if term == "morning":
#                    model_1h = self.learning_model1h_morning
#                    model_5m = self.learning_model5m_morning
#                elif term == "daytime":
#                    model_1h = self.learning_model1h_daytime
#                    model_5m = self.learning_model5m_daytime
#                elif term == "night":
#                    model_1h = self.learning_model1h_night
#                    model_5m = self.learning_model5m_night
#
#                self.predict_value1h = self.predict_value(base_time, model_1h, window_size=24, table_type="1h", output_train_index=1)
#                self.predict_value5m = self.predict_value(base_time, model_5m, window_size=8*12, table_type="5m", output_train_index=12)
#
#                if self.order_kind == "buy":
#                    if self.predict_value5m > self.ask_price and self.predict_value1h > self.ask_price:
#                        pass
#                    else:
#                        stl_flag = True
#                elif self.order_kind == "sell":
#                    if self.predict_value5m < self.bid_price and self.predict_value1h < self.bid_price:
#                        pass
#                    else:
#                        stl_flag = True

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


    def get_model(self, table_type, instruments):
        model = None
        if table_type == "1h" and instruments == "USD_JPY":
            model = self.usdjpy_1hmodel
        elif table_type == "3h" and instruments == "USD_JPY":
            model = self.usdjpy_3hmodel
        elif table_type == "day" and instruments == "USD_JPY":
            model = self.usdjpy_daymodel

        elif table_type == "1h" and instruments == "EUR_USD":
            model = self.eurusd_1hmodel
        elif table_type == "3h" and instruments == "EUR_USD":
            model = self.eurusd_3hmodel
        elif table_type == "day" and instruments == "EUR_USD":
            model = self.eurusd_daymodel

        elif table_type == "1h" and instruments == "GBP_USD":
            model = self.gbpusd_1hmodel
        elif table_type == "3h" and instruments == "GBP_USD":
            model = self.gbpusd_3hmodel
        elif table_type == "day" and instruments == "GBP_USD":
            model = self.gbpusd_daymodel

        elif table_type == "1h" and instruments == "GBP_JPY":
            model = self.gbpjpy_1hmodel
        elif table_type == "3h" and instruments == "GBP_JPY":
            model = self.gbpjpy_3hmodel
        elif table_type == "day" and instruments == "GBP_JPY":
            model = self.gbpjpy_daymodel

        elif table_type == "1h" and instruments == "EUR_JPY":
            model = self.eurjpy_1hmodel
        elif table_type == "3h" and instruments == "EUR_JPY":
            model = self.eurjpy_3hmodel
        elif table_type == "day" and instruments == "EUR_JPY":
            model = self.eurjpy_daymodel
 

        else:
            raise

        return model

    def multi_predict(self, table_type, target_time):
        right_string = "close_price"
        window_size = 10 
        output_train_index = 1

        instruments = "USD_JPY"
        usdjpy = predict_value(target_time, self.get_model(table_type, instruments), window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments=instruments, right_string=right_string)

        instruments = "EUR_USD"
        eurusd = predict_value(target_time, self.get_model(table_type, instruments), window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments=instruments, right_string=right_string)

        instruments = "GBP_USD"
        gbpusd = predict_value(target_time, self.get_model(table_type, instruments), window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments=instruments, right_string=right_string)

        instruments = "GBP_JPY"
        gbpjpy = predict_value(target_time, self.get_model(table_type, instruments), window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments=instruments, right_string=right_string)

        instruments = "EUR_JPY"
        eurjpy = predict_value(target_time, self.get_model(table_type, instruments), window_size=window_size, table_type=table_type, output_train_index=output_train_index, instruments=instruments, right_string=right_string)


        return usdjpy, eurusd, gbpusd, gbpjpy, eurjpy


    def set_current_price(self, target_time):
        table_type = "1m"
        instruments = "USD_JPY"
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instruments, table_type, target_time - timedelta(minutes=1)) 
        response = self.mysql_connector.select_sql(sql)
        self.usdjpy_current_price = (response[0][0] + response[0][1]) / 2

        instruments = "EUR_USD"
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instruments, table_type, target_time - timedelta(minutes=1)) 
        response = self.mysql_connector.select_sql(sql)
        self.eurusd_current_price = (response[0][0] + response[0][1]) / 2

        instruments = "GBP_USD"
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instruments, table_type, target_time - timedelta(minutes=1)) 
        response = self.mysql_connector.select_sql(sql)
        self.gbpusd_current_price = (response[0][0] + response[0][1]) / 2

        instruments = "GBP_JPY"
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instruments, table_type, target_time - timedelta(minutes=1)) 
        response = self.mysql_connector.select_sql(sql)
        self.gbpjpy_current_price = (response[0][0] + response[0][1]) / 2

        instruments = "EUR_JPY"
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instruments, table_type, target_time - timedelta(minutes=1)) 
        response = self.mysql_connector.select_sql(sql)
        self.eurjpy_current_price = (response[0][0] + response[0][1]) / 2


    def decideReverseTrade(self, trade_flag, current_price, base_time):
        if self.order_flag == False:
            minutes = base_time.minute
            seconds = base_time.second
    
            if 15 < seconds < 30:
                target_time = base_time
                self.set_current_price(target_time)

            if minutes == 0 and 0 < seconds <= 10:
                target_time = base_time
                
    
                table_type = "1h"
                self.usdjpy1h, self.eurusd1h, self.gbpusd1h, self.gbpjpy1h, self.eurjpy1h = self.multi_predict(table_type, target_time)
    
                table_type = "3h"
                self.usdjpy3h, self.eurusd3h, self.gbpusd3h, self.gbpjpy3h, self.eurjpy3h = self.multi_predict(table_type, target_time)
    
                table_type = "day"
                self.usdjpyday, self.eurusdday, self.gbpusdday, self.gbpjpyday, self.eurjpyday = self.multi_predict(table_type, target_time)
    
                trade1h_flag = ""
                trade3h_flag = ""
                tradeday_flag = ""
    
    
                if self.usdjpy_current_price < self.usdjpy1h and self.eurusd_current_price < self.eurusd1h:
                    trade1h_flag = "buy"
                if self.usdjpy_current_price > self.usdjpy1h and self.eurusd_current_price > self.eurusd1h:
                    trade1h_flag = "sell"
    
                if self.usdjpy_current_price < self.usdjpy3h and self.eurusd_current_price < self.eurusd3h:
                    trade3h_flag = "buy"
                if self.usdjpy_current_price > self.usdjpy3h and self.eurusd_current_price > self.eurusd3h:
                    trade3h_flag = "sell"
    
                if self.usdjpy_current_price < self.usdjpyday and self.eurusd_current_price < self.eurusdday:
                    tradeday_flag = "buy"
                if self.usdjpy_current_price > self.usdjpyday and self.eurusd_current_price > self.eurusdday:
                    tradeday_flag = "sell"
    
    
                #if trade1h_flag == trade3h_flag == tradeday_flag == "buy":
                if trade1h_flag == tradeday_flag == "buy":
                    self.first_trade_flag = "buy"
                    self.first_trade_time = base_time
                #elif trade1h_flag == trade3h_flag == tradeday_flag == "sell":
                elif trade1h_flag == tradeday_flag == "sell":
                    self.first_trade_flag = "sell"
                    self.first_trade_time = base_time
    
                self.writeDebugTradeLog(base_time, trade_flag)

            if self.first_trade_flag != "" and minutes % 5 == 0 and 5 < seconds < 15:
                self.usdjpy_sma = get_sma(instrument="USD_JPY", base_time=base_time, table_type="5m", length=40, con=self.mysql_connector)
                self.eurusd_sma = get_sma(instrument="EUR_USD", base_time=base_time, table_type="5m", length=40, con=self.mysql_connector)
                self.eurjpy_sma = get_sma(instrument="EUR_JPY", base_time=base_time, table_type="5m", length=40, con=self.mysql_connector)
            
                if self.first_trade_flag == "buy":
                    if self.usdjpy_current_price > self.usdjpy_sma and self.eurusd_current_price > self.eurusd_sma and self.eurjpy_current_price > self.eurjpy_sma:
                        trade_flag = "buy"
                elif self.first_trade_flag == "sell":
                    if self.usdjpy_current_price < self.usdjpy_sma and self.eurusd_current_price < self.eurusd_sma and self.eurjpy_current_price < self.eurjpy_sma:
                        trade_flag = "sell"
                else:
                    raise

                self.writeDebugTradeLog(base_time, trade_flag)

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



    def setBollinger(self, base_time):
        window_size = 21
        table_type = "5m"
        sigma_valiable = 3
        target_time = base_time - timedelta(hours=1)
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit %s" % (self.instrument, table_type, target_time, window_size)
        response = self.mysql_connector.select_sql(sql)
        close_price = []
        for res in response:
            close_price.append((res[0]+res[1])/2)

        close_price.reverse()

        dataset = getBollingerDataSet(close_price, window_size, sigma_valiable)
        self.upper_sigma1h = dataset["upper_sigmas"][-1]
        self.lower_sigma1h = dataset["lower_sigmas"][-1]




# reset flag and valiables function after settlement
    def resetFlag(self):
        self.first_trade_flag = ""
        self.mode = ""
        self.most_high_price = 0
        self.most_low_price = 0
        self.log_max_price = 0
        self.log_min_price = 0
        self.stl_logic = "none"
        super(LstmAlgo, self).resetFlag()


# write log function
    def writeDebugTradeLog(self, base_time, trade_flag):
        self.debug_logger.info("#############################################")
        self.debug_logger.info("# %s "% base_time)
        self.debug_logger.info("# trade_flag=%s" % trade_flag)
        self.debug_logger.info("# first_trade_flag=%s" % self.first_trade_flag)
        self.debug_logger.info("# first_trade_time=%s" % self.first_trade_time)
        self.debug_logger.info("# usdjpy=%s" % self.usdjpy_current_price)
        self.debug_logger.info("# usdjpy1h=%s" % self.usdjpy1h)
        self.debug_logger.info("# usdjpy3h=%s" % self.usdjpy3h)
        self.debug_logger.info("# usdjpyday=%s" % self.usdjpyday)
        self.debug_logger.info("# eurusd=%s" % self.eurusd_current_price)
        self.debug_logger.info("# eurusd1h=%s" % self.eurusd1h)
        self.debug_logger.info("# eurusd3h=%s" % self.eurusd3h)
        self.debug_logger.info("# eurusdday=%s" % self.eurusdday)
        self.debug_logger.info("# eurjpyday=%s" % self.eurjpyday)
        self.debug_logger.info("# usdjpy_sma=%s" % self.usdjpy_sma) 
        self.debug_logger.info("# eurusd_sma=%s" % self.eurusd_sma) 



    def entryLogWrite(self, base_time):
        self.result_logger.info("#######################################################")
        self.result_logger.info("# in %s Algorithm" % self.algorithm)
        self.result_logger.info("# first trade time at %s" % self.first_trade_time)
        self.result_logger.info("# EXECUTE ORDER at %s" % base_time)
        self.result_logger.info("# trade_flag=%s" % self.order_kind)
        self.result_logger.info("# ORDER_PRICE=%s" % ((self.ask_price + self.bid_price)/2 ))
        self.result_logger.info("# usdjpy=%s" % self.usdjpy_current_price)
        self.result_logger.info("# usdjpy1h=%s" % self.usdjpy1h)
        self.result_logger.info("# usdjpy3h=%s" % self.usdjpy3h)
        self.result_logger.info("# usdjpyday=%s" % self.usdjpyday)
        self.result_logger.info("# eurusd=%s" % self.eurusd_current_price)
        self.result_logger.info("# eurusd1h=%s" % self.eurusd1h)
        self.result_logger.info("# eurusd3h=%s" % self.eurusd3h)
        self.result_logger.info("# eurusdday=%s" % self.eurusdday)
        self.result_logger.info("# eurjpy=%s" % self.eurjpy_current_price)
        self.result_logger.info("# eurjpy1h=%s" % self.eurjpy1h)
        self.result_logger.info("# eurjpy3h=%s" % self.eurjpy3h)
        self.result_logger.info("# eurjpyday=%s" % self.eurjpyday)
        self.result_logger.info("# usdjpy_sma=%s" % self.usdjpy_sma) 
        self.result_logger.info("# eurusd_sma=%s" % self.eurusd_sma) 
        self.result_logger.info("# eurjpy_sma=%s" % self.eurjpy_sma) 

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
        model_filename = "%s/../model/master/%s" % (self.current_path, model_filename)
        weights_filename = "%s/../model/master/%s" % (self.current_path, weights_filename)

        print(model_filename)
        print(weights_filename)

        json_string = open(model_filename).read()
        learning_model = model_from_json(json_string)
        learning_model.load_weights(weights_filename)

        return learning_model


