# coding: utf-8
# 単純なパターン+予測が外れたら決済する
from datetime import timedelta, datetime
import gc
import objgraph
from memory_profiler import profile
from lstm_wrapper import LstmWrapper

def test_lstm(base_time):
    window_size = 20
    output_train_index = 1
    neurons = 400
    epochs = 20
    predict_currency = "EUR_JPY"
    lstm_wrapper = LstmWrapper()

    target_time = base_time
    table_type = "5m"
    start_time = base_time - timedelta(hours=3)
    end_time = start_time + timedelta(minutes=10)
    start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
    model5m =  lstm_wrapper.create_model(window_size, output_train_index, table_type, start_time, end_time, neurons, epochs, predict_currency)
    
    table_type = "1h"
    start_time = base_time - timedelta(hours=24)
    end_time = start_time + timedelta(hours=2)
    start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
    model1h =  lstm_wrapper.create_model(window_size, output_train_index, table_type, start_time, end_time, neurons, epochs, predict_currency)
    
    target_time = base_time - timedelta(minutes=5)
    table_type = "5m"
    predict_price5m = lstm_wrapper.predict_value(target_time, model5m, window_size, table_type, output_train_index, predict_currency)
    target_time = base_time - timedelta(hours=1)
    table_type = "1h"
    predict_price1h = lstm_wrapper.predict_value(target_time, model1h, window_size, table_type, output_train_index, predict_currency)
    target_time = base_time - timedelta(minutes=5)
    ask_price, bid_price = get_current_price(target_time)
    current_price = (ask_price + bid_price) / 2
    target_time = base_time + timedelta(hours=1)
    ask_price, bid_price = get_current_price(target_time)
    actual_price = (ask_price + bid_price) / 2


if __name__ == "__main__":
    base_time = datetime.strptime("2019-03-01 00:00:00", "%Y-%m-%d %H:%M:%S")

    while True:
        test_lstm(base_time)
        base_time = timedelta(minutes=5)


