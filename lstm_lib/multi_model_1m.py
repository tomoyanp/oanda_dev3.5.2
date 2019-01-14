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
from common import decideMarket
from logging import getLogger

import traceback
import subprocess
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
import json

mysql_connector = MysqlConnector()
instruments = sys.argv[1]
table_type = sys.argv[2]
#print(instruments)

def get_original_dataset(target_time, table_type, span, direct):
    daily_target_time = target_time - timedelta(days=1)
    target_time = target_time.strftime("%Y-%m-%d %H:%M:%S")
    daily_target_time = daily_target_time.strftime("%Y-%m-%d %H:%M:%S")

    if direct == "ASC" or direct == "asc":
        train_original_sql = "select end_price, sma20, sma40, sma80, sma100, insert_time, uppersigma3, lowersigma3 from %s_%s_TABLE where insert_time >= \'%s\' order by insert_time %s limit %s" % (instrument, table_type, target_time, direct, span)
    else:
        train_original_sql = "select end_price, sma20, sma40, sma80, sma100, insert_time, uppersigma3, lowersigma3 from %s_%s_TABLE where insert_time < \'%s\' order by insert_time %s limit %s" % (instrument, table_type, target_time, direct, span)

    response = mysql_connector.select_sql(train_original_sql)

    print("#### sql ####")
    print(train_original_sql)
    print(target_time)
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

    if direct == "DESC" or direct == "desc":
        end_price_list.reverse()
        sma20_list.reverse()
        sma40_list.reverse()
        sma80_list.reverse()
        sma100_list.reverse()
        insert_time_list.reverse()
        uppersigma3_list.reverse()
        lowersigma3_list.reverse()


    daily_train_original_sql = "select max_price, min_price, uppersigma2, lowersigma2, end_price from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instrument, table_type, daily_target_time)
    response = mysql_connector.select_sql(train_original_sql)
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





def get_original_dataset(target_time, table_type, span, direct):
    target_time = target_time.strftime("%Y-%m-%d %H:%M:%S")

    if direct == "ASC" or direct == "asc":
        where_statement = "insert_time >= \'%s\'" % target_time
    else:
        where_statement = "insert_time < \'%s\'" % target_time

    close_price_list = []
    high_price_list = []
    low_price_list = []
    insert_time_list = []


    train_original_sql = "select close_ask, close_bid, high_ask, high_bid, low_ask, low_bid, insert_time from %s_%s_TABLE where %s order by insert_time %s limit %s" % (instruments, table_type, where_statement, direct, span)
    response = mysql_connector.select_sql(train_original_sql)


    for res in response:
        close_price_list.append((res[0]+res[1])/2)
        high_price_list.append((res[2]+res[3])/2)
        low_price_list.append((res[4]+res[5])/2)
        insert_time_list.append(res[6])

    if direct == "ASC" or direct == "asc":
        pass
    else:
        close_price_list.reverse()
        high_price_list.reverse()
        low_price_list.reverse()
        insert_time_list.reverse()
        print("#########################")
        print(insert_time_list[0])

    tmp_original_dataset = {
        "close_price": close_price_list,
        "high_price": high_price_list,
        "low_price": low_price_list,
        "insert_time": insert_time_list
    }


    tmp_dataframe = pd.DataFrame(tmp_original_dataset)

    #print(tmp_dataframe)
    return tmp_dataframe

def build_to_normalization( dataset):
    tmp_df = pd.DataFrame(dataset)
    np_list = np.array(tmp_df)
    scaler = MinMaxScaler(feature_range=(0,1))
    scaler.fit_transform(np_list)

    return scaler

def change_to_normalization( model, dataset):
    tmp_df = pd.DataFrame(dataset)
    np_list = np.array(tmp_df)
    normalization_list = model.transform(np_list)

    return normalization_list


def create_train_dataset( dataset, learning_span, window_size):
    input_train_data = []
    for i in range(0, (learning_span-window_size)):
        temp = dataset[i:i+window_size].copy()
        model = build_to_normalization(temp)
        temp = change_to_normalization(model, temp)
        input_train_data.append(temp)

    input_train_data = np.array(input_train_data)

    return input_train_data

def build_learning_model( inputs, output_size, neurons, activ_func="linear", dropout=0.25, loss="mae", optimizer="adam"):
    model = Sequential()
    model.add(LSTM(neurons, input_shape=(inputs.shape[1], inputs.shape[2])))
    model.add(Dropout(dropout))
    model.add(Dense(units=output_size))
    model.add(Activation(activ_func))
    model.compile(loss=loss, optimizer=optimizer)

    return model

def change_to_ptime( time):
    return datetime.strptime(time, "%Y-%m-%d %H:%M:%S")

def decideConditions( table_type, target_time):
    return True


def decideTerm( hour):
    term = None
    if 5 <= hour < 13:
        term = "morning"
    if 13 <= hour < 21:
        term = "daytime"
    if 21 <= hour or hour < 6:
        term = "night"

    return term


def decide_market(base_time, table_type):
    flag = True

    sql = "select * from %s_1h_TABLE where insert_time = \'%s\'" % (instruments, base_time)
    response = mysql_connector.select_sql(sql)
    #print(response)
    if len(response) == 0:
        flag = False

    
    return flag


