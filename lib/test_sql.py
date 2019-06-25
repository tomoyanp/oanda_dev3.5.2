#coding: utf-8



from mysql_connector import MysqlConnector
from datetime import datetime
import time

connector = MysqlConnector()

while True:
    now = datetime.now()
    now = now.strftime("%Y-%m-%d %H:%M:%S")

    sql = "select insert_time from GBP_JPY_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % now
    response = connector.select_sql(sql)
    print("########### insert_price table###################")
    print(now)
    print(sql)
    print(response[0][0])
 
    sql = "select insert_time from GBP_JPY_1m_TABLE where insert_time < \'%s\' order by insert_time desc limit 1" % now
    response = connector.select_sql(sql)
    print("########### multi table###################")
    print(now)
    print(sql)
    print(response[0][0])
    time.sleep(60)
