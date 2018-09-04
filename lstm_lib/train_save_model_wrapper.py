# coding: utf-8

import pandas as pd

pd.set_option("display.max_colwidth", 1000)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

import numpy as np
np.set_printoptions(threshold=np.inf)
import matplotlib.pyplot as plt
plt.switch_backend("agg")

from mysql_connector import MysqlConnector
from tensor_lib import change_to_ptime, getDataset, change_to_normalization, createTrainDataset, build_model, save_to_normalization_model


def train_save_model_wrapper(base_time, table_layout, output_train_index, learning_span, window_size, model_filename, weight_filename, normalization_filename, figure_filename):
    connector = MysqlConnector()
    train_base_time = change_to_ptime(base_time)

    original_dataset, value_dataset = getDataset(train_base_time, connector, window_size, learning_span, output_train_index, table_layout)

    max_price = max(original_dataset["end"])
    min_price = min(original_dataset["end"])

    value_dataset, normalization_model = change_to_normalization(value_dataset)
    input_train_data, output_train_data, time_list = createTrainDataset(value_dataset, original_dataset, window_size, learning_span, output_train_index)

    np.random.seed(202)
    model = build_model(input_train_data, output_size=1, neurons=20)
    history = model.fit(input_train_data, output_train_data, epochs=50, batch_size=1, verbose=2, shuffle=True)

    # モデルの保存
    json_string = model.to_json()
    open(model_filename, "w").write(json_string)
    model.save_weights(weight_filename)

    # 正規化モデルの保存
    save_to_normalization_model(normalization_model, normalization_filename)

    ## 訓練データで予測
    train_predict = model.predict(input_train_data)
    paint_predict = []
    paint_right = []

    # 正規化戻し
    train_predict = normalization_model.inverse_transform(train_predict)
    output_train_data = normalization_model.inverse_transform(output_train_data)

    for i in range(len(train_predict)):
        print(time_list[i])
        paint_predict.append(train_predict[i])
        paint_right.append(output_train_data[i])
#        paint_predict.append((train_predict[i]*(max_price-min_price))+min_price)
#        paint_right.append((output_train_data[i]*(max_price-min_price))+min_price)

    ### paint predict train data
    fig, ax1 = plt.subplots(1,1)
    ax1.plot(time_list, paint_predict, label="Predict", color="blue")
    ax1.plot(time_list, paint_right, label="Actual", color="red")

    plt.savefig(figure_filename)

