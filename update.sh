#!/bin/bash
cd /root/arkadiy_bot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
systemctl restart arkadiybot
echo "Update completed at $(date)" >> /root/arkadiy_bot/update.log
