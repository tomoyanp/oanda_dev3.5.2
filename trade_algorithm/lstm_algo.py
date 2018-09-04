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
from datetime import timedelta
from logging import getLogger

import traceback

import pandas as pd

pd.set_option("display.max_colwidth", 1000)
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

from sklearn.preprocessing import MinMaxScaler


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
        self.train_save_model(base_time)

    # decide trade entry timing
    def decideTrade(self, base_time):
        trade_flag = "pass"
        try:
            weekday = base_time.weekday()
            hour = base_time.hour
            minutes = base_time.minute
            seconds = base_time.second
            current_price = self.getCurrentPrice()


            if hour == 6 and minutes == 0 and seconds < 10:
                self.train_save_model(base_time)

            # if weekday == Saturday, we will have no entry.
            if weekday == 5 and hour >= 5:
                trade_flag = "pass"

            else:
                # if spread rate is greater than 0.5, we will have no entry
                if (self.ask_price - self.bid_price) >= 0.05:
                    pass

                else:
                    trade_flag = self.decideReverseTrade(trade_flag, current_price, base_time)

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

                    elif hour == 12:
                        stl_flag = True

                    else:
                        pass

            else:
                pass

            return stl_flag
        except:
            raise


    def decideReverseStl(self, stl_flag, base_time):
        if self.order_flag:
            pass


        return stl_flag


    def decideReverseTrade(self, trade_flag, current_price, base_time):
        if trade_flag == "pass":
            hour = base_time.hour
            minutes = base_time.minute
            seconds = base_time.second

            if hour == 7 and minutes == 0 and seconds < 10:
                self.decide_predict(base_time)

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

    def get_original_dataset(self, target_time, table_type, span):
        train_original_sql = "select end_price, sma20, sma40, sma80, sma100, insert_time from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit %s" % (self.instrument, table_type, target_time, (span))

        response = self.mysql_connector.select_sql(train_original_sql)

        end_price_list = []
        sma20_list = []
        sma40_list = []
        sma80_list = []
        sma100_list = []
        insert_time_list = []

        for res in response:
            end_price_list.append(res[0])
            sma20_list.append(res[1])
            sma40_list.append(res[2])
            sma80_list.append(res[3])
            sma100_list.append(res[4])
            insert_time_list.append(res[5])

        end_price_list.reverse()
        sma20_list.reverse()
        sma40_list.reverse()
        sma80_list.reverse()
        sma100_list.reverse()
        insert_time_list.reverse()

        tmp_original_dataset = {"end_price": end_price_list,
                                "sma20": sma20_list,
                                "sma40": sma40_list,
                                "sma80": sma80_list,
                                "sma100": sma100_list,
                                "insert_time": insert_time_list}

        tmp_dataframe = pd.DataFrame(tmp_original_dataset)

        return tmp_dataframe

    def build_to_normalization(self, dataset):
        tmp_df = pd.DataFrame(dataset)
        np_list = np.array(tmp_df)
        scaler = MinMaxScaler(feature_range=(0,1))
        scaler.fit_transform(np_list)

        return scaler

    def change_to_normalization(self, model, dataset):
        tmp_df = pd.DataFrame(dataset)
        np_list = np.array(tmp_df)
        normalization_list = model.transform(np_list)

        return normalization_list


    def create_train_dataset(self, dataset, learning_span, window_size):
        input_train_data = []
        for i in range(0, (learning_span-window_size)):
            temp = dataset[i:i+window_size].copy()
            input_train_data.append(temp)

        input_train_data = np.array(input_train_data)

        return input_train_data

    def build_learning_model(self, inputs, output_size, neurons, activ_func="linear", dropout=0.25, loss="mae", optimizer="adam"):
        model = Sequential()
        model.add(LSTM(neurons, input_shape=(inputs.shape[1], inputs.shape[2])))
        model.add(Dropout(dropout))
        model.add(Dense(units=output_size))
        model.add(Activation(activ_func))
        model.compile(loss=loss, optimizer=optimizer)

        return model


    def train_save_model(self, base_time):
        window_size = 24 # 24時間単位で区切り
        learning_span = 24*20 # 1ヶ月分で学習
        output_train_index = 8 # 8時間後をラベルにする
        table_type = "1h"
        figure_filename = "figure_1h.png"
        target_time = base_time - timedelta(hours=1)


        tmp_dataframe = self.get_original_dataset(target_time, table_type, span=learning_span+output_train_index)

        # timestamp落とす前に退避
        #time_dataframe_dataset = tmp_dataframe["insert_time", output_train_index:].copy()
        time_dataframe_dataset = tmp_dataframe["insert_time"][(output_train_index+window_size):].copy()

        # 正規化したいのでtimestampを落とす
        del tmp_dataframe["insert_time"]

        #train_dataframe_dataset = tmp_dataframe[:, :-output_train_index].copy()
        train_dataframe_dataset = tmp_dataframe.copy().values[:-output_train_index]
        
        #output_dataframe_dataset = tmp_dataframe[:, output_train_index:].copy()
        output_dataframe_dataset = tmp_dataframe.copy().values[(output_train_index+window_size):]

        # 正規化を戻す際に必要
        max_price = max(tmp_dataframe["end_price"])
        min_price = min(tmp_dataframe["end_price"])

        # 全体で正規化してモデルを取得
        normalization_model = self.build_to_normalization(tmp_dataframe)

        # ビルドしたモデルで正規化する
        train_normalization_dataset = self.change_to_normalization(normalization_model, train_dataframe_dataset)
        output_normalization_dataset = self.change_to_normalization(normalization_model, output_dataframe_dataset)


        # window_sizeで分割する
        train_input_dataset = self.create_train_dataset(train_normalization_dataset, learning_span, window_size)

        # end_priceだけ抽出する
        train_output_dataset = output_normalization_dataset[:,0]

        print(train_input_dataset)
        print(train_output_dataset)

        print(train_input_dataset.shape)
        print(train_output_dataset.shape)

        learning_model = self.build_learning_model(train_input_dataset, output_size=1, neurons=50)
        history = learning_model.fit(train_input_dataset, train_output_dataset, epochs=50, batch_size=1, verbose=2, shuffle=True)

        train_predict = learning_model.predict(train_input_dataset)
        paint_train_predict = []

        for i in range(len(train_predict)):
            paint_train_predict.append(train_predict[i]*(max_price-min_price)+min_price)

        ### paint predict train data
        fig, ax1 = plt.subplots(1,1)
        ax1.plot(time_dataframe_dataset, paint_train_predict, label="Predict", color="blue")
        ax1.plot(time_dataframe_dataset, output_dataframe_dataset, label="Actual", color="red")

        plt.savefig(figure_filename)


    def predict_model(self, base_time):
        pass


    def settlementLogWrite(self, profit, base_time, stl_price, stl_method):
        self.result_logger.info("# %s at %s" % (stl_method, base_time))
        self.result_logger.info("# self.ask_price=%s" % self.ask_price)
        self.result_logger.info("# self.bid_price=%s" % self.bid_price)
        self.result_logger.info("# self.log_max_price=%s" % self.log_max_price)
        self.result_logger.info("# self.log_min_price=%s" % self.log_min_price)
        self.result_logger.info("# self.stl_logic=%s" % self.stl_logic)
        self.result_logger.info("# STL_PRICE=%s" % stl_price)
        self.result_logger.info("# PROFIT=%s" % profit)
