# coding: utf-8
from selenium import common
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import sys
import os
import traceback
import json
from datetime import datetime, timedelta

# 実行スクリプトのパスを取得して、追加
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path)
sys.path.append(current_path + "/trade_algorithm")
sys.path.append(current_path + "/obj")
sys.path.append(current_path + "/lib")
sys.path.append(current_path + "/lstm_lib")

property_path = current_path + "/property"
config_path = current_path + "/config"

from mysql_connector import MysqlConnector

options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1280,1024')
options.add_argument('--no-sandox')
options.add_argument('--disable-dev-shm-usage')

executable_path = "/usr/local/bin/chromedriver"
driver = webdriver.Chrome(executable_path=executable_path, chrome_options=options)

start_time = "20180701"
end_time = "20180901"
#url = "http://zai.diamond.jp/list/fxnews/backnumber?date=%s&page=%s"
original_url = "http://zai.diamond.jp/list/fxnews/backnumber?"

con = MysqlConnector()

#index = 1
index = 8 
while True:
    try:
        if datetime.strptime(start_time, "%Y%m%d") > datetime.strptime(end_time, "%Y%m%d"):
            break
        else:
            url = original_url + ("date=%s" % start_time) + ("&page=%s" % index)
            print("#######################################")
            print(url)
            driver.get(url)
            date = driver.find_element_by_class_name("date")
            #print(date.text)
            main_contents = driver.find_element_by_class_name("category-backnumber-list")
            contents = main_contents.find_elements_by_class_name("clearfix")
            for content in contents:
                #print("###########################################################")
                title = content.find_element_by_tag_name("h5")
                date = content.find_element_by_class_name("date")
                bodys = content.find_elements_by_tag_name("p")
                text_body = ""
#                print("%s --- %s" % (date.text, title.text))
                for body in bodys:
                    text_body = text_body + body.text
                    #print("%s" % body.text)

                date = date.text
                tmp = date.split("（")
                tmp_date = tmp[0]
                tmp_time = tmp[1].split("）")[1]
                tmp = tmp_date + tmp_time
                tmp_date = datetime.strptime(tmp, "%Y年%m月%d日%H時%M分")
                text_date = tmp_date.strftime("%Y-%m-%d %H:%M:%S")

                text_title = title.text
                short_title = text_title[:10]

                sql = "insert into FUNDAMENTALS_TABLE(insert_time, short_title, title, body) values(\'%s\', \'%s\', \'%s\', \'%s\')" % (text_date, short_title, text_title, text_body)
                #print(sql)
                con.insert_sql(sql)
                
        
            index = index + 1

#    except common.exceptions.NoSuchElementException as e:
    except:
        message = traceback.format_exc()
        print(message)
        start_time = datetime.strptime(start_time, "%Y%m%d")
        start_time = start_time + timedelta(days=1)
        start_time = start_time.strftime("%Y%m%d")
        index = 1

    
    
    #print(content.text)
#print(contents.text)
#driver.save_screenshot('test.png')
#for x in dir(driver):
#    print(x)
