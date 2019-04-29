#coding: utf-8
import sys
import os
import pickle

# 実行スクリプトのパスを取得して、追加
# confusion matrixは横の行が実際、縦の列が予想
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path + "/../")
sys.path.append(current_path + "/../lib")

from common import get_bollinger, change_to_targettime, decideMarket, get_sma, change_to_nexttime, change_to_ptime
from sklearn.cross_validation import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
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

import xgboost as xgb
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
    insert_time = response[0][6]

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
    x["bef_closeprice"].append(float(bef_closeprice))
    x["high_price"].append(float(high_price))
    x["low_price"].append(float(low_price))
    x["uppersigma"].append(float(uppersigma))
    x["lowersigma"].append(float(lowersigma))
    x["sma25"].append(float(sma25))
    x["sma75"].append(float(sma75))
    x["sma100"].append(float(sma100))
    x["insert_time"].append(insert_time)
    x["bef_insert_time"].append(bef_insert_time)
    
    x = pd.DataFrame(x)
    print(x)

    del x["insert_time"]
    del x["bef_insert_time"]
    x = x - closeprice

    y_targettime = change_to_nexttime(targettime, tabletype, index=y_index)
    y_close_ask, y_close_bid, y_high_ask, y_high_bid, y_low_ask, y_low_bid, y_insert_time = __get_price(con, y_targettime, tabletype, instrument)
#    if close_ask < y_close_bid:
##    if close_ask < y_close_ask:
#        y = 1
#    elif y_close_ask < close_bid:
#        y = 0
#    else:
#        y = 0.5


    if close_ask < y_close_ask:
        y = 1
    else:
        y = 0


    return x, y

def get_datasets(con, instrument, starttime, endtime, tabletype, y_index):
    x_list = []
    y_list = []
    while starttime < endtime:
        print(starttime)
        if decideMarket(starttime):
            targettime = change_to_targettime(starttime, tabletype)
            x, y = __get_dataset(con, instrument, targettime, tabletype, y_index)
            x = x.values.tolist()[0]
            x_list.append(x)
            y_list.append(y)

        starttime = change_to_nexttime(starttime, tabletype, index=1)

    return x_list, y_list

def normalize_data(data):
    means = data.mean()
    std = data.std()
    data = (data - means)/(std)
    
    return data


def learning(x_train, x_test, y_train, y_test, modelname):
    # create model
    if modelname == "svm":
        model = SVC(kernel="linear", random_state=None)
    elif modelname == "lgrg":
        model = LogisticRegression(random_state=None)
    elif modelname == "rf":
        model = RandomForestClassifier()
    elif modelname == "xgb":
         x_train = xgb.DMatrix(x_train, label=y_train)
         x_test = xgb.DMatrix(x_test, label=y_test)
         xgb_params = {
             "objective": "binary:logistic",
             "eval_metric": "logloss",
         }
    else:
        raise

    # learning
    if modelname == "xgb":
        model = xgb.train(xgb_params, x_train, num_boost_round=200,)
        
    else:
        model.fit(x_train, y_train)

    pred_train = model.predict(x_test)
    print(modelname)
    print(pred_train)
    pred_train = np.where(pred_train > 0.5, 1, 0)
    accuracy_train = accuracy_score(y_test, pred_train)
    labels=[0,1]
    #labels=[0,0.5,1]
    cfmatrix = confusion_matrix(y_test, pred_train, labels=labels)
    cfmatrix = pd.DataFrame(cfmatrix, columns=labels, index=labels)
    fmeasure = f1_score(y_test, pred_train)
    print("%s accuracy = %s" % (modelname, accuracy_train))
    print("%s fmeasure = %s" % (modelname, fmeasure))
    print("%s confusion_matrix is below" % (modelname))
    print(cfmatrix)
    filename = '%s.sav' % modelname
    pickle.dump(model, open(filename, 'wb'))

