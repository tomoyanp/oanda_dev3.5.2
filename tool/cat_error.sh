ls -ltrd ../log/* | tail -n 1 | awk '{print $9}' | xargs cat $1
