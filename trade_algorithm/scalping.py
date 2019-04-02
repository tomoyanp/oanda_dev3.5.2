# coding: utf-8
# 単純なパターン+予測が外れたら決済する
from super_algo import SuperAlgo
from mysql_connector import MysqlConnector
from datetime import timedelta
from logging import getLogger

import os
import pandas as pd
pd.set_option("display.max_colwidth", 2000)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

import numpy as np
np.set_printoptions(threshold=np.inf)
import matplotlib.pyplot as plt
plt.switch_backend("agg")

from common import get_sma, getSlope, decideMarket
from lstm_wrapper import LstmWrapper


from keras.models import model_from_json

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
        self.usdjpy_lstm_wrapper = LstmWrapper(self.neurons, self.window_size, "USD_JPY")
        self.eurusd_lstm_wrapper = LstmWrapper(self.neurons, self.window_size, "EUR_USD")
        self.gbpusd_lstm_wrapper = LstmWrapper(self.neurons, self.window_size, "GBP_USD")

        self.usdjpy1m_model = self.load_model("USD_JPY_1m")
        self.usdjpy5m_model = self.load_model("USD_JPY_5m")
        self.usdjpy1h_model = self.load_model("USD_JPY_1h")

        self.eurusd1m_model = self.load_model("EUR_USD_1m")
        self.eurusd5m_model = self.load_model("EUR_USD_5m")
        self.eurusd1h_model = self.load_model("EUR_USD_1h")

        self.gbpusd1m_model = self.load_model("GBP_USD_1m")
        self.gbpusd5m_model = self.load_model("GBP_USD_5m")
        self.gbpusd1h_model = self.load_model("GBP_USD_1h")

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
                if (self.ask_price - self.bid_price) >= 0.02:
                    pass

                else:
                    trade_flag = self.decideReverseTrade(trade_flag, current_price, base_time)


            #trade_flag = "buy"
            self.debug_logger.info("%s: pass" % base_time)
            #self.debug_logger.info(self.ask_price)
            #self.debug_logger.info(self.bid_price)
            #self.debug_logger.info(self.ask_price - self.bid_price)
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
                        #stl_flag = self.decideReverseStl(base_time, stl_flag)
                        pass
            else:
                pass

            return stl_flag
        except:
            raise



    def decideReverseStl(self, base_time, stl_flag):
        if self.order_flag:
            minutes = base_time.minute
            seconds = base_time.second

            if self.entry_time + timedelta(hours=1) < base_time:
                stl_flag = True

        return stl_flag
 

 
    def get_current_price(self, target_time):
        table_type = "5s"
        instrument = "USD_JPY"
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instrument, table_type, target_time - timedelta(seconds=5)) 
        response = self.mysql_connector.select_sql(sql)
        usdjpy_price = (response[0][0] + response[0][1]) / 2
        self.ask_price = response[0][0]
        self.bid_price = response[0][1]

        table_type = "5s"
        instrument = "EUR_USD"
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instrument, table_type, target_time - timedelta(seconds=5)) 
        response = self.mysql_connector.select_sql(sql)
        eurusd_price = (response[0][0] + response[0][1]) / 2

        table_type = "5s"
        instrument = "GBP_USD"
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instrument, table_type, target_time - timedelta(seconds=5)) 
        response = self.mysql_connector.select_sql(sql)
        gbpusd_price = (response[0][0] + response[0][1]) / 2


        table_type = "5s"
        instrument = "GBP_JPY"
        sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instrument, table_type, target_time - timedelta(seconds=5)) 
        response = self.mysql_connector.select_sql(sql)
        gbpjpy_price = (response[0][0] + response[0][1]) / 2
 

        return usdjpy_price, eurusd_price, gbpusd_price, gbpjpy_price

    def predictPrice(self, base_time):
        target_time = base_time
        minutes = base_time.minute
        seconds = base_time.second

        target_time = base_time - timedelta(minutes=1)
        table_type = "1m"

        usdjpy_predict1m = self.usdjpy_lstm_wrapper.predict_value(target_time, self.usdjpy1m_model, self.window_size, table_type, self.output_train_index, "USD_JPY")
        eurusd_predict1m = self.eurusd_lstm_wrapper.predict_value(target_time, self.eurusd1m_model, self.window_size, table_type, self.output_train_index, "EUR_USD")
        gbpusd_predict1m = self.gbpusd_lstm_wrapper.predict_value(target_time, self.gbpusd1m_model, self.window_size, table_type, self.output_train_index, "GBP_USD")


        target_time = base_time - timedelta(minutes=5)
        table_type = "5m"
        usdjpy_predict5m = self.usdjpy_lstm_wrapper.predict_value(target_time, self.usdjpy5m_model, self.window_size, table_type, self.output_train_index, "USD_JPY")
        eurusd_predict5m = self.eurusd_lstm_wrapper.predict_value(target_time, self.eurusd5m_model, self.window_size, table_type, self.output_train_index, "EUR_USD")
        gbpusd_predict5m = self.gbpusd_lstm_wrapper.predict_value(target_time, self.gbpusd5m_model, self.window_size, table_type, self.output_train_index, "GBP_USD")


        target_time = base_time - timedelta(hours=1)
        table_type = "1h"
        usdjpy_predict1h = self.usdjpy_lstm_wrapper.predict_value(target_time, self.usdjpy1h_model, self.window_size, table_type, self.output_train_index, "USD_JPY")
        eurusd_predict1h = self.eurusd_lstm_wrapper.predict_value(target_time, self.eurusd1h_model, self.window_size, table_type, self.output_train_index, "EUR_USD")
        gbpusd_predict1h = self.gbpusd_lstm_wrapper.predict_value(target_time, self.gbpusd1h_model, self.window_size, table_type, self.output_train_index, "GBP_USD")

        predict_object = {
                "usdjpy1m": usdjpy_predict1m,
                "usdjpy5m": usdjpy_predict5m,
                "usdjpy1h": usdjpy_predict1h,
                "eurusd1m": eurusd_predict1m,
                "eurusd5m": eurusd_predict5m,
                "eurusd1h": eurusd_predict1h,
                "gbpusd1m": gbpusd_predict1m,
                "gbpusd5m": gbpusd_predict5m,
                "gbpusd1h": gbpusd_predict1h
                }
        return predict_object 


    def decideReverseTrade(self, trade_flag, current_price, base_time):
        if self.order_flag == False:
            minutes = base_time.minute
            seconds = base_time.second

            if 0 < seconds <= 10:
                predict_object = self.predictPrice(base_time)
                usdjpy_price, eurusd_price, gbpusd_price, gbpjpy_price = self.get_current_price(base_time)

                table_type = "1m"
                target_time = base_time - timedelta(minutes=1)
                length = "100"
                usdjpy_sma100 = get_sma(self.instrument, target_time, table_type, length, self.mysql_connector)
                sql = "select close_ask, close_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (self.instrument, table_type, target_time)
                response = self.mysql_connector.select_sql(sql)
                usdjpy_closeprice = (response[0][0] + response[0][1]) / 2

                usdjpy_flag = "pass"
                if usdjpy_price < predict_object["usdjpy1m"] and usdjpy_price < predict_object["usdjpy5m"]:
                    usdjpy_flag = "buy"
                elif usdjpy_price > predict_object["usdjpy1m"] and usdjpy_price > predict_object["usdjpy5m"]:
                    usdjpy_flag = "sell"


                eurusd_flag = "pass"
                if eurusd_price < predict_object["eurusd1m"] and eurusd_price < predict_object["eurusd5m"]:
                    eurusd_flag = "sell"
                elif eurusd_price > predict_object["eurusd1m"] and eurusd_price > predict_object["eurusd5m"]:
                    eurusd_flag = "buy"

                gbpusd_flag = "pass"
                if gbpusd_price < predict_object["gbpusd1m"] and gbpusd_price < predict_object["gbpusd5m"]:
                    gbpusd_flag = "sell"
                elif gbpusd_price > predict_object["gbpusd1m"] and gbpusd_price > predict_object["gbpusd5m"]:
                    gbpusd_flag = "buy"

                if usdjpy_flag == "buy" and eurusd_flag == "buy":
                    self.first_trade_flag = "buy"
                    self.first_trade_time = base_time

                    self.setLogObject("A", "# ORDER_EXE: %s: usdjpy_price=%s" % (base_time, usdjpy_price))
                    self.setLogObject("B", "# ORDER_EXE: %s: usdjpy1m=%s" % (base_time, predict_object["usdjpy1m"]))
                    self.setLogObject("C", "# ORDER_EXE: %s: usdjpy5m=%s" % (base_time, predict_object["usdjpy5m"]))
                    self.setLogObject("D", "# ORDER_EXE: %s: usdjpy1h=%s" % (base_time, predict_object["usdjpy1h"]))
                    self.setLogObject("E", "# ORDER_EXE: %s: eurusd_price=%s" % (base_time, eurusd_price))
                    self.setLogObject("F", "# ORDER_EXE: %s: eurusd1m=%s" % (base_time, predict_object["eurusd1m"]))
                    self.setLogObject("G", "# ORDER_EXE: %s: eurusd5m=%s" % (base_time, predict_object["eurusd5m"]))
                    self.setLogObject("H", "# ORDER_EXE: %s: eurusd1h=%s" % (base_time, predict_object["eurusd1h"]))
                    self.setLogObject("I", "# ORDER_EXE: %s: gbpusd_price=%s" % (base_time, gbpusd_price))
                    self.setLogObject("J", "# ORDER_EXE: %s: gbpusd1m=%s" % (base_time, predict_object["gbpusd1m"]))
                    self.setLogObject("K", "# ORDER_EXE: %s: gbpusd5m=%s" % (base_time, predict_object["gbpusd5m"]))
                    self.setLogObject("L", "# ORDER_EXE: %s: gbpusd1h=%s" % (base_time, predict_object["gbpusd1h"]))
                    self.setLogObject("M", "# ORDER_EXE: %s: frist_trade_time=%s" % (base_time, self.first_trade_time))

                elif usdjpy_flag == "sell" and eurusd_flag == "sell":
                    self.first_trade_flag = "sell"
                    self.first_trade_time = base_time

                    self.setLogObject("A", "# ORDER_EXE: %s: usdjpy_price=%s" % (base_time, usdjpy_price))
                    self.setLogObject("B", "# ORDER_EXE: %s: usdjpy1m=%s" % (base_time, predict_object["usdjpy1m"]))
                    self.setLogObject("C", "# ORDER_EXE: %s: usdjpy5m=%s" % (base_time, predict_object["usdjpy5m"]))
                    self.setLogObject("D", "# ORDER_EXE: %s: usdjpy1h=%s" % (base_time, predict_object["usdjpy1h"]))
                    self.setLogObject("E", "# ORDER_EXE: %s: eurusd_price=%s" % (base_time, eurusd_price))
                    self.setLogObject("F", "# ORDER_EXE: %s: eurusd1m=%s" % (base_time, predict_object["eurusd1m"]))
                    self.setLogObject("G", "# ORDER_EXE: %s: eurusd5m=%s" % (base_time, predict_object["eurusd5m"]))
                    self.setLogObject("H", "# ORDER_EXE: %s: eurusd1h=%s" % (base_time, predict_object["eurusd1h"]))
                    self.setLogObject("I", "# ORDER_EXE: %s: gbpusd_price=%s" % (base_time, gbpusd_price))
                    self.setLogObject("J", "# ORDER_EXE: %s: gbpusd1m=%s" % (base_time, predict_object["gbpusd1m"]))
                    self.setLogObject("K", "# ORDER_EXE: %s: gbpusd5m=%s" % (base_time, predict_object["gbpusd5m"]))
                    self.setLogObject("L", "# ORDER_EXE: %s: gbpusd1h=%s" % (base_time, predict_object["gbpusd1h"]))
                    self.setLogObject("M", "# ORDER_EXE: %s: frist_trade_time=%s" % (base_time, self.first_trade_time))



                sma100_list = []
                table_type = "1m"
                index = 1
                while len(sma100_list) < 10:
                    target_time = base_time - timedelta(minutes=index)
                    if decideMarket(target_time):
                        length = "100"
                        usdjpy_sma100 = get_sma(self.instrument, target_time, table_type, length, self.mysql_connector)
                        sma100_list.append(usdjpy_sma100)
                    index = index + 1    

                sma100_list.reverse()
                usdjpy_sma100_slope = getSlope(sma100_list)

                if self.first_trade_flag == "buy" and usdjpy_sma100 < usdjpy_closeprice and 0 < usdjpy_sma100_slope:
                    trade_flag = "buy"
                elif self.first_trade_flag == "sell" and usdjpy_sma100 > usdjpy_closeprice and 0 > usdjpy_sma100_slope:
                    trade_flag = "sell"

