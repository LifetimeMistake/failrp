#!/usr/bin/bash
cd /app
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
echo "nfs" > /etc/modules
wget "https://bootstrap.pypa.io/get-pip.py"
python3 get-pip.py --break-system-packages
rm get-pip.py

apt update && apt install vitetris nsnake beep
pip install -r bootstrap-requirements.txt --break-system-packages
pip install -r requirements.txt --break-system-packages

echo "" > /etc/resolv.conf

systemctl disable start-ocs-live
systemctl enable start-failrp