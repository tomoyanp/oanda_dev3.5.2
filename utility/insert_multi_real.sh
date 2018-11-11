source /env/python35/bin/activate
nohup python insert_multi_real_table.py AUD_JPY > /var/log/product/aud_jpy.log &
nohup python insert_multi_real_table.py EUR_JPY > /var/log/product/eur_jpy.log &
nohup python insert_multi_real_table.py GBP_JPY > /var/log/product/gbp_jpy.log &
nohup python insert_multi_real_table.py EUR_USD > /var/log/product/usd_jpy.log &
nohup python insert_multi_real_table.py AUD_USD > /var/log/product/aud_usd.log &
nohup python insert_multi_real_table.py GBP_USD > /var/log/product/gbp_usd.log &
nohup python insert_multi_real_table.py USD_JPY > /var/log/product/usd_jpy.log &
