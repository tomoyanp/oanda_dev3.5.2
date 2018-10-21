TODAY=`date "+%Y%m%d%H%M%S"`
#echo $TODAY
mysqldump -u tomoyan -p oanda_db -r /home/tomoyan/oanda_db_$TODAY.dmp
