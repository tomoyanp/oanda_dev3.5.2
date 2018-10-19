# coding: utf-8

import pandas as pd


pd.set_option("display.max_colwidth", 1000)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

import numpy as np

np.set_printoptions(threshold=np.inf)

import seaborn as sns
import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.switch_backend("agg")
import oandapy
import configparser
import datetime
import pytz
from datetime import datetime, timedelta

from keras.models import Sequential
from keras.layers import Activation, Dense
from keras.layers import LSTM
from keras.layers import Dropout
from keras.models import model_from_json

from sklearn.preprocessing import MinMaxScaler

import json

from get_indicator import getBollingerWrapper
from mysql_connector import MysqlConnector

from tensor_lib import change_to_ptime, getDataset, change_to_normalization, createTestDataset, join_dataframe

connector = MysqlConnector()
base_time = "2018-07-01 00:00:00"
train_base_time = change_to_ptime(base_time)
original_dataset, value_dataset = getDataset(train_base_time, connector, window_size=30, learning_span=300, output_train_index=1, table_layout="day")


# testデータの正規化のために、最大値と最小値を取得しておく
max_list = []
min_list = []
max_price = max(original_dataset["end"])
min_price = min(original_dataset["end"])

df = original_dataset.copy()
del df["time"]

for col in df:
    max_list.append(max(df[col]))
    min_list.append(min(df[col]))

max_list = pd.DataFrame(max_list)
min_list = pd.DataFrame(min_list)

# あとで行追加するので転置しておく
max_list = max_list.T
min_list = min_list.T

window_size = 24
learning_span = 24*60
output_train_index = 8
table_layout = "1h"
base_time = "2018-07-31 07:00:00"
test_base_time = change_to_ptime(base_time)

test_original_dataset, test_value_dataset = getDataset(test_base_time, connector, window_size, learning_span, output_train_index, table_layout)

# 訓練データの最大、最小値を追加して、正規化する
# 正規化後はdropする
tmp = test_value_dataset.copy()
tmp = pd.DataFrame(tmp)

tmp = join_dataframe(max_list, tmp)
tmp = join_dataframe(min_list, tmp)

test_value_dataset = change_to_normalization(tmp)
test_value_dataset = pd.DataFrame(test_value_dataset)
test_value_dataset = test_value_dataset.iloc[:-2]
test_value_dataset = test_value_dataset.values

input_test_data = createTestDataset(test_value_dataset, window_size, learning_span)

model_filename = "model_1h.json"
weights_filename = "weight_1h.hdf5"

json_string = open(model_filename).read()
model = model_from_json(json_string)
model.load_weights(weights_filename)

predict = model.predict(input_test_data)

print(predict.shape)
print(predict)
print((predict[0][0]*(max_price-min_price))+min_price)
print((predict[1][0]*(max_price-min_price))+min_price)

#sql = "select end_price, insert_time from GBP_JPY_day_TABLE where insert_time < \'2018-08-01 00:00:00\' order by insert_time desc limit 2"

#response = connector.select_sql(sql)
#end_price_list = []
#end_time_list = []
#for res in response:
#    end_price_list.append(res[0])
#    end_time_list.append(res[1])
#
#end_price_list.reverse()
#end_time_list.reverse()


#train_predict = scaler.inverse_transform(train_predict)
#print(train_predict)

#file = open("result.txt", "w")
#file.write(numpy_list)
#file.write("\n==============================================\n")
#file.write(normalization_list)

#file.close()
#numpy_pd = pd.DataFrame(numpy_list)
#normalization_pd = pd.DataFrame(normalization_list)
#print(numpy_pd)
#print(normalization_pd)

#numpy_list = df.values
#print numpy_list
