#!/bin/bash

sed -i "s/{USE_LOCAL_FILE}/${USE_LOCAL_FILE}/g" /source/tamsConfig.json
sed -i "s/{PLC_LIST}/${PLC_LIST}/g" /source/tamsConfig.json

cd /source
python3 server.py