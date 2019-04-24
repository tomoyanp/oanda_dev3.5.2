# coding: utf-8
import sys
import os

# 実行スクリプトのパスを取得して、追加
# confusion matrixは横の行が実際、縦の列が予想
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path + "/../")
sys.path.append(current_path + "/../lib")

from common import change_to_ptime
from mysql_connector import MysqlConnector
from learninglib import get_datasets, train_test_split, normalize_data, create_lstm_dataset, resample_dataset
import numpy as np

# set parameters
instrument = sys.argv[1]
tabletype = sys.argv[2]
window_size = int(sys.argv[3])
y_index = int(sys.argv[4])
y_condition = float(sys.argv[5])
starttime = sys.argv[6] + " 00:00:00"
endtime = sys.argv[7] + " 00:00:00"

if __name__ == "__main__":
    starttime = change_to_ptime(starttime)
    endtime = change_to_ptime(endtime)
    con = MysqlConnector()
#    label_map = {"down": "0.0", "flat": "0.5", "up": "1.0"}
    label_map = {"else": "0", "up": "1.0"}

    # get train data set
    x, y = get_datasets(con, instrument, starttime, endtime, tabletype,  y_index, y_condition)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=None, shuffle=False)
    # Normalize Dataset
    x_train = normalize_data(np.array(x_train))
    x_test = normalize_data(np.array(x_test))

    x_train, y_train = create_lstm_dataset(x_train, y_train)
    x_test, y_test = create_lstm_dataset(x_test, y_test)

    print(x_train.shape)
    print(y_train.shape)
    x_train, y_train = resample_dataset(x_train, y_train, [0,1], "up")

    print(x_train.shape)
    print(y_train.shape)

    np.savez_compressed("datasets_%s_%s_window%s_y%s.npz" % (instrument, tabletype, window_size, y_index), x_train=x_train, y_train=y_train, x_test=x_test, y_test=y_test)




