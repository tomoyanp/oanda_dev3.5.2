#coding: utf-8
import sys
import os
import pickle

# 実行スクリプトのパスを取得して、追加
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path + "/../")
sys.path.append(current_path + "/../lib")

from common import get_bollinger, change_to_targettime, decideMarket, get_sma, change_to_nexttime, change_to_ptime
from sklearn.cross_validation import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from mysql_connector import MysqlConnector

from keras.models import Sequential
from keras.layers import Activation, Dense
from keras.layers import LSTM
from keras.layers import Dropout
from keras.models import model_from_json
from keras.callbacks import EarlyStopping
from sklearn.preprocessing import MinMaxScaler
import numpy as np
import pandas as pd


def __get_price(con, targettime, tabletype, instrument):
    sql = "select close_ask, close_bid, high_ask, high_bid, low_ask, low_bid, insert_time from %s_%s_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % (instrument, tabletype, targettime)
    response = con.select_sql(sql)
    close_ask = response[0][0]
    close_bid = response[0][1]
    high_ask = response[0][2]
    high_bid = response[0][3]
    low_ask = response[0][4]
    low_bid = response[0][5]
    insert_time = respones[0][6]

    return close_ask, close_bid, high_ask, high_bid, low_ask, low_bid, insert_time

def __get_dataset(con, instrument, targettime, tabletype, y_index):
    close_ask, close_bid, high_ask, high_bid, low_ask, low_bid, insert_time = __get_price(con, targettime, tabletype, instrument)
    closeprice = (close_ask + close_bid)/2
    high_price = (high_ask + high_bid) / 2
    low_price = (low_ask + low_bid) / 2
    
    bef_targettime = change_to_targettime(targettime, tabletype)
    bef_close_ask, bef_close_bid, bef_high_ask, bef_high_bid, bef_low_ask, bef_low_bid, bef_insert_time = __get_price(con, bef_targettime, tabletype, instrument)
    bef_closeprice = (bef_close_ask + bef_close_bid) / 2
    
    bollinger_dataset = get_bollinger(con, instrument, targettime, tabletype, window_size=21, sigma_valiable=2)
    uppersigma = bollinger_dataset["upper_sigmas"][-1]
    lowersigma = bollinger_dataset["lower_sigmas"][-1]
    sma25 = get_sma(instrument, targettime, tabletype, length=25,con=con)
    sma75 = get_sma(instrument, targettime, tabletype, length=75, con=con)
    sma100 = get_sma(instrument, targettime, tabletype, length=100, con=con)
    
    x = {"bef_closeprice": [],
         "high_price": [],
         "low_price": [],
         "uppersigma": [],
         "lowersigma": [],
         "sma25": [],
         "sma75": [],
         "sma100": [],
         "bef_insert_time": [],
         "insert_time": []
        }
    x["bef_closeprice"] = float(bef_closeprice)
    x["high_price"] = float(high_price)
    x["low_price"] = float(low_price)
    x["uppersigma"] = float(uppersigma)
    x["lowersigma"] = float(lowersigma)
    x["sma25"] = float(sma25)
    x["sma75"] = float(sma75)
    x["sma100"] = float(sma100)
    x["insert_time"] = insert_time
    x["bef_insert_time"] = bef_insert_time
    
    x = pd.DataFrame(x)
    print(x)

    del x["insert_time"]
    del x["bef_insert_time"]
    x = x - closeprice

    y_targettime = change_to_nexttime(targettime, tabletype, index=y_index)
    y_close_ask, y_close_bid, y_high_ask, y_high_bid, y_low_ask, y_low_bid = __get_price(con, y_targettime, tabletype, instrument)
#    if close_ask < y_close_bid:
    if close_ask < y_close_ask:
        y = 1
    else:
        y = 0

    return x, y

