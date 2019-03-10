TODAY=`date +%Y-%m-%d`
source /env/python35/bin/activate
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_multi_real_table.py AUD_JPY $TODAY > /var/log/product/aud_jpy.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_multi_real_table.py EUR_JPY $TODAY > /var/log/product/eur_jpy.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_multi_real_table.py GBP_JPY $TODAY > /var/log/product/gbp_jpy.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_multi_real_table.py EUR_USD $TODAY > /var/log/product/usd_jpy.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_multi_real_table.py AUD_USD $TODAY > /var/log/product/aud_usd.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_multi_real_table.py GBP_USD $TODAY > /var/log/product/gbp_usd.log &
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_multi_real_table.py USD_JPY $TODAY > /var/log/product/usd_jpy.log &
