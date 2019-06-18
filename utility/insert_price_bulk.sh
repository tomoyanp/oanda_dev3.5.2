TODAY=`date +%Y-%m-%d`
LOGTIME=`date +%Y%m%d%H%M%S`
source /env/python35/bin/activate
nohup python insert_price.py EUR_GBP 2017-04-01 bulk day > /dev/null &
nohup python insert_price.py EUR_GBP 2017-04-01 bulk 8h > /dev/null &
nohup python insert_price.py EUR_GBP 2017-04-01 bulk 3h > /dev/null &
nohup python insert_price.py EUR_GBP 2017-04-01 bulk 1h > /dev/null &
nohup python insert_price.py EUR_GBP 2017-04-01 bulk 30m > /dev/null &
nohup python insert_price.py EUR_GBP 2017-04-01 bulk 15m > /dev/null &
nohup python insert_price.py EUR_GBP 2017-04-01 bulk 5m > /dev/null &
nohup python insert_price.py EUR_GBP 2017-04-01 bulk 1m > /dev/null &
nohup python insert_price.py EUR_GBP 2017-04-01 bulk 5s > /dev/null &
