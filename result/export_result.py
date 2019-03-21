import re
import subprocess


file_list = subprocess.getoutput("ls *.log")
file_list = file_list.split("\n")

for rf in file_list:
  profit = 0

  write_file = open("profit_export.txt", "a")
  write_file.write("#######################\n")
  write_file.write("# %s\n" % rf)
  cmd = "cat %s | grep PROFIT" % rf
  out = subprocess.getoutput(cmd)
  out = out.split("\n")

  for line in out:
    if re.search("PROFIT", line):
        pf = line.split("PROFIT=")[1]
        pf = float(pf)
        profit = profit + pf


  write_file.write("# PROFIT=%s\n" % profit)
