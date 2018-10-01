source /env/python35/bin/activate
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_price.py "GBP_JPY" > /var/log/product/insert_price_gbp_jpy.log &
sleep 10
nohup python /home/tomoyan/staging/oanda_dev3.5.2/utility/insert_multi_table.py "GBP_JPY" "production" > /var/log/product/insert_multi_gbp_jpy.log & 
