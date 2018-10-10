import sys
import requests
from mysql_connector import MysqlConnector
from datetime import datetime, timedelta



con = MysqlConnector()
#sql = "select body from FUNDAMENTALS_TABLE where insert_time = \'2018-07-10 08:00:00\' order by insert_time desc limit 1"
start_time = datetime.strptime("2018-08-21 08:00:00", "%Y-%m-%d %H:%M:%S")
end_time = datetime.strptime("2018-08-22 08:00:00", "%Y-%m-%d %H:%M:%S")

while start_time < end_time:
    sql = "select body from FUNDAMENTALS_TABLE where insert_time = \'%s\' order by insert_time desc limit 1" % start_time
    response = con.select_sql(sql)

    if len(response) > 0:
        content = response[0][0]
        print(content)
        access_token = "AIzaSyD4c8ZIIqNzw_PJovRZ9qkbLZR-uafYrvk"
        url = 'https://language.googleapis.com/v1/documents:analyzeSentiment?key={}'.format(access_token)
        
        header = {'Content-Type': 'application/json'}
        body = {
            "document": {
                "type": "PLAIN_TEXT",
                "language": "JA",
                "content": content
            },
            "encodingType": "UTF8"
        }
        response = requests.post(url, headers=header, json=body).json()
        score = 0
        print(start_time)
        #print(response["documentSentiment"]["score"])
         
        for res in response["sentences"]:
            print(res["sentiment"])
            score = score + res["sentiment"]["score"]

    start_time = start_time + timedelta(days=1)
#print("total score = %s" % score)