#                if self.first_trade_flag != "":
#                    if self.first_trade_time + timedelta(minutes=10) < base_time:
#                        self.resetFlag()

                if trade_flag != "pass":
                    self.entry_time = base_time
                    self.setLogObject("N", "# ORDER_EXE: %s: usdjpy_sma100=%s" % (base_time, usdjpy_sma100))
                    self.setLogObject("O", "# ORDER_EXE: %s: usdjpy_sma100_slope=%s" % (base_time, usdjpy_sma100_slope))
                    self.setLogObject("P", "# ORDER_EXE: %s: usdjpy_closeprice=%s" % (base_time, usdjpy_closeprice))
                    self.setLogObject("Q", "# ORDER_EXE: %s: trade_flag=%s" % (base_time, trade_flag))
 
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
    def writeLogObject(self):
        keys = self.log_object.keys()
        sorted_keys = sorted(keys)
        for key in sorted_keys:
            self.result_logger.info(self.log_object[key])

        self.log_object = {}

    def entryLogWrite(self, base_time):
        self.writeLogObject()

    def settlementLogWrite(self, profit, base_time, stl_price, stl_method):
#        meta_time = base_time - timedelta(hours=7)
        meta_time = base_time
        self.writeLogObject()
        self.result_logger.info("# STL_EXE: %s: STL_PRICE=%s" % (meta_time, stl_price))
        self.result_logger.info("# STL_EXE: %s: LOG_MAX_PRICE=%s" % (meta_time, self.log_max_price))
        self.result_logger.info("# STL_EXE: %s: LOG_MIN_PRICE=%s" % (meta_time, self.log_min_price))
        self.result_logger.info("# STL_EXE: %s: PROFIT=%s" % (meta_time, profit))

    def load_model(self, filename):
        model_filename = "%s/../model/master/%s.json" % (self.current_path, filename)
        weights_filename = "%s/../model/master/%s.hdf5" % (self.current_path, filename)

        print(model_filename)
        print(weights_filename)

        json_string = open(model_filename).read()
        learning_model = model_from_json(json_string)
        learning_model.load_weights(weights_filename)

        return learning_model


