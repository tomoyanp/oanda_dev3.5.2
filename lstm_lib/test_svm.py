# coding: utf-8
import sys
import os
import traceback
import pickle

# 実行スクリプトのパスを取得して、追加
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path + "/../")
sys.path.append(current_path + "/../lib")

import numpy as np
import pandas as pd
from sklearn import datasets
from sklearn.cross_validation import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from common import get_bollinger, change_to_targettime, decideMarket, get_sma, change_to_nexttime, change_to_ptime
from mysql_connector import MysqlConnector
from sklearn.metrics import accuracy_score

######################################
# explanation of the dataset
# 1. close          = before_closeprice     - close_price 
# 2. high           = high_price            - close_price
# 3. low            = low_price             - close_price
# 4. bollinger_high = bollinger_uppersigma2 - close_price
# 5. bollinger_low  = bollinger_lowersigma2 - close_price
# 6. sma25          = sma20                 - close_price
# 7. sma75          = sma75                 - close_price
# 8. sma100         = sma100                - close_price
#####################################

# 1分足から、1分後を予測

def __get_datasets(con, instrument, starttime, endtime, tabletype, y_index):
    x_list = []
    y_list = []
    while starttime < endtime:
        if decideMarket(starttime):
            targettime = change_to_targettime(starttime, tabletype)


            sql = "select close_ask, close_bid, high_ask, high_bid, low_ask, low_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instrument, tabletype, targettime)
            response = con.select_sql(sql)
            close_ask = response[0][0]
            close_bid = response[0][1]
            close_price = (response[0][0] + response[0][1]) / 2



            before_targettime = change_to_targettime(targettime, tabletype)
            sql = "select close_ask, close_bid, high_ask, high_bid, low_ask, low_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instrument, tabletype, before_targettime)
            response = con.select_sql(sql)
            before_closeprice = (response[0][0] + response[0][1]) / 2

            high_price = (response[0][2] + response[0][3]) / 2
            low_price = (response[0][4] + response[0][5]) / 2
            bollinger_dataset = get_bollinger(con, instrument, targettime, tabletype, window_size=21, sigma_valiable=2)
            uppersigma = bollinger_dataset["upper_sigmas"][-1]
            lowersigma = bollinger_dataset["lower_sigmas"][-1]
            sma25 = get_sma(instrument, targettime, tabletype, length=25,con=con)
            sma75 = get_sma(instrument, targettime, tabletype, length=75, con=con)
            sma100 = get_sma(instrument, targettime, tabletype, length=100, con=con)

            tmp = []
            tmp.append(before_closeprice - close_price)
            tmp.append(high_price - close_price)
            tmp.append(low_price - close_price)
            tmp.append(uppersigma - close_price)
            tmp.append(lowersigma - close_price)
            tmp.append(sma25 - close_price)
            tmp.append(sma75 - close_price)
            tmp.append(sma100 - close_price)

            x_list.append(tmp)

            y_targettime = change_to_nexttime(targettime, tabletype, index=y_index)
            sql = "select close_ask, close_bid, high_ask, high_bid, low_ask, low_bid from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instrument, tabletype, y_targettime)
            response = con.select_sql(sql)
            y_closeprice = (response[0][0] + response[0][1])/2
            y_closeask = response[0][0]
            y_closebid = response[0][1]
#            if close_price < y_closeprice:
            if close_ask < y_closebid:
                y_list.append(1)
            else:
                y_list.append(0)

        starttime = change_to_nexttime(starttime, tabletype, index=1)
        print(starttime)

    return x_list, y_list


if __name__ == "__main__":
    # Get data and split traindata and testdata
    #iris = datasets.load_iris()
    #x = iris.data[:, [2,3]]
    #y = iris.target

    con = MysqlConnector()
    instrument = "USD_JPY"
    starttime = "2019-01-01 06:00:00"
    endtime = "2019-01-01 09:00:00"
    starttime = change_to_ptime(starttime)
    endtime = change_to_ptime(endtime)

    tabletype = "1m"
    y_index = 5
    x, y = __get_datasets(con, instrument, starttime, endtime,tabletype,  y_index)
    print(x)
    print(y)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=None)
    
    # Normalize Dataset
    sc = StandardScaler()
    sc.fit(x_train)
    x_train_std = sc.transform(x_train)
    x_test_std = sc.transform(x_test)
    
    # create model
    model = SVC(kernel="linear", random_state=None)
    
    # learning
    model.fit(x_train_std, y_train)
    
    pred_train = model.predict(x_train_std)
    accuracy_train = accuracy_score(y_train, pred_train)
    print("test results = %s" % accuracy_train)

    filename = 'svm.sav'
    pickle.dump(model, open(filename, 'wb'))


