# coding: utf-8
####################################################
# Learning and save build model
# if 5m end_price greater than uppersigma3_5m, Do learning

import os, sys
current_path = os.path.abspath(os.path.dirname(__file__))
base_path = current_path + "/.."
sys.path.append(base_path)
sys.path.append(base_path + "/lib")
sys.path.append(base_path + "/obj")
sys.path.append(base_path + "/lstm_lib")

from mysql_connector import MysqlConnector
from datetime import timedelta, datetime
from common import decideMarket, complement_offlinetime

import traceback
import subprocess
import pandas as pd
from memory_profiler import profile

import numpy as np
import matplotlib.pyplot as plt

from keras.models import Sequential
from keras.layers import Activation, Dense
from keras.layers import LSTM
from keras.layers import Dropout
from keras.models import model_from_json
from keras.callbacks import EarlyStopping
from sklearn.preprocessing import MinMaxScaler
import json

class LstmWrapper():
    def __init__(self, neurons, window_size, instrument):
        self.mysql_connector = MysqlConnector()
        self.instrument_list = ["EUR_USD", "USD_JPY", "AUD_USD", "GBP_USD"]
        self.predict_instrument = instrument
        for i in range(0, len(self.instrument_list)):
            if instrument == self.instrument_list[i]:
                del(self.instrument_list[i])
                break
        self.instrument_list.insert(0, instrument)


        self.learning_model = Sequential()
        # add dataset 3dimention size
        self.learning_model.add(LSTM(neurons, input_shape=(window_size, len(self.instrument_list))))
        # self.learning_model.add(Dropout(0.25))
        self.learning_model.add(Dense(units=1))
        #self.learning_model.add(Activation("linear"))
        self.learning_model.add(Activation("sigmoid"))
        #self.learning_model.compile(loss="mae", optimizer="adam")
        self.learning_model.compile(loss="mae", optimizer="RMSprop")


    def get_original_dataset(self, target_time, table_type, span, direct):
        target_time = target_time.strftime("%Y-%m-%d %H:%M:%S")
    
        if direct == "ASC" or direct == "asc":
            where_statement = "insert_time >= \'%s\'" % target_time
        else:
            where_statement = "insert_time < \'%s\'" % target_time
    
    
        tmp_original_dataset = {}
    
        for instrument in self.instrument_list:
            tmp_original_dataset[instrument] = []
            train_original_sql = "select close_ask, close_bid from %s_%s_TABLE where %s order by insert_time %s limit %s" % (instrument, table_type, where_statement, direct, span)
            response = self.mysql_connector.select_sql(train_original_sql)
    
            for res in response:
                tmp_original_dataset[instrument].append((res[0]+res[1])/2)
    
            if direct == "ASC" or direct == "asc":
                pass
            else:
                tmp_original_dataset[instrument].reverse()
    
    
        # insert_timeだけ別でリストを作る
        instrument = self.instrument_list[0]
        sql = "select insert_time from %s_%s_TABLE where %s order by insert_time %s limit %s" % (instrument, table_type, where_statement, direct, span)
    
        response = self.mysql_connector.select_sql(sql)
    
        tmp_original_dataset["insert_time"] = []
        for res in response:
            tmp_original_dataset["insert_time"].append(res[0])
    
    
        if direct == "ASC" or direct == "asc":
            pass
        else:
            tmp_original_dataset["insert_time"].reverse()
    
    
        tmp_dataframe = pd.DataFrame(tmp_original_dataset)
    
        #del response
        #del tmp_original_dataset
    
        return tmp_dataframe

    def build_to_normalization(self, dataset):
        tmp_df = pd.DataFrame(dataset)
        np_list = np.array(tmp_df)
        scaler = MinMaxScaler(feature_range=(0,1))
        scaler.fit_transform(np_list)
    
        #del tmp_df
        #del np_list
    
        return scaler

    def change_to_normalization(self, model, dataset):
        tmp_df = pd.DataFrame(dataset)
        np_list = np.array(tmp_df)
        normalization_list = model.transform(np_list)
    
        #del tmp_df
        #del np_list
    
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

    def change_to_ptime(self, time):
        return datetime.strptime(time, "%Y-%m-%d %H:%M:%S")

    def create_model(self, window_size, output_train_index, table_type, start_time, end_time, neurons, epochs, predict_currency):
        start_ptime = self.change_to_ptime(start_time)
        end_ptime = self.change_to_ptime(end_time)

        # 土日の取引時間外を補完する
        start_ptime = complement_offlinetime(start_ptime, end_ptime)
    
        target_time = start_ptime
    
        train_input_dataset = []
        train_output_dataset = []
        train_time_dataset = []
        input_max_price = []
        input_min_price = []
    
        print("start")
        while target_time < end_ptime:
            if decideMarket(target_time):
                hour = target_time.hour
                # 未来日付に変えて、教師データと一緒にまとめて取得
                tmp_dataframe = self.get_original_dataset(target_time, table_type, span=window_size, direct="DESC")
                tmp_output_dataframe = self.get_original_dataset(target_time, table_type, span=output_train_index, direct="ASC")
                print(tmp_dataframe)
        
                tmp_dataframe = pd.concat([tmp_dataframe, tmp_output_dataframe])
                tmp_time_dataframe = tmp_dataframe.copy()["insert_time"]
        
                input_max_price.append(max(tmp_dataframe[predict_currency]))
                input_min_price.append(min(tmp_dataframe[predict_currency]))
        
                del tmp_dataframe["insert_time"]
        
                tmp_time_dataframe = pd.DataFrame(tmp_time_dataframe)
                tmp_time_input_dataframe = tmp_time_dataframe.iloc[:window_size, 0]
                tmp_time_output_dataframe = tmp_time_dataframe.iloc[-1, 0]
        
                tmp_np_dataset = tmp_dataframe.values
                normalization_model = self.build_to_normalization(tmp_np_dataset)
                tmp_np_normalization_dataset = self.change_to_normalization(normalization_model, tmp_np_dataset)
                tmp_dataframe = pd.DataFrame(tmp_np_normalization_dataset)
        
                tmp_input_dataframe = tmp_dataframe.copy().iloc[:window_size, :]
                tmp_output_dataframe = tmp_dataframe.copy().iloc[-1, 0]
        
                tmp_input_dataframe = tmp_input_dataframe.values
        
        
                train_time_dataset.append(tmp_time_output_dataframe)
                train_input_dataset.append(tmp_input_dataframe)
                train_output_dataset.append(tmp_output_dataframe)

                #del tmp_dataframe
                #del tmp_output_dataframe
                #del tmp_time_dataframe
                #del tmp_input_dataframe
                #del tmp_np_dataset
                #del normalization_model
                #del tmp_np_normalization_dataset
 
            else:
                pass
    
            # usually
            if table_type == "1m":
                target_time = target_time + timedelta(minutes=1)
            elif table_type == "5m":
                target_time = target_time + timedelta(minutes=5)
            elif table_type == "15m":
                target_time = target_time + timedelta(minutes=15)
            elif table_type == "30m":
                target_time = target_time + timedelta(minutes=30)
            elif table_type == "1h":
                target_time = target_time + timedelta(hours=1)
            elif table_type == "3h":
                target_time = target_time + timedelta(hours=3)
            elif table_type == "8h":
                target_time = target_time + timedelta(hours=8)
            elif table_type == "day":
                target_time = target_time + timedelta(days=1)
            else:
                raise
    
    
        train_input_dataset = np.array(train_input_dataset)
        train_output_dataset = np.array(train_output_dataset)
    
        es_cb = EarlyStopping(monitor="val_loss", patience=0, verbose=0, mode="auto")
        history = self.learning_model.fit(train_input_dataset, train_output_dataset, epochs=epochs, batch_size=256, verbose=2, shuffle=False, callbacks=[es_cb])
    
        #del train_input_dataset
        #del train_output_dataset
        #del train_time_dataset
        #del history
    

        return self.learning_model

    def predict_value(self, base_time, learning_model, window_size, table_type, output_train_index, predict_currency):
        predict_value = 0
        target_time = base_time
    
        # パーフェクトオーダーが出てるときだけを教師データとして入力する
        tmp_dataframe = self.get_original_dataset(target_time, table_type, span=window_size, direct="DESC")
    
        # 正規化を戻したいので、高値安値を押さえておく
        output_max_price = max(tmp_dataframe[predict_currency])
        output_min_price = min(tmp_dataframe[predict_currency])
    
        # 正規化したいのでtimestampを落とす
        del tmp_dataframe["insert_time"]
        test_dataframe_dataset = tmp_dataframe.copy().values
    
        # outputは別のモデルで正規化する
        model = self.build_to_normalization(test_dataframe_dataset)
        test_normalization_dataset = self.change_to_normalization(model, test_dataframe_dataset)
    
        # データが1セットなので空配列に追加してndarrayに変換する
        test_input_dataset = []
        test_input_dataset.append(test_normalization_dataset)
        test_input_dataset = np.array(test_input_dataset)
    
        test_predict = learning_model.predict(test_input_dataset)
        predict_value = test_predict[0][0]
        predict_value = (predict_value*(output_max_price-output_min_price))+output_min_price
    
        #del tmp_dataframe
        #del test_dataframe_dataset
        #del test_normalization_dataset
        #del test_predict
    
        return predict_value

