TODAY=`date +%Y-%m-%d`
LOGTIME=`date +%Y%m%d%H%M%S`
source /env/python35/bin/activate
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py AUD_JPY 2019-01-01 bulk > /var/log/product/aud_jpy_bulk_$LOGTIME.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py EUR_JPY 2019-01-01 bulk > /var/log/product/eur_jpy_bulk_$LOGTIME.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py GBP_JPY 2019-01-01 bulk > /var/log/product/gbp_jpy_bulk_$LOGTIME.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py EUR_USD 2019-01-01 bulk > /var/log/product/usd_jpy_bulk_$LOGTIME.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py AUD_USD 2019-01-01 bulk > /var/log/product/aud_usd_bulk_$LOGTIME.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py GBP_USD 2019-01-01 bulk > /var/log/product/gbp_usd_bulk_$LOGTIME.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py USD_JPY 2019-01-01 bulk > /var/log/product/usd_jpy_bulk_$LOGTIME.log &
