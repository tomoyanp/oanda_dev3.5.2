import json
from oandapyV20 import API
from oandapyV20.exceptions import V20Error
from oandapyV20.endpoints.pricing import PricingStream

import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.accounts as accounts


accountID = "001-009-639857-001"
access_token = "8667a3c769f85ad5e92c3d16855b5ee7-64e7b74c5a4e377f83459eab8fbe05f1"
env = "live"
accountID="101-009-10684893-001"
access_token="d6fa56ee0ced50ea925683cb9c316df1-8daba3977f5335ed52327c5cc54ebf5a"
env="practice"

api = API(access_token=access_token, environment=env)
req = trades.OpenTrades(accountID=accountID)
response = api.request(req)

trade_list = response["trades"]

trade_id = response["trades"][0]["id"]

req = trades.TradeClose(accountID=accountID, tradeID=trade_id)
response = api.request(req)
print(response)

#currency="EUR_JPY"
#data = {
#    "longUnits": "ALL"
#}
#req = positions.PositionClose(accountID=accountID, instrument=currency, data=data)
#response = api.request(req)
#
#print(response)

# API v20でドル円のレートを引っ張る
#instruments = "USD_JPY"
#s = PricingStream(accountID=accountID, params={"instruments":instruments})
#try:
#    n = 0
#    for R in api.request(s):
#        print(json.dumps(R, indent=2))
#        n += 1
#        if n > 1:
#            s.terminate("maxrecs received: {}".format(MAXREC))
# 
#except V20Error as e:
#    print("Error: {}".format(e))