def get_datasets(con, instrument, starttime, endtime, tabletype, y_index, modelname, window_size=1):
    x_list = []
    y_list = []
    while starttime < endtime:
        print(starttime)
        if decideMarket(starttime):
            targettime = change_to_targettime(starttime, tabletype)
            if modelname == "lstm":
                count = 0
                x_rows = pd.DataFrame([])
                y_rows = []
                while count < window_size:
                    if decideMarket(targettime):
                        x, y = __get_dataset(con, instrument, targettime, tabletype, y_index)
                        count = count + 1
                        x_rows = x_rows.append(x, ignore_index=True)
                        y_rows.append(y)
                    else:
                        pass

                    targettime = change_to_targettime(targettime, tabletype)

                x = x_rows.values.tolist()
                x.reverse()
                y = y_rows[0]

            else:
                x, y = __get_dataset(con, instrument, targettime, tabletype, y_index)

            x_list.append(x)
            y_list.append(y)

        starttime = change_to_nexttime(starttime, tabletype, index=1)

    return x_list, y_list

def normalize_data(data):
    means = data.mean()
    std = data.std()
    data = (data - means)/(std)
    
    return data

if __name__ == "__main__":
    # set parameters
    instrument = "USD_JPY"
    starttime = "2019-04-08 17:30:00"
    endtime = "2019-04-08 18:00:00"
    starttime = change_to_ptime(starttime)
    endtime = change_to_ptime(endtime)
    tabletype = "1m"
    y_index = 5

    con = MysqlConnector()

    # get train data set
    modelname = "svm"
    x, y = get_datasets(con, instrument, starttime, endtime, tabletype,  y_index, modelname)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=None)

    # Normalize Dataset
    x_train_std = normalize_data(np.array(x_train))
    x_test_std = normalize_data(np.array(x_test))

    ### SVM
    # create model
    model = SVC(kernel="linear", random_state=None)
    # learning
    model.fit(x_train_std, y_train)
    pred_train = model.predict(x_train_std)
    accuracy_train = accuracy_score(y_train, pred_train)
    print("svm results = %s" % accuracy_train)
    filename = 'svm.sav'
    pickle.dump(model, open(filename, 'wb'))

    ### Logistic Regression
    # create model
    model = LogisticRegression(random_state=None)
    # learning
    model.fit(x_train_std, y_train)
    pred_train = model.predict(x_train_std)
    accuracy_train = accuracy_score(y_train, pred_train)
    print("logistic regression results = %s" % accuracy_train)
    filename = 'logistic.sav'
    pickle.dump(model, open(filename, 'wb'))

    ### Random Forest
    # create model
    model = RandomForestClassifier()
    # learning
    model.fit(x_train_std, y_train)
    pred_train = model.predict(x_train_std)
    accuracy_train = accuracy_score(y_train, pred_train)
    print("random forest results = %s" % accuracy_train)
    filename = 'rndfrst.sav'
    pickle.dump(model, open(filename, 'wb'))

    modelname = "lstm"
    window_size = 30
    neurons = 1000
    epochs = 1000

    x, y = get_datasets(con, instrument, starttime, endtime, tabletype,  y_index, modelname, window_size)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=None)

    # Normalize Dataset
    x_train_std = normalize_data(np.array(x_train))
    x_test_std = normalize_data(np.array(x_test))

    model = Sequential()
    # add dataset 3dimention size
    model.add(LSTM(neurons, input_shape=(window_size, len(x_train[0]))))
    # model.add(Dropout(0.25))
    model.add(Dense(units=1))
    #model.add(Activation("linear"))
    model.add(Activation("sigmoid"))
    #model.compile(loss="mae", optimizer="adam")
    model.compile(loss="mae", optimizer="RMSprop")
    es_cb = EarlyStopping(monitor="val_loss", patience=0, verbose=0, mode="auto")
    history = model.fit(x_train, y_train, epochs=epochs, batch_size=256, verbose=2, shuffle=False, callbacks=[es_cb])

    # モデルの保存
    model_filename = "lstm.json"
    weights_filename = "lstm.hdf5"
    json_string = model.to_json()
    open(model_filename, "w").write(json_string)
    model.save_weights(weights_filename)


