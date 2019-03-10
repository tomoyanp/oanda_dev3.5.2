TODAY=`date +%Y-%m-%d`
source /env/python35/bin/activate
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_check.py "GBP_JPY" $TODAY > /var/log/product/insert_check_gbp_jpy.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_check.py "USD_JPY" $TODAY > /var/log/product/insert_check_gbp_jpy.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_check.py "AUD_JPY" $TODAY > /var/log/product/insert_check_gbp_jpy.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_check.py "EUR_JPY" $TODAY > /var/log/product/insert_check_gbp_jpy.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_check.py "EUR_USD" $TODAY > /var/log/product/insert_check_gbp_jpy.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_check.py "GBP_USD" $TODAY > /var/log/product/insert_check_gbp_jpy.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_check.py "AUD_USD" $TODAY > /var/log/product/insert_check_gbp_jpy.log &
