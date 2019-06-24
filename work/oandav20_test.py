import json
from oandapyV20 import API
from oandapyV20.exceptions import V20Error
from oandapyV20.endpoints.pricing import PricingStream


accountID = "001-009-639857-001"
access_token = "8667a3c769f85ad5e92c3d16855b5ee7-64e7b74c5a4e377f83459eab8fbe05f1"
env = "live"

api = API(access_token=access_token, environment=env)


# API v20でドル円のレートを引っ張る
instruments = "USD_JPY"
s = PricingStream(accountID=accountID, params={"instruments":instruments})
try:
    n = 0
    for R in api.request(s):
        print(json.dumps(R, indent=2))
        n += 1
        if n > 1:
            s.terminate("maxrecs received: {}".format(MAXREC))
 
except V20Error as e:
    print("Error: {}".format(e))