def train_save_model(window_size, output_train_index, table_type, figure_filename, model_filename, weights_filename, start_time, end_time, term):
    command = "ls ../model/ | grep -e %s -e %s | wc -l" % (model_filename, weights_filename)
    out = subprocess.getoutput(command)
    if int(out) < 2:
        start_ptime = change_to_ptime(start_time)
        end_ptime = change_to_ptime(end_time)

        target_time = start_ptime

        train_input_dataset = []
        train_output_dataset = []
        train_time_dataset = []
        input_max_price = []
        input_min_price = []

        predict_currency = "close_price"

        while target_time < end_ptime:
            hour = target_time.hour
            if decide_market(target_time, table_type):
                if decideTerm(hour) == term or term == "all":
                    if decideConditions(table_type, target_time):
                    #if 1==1:
                        #print("term=%s, target_time=%s" % (term, target_time))
                        # 未来日付に変えて、教師データと一緒にまとめて取得
                        tmp_target_time = target_time - timedelta(hours=1)
                        tmp_dataframe = get_original_dataset(target_time, table_type, span=window_size, direct="DESC")
                        tmp_output_dataframe = get_original_dataset(target_time, table_type, span=output_train_index, direct="ASC")
    
                        tmp_dataframe = pd.concat([tmp_dataframe, tmp_output_dataframe])
                        tmp_time_dataframe = tmp_dataframe.copy()["insert_time"]
#                        input_max_price.append(max(tmp_dataframe["end_price"]))
#                        input_min_price.append(min(tmp_dataframe["end_price"]))

                        input_max_price.append(max(tmp_dataframe[predict_currency]))
                        input_min_price.append(min(tmp_dataframe[predict_currency]))
    
                        del tmp_dataframe["insert_time"]
    
                        tmp_time_dataframe = pd.DataFrame(tmp_time_dataframe)
                        tmp_time_input_dataframe = tmp_time_dataframe.iloc[:window_size, 0]
                        tmp_time_output_dataframe = tmp_time_dataframe.iloc[-1, 0]
    
                        #print("=========== train list ============")
                        #print(tmp_time_input_dataframe)
                        #print("=========== output list ============")
                        #print(tmp_time_output_dataframe)
    
                        #print(tmp_dataframe)
                        tmp_np_dataset = tmp_dataframe.values
                        normalization_model = build_to_normalization(tmp_np_dataset)
                        tmp_np_normalization_dataset = change_to_normalization(normalization_model, tmp_np_dataset)
                        tmp_dataframe = pd.DataFrame(tmp_np_normalization_dataset)
    
                        tmp_input_dataframe = tmp_dataframe.copy().iloc[:window_size, :]
                        tmp_output_dataframe = tmp_dataframe.copy().iloc[-1, 0]
    
                        tmp_input_dataframe = tmp_input_dataframe.values
    
    
                        train_time_dataset.append(tmp_time_output_dataframe)
                        train_input_dataset.append(tmp_input_dataframe)
                        train_output_dataset.append(tmp_output_dataframe)

            if table_type == "1m":
                target_time = target_time + timedelta(minutes=1)
            elif table_type == "5m":
                target_time = target_time + timedelta(minutes=5)
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

        print(train_input_dataset.shape)
        print(train_output_dataset.shape)
        learning_model = build_learning_model(train_input_dataset, output_size=1, neurons=200)
        history = learning_model.fit(train_input_dataset, train_output_dataset, epochs=500, batch_size=1, verbose=2, shuffle=True)
        #history = learning_model.fit(train_input_dataset, train_output_dataset, epochs=1, batch_size=1, verbose=2, shuffle=False)
        train_predict = learning_model.predict(train_input_dataset)

        # 正規化戻しする
        paint_train_predict = []
        paint_train_output = []

        for i in range(len(input_max_price)):
            paint_train_predict.append((train_predict[i][0]*(input_max_price[i]-input_min_price[i])) + input_min_price[i])
            paint_train_output.append((train_output_dataset[i]*(input_max_price[i]-input_min_price[i])) + input_min_price[i])

        ### paint predict train data
        fig, ax1 = plt.subplots(1,1)
        ax1.plot(train_time_dataset, paint_train_predict, label="Predict", color="blue")
        ax1.plot(train_time_dataset, paint_train_output, label="Actual", color="red")

        plt.savefig(figure_filename)

        # モデルの保存
        model_filename = "../model/%s" % model_filename
        weights_filename = "../model/%s" % weights_filename
        json_string = learning_model.to_json()
        open(model_filename, "w").write(json_string)
        learning_model.save_weights(weights_filename)

    return learning_model


if __name__ == "__main__":
#    instruments = sys.argv[1]
    start_time = "2016-01-01 00:00:00"
    end_time = "2017-01-01 00:00:00"
    model_name = "multi_model"
    window_size = 60
    output_train_index = 60 
    filename = "%s_%s_%s" % (model_name, instruments, table_type)
    learning_model1h = train_save_model(window_size=window_size, output_train_index=output_train_index, table_type=table_type, figure_filename="%s.png" % filename, model_filename="%s.json" % filename, weights_filename="%s.hdf5" % filename, start_time=start_time, end_time=end_time, term="all")

