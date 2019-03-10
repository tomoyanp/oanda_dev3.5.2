TODAY=`date +%Y-%m-%d`
LOGTIME=`date +%Y%m%d%H%M%S`
source /env/python35/bin/activate
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py AUD_JPY $TODAY production> /var/log/product/aud_jpy_$LOGTIME.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py EUR_JPY $TODAY production> /var/log/product/eur_jpy_$LOGTIME.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py GBP_JPY $TODAY production> /var/log/product/gbp_jpy_$LOGTIME.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py EUR_USD $TODAY production> /var/log/product/usd_jpy_$LOGTIME.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py AUD_USD $TODAY production> /var/log/product/aud_usd_$LOGTIME.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py GBP_USD $TODAY production> /var/log/product/gbp_usd_$LOGTIME.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py USD_JPY $TODAY production> /var/log/product/usd_jpy_$LOGTIME.log &
