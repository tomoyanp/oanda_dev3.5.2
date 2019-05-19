import MySQLdb
from datetime import datetime, timedelta
from price_table_wrapper import PriceTableWrapper

class MysqlConnector:

    def __init__(self):
        self.hostname = 'db-server'
        self.dbname = 'oanda_db'
        self.username = 'tomoyan'
        self.password = 'tomoyan180'
        self.character = 'utf8'
        self.connector = MySQLdb.connect(host=self.hostname, db=self.dbname, user=self.username, passwd=self.password, charset=self.character)
        self.cursor = self.connector.cursor()

    def insert_sql(self, sql):
        try:
            self.cursor.execute(sql)
            self.connector.commit()
        except:
            self.__init__()
            self.cursor.execute(sql)
            self.connector.commit()

    def select_sql(self, sql):
        try:
            self.cursor.execute(sql)
            response = self.cursor.fetchall()
        except:
            self.__init__()
            self.cursor.execute(sql)
            response = self.cursor.fetchall()

        return response

