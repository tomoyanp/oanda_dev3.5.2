# coding: utf-8


import subprocess



fileList = subprocess.getoutput("ls *.log")
fileList = fileList.split("\n")


for fl in fileList:
    filename = fl.strip()
    entry_count = subprocess.getoutput("cat %s | grep profit | wc -l" % filename)
    out = subprocess.getoutput("cat %s | grep profit" % filename)
    out = out.split("\n")
    profit = 0
    for i in out:
        profit = profit + float(i.split("=")[-1])

    print("%s Profit = %s, Entry count = %s" % (filename, profit, entry_count))



#print(profit)
