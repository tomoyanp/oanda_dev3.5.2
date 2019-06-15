#coding: utf-8
import subprocess
from datetime import datetime
import sys

filename = sys.argv[1]
stl_time = subprocess.getoutput("cat %s | grep \"SETTLEMENT\" | awk \'{print $7 \" \" $8}\'" % filename)
order_time = subprocess.getoutput("cat %s | grep \"EXECUTE ORDER\" | awk \'{print $5 \" \" $6}\'" % filename)
order_time = order_time.split("\n")
stl_time = stl_time.split("\n")
for i in range(0, len(stl_time)):
    tmp_order = datetime.strptime(order_time[i], "%Y-%m-%d %H:%M:%S")
    tmp_stl =  datetime.strptime(stl_time[i], "%Y-%m-%d %H:%M:%S")
    print(tmp_stl - tmp_order)

