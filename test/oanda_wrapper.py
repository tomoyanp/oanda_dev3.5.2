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

class OandaWrapper:
    def __init__(self, env, account_id, token, units):
        self.oanda = oandapyV20.API(environment=env, access_token=token)
        self.account_id = account_id
        self.units = units

    def get_price(self, currency):
        params = {"instruments": currency}

        req = pricing.PricingInfo(accountID=self.account_id, params=params)
        response = self.oanda.request(req)

        ask_price = response["prices"][0]["asks"][0]["price"]
        bid_price = response["prices"][0]["bids"][0]["price"]
        return ask_price, bid_price

    def setUnit(self, units):
        self.units = units

    def getUnit(self):
        return self.units

    def order(self, l_side, currency, stop_loss, take_profit):
        try:
            ask_price, bid_price = self.get_price(currency)
            if l_side == "buy":
                units = "+" + str(self.units)
                print(ask_price)
                take_profit_price = float(ask_price) + float(take_profit)
                stop_loss_price = float(ask_price) - float(stop_loss)
            else:
                units = "-" + str(self.units)
                take_profit_price = float(bid_price) - float(take_profit)
                stop_loss_price = float(bid_price) + float(stop_loss)

            stop_loss_price = round(stop_loss_price, 3)
            take_profit_price = round(take_profit_price, 3)

            data = {
                "order": {
                    "instrument": currency, 
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

            req = orders.OrderCreate(accountID=self.account_id, data=data)
            res = self.oanda.request(req)

            return res
        except Exception as e:
            raise

    def modify_trade(self, trade_id, stop_loss, take_profit):
        try:
            while True:
                response = self.oanda.modify_trade(self.account_id,
                    trade_id,
                    stopLoss=stop_loss,
                    takeProfit=take_profit
                )

                time.sleep(5)
                if len(response) > 0:
                    break
            return response
        except Exception as e:
            raise

    def get_trade_position(self, instrument):
        req = trades.OpenTrades(accountID=self.account_id)
        response = self.oanda.request(req)

        trade_list = response["trades"]

        order_flag = False
        if len(trade_list) > 0:
            order_flag = True

        return order_flag

    def getBalance(self):
        try:
            req = accounts.AccountSummary(accountID=self.account_id)
            response = self.oanda.request(req)

            balance = int(float(response["account"]["balance"]))

            return balance

        except:
            raise

    def get_current_trades(self):
        try:
            response = self.oanda.get_trades(self.account_id)
        except:
            raise

        return response

    def close_trade(self, currency):
        try:

            req = trades.OpenTrades(accountID=self.account_id)
            response = self.oanda.request(req)
            trade_id = response["trades"][0]["id"]


            req = trades.TradeClose(accountID=self.account_id, tradeID=trade_id)
            response = self.oanda.request(req)
            return response

        except:
            raise

