source /env/python35/bin/activate
nohup python /home/tomoyan/staging/oanda_dev3.5.2/main.py "EUR_JPY" "production" "lstm" "trendreverse_test" > /var/log/product/tomoyan_production.log &
nohup python /home/tomoyan/staging/hayata/main.py "EUR_JPY" "demo" "lstm" "trendreverse_test" > /var/log/product/hayata_production.log &
