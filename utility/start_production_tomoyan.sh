source /env/python35/bin/activate
nohup python /home/tomoyan/production/oanda_dev3.5.2/main.py "EUR_JPY" "production" "lstm" "trendreverse_test" > /var/log/product/tomoyan_production.log &

