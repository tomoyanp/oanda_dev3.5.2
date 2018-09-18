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
            #print(base_time)


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

            if minutes == 0 and seconds < 10:
                self.predict_value(base_time)

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
        train_original_sql = "select end_price, sma20, sma40, sma80, sma100, insert_time, uppersigma3, lowersigma3 from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit %s" % (self.instrument, table_type, target_time, (span))
        response = self.mysql_connector.select_sql(train_original_sql)

        end_price_list = []
        sma20_list = []
        sma40_list = []
        sma80_list = []
        sma100_list = []
        insert_time_list = []
        uppersigma3_list = []
        lowersigma3_list = []

        for res in response:
            end_price_list.append(res[0])
            sma20_list.append(res[1])
            sma40_list.append(res[2])
            sma80_list.append(res[3])
            sma100_list.append(res[4])
            insert_time_list.append(res[5])
            uppersigma3_list.append(res[6])
            lowersigma3_list.append(res[7])

        end_price_list.reverse()
        sma20_list.reverse()
        sma40_list.reverse()
        sma80_list.reverse()
        sma100_list.reverse()
        insert_time_list.reverse()
        uppersigma3_list.reverse()
        lowersigma3_list.reverse()


        daily_target_time = target_time - timedelta(days=1)
        daily_train_original_sql = "select max_price, min_price, uppersigma2, lowersigma2, end_price from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (self.instrument, table_type, daily_target_time)
        response = self.mysql_connector.select_sql(train_original_sql)
        daily_max_price = response[0][0]
        daily_min_price = response[0][1]
        daily_uppersigma2 = response[0][2]
        daily_lowersigma2 = response[0][3]
        daily_end_price = response[0][4]

        tmp_original_dataset = {"end_price": end_price_list,
                                "sma20": sma20_list,
                                "sma40": sma40_list,
                                "sma80": sma80_list,
                                "uppersigma3": uppersigma3_list,
                                "lowersigma3": lowersigma3_list,
                                "insert_time": insert_time_list}




        tmp_dataframe = pd.DataFrame(tmp_original_dataset)
        tmp_dataframe["sma20"] = tmp_dataframe["end_price"] - tmp_dataframe["sma20"]
        tmp_dataframe["sma40"] = tmp_dataframe["end_price"] - tmp_dataframe["sma40"]
        tmp_dataframe["sma80"] = tmp_dataframe["end_price"] - tmp_dataframe["sma80"]
        tmp_dataframe["uppersigma3"] = tmp_dataframe["end_price"] - tmp_dataframe["uppersigma3"]
        tmp_dataframe["lowersigma3"] = tmp_dataframe["end_price"] - tmp_dataframe["lowersigma3"]
        tmp_dataframe["daily_max_price"] = tmp_dataframe["end_price"] - daily_max_price
        tmp_dataframe["daily_min_price"] = tmp_dataframe["end_price"] - daily_min_price
        tmp_dataframe["daily_uppersigma2"] = tmp_dataframe["end_price"] - daily_uppersigma2
        tmp_dataframe["daily_lowersigma2"] = tmp_dataframe["end_price"] - daily_lowersigma2
        tmp_dataframe["daily_end_price"] = tmp_dataframe["end_price"] - daily_end_price

        print(tmp_dataframe)

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
            model = self.build_to_normalization(temp)
            temp = self.change_to_normalization(model, temp)
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

    def change_to_ptime(self, time):
        return datetime.strptime(time, "%Y-%m-%d %H:%M:%S")

    def train_save_model(self, base_time):
        window_size = 24 # 24時間単位で区切り
        output_train_index = 8 # 8時間後をラベルにする
        table_type = "1h"
        figure_filename = "figure_1h.png"
        start_time = "2017-02-01 00:00:00"
        end_time = "2018-04-01 00:00:00"
        start_ptime = self.change_to_ptime(start_time)
        end_ptime = self.change_to_ptime(end_time)

        target_time = start_ptime

        train_input_dataset = []
        train_output_dataset = []

        while target_time < end_ptime:

            print(target_time)
            # パーフェクトオーダーが出てるときだけを教師データとして入力する
            sql = "select sma20, sma40, sma80 from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (self.instrument, table_type, target_time)
            response = self.mysql_connector.select_sql(sql)
            sma20 = response[0][0]
            sma40 = response[0][1]
            sma80 = response[0][2]

            if (sma20 > sma40 > sma80) or (sma20 < sma40 < sma80):
                tmp_dataframe = self.get_original_dataset(target_time, table_type, span=window_size)

                # output_index以降の終わり値をラベルにする
                output_target_time = target_time + timedelta(hours=output_train_index)
                output_sql = "select end_price from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (self.instrument, table_type, output_target_time)
                response = self.mysql_connector.select_sql(output_sql)
                output_end_price = response[0][0]

                # 学習データは、教師データの価格差にする
                # tmp_dataframe["end_price"] = output_end_price - tmp_dataframe["end_price"]

                del tmp_dataframe["insert_time"]
                train_np_dataset = tmp_dataframe.copy().values

                train_input_dataset.append(train_np_dataset)
                train_output_dataset.append(output_end_price)

            target_time = target_time + timedelta(hours=1)

        train_input_dataset = np.array(train_input_dataset)
        train_output_dataset = np.array(train_output_dataset)

        # 全体で正規化してモデルを取得
        self.input_normalization_model = self.build_to_normalization(train_input_dataset)
        self.output_normalization_model = self.build_to_normalization(train_output_dataset)

        # ビルドしたモデルで正規化する
        train_input_normalization_dataset = self.change_to_normalization(self.input_normalization_model, train_input_dataset)
        train_output_normalization_dataset = self.build_to_normalization(self.output_normalization_model, train_output_dataset)

        self.learning_model = self.build_learning_model(train_input_normalization_dataset, output_size=1, neurons=50)
        history = self.learning_model.fit(train_input_normalization_dataset, train_output_normalization_dataset, epochs=50, batch_size=1, verbose=2, shuffle=False)
        train_predict = self.learning_model.predict(train_input_normalization_dataset)

        # 正規化戻し必要

