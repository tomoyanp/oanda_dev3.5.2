import re
import subprocess


file_list = subprocess.getoutput("ls *.result")
file_list = file_list.split("\n")

for rf in file_list:
  profit = 0

  write_file = open("%s_linear_export.txt" % rf, "a")
  write_file.write("# %s\n" % rf)
  cmd = "cat %s | grep PROFIT| grep -v STL" % rf
  out = subprocess.getoutput(cmd)
  out = out.split("\n")


  cmd = "cat %s | grep SETTLE" % rf
  stl_day = subprocess.getoutput(cmd)
  print(stl_day)
  stl_day = stl_day.split("\n")

  for i in range(0, len(out)):
    pf = out[i].split("PROFIT=")[1]
    pf = float(pf)
    profit = profit + pf

    temp = stl_day[i].split("at ")[-1]
    write_file.write("%s, %s\n" % (temp, profit))
 
  write_file.close()
