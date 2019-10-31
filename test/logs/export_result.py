import re
import subprocess


file_list = subprocess.getoutput("ls *.result")
file_list = file_list.split("\n")

for rf in file_list:
  profit = 0

  write_file = open("profit_export.txt", "a")
  write_file.write("#######################\n")
  write_file.write("# %s\n" % rf)
  cmd = "cat %s | grep Profit" % rf
  out = subprocess.getoutput(cmd)
  out = out.split("\n")
  order_count = len(out)

  profit_count = 0
  stoploss_count = 0
  for line in out:
    if re.search("Profit", line):
        pf = line.split("Profit=")[1]
        pf = float(pf)
        if pf < 0:
          stoploss_count += 1
        else:
          profit_count += 1

        profit = profit + pf


  write_file.write("# Profit=%s, Total_trade=%s, Profit_count=%s, Stoploss_count=%s, Profit_percentage=%s\n" % (profit, order_count, profit_count, stoploss_count, (profit_count/order_count)))
  write_file.close()

out = subprocess.getoutput("cat profit_export.txt")
print(out)


