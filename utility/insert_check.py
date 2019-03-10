# coding: utf-8

# 実行スクリプトのパスを取得して、追加
import sys
import os
import traceback
current_path = os.path.abspath(os.path.dirname(__file__))
current_path = current_path + "/.."
sys.path.append(current_path)
sys.path.append(current_path + "/trade_algorithm")
sys.path.append(current_path + "/obj")
sys.path.append(current_path + "/lib")
property_path = current_path + "/property"

from mysql_connector import MysqlConnector
from price_obj import PriceObj
from datetime import datetime, timedelta
from common import decideMarket, account_init, iso_jp, jp_utc, decideSeason
from get_indicator import getBollingerWrapper
from send_mail import SendMail
import time

con = MysqlConnector()
instrument = sys.argv[1] 
target_date = sys.argv[2]
target_date = datetime.strptime("%s 06:00:00" % target_date, "%Y-%m-%d %H:%M:%S")

season = decideSeason(target_date)
if season == "summer":
    pass
else:
    target_date = target_date + timedelta(hours=1)

start_time = target_date - timedelta(days=5)
end_time = target_date - timedelta(minutes=1)

print("start_time = %s" % start_time)
print("end_time = %s" % end_time)

table_list = ["1m", "5m", "1h", "3h", "8h", "day"]
master_count = [7200, 1440, 120, 40, 15, 5]
message = ""

for i in range(len(table_list)):
    sql = "select count(insert_time) from %s_%s_TABLE where insert_time >= \'%s\' and insert_time <= \'%s\' " % (instrument, table_list[i], start_time, end_time)
    response = con.select_sql(sql)

    length = response[0][0]
    message = message + "%s %s length check(expected_count - actual_count) = %s\n" % (instrument, table_list[i], master_count[i] - length)


print(message)
sendmail = SendMail("tomoyanpy@gmail.com", "tomoyanpy@gmail.com", property_path)
sendmail.set_msg(message)
sendmail.send_mail()
