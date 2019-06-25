from mysql_connector import MysqlConnector

con = MysqlConnector()
file = open("sql.result", "w")


sql = "select open_ask, insert_time from AUD_JPY_1m_TABLE order by insert_time asc limit 100000"
response = con.select_sql(sql)

for res in response:
    file.write("%s, %s\n" % (res[0], res[1]))

file.close()
