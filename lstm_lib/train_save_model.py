# coding: utf-8

from train_save_model_wrapper import train_save_model_wrapper


base_time = "2017-07-01 00:00:00"

# daily train
table_layout = "day"
output_train_index = 1
learning_span = 200
window_size = 5
model_filename = "model_1d.json"
weight_filename = "weight_1d.hdf5"
normalization_filename = "normalization_1d.json"
figure_filename = "figure_1d.png"

train_save_model_wrapper(base_time, table_layout, output_train_index, learning_span, window_size, model_filename, weight_filename, normalization_filename, figure_filename)

# 1h train
table_layout = "1h"
output_train_index = 8
learning_span = 24*60
window_size = 24
model_filename = "model_1h.json"
weight_filename = "weight_1h.hdf5"
normalization_filename = "normalization_1h.json"
figure_filename = "figure_1h.png"

#train_save_model_wrapper(base_time, table_layout, output_train_index, learning_span, window_size, model_filename, weight_filename, normalization_filename, figure_filename)
