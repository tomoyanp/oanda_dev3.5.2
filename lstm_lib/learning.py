# coding: utf-8
import sys
import os
from datetime import datetime
from logging import getLogger, FileHandler, DEBUG
# 実行スクリプトのパスを取得して、追加
# confusion matrixは横の行が実際、縦の列が予想
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path + "/../")
sys.path.append(current_path + "/../lib")


from learninglib import num_to_label
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from keras.models import Sequential
from keras.layers import Activation, Dense
from keras.layers import LSTM
from keras.callbacks import EarlyStopping

import numpy as np
import pandas as pd

instrument = sys.argv[1]
table_type = sys.argv[2]
window_size = sys.argv[3]
y_index = sys.argv[4]
filename = sys.argv[5]

now = datetime.now()
now = now.strftime("%Y%m%d%H%M%S")
debug_logfilename = "learning_%s.log" % now
debug_logger = getLogger("debug")
debug_fh = FileHandler(debug_logfilename, "a+")
debug_logger.addHandler(debug_fh)
debug_logger.setLevel(DEBUG)


if __name__ == "__main__":
    #label_map = {"down" : "0.0", "flat": "0.5", "up": "1.0"}
    label_map = {"else": "0", "up": "1"}
    labels=["else", "up"]
    loaded_data = np.load("%s.npz" % filename)
    x_train = loaded_data["x_train"]
    y_train = loaded_data["y_train"]
    x_test = loaded_data["x_test"]
    y_test = loaded_data["y_test"]

    print(x_train.shape)
    print(y_train.shape)

    modelname = "lstm"
    neurons = 500
    epochs = 50

    model = Sequential()
    # add dataset 3dimention size
    model.add(LSTM(neurons, input_shape=(x_train.shape[1], x_train.shape[2])))
    model.add(Dense(units=1))
    model.add(Activation("sigmoid"))
    model.compile(loss="mae", optimizer="RMSprop")
    es_cb = EarlyStopping(monitor="val_loss", patience=0, verbose=0, mode="auto")
    history = model.fit(x_train, y_train, epochs=epochs, batch_size=256, verbose=2, shuffle=True, callbacks=[es_cb])

    pred_test = model.predict(x_test)

    pred_test = np.where(pred_test < 0.5, 0, 1) 

    pred_test = np.array(pred_test)
    y_test = np.array(y_test)

    pred_test = num_to_label(pred_test, label_map)
    y_test = num_to_label(y_test, label_map)
    print(y_test)

    accuracy_test = accuracy_score(y_test, pred_test)
    print("%s accuracy = %s" % (modelname, accuracy_test))
    debug_logger.info("%s accuracy = %s" % (modelname, accuracy_test))
    fmeasure = f1_score(y_test, pred_test, average='macro')
    print("%s fmeasure = %s" % (modelname, fmeasure))
    debug_logger.info("%s fmeasure = %s" % (modelname, fmeasure))
    cfmatrix = confusion_matrix(y_test, pred_test, labels=labels)
    cfmatrix = pd.DataFrame(cfmatrix, columns=labels, index=labels)
    print("%s confusion_matrix is below" % (modelname))
    debug_logger.info("%s confusion_matrix is below" % (modelname))
    print(cfmatrix)
    debug_logger.info(cfmatrix)

    # モデルの保存
    model_filename = "%s.json" % filename
    weights_filename = "%s.hdf5" % filename
    json_string = model.to_json()
    open(model_filename, "w").write(json_string)
    model.save_weights(weights_filename)


