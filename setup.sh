#!/bin/bash

# install all requirements lib
pip install --no-cache-dir -r requirements.txt


# make fedasync global lib
python make_fedasync_global.py install


