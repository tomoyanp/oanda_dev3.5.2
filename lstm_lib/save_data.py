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
from learningwr import get_datasets
import numpy as np

# set parameters
instrument = sys.argv[1]
window_size = int(sys.argv[2])
y_index = int(sys.argv[3])

if __name__ == "__main__":

    # starttime = "2019-01-01 00:00:00"
    starttime = "2018-03-01 00:00:00"
    endtime = "2019-04-01 00:00:00"
    starttime = change_to_ptime(starttime)
    endtime = change_to_ptime(endtime)
    tabletype = "1m"
    con = MysqlConnector()
    label_map = {"down": "0.0", "flat": "0.5", "up": "1.0"}

    # get train data set
    x, y = get_datasets(con, instrument, starttime, endtime, tabletype,  y_index)
    np.savez_compressed("datasets.npz", x=x, y=y)
