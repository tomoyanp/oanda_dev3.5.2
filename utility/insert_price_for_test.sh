#source /home/tomoyan/virtualenv/.python2.7/bin/activate
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py "GBP_JPY" > /dev/null &
sleep 10
#nohup python /home/tomoyan/staging/oanda_dev/utility/insert_price.py "USD_JPY" > /dev/null &
#sleep 10
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_multi_table.py "GBP_JPY" "production" > /dev/null & 
#sleep 10
#nohup python /home/tomoyan/staging/oanda_dev/utility/insert_multi_table.py "USD_JPY" "production" > /dev/null & 
