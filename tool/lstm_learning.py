# coding: utf-8
####################################################
# Learning and save build model

import os, sys
current_path = os.path.abspath(os.path.dirname(__file__))
base_path = current_path + "/.."
sys.path.append(base_path)
sys.path.append(base_path + "/lib")
sys.path.append(base_path + "/obj")
sys.path.append(base_path + "/lstm_lib")

from lstm_model_wrapper import train_save_model

learning_model1h = train_save_model(window_size=24, output_train_index=8, table_type="1h", figure_filename="figure_1h.png", model_filename="lstm_1h.json", weights_filename="lstm_1h.hdf5", start_time="2017-03-01 00:00:00", end_time="2018-04-01 00:00:00", term="all")
#learning_model5m = train_save_model(window_size=8*12, output_train_index=12, table_type="5m", figure_filename="figure_5m.png", model_filename="lstm_5m.json", weights_filename="lstm_5m.hdf5", start_time="2017-03-01 00:00:00", end_time="2018-04-01 00:00:00", term="all")
learning_model1d = train_save_model(window_size=10, output_train_index=1, table_type="day", figure_filename="figure_1d.png", model_filename="lstm_1d.json", weights_filename="lstm_1d.hdf5", start_time="2017-03-01 00:00:00", end_time="2018-04-01 00:00:00", term="all")

