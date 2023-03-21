#!/usr/bin/bash
clear
echo "dzien dobry"
echo "witam w najlepszym programie do odtwarzania komputerow"
cd /app

echo "Bootstrapping..."
modprobe nfs
python3 bootstrap.py
exitCode=$?
if [ "$exitCode" != "0" ]; then
	echo "FailRP bootstrap failed: init error ${exitCode}"
	# echo "Halting in 10 seconds"
	# shutdown 10
	# sleep 10
	# exit
fi

bash
echo "FailRP finished"
exit