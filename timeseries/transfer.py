import os
import shutil
import pandas as pd

LOOP_MODE = True

INPUT_FOLDER = 'timeseries_raw'
OUTPUT_FOLDER = 'timeseries_continuous'
TRANSFER_FOLDER = 'timeseries_transfer'

station_list = [
'12355500',
'12389500',
'12355000',
'12335100',
'12330000',
'12304500',
'12302055',
'06295113',
'05014500',
'06177500',
'06079000',
'06078500',
'06061500',
'06183450',
'06137570',
'06131200',
'06033000',
'06019500',
'76M_01100',
'76HB_01000'
]

if LOOP_MODE:
    for file_name in station_list:
        source = os.path.join(OUTPUT_FOLDER, f'{file_name}.csv')
        destination = os.path.join(TRANSFER_FOLDER, f'{file_name}.csv')
        shutil.copy(source, destination)



