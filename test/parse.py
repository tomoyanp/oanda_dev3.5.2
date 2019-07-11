# coding: utf-8


import subprocess



out = subprocess.getoutput("cat result")
out = out.split("\n")

profit = 0
for i in out:
    profit = profit + float(i.split("=")[-1])

print(profit)
