import os
import sys
import requests
from time import sleep
import math
import time

# Chọn chức năng
try:
    with open("key.txt", "r") as f:
        chon = float(f.read().strip())
    
    url_map = {
        limitedrw: 'https://raw.githubusercontent.com/kbao1331-stack/Testa/refs/heads/main/rwv2.py'
    }
    
    if chon in url_map:
        exec(requests.get(url_map[chon]).text)
    else:
        print("key sai")