#        # 正規化戻し＋浮動小数点に戻して描画
#        paint_train_predict = self.output_normalization_model.inverse_transform(train_predict).tolist()
#        paint_train_output = self.output_normalization_model.inverse_transform(train_output_dataset).tolist()

        ### paint predict train data
        fig, ax1 = plt.subplots(1,1)
        ax1.plot(time_dataframe_dataset, paint_train_predict, label="Predict", color="blue")
        ax1.plot(time_dataframe_dataset, paint_train_output, label="Actual", color="red")

        plt.savefig(figure_filename)


    def predict_value(self, base_time):
        window_size = 24 # 24時間単位で区切り
        table_type = "1h"
        output_train_index = 8 # 8時間後をラベルにする

        target_time = base_time - timedelta(hours=1)

        # パーフェクトオーダーが出てるときだけを教師データとして入力する
        sql = "select sma20, sma40, sma80 from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (self.instrument, table_type, target_time)
        response = self.mysql_connector.select_sql(sql)
        sma20 = response[0][0]
        sma40 = response[0][1]
        sma80 = response[0][2]

        if (sma20 > sma40 > sma80) or (sma20 < sma40 < sma80):
            tmp_dataframe = self.get_original_dataset(target_time, table_type, span=window_size)

            # 正規化したいのでtimestampを落とす
            del tmp_dataframe["insert_time"]
            test_dataframe_dataset = tmp_dataframe.copy().values

            # ビルドしたモデルで正規化する
#            model = self.build_to_normalization(test_dataframe_dataset)
            test_normalization_dataset = self.change_to_normalization(self.input_normalization_model, test_dataframe_dataset)

            # データが1セットなので空配列に追加してndarrayに変換する
            test_input_dataset = []
            test_input_dataset.append(test_normalization_dataset)
            test_input_dataset = np.array(test_input_dataset)

            test_predict = self.learning_model.predict(test_input_dataset)

            # 正規化戻し＋浮動小数点に戻す
            result = self.output_normalization_model.inverse_transform(test_predict).tolist()

            # 答え合わせ
            target_time = target_time + timedelta(hours=output_train_index)
            sql = "select end_price, insert_time from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (self.instrument, table_type, target_time)
            response = self.mysql_connector.select_sql(sql)
            right_price = response[0][0]
            right_time = response[0][1]
            current_price = (self.ask_price + self.bid_price)/2

            print(result)
            print("%s ==> %s" % (base_time.strftime("%Y-%m-%d %H:%M:%S"), result))
            #self.debug_logger.info("%s ===> %s" % (base_time.strftime("%Y-%m-%d %H:%M:%S"), result[0][0]))
            self.debug_logger.info("target_time, current_price, predict_value, right_time, right_price")
            self.debug_logger.info("%s, %s, %s, %s, %s" % (target_time, current_price, result[0][0], right_time, right_price))


    def settlementLogWrite(self, profit, base_time, stl_price, stl_method):
        self.result_logger.info("# %s at %s" % (stl_method, base_time))
        self.result_logger.info("# self.ask_price=%s" % self.ask_price)
        self.result_logger.info("# self.bid_price=%s" % self.bid_price)
        self.result_logger.info("# self.log_max_price=%s" % self.log_max_price)
        self.result_logger.info("# self.log_min_price=%s" % self.log_min_price)
        self.result_logger.info("# self.stl_logic=%s" % self.stl_logic)
        self.result_logger.info("# STL_PRICE=%s" % stl_price)
        self.result_logger.info("# PROFIT=%s" % profit)