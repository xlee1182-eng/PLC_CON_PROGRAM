#!/bin/bash

sed -i "s/{PLC_LIST}/${PLC_LIST}/g" /source/Config.json

cd /source
python3 server.py
