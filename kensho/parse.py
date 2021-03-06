import re
import subprocess
from datetime import datetime
import time


file_list = subprocess.getoutput("ls *.result")
file_list = file_list.split("\n")

import sys
filename = sys.argv[1].strip()


write_file = open("%s.parse" % filename, "a")
write_file.write("# %s\n" % filename)
cmd = "cat %s | grep Algorithm" % filename
out = subprocess.getoutput(cmd)
out = out.split("\n")

algo_list = out

cmd = "cat %s | grep \"EXECUTE ORDER\"" % filename
out = subprocess.getoutput(cmd)
out = out.split("\n")

order_list = out

cmd = "cat %s | grep \"EXECUTE\" | grep \"SETTLE\"" % filename
out = subprocess.getoutput(cmd)
out = out.split("\n")

settle_list = out

cmd = "cat %s | grep PROFIT | grep -v STL" % filename
out = subprocess.getoutput(cmd)
out = out.split("\n")

profit_list = out


cmd = "cat %s | grep -e trade_flag -e TRADE_FLAG" % filename
out = subprocess.getoutput(cmd)
out = out.split("\n")

flag_list = out

print("order_time, settle_time, hold_time, algorithm, side, profit")
for i in range(0, len(profit_list)):
  algo = algo_list[i]
  
  order_time = order_list[i].split(" ")[4] + " " + order_list[i].split(" ")[5]
  profit = profit_list[i].split(" ")[1].split("=")[1]
  side = flag_list[i].split("=")[1]
  settle_time = settle_list[i].split("at ")[-1]

  order_ptime = datetime.strptime(order_time, "%Y-%m-%d %H:%M:%S")
  settle_ptime = datetime.strptime(settle_time, "%Y-%m-%d %H:%M:%S")
  difference_time = settle_ptime - order_ptime

  start_time = datetime.strptime(order_time, "%Y-%m-%d %H:%M:%S")
  end_time = datetime.strptime(settle_time, "%Y-%m-%d %H:%M:%S")
  end_time = time.mktime(end_time.timetuple())
  start_time = time.mktime(start_time.timetuple())
  result = end_time - start_time
  result = datetime.fromtimestamp(result)
  days = result.day-1
  hour = result.hour

  print(order_time + "," + settle_time + "," + str(difference_time.total_seconds()) + "," + algo + "," + side + "," + profit)
 
write_file.close()
