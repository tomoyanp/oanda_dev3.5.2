#coding: utf-8
import sys
import os
import random
import pickle
from datetime import datetime
from logging import getLogger, FileHandler, DEBUG
# 実行スクリプトのパスを取得して、追加
# confusion matrixは横の行が実際、縦の列が予想
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path + "/../")
sys.path.append(current_path + "/../lib")



from common import get_bollinger, change_to_targettime, decideMarket, get_sma, change_to_nexttime, change_to_ptime
from sklearn.model_selection import train_test_split
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

## set parameters
instrument = sys.argv[1]
tabletype = sys.argv[2]
window_size = int(sys.argv[3])
y_index = int(sys.argv[4])

now = datetime.now()
now = now.strftime("%Y%m%d%H%M%S")
debug_logfilename = "learningwr_%s.log" % now
debug_logger = getLogger("debug")
debug_fh = FileHandler(debug_logfilename, "a+")
debug_logger.addHandler(debug_fh)
debug_logger.setLevel(DEBUG)



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

def __get_dataset(con, instrument, starttime, tabletype, y_index, y_condition):
    targettime = change_to_targettime(starttime, tabletype)
    close_ask, close_bid, high_ask, high_bid, low_ask, low_bid, insert_time = __get_price(con, targettime, tabletype, instrument)
    closeprice = (close_ask + close_bid)/2
    high_price = (high_ask + high_bid) / 2
    low_price = (low_ask + low_bid) / 2
    
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
         "insert_time": []
        }
    x["bef_closeprice"].append(float(closeprice))
    x["high_price"].append(float(high_price))
    x["low_price"].append(float(low_price))
    x["uppersigma"].append(float(uppersigma))
    x["lowersigma"].append(float(lowersigma))
    x["sma25"].append(float(sma25))
    x["sma75"].append(float(sma75))
    x["sma100"].append(float(sma100))
    x["insert_time"].append(insert_time)
    
    x = pd.DataFrame(x)

    del x["insert_time"]
#    x = x - closeprice

    y_tabletype = "1m"
    y_targettime = change_to_nexttime(starttime, y_tabletype, index=y_index)
    y_close_ask, y_close_bid, y_high_ask, y_high_bid, y_low_ask, y_low_bid, y_insert_time = __get_price(con, y_targettime, y_tabletype, instrument)
    print("%s | %s | %s" % (starttime, targettime, y_targettime))
    if close_ask < (y_close_bid-y_condition):
        y = 1
    else:
        y = 0


    return x, y

def get_datasets(con, instrument, starttime, endtime, tabletype, y_index, y_condition):
    x_list = []
    y_list = []
    while starttime < endtime:
        debug_logger.info(starttime)
        if decideMarket(starttime):
            x, y = __get_dataset(con, instrument, starttime, tabletype, y_index, y_condition)
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
    labels=[0,0.5,1]
    cfmatrix = confusion_matrix(y_test, pred_train, labels=labels)
    cfmatrix = pd.DataFrame(cfmatrix, columns=labels, index=labels)
    fmeasure = f1_score(y_test, pred_train)
    print("%s accuracy = %s" % (modelname, accuracy_train))
    print("%s fmeasure = %s" % (modelname, fmeasure))
    print("%s confusion_matrix is below" % (modelname))
    print(cfmatrix)
    filename = '%s.sav' % modelname
    pickle.dump(model, open(filename, 'wb'))

def num_to_label(dataset, label_map):
    dataset = np.array(dataset, dtype="unicode")
    print(dataset)
    
    for key in label_map.keys():
        dataset = np.where(dataset == label_map[key], key, dataset)

    dataset = dataset.tolist()

    return dataset

def label_to_num(dataset, label_map):
    dataset = np.array(dataset, dtype="unicode")
    
    for key in label_map.keys():
        dataset = np.where(dataset == label_map[key], float(key), dataset)

    dataset = np.array(dataset, dtype="float16")
    dataset = dataset.tolist()

    return dataset

def create_lstm_dataset(x, y):
    rt_x = []
    rt_y = []
    for i in range(0, len(x)-window_size):
        rt_x.append(x[i:(window_size+i)])
        rt_y.append(y[window_size+i-1])

    rt_x = np.array(rt_x)
    rt_y = np.array(rt_y)

    return rt_x, rt_y

