import json
import os

CONFIG_LOC = 'data/config'
config = {}

for file in os.listdir(CONFIG_LOC):
    f = open(CONFIG_LOC + '/' + file, 'r')
    config[file.split('.')[0]] = json.load(f)
    f.close()