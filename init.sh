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
	echo "Halting in 120 seconds..."
	shutdown 2
	echo "Dropping into emergency shell"
	bash
	exit
fi

python3 app.py
echo "FailRP finished"
shutdown 0
exit