def resample_dataset(x, y, labels, rsmtype):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if rsmtype == "up":
        count_list = []
        for label in labels:
            count_list.append(np.sum(y == label))
   
        max_count = max(count_list) 
        for label in labels:
            index_list = np.where(y == label)
            index_list = index_list[0]
            index_list = index_list.tolist()
            label_count = np.sum(y == label)
            label_count = max_count - label_count
    
            for i in range(0, label_count):
                rand_num = random.choice(index_list)
                y = np.append(y, [y[rand_num]], axis=0)
                x = np.append(x, [x[rand_num]], axis=0)
            
            print("label = %s, count = %s" % (label, np.sum(y == label)))
 
    elif rsmtype == "down":
        count_list = []
        for label in labels:
            count_list.append(np.sum(y == label))
    
        min_count = min(count_list) 
        for label in labels:
            label_count = np.sum(y == label)
            label_count = label_count - min_count
    
            for i in range(0, label_count):
                index_list = np.where(y == label)
                index_list = index_list[0]
                index_list = index_list.tolist()
    
                rand_num = random.choice(index_list)
                y = np.delete(y, rand_num, 0)
                x = np.delete(x, rand_num, 0)
                index_list.remove(rand_num)
    
            
            print("label = %s, count = %s" % (label, np.sum(y == label)))
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return x, y


#if __name__ == "__main__":
#
#    #starttime = "2019-01-01 00:00:00"
#    starttime = "2018-03-01 00:00:00"
##    endtime = "2019-04-01 00:00:00"
#    endtime = "2018-03-01 12:00:00"
#    starttime = change_to_ptime(starttime)
#    endtime = change_to_ptime(endtime)
#    tabletype = "1m"
#    con = MysqlConnector()
#    label_map = {"down" : "0.0", "flat": "0.5", "up": "1.0"}
#
#    # get train data set
#    x, y = get_datasets(con, instrument, starttime, endtime, tabletype,  y_index)
#    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=None, shuffle=False)
#
#    # Normalize Dataset
#    x_train_std = normalize_data(np.array(x_train))
#    x_test_std = normalize_data(np.array(x_test))
#
#
##    ### SVM
##    modelname = "svm"
##    learning(x_train_std, x_test_std, y_train, y_test, modelname)
##
##    ### Logistic Regression
##    modelname = "lgrg"
##    learning(x_train_std, x_test_std, y_train, y_test, modelname)
##
##    ### Random Forest
##    modelname = "rf"
##    learning(x_train_std, x_test_std, y_train, y_test, modelname)
##
##    ### XGBoost
##    modelname = "xgb"
##    learning(x_train_std, x_test_std, y_train, y_test, modelname)
#
#    modelname = "lstm"
#    neurons = 100
#    epochs = 10
#
#    x_train_std, y_train = create_lstm_dataset(x_train_std, y_train)
#    x_test_std, y_test = create_lstm_dataset(x_test_std, y_test)
#
#    x_train_std, y_train = resample_dataset(x_train_std, y_train, [0,0.5,1])
#
#    dw_count = (np.sum(y_train == 0))
#    fl_count = (np.sum(y_train == 0.5))
#    up_count = (np.sum(y_train == 1))
#    model = Sequential()
#    # add dataset 3dimention size
#    model.add(LSTM(neurons, input_shape=(window_size, 8)))
#    model.add(Dense(units=1))
#    model.add(Activation("sigmoid"))
#    model.compile(loss="mae", optimizer="RMSprop")
#    es_cb = EarlyStopping(monitor="val_loss", patience=0, verbose=0, mode="auto")
#    history = model.fit(x_train_std, y_train, epochs=epochs, batch_size=256, verbose=2, shuffle=False, callbacks=[es_cb])
#
#    pred_test = model.predict(x_test_std)
#
#    pred_test = np.where(pred_test < 0.4, 0, pred_test)
#    pred_test = np.where((0.4 < pred_test) & (pred_test < 0.8), 0.5, pred_test)
#    pred_test = np.where(0.8 < pred_test, 1, pred_test)
#
#    pred_test = np.array(pred_test)
#    y_test = np.array(y_test)
#
#    labels=["down", "flat", "up"]
#    pred_test = num_to_label(pred_test, label_map)
#    y_test = num_to_label(y_test, label_map)
#
#    accuracy_test = accuracy_score(y_test, pred_test)
#    print("%s accuracy = %s" % (modelname, accuracy_test))
#    debug_logger.info("%s accuracy = %s" % (modelname, accuracy_test))
#    fmeasure = f1_score(y_test, pred_test, average='macro')
#    print("%s fmeasure = %s" % (modelname, fmeasure))
#    debug_logger.info("%s fmeasure = %s" % (modelname, fmeasure))
#    cfmatrix = confusion_matrix(y_test, pred_test, labels=labels)
#    cfmatrix = pd.DataFrame(cfmatrix, columns=labels, index=labels)
#    print("%s confusion_matrix is below" % (modelname))
#    debug_logger.info("%s confusion_matrix is below" % (modelname))
#    print(cfmatrix)
#    debug_logger.info(cfmatrix)
#
#    # モデルの保存
#    model_filename = "lstm.json"
#    weights_filename = "lstm.hdf5"
#    json_string = model.to_json()
#    open(model_filename, "w").write(json_string)
#    model.save_weights(weights_filename)