if __name__ == "__main__":
    # set parameters
    instrument = "USD_JPY"
    #starttime = "2019-01-01 00:00:00"
    starttime = "2019-03-01 00:00:00"
    #endtime = "2019-03-31 23:59:59"
    endtime = "2019-03-01 06:00:00"
    starttime = change_to_ptime(starttime)
    endtime = change_to_ptime(endtime)
    tabletype = "1m"
    y_index = 5
    con = MysqlConnector()

    # get train data set
    x, y = get_datasets(con, instrument, starttime, endtime, tabletype,  y_index)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=None)
    # Normalize Dataset
    x_train_std = normalize_data(np.array(x_train))
    x_test_std = normalize_data(np.array(x_test))

    ### SVM
    modelname = "svm"
    learning(x_train_std, x_test_std, y_train, y_test, modelname)

    ### Logistic Regression
    modelname = "lgrg"
    learning(x_train_std, x_test_std, y_train, y_test, modelname)

    ### Random Forest
    modelname = "rf"
    learning(x_train_std, x_test_std, y_train, y_test, modelname)

    ### XGBoost
    modelname = "xgb"
    learning(x_train_std, x_test_std, y_train, y_test, modelname)

    modelname = "lstm"
    window_size = 30
    #neurons = 1000
    #epochs = 1000
    neurons = 200
    epochs = 10



    x_train_tmp = []
    y_train_tmp = []
    x_tmp = []
    y_tmp = []
    for i in range(0, len(x_train_std)-window_size):
        x_tmp.append(x_train_std[i:(window_size+i)])
        y_tmp.append(y_train[window_size+i-1])

    x_train_tmp.append(x_tmp)
    y_train_tmp.append(y_tmp)
    x_train_std = x_train_tmp
    y_train = y_train_tmp

    x_test_tmp = []
    y_test_tmp = []
    x_tmp = []
    y_tmp = []
    for i in range(0, len(x_test_std)-window_size):
        x_tmp.append(x_test_std[i:(window_size+i)])
        y_tmp.append(y_test[window_size+i-1])

    x_test_tmp.append(x_tmp)
    y_test_tmp.append(y_tmp)
    x_test_std = x_test_tmp
    y_test = y_test_tmp


    print("=====================================")
    print(len(x_train_std))
    print(len(x_train_std[0]))
    print(len(x_train_std[0][0]))
    print(len(y_train))
    model = Sequential()
    # add dataset 3dimention size
    # model.add(LSTM(neurons, input_shape=(window_size, len(x_train_std[0]))))
    #model.add(LSTM(neurons, input_shape=(window_size, len(x_train_std[0][0][0]))))
    model.add(LSTM(neurons, input_shape=(window_size, 8)))
    # model.add(Dropout(0.25))
    model.add(Dense(units=1))
    #model.add(Activation("linear"))
    model.add(Activation("sigmoid"))
    #model.compile(loss="mae", optimizer="adam")
    model.compile(loss="mae", optimizer="RMSprop")
    es_cb = EarlyStopping(monitor="val_loss", patience=0, verbose=0, mode="auto")
    history = model.fit(x_train_std, y_train, epochs=epochs, batch_size=256, verbose=2, shuffle=False, callbacks=[es_cb])


    pred_test = model.predict(x_test_std)
    pred_test = np.where(pred_test > 0.5, 1, 0)

    pred_test_tmp = []
    for elm in pred_test:
        pred_test_tmp.append(elm)

    y_test = y_test[0]
    pred_test = pred_test_tmp

    print(pred_test)
    accuracy_test = accuracy_score(y_test, pred_test)
    #labels=[0,0.5,1]
    labels=[0,1]
    cfmatrix = confusion_matrix(y_test, pred_test, labels=labels)
    cfmatrix = pd.DataFrame(cfmatrix, columns=labels, index=labels)
    fmeasure = f1_score(y_test, pred_test)
    print("%s accuracy = %s" % (modelname, accuracy_test))
    print("%s fmeasure = %s" % (modelname, fmeasure))
    print("%s confusion_matrix is below" % (modelname))
    print(cfmatrix)
 

    # モデルの保存
    model_filename = "lstm.json"
    weights_filename = "lstm.hdf5"
    json_string = model.to_json()
    open(model_filename, "w").write(json_string)
    model.save_weights(weights_filename)


