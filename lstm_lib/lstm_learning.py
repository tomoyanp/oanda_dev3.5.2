# coding: utf-8
# 単純なパターン+予測が外れたら決済する
from datetime import timedelta, datetime
from logging import getLogger
from lstm_wrapper import LstmWrapper
import traceback
import os
import sys
import json

window_size = 20
output_train_index = 1
neurons = 500
epochs = 1000
instrument = sys.argv[1]
start_time = sys.argv[2].strip() + " 00:00:00"
end_time = sys.argv[3].strip() + " 00:00:00"
table_type = sys.argv[4].strip()

print(instrument)
print(start_time)
print(end_time)
print(table_type)

lstm_wrapper = LstmWrapper(neurons, window_size, instrument)
print("OK")
model =  lstm_wrapper.create_model(window_size, output_train_index, table_type, start_time, end_time, neurons, epochs, instrument)

model_filename = "../model/%s_%s.json" % (instrument, table_type)
weights_filename = "../model/%s_%s.hdf5" % (instrument, table_type)
json_string = model.to_json()
open(model_filename, "w").write(json_string)
model.save_weights(weights_filename)


