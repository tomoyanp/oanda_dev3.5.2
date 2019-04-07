import re
import subprocess
import sys

filename = sys.argv[1].strip()

order_time = subprocess.getoutput("cat %s | grep EXE | grep trade_flag|awk '{print $3 \" \" $4}'" % filename)
tmp_time = order_time.split("\n")

order_time = []
for time in tmp_time:
    order_time.append(time[:-1])
print(order_time)

trade_flag = subprocess.getoutput("cat %s | grep EXE | grep trade_flag | awk '{print $5}'" % filename)
tmp_flag = trade_flag.split("\n")

trade_flag = []
for flag in tmp_flag:
    trade_flag.append(flag.split("=")[1])


print(trade_flag)
    
#current_price = subprocess.getoutput("cat %s  | grep EXE | grep current_price | awk '{print $5}'" % filename)
current_price = subprocess.getoutput("cat %s  | grep EXE | grep gbpjpy_price | awk '{print $5}'" % filename)
tmp_price = current_price.split("\n")

current_price = []
for price in tmp_price:
    current_price.append(price.split("=")[1])


print(current_price)
 

stl_time = subprocess.getoutput("cat %s | grep EXE | grep PROFIT|awk '{print $3 \" \" $4}'" % filename)
tmp_time = stl_time.split("\n")

stl_time = []
for time in tmp_time:
    stl_time.append(time[:-1])
print(stl_time)


profit = subprocess.getoutput("cat %s | grep EXE | grep PROFIT| awk '{print $5}'" % filename)
tmp_profit = profit.split("\n")

profit = []
for pf in tmp_profit:
    profit.append(pf.split("=")[1])

print(profit)
 

print("order_time | order_price | trade_flag | stl_time | profit")

for i in range(0, len(profit)):
    print("%s | %s | %s | %s | %s" % (order_time[i], current_price[i], trade_flag[i], stl_time[i], profit[i]))

