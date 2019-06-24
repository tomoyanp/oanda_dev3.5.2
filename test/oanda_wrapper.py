# coding: utf-8

from datetime import datetime, timedelta
import time

import oandapyV20
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.accounts as accounts
import re

#trade_object = {
#     "accountId": ,
#     "env",
#     "accessToken"
#}


def calc_unit(trade_account, instrument, con):
    balance = get_balance(trade_account)

    calc_instrument = instrument
    if re.search("JPY", instrument) != None:
        pass
    elif re.search("EUR", instrument) != None:
        calc_instrument = "EUR_JPY"
    elif re.search("GBP", instrument) != None:
        calc_instrument = "GBP_JPY"
    else:
        raise

    sql = "select close_ask, close_bid from %s_5s_TABLE order by insert_time desc limit 1" % calc_instrument

    response = con.select_sql(sql)    
    price = (response[0][0]+response[0][1])/2
    units = (balance/price)*25*0.8

    return units

def open_order(trade_account, instrument, l_side, units, stop_loss, take_profit):
    oanda = oandapyV20.API(environment=trade_account["env"], access_token=trade_account["accessToken"])
    try:
        stop_loss_price = round(stop_loss, 3)
        take_profit_price = round(take_profit, 3)
        if l_side == "buy":
            units = "+" + str(units)
        else:
            units = "-" + str(units)

        data = {
            "order": {
                "instrument": instrument, 
                "units": units,
                "type": "MARKET",
                "positionFill": "DEFAULT",
                "stopLossOnFill": {
                    "price": str(stop_loss_price)
                },
                "takeProfitOnFill": {
                    "price": str(take_profit_price)
                }
            }
        }

        print(data)

        req = orders.OrderCreate(accountID=trade_account["accountId"], data=data)
        res = oanda.request(req)

        return res
    except Exception as e:
        raise

def check_position(trade_account):
    oanda = oandapyV20.API(environment=trade_account["env"], access_token=trade_account["accessToken"])
    req = trades.OpenTrades(accountID=trade_account["accountId"])
    response = oanda.request(req)

    trade_list = response["trades"]

    order_flag = False
    if len(trade_list) > 0:
        order_flag = True

    return order_flag

def get_balance(trade_account):
    try:
        oanda = oandapyV20.API(environment=trade_account["env"], access_token=trade_account["accessToken"])
        req = accounts.AccountSummary(accountID=trade_account["accountId"])
        response = oanda.request(req)

        balance = int(float(response["account"]["balance"]))

        return balance

    except:
        raise

def close_position(trade_account):
    try:
        oanda = oandapyV20.API(environment=trade_account["env"], access_token=trade_account["accessToken"])
        req = trades.OpenTrades(accountID=trade_account["accountId"])
        response = oanda.request(req)
        trade_id = response["trades"][0]["id"]


        req = trades.TradeClose(accountID=trade_account["accountId"], tradeID=trade_id)
        response = oanda.request(req)
        return response

    except:
        raise

