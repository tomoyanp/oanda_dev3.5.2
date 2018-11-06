import re
import subprocess
from datetime import datetime


file_list = subprocess.getoutput("ls *.result")
file_list = file_list.split("\n")

for rf in file_list:
  profit = 0

  write_file = open("%s_yearly_export.txt" % rf, "a")
  write_file.write("# %s\n" % rf)
  cmd = "cat %s | grep PROFIT| grep -v STL" % rf
  out = subprocess.getoutput(cmd)
  out = out.split("\n")


  cmd = "cat %s | grep EXECUTE|grep SETTLE" % rf
  stl_day = subprocess.getoutput(cmd)
  stl_day = stl_day.split("\n")

  profit = 0
  bef_year = 0

  for i in range(0, len(out)):
    temp = stl_day[i].split("at ")[-1]
    temp = datetime.strptime(temp, "%Y-%m-%d %H:%M:%S")
    year = temp.year

    pf = out[i].split("PROFIT=")[1]
    pf = float(pf)

    if bef_year == year or bef_year == 0:
      profit = profit + pf
    else:
      write_file.write("%s, %s\n" % (bef_year, profit))
      profit = pf

    bef_year = year
 
  write_file.write("%s, %s\n" % (bef_year, profit))
  

  write_file.close()
